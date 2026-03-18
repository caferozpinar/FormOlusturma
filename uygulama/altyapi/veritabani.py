#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite Veritabanı Bağlantı Yöneticisi.
WAL mode, foreign key desteği, connection pooling.
"""

import sqlite3
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from uygulama.ortak.yardimcilar import logger_olustur

logger = logger_olustur("veritabani")


class Veritabani:
    """SQLite veritabanı bağlantı yöneticisi."""

    def __init__(self, db_yolu: str):
        self.db_yolu = db_yolu
        self._baglanti: Optional[sqlite3.Connection] = None

        # Dizini oluştur
        Path(os.path.dirname(db_yolu)).mkdir(parents=True, exist_ok=True)

    def baglan(self) -> sqlite3.Connection:
        """Veritabanına bağlan veya mevcut bağlantıyı döndür."""
        if self._baglanti is None:
            self._baglanti = sqlite3.connect(self.db_yolu)
            self._baglanti.row_factory = sqlite3.Row
            self._baglanti.execute("PRAGMA journal_mode=WAL")
            self._baglanti.execute("PRAGMA foreign_keys=ON")
            self._baglanti.execute("PRAGMA busy_timeout=5000")
            logger.info(f"Veritabanı bağlantısı açıldı: {self.db_yolu}")
        return self._baglanti

    def kapat(self):
        """Bağlantıyı kapat."""
        if self._baglanti:
            self._baglanti.close()
            self._baglanti = None
            logger.info("Veritabanı bağlantısı kapatıldı.")

    @contextmanager
    def transaction(self):
        """
        Transaction context manager.
        Hata olursa rollback, başarılıysa commit.
        """
        conn = self.baglan()
        try:
            yield conn
            conn.commit()
        except sqlite3.IntegrityError as integrity_err:
            conn.rollback()
            logger.error(
                f"Transaction Integrity hatası (rollback yapıldı):\n"
                f"Hata: {type(integrity_err).__name__}\n"
                f"Detay: {integrity_err}"
            )
            raise
        except sqlite3.DatabaseError as db_err:
            conn.rollback()
            logger.error(
                f"Transaction Veritabanı hatası (rollback yapıldı):\n"
                f"Hata: {type(db_err).__name__}\n"
                f"Detay: {db_err}"
            )
            raise
        except Exception as e:
            conn.rollback()
            logger.error(
                f"Transaction hatası (rollback yapıldı): {type(e).__name__}\n"
                f"Detay: {e}"
            )
            raise

    def calistir(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Tek bir SQL çalıştır."""
        conn = self.baglan()
        return conn.execute(sql, params)

    def calistir_coklu(self, sql: str, params_listesi: list) -> None:
        """Birden fazla parametre seti ile SQL çalıştır."""
        conn = self.baglan()
        conn.executemany(sql, params_listesi)
        conn.commit()

    def getir_tek(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Tek satır getir."""
        cursor = self.calistir(sql, params)
        return cursor.fetchone()

    def getir_hepsi(self, sql: str, params: tuple = ()) -> list:
        """Tüm satırları getir."""
        cursor = self.calistir(sql, params)
        return cursor.fetchall()
