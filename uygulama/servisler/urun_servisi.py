from typing import Protocol, List


class UrunOkuyucu(Protocol):
    def urunleri_oku(self) -> List[str]:
        ...


class UrunServisi:
    def __init__(self, okuyucu: UrunOkuyucu):
        self.okuyucu = okuyucu

    def urun_listesi_getir(self, bos_secim: bool = False) -> list[str]:
        urunler = self.okuyucu.urunleri_oku()
        if bos_secim:
            return [""] + urunler
        return urunler
