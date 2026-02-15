#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Maliyet Repository — Parametre kombinasyonları, maliyet versiyonlama,
girdi değerleri, formüller ve konum çarpanları.
"""

import json
from typing import Optional
from datetime import datetime

from uygulama.altyapi.veritabani import Veritabani
from uygulama.domain.modeller import (
    ParametreKombinasyonu, MaliyetVersiyonu,
    MaliyetGirdiDegeri, MaliyetFormulu, KonumMaliyetCarpani,
    _yeni_uuid
)
from uygulama.ortak.yardimcilar import logger_olustur

logger = logger_olustur("maliyet_repo")


class MaliyetRepository:
    """Maliyet motoru veritabanı işlemleri."""

    def __init__(self, db: Veritabani):
        self.db = db

    # ═════════════════════════════════════════
    # PARAMETRE KOMBİNASYONLARI
    # ═════════════════════════════════════════

    def kombinasyon_getir(self, komb_id: str) -> Optional[dict]:
        row = self.db.getir_tek(
            "SELECT * FROM alt_kalem_parametre_kombinasyonlari WHERE id = ?",
            (komb_id,))
        return dict(row) if row else None

    def kombinasyon_hash_ile_getir(self, alt_kalem_id: str,
                                    komb_hash: str) -> Optional[dict]:
        """Aynı parametre seti daha önce kaydedilmiş mi?"""
        row = self.db.getir_tek(
            """SELECT * FROM alt_kalem_parametre_kombinasyonlari
               WHERE alt_kalem_id = ? AND kombinasyon_hash = ?
               AND aktif_mi = 1""",
            (alt_kalem_id, komb_hash))
        return dict(row) if row else None

    def kombinasyon_olustur(self, alt_kalem_id: str, komb_hash: str,
                             parametre_json: str) -> str:
        kayit_id = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO alt_kalem_parametre_kombinasyonlari
                   (id, alt_kalem_id, kombinasyon_hash, parametre_json)
                   VALUES (?, ?, ?, ?)""",
                (kayit_id, alt_kalem_id, komb_hash, parametre_json))
        return kayit_id

    def kombinasyon_pasif_yap(self, komb_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                """UPDATE alt_kalem_parametre_kombinasyonlari
                   SET aktif_mi = 0 WHERE id = ?""", (komb_id,))

    def kombinasyonlari_listele(self, alt_kalem_id: str) -> list[dict]:
        rows = self.db.getir_hepsi(
            """SELECT * FROM alt_kalem_parametre_kombinasyonlari
               WHERE alt_kalem_id = ? AND aktif_mi = 1
               ORDER BY created_at DESC""",
            (alt_kalem_id,))
        return [dict(r) for r in rows]

    # ═════════════════════════════════════════
    # MALİYET VERSİYONLARI
    # ═════════════════════════════════════════

    def versiyon_getir(self, versiyon_id: str) -> Optional[dict]:
        row = self.db.getir_tek(
            "SELECT * FROM alt_kalem_maliyet_versiyonlari WHERE id = ?",
            (versiyon_id,))
        return dict(row) if row else None

    def aktif_versiyon_getir(self, kombinasyon_id: str) -> Optional[dict]:
        """Bir kombinasyon için aktif maliyet versiyonunu getirir."""
        row = self.db.getir_tek(
            """SELECT * FROM alt_kalem_maliyet_versiyonlari
               WHERE kombinasyon_id = ? AND aktif_mi = 1
               ORDER BY versiyon_no DESC LIMIT 1""",
            (kombinasyon_id,))
        return dict(row) if row else None

    def versiyonlari_listele(self, kombinasyon_id: str) -> list[dict]:
        rows = self.db.getir_hepsi(
            """SELECT * FROM alt_kalem_maliyet_versiyonlari
               WHERE kombinasyon_id = ?
               ORDER BY versiyon_no DESC""",
            (kombinasyon_id,))
        return [dict(r) for r in rows]

    def versiyon_olustur(self, kombinasyon_id: str,
                          versiyon_no: int) -> str:
        kayit_id = _yeni_uuid()
        with self.db.transaction() as conn:
            # Önceki aktif versiyonu pasif yap
            conn.execute(
                """UPDATE alt_kalem_maliyet_versiyonlari
                   SET aktif_mi = 0
                   WHERE kombinasyon_id = ? AND aktif_mi = 1""",
                (kombinasyon_id,))
            conn.execute(
                """INSERT INTO alt_kalem_maliyet_versiyonlari
                   (id, kombinasyon_id, versiyon_no, aktif_mi)
                   VALUES (?, ?, ?, 1)""",
                (kayit_id, kombinasyon_id, versiyon_no))
        return kayit_id

    def versiyon_pasif_yap(self, versiyon_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                """UPDATE alt_kalem_maliyet_versiyonlari
                   SET aktif_mi = 0 WHERE id = ?""", (versiyon_id,))

    def son_versiyon_no(self, kombinasyon_id: str) -> int:
        row = self.db.getir_tek(
            """SELECT MAX(versiyon_no) as son
               FROM alt_kalem_maliyet_versiyonlari
               WHERE kombinasyon_id = ?""",
            (kombinasyon_id,))
        return row["son"] if row and row["son"] else 0

    # ═════════════════════════════════════════
    # GİRDİ DEĞERLERİ
    # ═════════════════════════════════════════

    def girdileri_getir(self, versiyon_id: str) -> list[dict]:
        rows = self.db.getir_hepsi(
            """SELECT * FROM alt_kalem_maliyet_girdi_degerleri
               WHERE versiyon_id = ?""",
            (versiyon_id,))
        return [dict(r) for r in rows]

    def girdi_ekle(self, versiyon_id: str, girdi_adi: str,
                    deger: str) -> str:
        kayit_id = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO alt_kalem_maliyet_girdi_degerleri
                   (id, versiyon_id, girdi_adi, deger)
                   VALUES (?, ?, ?, ?)""",
                (kayit_id, versiyon_id, girdi_adi, deger))
        return kayit_id

    def girdileri_toplu_ekle(self, versiyon_id: str,
                              girdiler: dict[str, str]) -> None:
        with self.db.transaction() as conn:
            for adi, deger in girdiler.items():
                conn.execute(
                    """INSERT INTO alt_kalem_maliyet_girdi_degerleri
                       (id, versiyon_id, girdi_adi, deger)
                       VALUES (?, ?, ?, ?)""",
                    (_yeni_uuid(), versiyon_id, adi, str(deger)))

    # ═════════════════════════════════════════
    # FORMÜLLER
    # ═════════════════════════════════════════

    def formulleri_getir(self, versiyon_id: str) -> list[dict]:
        rows = self.db.getir_hepsi(
            """SELECT * FROM alt_kalem_maliyet_formulleri
               WHERE versiyon_id = ?""",
            (versiyon_id,))
        return [dict(r) for r in rows]

    def formul_ekle(self, versiyon_id: str, alan_adi: str,
                     formul: str) -> str:
        kayit_id = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO alt_kalem_maliyet_formulleri
                   (id, versiyon_id, alan_adi, formul)
                   VALUES (?, ?, ?, ?)""",
                (kayit_id, versiyon_id, alan_adi, formul))
        return kayit_id

    def formulleri_toplu_ekle(self, versiyon_id: str,
                               formuller: dict[str, str]) -> None:
        with self.db.transaction() as conn:
            for alan, formul in formuller.items():
                conn.execute(
                    """INSERT INTO alt_kalem_maliyet_formulleri
                       (id, versiyon_id, alan_adi, formul)
                       VALUES (?, ?, ?, ?)""",
                    (_yeni_uuid(), versiyon_id, alan, formul))

    # ═════════════════════════════════════════
    # KONUM MALİYET ÇARPANLARI
    # ═════════════════════════════════════════

    def konum_carpani_getir(self, konum: str,
                             yil: int = None) -> Optional[dict]:
        if yil is None:
            yil = datetime.now().year
        row = self.db.getir_tek(
            """SELECT * FROM konum_maliyet_carpanlari
               WHERE konum = ? AND yil = ?""",
            (konum, yil))
        return dict(row) if row else None

    def konum_carpani_kaydet(self, konum: str, tasima: float,
                              iscilik: float, yil: int = None) -> str:
        if yil is None:
            yil = datetime.now().year
        # Mevcut varsa güncelle
        mevcut = self.konum_carpani_getir(konum, yil)
        if mevcut:
            with self.db.transaction() as conn:
                conn.execute(
                    """UPDATE konum_maliyet_carpanlari
                       SET tasima_carpani = ?, iscilik_carpani = ?
                       WHERE id = ?""",
                    (tasima, iscilik, mevcut["id"]))
            return mevcut["id"]
        # Yoksa oluştur
        kayit_id = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO konum_maliyet_carpanlari
                   (id, konum, tasima_carpani, iscilik_carpani, yil)
                   VALUES (?, ?, ?, ?, ?)""",
                (kayit_id, konum, tasima, iscilik, yil))
        return kayit_id

    def konum_carpanlari_listele(self, yil: int = None) -> list[dict]:
        if yil is None:
            yil = datetime.now().year
        rows = self.db.getir_hepsi(
            """SELECT * FROM konum_maliyet_carpanlari
               WHERE yil = ? ORDER BY konum""",
            (yil,))
        return [dict(r) for r in rows]

    # ═════════════════════════════════════════
    # TAM SNAPSHOT
    # ═════════════════════════════════════════

    def versiyon_tam_snapshot(self, versiyon_id: str) -> dict:
        """Bir versiyonun tüm verilerini snapshot olarak döndürür."""
        versiyon = self.versiyon_getir(versiyon_id)
        girdiler = self.girdileri_getir(versiyon_id)
        formuller = self.formulleri_getir(versiyon_id)
        komb = None
        if versiyon:
            komb = self.kombinasyon_getir(versiyon["kombinasyon_id"])
        return {
            "versiyon": versiyon,
            "kombinasyon": komb,
            "girdiler": girdiler,
            "formuller": formuller,
        }
