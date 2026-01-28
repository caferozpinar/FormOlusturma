from pathlib import Path
from uygulama.veri.urun_yukleyici import urun_listesi_al, config_deger_oku


class DosyaOkuyucu:
    def __init__(self, config_yolu: Path | None = None):
        if config_yolu is None:
            self.config_yolu = Path(__file__).parent.parent.parent / "config.txt"
        else:
            self.config_yolu = config_yolu

    def urunleri_oku(self):
        return urun_listesi_al(self.config_yolu)

    def config_degeri_oku(self, anahtar: str):
        return config_deger_oku(self.config_yolu, anahtar)
