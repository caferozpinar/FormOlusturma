#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Global Uygulama Durumu — Tüm katmanlar arası paylaşılan state.
Singleton pattern ile tek instance garanti edilir.
"""

from typing import Optional
from uygulama.domain.modeller import Kullanici


class AppState:
    """Uygulama genelinde paylaşılan durum bilgisi."""

    _instance: Optional["AppState"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.aktif_kullanici: Optional[Kullanici] = None
        self.db_yolu: str = ""
        self.uygulama_surumu: str = "1.0.0"
        self.sync_durumu: str = "idle"  # idle, syncing, error
        self.son_sync_tarihi: Optional[str] = None

    @property
    def giris_yapildi(self) -> bool:
        return self.aktif_kullanici is not None

    @property
    def admin_mi(self) -> bool:
        if self.aktif_kullanici is None:
            return False
        from uygulama.domain.modeller import KullaniciRolu
        return self.aktif_kullanici.rol == KullaniciRolu.ADMIN

    def cikis_yap(self):
        self.aktif_kullanici = None

    @classmethod
    def sifirla(cls):
        """Test amaçlı — singleton'ı sıfırlar."""
        cls._instance = None


def app_state() -> AppState:
    """Global state erişim fonksiyonu."""
    return AppState()
