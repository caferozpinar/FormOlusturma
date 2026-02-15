#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Belge Repository — Veritabanı erişim katmanı.
Belgeler, belge ürünleri, belge alt kalemleri.
"""

import json
import sqlite3
from typing import Optional

from uygulama.altyapi.veritabani import Veritabani
from uygulama.domain.modeller import Belge, BelgeDurumu
from uygulama.ortak.yardimcilar import logger_olustur, simdi_iso

logger = logger_olustur("belge_repo")


class BelgeRepository:
    """Belge veritabanı işlemleri."""

    def __init__(self, db: Veritabani):
        self.db = db

    # ─────────────────────────────────────────
    # ROW → MODEL
    # ─────────────────────────────────────────

    @staticmethod
    def _row_to_model(row: sqlite3.Row) -> Belge:
        return Belge(
            id=row["id"],
            proje_id=row["proje_id"],
            tur=row["tur"],
            revizyon_no=row["revizyon_no"],
            durum=BelgeDurumu(row["durum"]),
            toplam_maliyet=row["toplam_maliyet"],
            kar_orani=row["kar_orani"],
            kdv_orani=row["kdv_orani"],
            olusturan_id=row["olusturan_id"],
            olusturma_tarihi=row["olusturma_tarihi"],
            guncelleme_tarihi=row["guncelleme_tarihi"],
            silinme_tarihi=row["silinme_tarihi"],
            snapshot_veri=row["snapshot_veri"],
        )

    # ─────────────────────────────────────────
    # TEK KAYIT
    # ─────────────────────────────────────────

    def id_ile_getir(self, belge_id: str) -> Optional[Belge]:
        row = self.db.getir_tek(
            """SELECT * FROM belgeler
               WHERE id = ? AND silinme_tarihi IS NULL""",
            (belge_id,)
        )
        return self._row_to_model(row) if row else None

    # ─────────────────────────────────────────
    # LİSTELEME
    # ─────────────────────────────────────────

    def proje_belgeleri(self, proje_id: str) -> list[Belge]:
        """Bir projeye ait tüm aktif belgeleri getirir (son revizyon önce)."""
        rows = self.db.getir_hepsi(
            """SELECT * FROM belgeler
               WHERE proje_id = ? AND silinme_tarihi IS NULL
               ORDER BY tur, revizyon_no DESC""",
            (proje_id,)
        )
        return [self._row_to_model(r) for r in rows]

    def proje_belgesi_son_revizyon(self, proje_id: str,
                                    tur: str) -> Optional[Belge]:
        """Bir proje+tür için en yüksek revizyon numaralı belgeyi getirir."""
        row = self.db.getir_tek(
            """SELECT * FROM belgeler
               WHERE proje_id = ? AND tur = ? AND silinme_tarihi IS NULL
               ORDER BY revizyon_no DESC LIMIT 1""",
            (proje_id, tur)
        )
        return self._row_to_model(row) if row else None

    def proje_tur_revizyonlari(self, proje_id: str,
                                tur: str) -> list[Belge]:
        """Bir proje+tür kombinasyonu için tüm revizyonları getirir."""
        rows = self.db.getir_hepsi(
            """SELECT * FROM belgeler
               WHERE proje_id = ? AND tur = ? AND silinme_tarihi IS NULL
               ORDER BY revizyon_no DESC""",
            (proje_id, tur)
        )
        return [self._row_to_model(r) for r in rows]

    # ─────────────────────────────────────────
    # CRUD
    # ─────────────────────────────────────────

    def olustur(self, belge: Belge) -> Belge:
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO belgeler
                   (id, proje_id, tur, revizyon_no, durum,
                    toplam_maliyet, kar_orani, kdv_orani,
                    olusturan_id, olusturma_tarihi, guncelleme_tarihi,
                    snapshot_veri)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (belge.id, belge.proje_id, belge.tur, belge.revizyon_no,
                 belge.durum.value, belge.toplam_maliyet, belge.kar_orani,
                 belge.kdv_orani, belge.olusturan_id,
                 belge.olusturma_tarihi, belge.guncelleme_tarihi,
                 belge.snapshot_veri)
            )
        logger.info(f"Belge oluşturuldu: {belge.tur} Rev.{belge.revizyon_no} "
                     f"[{belge.id[:8]}]")
        return belge

    def guncelle(self, belge: Belge) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                """UPDATE belgeler SET
                   durum = ?, toplam_maliyet = ?, kar_orani = ?,
                   kdv_orani = ?, guncelleme_tarihi = ?, snapshot_veri = ?
                   WHERE id = ?""",
                (belge.durum.value, belge.toplam_maliyet, belge.kar_orani,
                 belge.kdv_orani, simdi_iso(), belge.snapshot_veri,
                 belge.id)
            )
        logger.info(f"Belge güncellendi: {belge.tur} Rev.{belge.revizyon_no}")

    def durum_guncelle(self, belge_id: str, durum: BelgeDurumu) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                """UPDATE belgeler SET durum = ?, guncelleme_tarihi = ?
                   WHERE id = ?""",
                (durum.value, simdi_iso(), belge_id)
            )

    def soft_delete(self, belge_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                """UPDATE belgeler SET
                   silinme_tarihi = ?, guncelleme_tarihi = ?
                   WHERE id = ?""",
                (simdi_iso(), simdi_iso(), belge_id)
            )
        logger.info(f"Belge silindi (soft): {belge_id}")

    # ─────────────────────────────────────────
    # BELGE ÜRÜNLERİ
    # ─────────────────────────────────────────

    def belge_urunlerini_getir(self, belge_id: str) -> list[dict]:
        """Belgeye bağlı ürünleri getirir."""
        rows = self.db.getir_hepsi(
            """SELECT bu.*, u.kod as urun_kodu, u.ad as urun_adi
               FROM belge_urunleri bu
               JOIN urunler u ON u.id = bu.urun_id
               WHERE bu.belge_id = ? AND bu.silinme_tarihi IS NULL
               ORDER BY u.kod""",
            (belge_id,)
        )
        return [dict(r) for r in rows]

    def belge_urunu_ekle(self, belge_id: str, urun_id: str,
                          miktar: int = 1, alan_verileri: str = "{}") -> str:
        """Belgeye ürün ekler. Oluşturulan kaydın ID'sini döndürür."""
        from uygulama.domain.modeller import _yeni_uuid
        kayit_id = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO belge_urunleri
                   (id, belge_id, urun_id, miktar, alan_verileri)
                   VALUES (?, ?, ?, ?, ?)""",
                (kayit_id, belge_id, urun_id, miktar, alan_verileri)
            )
        return kayit_id

    def belge_urunu_guncelle(self, kayit_id: str, miktar: int = None,
                              alan_verileri: str = None) -> None:
        """Belge ürün kaydını günceller."""
        updates = []
        params = []
        if miktar is not None:
            updates.append("miktar = ?")
            params.append(miktar)
        if alan_verileri is not None:
            updates.append("alan_verileri = ?")
            params.append(alan_verileri)
        if not updates:
            return
        params.append(kayit_id)
        with self.db.transaction() as conn:
            conn.execute(
                f"UPDATE belge_urunleri SET {', '.join(updates)} WHERE id = ?",
                tuple(params)
            )

    def belge_urunu_sil(self, kayit_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                """UPDATE belge_urunleri SET silinme_tarihi = ?
                   WHERE id = ?""",
                (simdi_iso(), kayit_id)
            )

    # ─────────────────────────────────────────
    # BELGE ALT KALEMLERİ
    # ─────────────────────────────────────────

    def belge_alt_kalemlerini_getir(self, belge_id: str,
                                     belge_urun_id: str = None) -> list[dict]:
        """Belgeye ait alt kalemleri getirir."""
        if belge_urun_id:
            rows = self.db.getir_hepsi(
                """SELECT bak.*, ak.ad as alt_kalem_adi
                   FROM belge_alt_kalemleri bak
                   JOIN alt_kalemler ak ON ak.id = bak.alt_kalem_id
                   WHERE bak.belge_id = ? AND bak.belge_urun_id = ?
                   AND bak.silinme_tarihi IS NULL""",
                (belge_id, belge_urun_id)
            )
        else:
            rows = self.db.getir_hepsi(
                """SELECT bak.*, ak.ad as alt_kalem_adi
                   FROM belge_alt_kalemleri bak
                   JOIN alt_kalemler ak ON ak.id = bak.alt_kalem_id
                   WHERE bak.belge_id = ? AND bak.silinme_tarihi IS NULL""",
                (belge_id,)
            )
        return [dict(r) for r in rows]

    def belge_alt_kalemi_ekle(self, belge_id: str, belge_urun_id: str,
                               alt_kalem_id: str, miktar: int = 1,
                               birim_fiyat: float = 0.0,
                               dahil: bool = True) -> str:
        from uygulama.domain.modeller import _yeni_uuid
        kayit_id = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO belge_alt_kalemleri
                   (id, belge_id, belge_urun_id, alt_kalem_id,
                    dahil, miktar, birim_fiyat)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (kayit_id, belge_id, belge_urun_id, alt_kalem_id,
                 int(dahil), miktar, birim_fiyat)
            )
        return kayit_id

    def belge_alt_kalemi_guncelle(self, kayit_id: str, dahil: bool = None,
                                   miktar: int = None,
                                   birim_fiyat: float = None) -> None:
        updates, params = [], []
        if dahil is not None:
            updates.append("dahil = ?")
            params.append(int(dahil))
        if miktar is not None:
            updates.append("miktar = ?")
            params.append(miktar)
        if birim_fiyat is not None:
            updates.append("birim_fiyat = ?")
            params.append(birim_fiyat)
        if not updates:
            return
        params.append(kayit_id)
        with self.db.transaction() as conn:
            conn.execute(
                f"UPDATE belge_alt_kalemleri SET {', '.join(updates)} WHERE id = ?",
                tuple(params)
            )

    def belge_alt_kalemi_sil(self, kayit_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                """UPDATE belge_alt_kalemleri SET silinme_tarihi = ?
                   WHERE id = ?""",
                (simdi_iso(), kayit_id)
            )

    # ─────────────────────────────────────────
    # İSTATİSTİKLER
    # ─────────────────────────────────────────

    def proje_belge_istatistikleri(self, proje_id: str) -> dict:
        """Proje belge istatistiklerini döndürür."""
        rows = self.db.getir_hepsi(
            """SELECT durum, COUNT(*) as sayi, SUM(toplam_maliyet) as toplam
               FROM belgeler
               WHERE proje_id = ? AND silinme_tarihi IS NULL
               GROUP BY durum""",
            (proje_id,)
        )
        stats = {"toplam_belge": 0, "toplam_maliyet": 0.0,
                 "taslak": 0, "onaylanan": 0, "reddedilen": 0}
        for r in rows:
            sayi = r["sayi"]
            stats["toplam_belge"] += sayi
            stats["toplam_maliyet"] += r["toplam"] or 0
            d = r["durum"]
            if d == "DRAFT":
                stats["taslak"] = sayi
            elif d == "APPROVED":
                stats["onaylanan"] = sayi
            elif d == "REJECTED":
                stats["reddedilen"] = sayi
        return stats
