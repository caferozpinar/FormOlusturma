#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Belge Servisi — Belge iş kuralları.
Revizyon sistemi, snapshot mantığı, durum geçişleri,
maliyet hesaplama, proje durum etkileşimi.
"""

import json
from typing import Optional, Tuple

from uygulama.domain.modeller import (
    Belge, BelgeDurumu, ProjeDurumu, HareketLogu, IslemTipi
)
from uygulama.altyapi.belge_repo import BelgeRepository
from uygulama.altyapi.proje_repo import ProjeRepository
from uygulama.altyapi.log_repo import LogRepository
from uygulama.ortak.app_state import app_state
from uygulama.ortak.yardimcilar import logger_olustur, simdi_iso

logger = logger_olustur("belge_servisi")

# Geçerli belge türleri
BELGE_TURLERI = ("TEKLİF", "KEŞİF", "TANIM")

# Durum geçiş kuralları: mevcut_durum → izin verilen hedefler
DURUM_GECISLERI = {
    BelgeDurumu.DRAFT:    [BelgeDurumu.SENT],
    BelgeDurumu.SENT:     [BelgeDurumu.APPROVED, BelgeDurumu.REJECTED,
                           BelgeDurumu.EXPIRED],
    BelgeDurumu.REJECTED: [BelgeDurumu.DRAFT],  # düzeltip tekrar taslak
    BelgeDurumu.APPROVED: [],  # son durum
    BelgeDurumu.EXPIRED:  [BelgeDurumu.DRAFT],  # yenilenebilir
}


class BelgeServisi:
    """Belge yönetim servisi."""

    def __init__(self, belge_repo: BelgeRepository,
                 proje_repo: ProjeRepository,
                 log_repo: LogRepository,
                 maliyet_repo=None):
        self.belge_repo = belge_repo
        self.proje_repo = proje_repo
        self.log_repo = log_repo
        self.maliyet_repo = maliyet_repo

    # ═════════════════════════════════════════
    # BELGE OLUŞTURMA
    # ═════════════════════════════════════════

    def olustur(self, proje_id: str, tur: str) -> Tuple[bool, str, Optional[Belge]]:
        """
        Yeni belge oluşturur (Rev.1).
        Aynı tür için mevcut belge varsa yeni revizyon oluşturulmalı.
        """
        state = app_state()
        if not state.giris_yapildi:
            return False, "Giriş yapılmamış.", None

        # Validasyon
        tur = tur.upper().strip()
        if tur not in BELGE_TURLERI:
            return False, f"Geçersiz belge türü. İzin verilenler: {', '.join(BELGE_TURLERI)}", None

        # Proje kontrolü
        proje = self.proje_repo.id_ile_getir(proje_id)
        if not proje:
            return False, "Proje bulunamadı.", None
        if proje.durum == ProjeDurumu.CLOSED:
            return False, "Kapalı projede yeni belge oluşturulamaz.", None

        # Bu tür için mevcut belge var mı?
        mevcut = self.belge_repo.proje_belgesi_son_revizyon(proje_id, tur)
        if mevcut:
            return False, (f"Bu proje için zaten bir {tur} belgesi mevcut "
                          f"(Rev.{mevcut.revizyon_no}). "
                          f"Yeni revizyon açmak için 'Revizyon Aç' kullanın."), None

        belge = Belge(
            proje_id=proje_id,
            tur=tur,
            revizyon_no=1,
            durum=BelgeDurumu.DRAFT,
            olusturan_id=state.aktif_kullanici.id,
        )
        self.belge_repo.olustur(belge)

        self._log_kaydet(
            IslemTipi.BELGE_OLUSTUR, "belgeler", belge.id,
            f"{tur} belgesi oluşturuldu (Rev.1) — Proje: {proje.hash_kodu}"
        )

        logger.info(f"Belge oluşturuldu: {tur} Rev.1 [{proje.hash_kodu}]")
        return True, f"{tur} belgesi oluşturuldu.", belge

    # ═════════════════════════════════════════
    # REVİZYON SİSTEMİ
    # ═════════════════════════════════════════

    def revizyon_ac(self, belge_id: str) -> Tuple[bool, str, Optional[Belge]]:
        """
        Mevcut belgenin yeni revizyonunu oluşturur.
        Eski revizyon snapshot alınarak korunur.
        Yeni revizyon DRAFT olarak başlar.
        """
        state = app_state()
        if not state.giris_yapildi:
            return False, "Giriş yapılmamış.", None

        mevcut = self.belge_repo.id_ile_getir(belge_id)
        if not mevcut:
            return False, "Belge bulunamadı.", None

        # Proje kontrolü
        proje = self.proje_repo.id_ile_getir(mevcut.proje_id)
        if not proje:
            return False, "Proje bulunamadı.", None
        if proje.durum == ProjeDurumu.CLOSED:
            return False, "Kapalı projede yeni revizyon açılamaz.", None

        # Sadece son revizyon üzerinden yeni revizyon açılabilir
        son = self.belge_repo.proje_belgesi_son_revizyon(
            mevcut.proje_id, mevcut.tur)
        if son and son.id != mevcut.id:
            return False, (f"Sadece son revizyon üzerinden yeni revizyon açılabilir. "
                          f"Son revizyon: Rev.{son.revizyon_no}"), None

        # DRAFT durumdaki belge üzerinden revizyon açılamaz (önce kaydet/gönder)
        if mevcut.durum == BelgeDurumu.DRAFT:
            return False, "Taslak durumundaki belge için revizyon açılamaz. Önce gönderin.", None

        # Eski belgenin snapshot'ını al
        snapshot = self._snapshot_olustur(mevcut)
        mevcut.snapshot_veri = json.dumps(snapshot, ensure_ascii=False)
        self.belge_repo.guncelle(mevcut)

        # Yeni revizyon oluştur
        yeni_rev = mevcut.revizyon_no + 1
        yeni_belge = Belge(
            proje_id=mevcut.proje_id,
            tur=mevcut.tur,
            revizyon_no=yeni_rev,
            durum=BelgeDurumu.DRAFT,
            toplam_maliyet=mevcut.toplam_maliyet,
            kar_orani=mevcut.kar_orani,
            kdv_orani=mevcut.kdv_orani,
            olusturan_id=state.aktif_kullanici.id,
        )
        self.belge_repo.olustur(yeni_belge)

        # Mevcut belgenin ürünlerini yeni revizyona kopyala
        self._urunleri_kopyala(mevcut.id, yeni_belge.id)

        self._log_kaydet(
            IslemTipi.REVIZYON_AC, "belgeler", yeni_belge.id,
            f"Yeni revizyon açıldı: {mevcut.tur} Rev.{yeni_rev} "
            f"(önceki: Rev.{mevcut.revizyon_no})"
        )

        logger.info(f"Revizyon açıldı: {mevcut.tur} Rev.{yeni_rev}")
        return True, f"Rev.{yeni_rev} oluşturuldu.", yeni_belge

    # ═════════════════════════════════════════
    # DURUM GEÇİŞLERİ
    # ═════════════════════════════════════════

    def durum_degistir(self, belge_id: str,
                        yeni_durum: BelgeDurumu) -> Tuple[bool, str]:
        """Belge durumunu değiştirir. Geçiş kurallarını uygular."""
        state = app_state()
        if not state.giris_yapildi:
            return False, "Giriş yapılmamış."

        belge = self.belge_repo.id_ile_getir(belge_id)
        if not belge:
            return False, "Belge bulunamadı."

        # Geçiş kontrolü
        izinli = DURUM_GECISLERI.get(belge.durum, [])
        if yeni_durum not in izinli:
            return False, (f"{belge.durum.value} → {yeni_durum.value} "
                          f"geçişine izin verilmiyor.")

        eski = belge.durum
        belge.durum = yeni_durum
        self.belge_repo.guncelle(belge)

        # APPROVED ise snapshot al ve projeyi kapat
        if yeni_durum == BelgeDurumu.APPROVED:
            snapshot = self._snapshot_olustur(belge)
            belge.snapshot_veri = json.dumps(snapshot, ensure_ascii=False)
            self.belge_repo.guncelle(belge)
            self._proje_kapat_otomatik(belge.proje_id)

        # Log kaydet
        islem_map = {
            BelgeDurumu.SENT: IslemTipi.BELGE_GONDER,
            BelgeDurumu.APPROVED: IslemTipi.BELGE_ONAYLA,
            BelgeDurumu.REJECTED: IslemTipi.BELGE_REDDET,
        }
        islem = islem_map.get(yeni_durum, IslemTipi.BELGE_GUNCELLE)

        self._log_kaydet(
            islem, "belgeler", belge_id,
            f"Durum değişikliği: {eski.value} → {yeni_durum.value} "
            f"({belge.tur} Rev.{belge.revizyon_no})"
        )

        logger.info(f"Belge durumu değişti: {eski.value} → {yeni_durum.value}")
        return True, f"Belge durumu güncellendi: {yeni_durum.value}"

    def gonder(self, belge_id: str) -> Tuple[bool, str]:
        return self.durum_degistir(belge_id, BelgeDurumu.SENT)

    def onayla(self, belge_id: str) -> Tuple[bool, str]:
        return self.durum_degistir(belge_id, BelgeDurumu.APPROVED)

    def reddet(self, belge_id: str) -> Tuple[bool, str]:
        return self.durum_degistir(belge_id, BelgeDurumu.REJECTED)

    # ═════════════════════════════════════════
    # GÜNCELLEME VE MALİYET
    # ═════════════════════════════════════════

    def mali_bilgileri_guncelle(self, belge_id: str,
                                 toplam_maliyet: float = None,
                                 kar_orani: float = None,
                                 kdv_orani: float = None) -> Tuple[bool, str]:
        """Belgenin mali bilgilerini günceller."""
        state = app_state()
        if not state.giris_yapildi:
            return False, "Giriş yapılmamış."

        belge = self.belge_repo.id_ile_getir(belge_id)
        if not belge:
            return False, "Belge bulunamadı."

        if belge.durum == BelgeDurumu.APPROVED:
            return False, "Onaylanmış belge düzenlenemez."

        if toplam_maliyet is not None:
            belge.toplam_maliyet = toplam_maliyet
        if kar_orani is not None:
            belge.kar_orani = kar_orani
        if kdv_orani is not None:
            belge.kdv_orani = kdv_orani

        self.belge_repo.guncelle(belge)
        return True, "Mali bilgiler güncellendi."

    @staticmethod
    def maliyet_hesapla(toplam_maliyet: float, kar_orani: float,
                         kdv_orani: float) -> dict:
        """Maliyet, kâr, KDV hesaplar."""
        kar_tutari = toplam_maliyet * (kar_orani / 100.0)
        ara_toplam = toplam_maliyet + kar_tutari
        kdv_tutari = ara_toplam * (kdv_orani / 100.0)
        genel_toplam = ara_toplam + kdv_tutari
        return {
            "toplam_maliyet": round(toplam_maliyet, 2),
            "kar_orani": round(kar_orani, 2),
            "kar_tutari": round(kar_tutari, 2),
            "ara_toplam": round(ara_toplam, 2),
            "kdv_orani": round(kdv_orani, 2),
            "kdv_tutari": round(kdv_tutari, 2),
            "genel_toplam": round(genel_toplam, 2),
        }

    # ═════════════════════════════════════════
    # SİLME
    # ═════════════════════════════════════════

    def sil(self, belge_id: str) -> Tuple[bool, str]:
        """Belgeyi soft delete ile siler."""
        state = app_state()
        if not state.giris_yapildi:
            return False, "Giriş yapılmamış."

        belge = self.belge_repo.id_ile_getir(belge_id)
        if not belge:
            return False, "Belge bulunamadı."

        if belge.durum == BelgeDurumu.APPROVED:
            return False, "Onaylanmış belge silinemez."

        self.belge_repo.soft_delete(belge_id)

        self._log_kaydet(
            IslemTipi.BELGE_SIL, "belgeler", belge_id,
            f"Belge silindi: {belge.tur} Rev.{belge.revizyon_no}"
        )
        return True, "Belge silindi."

    # ═════════════════════════════════════════
    # LİSTELEME
    # ═════════════════════════════════════════

    def proje_belgeleri(self, proje_id: str) -> list[Belge]:
        return self.belge_repo.proje_belgeleri(proje_id)

    def getir(self, belge_id: str) -> Optional[Belge]:
        return self.belge_repo.id_ile_getir(belge_id)

    def revizyonlar(self, proje_id: str, tur: str) -> list[Belge]:
        return self.belge_repo.proje_tur_revizyonlari(proje_id, tur)

    def belge_urunleri(self, belge_id: str) -> list[dict]:
        return self.belge_repo.belge_urunlerini_getir(belge_id)

    def belge_alt_kalemleri(self, belge_id: str,
                             belge_urun_id: str = None) -> list[dict]:
        return self.belge_repo.belge_alt_kalemlerini_getir(
            belge_id, belge_urun_id)

    def proje_belge_istatistikleri(self, proje_id: str) -> dict:
        return self.belge_repo.proje_belge_istatistikleri(proje_id)

    # ═════════════════════════════════════════
    # ÜRÜN İŞLEMLERİ
    # ═════════════════════════════════════════

    def urun_ekle(self, belge_id: str, urun_id: str,
                   miktar: int = 1) -> Tuple[bool, str]:
        """Belgeye ürün ekler."""
        belge = self.belge_repo.id_ile_getir(belge_id)
        if not belge:
            return False, "Belge bulunamadı."
        if belge.durum == BelgeDurumu.APPROVED:
            return False, "Onaylanmış belge düzenlenemez."

        self.belge_repo.belge_urunu_ekle(belge_id, urun_id, miktar)
        return True, "Ürün eklendi."

    def urun_cikar(self, kayit_id: str) -> Tuple[bool, str]:
        """Belgeden ürün çıkarır."""
        self.belge_repo.belge_urunu_sil(kayit_id)
        return True, "Ürün çıkarıldı."

    # ═════════════════════════════════════════
    # YARDIMCI — ÖZEL
    # ═════════════════════════════════════════

    def _snapshot_olustur(self, belge: Belge) -> dict:
        """
        Belgenin tam snapshot'ını oluşturur.
        Maliyet Motoru V2: Parametre, girdi, formül ve hesap sonuçları dahil.
        """
        urunler = self.belge_repo.belge_urunlerini_getir(belge.id)
        alt_kalemler = self.belge_repo.belge_alt_kalemlerini_getir(belge.id)

        # Maliyet versiyonu snapshot'ları
        maliyet_snapshots = []
        if self.maliyet_repo:
            for ak in alt_kalemler:
                versiyon_id = ak.get("versiyon_id")
                komb_id = ak.get("kombinasyon_id")
                snap = {"alt_kalem_id": ak.get("alt_kalem_id", "")}
                if versiyon_id:
                    snap["versiyon_snapshot"] = \
                        self.maliyet_repo.versiyon_tam_snapshot(versiyon_id)
                if komb_id:
                    snap["kombinasyon"] = \
                        self.maliyet_repo.kombinasyon_getir(komb_id)
                if versiyon_id or komb_id:
                    maliyet_snapshots.append(snap)

        return {
            "snapshot_tarihi": simdi_iso(),
            "snapshot_versiyonu": 2,  # V2 format
            "belge": {
                "id": belge.id,
                "tur": belge.tur,
                "revizyon_no": belge.revizyon_no,
                "durum": belge.durum.value,
                "toplam_maliyet": belge.toplam_maliyet,
                "kar_orani": belge.kar_orani,
                "kdv_orani": belge.kdv_orani,
            },
            "urunler": urunler,
            "alt_kalemler": alt_kalemler,
            "maliyet_snapshots": maliyet_snapshots,
            "hesaplama": self.maliyet_hesapla(
                belge.toplam_maliyet, belge.kar_orani, belge.kdv_orani
            ),
        }

    def _urunleri_kopyala(self, kaynak_belge_id: str,
                           hedef_belge_id: str) -> None:
        """Kaynak belgeden hedef belgeye ürünleri kopyalar."""
        urunler = self.belge_repo.belge_urunlerini_getir(kaynak_belge_id)
        for urun in urunler:
            yeni_id = self.belge_repo.belge_urunu_ekle(
                hedef_belge_id, urun["urun_id"],
                urun["miktar"], urun["alan_verileri"]
            )
            # Alt kalemleri de kopyala
            alt_kalemler = self.belge_repo.belge_alt_kalemlerini_getir(
                kaynak_belge_id, urun["id"])
            for ak in alt_kalemler:
                self.belge_repo.belge_alt_kalemi_ekle(
                    hedef_belge_id, yeni_id, ak["alt_kalem_id"],
                    ak["miktar"], ak["birim_fiyat"], bool(ak["dahil"])
                )

    def _proje_kapat_otomatik(self, proje_id: str) -> None:
        """APPROVED belge olduğunda projeyi otomatik kapatır."""
        proje = self.proje_repo.id_ile_getir(proje_id)
        if proje and proje.durum == ProjeDurumu.ACTIVE:
            proje.durum = ProjeDurumu.CLOSED
            self.proje_repo.guncelle(proje)
            self._log_kaydet(
                IslemTipi.PROJE_KAPAT, "projeler", proje_id,
                "Proje otomatik kapatıldı (belge onaylandı)"
            )
            logger.info(f"Proje otomatik kapatıldı: {proje.hash_kodu}")

    def _log_kaydet(self, islem: IslemTipi, hedef_tablo: str,
                    hedef_id: str, detay: str) -> None:
        try:
            state = app_state()
            log = HareketLogu(
                kullanici_id=state.aktif_kullanici.id if state.aktif_kullanici else "",
                islem=islem,
                hedef_tablo=hedef_tablo,
                hedef_id=hedef_id,
                detay=detay,
            )
            self.log_repo.kaydet(log)
        except Exception as e:
            logger.error(f"Log kaydı hatası: {e}")
