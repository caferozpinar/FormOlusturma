"""
FileReader.py - Geriye Uyumluluk Wrapper
========================================

Bu dosya eski import'ların çalışması için bir wrapper'dır.

Yeni kullanım:
>>> from uygulama.veri.urun_yukleyici import urun_listesi_al
>>> urunler = urun_listesi_al()

Eski kullanım (hala çalışır):
>>> import FileReader
>>> FileReader.items()
"""

from uygulama.veri.urun_yukleyici import (
    urun_listesi_al,
    items,
    config_deger_oku as extract_value_from_file,
)

__all__ = ["extract_value_from_file", "items", "urun_listesi_al"]
