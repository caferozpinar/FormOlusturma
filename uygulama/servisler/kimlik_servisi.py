#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kimlik Servisi — Giriş, çıkış, şifre yönetimi, kullanıcı CRUD.
İş kuralları bu katmandadır; veritabanı erişimi repository üzerinden yapılır.
"""

import bcrypt
from typing import Optional, Tuple

from uygulama.domain.modeller import (
    Kullanici, KullaniciRolu, HareketLogu, IslemTipi
)
from uygulama.altyapi.kullanici_repo import KullaniciRepository
from uygulama.altyapi.log_repo import LogRepository
from uygulama.ortak.app_state import app_state
from uygulama.ortak.yardimcilar import logger_olustur, simdi_iso

logger = logger_olustur("kimlik_servisi")


class KimlikServisi:
    """Kimlik doğrulama ve kullanıcı yönetim servisi."""

    def __init__(self, kullanici_repo: KullaniciRepository,
                 log_repo: LogRepository):
        self.kullanici_repo = kullanici_repo
        self.log_repo = log_repo

    # ─────────────────────────────────────────
    # ŞİFRE İŞLEMLERİ
    # ─────────────────────────────────────────

    @staticmethod
    def sifre_hashle(sifre: str) -> str:
        """Şifreyi bcrypt ile hashler."""
        tuz = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(sifre.encode("utf-8"), tuz).decode("utf-8")

    @staticmethod
    def sifre_dogrula(sifre: str, hash_deger: str) -> bool:
        """Şifreyi hash ile karşılaştırır."""
        try:
            return bcrypt.checkpw(
                sifre.encode("utf-8"),
                hash_deger.encode("utf-8")
            )
        except Exception:
            return False

    # ─────────────────────────────────────────
    # GİRİŞ / ÇIKIŞ
    # ─────────────────────────────────────────

    def giris_yap(self, kullanici_adi: str, sifre: str) -> Tuple[bool, str]:
        """
        Giriş işlemi.
        Returns: (başarılı_mı, mesaj)
        """
        if not kullanici_adi or not sifre:
            return False, "Kullanıcı adı ve şifre gereklidir."

        kullanici = self.kullanici_repo.adi_ile_getir(kullanici_adi)

        if kullanici is None:
            logger.warning(f"Başarısız giriş denemesi: {kullanici_adi} (bulunamadı)")
            return False, "Kullanıcı adı veya şifre hatalı."

        if not kullanici.aktif:
            logger.warning(f"Deaktif kullanıcı giriş denemesi: {kullanici_adi}")
            return False, "Bu hesap devre dışı bırakılmış."

        if not self.sifre_dogrula(sifre, kullanici.sifre_hash):
            # Başarısız giriş logu
            self._log_kaydet(
                kullanici.id, IslemTipi.GIRIS_BASARISIZ,
                "kullanicilar", kullanici.id,
                f"Başarısız giriş: {kullanici_adi}"
            )
            logger.warning(f"Başarısız giriş: {kullanici_adi} (yanlış şifre)")
            return False, "Kullanıcı adı veya şifre hatalı."

        # Başarılı giriş
        state = app_state()
        state.aktif_kullanici = kullanici

        self._log_kaydet(
            kullanici.id, IslemTipi.GIRIS_BASARILI,
            "kullanicilar", kullanici.id,
            f"Giriş yapıldı: {kullanici_adi}"
        )

        logger.info(f"Giriş başarılı: {kullanici_adi} ({kullanici.rol.value})")
        return True, f"Hoş geldiniz, {kullanici_adi}!"

    def cikis_yap(self) -> None:
        """Çıkış işlemi."""
        state = app_state()
        if state.aktif_kullanici:
            logger.info(f"Çıkış: {state.aktif_kullanici.kullanici_adi}")
        state.cikis_yap()

    # ─────────────────────────────────────────
    # KULLANICI CRUD
    # ─────────────────────────────────────────

    def kullanici_olustur(self, kullanici_adi: str, sifre: str,
                          rol: KullaniciRolu = KullaniciRolu.EDITOR
                          ) -> Tuple[bool, str, Optional[Kullanici]]:
        """
        Yeni kullanıcı oluşturur.
        Returns: (başarılı_mı, mesaj, kullanıcı)
        """
        # Validasyon
        if not kullanici_adi or len(kullanici_adi) < 3:
            return False, "Kullanıcı adı en az 3 karakter olmalıdır.", None

        if not sifre or len(sifre) < 6:
            return False, "Şifre en az 6 karakter olmalıdır.", None

        if self.kullanici_repo.kullanici_adi_mevcut_mu(kullanici_adi):
            return False, "Bu kullanıcı adı zaten kullanılıyor.", None

        # Oluştur
        kullanici = Kullanici(
            kullanici_adi=kullanici_adi,
            sifre_hash=self.sifre_hashle(sifre),
            rol=rol,
        )
        self.kullanici_repo.olustur(kullanici)

        # Log
        state = app_state()
        olusturan_id = state.aktif_kullanici.id if state.aktif_kullanici else kullanici.id
        self._log_kaydet(
            olusturan_id, IslemTipi.KULLANICI_OLUSTUR,
            "kullanicilar", kullanici.id,
            f"Kullanıcı oluşturuldu: {kullanici_adi} ({rol.value})"
        )

        logger.info(f"Kullanıcı oluşturuldu: {kullanici_adi}")
        return True, "Kullanıcı başarıyla oluşturuldu.", kullanici

    def sifre_degistir(self, kullanici_id: str, yeni_sifre: str) -> Tuple[bool, str]:
        """Kullanıcı şifresini değiştirir."""
        if not yeni_sifre or len(yeni_sifre) < 6:
            return False, "Şifre en az 6 karakter olmalıdır."

        kullanici = self.kullanici_repo.id_ile_getir(kullanici_id)
        if not kullanici:
            return False, "Kullanıcı bulunamadı."

        kullanici.sifre_hash = self.sifre_hashle(yeni_sifre)
        self.kullanici_repo.guncelle(kullanici)

        logger.info(f"Şifre değiştirildi: {kullanici.kullanici_adi}")
        return True, "Şifre başarıyla değiştirildi."

    def kullanici_deaktif_et(self, kullanici_id: str) -> Tuple[bool, str]:
        """Kullanıcıyı deaktif eder."""
        kullanici = self.kullanici_repo.id_ile_getir(kullanici_id)
        if not kullanici:
            return False, "Kullanıcı bulunamadı."

        kullanici.aktif = False
        self.kullanici_repo.guncelle(kullanici)

        state = app_state()
        if state.aktif_kullanici:
            self._log_kaydet(
                state.aktif_kullanici.id, IslemTipi.KULLANICI_GUNCELLE,
                "kullanicilar", kullanici_id,
                f"Kullanıcı deaktif edildi: {kullanici.kullanici_adi}"
            )

        logger.info(f"Kullanıcı deaktif: {kullanici.kullanici_adi}")
        return True, "Kullanıcı devre dışı bırakıldı."

    def rol_degistir(self, kullanici_id: str,
                     yeni_rol: KullaniciRolu) -> Tuple[bool, str]:
        """Kullanıcı rolünü değiştirir."""
        kullanici = self.kullanici_repo.id_ile_getir(kullanici_id)
        if not kullanici:
            return False, "Kullanıcı bulunamadı."

        eski_rol = kullanici.rol
        kullanici.rol = yeni_rol
        self.kullanici_repo.guncelle(kullanici)

        state = app_state()
        if state.aktif_kullanici:
            self._log_kaydet(
                state.aktif_kullanici.id, IslemTipi.KULLANICI_GUNCELLE,
                "kullanicilar", kullanici_id,
                f"Rol değişikliği: {eski_rol.value} → {yeni_rol.value}"
            )

        return True, f"Rol güncellendi: {yeni_rol.value}"

    def tum_kullanicilar(self, aktif_sadece: bool = True) -> list[Kullanici]:
        """Tüm kullanıcıları listeler."""
        return self.kullanici_repo.tumu(aktif_sadece)

    # ─────────────────────────────────────────
    # İLK KURULUM
    # ─────────────────────────────────────────

    def varsayilan_admin_olustur(self) -> None:
        """
        Eğer hiç kullanıcı yoksa varsayılan admin oluşturur.
        İlk çalıştırmada çağrılır.
        """
        mevcut = self.kullanici_repo.adi_ile_getir("admin")
        if mevcut:
            return

        basarili, mesaj, _ = self.kullanici_olustur(
            kullanici_adi="admin",
            sifre="admin123",
            rol=KullaniciRolu.ADMIN,
        )
        if basarili:
            logger.info("Varsayılan admin kullanıcısı oluşturuldu. "
                        "(admin / admin123)")

    # ─────────────────────────────────────────
    # YARDIMCI
    # ─────────────────────────────────────────

    def _log_kaydet(self, kullanici_id: str, islem: IslemTipi,
                    hedef_tablo: str, hedef_id: str, detay: str) -> None:
        """Audit log kaydı oluşturur."""
        try:
            log = HareketLogu(
                kullanici_id=kullanici_id,
                islem=islem,
                hedef_tablo=hedef_tablo,
                hedef_id=hedef_id,
                detay=detay,
            )
            self.log_repo.kaydet(log)
        except Exception as e:
            logger.error(f"Log kaydı hatası: {e}")
