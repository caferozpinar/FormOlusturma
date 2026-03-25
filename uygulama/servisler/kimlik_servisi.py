#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kimlik Servisi — Giriş, çıkış, şifre yönetimi, kullanıcı CRUD.
İş kuralları bu katmandadır; veritabanı erişimi repository üzerinden yapılır.
"""

import sqlite3
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
        except Exception as e:
            logger.warning(f"Şifre doğrulama hatası: {type(e).__name__} - {e}")
            return False

    # ─────────────────────────────────────────
    # GİRİŞ / ÇIKIŞ
    # ─────────────────────────────────────────

    def giris_yap(self, email: str, sifre: str) -> Tuple[bool, str]:
        """
        Giriş işlemi (e-posta + şifre).
        Returns: (başarılı_mı, mesaj)
        """
        if not email or not sifre:
            return False, "E-posta ve şifre gereklidir."

        kullanici = self.kullanici_repo.email_ile_getir(email)

        if kullanici is None:
            logger.warning(f"Başarısız giriş denemesi: {email} (bulunamadı)")
            return False, "E-posta veya şifre hatalı."

        if not kullanici.aktif:
            logger.warning(f"Deaktif kullanıcı giriş denemesi: {email}")
            return False, "Bu hesap devre dışı bırakılmış."

        if not self.sifre_dogrula(sifre, kullanici.sifre_hash):
            self._log_kaydet(
                kullanici.id, IslemTipi.GIRIS_BASARISIZ,
                "kullanicilar", kullanici.id,
                f"Başarısız giriş: {email}"
            )
            logger.warning(f"Başarısız giriş: {email} (yanlış şifre)")
            return False, "E-posta veya şifre hatalı."

        # Başarılı giriş
        state = app_state()
        state.aktif_kullanici = kullanici

        self._log_kaydet(
            kullanici.id, IslemTipi.GIRIS_BASARILI,
            "kullanicilar", kullanici.id,
            f"Giriş yapıldı: {email}"
        )

        logger.info(f"Giriş başarılı: {email} ({kullanici.rol.value})")
        return True, f"Hoş geldiniz, {kullanici.tam_ad}!"

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
                          rol: KullaniciRolu = KullaniciRolu.EDITOR,
                          ad: str = "", soyad: str = "",
                          email: str = ""
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

        if email and "@" not in email:
            return False, "Geçerli bir e-posta adresi girin.", None

        if self.kullanici_repo.kullanici_adi_mevcut_mu(kullanici_adi):
            return False, "Bu kullanıcı adı zaten kullanılıyor.", None

        if email and self.kullanici_repo.email_ile_getir(email):
            return False, "Bu e-posta adresi zaten kullanılıyor.", None

        # Oluştur
        kullanici = Kullanici(
            kullanici_adi=kullanici_adi,
            sifre_hash=self.sifre_hashle(sifre),
            rol=rol,
            ad=ad,
            soyad=soyad,
            email=email,
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

    def kullanici_listele(self, aktif_sadece: bool = False) -> list[Kullanici]:
        """Admin paneli için tüm kullanıcıları listeler."""
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
            # Mevcut admin'in emaili boşsa güncelle
            if not mevcut.email:
                mevcut.email = "admin@localhost"
                self.kullanici_repo.guncelle(mevcut)
            return

        basarili, mesaj, _ = self.kullanici_olustur(
            kullanici_adi="admin",
            sifre="admin123",
            rol=KullaniciRolu.ADMIN,
            ad="Admin",
            email="admin@localhost",
        )
        if basarili:
            logger.info("Varsayılan admin kullanıcısı oluşturuldu. "
                        "(admin@localhost / admin123)")

    def kullanici_bilgi_guncelle(self, kullanici_id: str,
                                  ad: str, soyad: str, email: str,
                                  yeni_sifre: str = "") -> Tuple[bool, str]:
        """Kullanıcının ad/soyad/email/şifre bilgilerini günceller."""
        kullanici = self.kullanici_repo.id_ile_getir(kullanici_id)
        if not kullanici:
            return False, "Kullanıcı bulunamadı."

        if not email or "@" not in email:
            return False, "Geçerli bir e-posta adresi girin."

        mevcut_email = self.kullanici_repo.email_ile_getir(email)
        if mevcut_email and mevcut_email.id != kullanici_id:
            return False, "Bu e-posta adresi başka bir kullanıcıda zaten kullanılıyor."

        kullanici.ad = ad
        kullanici.soyad = soyad
        kullanici.email = email
        kullanici.kullanici_adi = email

        if yeni_sifre:
            if len(yeni_sifre) < 6:
                return False, "Şifre en az 6 karakter olmalıdır."
            kullanici.sifre_hash = self.sifre_hashle(yeni_sifre)

        self.kullanici_repo.guncelle(kullanici)

        state = app_state()
        if state.aktif_kullanici:
            self._log_kaydet(
                state.aktif_kullanici.id, IslemTipi.KULLANICI_GUNCELLE,
                "kullanicilar", kullanici_id,
                f"Kullanıcı bilgileri güncellendi: {email}"
            )

        logger.info(f"Kullanıcı bilgileri güncellendi: {email}")
        return True, "Kullanıcı bilgileri güncellendi."

    def varsayilan_kullanici_olustur(self) -> None:
        """Standart varsayılan kullanıcı oluşturur (Viewer rolü)."""
        email = "kullanıcı@kullanıcı"
        mevcut = self.kullanici_repo.email_ile_getir(email)
        if mevcut:
            return

        basarili, _, _ = self.kullanici_olustur(
            kullanici_adi=email,
            sifre="kullanıcı",
            rol=KullaniciRolu.VIEWER,
            ad="Kullanıcı",
            email=email,
        )
        if basarili:
            logger.info("Varsayılan kullanıcı oluşturuldu. "
                        "(kullanıcı@kullanıcı / kullanıcı)")

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
        except sqlite3.DatabaseError as db_err:
            logger.error(f"Log kaydı veritabanı hatası:\nHata: {type(db_err).__name__} - {db_err}\nDetay: {detay}")
        except Exception as e:
            logger.error(f"Log kaydı hatası: {type(e).__name__}\nHata: {e}\nDetay: {detay}")

    def tum_kullanicilar(self) -> list:
        """Tüm kullanıcıları listeler (soft delete hariç)."""
        return self.kullanici_repo.tumu()
