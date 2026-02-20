#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Enterprise Maliyet Repository — Versiyonlu ürün/alt kalem/formül/snapshot."""

import json
from typing import Optional
from uygulama.altyapi.veritabani import Veritabani
from uygulama.domain.modeller import _yeni_uuid
from uygulama.ortak.yardimcilar import logger_olustur, simdi_iso

logger = logger_olustur("enterprise_maliyet_repo")


class EnterpriseMaliyetRepository:
    def __init__(self, db: Veritabani):
        self.db = db

    # ═══════════════════════════════════════
    # PARAMETRE TİPLERİ
    # ═══════════════════════════════════════

    def parametre_tipleri(self) -> list[dict]:
        rows = self.db.getir_hepsi("SELECT * FROM parametre_tipler ORDER BY kod")
        return [dict(r) for r in rows]

    def birimler(self, kategori: str = None) -> list[dict]:
        if kategori:
            rows = self.db.getir_hepsi(
                "SELECT * FROM birimler WHERE kategori=? ORDER BY ad", (kategori,))
        else:
            rows = self.db.getir_hepsi("SELECT * FROM birimler ORDER BY kategori, ad")
        return [dict(r) for r in rows]

    def parametre_tipi_getir(self, tip_id: str) -> dict | None:
        row = self.db.getir_tek("SELECT * FROM parametre_tipler WHERE id=?", (tip_id,))
        return dict(row) if row else None

    # ═══════════════════════════════════════
    # ÜRÜN VERSİYON
    # ═══════════════════════════════════════

    def urun_versiyon_olustur(self, urun_id: str) -> tuple[str, int]:
        """Yeni ürün versiyonu oluşturur. Returns: (versiyon_id, versiyon_no)."""
        row = self.db.getir_tek(
            "SELECT COALESCE(MAX(versiyon_no),0) as m FROM urun_versiyonlar WHERE urun_id=?",
            (urun_id,))
        vno = (row["m"] if row else 0) + 1
        vid = _yeni_uuid()
        with self.db.transaction() as conn:
            # Eskiyi pasifle
            conn.execute("UPDATE urun_versiyonlar SET aktif_mi=0 WHERE urun_id=?", (urun_id,))
            conn.execute(
                """INSERT INTO urun_versiyonlar (id, urun_id, versiyon_no, olusturma_tarihi)
                   VALUES (?,?,?,?)""", (vid, urun_id, vno, simdi_iso()))
        return vid, vno

    def aktif_urun_versiyon(self, urun_id: str) -> dict | None:
        row = self.db.getir_tek(
            "SELECT * FROM urun_versiyonlar WHERE urun_id=? AND aktif_mi=1", (urun_id,))
        return dict(row) if row else None

    def urun_versiyonlar(self, urun_id: str) -> list[dict]:
        rows = self.db.getir_hepsi(
            "SELECT * FROM urun_versiyonlar WHERE urun_id=? ORDER BY versiyon_no DESC",
            (urun_id,))
        return [dict(r) for r in rows]

    # ═══════════════════════════════════════
    # ÜRÜN PARAMETRELERİ
    # ═══════════════════════════════════════

    def urun_parametre_ekle(self, urun_versiyon_id: str, ad: str, tip_id: str,
                             zorunlu: int = 0, varsayilan: str = "",
                             sira: int = 0, birim: str = "") -> str:
        pid = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO urun_parametreler
                   (id, urun_versiyon_id, ad, tip_id, zorunlu, varsayilan_deger, sira, birim)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (pid, urun_versiyon_id, ad, tip_id, zorunlu, varsayilan, sira, birim))
        return pid

    def urun_parametreleri(self, urun_versiyon_id: str) -> list[dict]:
        rows = self.db.getir_hepsi(
            """SELECT p.*, t.kod as tip_kodu, t.python_tipi
               FROM urun_parametreler p
               JOIN parametre_tipler t ON t.id = p.tip_id
               WHERE p.urun_versiyon_id=? AND p.aktif_mi=1 ORDER BY p.sira""",
            (urun_versiyon_id,))
        result = []
        for r in rows:
            d = dict(r)
            # birim kolonu yoksa boş
            if "birim" not in d:
                d["birim"] = ""
            result.append(d)
        return result

    def urun_parametre_sil(self, param_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute("UPDATE urun_parametreler SET aktif_mi=0 WHERE id=?", (param_id,))

    # ═══════════════════════════════════════
    # DROPDOWN DEĞERLER
    # ═══════════════════════════════════════

    def dropdown_deger_ekle(self, parametre_id: str, deger: str, sira: int = 0) -> str:
        did = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO parametre_dropdown_degerler
                   (id, parametre_id, deger, sira) VALUES (?,?,?,?)""",
                (did, parametre_id, deger, sira))
        return did

    def dropdown_degerleri(self, parametre_id: str) -> list[dict]:
        rows = self.db.getir_hepsi(
            "SELECT * FROM parametre_dropdown_degerler WHERE parametre_id=? ORDER BY sira",
            (parametre_id,))
        return [dict(r) for r in rows]

    def dropdown_deger_sil(self, deger_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM parametre_dropdown_degerler WHERE id=?", (deger_id,))

    # ═══════════════════════════════════════
    # ALT KALEM VERSİYON
    # ═══════════════════════════════════════

    def alt_kalem_versiyon_olustur(self, alt_kalem_id: str,
                                    urun_versiyon_id: str) -> tuple[str, int]:
        row = self.db.getir_tek(
            "SELECT COALESCE(MAX(versiyon_no),0) as m FROM alt_kalem_versiyonlar WHERE alt_kalem_id=?",
            (alt_kalem_id,))
        vno = (row["m"] if row else 0) + 1
        vid = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE alt_kalem_versiyonlar SET aktif_mi=0 WHERE alt_kalem_id=?",
                (alt_kalem_id,))
            conn.execute(
                """INSERT INTO alt_kalem_versiyonlar
                   (id, alt_kalem_id, urun_versiyon_id, versiyon_no, olusturma_tarihi)
                   VALUES (?,?,?,?,?)""",
                (vid, alt_kalem_id, urun_versiyon_id, vno, simdi_iso()))
        return vid, vno

    def aktif_alt_kalem_versiyon(self, alt_kalem_id: str) -> dict | None:
        row = self.db.getir_tek(
            "SELECT * FROM alt_kalem_versiyonlar WHERE alt_kalem_id=? AND aktif_mi=1",
            (alt_kalem_id,))
        return dict(row) if row else None

    def urun_versiyonuna_bagli_alt_kalemler(self, urun_versiyon_id: str) -> list[dict]:
        rows = self.db.getir_hepsi(
            """SELECT akv.*, ak.ad as alt_kalem_adi FROM alt_kalem_versiyonlar akv
               JOIN alt_kalemler ak ON ak.id = akv.alt_kalem_id
               WHERE akv.urun_versiyon_id=? AND akv.aktif_mi=1
               ORDER BY ak.ad""", (urun_versiyon_id,))
        return [dict(r) for r in rows]

    # ═══════════════════════════════════════
    # ALT KALEM PARAMETRELERİ
    # ═══════════════════════════════════════

    def alt_kalem_parametre_ekle(self, akv_id: str, ad: str, tip_id: str,
                                  zorunlu: int = 0, varsayilan: str = "",
                                  urun_param_ref: str = None, sira: int = 0,
                                  birim: str = "") -> str:
        pid = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO alt_kalem_parametreler
                   (id, alt_kalem_versiyon_id, ad, tip_id, zorunlu,
                    varsayilan_deger, urun_param_ref_id, sira, birim)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (pid, akv_id, ad, tip_id, zorunlu, varsayilan, urun_param_ref, sira, birim))
        return pid

    def alt_kalem_parametreleri(self, akv_id: str) -> list[dict]:
        rows = self.db.getir_hepsi(
            """SELECT p.*, t.kod as tip_kodu FROM alt_kalem_parametreler p
               JOIN parametre_tipler t ON t.id = p.tip_id
               WHERE p.alt_kalem_versiyon_id=? AND p.aktif_mi=1 ORDER BY p.sira""",
            (akv_id,))
        return [dict(r) for r in rows]

    # ═══════════════════════════════════════
    # MALİYET ŞABLONLARI
    # ═══════════════════════════════════════

    def sablon_olustur(self, akv_id: str, formul: str,
                        varsayilan: bool = True, kar: float = 0) -> str:
        sid = _yeni_uuid()
        with self.db.transaction() as conn:
            if varsayilan:
                conn.execute(
                    "UPDATE maliyet_sablonlar SET varsayilan_formul_mu=0 WHERE alt_kalem_versiyon_id=?",
                    (akv_id,))
            conn.execute(
                """INSERT INTO maliyet_sablonlar
                   (id, alt_kalem_versiyon_id, formul_ifadesi, varsayilan_formul_mu,
                    kar_orani, olusturma_tarihi)
                   VALUES (?,?,?,?,?,?)""",
                (sid, akv_id, formul, 1 if varsayilan else 0, kar, simdi_iso()))
        return sid

    def sablon_parametre_ekle(self, sablon_id: str, ad: str,
                               degisken_kodu: str, varsayilan: float = 0) -> str:
        pid = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO maliyet_parametreler
                   (id, maliyet_sablon_id, ad, degisken_kodu, varsayilan_deger)
                   VALUES (?,?,?,?,?)""", (pid, sablon_id, ad, degisken_kodu, varsayilan))
        return pid

    def aktif_sablon(self, akv_id: str) -> dict | None:
        row = self.db.getir_tek(
            """SELECT * FROM maliyet_sablonlar
               WHERE alt_kalem_versiyon_id=? AND aktif_mi=1 AND varsayilan_formul_mu=1""",
            (akv_id,))
        return dict(row) if row else None

    def sablon_parametreleri(self, sablon_id: str) -> list[dict]:
        rows = self.db.getir_hepsi(
            "SELECT * FROM maliyet_parametreler WHERE maliyet_sablon_id=? ORDER BY degisken_kodu",
            (sablon_id,))
        return [dict(r) for r in rows]

    def sablon_sil(self, sablon_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute("UPDATE maliyet_sablonlar SET aktif_mi=0 WHERE id=?", (sablon_id,))

    # ═══════════════════════════════════════
    # KONUM FİYAT
    # ═══════════════════════════════════════

    def konum_fiyat_getir(self, ulke: str, sehir: str) -> float:
        row = self.db.getir_tek(
            "SELECT fiyat FROM konum_fiyatlar WHERE ulke=? AND sehir=?",
            (ulke, sehir))
        return row["fiyat"] if row else 0.0

    def konum_fiyatlar(self) -> list[dict]:
        rows = self.db.getir_hepsi("SELECT * FROM konum_fiyatlar ORDER BY ulke, sehir")
        return [dict(r) for r in rows]

    def konum_fiyat_ekle(self, ulke: str, sehir: str, fiyat: float) -> str:
        kid = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT INTO konum_fiyatlar (id, ulke, sehir, fiyat) VALUES (?,?,?,?)",
                (kid, ulke, sehir, fiyat))
        return kid

    def konum_fiyat_guncelle(self, fiyat_id: str, fiyat: float) -> None:
        with self.db.transaction() as conn:
            conn.execute("UPDATE konum_fiyatlar SET fiyat=? WHERE id=?", (fiyat, fiyat_id))

    # ═══════════════════════════════════════
    # SNAPSHOT
    # ═══════════════════════════════════════

    def snapshot_kaydet(self, proje_id: str, belge_id: str, revizyon_no: int,
                         urun_id: str, urun_versiyon_id: str,
                         alt_kalem_id: str, alt_kalem_versiyon_id: str,
                         parametre_degerleri: dict, formul_ifadesi: str,
                         birim_fiyat: float, miktar: int, toplam_fiyat: float,
                         kar_orani: float, konum_fiyat: float,
                         opsiyon_mu: bool, olusturma_yili: int) -> str:
        sid = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO proje_maliyet_snapshot
                   (id, proje_id, belge_id, revizyon_no,
                    urun_id, urun_versiyon_id, alt_kalem_id, alt_kalem_versiyon_id,
                    parametre_degerleri, formul_ifadesi,
                    birim_fiyat, miktar, toplam_fiyat,
                    kar_orani, konum_fiyat, opsiyon_mu, olusturma_yili)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (sid, proje_id, belge_id, revizyon_no,
                 urun_id, urun_versiyon_id, alt_kalem_id, alt_kalem_versiyon_id,
                 json.dumps(parametre_degerleri, ensure_ascii=False),
                 formul_ifadesi, birim_fiyat, miktar, toplam_fiyat,
                 kar_orani, konum_fiyat, 1 if opsiyon_mu else 0, olusturma_yili))
        return sid

    def proje_snapshots(self, proje_id: str, revizyon_no: int = None) -> list[dict]:
        if revizyon_no is not None:
            rows = self.db.getir_hepsi(
                "SELECT * FROM proje_maliyet_snapshot WHERE proje_id=? AND revizyon_no=? ORDER BY id",
                (proje_id, revizyon_no))
        else:
            rows = self.db.getir_hepsi(
                "SELECT * FROM proje_maliyet_snapshot WHERE proje_id=? ORDER BY revizyon_no, id",
                (proje_id,))
        return [dict(r) for r in rows]

    def snapshot_sil(self, snapshot_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM proje_maliyet_snapshot WHERE id=?", (snapshot_id,))

    # ═══════════════════════════════════════
    # VERSİYON KOPYALAMA
    # ═══════════════════════════════════════

    def urun_versiyon_kopyala(self, urun_id: str) -> tuple[str, int]:
        """Aktif versiyondaki tüm parametreleri yeni versiyona kopyalar."""
        eski = self.aktif_urun_versiyon(urun_id)
        yeni_vid, yeni_vno = self.urun_versiyon_olustur(urun_id)
        if eski:
            for p in self.urun_parametreleri(eski["id"]):
                self.urun_parametre_ekle(
                    yeni_vid, p["ad"], p["tip_id"], p["zorunlu"],
                    p["varsayilan_deger"], p["sira"])
        return yeni_vid, yeni_vno

    def alt_kalem_versiyonu_kopyala(self, alt_kalem_id: str,
                                     urun_versiyon_id: str) -> tuple[str, int]:
        """Aktif alt kalem versiyonunu parametreler + formülle kopyalar."""
        eski = self.aktif_alt_kalem_versiyon(alt_kalem_id)
        yeni_vid, yeni_vno = self.alt_kalem_versiyon_olustur(
            alt_kalem_id, urun_versiyon_id)
        if eski:
            # Parametreleri kopyala
            for p in self.alt_kalem_parametreleri(eski["id"]):
                self.alt_kalem_parametre_ekle(
                    yeni_vid, p["ad"], p["tip_id"], p["zorunlu"],
                    p["varsayilan_deger"], p.get("urun_param_ref_id"), p["sira"])
            # Şablonu kopyala
            sablon = self.aktif_sablon(eski["id"])
            if sablon:
                yeni_sid = self.sablon_olustur(
                    yeni_vid, sablon["formul_ifadesi"], True, sablon["kar_orani"])
                for mp in self.sablon_parametreleri(sablon["id"]):
                    self.sablon_parametre_ekle(
                        yeni_sid, mp["ad"], mp["degisken_kodu"], mp["varsayilan_deger"])
        return yeni_vid, yeni_vno
