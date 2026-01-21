"""
Fiyat Formatlayıcı Modülü
=========================

Türk para birimi formatı (xxx.xxx.xxx,xx) için merkezi yönetim sistemi.

Bu modül, uygulamadaki tüm fiyat verilerinin standart bir formatta
işlenmesini sağlar:
- Girdi: Kullanıcıdan gelen çeşitli formatlar (1256, 1256.8, 1256,8)
- İşlem: Python float
- Çıktı: Türk formatı (1.256,80)

Özellikler:
-----------
- Otomatik format algılama ve dönüştürme
- Türk para birimi formatı doğrulama
- QLineEdit için özel validator
- Thread-safe işlemler
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Optional, Union


class FiyatFormatlayici:
    """
    Türk para birimi formatı yöneticisi.
    
    Format Standardı:
    -----------------
    xxx.xxx.xxx,xx
    - "." : Binlik ayırıcı
    - "," : Ondalık ayırıcı
    - İki ondalık basamak zorunlu
    
    Örnekler:
    ---------
    >>> FiyatFormatlayici.float_to_turk_format(1256.8)
    '1.256,80'
    >>> FiyatFormatlayici.turk_format_to_float("1.256,80")
    1256.8
    >>> FiyatFormatlayici.normalize("1256,8")
    '1.256,80'
    """
    
    # Regex desenleri
    _TURK_FORMAT_PATTERN = re.compile(
        r'^-?\d{1,3}(?:\.\d{3})*,\d{2}$'
    )
    
    @staticmethod
    def float_to_turk_format(
        deger: Union[float, int, Decimal, str],
        ondalik_basamak: int = 2
    ) -> str:
        """
        Float değeri Türk para formatına çevirir.
        
        Parametreler:
        -------------
        deger : Union[float, int, Decimal, str]
            Dönüştürülecek değer
        ondalik_basamak : int, optional
            Ondalık basamak sayısı (varsayılan: 2)
        
        Döndürür:
        ---------
        str
            Türk formatında fiyat (örn: "1.256,80")
        
        Örnekler:
        ---------
        >>> FiyatFormatlayici.float_to_turk_format(1256.8)
        '1.256,80'
        >>> FiyatFormatlayici.float_to_turk_format(0)
        '0,00'
        >>> FiyatFormatlayici.float_to_turk_format(-1256.8)
        '-1.256,80'
        """
        # Önce float'a çevir
        try:
            if isinstance(deger, str):
                deger_float = FiyatFormatlayici.turk_format_to_float(deger)
            else:
                deger_float = float(deger)
        except (ValueError, TypeError):
            return f"0,{'0' * ondalik_basamak}"
        
        # Negatif kontrolü
        negatif = deger_float < 0
        deger_float = abs(deger_float)
        
        # Decimal kullanarak kesin hesaplama
        deger_decimal = Decimal(str(deger_float))
        
        # Ondalık basamağa yuvarla
        format_str = f"0.{'0' * ondalik_basamak}"
        yuvarlanmis = deger_decimal.quantize(Decimal(format_str))
        
        # String'e çevir ve parçala
        deger_str = str(yuvarlanmis)
        
        if '.' in deger_str:
            tamsayi, ondalik = deger_str.split('.')
        else:
            tamsayi = deger_str
            ondalik = '0' * ondalik_basamak
        
        # Ondalık kısmını düzenle (yetersizse sıfır ekle)
        ondalik = ondalik.ljust(ondalik_basamak, '0')[:ondalik_basamak]
        
        # Binlik ayırıcı ekle
        tamsayi_formatli = FiyatFormatlayici._binlik_ayirici_ekle(tamsayi)
        
        # Birleştir
        sonuc = f"{tamsayi_formatli},{ondalik}"
        
        # Negatif işareti ekle
        if negatif:
            sonuc = f"-{sonuc}"
        
        return sonuc
    
    @staticmethod
    def _binlik_ayirici_ekle(sayi_str: str) -> str:
        """
        Tam sayıya binlik ayırıcı ekler.
        
        Parametreler:
        -------------
        sayi_str : str
            Tam sayı string'i
        
        Döndürür:
        ---------
        str
            Binlik ayırıcılı string
        
        Örnekler:
        ---------
        >>> FiyatFormatlayici._binlik_ayirici_ekle("1256")
        '1.256'
        >>> FiyatFormatlayici._binlik_ayirici_ekle("1256789")
        '1.256.789'
        """
        # Ters çevir, 3'lü grupla, tekrar ters çevir
        ters = sayi_str[::-1]
        gruplar = [ters[i:i+3] for i in range(0, len(ters), 3)]
        return '.'.join(gruplar)[::-1]
    
    @staticmethod
    def turk_format_to_float(metin: str) -> float:
        """
        Türk formatındaki string'i float'a çevirir.
        
        Esnek Girdi:
        ------------
        - "1.256,80" → 1256.8
        - "1256,80"  → 1256.8
        - "1.256"    → 1256.0
        - "1256"     → 1256.0
        - "1256.8"   → 1256.8 (İngiliz formatı da kabul edilir)
        - ""         → 0.0
        - "abc"      → 0.0
        
        Parametreler:
        -------------
        metin : str
            Dönüştürülecek metin
        
        Döndürür:
        ---------
        float
            Float değer (hata durumunda 0.0)
        """
        # Boş kontrol
        if not metin or not isinstance(metin, str):
            return 0.0
        
        # Temizle
        metin = metin.strip().replace(' ', '')
        
        if not metin:
            return 0.0
        
        try:
            # Negatif kontrolü
            negatif = metin.startswith('-')
            if negatif:
                metin = metin[1:]
            
            # Virgül ve nokta sayısını kontrol et
            virgul_sayisi = metin.count(',')
            nokta_sayisi = metin.count('.')
            
            # Durum 1: Sadece virgül var (Türk formatı - ondalık)
            # Örnek: "1256,80"
            if virgul_sayisi == 1 and nokta_sayisi == 0:
                sonuc = float(metin.replace(',', '.'))
            
            # Durum 2: Sadece nokta var
            # Alt durum 2a: Binlik ayırıcı (3'lü gruplar) → "1.256"
            # Alt durum 2b: Ondalık ayırıcı (İngiliz formatı) → "1256.8"
            elif virgul_sayisi == 0 and nokta_sayisi > 0:
                parcalar = metin.split('.')
                
                # Eğer son parça 3 haneden az veya ilk parça 3'ten büyükse
                # muhtemelen İngiliz formatı
                if len(parcalar[-1]) < 3 or len(parcalar[0]) > 3:
                    # İngiliz formatı: "1256.8"
                    sonuc = float(metin)
                else:
                    # Türk formatı binlik: "1.256" → "1256"
                    sonuc = float(metin.replace('.', ''))
            
            # Durum 3: Hem virgül hem nokta var (Tam Türk formatı)
            # Örnek: "1.256,80"
            elif virgul_sayisi == 1 and nokta_sayisi > 0:
                # Binlik ayırıcıları sil, virgülü noktaya çevir
                sonuc = float(metin.replace('.', '').replace(',', '.'))
            
            # Durum 4: Sadece rakam (binlik/ondalık yok)
            # Örnek: "1256"
            elif virgul_sayisi == 0 and nokta_sayisi == 0:
                sonuc = float(metin)
            
            else:
                # Beklenmeyen format
                return 0.0
            
            return -sonuc if negatif else sonuc
            
        except (ValueError, AttributeError):
            return 0.0
    
    @staticmethod
    def validate_turk_format(metin: str) -> bool:
        """
        Metnin Türk formatına tam uygun olup olmadığını kontrol eder.
        
        Strict kontrol - tam format gerekir:
        - xxx.xxx.xxx,xx
        
        Parametreler:
        -------------
        metin : str
            Kontrol edilecek metin
        
        Döndürür:
        ---------
        bool
            Format uygunsa True
        
        Örnekler:
        ---------
        >>> FiyatFormatlayici.validate_turk_format("1.256,80")
        True
        >>> FiyatFormatlayici.validate_turk_format("1256,80")
        False
        >>> FiyatFormatlayici.validate_turk_format("1.256")
        False
        """
        if not metin or not isinstance(metin, str):
            return False
        
        return bool(FiyatFormatlayici._TURK_FORMAT_PATTERN.match(metin.strip()))
    
    @staticmethod
    def normalize(
        metin: str,
        ondalik_basamak: int = 2
    ) -> str:
        """
        Herhangi bir fiyat formatını Türk formatına normalize eder.
        
        Bu fonksiyon girdiyi önce float'a, sonra Türk formatına çevirir.
        
        Parametreler:
        -------------
        metin : str
            Normalize edilecek fiyat metni
        ondalik_basamak : int, optional
            Ondalık basamak sayısı (varsayılan: 2)
        
        Döndürür:
        ---------
        str
            Türk formatında normalize edilmiş fiyat
        
        Örnekler:
        ---------
        >>> FiyatFormatlayici.normalize("1256,8")
        '1.256,80'
        >>> FiyatFormatlayici.normalize("1256.8")
        '1.256,80'
        >>> FiyatFormatlayici.normalize("1256")
        '1.256,00'
        """
        deger_float = FiyatFormatlayici.turk_format_to_float(metin)
        return FiyatFormatlayici.float_to_turk_format(deger_float, ondalik_basamak)
    
    @staticmethod
    def format_para(
        deger: Union[float, int, str],
        sembol: str = "₺",
        ondalik_basamak: int = 2
    ) -> str:
        """
        Fiyatı para birimi sembolü ile birlikte formatlar.
        
        Parametreler:
        -------------
        deger : Union[float, int, str]
            Formatlanacak değer
        sembol : str, optional
            Para birimi sembolü (varsayılan: "₺")
        ondalik_basamak : int, optional
            Ondalık basamak sayısı (varsayılan: 2)
        
        Döndürür:
        ---------
        str
            Para birimi sembolü ile formatlanmış fiyat
        
        Örnekler:
        ---------
        >>> FiyatFormatlayici.format_para(1256.8)
        '1.256,80 ₺'
        >>> FiyatFormatlayici.format_para(1256.8, "$")
        '1.256,80 $'
        """
        formatli = FiyatFormatlayici.float_to_turk_format(deger, ondalik_basamak)
        return f"{formatli} {sembol}"
    
    @staticmethod
    def guvenli_float_donustur(metin: str) -> float:
        """
        Esnek float dönüşümü - hata durumunda 0.0 döner.
        
        Not: Bu fonksiyon turk_format_to_float() ile aynı işlevi görür.
        Geriye dönük uyumluluk için bırakılmıştır.
        
        Parametreler:
        -------------
        metin : str
            Dönüştürülecek metin
        
        Döndürür:
        ---------
        float
            Float değer (hata durumunda 0.0)
        """
        return FiyatFormatlayici.turk_format_to_float(metin)


# =============================================================================
# Yardımcı Fonksiyonlar (Modül Seviyesi)
# =============================================================================

def para_formatla(
    deger: Union[float, int, str],
    sembol: str = "₺"
) -> str:
    """
    Kısa yol: Para formatı.
    
    Örnekler:
    ---------
    >>> para_formatla(1256.8)
    '1.256,80 ₺'
    """
    return FiyatFormatlayici.format_para(deger, sembol)


def normalize_fiyat(metin: str) -> str:
    """
    Kısa yol: Fiyat normalize etme.
    
    Örnekler:
    ---------
    >>> normalize_fiyat("1256,8")
    '1.256,80'
    """
    return FiyatFormatlayici.normalize(metin)


def fiyat_to_float(metin: str) -> float:
    """
    Kısa yol: Fiyat string'ini float'a çevirme.
    
    Örnekler:
    ---------
    >>> fiyat_to_float("1.256,80")
    1256.8
    """
    return FiyatFormatlayici.turk_format_to_float(metin)
