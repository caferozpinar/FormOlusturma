import csv
import re
from pathlib import Path
from typing import Optional


def _kok_dizin_al() -> Path:
    return Path(__file__).parent.parent.parent


def _varsayilan_urun_listesi_yolu() -> Path:
    return _kok_dizin_al() / "kaynaklar" / "veriler" / "UrunListesi.csv"


def config_deger_oku(config_yolu: Path, anahtar: str) -> Optional[str]:
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
    if config_yolu is None:
        config_yolu = _kok_dizin_al() / "config.txt"

    urunler_yolu_str = config_deger_oku(config_yolu, "{{URUN_LISTESI}}")

    if urunler_yolu_str:
        urunler_yolu = Path(urunler_yolu_str)
    else:
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


if __name__ == "__main__":
    for urun in urun_listesi_al():
        print(urun)
