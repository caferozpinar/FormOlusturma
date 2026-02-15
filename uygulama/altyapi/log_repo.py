#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hareket Log Repository — Genişletilmiş audit log."""

import json
from uygulama.altyapi.veritabani import Veritabani
from uygulama.domain.modeller import HareketLogu
from uygulama.ortak.yardimcilar import logger_olustur

logger = logger_olustur("log_repo")


class LogRepository:
    def __init__(self, db: Veritabani):
        self.db = db

    def kaydet(self, log: HareketLogu) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO hareket_loglari
                   (id, kullanici_id, islem, hedef_tablo, hedef_id, detay, tarih)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (log.id, log.kullanici_id, log.islem.value,
                 log.hedef_tablo, log.hedef_id, log.detay, log.tarih))

    def hedef_icin_getir(self, hedef_tablo: str, hedef_id: str, limit: int = 50) -> list[dict]:
        rows = self.db.getir_hepsi(
            """SELECT l.*, k.kullanici_adi FROM hareket_loglari l
               LEFT JOIN kullanicilar k ON k.id = l.kullanici_id
               WHERE l.hedef_tablo = ? AND l.hedef_id = ?
               ORDER BY l.tarih DESC LIMIT ?""",
            (hedef_tablo, hedef_id, limit))
        return [dict(r) for r in rows]

    def son_loglar(self, limit: int = 100) -> list[dict]:
        rows = self.db.getir_hepsi(
            """SELECT l.*, k.kullanici_adi FROM hareket_loglari l
               LEFT JOIN kullanicilar k ON k.id = l.kullanici_id
               ORDER BY l.tarih DESC LIMIT ?""", (limit,))
        return [dict(r) for r in rows]

    def kullanici_loglari(self, kullanici_id: str, limit: int = 100) -> list[dict]:
        rows = self.db.getir_hepsi(
            """SELECT l.*, k.kullanici_adi FROM hareket_loglari l
               LEFT JOIN kullanicilar k ON k.id = l.kullanici_id
               WHERE l.kullanici_id = ? ORDER BY l.tarih DESC LIMIT ?""",
            (kullanici_id, limit))
        return [dict(r) for r in rows]

    def filtreli_getir(self, islem: str = None, hedef_tablo: str = None,
                        kullanici_id: str = None, baslangic: str = None,
                        bitis: str = None, arama: str = None,
                        limit: int = 200) -> list[dict]:
        sql = """SELECT l.*, k.kullanici_adi FROM hareket_loglari l
                 LEFT JOIN kullanicilar k ON k.id = l.kullanici_id WHERE 1=1"""
        params = []
        if islem: sql += " AND l.islem = ?"; params.append(islem)
        if hedef_tablo: sql += " AND l.hedef_tablo = ?"; params.append(hedef_tablo)
        if kullanici_id: sql += " AND l.kullanici_id = ?"; params.append(kullanici_id)
        if baslangic: sql += " AND l.tarih >= ?"; params.append(baslangic)
        if bitis: sql += " AND l.tarih <= ?"; params.append(bitis)
        if arama: sql += " AND l.detay LIKE ?"; params.append(f"%{arama}%")
        sql += " ORDER BY l.tarih DESC LIMIT ?"
        params.append(limit)
        rows = self.db.getir_hepsi(sql, tuple(params))
        return [dict(r) for r in rows]

    def islem_istatistikleri(self, gun_sayisi: int = 30) -> list[dict]:
        rows = self.db.getir_hepsi(
            """SELECT islem, COUNT(*) as sayi FROM hareket_loglari
               WHERE tarih >= datetime('now', ? || ' days')
               GROUP BY islem ORDER BY sayi DESC""",
            (f"-{gun_sayisi}",))
        return [dict(r) for r in rows]

    def kullanici_aktivite(self, gun_sayisi: int = 30) -> list[dict]:
        rows = self.db.getir_hepsi(
            """SELECT k.kullanici_adi, COUNT(*) as islem_sayisi,
                      MAX(l.tarih) as son_islem
               FROM hareket_loglari l
               LEFT JOIN kullanicilar k ON k.id = l.kullanici_id
               WHERE l.tarih >= datetime('now', ? || ' days')
               GROUP BY l.kullanici_id ORDER BY islem_sayisi DESC""",
            (f"-{gun_sayisi}",))
        return [dict(r) for r in rows]

    def gunluk_ozet(self, gun_sayisi: int = 7) -> list[dict]:
        rows = self.db.getir_hepsi(
            """SELECT DATE(tarih) as gun, COUNT(*) as sayi FROM hareket_loglari
               WHERE tarih >= datetime('now', ? || ' days')
               GROUP BY DATE(tarih) ORDER BY gun DESC""",
            (f"-{gun_sayisi}",))
        return [dict(r) for r in rows]

    def toplam_log_sayisi(self) -> int:
        row = self.db.getir_tek("SELECT COUNT(*) as c FROM hareket_loglari")
        return row["c"] if row else 0

    def yetki_reddi_loglari(self, limit: int = 50) -> list[dict]:
        return self.filtreli_getir(islem="YETKI_REDDEDILDI", limit=limit)

    def json_aktar(self, limit: int = 1000) -> str:
        return json.dumps(self.son_loglar(limit), ensure_ascii=False, indent=2, default=str)

    def csv_satirlari(self, limit: int = 1000) -> list[str]:
        loglar = self.son_loglar(limit)
        satirlar = ["tarih;kullanici;islem;tablo;detay"]
        for l in loglar:
            satirlar.append(f"{l.get('tarih','')};{l.get('kullanici_adi','')}"
                f";{l.get('islem','')};{l.get('hedef_tablo','')};{l.get('detay','')}")
        return satirlar
