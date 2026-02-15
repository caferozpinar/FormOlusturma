#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Yetki Servisi — Merkezi rol bazlı yetkilendirme.

İzin matrisi ile tüm işlemlerin rol kontrolü tek noktadan yapılır.
Yetki reddi durumunda audit log kaydı oluşturulur.
"""

from typing import Tuple
from uygulama.domain.modeller import KullaniciRolu, IslemTipi, HareketLogu
from uygulama.altyapi.log_repo import LogRepository
from uygulama.ortak.app_state import app_state
from uygulama.ortak.yardimcilar import logger_olustur

logger = logger_olustur("yetki_servisi")

# ═════════════════════════════════════════════
# İZİN MATRİSİ
# ═════════════════════════════════════════════
# Her işlem için hangi roller izinli
# True = izinli, False/yok = izinsiz

IZIN_MATRISI: dict[str, set[KullaniciRolu]] = {
    # Proje
    "proje_olustur":    {KullaniciRolu.ADMIN, KullaniciRolu.EDITOR},
    "proje_guncelle":   {KullaniciRolu.ADMIN, KullaniciRolu.EDITOR},
    "proje_kapat":      {KullaniciRolu.ADMIN, KullaniciRolu.EDITOR},
    "proje_aktifle":    {KullaniciRolu.ADMIN},
    "proje_sil":        {KullaniciRolu.ADMIN, KullaniciRolu.EDITOR},
    "proje_goruntule":  {KullaniciRolu.ADMIN, KullaniciRolu.EDITOR, KullaniciRolu.VIEWER},

    # Belge
    "belge_olustur":    {KullaniciRolu.ADMIN, KullaniciRolu.EDITOR},
    "belge_guncelle":   {KullaniciRolu.ADMIN, KullaniciRolu.EDITOR},
    "belge_gonder":     {KullaniciRolu.ADMIN, KullaniciRolu.EDITOR},
    "belge_onayla":     {KullaniciRolu.ADMIN},
    "belge_reddet":     {KullaniciRolu.ADMIN},
    "belge_sil":        {KullaniciRolu.ADMIN, KullaniciRolu.EDITOR},
    "belge_goruntule":  {KullaniciRolu.ADMIN, KullaniciRolu.EDITOR, KullaniciRolu.VIEWER},
    "revizyon_ac":      {KullaniciRolu.ADMIN, KullaniciRolu.EDITOR},

    # Ürün yönetimi (sadece admin)
    "urun_olustur":     {KullaniciRolu.ADMIN},
    "urun_guncelle":    {KullaniciRolu.ADMIN},
    "urun_sil":         {KullaniciRolu.ADMIN},
    "urun_goruntule":   {KullaniciRolu.ADMIN, KullaniciRolu.EDITOR, KullaniciRolu.VIEWER},
    "alan_yonetimi":    {KullaniciRolu.ADMIN},
    "alt_kalem_yonetimi": {KullaniciRolu.ADMIN},

    # Kullanıcı yönetimi
    "kullanici_olustur":  {KullaniciRolu.ADMIN},
    "kullanici_guncelle": {KullaniciRolu.ADMIN},
    "kullanici_sil":      {KullaniciRolu.ADMIN},
    "kullanici_rol_degistir": {KullaniciRolu.ADMIN},

    # Maliyet
    "maliyet_versiyon":   {KullaniciRolu.ADMIN},
    "maliyet_hesapla":    {KullaniciRolu.ADMIN, KullaniciRolu.EDITOR},

    # Sync
    "sync_baslat":      {KullaniciRolu.ADMIN, KullaniciRolu.EDITOR},
    "sync_goruntule":   {KullaniciRolu.ADMIN, KullaniciRolu.EDITOR, KullaniciRolu.VIEWER},

    # Admin panel
    "admin_panel":      {KullaniciRolu.ADMIN},

    # Log
    "log_goruntule":    {KullaniciRolu.ADMIN},
    "log_aktar":        {KullaniciRolu.ADMIN},
}


class YetkiServisi:
    """Merkezi rol bazlı yetkilendirme servisi."""

    def __init__(self, log_repo: LogRepository):
        self.log_repo = log_repo

    def kontrol(self, islem: str) -> Tuple[bool, str]:
        """
        İşlem yetkisini kontrol eder.
        Returns: (izinli_mi, mesaj)
        """
        state = app_state()

        if not state.giris_yapildi:
            return False, "Giriş yapılmamış."

        kullanici = state.aktif_kullanici
        rol = kullanici.rol

        izinli_roller = IZIN_MATRISI.get(islem)
        if izinli_roller is None:
            # Tanımsız işlem — varsayılan olarak sadece admin
            logger.warning(f"Tanımsız yetki işlemi: {islem}")
            izinli_roller = {KullaniciRolu.ADMIN}

        if rol in izinli_roller:
            return True, "İzinli."

        # Yetki reddedildi — log kaydet
        mesaj = (f"Yetki reddedildi: {kullanici.kullanici_adi} "
                 f"({rol.value}) → {islem}")
        logger.warning(mesaj)

        try:
            log = HareketLogu(
                kullanici_id=kullanici.id,
                islem=IslemTipi.YETKI_REDDEDILDI,
                hedef_tablo="yetki",
                hedef_id=islem,
                detay=mesaj)
            self.log_repo.kaydet(log)
        except Exception as e:
            logger.error(f"Yetki red logu yazılamadı: {e}")

        return False, f"Bu işlem için yetkiniz yok ({rol.value})."

    def admin_mi(self) -> bool:
        return app_state().admin_mi

    def editor_mi(self) -> bool:
        state = app_state()
        if not state.aktif_kullanici:
            return False
        return state.aktif_kullanici.rol in (
            KullaniciRolu.ADMIN, KullaniciRolu.EDITOR)

    def viewer_mi(self) -> bool:
        return app_state().giris_yapildi

    def aktif_rol(self) -> str:
        state = app_state()
        if state.aktif_kullanici:
            return state.aktif_kullanici.rol.value
        return "—"

    def izin_matrisi_ozet(self) -> dict[str, list[str]]:
        """İzin matrisini okunabilir formatta döndürür."""
        return {islem: [r.value for r in roller]
                for islem, roller in sorted(IZIN_MATRISI.items())}
