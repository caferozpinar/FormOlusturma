"""
Eşleme Motoru Modülü
====================

Placeholder eşleme kuralları yönetimi.

Bu modül, mapping_rules.txt dosyasından kuralları okuyup
form verilerine uygulayarak placeholder değerlerini üretir.

Desteklenen Kural Formatları:
- field:ALAN_ADI -> Direkt alan değeri
- format:"şablon" using a:alan1, b:alan2 -> Formatlı metin
- if KOSUL then "değer" elif KOSUL2 then "değer2" else "varsayılan"
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

# Modül günlükleyicisi
gunluk = logging.getLogger(__name__)

# =============================================================================
# Regex Desenleri
# =============================================================================

BOLUM_RE = re.compile(r"^\s*\[([A-Za-z0-9_]+)\]\s*$")
KURAL_RE = re.compile(r"^\s*(\{/\s*[A-Za-z0-9_]+\s*/\})\s*=\s*(.+?)\s*$")
FORMAT_RE = re.compile(r'^\s*format\s*:\s*(".*?"|\'.*?\')\s+using\s+(.+?)\s*$')
ALAN_RE = re.compile(r'^\s*field\s*:\s*([A-Za-z0-9_]+)\s*$')
DYNAMIC_RE = re.compile(r"^\s*dynamic\s*:\s*([A-Za-z0-9_]+)\s*$")

def _tirnak_cikar(metin: str) -> str:
    """Metnin etrafındaki tırnak işaretlerini çıkarır."""
    metin = metin.strip()
    if len(metin) >= 2 and metin[0] == metin[-1] and metin[0] in ('"', "'"):
        return metin[1:-1]
    return metin


def _bool_deger_al(kaynak: dict[str, Any], anahtar: str) -> bool:
    """Kaynaktan boolean değer çıkarır."""
    deger = kaynak.get(anahtar, False)
    
    if isinstance(deger, bool):
        return deger
    if isinstance(deger, (int, float)):
        return bool(deger)
    if isinstance(deger, str):
        return deger.strip().lower() in ("1", "true", "evet", "yes", "on")
    
    return False


def _metin_deger_al(kaynak: dict[str, Any], anahtar: str) -> str:
    """Kaynaktan metin değer çıkarır."""
    deger = kaynak.get(anahtar, "")
    return str(deger) if deger is not None else ""


def kurallari_yukle(dosya_yolu: str | Path) -> dict[str, dict[str, str]]:
    """
    Eşleme kurallarını dosyadan yükler.
    
    Dosya Formatı:
    --------------
    [BOLUM_ADI]
    {/PLACEHOLDER/} = kural_ifadesi
    
    Parametreler:
    -------------
    dosya_yolu : str | Path
        Kural dosyası yolu (mapping_rules.txt)
    
    Döndürür:
    ---------
    dict[str, dict[str, str]]
        kurallar[BOLUM][{/PLACEHOLDER/}] = kural_ifadesi
    
    Hatalar:
    --------
    ValueError
        Geçersiz kural satırı bulunursa
    FileNotFoundError
        Dosya bulunamazsa
    """
    dosya_yolu = Path(dosya_yolu)
    
    if not dosya_yolu.exists():
        gunluk.error(f"Kural dosyası bulunamadı: {dosya_yolu}")
        raise FileNotFoundError(f"Kural dosyası bulunamadı: {dosya_yolu}")
    
    metin = dosya_yolu.read_text(encoding="utf-8")
    kurallar: dict[str, dict[str, str]] = {}
    mevcut_bolum = None
    
    for satir_no, ham_satir in enumerate(metin.splitlines(), 1):
        satir = ham_satir.strip()
        
        # Boş satır veya yorum
        if not satir or satir.startswith("#"):
            continue
        
        # Bölüm başlığı
        bolum_eslesmesi = BOLUM_RE.match(satir)
        if bolum_eslesmesi:
            mevcut_bolum = bolum_eslesmesi.group(1)
            kurallar.setdefault(mevcut_bolum, {})
            gunluk.debug(f"Bölüm yüklendi: [{mevcut_bolum}]")
            continue
        
        # Kural satırı
        kural_eslesmesi = KURAL_RE.match(satir)
        if kural_eslesmesi and mevcut_bolum:
            placeholder = kural_eslesmesi.group(1).replace(" ", "")
            ifade = kural_eslesmesi.group(2).strip()
            kurallar[mevcut_bolum][placeholder] = ifade
            continue
        
        # Geçersiz satır
        raise ValueError(f"Kural satırı ayrıştırılamadı (satır {satir_no}): {ham_satir}")
    
    toplam = sum(len(k) for k in kurallar.values())
    gunluk.info(f"Kurallar yüklendi: {len(kurallar)} bölüm, {toplam} kural")
    
    return kurallar


def ifade_degerlendir(ifade: str, kaynak: dict[str, Any]) -> str:
    """
    Tek bir kural ifadesini değerlendirir.
    
    Desteklenen Formatlar:
    ----------------------
    - field:ALAN_ADI
    - format:"şablon {a} {b}" using a:alan1, b:alan2
    - if KOSUL then "değer" else "varsayılan"
    - "sabit metin"
    
    Parametreler:
    -------------
    ifade : str
        Kural ifadesi
    kaynak : dict[str, Any]
        Veri kaynağı (form verileri)
    
    Döndürür:
    ---------
    str
        Değerlendirilmiş sonuç
    """
    # field: formatı
    alan_eslesmesi = ALAN_RE.match(ifade)
    if alan_eslesmesi:
        return _metin_deger_al(kaynak, alan_eslesmesi.group(1))

    dyn_eslesmesi = DYNAMIC_RE.match(ifade)
    if dyn_eslesmesi:
        key = dyn_eslesmesi.group(1)
        dyn = kaynak.get("__dynamic__", {})
        val = dyn.get(key, "")
        return "" if val is None else str(val)

    # format: formatı
    format_eslesmesi = FORMAT_RE.match(ifade)
    if format_eslesmesi:
        sablon = _tirnak_cikar(format_eslesmesi.group(1))
        using_kismi = format_eslesmesi.group(2)
        
        baglam = {}
        parcalar = [p.strip() for p in using_kismi.split(",") if p.strip()]
        
        for parca in parcalar:
            if ":" not in parca:
                continue
            takma_ad, alan_adi = [x.strip() for x in parca.split(":", 1)]
            baglam[takma_ad] = _metin_deger_al(kaynak, alan_adi)
        
        try:
            return sablon.format(**baglam)
        except (KeyError, ValueError):
            return ""
    
    # if ... then ... formatı
    if ifade.strip().startswith("if "):
        return _kosullu_ifade_degerlendir(ifade, kaynak)
    
    # Sabit metin (tırnak içinde)
    return _tirnak_cikar(ifade)


def _kosullu_ifade_degerlendir(ifade: str, kaynak: dict[str, Any]) -> str:
    """
    Koşullu ifadeyi değerlendirir.
    
    Format: if KOSUL then "değer" elif KOSUL2 then "değer2" else "varsayılan"
    """
    tokenlar = ifade.strip().split()
    
    # Minimum: if A then X
    if len(tokenlar) < 4 or tokenlar[0] != "if" or tokenlar[2] != "then":
        return ""
    
    def deger_oku(baslangic: int) -> tuple[str, int]:
        """Token dizisinden değer okur."""
        if baslangic >= len(tokenlar):
            return "", baslangic
        
        t = tokenlar[baslangic]
        
        if t.startswith(("'", '"')):
            # Tırnaklı değer: birleşene kadar topla
            tirnak = t[0]
            parca = [t]
            j = baslangic
            
            while j < len(tokenlar) and not tokenlar[j].endswith(tirnak):
                j += 1
                if j < len(tokenlar):
                    parca.append(tokenlar[j])
            
            deger = " ".join(parca)
            return _tirnak_cikar(deger), j + 1
        else:
            return t, baslangic + 1
    
    # if koşulu
    kosul = tokenlar[1]
    idx = 3
    deger, idx = deger_oku(idx)
    
    if _bool_deger_al(kaynak, kosul):
        return deger
    
    # elif zinciri
    while idx < len(tokenlar) and tokenlar[idx] == "elif":
        if idx + 2 >= len(tokenlar) or tokenlar[idx + 2] != "then":
            return ""
        
        kosul = tokenlar[idx + 1]
        idx = idx + 3
        deger, idx = deger_oku(idx)
        
        if _bool_deger_al(kaynak, kosul):
            return deger
    
    # else
    if idx < len(tokenlar) and tokenlar[idx] == "else":
        idx += 1
        deger, _ = deger_oku(idx)
        return deger
    
    return ""


def placeholder_esleme_olustur(
    urun_kodu: str,
    urun_durumu: dict[str, Any],
    tum_kurallar: dict[str, dict[str, str]]
) -> dict[str, str]:
    """
    Ürün için placeholder eşleme dictionary'si oluşturur.
    
    Parametreler:
    -------------
    urun_kodu : str
        Ürün kodu (örn: "LK", "ZR20")
    urun_durumu : dict[str, Any]
        Ürün form verileri
    tum_kurallar : dict[str, dict[str, str]]
        Yüklenmiş tüm kurallar
    
    Döndürür:
    ---------
    dict[str, str]
        {/PLACEHOLDER/} -> değer eşlemesi
    """
    kurallar = tum_kurallar.get(urun_kodu, {})
    sonuc: dict[str, str] = {}
    
    for placeholder, ifade in kurallar.items():
        sonuc[placeholder] = ifade_degerlendir(ifade, urun_durumu)
    
    gunluk.debug(f"Eşleme oluşturuldu: {urun_kodu} -> {len(sonuc)} placeholder")
    return sonuc


# =============================================================================
# Geriye Uyumluluk İçin Alias'lar
# =============================================================================

# Eski: MappingEngine.load_rules(path)
# Yeni: esleme_motoru.kurallari_yukle(dosya_yolu)
load_rules = kurallari_yukle

# Eski: MappingEngine.eval_expr(expr, src)
# Yeni: esleme_motoru.ifade_degerlendir(ifade, kaynak)
eval_expr = ifade_degerlendir

# Eski: MappingEngine.build_placeholder_mapping(code, state, rules)
# Yeni: esleme_motoru.placeholder_esleme_olustur(urun_kodu, urun_durumu, tum_kurallar)
build_placeholder_mapping = placeholder_esleme_olustur
