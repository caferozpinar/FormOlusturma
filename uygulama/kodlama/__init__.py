"""
Kodlama Paketi
==============

Belge ve proje kodları üretimi.

Kullanım:
---------
>>> from uygulama.kodlama import kod_uret
>>> kod = kod_uret({"konum": "İstanbul / Türkiye", ...})
"""

from uygulama.kodlama.kod_uretici import kod_uret, GenerateCode

__all__ = [
    "kod_uret",
    "GenerateCode",  # Geriye uyumluluk
]
