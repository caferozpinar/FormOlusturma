#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Teklif Repository — Teklif/Keşif CRUD, kalem ve parametre yönetimi."""

from typing import Optional
from uygulama.altyapi.veritabani import Veritabani
from uygulama.domain.modeller import _yeni_uuid
from uygulama.ortak.yardimcilar import logger_olustur, simdi_iso

logger = logger_olustur("teklif_repo")

PARA_BIRIMLERI = [
    ("TRY", "₺", "Türk Lirası"),
    ("EUR", "€", "Euro"),
    ("USD", "$", "Amerikan Doları"),
    ("GBP", "£", "İngiliz Sterlini"),
]

TEKLIF_DURUMLARI = ["TASLAK", "GONDERILDI", "ONAYLANDI", "REDDEDILDI", "KAPANDI"]


class TeklifRepository:
    def __init__(self, db: Veritabani):
        self.db = db

    # ═══════════════════════════════════════
    # TEKLİF CRUD
    # ═══════════════════════════════════════

    def olustur(self, proje_id: str, tur: str = "TEKLİF",
                baslik: str = "", para_birimi: str = "TRY",
                olusturan: str = "") -> str:
        tid = _yeni_uuid()
        # Revizyon no: aynı proje+tür için max+1
        row = self.db.getir_tek(
            "SELECT COALESCE(MAX(revizyon_no),0) as m FROM teklifler WHERE proje_id=? AND tur=?",
            (proje_id, tur))
        rev = (row["m"] if row else 0) + 1
        if not baslik:
            baslik = f"{tur} Rev.{rev}"
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO teklifler
                   (id, proje_id, tur, baslik, para_birimi, revizyon_no,
                    olusturan, olusturma_tarihi, guncelleme_tarihi)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (tid, proje_id, tur, baslik, para_birimi, rev,
                 olusturan, simdi_iso(), simdi_iso()))
        logger.info(f"Teklif oluşturuldu: {tur} Rev.{rev} ({tid[:8]})")
        return tid

    def getir(self, teklif_id: str) -> dict | None:
        row = self.db.getir_tek("SELECT * FROM teklifler WHERE id=?", (teklif_id,))
        return dict(row) if row else None

    def proje_teklifleri(self, proje_id: str) -> list[dict]:
        rows = self.db.getir_hepsi(
            """SELECT * FROM teklifler WHERE proje_id=?
               ORDER BY tur, revizyon_no DESC""", (proje_id,))
        return [dict(r) for r in rows]

    def guncelle(self, teklif_id: str, **kwargs) -> None:
        allowed = {"baslik", "para_birimi", "durum", "notlar",
                   "toplam_fiyat", "kdv_orani", "kdv_tutari", "kdv_dahil_toplam"}
        updates, params = ["guncelleme_tarihi=?"], [simdi_iso()]
        for k, v in kwargs.items():
            if k in allowed:
                updates.append(f"{k}=?"); params.append(v)
        params.append(teklif_id)
        with self.db.transaction() as conn:
            conn.execute(
                f"UPDATE teklifler SET {','.join(updates)} WHERE id=?", params)

    def sil(self, teklif_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM teklif_parametre_degerleri WHERE teklif_kalem_id IN (SELECT id FROM teklif_kalemleri WHERE teklif_id=?)", (teklif_id,))
            conn.execute("DELETE FROM teklif_kalemleri WHERE teklif_id=?", (teklif_id,))
            conn.execute("DELETE FROM teklifler WHERE id=?", (teklif_id,))

    # ═══════════════════════════════════════
    # TEKLİF KALEMLERİ
    # ═══════════════════════════════════════

    def kalem_ekle(self, teklif_id: str, urun_id: str,
                    urun_versiyon_id: str,
                    alt_kalem_id: str = None,
                    alt_kalem_versiyon_id: str = None,
                    sira: int = 0) -> str:
        kid = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO teklif_kalemleri
                   (id, teklif_id, urun_id, urun_versiyon_id,
                    alt_kalem_id, alt_kalem_versiyon_id, sira)
                   VALUES (?,?,?,?,?,?,?)""",
                (kid, teklif_id, urun_id, urun_versiyon_id,
                 alt_kalem_id, alt_kalem_versiyon_id, sira))
        return kid

    def kalemler(self, teklif_id: str) -> list[dict]:
        rows = self.db.getir_hepsi(
            "SELECT * FROM teklif_kalemleri WHERE teklif_id=? ORDER BY sira",
            (teklif_id,))
        return [dict(r) for r in rows]

    def kalem_guncelle(self, kalem_id: str, **kwargs) -> None:
        allowed = {"secili_mi", "miktar", "birim_fiyat", "toplam_fiyat", "dahil_durumu"}
        updates, params = [], []
        for k, v in kwargs.items():
            if k in allowed:
                updates.append(f"{k}=?"); params.append(v)
        if updates:
            params.append(kalem_id)
            with self.db.transaction() as conn:
                conn.execute(
                    f"UPDATE teklif_kalemleri SET {','.join(updates)} WHERE id=?",
                    params)

    def kalem_sil(self, kalem_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM teklif_parametre_degerleri WHERE teklif_kalem_id=?", (kalem_id,))
            conn.execute("DELETE FROM teklif_kalemleri WHERE id=?", (kalem_id,))

    # ═══════════════════════════════════════
    # PARAMETRE DEĞERLERİ
    # ═══════════════════════════════════════

    def parametre_kaydet(self, kalem_id: str, parametre_id: str,
                          parametre_adi: str, deger: str) -> str:
        # Upsert: varsa güncelle, yoksa ekle
        row = self.db.getir_tek(
            "SELECT id FROM teklif_parametre_degerleri WHERE teklif_kalem_id=? AND parametre_id=?",
            (kalem_id, parametre_id))
        if row:
            with self.db.transaction() as conn:
                conn.execute(
                    "UPDATE teklif_parametre_degerleri SET deger=? WHERE id=?",
                    (deger, row["id"]))
            return row["id"]
        else:
            pid = _yeni_uuid()
            with self.db.transaction() as conn:
                conn.execute(
                    """INSERT INTO teklif_parametre_degerleri
                       (id, teklif_kalem_id, parametre_id, parametre_adi, deger)
                       VALUES (?,?,?,?,?)""",
                    (pid, kalem_id, parametre_id, parametre_adi, deger))
            return pid

    def parametre_degerleri(self, kalem_id: str) -> list[dict]:
        rows = self.db.getir_hepsi(
            "SELECT * FROM teklif_parametre_degerleri WHERE teklif_kalem_id=? ORDER BY parametre_adi",
            (kalem_id,))
        return [dict(r) for r in rows]

    def toplu_parametre_kaydet(self, kalem_id: str,
                                degerler: list[dict]) -> None:
        """degerler: [{parametre_id, parametre_adi, deger}, ...]"""
        for d in degerler:
            self.parametre_kaydet(
                kalem_id, d["parametre_id"], d["parametre_adi"], d["deger"])

    # ═══════════════════════════════════════
    # TOPLAM HESAPLAMA
    # ═══════════════════════════════════════

    def teklif_toplamini_hesapla(self, teklif_id: str) -> dict:
        """DAHIL durumundaki seçili kalemlerin toplamını hesaplar + KDV.
        Returns: {toplam, kdv_orani, kdv_tutari, kdv_dahil_toplam}"""
        row = self.db.getir_tek(
            """SELECT COALESCE(SUM(toplam_fiyat), 0) as toplam
               FROM teklif_kalemleri
               WHERE teklif_id=? AND secili_mi=1 AND dahil_durumu='DAHIL'""",
            (teklif_id,))
        toplam = row["toplam"] if row else 0

        # KDV oranını oku
        teklif = self.getir(teklif_id)
        kdv_orani = teklif.get("kdv_orani", 20) if teklif else 20
        kdv_tutari = round(toplam * kdv_orani / 100, 2)
        kdv_dahil = round(toplam + kdv_tutari, 2)

        self.guncelle(teklif_id,
                       toplam_fiyat=toplam,
                       kdv_tutari=kdv_tutari,
                       kdv_dahil_toplam=kdv_dahil)
        return {
            "toplam": toplam,
            "kdv_orani": kdv_orani,
            "kdv_tutari": kdv_tutari,
            "kdv_dahil_toplam": kdv_dahil,
        }
