#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Oturum Yöneticisi — "Beni Hatırla" kalıcı oturum desteği.

Kullanıcı adı ve şifre, makineye özgü bir anahtar ile XOR şifrelenerek
veri/.session dosyasına kaydedilir. Çıkış yapıldığında dosya silinir.
"""

import os
import json
import base64
import hashlib
import uuid
from typing import Optional, Tuple


class OturumYoneticisi:
    """Kalıcı oturum kayıt/yükleme/silme işlemleri."""

    @staticmethod
    def _dosya_yolu() -> str:
        """Oturum dosyasının yolunu döndürür."""
        from uygulama.ortak.app_state import app_state
        db_yolu = app_state().db_yolu
        if db_yolu:
            veri_dizini = os.path.dirname(db_yolu)
        else:
            veri_dizini = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(
                    os.path.abspath(__file__)))),
                "veri"
            )
        return os.path.join(veri_dizini, ".session")

    @staticmethod
    def _anahtar() -> bytes:
        """Makineye özgü şifreleme anahtarı türetir."""
        mac = str(uuid.getnode())
        try:
            hostname = os.uname().nodename
        except AttributeError:
            hostname = "local"
        raw = f"pys-session-{mac}-{hostname}".encode("utf-8")
        return hashlib.sha256(raw).digest()

    @classmethod
    def _sifrele(cls, metin: str) -> str:
        anahtar = cls._anahtar()
        encoded = metin.encode("utf-8")
        xored = bytes(b ^ anahtar[i % len(anahtar)] for i, b in enumerate(encoded))
        return base64.b64encode(xored).decode("ascii")

    @classmethod
    def _coz(cls, sifrelenmis: str) -> str:
        anahtar = cls._anahtar()
        xored = base64.b64decode(sifrelenmis.encode("ascii"))
        return bytes(b ^ anahtar[i % len(anahtar)] for i, b in enumerate(xored)).decode("utf-8")

    @classmethod
    def kaydet(cls, kullanici_adi: str, sifre: str) -> None:
        """Oturumu şifreli olarak diske yazar."""
        try:
            veri = {
                "k": cls._sifrele(kullanici_adi),
                "s": cls._sifrele(sifre),
            }
            with open(cls._dosya_yolu(), "w", encoding="utf-8") as f:
                json.dump(veri, f)
        except Exception:
            pass

    @classmethod
    def yukle(cls) -> Optional[Tuple[str, str]]:
        """
        Kayıtlı oturumu yükler.
        Returns: (kullanici_adi, sifre) veya None
        """
        try:
            dosya = cls._dosya_yolu()
            if not os.path.exists(dosya):
                return None
            with open(dosya, "r", encoding="utf-8") as f:
                veri = json.load(f)
            kullanici_adi = cls._coz(veri["k"])
            sifre = cls._coz(veri["s"])
            return kullanici_adi, sifre
        except Exception:
            return None

    @classmethod
    def sil(cls) -> None:
        """Kayıtlı oturumu siler."""
        try:
            dosya = cls._dosya_yolu()
            if os.path.exists(dosya):
                os.remove(dosya)
        except Exception:
            pass

    @classmethod
    def mevcut_mu(cls) -> bool:
        """Kayıtlı oturum var mı?"""
        try:
            return os.path.exists(cls._dosya_yolu())
        except Exception:
            return False
