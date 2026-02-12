#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hareket Log Repository — Audit log veritabanı işlemleri.
"""

from typing import Optional

from uygulama.altyapi.veritabani import Veritabani
from uygulama.domain.modeller import HareketLogu, IslemTipi
from uygulama.ortak.yardimcilar import logger_olustur

logger = logger_olustur("log_repo")


class LogRepository:
    """Hareket logları veritabanı işlemleri."""

    def __init__(self, db: Veritabani):
        self.db = db

    def kaydet(self, log: HareketLogu) -> None:
        """Log kaydı oluşturur."""
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO hareket_loglari
                   (id, kullanici_id, islem, hedef_tablo, hedef_id, detay, tarih)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    log.id, log.kullanici_id, log.islem.value,
                    log.hedef_tablo, log.hedef_id, log.detay, log.tarih
                )
            )

    def hedef_icin_getir(self, hedef_tablo: str, hedef_id: str,
                         limit: int = 50) -> list[dict]:
        """Belirli bir hedef için logları getirir."""
        rows = self.db.getir_hepsi(
            """SELECT l.*, k.kullanici_adi
               FROM hareket_loglari l
               JOIN kullanicilar k ON k.id = l.kullanici_id
               WHERE l.hedef_tablo = ? AND l.hedef_id = ?
               ORDER BY l.tarih DESC
               LIMIT ?""",
            (hedef_tablo, hedef_id, limit)
        )
        return [dict(r) for r in rows]

    def son_loglar(self, limit: int = 100) -> list[dict]:
        """Son logları getirir."""
        rows = self.db.getir_hepsi(
            """SELECT l.*, k.kullanici_adi
               FROM hareket_loglari l
               JOIN kullanicilar k ON k.id = l.kullanici_id
               ORDER BY l.tarih DESC
               LIMIT ?""",
            (limit,)
        )
        return [dict(r) for r in rows]
