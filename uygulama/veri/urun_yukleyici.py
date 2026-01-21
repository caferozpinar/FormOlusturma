"""
Ürün Yükleyici Modülü
=====================

Ürün listesini CSV dosyasından yükler.

Bu modül eski FileReader.py'ın modernize edilmiş halidir.

Kullanım:
---------
>>> from uygulama.veri.urun_yukleyici import urun_listesi_al
>>> urunler = urun_listesi_al()
"""

import csv
import re
from pathlib import Path
from typing import Optional


def _kok_dizin_al() -> Path:
    """Kök dizini döndürür (import döngüsünü önlemek için)."""
    return Path(__file__).parent.parent.parent


def _varsayilan_urun_listesi_yolu() -> Path:
    """Varsayılan ürün listesi yolunu döndürür."""
    return _kok_dizin_al() / "kaynaklar" / "veriler" / "UrunListesi.csv"


def config_deger_oku(config_yolu: Path, anahtar: str) -> Optional[str]:
    """
    Config dosyasından değer okur.
    
    Parametreler:
    -------------
    config_yolu : Path
        Config dosyası yolu
    anahtar : str
        Aranacak anahtar (örn: "{{URUN_LISTESI}}")
    
    Döndürür:
    ---------
    Optional[str]
        Bulunan değer veya None
    """
    try:
        with open(config_yolu, "r", encoding="utf-8") as f:
            for line in f:
                if anahtar in line:
                    m = re.search(r'"([^"]+)"', line)
                    if m:
                        return m.group(1)
    except Exception:
        pass
    return None


def urun_listesi_al(config_yolu: Optional[Path] = None) -> list[str]:
    """
    Ürün listesini döndürür.
    
    Parametreler:
    -------------
    config_yolu : Optional[Path]
        Config dosyası yolu (None ise varsayılan kullanılır)
    
    Döndürür:
    ---------
    list[str]
        Ürün kodları listesi
    """
    if config_yolu is None:
        config_yolu = _kok_dizin_al() / "config.txt"
    
    # Config'den ürün listesi yolunu oku
    urunler_yolu_str = config_deger_oku(config_yolu, "{{URUN_LISTESI}}")
    
    if urunler_yolu_str:
        urunler_yolu = Path(urunler_yolu_str)
    else:
        # Varsayılan yolu kullan
        urunler_yolu = _varsayilan_urun_listesi_yolu()
    
    if not urunler_yolu.exists():
        return []
    
    urunler: list[str] = []
    
    try:
        with urunler_yolu.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                urun = (row.get("urun") or "").strip()
                if urun:
                    urunler.append(urun)
    except Exception:
        pass
    
    return urunler


# =============================================================================
# Geriye Uyumluluk
# =============================================================================

# Eski isim (FileReader.items() uyumluluğu için)
items = urun_listesi_al


# Test
if __name__ == "__main__":
    print("Ürün Listesi:")
    for urun in urun_listesi_al():
        print(f"  - {urun}")
