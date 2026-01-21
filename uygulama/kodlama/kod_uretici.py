"""
Kod Üretici Modülü
==================

Belge ve proje kodları üretimi.

Bu modül, form verilerinden benzersiz takip kodları
üretmek için fonksiyonlar sağlar.

Format: IDX1|I=il|U=ulke|F=firma|R=rev|PE=urun1:ebat1,...
"""

from __future__ import annotations

import logging
from typing import Any

# Modül günlükleyicisi
gunluk = logging.getLogger(__name__)


def _kacis_karakteri_ekle(metin: str) -> str:
    """
    Özel karakterleri URL-safe formata dönüştürür.
    
    Parametreler:
    -------------
    metin : str
        Dönüştürülecek metin
    
    Döndürür:
    ---------
    str
        Kaçış karakterleri eklenmiş metin
    """
    return (metin
            .replace("%", "%25")
            .replace("|", "%7C")
            .replace("=", "%3D")
            .replace(",", "%2C")
            .replace(":", "%3A"))


def _alti_slot_normalize_et(
    degerler: list[Any] | None,
    dolgu: str = "-"
) -> list[str]:
    """
    Değer listesini 6 slota normalize eder.
    
    Parametreler:
    -------------
    degerler : list[Any] | None
        Normalize edilecek değerler
    dolgu : str, optional
        Boş slotlar için dolgu karakteri (varsayılan: "-")
    
    Döndürür:
    ---------
    list[str]
        6 elemanlı normalize edilmiş liste
    """
    degerler = degerler or []
    sonuc = [str(v).strip() for v in degerler]
    
    # Fazlaysa kes
    if len(sonuc) > 6:
        sonuc = sonuc[:6]
    
    # Eksikse doldur
    while len(sonuc) < 6:
        sonuc.append(dolgu)
    
    # Boş stringleri dolgu yap
    sonuc = [v if v else dolgu for v in sonuc]
    
    return sonuc


def kod_uret(yukler: dict[str, Any]) -> str:
    """
    Form verilerinden benzersiz takip kodu üretir.
    
    Kod Formatı:
    ------------
    IDX1|I=il|U=ulke|F=firma|R=revizyon|PE=urun1:ebat1,urun2:ebat2,...
    
    Parametreler:
    -------------
    yukler : dict[str, Any]
        Kod üretimi için gerekli veriler:
        - "il" veya "konum" içinden çıkarılır
        - "ulke" veya "konum" içinden çıkarılır
        - "firma": Firma/düzenleyen adı
        - "rev": Revizyon (03 / R03 / 3 formatında)
        - "urunler": Ürün kodları listesi (max 6)
        - "ebatlar": Ebat listesi (max 6, ürünlerle eşleşir)
    
    Döndürür:
    ---------
    str
        Üretilen kod
    
    Örnekler:
    ---------
    >>> yukler = {
    ...     "konum": "İstanbul / Türkiye",
    ...     "firma": "ABC Ltd",
    ...     "rev": "R01",
    ...     "urunler": ["LK", "ZR20"],
    ...     "ebatlar": ["100x200 cm", "150x250 cm"]
    ... }
    >>> kod_uret(yukler)
    'IDX1|I=İstanbul|U=Türkiye|F=ABC Ltd|R=R01|PE=LK:100x200 cm,ZR20:150x250 cm,...'
    """
    # İl ve ülke çıkarma
    il = str(yukler.get("il") or "").strip()
    ulke = str(yukler.get("ulke") or "").strip()
    
    # Konum alanından çıkarma (İL / ÜLKE formatı)
    if (not il or not ulke) and yukler.get("konum"):
        konum = str(yukler["konum"]).strip()
        if "/" in konum:
            sol, sag = konum.split("/", 1)
            il = il or sol.strip()
            ulke = ulke or sag.strip()
        else:
            il = il or konum
    
    # Firma
    firma = str(yukler.get("firma") or "").strip()
    
    # Revizyon normalizasyonu
    rev_ham = str(yukler.get("rev") or "").strip()
    if rev_ham:
        rev = rev_ham.upper() if rev_ham.upper().startswith("R") else ("R" + rev_ham)
    else:
        rev = "-"
    
    # 6 slota normalize et
    urunler = _alti_slot_normalize_et(yukler.get("urunler"), dolgu="-")
    ebatlar = _alti_slot_normalize_et(yukler.get("ebatlar"), dolgu="-")
    
    # Ürün-Ebat çiftleri oluştur
    ciftler = []
    for urun, ebat in zip(urunler, ebatlar):
        ciftler.append(f"{_kacis_karakteri_ekle(urun)}:{_kacis_karakteri_ekle(ebat)}")
    
    pe = ",".join(ciftler)
    
    # Kod oluştur
    kod = (
        "IDX1"
        f"|I={_kacis_karakteri_ekle(il) if il else '-'}"
        f"|U={_kacis_karakteri_ekle(ulke) if ulke else '-'}"
        f"|F={_kacis_karakteri_ekle(firma) if firma else '-'}"
        f"|R={_kacis_karakteri_ekle(rev)}"
        f"|PE={pe}"
    )
    
    gunluk.debug(f"Kod üretildi: {kod[:50]}...")
    return kod


# =============================================================================
# Geriye Uyumluluk İçin Alias
# =============================================================================

# Eski kod: Coding.GenerateCode(payload)
# Yeni kod: kod_uretici.kod_uret(yukler)
GenerateCode = kod_uret
