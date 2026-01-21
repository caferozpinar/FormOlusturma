"""
Dönüştürücüler Modülü
=====================

Güvenli tip dönüşüm fonksiyonları.

Bu modül, kullanıcı girdilerini güvenli bir şekilde
hedef tiplere dönüştürmek için fonksiyonlar sağlar.
Hatalı girdilerde exception fırlatmak yerine varsayılan
değerler döndürür.

GÜNCELLENDİ: guvenli_float_donustur() artık Türk para formatını destekler.
"""

from __future__ import annotations

import re
from typing import Optional

from uygulama.sabitler import TURKCE_KARAKTER_DONUSUMU

# Fiyat formatlayıcı entegrasyonu
try:
    from uygulama.yardimcilar.fiyat_formatlayici import FiyatFormatlayici
    FIYAT_FORMAT_MEVCUT = True
except ImportError:
    FIYAT_FORMAT_MEVCUT = False


def guvenli_float_donustur(
    metin: str,
    varsayilan: float = 0.0
) -> float:
    """
    Metni güvenli şekilde float'a dönüştürür.

    GÜNCELLENDİ: Artık Türk para formatını destekler!
    - "1.256,80" → 1256.8
    - "1256,80" → 1256.8
    - "1256.8" → 1256.8
    - "1256" → 1256.0

    Boş string, None veya dönüştürülemeyen değerler için
    varsayılan değer döndürür.

    Parametreler:
    -------------
    metin : str
        Dönüştürülecek metin (Türk formatı veya standart float)
    varsayilan : float, optional
        Dönüşüm başarısız olursa kullanılacak değer (varsayılan: 0.0)

    Döndürür:
    ---------
    float
        Dönüştürülen değer veya varsayılan

    Örnekler:
    ---------
    >>> guvenli_float_donustur("123.45")
    123.45
    >>> guvenli_float_donustur("1.256,80")
    1256.8
    >>> guvenli_float_donustur("1256,8")
    1256.8
    >>> guvenli_float_donustur("abc")
    0.0
    >>> guvenli_float_donustur("", varsayilan=-1.0)
    -1.0
    >>> guvenli_float_donustur("  42.5  ")
    42.5
    """
    if metin is None:
        return varsayilan

    try:
        temiz = str(metin).strip()
        if not temiz:
            return varsayilan

        # Eğer FiyatFormatlayici mevcutsa, onu kullan
        # (Türk formatını da destekler)
        if FIYAT_FORMAT_MEVCUT:
            return FiyatFormatlayici.turk_format_to_float(temiz)

        # Fallback: Basit float dönüşümü
        # Türk formatı desteği için basit kontrol
        virgul_sayisi = temiz.count(',')
        nokta_sayisi = temiz.count('.')

        # Türk formatı: "1.256,80" veya "1256,80"
        if virgul_sayisi == 1 and nokta_sayisi >= 0:
            # Binlik ayırıcıları sil, virgülü noktaya çevir
            temiz = temiz.replace('.', '').replace(',', '.')

        return float(temiz)

    except (ValueError, TypeError):
        return varsayilan


def guvenli_int_donustur(
    metin: str,
    varsayilan: int = 0
) -> int:
    """
    Metni güvenli şekilde int'e dönüştürür.

    Boş string, None veya dönüştürülemeyen değerler için
    varsayılan değer döndürür. Float değerler yuvarlanır.

    Parametreler:
    -------------
    metin : str
        Dönüştürülecek metin
    varsayilan : int, optional
        Dönüşüm başarısız olursa kullanılacak değer (varsayılan: 0)

    Döndürür:
    ---------
    int
        Dönüştürülen değer veya varsayılan

    Örnekler:
    ---------
    >>> guvenli_int_donustur("123")
    123
    >>> guvenli_int_donustur("12.7")
    12
    >>> guvenli_int_donustur("abc")
    0
    >>> guvenli_int_donustur("", varsayilan=-1)
    -1
    """
    if metin is None:
        return varsayilan

    try:
        temiz = str(metin).strip()
        if not temiz:
            return varsayilan
        # Önce float'a çevir (ondalıklı sayıları da kabul etmek için)
        return int(float(temiz))
    except (ValueError, TypeError):
        return varsayilan


def turkce_karakterleri_temizle(metin: str) -> str:
    """
    Türkçe karakterleri ASCII eşdeğerlerine dönüştürür.

    Dosya adları ve URL'ler için güvenli metinler oluşturmak
    amacıyla kullanılır.

    Parametreler:
    -------------
    metin : str
        Temizlenecek metin

    Döndürür:
    ---------
    str
        Türkçe karakterler ASCII'ye dönüştürülmüş metin

    Örnekler:
    ---------
    >>> turkce_karakterleri_temizle("Türkçe Öğrenci")
    'Turkce Ogrenci'
    >>> turkce_karakterleri_temizle("çğıöşü")
    'cgiosu'
    """
    if metin is None:
        return ""

    return str(metin).translate(TURKCE_KARAKTER_DONUSUMU)


def guvenli_dosya_adi(
    metin: str,
    bosluk_karakteri: str = "_",
    maksimum_uzunluk: Optional[int] = 100
) -> str:
    """
    Metni güvenli dosya adına dönüştürür.

    - Türkçe karakterleri ASCII'ye çevirir
    - Özel karakterleri kaldırır
    - Boşlukları belirtilen karakterle değiştirir
    - Maksimum uzunluğa göre keser

    Parametreler:
    -------------
    metin : str
        Dönüştürülecek metin
    bosluk_karakteri : str, optional
        Boşlukların yerine kullanılacak karakter (varsayılan: "_")
    maksimum_uzunluk : int, optional
        Maksimum dosya adı uzunluğu (varsayılan: 100)

    Döndürür:
    ---------
    str
        Güvenli dosya adı

    Örnekler:
    ---------
    >>> guvenli_dosya_adi("Proje Raporu 2024")
    'Proje_Raporu_2024'
    >>> guvenli_dosya_adi("Şirket/Ürün:Fiyat")
    'Sirket_Urun_Fiyat'
    """
    if metin is None:
        return ""

    # Türkçe karakterleri temizle
    temiz = turkce_karakterleri_temizle(metin)

    # Sadece alfanumerik, boşluk ve alt çizgi karakterlerini tut
    temiz = re.sub(r"[^A-Za-z0-9_ ]+", "", temiz)

    # Boşlukları değiştir
    temiz = temiz.strip().replace(" ", bosluk_karakteri)

    # Birden fazla alt çizgiyi teke indir
    temiz = re.sub(r"_+", "_", temiz)

    # Maksimum uzunluk kontrolü
    if maksimum_uzunluk and len(temiz) > maksimum_uzunluk:
        temiz = temiz[:maksimum_uzunluk]

    return temiz


def metin_veya_varsayilan(
    deger: any,
    varsayilan: str = ""
) -> str:
    """
    Herhangi bir değeri metne dönüştürür, None için varsayılan döndürür.

    Parametreler:
    -------------
    deger : any
        Dönüştürülecek değer
    varsayilan : str, optional
        None veya boş değer için döndürülecek metin (varsayılan: "")

    Döndürür:
    ---------
    str
        Metin değeri veya varsayılan
    """
    if deger is None:
        return varsayilan

    metin = str(deger).strip()
    return metin if metin else varsayilan
