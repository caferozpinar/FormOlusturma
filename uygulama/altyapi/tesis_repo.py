#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tesis Repository — Tesis Türü CRUD."""

from uygulama.altyapi.veritabani import Veritabani
from uygulama.domain.modeller import _yeni_uuid
from uygulama.ortak.yardimcilar import logger_olustur, simdi_iso

logger = logger_olustur("tesis_repo")


class TesisRepository:
    def __init__(self, db: Veritabani):
        self.db = db

    def aktif_listele(self) -> list[dict]:
        rows = self.db.getir_hepsi(
            "SELECT * FROM tesis_turleri WHERE aktif=1 AND silindi=0 ORDER BY ad")
        return [dict(r) for r in rows]

    def tum_listele(self) -> list[dict]:
        rows = self.db.getir_hepsi(
            "SELECT * FROM tesis_turleri WHERE silindi=0 ORDER BY ad")
        return [dict(r) for r in rows]

    def getir(self, tesis_id: str) -> dict | None:
        row = self.db.getir_tek(
            "SELECT * FROM tesis_turleri WHERE id=?", (tesis_id,))
        return dict(row) if row else None

    def ekle(self, ad: str) -> str:
        tid = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT INTO tesis_turleri (id, ad, olusturma_tarihi) VALUES (?,?,?)",
                (tid, ad.strip(), simdi_iso()))
        logger.info(f"Tesis türü eklendi: {ad}")
        return tid

    def guncelle(self, tesis_id: str, ad: str = None, aktif: int = None) -> None:
        parts, params = [], []
        if ad is not None:
            parts.append("ad=?"); params.append(ad.strip())
        if aktif is not None:
            parts.append("aktif=?"); params.append(aktif)
        if not parts:
            return
        params.append(tesis_id)
        with self.db.transaction() as conn:
            conn.execute(
                f"UPDATE tesis_turleri SET {','.join(parts)} WHERE id=?",
                tuple(params))

    def sil(self, tesis_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE tesis_turleri SET silindi=1 WHERE id=?", (tesis_id,))
