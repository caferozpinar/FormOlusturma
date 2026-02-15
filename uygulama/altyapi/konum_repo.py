#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Konum Repository — Ülke ve Şehir CRUD."""

from uygulama.altyapi.veritabani import Veritabani
from uygulama.domain.modeller import _yeni_uuid
from uygulama.ortak.yardimcilar import logger_olustur, simdi_iso

logger = logger_olustur("konum_repo")

# Türkçe normalize
_TR_MAP = str.maketrans("ÇĞİÖŞÜçğıöşü", "CGIOSUcgiosu")


def _normalize(s: str) -> str:
    return s.translate(_TR_MAP).lower().strip()


class KonumRepository:
    def __init__(self, db: Veritabani):
        self.db = db

    # ── ÜLKELER ──

    def aktif_ulkeleri_getir(self) -> list[dict]:
        rows = self.db.getir_hepsi(
            "SELECT * FROM ulkeler WHERE aktif=1 AND silindi=0 ORDER BY ad")
        return [dict(r) for r in rows]

    def tum_ulkeleri_getir(self) -> list[dict]:
        rows = self.db.getir_hepsi(
            "SELECT * FROM ulkeler WHERE silindi=0 ORDER BY ad")
        return [dict(r) for r in rows]

    def ulke_getir(self, ulke_id: str) -> dict | None:
        row = self.db.getir_tek("SELECT * FROM ulkeler WHERE id=?", (ulke_id,))
        return dict(row) if row else None

    def ulke_ekle(self, ad: str) -> str:
        uid = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT INTO ulkeler (id, ad, olusturma_tarihi) VALUES (?,?,?)",
                (uid, ad.strip(), simdi_iso()))
        logger.info(f"Ülke eklendi: {ad}")
        return uid

    def ulke_guncelle(self, ulke_id: str, ad: str = None,
                       aktif: int = None) -> None:
        parts, params = [], []
        if ad is not None:
            parts.append("ad=?"); params.append(ad.strip())
        if aktif is not None:
            parts.append("aktif=?"); params.append(aktif)
        if not parts:
            return
        params.append(ulke_id)
        with self.db.transaction() as conn:
            conn.execute(
                f"UPDATE ulkeler SET {','.join(parts)} WHERE id=?", tuple(params))

    def ulke_sil(self, ulke_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute("UPDATE ulkeler SET silindi=1 WHERE id=?", (ulke_id,))
            conn.execute("UPDATE sehirler SET silindi=1 WHERE ulke_id=?", (ulke_id,))

    def ulke_ara(self, arama: str) -> list[dict]:
        """Normalize Türkçe arama — Python tarafında filtre."""
        norm = _normalize(arama)
        tum = self.db.getir_hepsi(
            "SELECT * FROM ulkeler WHERE silindi=0 ORDER BY ad")
        return [dict(r) for r in tum if norm in _normalize(r["ad"])]

    # ── ŞEHİRLER ──

    def aktif_sehirleri_getir(self, ulke_id: str) -> list[dict]:
        rows = self.db.getir_hepsi(
            """SELECT * FROM sehirler
               WHERE ulke_id=? AND aktif=1 AND silindi=0
               ORDER BY ad""", (ulke_id,))
        return [dict(r) for r in rows]

    def tum_sehirleri_getir(self, ulke_id: str) -> list[dict]:
        rows = self.db.getir_hepsi(
            """SELECT * FROM sehirler
               WHERE ulke_id=? AND silindi=0 ORDER BY ad""", (ulke_id,))
        return [dict(r) for r in rows]

    def sehir_getir(self, sehir_id: str) -> dict | None:
        row = self.db.getir_tek("SELECT * FROM sehirler WHERE id=?", (sehir_id,))
        return dict(row) if row else None

    def sehir_ekle(self, ulke_id: str, ad: str) -> str:
        sid = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO sehirler (id, ulke_id, ad, olusturma_tarihi)
                   VALUES (?,?,?,?)""",
                (sid, ulke_id, ad.strip(), simdi_iso()))
        logger.info(f"Şehir eklendi: {ad}")
        return sid

    def sehir_guncelle(self, sehir_id: str, ad: str = None,
                        aktif: int = None) -> None:
        parts, params = [], []
        if ad is not None:
            parts.append("ad=?"); params.append(ad.strip())
        if aktif is not None:
            parts.append("aktif=?"); params.append(aktif)
        if not parts:
            return
        params.append(sehir_id)
        with self.db.transaction() as conn:
            conn.execute(
                f"UPDATE sehirler SET {','.join(parts)} WHERE id=?", tuple(params))

    def sehir_sil(self, sehir_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute("UPDATE sehirler SET silindi=1 WHERE id=?", (sehir_id,))

    def sehir_ara(self, arama: str, ulke_id: str = None) -> list[dict]:
        norm = _normalize(arama)
        if ulke_id:
            tum = self.db.getir_hepsi(
                "SELECT * FROM sehirler WHERE silindi=0 AND ulke_id=? ORDER BY ad",
                (ulke_id,))
        else:
            tum = self.db.getir_hepsi(
                """SELECT s.*, u.ad as ulke_adi FROM sehirler s
                   JOIN ulkeler u ON u.id = s.ulke_id
                   WHERE s.silindi=0 ORDER BY s.ad""")
        return [dict(r) for r in tum if norm in _normalize(r["ad"])]
