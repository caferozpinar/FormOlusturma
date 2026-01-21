"""
Belge Paketi
============

Belge oluşturma ve şablon işlemleri.

Modüller:
---------
- olusturucu: Ana belge oluşturma fonksiyonu
- sablon_islemleri: Şablon placeholder değiştirme ve birleştirme
- yardimcilar: Yardımcı fonksiyonlar
- log_yoneticisi: Log yönetimi

Kullanım:
---------
>>> from uygulama.belge import teklif_formu_olustur
>>> cikti = teklif_formu_olustur(urun_kodlari=["LK", "ZR20"], ...)
"""

from .fiyat_tablosu import fiyat_tablosu_uret_ve_doldur
from uygulama.belge.olusturucu import teklif_formu_olustur, build_offer_form
from uygulama.belge.kesif_ozeti_olusturucu import kesif_ozeti_olustur
from uygulama.belge.sablon_islemleri import (
    belgede_placeholder_degistir,
    gecici_dosyaya_render_et,
    belgeleri_birlestir,
    global_placeholder_uygula,
)
from uygulama.belge.yardimcilar import (
    config_deger_oku,
    urun_basliklarini_yukle,
    basliklari_turkce_birlestir,
    guvenli_dosya_adi_olustur,
)
from uygulama.belge.log_yoneticisi import LogYoneticisi

__all__ = [
    # Ana fonksiyonlar
    "teklif_formu_olustur",
    "kesif_ozeti_olustur",
    "build_offer_form",
    # Şablon işlemleri
    "belgede_placeholder_degistir",
    "gecici_dosyaya_render_et",
    "belgeleri_birlestir",
    "global_placeholder_uygula",
    # Fiyat tablosu
    "fiyat_tablosu_uret_ve_doldur",
    # Yardımcılar
    "config_deger_oku",
    "urun_basliklarini_yukle",
    "basliklari_turkce_birlestir",
    "guvenli_dosya_adi_olustur",
    # Log
    "LogYoneticisi",
]
