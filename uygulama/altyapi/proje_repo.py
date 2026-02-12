#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proje Repository — Veritabanı erişim katmanı.
"""

import sqlite3
from typing import Optional

from uygulama.altyapi.veritabani import Veritabani
from uygulama.domain.modeller import Proje, ProjeDurumu
from uygulama.ortak.yardimcilar import logger_olustur, simdi_iso

logger = logger_olustur("proje_repo")


class ProjeRepository:
    """Proje veritabanı işlemleri."""

    def __init__(self, db: Veritabani):
        self.db = db

    @staticmethod
    def _row_to_model(row: sqlite3.Row) -> Proje:
        return Proje(
            id=row["id"],
            firma=row["firma"],
            konum=row["konum"],
            tesis=row["tesis"],
            urun_seti=row["urun_seti"],
            hash_kodu=row["hash_kodu"],
            durum=ProjeDurumu(row["durum"]),
            olusturan_id=row["olusturan_id"],
            olusturma_tarihi=row["olusturma_tarihi"],
            guncelleme_tarihi=row["guncelleme_tarihi"],
            silinme_tarihi=row["silinme_tarihi"],
        )

    def id_ile_getir(self, proje_id: str) -> Optional[Proje]:
        row = self.db.getir_tek(
            """SELECT * FROM projeler
               WHERE id = ? AND silinme_tarihi IS NULL""",
            (proje_id,)
        )
        return self._row_to_model(row) if row else None

    def hash_ile_getir(self, hash_kodu: str) -> Optional[Proje]:
        row = self.db.getir_tek(
            """SELECT * FROM projeler
               WHERE hash_kodu = ? AND silinme_tarihi IS NULL""",
            (hash_kodu,)
        )
        return self._row_to_model(row) if row else None

    def listele(self, durum: Optional[ProjeDurumu] = None,
                arama: str = "",
                baslangic_tarihi: str = "",
                bitis_tarihi: str = "") -> list[Proje]:
        """Projeleri filtreli listeler."""
        sql = """SELECT p.*, k.kullanici_adi as son_kullanici
                 FROM projeler p
                 LEFT JOIN kullanicilar k ON k.id = p.olusturan_id
                 WHERE p.silinme_tarihi IS NULL"""
        params = []

        if durum:
            sql += " AND p.durum = ?"
            params.append(durum.value)

        if arama:
            sql += """ AND (p.firma LIKE ? OR p.konum LIKE ?
                       OR p.tesis LIKE ? OR p.hash_kodu LIKE ?)"""
            like = f"%{arama}%"
            params.extend([like, like, like, like])

        if baslangic_tarihi:
            sql += " AND p.olusturma_tarihi >= ?"
            params.append(baslangic_tarihi)

        if bitis_tarihi:
            sql += " AND p.olusturma_tarihi <= ?"
            params.append(bitis_tarihi)

        sql += " ORDER BY p.guncelleme_tarihi DESC"

        rows = self.db.getir_hepsi(sql, tuple(params))
        return [self._row_to_model(r) for r in rows]

    def olustur(self, proje: Proje) -> Proje:
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO projeler
                   (id, firma, konum, tesis, urun_seti, hash_kodu,
                    durum, olusturan_id, olusturma_tarihi, guncelleme_tarihi)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (proje.id, proje.firma, proje.konum, proje.tesis,
                 proje.urun_seti, proje.hash_kodu, proje.durum.value,
                 proje.olusturan_id, proje.olusturma_tarihi,
                 proje.guncelleme_tarihi)
            )
        logger.info(f"Proje oluşturuldu: {proje.firma} [{proje.hash_kodu}]")
        return proje

    def guncelle(self, proje: Proje) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                """UPDATE projeler SET
                   firma = ?, konum = ?, tesis = ?, urun_seti = ?,
                   durum = ?, guncelleme_tarihi = ?
                   WHERE id = ?""",
                (proje.firma, proje.konum, proje.tesis, proje.urun_seti,
                 proje.durum.value, simdi_iso(), proje.id)
            )
        logger.info(f"Proje güncellendi: {proje.firma} [{proje.hash_kodu}]")

    def soft_delete(self, proje_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                """UPDATE projeler SET
                   silinme_tarihi = ?, guncelleme_tarihi = ?
                   WHERE id = ?""",
                (simdi_iso(), simdi_iso(), proje_id)
            )
        logger.info(f"Proje silindi (soft): {proje_id}")

    def hash_mevcut_mu(self, hash_kodu: str, haric_id: str = "") -> bool:
        if haric_id:
            row = self.db.getir_tek(
                """SELECT COUNT(*) as sayi FROM projeler
                   WHERE hash_kodu = ? AND id != ?
                   AND silinme_tarihi IS NULL""",
                (hash_kodu, haric_id)
            )
        else:
            row = self.db.getir_tek(
                """SELECT COUNT(*) as sayi FROM projeler
                   WHERE hash_kodu = ? AND silinme_tarihi IS NULL""",
                (hash_kodu,)
            )
        return row["sayi"] > 0 if row else False

    def istatistikler(self) -> dict:
        """Genel proje istatistiklerini döndürür."""
        rows = self.db.getir_hepsi(
            """SELECT durum, COUNT(*) as sayi FROM projeler
               WHERE silinme_tarihi IS NULL GROUP BY durum"""
        )
        stats = {"toplam": 0, "aktif": 0, "kapali": 0}
        for r in rows:
            sayi = r["sayi"]
            stats["toplam"] += sayi
            if r["durum"] == "ACTIVE":
                stats["aktif"] = sayi
            elif r["durum"] == "CLOSED":
                stats["kapali"] = sayi
        return stats
