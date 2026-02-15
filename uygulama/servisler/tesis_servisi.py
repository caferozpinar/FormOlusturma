#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tesis Servisi — Tesis Türü iş kuralları."""

from typing import Tuple, Optional
from uygulama.altyapi.tesis_repo import TesisRepository
from uygulama.ortak.app_state import app_state


class TesisServisi:
    def __init__(self, tesis_repo: TesisRepository):
        self.repo = tesis_repo

    def listele(self, sadece_aktif: bool = True) -> list[dict]:
        return self.repo.aktif_listele() if sadece_aktif else self.repo.tum_listele()

    def getir(self, tesis_id: str) -> dict | None:
        return self.repo.getir(tesis_id)

    def _admin_kontrol(self) -> Tuple[bool, str]:
        state = app_state()
        if not state.giris_yapildi:
            return False, "Giriş yapılmamış."
        if not state.admin_mi:
            return False, "Sadece Admin."
        return True, ""

    def ekle(self, ad: str) -> Tuple[bool, str, Optional[str]]:
        ok, msg = self._admin_kontrol()
        if not ok: return False, msg, None
        if not ad or not ad.strip():
            return False, "Tesis türü adı zorunlu.", None
        tid = self.repo.ekle(ad)
        return True, f"Tesis türü eklendi: {ad}", tid

    def guncelle(self, tesis_id: str, **kwargs) -> Tuple[bool, str]:
        ok, msg = self._admin_kontrol()
        if not ok: return False, msg
        self.repo.guncelle(tesis_id, **kwargs)
        return True, "Güncellendi."

    def sil(self, tesis_id: str) -> Tuple[bool, str]:
        ok, msg = self._admin_kontrol()
        if not ok: return False, msg
        self.repo.sil(tesis_id)
        return True, "Silindi."
