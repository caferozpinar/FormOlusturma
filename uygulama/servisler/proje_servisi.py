#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proje Servisi — Proje iş kuralları.
Hash üretimi, durum yönetimi, CRUD operasyonları.
"""

from typing import Optional, Tuple

from uygulama.domain.modeller import (
    Proje, ProjeDurumu, HareketLogu, IslemTipi, KullaniciRolu
)
from uygulama.altyapi.proje_repo import ProjeRepository
from uygulama.altyapi.log_repo import LogRepository
from uygulama.ortak.app_state import app_state
from uygulama.ortak.yardimcilar import logger_olustur, proje_hash_uret

logger = logger_olustur("proje_servisi")


class ProjeServisi:
    """Proje yönetim servisi."""

    def __init__(self, proje_repo: ProjeRepository, log_repo: LogRepository):
        self.proje_repo = proje_repo
        self.log_repo = log_repo

    # ─────────────────────────────────────────
    # OLUŞTURMA
    # ─────────────────────────────────────────

    def olustur(self, firma: str, konum: str, tesis: str,
                urun_seti: str = "") -> Tuple[bool, str, Optional[Proje]]:
        """
        Yeni proje oluşturur.
        Returns: (başarılı_mı, mesaj, proje)
        """
        state = app_state()
        if not state.giris_yapildi:
            return False, "Giriş yapılmamış.", None

        # Validasyon
        if not firma or not firma.strip():
            return False, "Firma adı zorunludur.", None
        if not konum or not konum.strip():
            return False, "Konum zorunludur.", None
        if not tesis or not tesis.strip():
            return False, "Tesis adı zorunludur.", None

        firma = firma.strip()
        konum = konum.strip()
        tesis = tesis.strip()
        urun_seti = urun_seti.strip() if urun_seti else ""

        # Benzersiz hash üret
        hash_kodu = self._benzersiz_hash_uret(firma, konum, tesis)

        proje = Proje(
            firma=firma,
            konum=konum,
            tesis=tesis,
            urun_seti=urun_seti,
            hash_kodu=hash_kodu,
            durum=ProjeDurumu.ACTIVE,
            olusturan_id=state.aktif_kullanici.id,
        )

        self.proje_repo.olustur(proje)

        self._log_kaydet(
            IslemTipi.PROJE_OLUSTUR, "projeler", proje.id,
            f"Proje oluşturuldu: {firma} – {konum} – {tesis} [{hash_kodu}]"
        )

        logger.info(f"Proje oluşturuldu: {firma} [{hash_kodu}]")
        return True, f"Proje oluşturuldu. Hash: {hash_kodu}", proje

    # ─────────────────────────────────────────
    # GÜNCELLEME
    # ─────────────────────────────────────────

    def guncelle(self, proje_id: str, firma: str = None, konum: str = None,
                 tesis: str = None, urun_seti: str = None) -> Tuple[bool, str]:
        """Proje bilgilerini günceller."""
        state = app_state()
        if not state.giris_yapildi:
            return False, "Giriş yapılmamış."

        proje = self.proje_repo.id_ile_getir(proje_id)
        if not proje:
            return False, "Proje bulunamadı."

        if proje.durum == ProjeDurumu.CLOSED and not state.admin_mi:
            return False, "Kapalı projeyi sadece Admin düzenleyebilir."

        degisiklikler = []
        if firma is not None and firma.strip():
            proje.firma = firma.strip()
            degisiklikler.append("firma")
        if konum is not None and konum.strip():
            proje.konum = konum.strip()
            degisiklikler.append("konum")
        if tesis is not None and tesis.strip():
            proje.tesis = tesis.strip()
            degisiklikler.append("tesis")
        if urun_seti is not None:
            proje.urun_seti = urun_seti.strip()
            degisiklikler.append("ürün seti")

        if not degisiklikler:
            return False, "Değişiklik yapılmadı."

        self.proje_repo.guncelle(proje)

        self._log_kaydet(
            IslemTipi.PROJE_GUNCELLE, "projeler", proje_id,
            f"Güncellenen alanlar: {', '.join(degisiklikler)}"
        )

        return True, "Proje güncellendi."

    # ─────────────────────────────────────────
    # DURUM YÖNETİMİ
    # ─────────────────────────────────────────

    def kapat(self, proje_id: str) -> Tuple[bool, str]:
        """Projeyi kapatır."""
        state = app_state()
        if not state.giris_yapildi:
            return False, "Giriş yapılmamış."

        proje = self.proje_repo.id_ile_getir(proje_id)
        if not proje:
            return False, "Proje bulunamadı."

        if proje.durum == ProjeDurumu.CLOSED:
            return False, "Proje zaten kapalı."

        proje.durum = ProjeDurumu.CLOSED
        self.proje_repo.guncelle(proje)

        self._log_kaydet(
            IslemTipi.PROJE_KAPAT, "projeler", proje_id,
            f"Proje kapatıldı: {proje.firma} [{proje.hash_kodu}]"
        )

        logger.info(f"Proje kapatıldı: {proje.hash_kodu}")
        return True, "Proje kapatıldı."

    def aktifle(self, proje_id: str) -> Tuple[bool, str]:
        """Kapalı projeyi tekrar aktifler. Sadece Admin."""
        state = app_state()
        if not state.giris_yapildi:
            return False, "Giriş yapılmamış."

        if not state.admin_mi:
            return False, "Bu işlem sadece Admin tarafından yapılabilir."

        proje = self.proje_repo.id_ile_getir(proje_id)
        if not proje:
            return False, "Proje bulunamadı."

        if proje.durum == ProjeDurumu.ACTIVE:
            return False, "Proje zaten aktif."

        proje.durum = ProjeDurumu.ACTIVE
        self.proje_repo.guncelle(proje)

        self._log_kaydet(
            IslemTipi.PROJE_AKTIFLE, "projeler", proje_id,
            f"Proje aktifleştirildi: {proje.firma} [{proje.hash_kodu}]"
        )

        logger.info(f"Proje aktifleştirildi: {proje.hash_kodu}")
        return True, "Proje tekrar aktifleştirildi."

    # ─────────────────────────────────────────
    # SİLME
    # ─────────────────────────────────────────

    def sil(self, proje_id: str) -> Tuple[bool, str]:
        """Projeyi soft delete ile siler."""
        state = app_state()
        if not state.giris_yapildi:
            return False, "Giriş yapılmamış."

        proje = self.proje_repo.id_ile_getir(proje_id)
        if not proje:
            return False, "Proje bulunamadı."

        self.proje_repo.soft_delete(proje_id)

        self._log_kaydet(
            IslemTipi.PROJE_SIL, "projeler", proje_id,
            f"Proje silindi: {proje.firma} [{proje.hash_kodu}]"
        )

        logger.info(f"Proje silindi: {proje.hash_kodu}")
        return True, "Proje silindi."

    # ─────────────────────────────────────────
    # LİSTELEME
    # ─────────────────────────────────────────

    def listele(self, durum: Optional[ProjeDurumu] = None,
                arama: str = "",
                baslangic_tarihi: str = "",
                bitis_tarihi: str = "") -> list[Proje]:
        """Projeleri filtreli listeler."""
        return self.proje_repo.listele(durum, arama,
                                        baslangic_tarihi, bitis_tarihi)

    def getir(self, proje_id: str) -> Optional[Proje]:
        """Tek proje getirir."""
        return self.proje_repo.id_ile_getir(proje_id)

    def hash_ile_getir(self, hash_kodu: str) -> Optional[Proje]:
        """Hash kodu ile proje getirir."""
        return self.proje_repo.hash_ile_getir(hash_kodu)

    def istatistikler(self) -> dict:
        """Proje istatistiklerini döndürür."""
        return self.proje_repo.istatistikler()

    # ─────────────────────────────────────────
    # YARDIMCI
    # ─────────────────────────────────────────

    def _benzersiz_hash_uret(self, firma: str, konum: str, tesis: str) -> str:
        """Benzersiz olana kadar hash üretir."""
        for _ in range(10):
            hash_kodu = proje_hash_uret(firma, konum, tesis)
            if not self.proje_repo.hash_mevcut_mu(hash_kodu):
                return hash_kodu
        # Fallback — çok düşük ihtimal
        import uuid
        return uuid.uuid4().hex[:6]

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
