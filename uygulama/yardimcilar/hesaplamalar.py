"""
Hesaplamalar Modülü
===================

Matematiksel hesaplama fonksiyonları.

Bu modül, form hesaplamaları için kullanılan
matematiksel fonksiyonları içerir.

GÜNCELLENDİ: Artık FiyatFormatlayici ile entegre edilmiştir.
Tüm hesaplamalar Türk para formatını destekler.
"""

from __future__ import annotations

from typing import Optional

from uygulama.yardimcilar.donusturucular import guvenli_float_donustur
from uygulama.sabitler import VARSAYILAN_KENAR_PAYI

# Fiyat formatlayıcı entegrasyonu
try:
    from uygulama.yardimcilar.fiyat_formatlayici import FiyatFormatlayici
    FIYAT_FORMAT_MEVCUT = True
except ImportError:
    FIYAT_FORMAT_MEVCUT = False


def satir_toplami_hesapla(
    adet: str,
    birim_fiyat: str
) -> Optional[float]:
    """
    Satır toplamını hesaplar (adet × birim fiyat).

    GÜNCELLENDİ: Artık Türk para formatını destekler.
    - adet: "10" veya "10,5" (Türk formatı)
    - birim_fiyat: "1.256,80" veya "1256.8" (her format kabul edilir)

    Parametreler:
    -------------
    adet : str
        Adet değeri (metin olarak, Türk formatı kabul edilir)
    birim_fiyat : str
        Birim fiyat değeri (metin olarak, Türk formatı kabul edilir)

    Döndürür:
    ---------
    Optional[float]
        Hesaplanan toplam veya None (geçersiz girdi durumunda)

    Örnekler:
    ---------
    >>> satir_toplami_hesapla("10", "5.5")
    55.0
    >>> satir_toplami_hesapla("10", "1.256,80")
    12568.0
    >>> satir_toplami_hesapla("0", "100")
    None
    >>> satir_toplami_hesapla("abc", "5")
    None
    """
    # guvenli_float_donustur artık Türk formatını destekler
    adet_f = guvenli_float_donustur(adet)
    fiyat_f = guvenli_float_donustur(birim_fiyat)

    # Her iki değer de pozitif olmalı
    if adet_f > 0 and fiyat_f > 0:
        return adet_f * fiyat_f

    return None


def kdvli_toplam_hesapla(
    ara_toplam: float,
    kdv_orani: float
) -> float:
    """
    KDV dahil toplam hesaplar.

    Parametreler:
    -------------
    ara_toplam : float
        KDV öncesi toplam
    kdv_orani : float
        KDV oranı (yüzde olarak, örn: 18 veya 20)

    Döndürür:
    ---------
    float
        KDV dahil toplam

    Örnekler:
    ---------
    >>> kdvli_toplam_hesapla(100.0, 18)
    118.0
    >>> kdvli_toplam_hesapla(200.0, 20)
    240.0
    >>> kdvli_toplam_hesapla(100.0, 0)
    100.0
    """
    if ara_toplam <= 0:
        return 0.0

    if kdv_orani < 0:
        kdv_orani = 0.0

    kdv_tutari = (ara_toplam / 100) * kdv_orani
    return ara_toplam + kdv_tutari


def kdv_tutari_hesapla(
    ara_toplam: float,
    kdv_orani: float
) -> float:
    """
    Sadece KDV tutarını hesaplar.

    Parametreler:
    -------------
    ara_toplam : float
        KDV öncesi toplam
    kdv_orani : float
        KDV oranı (yüzde olarak)

    Döndürür:
    ---------
    float
        KDV tutarı

    Örnekler:
    ---------
    >>> kdv_tutari_hesapla(100.0, 18)
    18.0
    """
    if ara_toplam <= 0 or kdv_orani <= 0:
        return 0.0

    return (ara_toplam / 100) * kdv_orani


def ebat_metni_olustur(
    en: str,
    boy: str,
    birim: str = "cm"
) -> str:
    """
    En ve boy değerlerinden ebat metni oluşturur.

    GÜNCELLENDİ: Türk formatını destekler ve formatlanmış çıktı verir.

    Parametreler:
    -------------
    en : str
        En değeri (metin olarak, Türk formatı kabul edilir)
    boy : str
        Boy değeri (metin olarak, Türk formatı kabul edilir)
    birim : str, optional
        Ölçü birimi (varsayılan: "cm")

    Döndürür:
    ---------
    str
        Formatlanmış ebat metni veya boş string (geçersiz girdi)

    Örnekler:
    ---------
    >>> ebat_metni_olustur("100", "200")
    '100 x 200 cm'
    >>> ebat_metni_olustur("150,5", "250,5", "mm")
    '150,5 x 250,5 mm'
    >>> ebat_metni_olustur("abc", "200")
    ''
    """
    en_f = guvenli_float_donustur(en)
    boy_f = guvenli_float_donustur(boy)

    if en_f > 0 and boy_f > 0:
        # Türk formatında göster (eğer FiyatFormatlayici mevcutsa)
        if FIYAT_FORMAT_MEVCUT:
            # Ondalık kısmı varsa göster, yoksa tam sayı olarak
            en_str = _format_olcu_degeri(en_f)
            boy_str = _format_olcu_degeri(boy_f)
            return f"{en_str} x {boy_str} {birim}"
        else:
            # Fallback: Basit formatla
            return f"{en_f} x {boy_f} {birim}"

    return ""


