#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Placeholder Repository — Placeholder ve kural CRUD."""

import json
from typing import Optional
from uygulama.altyapi.veritabani import Veritabani
from uygulama.domain.modeller import _yeni_uuid
from uygulama.ortak.yardimcilar import logger_olustur, simdi_iso

logger = logger_olustur("placeholder_repo")

# Geçerli kural tipleri
KURAL_TIPLERI = ("esitlik", "karsilastirma", "dogrudan", "birlestirme", "sablon")
# Geçerli operatörler
OPERATORLER = ("=", "!=", ">", "<", ">=", "<=", "icerir", "baslar", "biter")
# Parametre kaynakları
PARAMETRE_KAYNAKLARI = ("urun_param", "alt_kalem_param", "proje_bilgi", "teklif_param")

# Proje bilgi alanları (parametre_adi olarak kullanılır)
PROJE_BILGI_ALANLARI = [
    "PROJE_ADI", "PROJE_KODU", "PROJE_KONUM", "PROJE_TESIS_TURU",
    "PROJE_ULKE", "PROJE_SEHIR", "PROJE_TARIHI",
]


class PlaceholderRepository:
    def __init__(self, db: Veritabani):
        self.db = db

    # ═══════════════════════════════════════
    # PLACEHOLDER CRUD
    # ═══════════════════════════════════════

    def olustur(self, kod: str, ad: str = "", aciklama: str = "") -> tuple[bool, str, str]:
        """Yeni placeholder oluşturur. Returns: (ok, mesaj, id)."""
        # Kod formatı kontrol: {/XXX/} şeklinde olmalı
        if not kod.startswith("{/") or not kod.endswith("/}"):
            kod = "{/" + kod.strip("{}/ ").upper() + "/}"

        # Unique kontrol
        mevcut = self.db.getir_tek(
            "SELECT id FROM placeholders WHERE kod=?", (kod,))
        if mevcut:
            return False, f"'{kod}' zaten mevcut.", ""

        pid = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO placeholders (id, kod, ad, aciklama, olusturma_tarihi)
                   VALUES (?,?,?,?,?)""",
                (pid, kod, ad or kod, aciklama, simdi_iso()))
        logger.info(f"Placeholder oluşturuldu: {kod}")
        return True, "Oluşturuldu.", pid

    def getir(self, placeholder_id: str) -> dict | None:
        row = self.db.getir_tek("SELECT * FROM placeholders WHERE id=?", (placeholder_id,))
        return dict(row) if row else None

    def kod_ile_getir(self, kod: str) -> dict | None:
        row = self.db.getir_tek("SELECT * FROM placeholders WHERE kod=?", (kod,))
        return dict(row) if row else None

    def listele(self, sadece_aktif: bool = True) -> list[dict]:
        if sadece_aktif:
            rows = self.db.getir_hepsi(
                "SELECT * FROM placeholders WHERE aktif_mi=1 ORDER BY kod")
        else:
            rows = self.db.getir_hepsi("SELECT * FROM placeholders ORDER BY kod")
        return [dict(r) for r in rows]

    def guncelle(self, placeholder_id: str, ad: str = None,
                  aciklama: str = None) -> None:
        updates, params = [], []
        if ad is not None:
            updates.append("ad=?"); params.append(ad)
        if aciklama is not None:
            updates.append("aciklama=?"); params.append(aciklama)
        if updates:
            params.append(placeholder_id)
            with self.db.transaction() as conn:
                conn.execute(
                    f"UPDATE placeholders SET {','.join(updates)} WHERE id=?",
                    params)

    def sil(self, placeholder_id: str) -> None:
        """Soft delete."""
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE placeholders SET aktif_mi=0 WHERE id=?", (placeholder_id,))

    # ═══════════════════════════════════════
    # KURAL CRUD
    # ═══════════════════════════════════════

    def kural_ekle(self, placeholder_id: str, kural_tipi: str,
                    parametre_kaynak: str, parametre_adi: str,
                    operator: str = "=", kosul_degeri: str = "",
                    sonuc_metni: str = "", varsayilan_mi: bool = False,
                    parametre_ref_id: str = None) -> tuple[bool, str, str]:
        """Placeholder'a kural ekler."""
        if kural_tipi not in KURAL_TIPLERI:
            return False, f"Geçersiz kural tipi: {kural_tipi}", ""

        # Sıra hesapla
        row = self.db.getir_tek(
            "SELECT COALESCE(MAX(sira),0) as m FROM placeholder_kurallar WHERE placeholder_id=?",
            (placeholder_id,))
        sira = (row["m"] if row else 0) + 1

        kid = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO placeholder_kurallar
                   (id, placeholder_id, sira, kural_tipi, parametre_kaynak,
                    parametre_ref_id, parametre_adi, operator, kosul_degeri,
                    sonuc_metni, varsayilan_mi, olusturma_tarihi)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (kid, placeholder_id, sira, kural_tipi, parametre_kaynak,
                 parametre_ref_id, parametre_adi, operator, kosul_degeri,
                 sonuc_metni, 1 if varsayilan_mi else 0, simdi_iso()))
        return True, "Kural eklendi.", kid

    def kurallar(self, placeholder_id: str) -> list[dict]:
        rows = self.db.getir_hepsi(
            """SELECT * FROM placeholder_kurallar
               WHERE placeholder_id=? AND aktif_mi=1 ORDER BY sira""",
            (placeholder_id,))
        return [dict(r) for r in rows]

    def kural_getir(self, kural_id: str) -> dict | None:
        row = self.db.getir_tek(
            "SELECT * FROM placeholder_kurallar WHERE id=?", (kural_id,))
        return dict(row) if row else None

    def kural_guncelle(self, kural_id: str, **kwargs) -> None:
        allowed = {"kural_tipi", "parametre_kaynak", "parametre_adi",
                    "operator", "kosul_degeri", "sonuc_metni", "varsayilan_mi",
                    "parametre_ref_id", "sira"}
        updates, params = [], []
        for k, v in kwargs.items():
            if k in allowed:
                updates.append(f"{k}=?")
                params.append(v if k != "varsayilan_mi" else (1 if v else 0))
        if updates:
            params.append(kural_id)
            with self.db.transaction() as conn:
                conn.execute(
                    f"UPDATE placeholder_kurallar SET {','.join(updates)} WHERE id=?",
                    params)

    def kural_sil(self, kural_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE placeholder_kurallar SET aktif_mi=0 WHERE id=?", (kural_id,))

    def kural_sira_degistir(self, kural_id: str, yeni_sira: int) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE placeholder_kurallar SET sira=? WHERE id=?",
                (yeni_sira, kural_id))
