#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ProjeUrun Repository — Proje-ürün bağlantı CRUD, sıralama, snapshot."""

import json
from uygulama.altyapi.veritabani import Veritabani
from uygulama.domain.modeller import _yeni_uuid
from uygulama.ortak.yardimcilar import logger_olustur, simdi_iso

logger = logger_olustur("proje_urun_repo")


class ProjeUrunRepository:
    def __init__(self, db: Veritabani):
        self.db = db

    # ═════════════════════════════════════════
    # SORGULAMA
    # ═════════════════════════════════════════

    def proje_urunleri_getir(self, proje_id: str) -> list[dict]:
        """Projenin ürünlerini sıralı getirir (ürün detayları dahil)."""
        rows = self.db.getir_hepsi(
            """SELECT pu.id, pu.proje_id, pu.urun_id, pu.sira,
                      pu.urun_snapshot,
                      u.kod, u.ad, u.aktif as urun_aktif
               FROM proje_urunleri pu
               JOIN urunler u ON u.id = pu.urun_id
               WHERE pu.proje_id = ? AND pu.silinme_tarihi IS NULL
               ORDER BY pu.sira ASC""", (proje_id,))
        return [dict(r) for r in rows]

    def urun_zaten_ekli_mi(self, proje_id: str, urun_id: str) -> bool:
        """Duplicate kontrol."""
        row = self.db.getir_tek(
            """SELECT COUNT(*) as c FROM proje_urunleri
               WHERE proje_id = ? AND urun_id = ?
               AND silinme_tarihi IS NULL""",
            (proje_id, urun_id))
        return (row["c"] > 0) if row else False

    def max_sira(self, proje_id: str) -> int:
        """Projedeki en yüksek sıra numarasını döndürür."""
        row = self.db.getir_tek(
            """SELECT COALESCE(MAX(sira), 0) as m FROM proje_urunleri
               WHERE proje_id = ? AND silinme_tarihi IS NULL""",
            (proje_id,))
        return row["m"] if row else 0

    def getir(self, proje_urun_id: str) -> dict | None:
        row = self.db.getir_tek(
            """SELECT pu.*, u.kod, u.ad
               FROM proje_urunleri pu
               JOIN urunler u ON u.id = pu.urun_id
               WHERE pu.id = ?""", (proje_urun_id,))
        return dict(row) if row else None

    # ═════════════════════════════════════════
    # EKLEME
    # ═════════════════════════════════════════

    def urun_ekle(self, proje_id: str, urun_id: str, sira: int,
                   snapshot: dict = None) -> str:
        """Projeye ürün ekler. Returns: proje_urun_id."""
        pu_id = _yeni_uuid()
        snap_json = json.dumps(snapshot or {}, ensure_ascii=False)
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO proje_urunleri
                   (id, proje_id, urun_id, sira, urun_snapshot)
                   VALUES (?, ?, ?, ?, ?)""",
                (pu_id, proje_id, urun_id, sira, snap_json))
        logger.info(f"Proje ürün eklendi: proje={proje_id[:8]}, "
                    f"urun={urun_id[:8]}, sira={sira}")
        return pu_id

    # ═════════════════════════════════════════
    # SİLME
    # ═════════════════════════════════════════

    def urun_sil(self, proje_urun_id: str) -> None:
        """Soft delete."""
        with self.db.transaction() as conn:
            conn.execute(
                """UPDATE proje_urunleri SET silinme_tarihi = ?
                   WHERE id = ?""", (simdi_iso(), proje_urun_id))
        logger.info(f"Proje ürün silindi: {proje_urun_id[:8]}")

    # ═════════════════════════════════════════
    # SIRALAMA
    # ═════════════════════════════════════════

    def sira_guncelle(self, proje_urun_id: str, yeni_sira: int) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE proje_urunleri SET sira = ? WHERE id = ?",
                (yeni_sira, proje_urun_id))

    def toplu_sira_guncelle(self, sira_listesi: list[tuple[str, int]]) -> None:
        """Toplu sıra güncelleme. [(proje_urun_id, yeni_sira), ...]"""
        with self.db.transaction() as conn:
            for pu_id, sira in sira_listesi:
                conn.execute(
                    "UPDATE proje_urunleri SET sira = ? WHERE id = ?",
                    (sira, pu_id))

    def siralari_yeniden_indexle(self, proje_id: str) -> None:
        """Silme sonrası sıraları 1'den başlayarak yeniden düzenler."""
        urunler = self.proje_urunleri_getir(proje_id)
        with self.db.transaction() as conn:
            for i, u in enumerate(urunler, 1):
                conn.execute(
                    "UPDATE proje_urunleri SET sira = ? WHERE id = ?",
                    (i, u["id"]))

    # ═════════════════════════════════════════
    # SNAPSHOT
    # ═════════════════════════════════════════

    def snapshot_olustur(self, proje_id: str) -> list[dict]:
        """Projenin ürünlerini snapshot formatında döndürür."""
        urunler = self.proje_urunleri_getir(proje_id)
        return [{
            "urun_id": u["urun_id"],
            "kod": u["kod"],
            "ad": u["ad"],
            "sira": u["sira"],
        } for u in urunler]
