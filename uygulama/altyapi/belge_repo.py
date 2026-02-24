#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Belge Oluşturma Repository — Şablon dosyalar, belge türleri,
bölümler, şablon atamaları ve üretim kayıtları CRUD.
"""

import uuid
from uygulama.altyapi.veritabani import Veritabani
from uygulama.ortak.yardimcilar import logger_olustur

logger = logger_olustur("belge_repo")

BOLUM_TURLERI = ("sabit", "urun_bazli", "alt_kalem_bazli", "urun_alt_kalem")


def _id():
    return str(uuid.uuid4())


class BelgeRepository:
    def __init__(self, db: Veritabani):
        self.db = db

    # ═══════════════════════════════════════
    # ŞABLON DOSYALARI
    # ═══════════════════════════════════════

    def sablon_dosya_ekle(self, ad: str, dosya_yolu: str,
                           sheet_adi: str = "Sheet1") -> str:
        sid = _id()
        with self.db.transaction() as c:
            c.execute(
                """INSERT INTO belge_sablon_dosyalar
                   (id, ad, dosya_yolu, sheet_adi) VALUES (?,?,?,?)""",
                (sid, ad, dosya_yolu, sheet_adi))
        logger.info(f"Şablon dosya eklendi: {ad}")
        return sid

    def sablon_dosyalar(self, sadece_aktif: bool = True) -> list[dict]:
        sql = "SELECT * FROM belge_sablon_dosyalar"
        if sadece_aktif:
            sql += " WHERE aktif_mi=1"
        sql += " ORDER BY ad"
        return [dict(r) for r in self.db.getir_hepsi(sql)]

    def sablon_dosya_getir(self, sid: str) -> dict | None:
        r = self.db.getir_tek(
            "SELECT * FROM belge_sablon_dosyalar WHERE id=?", (sid,))
        return dict(r) if r else None

    def sablon_dosya_guncelle(self, sid: str, **kw) -> None:
        allowed = {"ad", "dosya_yolu", "sheet_adi", "aktif_mi"}
        ups, ps = [], []
        for k, v in kw.items():
            if k in allowed:
                ups.append(f"{k}=?"); ps.append(v)
        if ups:
            ps.append(sid)
            with self.db.transaction() as c:
                c.execute(f"UPDATE belge_sablon_dosyalar SET {','.join(ups)} WHERE id=?", ps)

    def sablon_dosya_sil(self, sid: str) -> None:
        with self.db.transaction() as c:
            c.execute("UPDATE belge_sablon_dosyalar SET aktif_mi=0 WHERE id=?", (sid,))

    # ═══════════════════════════════════════
    # BELGE TÜRLERİ
    # ═══════════════════════════════════════

    def belge_turleri(self) -> list[dict]:
        return [dict(r) for r in self.db.getir_hepsi(
            "SELECT * FROM belge_turleri WHERE aktif_mi=1 ORDER BY kod")]

    def belge_turu_getir(self, tid: str) -> dict | None:
        r = self.db.getir_tek("SELECT * FROM belge_turleri WHERE id=?", (tid,))
        return dict(r) if r else None

    def belge_turu_kod_ile(self, kod: str) -> dict | None:
        r = self.db.getir_tek(
            "SELECT * FROM belge_turleri WHERE kod=? AND aktif_mi=1", (kod,))
        return dict(r) if r else None

    def belge_turu_guncelle(self, tid: str, **kw) -> None:
        allowed = {"ad", "sutun_araligi", "aktif_mi"}
        ups, ps = [], []
        for k, v in kw.items():
            if k in allowed:
                ups.append(f"{k}=?"); ps.append(v)
        if ups:
            ps.append(tid)
            with self.db.transaction() as c:
                c.execute(f"UPDATE belge_turleri SET {','.join(ups)} WHERE id=?", ps)

    # ═══════════════════════════════════════
    # BÖLÜMLER
    # ═══════════════════════════════════════

    def bolum_ekle(self, belge_turu_id: str, ad: str,
                    tur: str = "sabit", sira: int = 0) -> str:
        bid = _id()
        with self.db.transaction() as c:
            c.execute(
                """INSERT INTO belge_bolumler
                   (id, belge_turu_id, ad, tur, sira) VALUES (?,?,?,?,?)""",
                (bid, belge_turu_id, ad, tur, sira))
        logger.info(f"Bölüm eklendi: {ad} ({tur})")
        return bid

    def bolumler(self, belge_turu_id: str) -> list[dict]:
        return [dict(r) for r in self.db.getir_hepsi(
            """SELECT * FROM belge_bolumler
               WHERE belge_turu_id=? AND aktif_mi=1 ORDER BY sira""",
            (belge_turu_id,))]

    def bolum_getir(self, bid: str) -> dict | None:
        r = self.db.getir_tek("SELECT * FROM belge_bolumler WHERE id=?", (bid,))
        return dict(r) if r else None

    def bolum_guncelle(self, bid: str, **kw) -> None:
        allowed = {"ad", "tur", "sira", "aktif_mi"}
        ups, ps = [], []
        for k, v in kw.items():
            if k in allowed:
                ups.append(f"{k}=?"); ps.append(v)
        if ups:
            ps.append(bid)
            with self.db.transaction() as c:
                c.execute(f"UPDATE belge_bolumler SET {','.join(ups)} WHERE id=?", ps)

    def bolum_sil(self, bid: str) -> None:
        with self.db.transaction() as c:
            c.execute("UPDATE belge_sablon_atamalari SET aktif_mi=0 WHERE bolum_id=?", (bid,))
            c.execute("UPDATE belge_bolumler SET aktif_mi=0 WHERE id=?", (bid,))

    def bolum_sira_degistir(self, bid: str, yeni_sira: int) -> None:
        with self.db.transaction() as c:
            c.execute("UPDATE belge_bolumler SET sira=? WHERE id=?", (yeni_sira, bid))

    # ═══════════════════════════════════════
    # ŞABLON ATAMALARI
    # ═══════════════════════════════════════

    def atama_ekle(self, bolum_id: str, sablon_dosya_id: str,
                    satir_baslangic: int, satir_bitis: int,
                    urun_id: str = None, alt_kalem_id: str = None,
                    sira: int = 0) -> str:
        aid = _id()
        with self.db.transaction() as c:
            c.execute(
                """INSERT INTO belge_sablon_atamalari
                   (id, bolum_id, sablon_dosya_id, urun_id, alt_kalem_id,
                    satir_baslangic, satir_bitis, sira)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (aid, bolum_id, sablon_dosya_id, urun_id, alt_kalem_id,
                 satir_baslangic, satir_bitis, sira))
        return aid

    def atamalar(self, bolum_id: str) -> list[dict]:
        return [dict(r) for r in self.db.getir_hepsi(
            """SELECT a.*, sd.ad as sablon_adi, sd.dosya_yolu, sd.sheet_adi
               FROM belge_sablon_atamalari a
               JOIN belge_sablon_dosyalar sd ON sd.id = a.sablon_dosya_id
               WHERE a.bolum_id=? AND a.aktif_mi=1
               ORDER BY a.sira""", (bolum_id,))]

    def atama_getir(self, aid: str) -> dict | None:
        r = self.db.getir_tek(
            "SELECT * FROM belge_sablon_atamalari WHERE id=?", (aid,))
        return dict(r) if r else None

    def atama_guncelle(self, aid: str, **kw) -> None:
        allowed = {"sablon_dosya_id", "urun_id", "alt_kalem_id",
                   "satir_baslangic", "satir_bitis", "sira", "aktif_mi"}
        ups, ps = [], []
        for k, v in kw.items():
            if k in allowed:
                ups.append(f"{k}=?"); ps.append(v)
        if ups:
            ps.append(aid)
            with self.db.transaction() as c:
                c.execute(f"UPDATE belge_sablon_atamalari SET {','.join(ups)} WHERE id=?", ps)

    def atama_sil(self, aid: str) -> None:
        with self.db.transaction() as c:
            c.execute("UPDATE belge_sablon_atamalari SET aktif_mi=0 WHERE id=?", (aid,))

    # ═══════════════════════════════════════
    # ÜRETİM KAYITLARI
    # ═══════════════════════════════════════

    def uretim_kaydet(self, teklif_id: str, belge_turu_id: str,
                       dosya_yolu: str, dosya_adi: str,
                       klasor_yolu: str, olusturan: str) -> str:
        uid = _id()
        with self.db.transaction() as c:
            c.execute(
                """INSERT INTO belge_uretim_kayitlari
                   (id, teklif_id, belge_turu_id, dosya_yolu,
                    dosya_adi, klasor_yolu, olusturan)
                   VALUES (?,?,?,?,?,?,?)""",
                (uid, teklif_id, belge_turu_id, dosya_yolu,
                 dosya_adi, klasor_yolu, olusturan))
        logger.info(f"Belge üretim kaydı: {dosya_adi}")
        return uid

    def uretim_kayitlari(self, teklif_id: str) -> list[dict]:
        return [dict(r) for r in self.db.getir_hepsi(
            """SELECT uk.*, bt.kod as belge_turu_kodu, bt.ad as belge_turu_adi
               FROM belge_uretim_kayitlari uk
               JOIN belge_turleri bt ON bt.id = uk.belge_turu_id
               WHERE uk.teklif_id=?
               ORDER BY uk.olusturma_tarihi DESC""", (teklif_id,))]

    def uretim_kaydi_getir(self, uid: str) -> dict | None:
        r = self.db.getir_tek(
            "SELECT * FROM belge_uretim_kayitlari WHERE id=?", (uid,))
        return dict(r) if r else None
