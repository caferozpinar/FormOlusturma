#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teklif Servisi — Teklif/Keşif oluşturma, proje ürünlerini otomatik yükleme,
parametre girişi ve fiyat hesaplama.
"""

from typing import Optional, Tuple
from uygulama.altyapi.teklif_repo import TeklifRepository, PARA_BIRIMLERI
from uygulama.altyapi.enterprise_maliyet_repo import EnterpriseMaliyetRepository
from uygulama.servisler.enterprise_maliyet_servisi import EnterpriseMaliyetServisi
from uygulama.ortak.yardimcilar import logger_olustur
from uygulama.ortak.app_state import app_state

logger = logger_olustur("teklif_srv")


class TeklifServisi:
    def __init__(self, teklif_repo: TeklifRepository,
                 em_repo: EnterpriseMaliyetRepository,
                 em_srv: EnterpriseMaliyetServisi,
                 proje_servisi=None):
        self.repo = teklif_repo
        self.em_repo = em_repo
        self.em_srv = em_srv
        self.proje_srv = proje_servisi

    # ═══════════════════════════════════════
    # TEKLİF OLUŞTURMA
    # ═══════════════════════════════════════

    def teklif_olustur(self, proje_id: str, tur: str = "TEKLİF",
                        para_birimi: str = "TRY") -> Tuple[bool, str, Optional[str]]:
        """
        Yeni teklif oluşturur ve proje ürünlerini + alt kalemlerini otomatik yükler.
        Returns: (ok, mesaj, teklif_id)
        """
        state = app_state()
        olusturan = state.aktif_kullanici.kullanici_adi if state.aktif_kullanici else ""

        teklif_id = self.repo.olustur(proje_id, tur, "", para_birimi, olusturan)

        # Proje ürünlerini otomatik ekle
        if self.proje_srv:
            proje_urunler = self.proje_srv.proje_urunleri(proje_id)
            sira = 0
            for pu in proje_urunler:
                urun_id = pu["urun_id"]
                # Aktif ürün versiyonu
                ver = self.em_repo.aktif_urun_versiyon(urun_id)
                if not ver:
                    continue
                urun_ver_id = ver["id"]

                # Ürün parametreleri için kalem (ana ürün satırı)
                urun_kalem_id = self.repo.kalem_ekle(
                    teklif_id, urun_id, urun_ver_id, sira=sira)
                sira += 1

                # Ürün parametrelerinin varsayılan değerlerini kaydet
                urun_params = self.em_repo.urun_parametreleri(urun_ver_id)
                for p in urun_params:
                    self.repo.parametre_kaydet(
                        urun_kalem_id, p["id"], p["ad"],
                        p["varsayilan_deger"])

                # Alt kalemler
                alt_kalemler = self.em_repo.urun_versiyonuna_bagli_alt_kalemler(urun_ver_id)
                for ak in alt_kalemler:
                    akv = self.em_repo.aktif_alt_kalem_versiyon(ak["alt_kalem_id"])
                    if not akv:
                        continue
                    ak_kalem_id = self.repo.kalem_ekle(
                        teklif_id, urun_id, urun_ver_id,
                        ak["alt_kalem_id"], akv["id"], sira=sira)
                    sira += 1

                    # Alt kalem parametreleri varsayılan
                    ak_params = self.em_repo.alt_kalem_parametreleri(akv["id"])
                    for p in ak_params:
                        self.repo.parametre_kaydet(
                            ak_kalem_id, p["id"], p["ad"],
                            p["varsayilan_deger"])

        teklif = self.repo.getir(teklif_id)
        logger.info(f"Teklif oluşturuldu: {teklif['baslik']}")
        return True, f"Teklif oluşturuldu: {teklif['baslik']}", teklif_id

    # ═══════════════════════════════════════
    # TEKLİF CRUD
    # ═══════════════════════════════════════

    def getir(self, teklif_id: str) -> dict | None:
        return self.repo.getir(teklif_id)

    def proje_teklifleri(self, proje_id: str) -> list[dict]:
        return self.repo.proje_teklifleri(proje_id)

    def guncelle(self, teklif_id: str, **kwargs) -> None:
        self.repo.guncelle(teklif_id, **kwargs)

    def sil(self, teklif_id: str) -> None:
        self.repo.sil(teklif_id)

    def durum_degistir(self, teklif_id: str, yeni_durum: str) -> Tuple[bool, str]:
        teklif = self.repo.getir(teklif_id)
        if not teklif:
            return False, "Teklif bulunamadı."
        self.repo.guncelle(teklif_id, durum=yeni_durum)
        return True, f"Durum güncellendi: {yeni_durum}"

    # ═══════════════════════════════════════
    # KALEM & PARAMETRE YÖNETİMİ
    # ═══════════════════════════════════════

    def kalemler(self, teklif_id: str) -> list[dict]:
        return self.repo.kalemler(teklif_id)

    def kalem_secim_degistir(self, kalem_id: str, secili: bool) -> None:
        self.repo.kalem_guncelle(kalem_id, secili_mi=1 if secili else 0)

    def kalem_miktar_degistir(self, kalem_id: str, miktar: int) -> None:
        self.repo.kalem_guncelle(kalem_id, miktar=miktar)

    def parametre_degerleri(self, kalem_id: str) -> list[dict]:
        return self.repo.parametre_degerleri(kalem_id)

    def parametre_kaydet(self, kalem_id: str, parametre_id: str,
                          parametre_adi: str, deger: str) -> None:
        self.repo.parametre_kaydet(kalem_id, parametre_id, parametre_adi, deger)

    # ═══════════════════════════════════════
    # FİYAT HESAPLAMA
    # ═══════════════════════════════════════

    def kalem_fiyat_hesapla(self, kalem_id: str,
                              konum_fiyat: float = 0) -> Tuple[bool, str, dict]:
        """
        Tek bir kalem için fiyat hesaplar.
        Alt kalem versiyonu yoksa (ana ürün satırı) fiyat 0 döner.
        """
        kalem = None
        for k in self.repo.db.getir_hepsi(
                "SELECT * FROM teklif_kalemleri WHERE id=?", (kalem_id,)):
            kalem = dict(k)

        if not kalem:
            return False, "Kalem bulunamadı.", {}

        akv_id = kalem.get("alt_kalem_versiyon_id")
        if not akv_id:
            # Ana ürün satırı — fiyat yok
            return True, "Ana ürün satırı.", {"birim_fiyat": 0, "toplam_fiyat": 0}

        # Parametre değerlerini topla
        param_degerler = self.repo.parametre_degerleri(kalem_id)
        # Formül değişken kodları ile eşleştir
        sablon = self.em_repo.aktif_sablon(akv_id)
        if not sablon:
            return False, "Formül şablonu bulunamadı.", {}

        sablon_params = self.em_repo.sablon_parametreleri(sablon["id"])
        degiskenler = {}
        for sp in sablon_params:
            kod = sp["degisken_kodu"]
            # Eşleşen parametre değerini bul
            param_adi = sp["ad"]
            deger = sp["varsayilan_deger"]
            for pd in param_degerler:
                if pd["parametre_adi"] == param_adi:
                    try:
                        deger = float(pd["deger"])
                    except (ValueError, TypeError):
                        deger = float(sp["varsayilan_deger"])
                    break
            degiskenler[kod] = deger

        ok, msg, sonuc = self.em_srv.toplam_fiyat_hesapla(
            akv_id, kalem["miktar"], degiskenler, konum_fiyat)

        if ok:
            self.repo.kalem_guncelle(
                kalem_id,
                birim_fiyat=sonuc["birim_fiyat"],
                toplam_fiyat=sonuc["toplam_fiyat"])

        return ok, msg, sonuc

    def teklif_hesapla(self, teklif_id: str,
                        konum_fiyat: float = 0) -> Tuple[bool, str, float]:
        """
        Teklifteki tüm seçili kalemlerin fiyatlarını hesaplar.
        Returns: (ok, mesaj, genel_toplam)
        """
        kalemler = self.repo.kalemler(teklif_id)
        hatalar = []

        for k in kalemler:
            if not k["secili_mi"] or not k.get("alt_kalem_versiyon_id"):
                continue
            ok, msg, _ = self.kalem_fiyat_hesapla(k["id"], konum_fiyat)
            if not ok:
                hatalar.append(f"{k['id'][:8]}: {msg}")

        toplam = self.repo.teklif_toplamini_hesapla(teklif_id)

        if hatalar:
            return False, f"{len(hatalar)} kalemde hata. Toplam: {toplam}", toplam

        return True, f"Hesaplandı.", toplam

    # ═══════════════════════════════════════
    # YARDIMCI
    # ═══════════════════════════════════════

    @staticmethod
    def para_birimleri() -> list[tuple]:
        return list(PARA_BIRIMLERI)

    def para_birimi_sembol(self, kod: str) -> str:
        for k, s, _ in PARA_BIRIMLERI:
            if k == kod:
                return s
        return kod

    def zenginlestirilmis_kalemler(self, teklif_id: str) -> list[dict]:
        """
        Kalemleri ürün/alt kalem adlarıyla zenginleştirerek döndürür.
        UI için kullanılır.
        """
        kalemler = self.repo.kalemler(teklif_id)
        sonuc = []
        for k in kalemler:
            z = dict(k)
            # Ürün adı
            urun = self.em_repo.db.getir_tek(
                "SELECT kod, ad FROM urunler WHERE id=?", (k["urun_id"],))
            z["urun_kod"] = urun["kod"] if urun else "?"
            z["urun_ad"] = urun["ad"] if urun else "?"

            # Alt kalem adı
            if k.get("alt_kalem_id"):
                ak = self.em_repo.db.getir_tek(
                    "SELECT ad FROM alt_kalemler WHERE id=?", (k["alt_kalem_id"],))
                z["alt_kalem_ad"] = ak["ad"] if ak else "?"
                z["tip"] = "alt_kalem"
            else:
                z["alt_kalem_ad"] = ""
                z["tip"] = "urun"
            sonuc.append(z)
        return sonuc
