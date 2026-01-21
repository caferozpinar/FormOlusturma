"""
Yardımcılar Modülü Testleri
===========================

uygulama/yardimcilar/ altındaki modüllerin birim testleri.

Çalıştırma:
-----------
pytest testler/test_yardimcilar.py -v
"""

import pytest
from datetime import date


class TestDonusturucular:
    """Dönüştürücü fonksiyonlarının testleri."""
    
    def test_guvenli_float_donustur_gecerli(self):
        """Geçerli float değerleri doğru dönüştürülmeli."""
        from uygulama.yardimcilar.donusturucular import guvenli_float_donustur
        
        assert guvenli_float_donustur("123.45") == 123.45
        assert guvenli_float_donustur("100") == 100.0
        assert guvenli_float_donustur("-50.5") == -50.5
        assert guvenli_float_donustur("  42.5  ") == 42.5
    
    def test_guvenli_float_donustur_gecersiz(self):
        """Geçersiz değerler varsayılan döndürmeli."""
        from uygulama.yardimcilar.donusturucular import guvenli_float_donustur
        
        assert guvenli_float_donustur("abc") == 0.0
        assert guvenli_float_donustur("") == 0.0
        assert guvenli_float_donustur("  ") == 0.0
        assert guvenli_float_donustur(None) == 0.0
        assert guvenli_float_donustur("12.34.56") == 0.0
    
    def test_guvenli_float_donustur_varsayilan(self):
        """Özel varsayılan değer kullanılmalı."""
        from uygulama.yardimcilar.donusturucular import guvenli_float_donustur
        
        assert guvenli_float_donustur("abc", varsayilan=-1.0) == -1.0
        assert guvenli_float_donustur("", varsayilan=99.9) == 99.9
    
    def test_guvenli_int_donustur_gecerli(self):
        """Geçerli int değerleri doğru dönüştürülmeli."""
        from uygulama.yardimcilar.donusturucular import guvenli_int_donustur
        
        assert guvenli_int_donustur("123") == 123
        assert guvenli_int_donustur("-50") == -50
        assert guvenli_int_donustur("  42  ") == 42
        assert guvenli_int_donustur("12.7") == 12  # Float yuvarlanmalı
    
    def test_guvenli_int_donustur_gecersiz(self):
        """Geçersiz değerler varsayılan döndürmeli."""
        from uygulama.yardimcilar.donusturucular import guvenli_int_donustur
        
        assert guvenli_int_donustur("abc") == 0
        assert guvenli_int_donustur("") == 0
        assert guvenli_int_donustur(None) == 0
    
    def test_turkce_karakterleri_temizle(self):
        """Türkçe karakterler ASCII'ye dönüştürülmeli."""
        from uygulama.yardimcilar.donusturucular import turkce_karakterleri_temizle
        
        assert turkce_karakterleri_temizle("Türkçe") == "Turkce"
        assert turkce_karakterleri_temizle("çğıöşü") == "cgiosu"
        assert turkce_karakterleri_temizle("ÇĞİÖŞÜ") == "CGIOSU"
        assert turkce_karakterleri_temizle("Test123") == "Test123"
        assert turkce_karakterleri_temizle(None) == ""
    
    def test_guvenli_dosya_adi(self):
        """Dosya adları güvenli formata dönüştürülmeli."""
        from uygulama.yardimcilar.donusturucular import guvenli_dosya_adi
        
        assert guvenli_dosya_adi("Proje Raporu") == "Proje_Raporu"
        assert guvenli_dosya_adi("Şirket/Ürün") == "Sirket_Urun"
        assert guvenli_dosya_adi("Test:123") == "Test_123"
        assert guvenli_dosya_adi("  Boşluk  ") == "Bosluk"
        assert guvenli_dosya_adi(None) == ""


class TestDogrulayicilar:
    """Doğrulayıcı fonksiyonlarının testleri."""
    
    def test_tarih_dogrula_gecerli(self):
        """Geçerli tarihler kabul edilmeli."""
        from uygulama.yardimcilar.dogrulayicilar import tarih_dogrula
        
        basarili, tarih, hata = tarih_dogrula(2024, 1, 15)
        assert basarili is True
        assert tarih == date(2024, 1, 15)
        assert hata == ""
        
        # Artık yıl
        basarili, tarih, hata = tarih_dogrula(2024, 2, 29)
        assert basarili is True
        assert tarih == date(2024, 2, 29)
    
    def test_tarih_dogrula_gecersiz_yil(self):
        """Geçersiz yıllar reddedilmeli."""
        from uygulama.yardimcilar.dogrulayicilar import tarih_dogrula
        
        basarili, tarih, hata = tarih_dogrula(1800, 1, 1)
        assert basarili is False
        assert tarih is None
        assert "yıl" in hata.lower()
        
        basarili, tarih, hata = tarih_dogrula(2200, 1, 1)
        assert basarili is False
    
    def test_tarih_dogrula_gecersiz_ay(self):
        """Geçersiz aylar reddedilmeli."""
        from uygulama.yardimcilar.dogrulayicilar import tarih_dogrula
        
        basarili, tarih, hata = tarih_dogrula(2024, 0, 1)
        assert basarili is False
        assert "ay" in hata.lower()
        
        basarili, tarih, hata = tarih_dogrula(2024, 13, 1)
        assert basarili is False
    
    def test_tarih_dogrula_gecersiz_gun(self):
        """Geçersiz günler reddedilmeli."""
        from uygulama.yardimcilar.dogrulayicilar import tarih_dogrula
        
        # 31 Şubat
        basarili, tarih, hata = tarih_dogrula(2024, 2, 31)
        assert basarili is False
        
        # Artık yıl değil, 29 Şubat
        basarili, tarih, hata = tarih_dogrula(2023, 2, 29)
        assert basarili is False
    
    def test_bos_degil_dogrula(self):
        """Boş değer kontrolü çalışmalı."""
        from uygulama.yardimcilar.dogrulayicilar import bos_degil_dogrula
        
        basarili, deger, hata = bos_degil_dogrula("test", "İsim")
        assert basarili is True
        assert deger == "test"
        
        basarili, deger, hata = bos_degil_dogrula("", "İsim")
        assert basarili is False
        assert "İsim" in hata
        
        basarili, deger, hata = bos_degil_dogrula(None, "İsim")
        assert basarili is False
    
    def test_pozitif_sayi_dogrula(self):
        """Pozitif sayı kontrolü çalışmalı."""
        from uygulama.yardimcilar.dogrulayicilar import pozitif_sayi_dogrula
        
        basarili, deger, hata = pozitif_sayi_dogrula("42.5", "Fiyat")
        assert basarili is True
        assert deger == 42.5
        
        basarili, deger, hata = pozitif_sayi_dogrula("-5", "Fiyat")
        assert basarili is False
        
        basarili, deger, hata = pozitif_sayi_dogrula("0", "Adet")
        assert basarili is False
        
        basarili, deger, hata = pozitif_sayi_dogrula("0", "Adet", sifir_dahil=True)
        assert basarili is True


