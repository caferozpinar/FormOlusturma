from uygulama.servisler.urun_servisi import UrunServisi


class SahteUrunOkuyucu:
    def urunleri_oku(self):
        return ["A", "B", "C"]


def test_urun_listesi_bos_secimsiz():
    servis = UrunServisi(SahteUrunOkuyucu())
    assert servis.urun_listesi_getir() == ["A", "B", "C"]


def test_urun_listesi_bos_secimli():
    servis = UrunServisi(SahteUrunOkuyucu())
    assert servis.urun_listesi_getir(bos_secim=True) == ["", "A", "B", "C"]
