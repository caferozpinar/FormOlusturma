#!/usr/bin/env python3
"""
Form Oluşturma Uygulaması - Ana Giriş Noktası
=============================================

Bu dosya uygulamanın giriş noktasıdır.
Tüm iş mantığı uygulama/ paketi altındadır.

Kullanım:
---------
    python main.py

Yazar: Form Oluşturma Ekibi
Sürüm: 2.0.0
"""

import sys
import logging

from PyQt5 import QtWidgets

from uygulama import AnaPencere, oturum, yapilandirma, __version__
from uygulama.pencereler.giris_penceresi import GirisPenceresi


def gunlukleyici_ayarla() -> logging.Logger:
    """Uygulama günlükleyicisini yapılandırır."""
    gunlukleyici = logging.getLogger("FormUygulamasi")
    gunlukleyici.setLevel(logging.DEBUG)
    
    # Konsol handler
    if not gunlukleyici.handlers:
        konsol = logging.StreamHandler()
        konsol.setLevel(logging.INFO)
        
        bicim = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        konsol.setFormatter(bicim)
        gunlukleyici.addHandler(konsol)
    
    return gunlukleyici


def main() -> int:
    """
    Uygulamanın ana giriş noktası.
    
    Returns:
        Çıkış kodu (0 = başarılı)
    """
    # Günlükleyiciyi ayarla
    gunluk = gunlukleyici_ayarla()
    
    gunluk.info("=" * 60)
    gunluk.info(f"Form Oluşturma Uygulaması v{__version__} başlatılıyor...")
    gunluk.info("=" * 60)
    
    # Gerekli dizinleri oluştur
    yapilandirma.dizinleri_olustur()
    
    # Qt uygulaması oluştur
    uygulama = QtWidgets.QApplication(sys.argv)
    
    # ÖNEMLİ: Kullanıcı girişi kontrolü
    gunluk.info("Kullanıcı girişi bekleniyor...")
    giris_sonucu = GirisPenceresi.giris_kontrolu()
    
    # Giriş iptal edildiyse uygulamayı kapat
    if giris_sonucu is None:
        gunluk.info("Kullanıcı girişi iptal edildi")
        return 0
    
    # Kullanıcı bilgilerini ayır
    kullanici_adi, gercek_ad = giris_sonucu
    
    gunluk.info(f"Kullanıcı girişi başarılı: {kullanici_adi} ({gercek_ad})")
    
    # Kullanıcı bilgilerini oturuma kaydet
    oturum.kullanici_adi = kullanici_adi
    oturum.gercek_ad = gercek_ad
    
    # Ana pencereyi oluştur ve göster
    pencere = AnaPencere(oturum, yapilandirma)
    pencere.show()
    
    gunluk.info("Ana pencere gösterildi")
    
    # Uygulama döngüsünü başlat
    cikis_kodu = uygulama.exec_()
    
    gunluk.info(f"Uygulama kapatıldı (çıkış kodu: {cikis_kodu})")
    return cikis_kodu


if __name__ == "__main__":
    sys.exit(main())
