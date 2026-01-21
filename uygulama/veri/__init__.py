"""
Veri Yönetim Modülü
===================

Belge önbelleği, yapılandırma yönetimi ve veri yükleme.
"""

from .belge_onbellegi import BelgeOnbellegi
from .urun_yukleyici import urun_listesi_al, items

__all__ = [
    'BelgeOnbellegi',
    'urun_listesi_al',
    'items',  # Geriye uyumluluk
]
