#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Versiyonlu Ürün/Alt Kalem/Maliyet Repository — Enterprise seviye."""

import json
from uygulama.altyapi.veritabani import Veritabani
from uygulama.domain.modeller import _yeni_uuid
from uygulama.ortak.yardimcilar import logger_olustur, simdi_iso

logger = logger_olustur("versiyon_repo")


class VersiyonRepository:
    """Versiyonlu ürün, alt kalem, maliyet şablon, snapshot işlemleri."""

    def __init__(self, db: Veritabani):
        self.db = db

    # ═════════════════════════════════════════
    # PARAMETRE TİP KATALOĞU
    # ═════════════════════════════════════════

    def parametre_tipleri(self) -> list[dict]:
        rows = self.db.getir_hepsi("SELECT * FROM parametre_tipler ORDER BY kod")
        return [dict(r) for r in rows]

    def parametre_tip_getir(self, tip_id: str) -> dict | None:
        row = self.db.getir_tek("SELECT * FROM parametre_tipler WHERE id=?", (tip_id,))
        return dict(row) if row else None

    # ═════════════════════════════════════════
    # ÜRÜN VERSİYON
    # ═════════════════════════════════════════

    def urun_versiyon_olustur(self, urun_id: str) -> str:
        """Yeni ürün versiyonu. Returns: versiyon_id."""
        max_row = self.db.getir_tek(
            "SELECT COALESCE(MAX(versiyon_no),0) as m FROM urun_versiyonlar WHERE urun_id=?",
            (urun_id,))
        yeni_no = (max_row["m"] if max_row else 0) + 1
        vid = _yeni_uuid()
        with self.db.transaction() as conn:
            # Eski aktifi pasifle
            conn.execute(
                "UPDATE urun_versiyonlar SET aktif_mi=0 WHERE urun_id=? AND aktif_mi=1",
                (urun_id,))
            conn.execute(
                """INSERT INTO urun_versiyonlar (id, urun_id, versiyon_no, olusturma_tarihi)
                   VALUES (?,?,?,?)""",
                (vid, urun_id, yeni_no, simdi_iso()))
        logger.info(f"Ürün versiyon v{yeni_no}: {urun_id[:8]}")
        return vid

    def aktif_urun_versiyon(self, urun_id: str) -> dict | None:
        row = self.db.getir_tek(
            "SELECT * FROM urun_versiyonlar WHERE urun_id=? AND aktif_mi=1", (urun_id,))
        return dict(row) if row else None

    def urun_versiyonlari(self, urun_id: str) -> list[dict]:
        rows = self.db.getir_hepsi(
            "SELECT * FROM urun_versiyonlar WHERE urun_id=? ORDER BY versiyon_no DESC",
            (urun_id,))
        return [dict(r) for r in rows]

    # ═════════════════════════════════════════
    # ÜRÜN PARAMETRE
    # ═════════════════════════════════════════

    def urun_parametre_ekle(self, urun_versiyon_id: str, ad: str,
                             tip_id: str, zorunlu: bool = False,
                             varsayilan: str = "", sira: int = 0) -> str:
        pid = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO urun_parametreler
                   (id, urun_versiyon_id, ad, tip_id, zorunlu, varsayilan_deger, sira)
                   VALUES (?,?,?,?,?,?,?)""",
                (pid, urun_versiyon_id, ad, tip_id, int(zorunlu), varsayilan, sira))
        return pid

    def urun_parametreleri(self, urun_versiyon_id: str) -> list[dict]:
        rows = self.db.getir_hepsi(
            """SELECT up.*, pt.kod as tip_kod, pt.python_tipi
               FROM urun_parametreler up
               JOIN parametre_tipler pt ON pt.id = up.tip_id
               WHERE up.urun_versiyon_id=? AND up.aktif_mi=1
               ORDER BY up.sira""",
            (urun_versiyon_id,))
        return [dict(r) for r in rows]

    def dropdown_deger_ekle(self, parametre_id: str, deger: str, sira: int = 0) -> str:
        did = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT INTO parametre_dropdown_degerler (id, parametre_id, deger, sira) VALUES (?,?,?,?)",
                (did, parametre_id, deger, sira))
        return did

    def dropdown_degerleri(self, parametre_id: str) -> list[dict]:
        rows = self.db.getir_hepsi(
            "SELECT * FROM parametre_dropdown_degerler WHERE parametre_id=? ORDER BY sira",
            (parametre_id,))
        return [dict(r) for r in rows]

    # ═════════════════════════════════════════
    # ALT KALEM VERSİYON
    # ═════════════════════════════════════════

    def alt_kalem_versiyon_olustur(self, alt_kalem_id: str,
                                     urun_versiyon_id: str) -> str:
        max_row = self.db.getir_tek(
            "SELECT COALESCE(MAX(versiyon_no),0) as m FROM alt_kalem_versiyonlar WHERE alt_kalem_id=?",
            (alt_kalem_id,))
        yeni_no = (max_row["m"] if max_row else 0) + 1
        vid = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE alt_kalem_versiyonlar SET aktif_mi=0 WHERE alt_kalem_id=? AND aktif_mi=1",
                (alt_kalem_id,))
            conn.execute(
                """INSERT INTO alt_kalem_versiyonlar
                   (id, alt_kalem_id, urun_versiyon_id, versiyon_no, olusturma_tarihi)
                   VALUES (?,?,?,?,?)""",
                (vid, alt_kalem_id, urun_versiyon_id, yeni_no, simdi_iso()))
        logger.info(f"Alt kalem versiyon v{yeni_no}: {alt_kalem_id[:8]}")
        return vid

    def aktif_alt_kalem_versiyon(self, alt_kalem_id: str) -> dict | None:
        row = self.db.getir_tek(
            "SELECT * FROM alt_kalem_versiyonlar WHERE alt_kalem_id=? AND aktif_mi=1",
            (alt_kalem_id,))
        return dict(row) if row else None

    def urun_versiyon_alt_kalemleri(self, urun_versiyon_id: str) -> list[dict]:
        rows = self.db.getir_hepsi(
            """SELECT akv.*, ak.ad as alt_kalem_adi
               FROM alt_kalem_versiyonlar akv
               JOIN alt_kalemler ak ON ak.id = akv.alt_kalem_id
               WHERE akv.urun_versiyon_id=? AND akv.aktif_mi=1
               ORDER BY ak.ad""",
            (urun_versiyon_id,))
        return [dict(r) for r in rows]

    # ═════════════════════════════════════════
    # ALT KALEM PARAMETRE
    # ═════════════════════════════════════════

    def alt_kalem_parametre_ekle(self, alt_kalem_versiyon_id: str, ad: str,
                                  tip_id: str, zorunlu: bool = False,
                                  varsayilan: str = "",
                                  urun_param_ref_id: str = None,
                                  sira: int = 0) -> str:
        pid = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO alt_kalem_parametreler
                   (id, alt_kalem_versiyon_id, ad, tip_id, zorunlu,
                    varsayilan_deger, urun_param_ref_id, sira)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (pid, alt_kalem_versiyon_id, ad, tip_id, int(zorunlu),
                 varsayilan, urun_param_ref_id, sira))
        return pid

    def alt_kalem_parametreleri(self, alt_kalem_versiyon_id: str) -> list[dict]:
        rows = self.db.getir_hepsi(
            """SELECT akp.*, pt.kod as tip_kod, pt.python_tipi
               FROM alt_kalem_parametreler akp
               JOIN parametre_tipler pt ON pt.id = akp.tip_id
               WHERE akp.alt_kalem_versiyon_id=? AND akp.aktif_mi=1
               ORDER BY akp.sira""",
            (alt_kalem_versiyon_id,))
        return [dict(r) for r in rows]

    # ═════════════════════════════════════════
    # MALİYET ŞABLON
    # ═════════════════════════════════════════

    def maliyet_sablon_olustur(self, alt_kalem_versiyon_id: str,
                                formul: str, kar_orani: float = 0,
                                varsayilan: bool = True) -> str:
        sid = _yeni_uuid()
        with self.db.transaction() as conn:
            if varsayilan:
                conn.execute(
                    """UPDATE maliyet_sablonlar SET varsayilan_formul_mu=0
                       WHERE alt_kalem_versiyon_id=?""",
                    (alt_kalem_versiyon_id,))
            conn.execute(
                """INSERT INTO maliyet_sablonlar
                   (id, alt_kalem_versiyon_id, formul_ifadesi,
                    varsayilan_formul_mu, kar_orani, olusturma_tarihi)
                   VALUES (?,?,?,?,?,?)""",
                (sid, alt_kalem_versiyon_id, formul,
                 int(varsayilan), kar_orani, simdi_iso()))
        return sid

    def aktif_maliyet_sablon(self, alt_kalem_versiyon_id: str) -> dict | None:
        row = self.db.getir_tek(
            """SELECT * FROM maliyet_sablonlar
               WHERE alt_kalem_versiyon_id=? AND aktif_mi=1
                     AND varsayilan_formul_mu=1""",
            (alt_kalem_versiyon_id,))
        return dict(row) if row else None

    def maliyet_sablonlari(self, alt_kalem_versiyon_id: str) -> list[dict]:
        rows = self.db.getir_hepsi(
            """SELECT * FROM maliyet_sablonlar
               WHERE alt_kalem_versiyon_id=?
               ORDER BY olusturma_tarihi DESC""",
            (alt_kalem_versiyon_id,))
        return [dict(r) for r in rows]

    def maliyet_parametre_ekle(self, sablon_id: str, ad: str,
                                degisken: str, varsayilan: float = 0) -> str:
        mid = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO maliyet_parametreler
                   (id, maliyet_sablon_id, ad, degisken_kodu, varsayilan_deger)
                   VALUES (?,?,?,?,?)""",
                (mid, sablon_id, ad, degisken, varsayilan))
        return mid

    def maliyet_parametreleri(self, sablon_id: str) -> list[dict]:
        rows = self.db.getir_hepsi(
            "SELECT * FROM maliyet_parametreler WHERE maliyet_sablon_id=? ORDER BY degisken_kodu",
            (sablon_id,))
        return [dict(r) for r in rows]

    # ═════════════════════════════════════════
    # KONUM FİYAT
    # ═════════════════════════════════════════

    def konum_fiyat_getir(self, ulke: str, sehir: str) -> float:
        row = self.db.getir_tek(
            "SELECT fiyat FROM konum_fiyatlar WHERE ulke=? AND sehir=?",
            (ulke, sehir))
        return row["fiyat"] if row else 0.0

    def konum_fiyat_ekle(self, ulke: str, sehir: str, fiyat: float) -> str:
        kid = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT INTO konum_fiyatlar (id, ulke, sehir, fiyat) VALUES (?,?,?,?)",
                (kid, ulke, sehir, fiyat))
        return kid

    def konum_fiyatlar(self) -> list[dict]:
        rows = self.db.getir_hepsi("SELECT * FROM konum_fiyatlar ORDER BY ulke, sehir")
        return [dict(r) for r in rows]

    # ═════════════════════════════════════════
    # SNAPSHOT
    # ═════════════════════════════════════════

    def snapshot_kaydet(self, snap: dict) -> str:
        sid = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO proje_maliyet_snapshot
                   (id, proje_id, belge_id, revizyon_no, urun_id,
                    urun_versiyon_id, alt_kalem_id, alt_kalem_versiyon_id,
                    parametre_degerleri, formul_ifadesi,
                    birim_fiyat, miktar, toplam_fiyat,
                    kar_orani, konum_fiyat, opsiyon_mu, olusturma_yili,
                    olusturma_tarihi)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (sid, snap["proje_id"], snap.get("belge_id"),
                 snap.get("revizyon_no", 1), snap["urun_id"],
                 snap["urun_versiyon_id"], snap["alt_kalem_id"],
                 snap["alt_kalem_versiyon_id"],
                 json.dumps(snap.get("parametre_degerleri", {}), ensure_ascii=False),
                 snap.get("formul_ifadesi", "0"),
                 snap.get("birim_fiyat", 0), snap.get("miktar", 1),
                 snap.get("toplam_fiyat", 0), snap.get("kar_orani", 0),
                 snap.get("konum_fiyat", 0), int(snap.get("opsiyon_mu", False)),
                 snap.get("olusturma_yili", 2026), simdi_iso()))
        return sid

    def proje_snapshotlari(self, proje_id: str, revizyon_no: int = None) -> list[dict]:
        if revizyon_no:
            rows = self.db.getir_hepsi(
                "SELECT * FROM proje_maliyet_snapshot WHERE proje_id=? AND revizyon_no=? ORDER BY olusturma_tarihi",
                (proje_id, revizyon_no))
        else:
            rows = self.db.getir_hepsi(
                "SELECT * FROM proje_maliyet_snapshot WHERE proje_id=? ORDER BY revizyon_no, olusturma_tarihi",
                (proje_id,))
        return [dict(r) for r in rows]

    # ═════════════════════════════════════════
    # VERSİYON ZİNCİRİ KOPYALAMA
    # ═════════════════════════════════════════

    def urun_versiyon_kopyala(self, urun_id: str) -> str:
        """Yeni ürün versiyonu oluştur ve mevcut parametreleri + alt kalemleri kopyala."""
        eski_ver = self.aktif_urun_versiyon(urun_id)
        yeni_ver_id = self.urun_versiyon_olustur(urun_id)

        if eski_ver:
            # Parametreleri kopyala
            for p in self.urun_parametreleri(eski_ver["id"]):
                self.urun_parametre_ekle(yeni_ver_id, p["ad"], p["tip_id"],
                                          bool(p["zorunlu"]), p["varsayilan_deger"], p["sira"])
            # Alt kalemleri kopyala
            for akv in self.urun_versiyon_alt_kalemleri(eski_ver["id"]):
                yeni_akv_id = self.alt_kalem_versiyon_olustur(
                    akv["alt_kalem_id"], yeni_ver_id)
                # Alt kalem parametreleri kopyala
                for akp in self.alt_kalem_parametreleri(akv["id"]):
                    self.alt_kalem_parametre_ekle(
                        yeni_akv_id, akp["ad"], akp["tip_id"],
                        bool(akp["zorunlu"]), akp["varsayilan_deger"],
                        akp.get("urun_param_ref_id"), akp["sira"])
                # Maliyet şablonları kopyala
                for ms in self.maliyet_sablonlari(akv["id"]):
                    yeni_ms_id = self.maliyet_sablon_olustur(
                        yeni_akv_id, ms["formul_ifadesi"],
                        ms["kar_orani"], bool(ms["varsayilan_formul_mu"]))
                    for mp in self.maliyet_parametreleri(ms["id"]):
                        self.maliyet_parametre_ekle(
                            yeni_ms_id, mp["ad"], mp["degisken_kodu"],
                            mp["varsayilan_deger"])

        logger.info(f"Ürün versiyon kopyalandı: {urun_id[:8]} → {yeni_ver_id[:8]}")
        return yeni_ver_id
