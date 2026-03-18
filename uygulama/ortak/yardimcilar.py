#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ortak yardımcı fonksiyonlar.
"""

import hashlib
import logging
import os
import sys
from datetime import datetime
from pathlib import Path


# ─────────────────────────────────────────────
# UYGULAMA DİZİNİ
# ─────────────────────────────────────────────

def uygulama_dizini() -> str:
    """
    Uygulamanın kullanıcı veri dizinini döndürür.
    Frozen (exe) modda: FormOlusturma.exe'nin bulunduğu klasör.
    Dev modda: proje kökü (bu dosyadan 2 seviye yukarı).
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─────────────────────────────────────────────
# LOGLAMA
# ─────────────────────────────────────────────

def logger_olustur(ad: str, log_dizini: str = "") -> logging.Logger:
    """Modül bazlı logger oluşturur."""
    if not log_dizini:
        log_dizini = os.path.join(uygulama_dizini(), "loglar")
    Path(log_dizini).mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(ad)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # Dosya handler
    dosya_adi = os.path.join(log_dizini, f"{datetime.now():%Y-%m-%d}.log")
    fh = logging.FileHandler(dosya_adi, encoding="utf-8")
    fh.setLevel(logging.DEBUG)

    # Konsol handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S"
    )
    fh.setFormatter(fmt)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


# ─────────────────────────────────────────────
# HASH ÜRETİMİ
# ─────────────────────────────────────────────

def proje_hash_uret(firma: str, konum: str, tesis: str, urun_seti: str = "") -> str:
    """
    Proje için 6 karakterlik deterministik hash üretir.
    firma + konum + tesis + urun_seti birleşiminden.
    Aynı veriler → HER ZAMAN aynı hash (timestamp yok).
    Yalnızca büyük harfler ve rakamlardan oluşur.
    """
    kaynak = f"{firma}|{konum}|{tesis}|{urun_seti}"
    tam_hash = hashlib.sha256(kaynak.encode("utf-8")).hexdigest()
    # Sadece büyük harfler (A-Z) ve rakamlar (0-9) kullanılır; özel karakterler ve küçük harfler hariç tutulur,
    # böylece hash kolay okunur ve dosya/dizin adlarında güvenle kullanılabilir.
    hash_temiz = "".join(c for c in tam_hash.upper() if c.isalnum())
    return hash_temiz[:6]


# ─────────────────────────────────────────────
# TARİH YARDIMCILARI
# ─────────────────────────────────────────────

def simdi_iso() -> str:
    """Şu anki zamanı ISO formatında döndürür."""
    return datetime.now().isoformat()


def tarih_formatla(iso_str: str, fmt: str = "%d.%m.%Y %H:%M") -> str:
    """ISO tarih stringini okunabilir formata çevirir."""
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime(fmt)
    except (ValueError, TypeError):
        return iso_str or ""


def tarih_sadece_gun(iso_str: str) -> str:
    """ISO tarih stringinden sadece gün döndürür."""
    return tarih_formatla(iso_str, "%d.%m.%Y")
