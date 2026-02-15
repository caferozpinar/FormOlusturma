#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ürün Repository — Ürün, alan, seçenek, alt kalem veritabanı işlemleri.
"""

from typing import Optional

from uygulama.altyapi.veritabani import Veritabani
from uygulama.domain.modeller import (
    Urun, UrunAlani, UrunAlanSecenegi, AltKalem, UrunAltKalemi,
    AlanTipi, _yeni_uuid
)
from uygulama.ortak.yardimcilar import logger_olustur, simdi_iso

logger = logger_olustur("urun_repo")


class UrunRepository:
    """Ürün veritabanı işlemleri."""

    def __init__(self, db: Veritabani):
        self.db = db

    # ═════════════════════════════════════════
    # ÜRÜN CRUD
    # ═════════════════════════════════════════

    def id_ile_getir(self, urun_id: str) -> Optional[Urun]:
        row = self.db.getir_tek(
            "SELECT * FROM urunler WHERE id = ? AND silinme_tarihi IS NULL",
            (urun_id,))
        if not row:
            return None
        return Urun(id=row["id"], kod=row["kod"], ad=row["ad"],
                     aktif=bool(row["aktif"]),
                     olusturma_tarihi=row["olusturma_tarihi"],
                     silinme_tarihi=row["silinme_tarihi"])

    def kod_ile_getir(self, kod: str) -> Optional[Urun]:
        row = self.db.getir_tek(
            "SELECT * FROM urunler WHERE kod = ? AND silinme_tarihi IS NULL",
            (kod,))
        if not row:
            return None
        return Urun(id=row["id"], kod=row["kod"], ad=row["ad"],
                     aktif=bool(row["aktif"]),
                     olusturma_tarihi=row["olusturma_tarihi"],
                     silinme_tarihi=row["silinme_tarihi"])

    def listele(self, sadece_aktif: bool = True) -> list[Urun]:
        sql = "SELECT * FROM urunler WHERE silinme_tarihi IS NULL"
        if sadece_aktif:
            sql += " AND aktif = 1"
        sql += " ORDER BY kod"
        rows = self.db.getir_hepsi(sql)
        return [Urun(id=r["id"], kod=r["kod"], ad=r["ad"],
                      aktif=bool(r["aktif"]),
                      olusturma_tarihi=r["olusturma_tarihi"])
                for r in rows]

    def olustur(self, urun: Urun) -> Urun:
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO urunler (id, kod, ad, aktif, olusturma_tarihi)
                   VALUES (?, ?, ?, ?, ?)""",
                (urun.id, urun.kod, urun.ad, int(urun.aktif),
                 urun.olusturma_tarihi))
        logger.info(f"Ürün oluşturuldu: {urun.kod} — {urun.ad}")
        return urun

    def guncelle(self, urun: Urun) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE urunler SET kod = ?, ad = ?, aktif = ? WHERE id = ?",
                (urun.kod, urun.ad, int(urun.aktif), urun.id))
        logger.info(f"Ürün güncellendi: {urun.kod}")

    def soft_delete(self, urun_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE urunler SET silinme_tarihi = ? WHERE id = ?",
                (simdi_iso(), urun_id))
        logger.info(f"Ürün silindi (soft): {urun_id}")

    def kod_mevcut_mu(self, kod: str, haric_id: str = "") -> bool:
        if haric_id:
            row = self.db.getir_tek(
                """SELECT COUNT(*) as c FROM urunler
                   WHERE kod = ? AND id != ? AND silinme_tarihi IS NULL""",
                (kod, haric_id))
        else:
            row = self.db.getir_tek(
                """SELECT COUNT(*) as c FROM urunler
                   WHERE kod = ? AND silinme_tarihi IS NULL""", (kod,))
        return row["c"] > 0 if row else False

    # ═════════════════════════════════════════
    # ÜRÜN ALANLARI
    # ═════════════════════════════════════════

    def alanlari_getir(self, urun_id: str) -> list[dict]:
        rows = self.db.getir_hepsi(
            """SELECT * FROM urun_alanlari
               WHERE urun_id = ? AND silinme_tarihi IS NULL
               ORDER BY sira, etiket""",
            (urun_id,))
        return [dict(r) for r in rows]

    def alan_getir(self, alan_id: str) -> Optional[dict]:
        row = self.db.getir_tek(
            "SELECT * FROM urun_alanlari WHERE id = ? AND silinme_tarihi IS NULL",
            (alan_id,))
        return dict(row) if row else None

    def alan_ekle(self, urun_id: str, etiket: str, alan_anahtari: str,
                   tip: str = "text", zorunlu: bool = False, sira: int = 0,
                   min_deger: float = None, max_deger: float = None,
                   hassasiyet: int = None) -> str:
        alan_id = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO urun_alanlari
                   (id, urun_id, etiket, alan_anahtari, tip, zorunlu, sira,
                    min_deger, max_deger, hassasiyet)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (alan_id, urun_id, etiket, alan_anahtari, tip,
                 int(zorunlu), sira, min_deger, max_deger, hassasiyet))
        logger.info(f"Alan eklendi: {etiket} ({tip}) → ürün {urun_id[:8]}")
        return alan_id

    def alan_guncelle(self, alan_id: str, etiket: str = None,
                       tip: str = None, zorunlu: bool = None,
                       sira: int = None, min_deger: float = None,
                       max_deger: float = None,
                       hassasiyet: int = None) -> None:
        updates, params = [], []
        if etiket is not None:
            updates.append("etiket = ?"); params.append(etiket)
        if tip is not None:
            updates.append("tip = ?"); params.append(tip)
        if zorunlu is not None:
            updates.append("zorunlu = ?"); params.append(int(zorunlu))
        if sira is not None:
            updates.append("sira = ?"); params.append(sira)
        if min_deger is not None:
            updates.append("min_deger = ?"); params.append(min_deger)
        if max_deger is not None:
            updates.append("max_deger = ?"); params.append(max_deger)
        if hassasiyet is not None:
            updates.append("hassasiyet = ?"); params.append(hassasiyet)
        if not updates:
            return
        params.append(alan_id)
        with self.db.transaction() as conn:
            conn.execute(
                f"UPDATE urun_alanlari SET {', '.join(updates)} WHERE id = ?",
                tuple(params))

    def alan_sil(self, alan_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE urun_alanlari SET silinme_tarihi = ? WHERE id = ?",
                (simdi_iso(), alan_id))
            conn.execute(
                "UPDATE urun_alan_secenekleri SET silinme_tarihi = ? WHERE alan_id = ?",
                (simdi_iso(), alan_id))

    # ═════════════════════════════════════════
    # ALAN SEÇENEKLERİ
    # ═════════════════════════════════════════

    def secenekleri_getir(self, alan_id: str) -> list[dict]:
        rows = self.db.getir_hepsi(
            """SELECT * FROM urun_alan_secenekleri
               WHERE alan_id = ? AND silinme_tarihi IS NULL
               ORDER BY sira, deger""",
            (alan_id,))
        return [dict(r) for r in rows]

    def secenek_ekle(self, alan_id: str, deger: str, sira: int = 0) -> str:
        sec_id = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO urun_alan_secenekleri
                   (id, alan_id, deger, sira) VALUES (?, ?, ?, ?)""",
                (sec_id, alan_id, deger, sira))
        return sec_id

    def secenek_guncelle(self, sec_id: str, deger: str = None,
                          sira: int = None) -> None:
        updates, params = [], []
        if deger is not None:
            updates.append("deger = ?"); params.append(deger)
        if sira is not None:
            updates.append("sira = ?"); params.append(sira)
        if not updates:
            return
        params.append(sec_id)
        with self.db.transaction() as conn:
            conn.execute(
                f"UPDATE urun_alan_secenekleri SET {', '.join(updates)} WHERE id = ?",
                tuple(params))

    def secenek_sil(self, sec_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE urun_alan_secenekleri SET silinme_tarihi = ? WHERE id = ?",
                (simdi_iso(), sec_id))

    # ═════════════════════════════════════════
    # ALT KALEMLER
    # ═════════════════════════════════════════

    def alt_kalem_listele(self, sadece_aktif: bool = True) -> list[dict]:
        sql = "SELECT * FROM alt_kalemler WHERE silinme_tarihi IS NULL"
        if sadece_aktif:
            sql += " AND aktif = 1"
        sql += " ORDER BY ad"
        return [dict(r) for r in self.db.getir_hepsi(sql)]

    def alt_kalem_getir(self, ak_id: str) -> Optional[dict]:
        row = self.db.getir_tek(
            "SELECT * FROM alt_kalemler WHERE id = ? AND silinme_tarihi IS NULL",
            (ak_id,))
        return dict(row) if row else None

    def alt_kalem_olustur(self, ad: str) -> str:
        ak_id = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT INTO alt_kalemler (id, ad) VALUES (?, ?)", (ak_id, ad))
        logger.info(f"Alt kalem oluşturuldu: {ad}")
        return ak_id

    def alt_kalem_guncelle(self, ak_id: str, ad: str = None,
                            aktif: bool = None) -> None:
        updates, params = [], []
        if ad is not None:
            updates.append("ad = ?"); params.append(ad)
        if aktif is not None:
            updates.append("aktif = ?"); params.append(int(aktif))
        if not updates:
            return
        params.append(ak_id)
        with self.db.transaction() as conn:
            conn.execute(
                f"UPDATE alt_kalemler SET {', '.join(updates)} WHERE id = ?",
                tuple(params))

    def alt_kalem_sil(self, ak_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE alt_kalemler SET silinme_tarihi = ? WHERE id = ?",
                (simdi_iso(), ak_id))

    # ═════════════════════════════════════════
    # ÜRÜN ↔ ALT KALEM BAĞLANTILARI
    # ═════════════════════════════════════════

    def urun_alt_kalemleri(self, urun_id: str) -> list[dict]:
        rows = self.db.getir_hepsi(
            """SELECT uak.*, ak.ad as alt_kalem_adi
               FROM urun_alt_kalemleri uak
               JOIN alt_kalemler ak ON ak.id = uak.alt_kalem_id
               WHERE uak.urun_id = ? AND uak.silinme_tarihi IS NULL
               AND ak.silinme_tarihi IS NULL
               ORDER BY ak.ad""",
            (urun_id,))
        return [dict(r) for r in rows]

    def urun_alt_kalem_bagla(self, urun_id: str, alt_kalem_id: str,
                              varsayilan_birim_fiyat: float = 0.0) -> str:
        kayit_id = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO urun_alt_kalemleri
                   (id, urun_id, alt_kalem_id, varsayilan_birim_fiyat)
                   VALUES (?, ?, ?, ?)""",
                (kayit_id, urun_id, alt_kalem_id, varsayilan_birim_fiyat))
        return kayit_id

    def urun_alt_kalem_fiyat_guncelle(self, kayit_id: str, fiyat: float) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE urun_alt_kalemleri SET varsayilan_birim_fiyat = ? WHERE id = ?",
                (fiyat, kayit_id))

    def urun_alt_kalem_kopar(self, kayit_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE urun_alt_kalemleri SET silinme_tarihi = ? WHERE id = ?",
                (simdi_iso(), kayit_id))

    # ═════════════════════════════════════════
    # TAM ÜRÜN DETAYI
    # ═════════════════════════════════════════

    def tam_detay(self, urun_id: str) -> Optional[dict]:
        """Ürün + alanlar + seçenekler + alt kalemler."""
        urun = self.id_ile_getir(urun_id)
        if not urun:
            return None
        alanlar = self.alanlari_getir(urun_id)
        for alan in alanlar:
            if alan["tip"] in ("choice", "multi-choice"):
                alan["secenekler"] = self.secenekleri_getir(alan["id"])
            else:
                alan["secenekler"] = []
        alt_kalemler = self.urun_alt_kalemleri(urun_id)
        return {"urun": urun, "alanlar": alanlar, "alt_kalemler": alt_kalemler}
