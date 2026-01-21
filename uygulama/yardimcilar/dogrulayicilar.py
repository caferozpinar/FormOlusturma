"""
Doğrulayıcılar Modülü
=====================

Veri doğrulama fonksiyonları.

Bu modül, kullanıcı girdilerini doğrulamak için
fonksiyonlar sağlar. Her fonksiyon (başarılı, sonuç, hata_mesaji)
tuple'ı döndürür.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional, Any, Tuple

from uygulama.sabitler import (
    MINIMUM_YIL,
    MAKSIMUM_YIL,
    HATA_MESAJLARI,
)


@dataclass
class DogrulamaHatasi:
    """Doğrulama hatası detayları."""
    alan: str
    mesaj: str
    deger: Any = None


def tarih_dogrula(
    yil: int,
    ay: int,
    gun: int
) -> Tuple[bool, Optional[date], str]:
    """
    Tarih değerlerini doğrular ve date nesnesi oluşturur.
    
    Parametreler:
    -------------
    yil : int
        Yıl değeri (1900-2100 arası)
    ay : int
        Ay değeri (1-12 arası)
    gun : int
        Gün değeri (1-31 arası)
    
    Döndürür:
    ---------
    tuple[bool, Optional[date], str]
        (başarılı, tarih_nesnesi, hata_mesaji)
        - başarılı: Doğrulama geçti mi
        - tarih_nesnesi: Oluşturulan date nesnesi (başarısızsa None)
        - hata_mesaji: Hata açıklaması (başarılıysa boş string)
    
    Örnekler:
    ---------
    >>> tarih_dogrula(2024, 2, 29)  # Artık yıl
    (True, date(2024, 2, 29), '')
    
    >>> tarih_dogrula(2023, 2, 29)  # Artık yıl değil
    (False, None, 'Geçersiz tarih: day is out of range for month')
    
    >>> tarih_dogrula(1800, 1, 1)  # Geçersiz yıl
    (False, None, 'Geçersiz yıl: 1800. 1900-2100 arasında olmalı.')
    """
    # Yıl kontrolü
    if not (MINIMUM_YIL <= yil <= MAKSIMUM_YIL):
        mesaj = HATA_MESAJLARI["GECERSIZ_YIL"].format(
            yil=yil,
            min=MINIMUM_YIL,
            max=MAKSIMUM_YIL
        )
        return False, None, mesaj
    
    # Ay kontrolü
    if not (1 <= ay <= 12):
        mesaj = HATA_MESAJLARI["GECERSIZ_AY"].format(ay=ay)
        return False, None, mesaj
    
    # Gün kontrolü (temel)
    if not (1 <= gun <= 31):
        mesaj = HATA_MESAJLARI["GECERSIZ_GUN"].format(gun=gun)
        return False, None, mesaj
    
    # date nesnesi oluşturmayı dene (31 Şubat gibi durumları yakalar)
    try:
        tarih = date(yil, ay, gun)
        return True, tarih, ""
    except ValueError as e:
        mesaj = HATA_MESAJLARI["GECERSIZ_TARIH"].format(tarih=str(e))
        return False, None, mesaj


def bos_degil_dogrula(
    deger: Any,
    alan_adi: str = "Değer"
) -> Tuple[bool, str, str]:
    """
    Değerin boş olmadığını doğrular.
    
    Parametreler:
    -------------
    deger : Any
        Kontrol edilecek değer
    alan_adi : str, optional
        Hata mesajında kullanılacak alan adı (varsayılan: "Değer")
    
    Döndürür:
    ---------
    tuple[bool, str, str]
        (başarılı, temiz_deger, hata_mesaji)
    
    Örnekler:
    ---------
    >>> bos_degil_dogrula("test", "İsim")
    (True, 'test', '')
    
    >>> bos_degil_dogrula("", "İsim")
    (False, '', 'İsim boş olamaz.')
    
    >>> bos_degil_dogrula(None, "İsim")
    (False, '', 'İsim boş olamaz.')
    """
    if deger is None:
        return False, "", f"{alan_adi} boş olamaz."
    
    metin = str(deger).strip()
    
    if not metin:
        return False, "", f"{alan_adi} boş olamaz."
    
    return True, metin, ""


def pozitif_sayi_dogrula(
    deger: Any,
    alan_adi: str = "Değer",
    sifir_dahil: bool = False
) -> Tuple[bool, float, str]:
    """
    Değerin pozitif sayı olduğunu doğrular.
    
    Parametreler:
    -------------
    deger : Any
        Kontrol edilecek değer
    alan_adi : str, optional
        Hata mesajında kullanılacak alan adı (varsayılan: "Değer")
    sifir_dahil : bool, optional
        Sıfırın geçerli kabul edilip edilmeyeceği (varsayılan: False)
    
    Döndürür:
    ---------
    tuple[bool, float, str]
        (başarılı, sayi_degeri, hata_mesaji)
    
    Örnekler:
    ---------
    >>> pozitif_sayi_dogrula("42.5", "Fiyat")
    (True, 42.5, '')
    
    >>> pozitif_sayi_dogrula("-5", "Fiyat")
    (False, 0.0, 'Fiyat pozitif bir sayı olmalıdır.')
    
    >>> pozitif_sayi_dogrula("0", "Adet", sifir_dahil=True)
    (True, 0.0, '')
    """
    if deger is None:
        return False, 0.0, f"{alan_adi} boş olamaz."
    
    try:
        sayi = float(str(deger).strip())
    except (ValueError, TypeError):
        return False, 0.0, f"{alan_adi} geçerli bir sayı olmalıdır."
    
    if sifir_dahil:
        if sayi < 0:
            return False, 0.0, f"{alan_adi} negatif olamaz."
    else:
        if sayi <= 0:
            return False, 0.0, f"{alan_adi} pozitif bir sayı olmalıdır."
    
    return True, sayi, ""


def aralik_dogrula(
    deger: Any,
    minimum: float,
    maksimum: float,
    alan_adi: str = "Değer"
) -> Tuple[bool, float, str]:
    """
    Değerin belirtilen aralıkta olduğunu doğrular.
    
    Parametreler:
    -------------
    deger : Any
        Kontrol edilecek değer
    minimum : float
        Minimum kabul edilen değer (dahil)
    maksimum : float
        Maksimum kabul edilen değer (dahil)
    alan_adi : str, optional
        Hata mesajında kullanılacak alan adı (varsayılan: "Değer")
    
    Döndürür:
    ---------
    tuple[bool, float, str]
        (başarılı, sayi_degeri, hata_mesaji)
    
    Örnekler:
    ---------
    >>> aralik_dogrula("50", 0, 100, "Yüzde")
    (True, 50.0, '')
    
    >>> aralik_dogrula("150", 0, 100, "Yüzde")
    (False, 0.0, 'Yüzde 0-100 arasında olmalıdır.')
    """
    if deger is None:
        return False, 0.0, f"{alan_adi} boş olamaz."
    
    try:
        sayi = float(str(deger).strip())
    except (ValueError, TypeError):
        return False, 0.0, f"{alan_adi} geçerli bir sayı olmalıdır."
    
    if not (minimum <= sayi <= maksimum):
        return False, 0.0, f"{alan_adi} {minimum}-{maksimum} arasında olmalıdır."
    
    return True, sayi, ""


def coklu_dogrula(
    dogrulamalar: list[Tuple[bool, Any, str]]
) -> Tuple[bool, list[str]]:
    """
    Birden fazla doğrulama sonucunu birleştirir.
    
    Parametreler:
    -------------
    dogrulamalar : list[tuple[bool, Any, str]]
        Doğrulama sonuçları listesi
    
    Döndürür:
    ---------
    tuple[bool, list[str]]
        (tumu_basarili, hata_mesajlari_listesi)
    
    Örnekler:
    ---------
    >>> dogrulamalar = [
    ...     tarih_dogrula(2024, 1, 15),
    ...     bos_degil_dogrula("test"),
    ...     pozitif_sayi_dogrula("10"),
    ... ]
    >>> coklu_dogrula(dogrulamalar)
    (True, [])
    """
    hatalar = []
    
    for basarili, _, mesaj in dogrulamalar:
        if not basarili and mesaj:
            hatalar.append(mesaj)
    
    return len(hatalar) == 0, hatalar