class TestHesaplamalar:
    """Hesaplama fonksiyonlarının testleri."""
    
    def test_satir_toplami_hesapla_gecerli(self):
        """Satır toplamı doğru hesaplanmalı."""
        from uygulama.yardimcilar.hesaplamalar import satir_toplami_hesapla
        
        assert satir_toplami_hesapla("10", "5.5") == 55.0
        assert satir_toplami_hesapla("3", "100") == 300.0
        assert satir_toplami_hesapla("2.5", "4") == 10.0
    
    def test_satir_toplami_hesapla_gecersiz(self):
        """Geçersiz girdiler None döndürmeli."""
        from uygulama.yardimcilar.hesaplamalar import satir_toplami_hesapla
        
        assert satir_toplami_hesapla("0", "100") is None
        assert satir_toplami_hesapla("10", "0") is None
        assert satir_toplami_hesapla("abc", "5") is None
        assert satir_toplami_hesapla("", "") is None
    
    def test_kdvli_toplam_hesapla(self):
        """KDV'li toplam doğru hesaplanmalı."""
        from uygulama.yardimcilar.hesaplamalar import kdvli_toplam_hesapla
        
        assert kdvli_toplam_hesapla(100.0, 18) == 118.0
        assert kdvli_toplam_hesapla(100.0, 20) == 120.0
        assert kdvli_toplam_hesapla(200.0, 10) == 220.0
        assert kdvli_toplam_hesapla(100.0, 0) == 100.0
    
    def test_ebat_metni_olustur(self):
        """Ebat metni doğru oluşturulmalı."""
        from uygulama.yardimcilar.hesaplamalar import ebat_metni_olustur
        
        assert ebat_metni_olustur("100", "200") == "100.0 x 200.0 cm"
        assert ebat_metni_olustur("150.5", "250.5", "mm") == "150.5 x 250.5 mm"
        assert ebat_metni_olustur("abc", "200") == ""
        assert ebat_metni_olustur("0", "200") == ""
    
    def test_ic_ebat_hesapla(self):
        """İç ebat doğru hesaplanmalı."""
        from uygulama.yardimcilar.hesaplamalar import ic_ebat_hesapla
        
        assert ic_ebat_hesapla("100", "200") == "80.0 x 180.0 cm"
        assert ic_ebat_hesapla("100", "200", kenar_payi=10) == "90.0 x 190.0 cm"
        assert ic_ebat_hesapla("30", "30") == ""  # Kenar payından küçük


class TestOturumYoneticisi:
    """OturumYoneticisi sınıfının testleri."""
    
    def test_form_kaydet_ve_al(self):
        """Form verisi kaydedilip alınabilmeli."""
        from uygulama.veri.oturum import OturumYoneticisi
        
        oturum = OturumYoneticisi()
        veri = {"adet_line_1": "10", "fiyat_line_1": "100"}
        
        oturum.form_verisini_kaydet("LK", veri)
        alinan = oturum.form_verisini_al("LK")
        
        assert alinan is not None
        assert alinan["adet_line_1"] == "10"
        assert oturum.form_verisi_var_mi("LK") is True
        assert oturum.form_verisi_var_mi("ZR20") is False
    
    def test_standart_girdi_islemleri(self):
        """Standart girdi işlemleri çalışmalı."""
        from uygulama.veri.oturum import OturumYoneticisi
        
        oturum = OturumYoneticisi()
        
        oturum.standart_girdi_guncelle("PROJEADI", "Test Projesi")
        assert oturum.standart_girdi_al("PROJEADI") == "Test Projesi"
        assert oturum.standart_girdi_al("OLMAYAN", "varsayilan") == "varsayilan"
    
    def test_temizle(self):
        """Oturum temizleme çalışmalı."""
        from uygulama.veri.oturum import OturumYoneticisi
        
        oturum = OturumYoneticisi()
        oturum.form_verisini_kaydet("LK", {"test": "veri"})
        oturum.standart_girdi_guncelle("PROJEADI", "Test")
        
        oturum.temizle()
        
        assert oturum.form_verisini_al("LK") is None
        assert len(oturum.kayitli_form_listesi()) == 0


# =============================================================================
# Test Çalıştırma
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
