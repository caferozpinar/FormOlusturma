"""
Form Oluşturma Uygulaması
=========================

PyQt5 tabanlı profesyonel form ve belge oluşturma uygulaması.

Modüller:
---------
- pencereler: UI pencere sınıfları
- veri: Oturum ve yapılandırma yönetimi
- yardimcilar: Yardımcı fonksiyonlar
- belge: Belge oluşturma işlemleri (Aşama 3'te eklenecek)
- kodlama: Kod üretimi (Aşama 3'te eklenecek)
- esleme: Placeholder eşleme (Aşama 3'te eklenecek)

Kullanım:
---------
>>> from uygulama import AnaPencere, oturum, yapilandirma
>>> pencere = AnaPencere(oturum, yapilandirma)
>>> pencere.show()
"""

__version__ = "2.0.0"
__author__ = "Form Oluşturma Ekibi"

# =============================================================================
# Veri Modülleri
# =============================================================================

from uygulama.veri.oturum import OturumYoneticisi, oturum
from uygulama.veri.yapilandirma import YapilandirmaYoneticisi, yapilandirma

# =============================================================================
# Pencere Modülleri
# =============================================================================

from uygulama.pencereler.ana_pencere import AnaPencere
from uygulama.pencereler.urun_penceresi import UrunPenceresi

# =============================================================================
# Dışa Aktarılan Nesneler
# =============================================================================

__all__ = [
    # Pencereler
    "AnaPencere",
    "UrunPenceresi",
    # Veri sınıfları
    "OturumYoneticisi",
    "YapilandirmaYoneticisi",
    # Global nesneler
    "oturum",
    "yapilandirma",
    # Meta
    "__version__",
    "__author__",
]
