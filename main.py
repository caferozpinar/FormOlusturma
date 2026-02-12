#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proje Yönetim Sistemi — Ana Giriş Noktası.
Veritabanı, migration, servisler ve UI burada başlatılır.

Varsayılan giriş bilgileri:
  Kullanıcı: admin
  Şifre: admin123
"""

import sys
import os

from PyQt5.QtWidgets import QApplication

# Proje kök dizinini Python path'ine ekle
PROJE_KOKU = os.path.dirname(os.path.abspath(__file__))
if PROJE_KOKU not in sys.path:
    sys.path.insert(0, PROJE_KOKU)

from uygulama.altyapi.veritabani import Veritabani
from uygulama.altyapi.migration import MigrationMotoru
from uygulama.altyapi.kullanici_repo import KullaniciRepository
from uygulama.altyapi.proje_repo import ProjeRepository
from uygulama.altyapi.log_repo import LogRepository
from uygulama.servisler.kimlik_servisi import KimlikServisi
from uygulama.servisler.proje_servisi import ProjeServisi
from uygulama.ortak.app_state import app_state
from uygulama.arayuz.stiller import STYLESHEET
from uygulama.arayuz.ana_pencere import AnaPencere
from uygulama.ortak.yardimcilar import logger_olustur

logger = logger_olustur("main")


def baslat():
    """Uygulamayı başlatır."""

    # ── 1. Veritabanı ──
    db_yolu = os.path.join(PROJE_KOKU, "veri", "proje_yonetimi.db")
    db = Veritabani(db_yolu)
    db.baglan()
    logger.info(f"Veritabanı: {db_yolu}")

    # ── 2. Migration ──
    migration = MigrationMotoru(db)
    uygulanan = migration.uygula()
    if uygulanan > 0:
        logger.info(f"{uygulanan} migration uygulandı.")

    # ── 3. Repository'ler ──
    kullanici_repo = KullaniciRepository(db)
    proje_repo = ProjeRepository(db)
    log_repo = LogRepository(db)

    # ── 4. Servisler ──
    kimlik_servisi = KimlikServisi(kullanici_repo, log_repo)
    proje_servisi = ProjeServisi(proje_repo, log_repo)

    # ── 5. Varsayılan admin ──
    kimlik_servisi.varsayilan_admin_olustur()

    # ── 6. App State ──
    state = app_state()
    state.db_yolu = db_yolu

    # ── 7. UI Başlat ──
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    app.setStyle("Fusion")

    pencere = AnaPencere(kimlik_servisi, proje_servisi, log_repo)
    pencere.show()

    logger.info("Uygulama başlatıldı.")
    logger.info("Varsayılan giriş: admin / admin123")

    kod = app.exec_()

    # ── 8. Temizlik ──
    db.kapat()
    logger.info("Uygulama kapatıldı.")
    sys.exit(kod)


if __name__ == "__main__":
    baslat()
