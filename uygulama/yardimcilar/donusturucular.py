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
    if metin is None:
        return varsayilan

    temiz = str(metin).strip()
    if not temiz:
        return varsayilan

    try:
        if FIYAT_FORMAT_MEVCUT:
            deger = FiyatFormatlayici.turk_format_to_float(temiz)
            # KRİTİK: dönüşüm başarısızsa varsayılana dön
            return deger if deger != 0.0 or temiz in ("0", "0.0", "0,0") else varsayilan

        # fallback
        virgul_sayisi = temiz.count(',')
        nokta_sayisi = temiz.count('.')

        if virgul_sayisi == 1:
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

    # Ayraçları ve boşlukları _ yap
    temiz = re.sub(r"[\/\\:\s]+", bosluk_karakteri, temiz)

    # Geri kalan özel karakterleri sil
    temiz = re.sub(r"[^A-Za-z0-9_]+", "", temiz)

    # Boşlukları değiştir
    temiz = temiz.strip().replace(" ", bosluk_karakteri)

    # Birden fazla alt çizgiyi teke indir
    temiz = re.sub(r"_+", "_", temiz)

    # Başta ve sonda kalan alt çizgileri temizle
    temiz = temiz.strip(bosluk_karakteri)

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
