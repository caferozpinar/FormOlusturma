#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Konum Servisi — Ülke/Şehir iş kuralları."""

from typing import Tuple, Optional
from uygulama.altyapi.konum_repo import KonumRepository
from uygulama.ortak.app_state import app_state
from uygulama.ortak.yardimcilar import logger_olustur

logger = logger_olustur("konum_servisi")


class KonumServisi:
    def __init__(self, konum_repo: KonumRepository):
        self.repo = konum_repo

    # ── OKUMA (herkes) ──

    def ulke_listesi(self, sadece_aktif: bool = True) -> list[dict]:
        if sadece_aktif:
            return self.repo.aktif_ulkeleri_getir()
        return self.repo.tum_ulkeleri_getir()

    def sehir_listesi(self, ulke_id: str, sadece_aktif: bool = True) -> list[dict]:
        if sadece_aktif:
            return self.repo.aktif_sehirleri_getir(ulke_id)
        return self.repo.tum_sehirleri_getir(ulke_id)

    def ulke_getir(self, ulke_id: str) -> dict | None:
        return self.repo.ulke_getir(ulke_id)

    def sehir_getir(self, sehir_id: str) -> dict | None:
        return self.repo.sehir_getir(sehir_id)

    # ── YAZMA (admin) ──

    def _admin_kontrol(self) -> Tuple[bool, str]:
        state = app_state()
        if not state.giris_yapildi:
            return False, "Giriş yapılmamış."
        if not state.admin_mi:
            return False, "Sadece Admin."
        return True, ""

    def ulke_ekle(self, ad: str) -> Tuple[bool, str, Optional[str]]:
        ok, msg = self._admin_kontrol()
        if not ok: return False, msg, None
        if not ad or not ad.strip():
            return False, "Ülke adı zorunlu.", None
        uid = self.repo.ulke_ekle(ad)
        return True, f"Ülke eklendi: {ad}", uid

    def ulke_guncelle(self, ulke_id: str, **kwargs) -> Tuple[bool, str]:
        ok, msg = self._admin_kontrol()
        if not ok: return False, msg
        self.repo.ulke_guncelle(ulke_id, **kwargs)
        return True, "Ülke güncellendi."

    def ulke_sil(self, ulke_id: str) -> Tuple[bool, str]:
        ok, msg = self._admin_kontrol()
        if not ok: return False, msg
        self.repo.ulke_sil(ulke_id)
        return True, "Ülke silindi."

    def sehir_ekle(self, ulke_id: str, ad: str) -> Tuple[bool, str, Optional[str]]:
        ok, msg = self._admin_kontrol()
        if not ok: return False, msg, None
        if not ad or not ad.strip():
            return False, "Şehir adı zorunlu.", None
        sid = self.repo.sehir_ekle(ulke_id, ad)
        return True, f"Şehir eklendi: {ad}", sid

    def sehir_guncelle(self, sehir_id: str, **kwargs) -> Tuple[bool, str]:
        ok, msg = self._admin_kontrol()
        if not ok: return False, msg
        self.repo.sehir_guncelle(sehir_id, **kwargs)
        return True, "Şehir güncellendi."

    def sehir_sil(self, sehir_id: str) -> Tuple[bool, str]:
        ok, msg = self._admin_kontrol()
        if not ok: return False, msg
        self.repo.sehir_sil(sehir_id)
        return True, "Şehir silindi."

    def ulke_ara(self, arama: str) -> list[dict]:
        return self.repo.ulke_ara(arama)

    def sehir_ara(self, arama: str, ulke_id: str = None) -> list[dict]:
        return self.repo.sehir_ara(arama, ulke_id)