def _format_olcu_degeri(deger: float) -> str:
    """
    Ölçü değerini formatlar (iç yardımcı fonksiyon).

    - 100.0 → "100"
    - 150.5 → "150,5"
    - 150.75 → "150,75"
    """
    if deger == int(deger):
        return str(int(deger))
    else:
        # Türk formatına çevir ama binlik ayırıcı olmadan
        deger_str = str(deger).replace('.', ',')
        return deger_str


def ic_ebat_hesapla(
    en: str,
    boy: str,
    kenar_payi: float = VARSAYILAN_KENAR_PAYI,
    birim: str = "cm"
) -> str:
    """
    İç ebat hesaplar (dış ebattan kenar payı çıkararak).

    GÜNCELLENDİ: Türk formatını destekler.

    Parametreler:
    -------------
    en : str
        Dış en değeri (metin olarak, Türk formatı kabul edilir)
    boy : str
        Dış boy değeri (metin olarak, Türk formatı kabul edilir)
    kenar_payi : float, optional
        Her kenardan çıkarılacak pay (varsayılan: 20.0)
    birim : str, optional
        Ölçü birimi (varsayılan: "cm")

    Döndürür:
    ---------
    str
        Formatlanmış iç ebat metni veya boş string

    Örnekler:
    ---------
    >>> ic_ebat_hesapla("100", "200")
    '80 x 180 cm'
    >>> ic_ebat_hesapla("100", "200", kenar_payi=10)
    '90 x 190 cm'
    >>> ic_ebat_hesapla("30", "30")  # Kenar payından küçük
    ''
    """
    en_f = guvenli_float_donustur(en)
    boy_f = guvenli_float_donustur(boy)

    # Kenar payından büyük olmalı
    if en_f > kenar_payi and boy_f > kenar_payi:
        ic_en = en_f - kenar_payi
        ic_boy = boy_f - kenar_payi

        # Formatla
        if FIYAT_FORMAT_MEVCUT:
            ic_en_str = _format_olcu_degeri(ic_en)
            ic_boy_str = _format_olcu_degeri(ic_boy)
            return f"{ic_en_str} x {ic_boy_str} {birim}"
        else:
            return f"{ic_en} x {ic_boy} {birim}"

    return ""


def yuzde_hesapla(
    deger: float,
    toplam: float
) -> float:
    """
    Bir değerin toplama göre yüzdesini hesaplar.

    Parametreler:
    -------------
    deger : float
        Yüzdesi hesaplanacak değer
    toplam : float
        Toplam değer (100% olarak kabul edilir)

    Döndürür:
    ---------
    float
        Yüzde değeri (0-100 arası)

    Örnekler:
    ---------
    >>> yuzde_hesapla(25, 100)
    25.0
    >>> yuzde_hesapla(50, 200)
    25.0
    """
    if toplam <= 0:
        return 0.0

    return (deger / toplam) * 100


def yuvarla(
    deger: float,
    basamak: int = 2
) -> float:
    """
    Değeri belirtilen ondalık basamağa yuvarlar.

    Parametreler:
    -------------
    deger : float
        Yuvarlanacak değer
    basamak : int, optional
        Ondalık basamak sayısı (varsayılan: 2)

    Döndürür:
    ---------
    float
        Yuvarlanmış değer

    Örnekler:
    ---------
    >>> yuvarla(3.14159, 2)
    3.14
    >>> yuvarla(3.14159, 4)
    3.1416
    """
    return round(deger, basamak)


def coklu_satir_toplami_hesapla(
    satirlar: list[tuple[str, str]]
) -> float:
    """
    Birden fazla satırın toplamını hesaplar.

    GÜNCELLENDİ: Türk formatını destekler.

    Parametreler:
    -------------
    satirlar : list[tuple[str, str]]
        (adet, birim_fiyat) tuple'larından oluşan liste
        Her iki değer de Türk formatında olabilir

    Döndürür:
    ---------
    float
        Tüm satırların toplamı

    Örnekler:
    ---------
    >>> satirlar = [("10", "5"), ("20", "3"), ("5", "10")]
    >>> coklu_satir_toplami_hesapla(satirlar)
    160.0
    >>> satirlar = [("10", "1.256,80"), ("5", "500,00")]
    >>> coklu_satir_toplami_hesapla(satirlar)
    15068.0
    """
    toplam = 0.0

    for adet, fiyat in satirlar:
        satir_toplam = satir_toplami_hesapla(adet, fiyat)
        if satir_toplam is not None:
            toplam += satir_toplam

    return toplam


def fiyat_formatla_turk(deger: float) -> str:
    """
    Float değeri Türk para formatına çevirir.

    YENI FONKSİYON: Hesaplama sonuçlarını formatlamak için.

    Parametreler:
    -------------
    deger : float
        Formatlanacak değer

    Döndürür:
    ---------
    str
        Türk formatında fiyat (xxx.xxx.xxx,xx)

    Örnekler:
    ---------
    >>> fiyat_formatla_turk(1256.8)
    '1.256,80'
    >>> fiyat_formatla_turk(12568.0)
    '12.568,00'
    """
    if FIYAT_FORMAT_MEVCUT:
        return FiyatFormatlayici.float_to_turk_format(deger)
    else:
        # Fallback: Basit formatla
        return f"{deger:.2f}".replace('.', ',')
