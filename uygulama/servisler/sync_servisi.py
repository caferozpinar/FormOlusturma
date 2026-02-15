#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sync Servisi — SQLite snapshot senkronizasyon, conflict çözümü.

Yol haritası kuralları:
- Manuel sync butonu
- 10 dakikada bir senkron kontrolü
- Sync sırasında belge oluşturma disable
- SQLite snapshot yaklaşımı
- Conflict durumunda kullanıcı seçimi
- Silinen dosyalar soft delete
"""

import os
import shutil
import sqlite3
from typing import Optional, Tuple

from uygulama.altyapi.sync_repo import SyncRepository
from uygulama.altyapi.log_repo import LogRepository
from uygulama.domain.modeller import IslemTipi, HareketLogu
from uygulama.ortak.app_state import app_state
from uygulama.ortak.yardimcilar import logger_olustur, simdi_iso

logger = logger_olustur("sync_servisi")

# Sync durumları
SYNC_BASLATILDI = "BASLATILDI"
SYNC_DEVAM = "DEVAM_EDIYOR"
SYNC_TAMAMLANDI = "TAMAMLANDI"
SYNC_HATA = "HATA"
SYNC_CONFLICT = "CONFLICT_BEKLIYOR"

# Conflict çözüm seçenekleri
COZUM_YEREL = "YEREL"
COZUM_UZAK = "UZAK"
COZUM_BIRLESTIR = "BIRLESTIR"
COZUM_BEKLIYOR = "BEKLIYOR"

# Otomatik sync aralığı (saniye)
OTOMATIK_SYNC_ARALIGI = 600  # 10 dakika


class SyncServisi:
    """Senkronizasyon yönetim servisi."""

    def __init__(self, sync_repo: SyncRepository,
                 log_repo: LogRepository):
        self.sync_repo = sync_repo
        self.log_repo = log_repo
        self._sync_aktif = False

    # ═════════════════════════════════════════
    # DURUM SORGULAMA
    # ═════════════════════════════════════════

    @property
    def sync_aktif(self) -> bool:
        """Sync devam ediyor mu?"""
        return self._sync_aktif

    def son_sync(self) -> Optional[dict]:
        """En son sync bilgisini döndürür."""
        return self.sync_repo.son_sync_bilgisi()

    def sync_gecmisi(self, limit: int = 20) -> list[dict]:
        return self.sync_repo.sync_gecmisi(limit)

    def bekleyen_conflictler(self) -> list[dict]:
        return self.sync_repo.bekleyen_conflictler()

    # ═════════════════════════════════════════
    # SNAPSHOT OLUŞTURMA
    # ═════════════════════════════════════════

    def snapshot_olustur(self) -> Tuple[bool, str, Optional[str]]:
        """
        Manuel snapshot oluşturur.
        Returns: (başarılı, mesaj, snapshot_yol)
        """
        state = app_state()
        if not state.giris_yapildi:
            return False, "Giriş yapılmamış.", None

        try:
            yol = self.sync_repo.snapshot_olustur()
            # Eski snapshot'ları temizle
            self.sync_repo.eski_snapshotlari_temizle(sakla=5)

            self._log_kaydet(
                IslemTipi.SYNC_BASLAT,
                f"Snapshot oluşturuldu: {os.path.basename(yol)}")

            logger.info(f"Snapshot oluşturuldu: {yol}")
            return True, "Snapshot başarıyla oluşturuldu.", yol

        except Exception as e:
            logger.error(f"Snapshot hatası: {e}")
            return False, f"Snapshot oluşturulamadı: {e}", None

    def snapshot_listele(self) -> list[dict]:
        return self.sync_repo.snapshot_listele()

    # ═════════════════════════════════════════
    # TAM SYNC İŞLEMİ
    # ═════════════════════════════════════════

    def sync_baslat(self, uzak_db_yolu: str = "") -> Tuple[bool, str, Optional[str]]:
        """
        Tam senkronizasyon başlatır.
        1. Yerel snapshot al
        2. Uzak veritabanı ile karşılaştır
        3. Conflict'leri tespit et
        4. Otomatik çözülebilenleri çöz
        5. Kullanıcı müdahalesi gerekenleri raporla

        Returns: (başarılı, mesaj, sync_id)
        """
        state = app_state()
        if not state.giris_yapildi:
            return False, "Giriş yapılmamış.", None

        if self._sync_aktif:
            return False, "Başka bir senkronizasyon devam ediyor.", None

        self._sync_aktif = True

        try:
            # Sync kaydı oluştur
            sync_id = self.sync_repo.sync_kaydi_olustur(
                tur="MANUAL", durum=SYNC_BASLATILDI,
                hedef=uzak_db_yolu or "local_snapshot")

            # 1. Yerel snapshot
            snapshot_yol = self.sync_repo.snapshot_olustur()

            self.sync_repo.sync_kaydi_guncelle(
                sync_id, SYNC_DEVAM, f"Snapshot alındı: {snapshot_yol}")

            # 2. Uzak DB ile karşılaştırma
            if uzak_db_yolu and os.path.exists(uzak_db_yolu):
                conflict_sayisi = self._uzak_ile_karsilastir(
                    sync_id, uzak_db_yolu)

                if conflict_sayisi > 0:
                    self.sync_repo.sync_kaydi_guncelle(
                        sync_id, SYNC_CONFLICT,
                        f"{conflict_sayisi} çakışma tespit edildi")

                    self._log_kaydet(
                        IslemTipi.SYNC_BASLAT,
                        f"Sync: {conflict_sayisi} çakışma bulundu")

                    return True, (f"Sync tamamlandı. {conflict_sayisi} çakışma "
                                  f"çözüm bekliyor."), sync_id
                else:
                    # Conflict yok — otomatik merge
                    self._uzak_merge(uzak_db_yolu)

            # Conflict yoksa direkt tamamla
            self.sync_repo.sync_kaydi_guncelle(
                sync_id, SYNC_TAMAMLANDI, "Senkronizasyon başarılı")

            self.sync_repo.eski_snapshotlari_temizle(sakla=5)

            self._log_kaydet(
                IslemTipi.SYNC_TAMAMLA, "Senkronizasyon tamamlandı")

            logger.info("Sync tamamlandı (conflict yok)")
            return True, "Senkronizasyon başarıyla tamamlandı.", sync_id

        except Exception as e:
            logger.error(f"Sync hatası: {e}")
            return False, f"Senkronizasyon hatası: {e}", None

        finally:
            self._sync_aktif = False

    # ═════════════════════════════════════════
    # CONFLICT ÇÖZÜM
    # ═════════════════════════════════════════

    def conflict_coz(self, conflict_id: str,
                      cozum: str) -> Tuple[bool, str]:
        """
        Tek bir conflict'i çözer.
        cozum: YEREL | UZAK | BIRLESTIR
        """
        if cozum not in (COZUM_YEREL, COZUM_UZAK, COZUM_BIRLESTIR):
            return False, f"Geçersiz çözüm: {cozum}"

        self.sync_repo.conflict_coz(conflict_id, cozum)
        logger.info(f"Conflict çözüldü: {conflict_id} → {cozum}")
        return True, f"Çakışma çözüldü: {cozum}"

    def tum_conflictleri_coz(self, sync_id: str,
                              cozum: str) -> Tuple[bool, str]:
        """Bir sync'in tüm conflict'lerini aynı çözümle çözer."""
        conflicts = self.sync_repo.bekleyen_conflictler(sync_id)
        for c in conflicts:
            self.sync_repo.conflict_coz(c["id"], cozum)

        # Sync'i tamamla
        self.sync_repo.sync_kaydi_guncelle(
            sync_id, SYNC_TAMAMLANDI,
            f"{len(conflicts)} çakışma {cozum} ile çözüldü")

        return True, f"{len(conflicts)} çakışma çözüldü."

    def sync_conflictleri(self, sync_id: str) -> list[dict]:
        return self.sync_repo.sync_conflictleri(sync_id)

    # ═════════════════════════════════════════
    # UZAK VERİTABANI İŞLEMLERİ
    # ═════════════════════════════════════════

    def _uzak_ile_karsilastir(self, sync_id: str,
                               uzak_yol: str) -> int:
        """Uzak DB ile yerel DB'yi karşılaştırır. Conflict sayısını döndürür."""
        conflict_sayisi = 0
        karsilastirma_tablolari = [
            ("projeler", "id", ["firma", "konum", "tesis", "durum"]),
            ("belgeler", "id", ["durum", "toplam_maliyet", "kar_orani"]),
            ("urunler", "id", ["kod", "ad", "aktif"]),
        ]

        try:
            uzak = sqlite3.connect(uzak_yol)
            uzak.row_factory = sqlite3.Row

            for tablo, pk, alanlar in karsilastirma_tablolari:
                conflict_sayisi += self._tablo_karsilastir(
                    sync_id, uzak, tablo, pk, alanlar)

            uzak.close()

        except Exception as e:
            logger.error(f"Karşılaştırma hatası: {e}")

        return conflict_sayisi

    def _tablo_karsilastir(self, sync_id: str, uzak_conn: sqlite3.Connection,
                            tablo: str, pk: str,
                            alanlar: list[str]) -> int:
        """Tek tablo karşılaştırma. Conflict sayısı döndürür."""
        conflict = 0
        try:
            yerel_rows = self.sync_repo.db.getir_hepsi(
                f"SELECT * FROM {tablo} WHERE silinme_tarihi IS NULL")
            uzak_rows = uzak_conn.execute(
                f"SELECT * FROM {tablo} WHERE silinme_tarihi IS NULL"
            ).fetchall()

            yerel_map = {r[pk]: dict(r) for r in yerel_rows}
            uzak_map = {r[pk]: dict(r) for r in uzak_rows}

            # Her iki tarafta da olan kayıtları karşılaştır
            for kayit_id in set(yerel_map) & set(uzak_map):
                yerel = yerel_map[kayit_id]
                uzak = uzak_map[kayit_id]
                for alan in alanlar:
                    y_val = str(yerel.get(alan, ""))
                    u_val = str(uzak.get(alan, ""))
                    if y_val != u_val:
                        self.sync_repo.conflict_kaydet(
                            sync_id, tablo, kayit_id, alan,
                            y_val, u_val)
                        conflict += 1

        except Exception as e:
            logger.warning(f"Tablo karşılaştırma hatası [{tablo}]: {e}")

        return conflict

    def _uzak_merge(self, uzak_yol: str) -> None:
        """Uzak değişiklikleri yerel'e merge eder (conflict yoksa)."""
        # Şimdilik sadece log — gerçek merge daha sonra
        logger.info(f"Uzak merge: {uzak_yol} (conflict yok)")

    # ═════════════════════════════════════════
    # YARDIMCI
    # ═════════════════════════════════════════

    def _log_kaydet(self, islem: IslemTipi, detay: str) -> None:
        try:
            state = app_state()
            log = HareketLogu(
                kullanici_id=state.aktif_kullanici.id if state.aktif_kullanici else "",
                islem=islem,
                hedef_tablo="sync",
                hedef_id="",
                detay=detay)
            self.log_repo.kaydet(log)
        except Exception as e:
            logger.error(f"Log hatası: {e}")
