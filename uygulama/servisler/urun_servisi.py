#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ürün Servisi — Ürün ve dinamik alan yönetimi iş kuralları."""

from typing import Optional, Tuple
from uygulama.domain.modeller import Urun, AlanTipi
from uygulama.altyapi.urun_repo import UrunRepository
from uygulama.altyapi.log_repo import LogRepository
from uygulama.ortak.app_state import app_state
from uygulama.ortak.yardimcilar import logger_olustur

logger = logger_olustur("urun_servisi")
GECERLI_TIPLER = {t.value for t in AlanTipi}


class UrunServisi:
    def __init__(self, urun_repo: UrunRepository, log_repo: LogRepository):
        self.urun_repo = urun_repo
        self.log_repo = log_repo

    # ── ÜRÜN CRUD ──
    def olustur(self, kod: str, ad: str) -> Tuple[bool, str, Optional[Urun]]:
        state = app_state()
        if not state.giris_yapildi: return False, "Giriş yapılmamış.", None
        if not state.admin_mi: return False, "Sadece Admin.", None
        kod, ad = kod.strip().upper(), ad.strip()
        if not kod: return False, "Ürün kodu zorunludur.", None
        if not ad: return False, "Ürün adı zorunludur.", None
        if self.urun_repo.kod_mevcut_mu(kod):
            return False, f"'{kod}' kodu zaten kullanılıyor.", None
        urun = Urun(kod=kod, ad=ad)
        self.urun_repo.olustur(urun)
        return True, f"Ürün oluşturuldu: {kod}", urun

    def guncelle(self, urun_id: str, kod: str = None, ad: str = None) -> Tuple[bool, str]:
        if not app_state().admin_mi: return False, "Sadece Admin."
        urun = self.urun_repo.id_ile_getir(urun_id)
        if not urun: return False, "Ürün bulunamadı."
        if kod is not None:
            kod = kod.strip().upper()
            if not kod: return False, "Ürün kodu boş olamaz."
            if self.urun_repo.kod_mevcut_mu(kod, haric_id=urun_id):
                return False, f"'{kod}' kodu zaten kullanılıyor."
            urun.kod = kod
        if ad is not None:
            ad = ad.strip()
            if not ad: return False, "Ürün adı boş olamaz."
            urun.ad = ad
        self.urun_repo.guncelle(urun)
        return True, "Ürün güncellendi."

    def aktiflik_degistir(self, urun_id: str) -> Tuple[bool, str]:
        if not app_state().admin_mi: return False, "Sadece Admin."
        urun = self.urun_repo.id_ile_getir(urun_id)
        if not urun: return False, "Ürün bulunamadı."
        urun.aktif = not urun.aktif
        self.urun_repo.guncelle(urun)
        return True, f"Ürün {'aktif' if urun.aktif else 'pasif'} yapıldı."

    def sil(self, urun_id: str) -> Tuple[bool, str]:
        if not app_state().admin_mi: return False, "Sadece Admin."
        if not self.urun_repo.id_ile_getir(urun_id): return False, "Ürün bulunamadı."
        self.urun_repo.soft_delete(urun_id)
        return True, "Ürün silindi."

    def listele(self, sadece_aktif: bool = True) -> list[Urun]:
        return self.urun_repo.listele(sadece_aktif)

    def getir(self, urun_id: str) -> Optional[Urun]:
        return self.urun_repo.id_ile_getir(urun_id)

    def tam_detay(self, urun_id: str) -> Optional[dict]:
        return self.urun_repo.tam_detay(urun_id)

    # ── ALAN YÖNETİMİ ──
    def alan_ekle(self, urun_id: str, etiket: str, alan_anahtari: str,
                   tip: str = "text", zorunlu: bool = False, sira: int = 0,
                   min_deger: float = None, max_deger: float = None,
                   hassasiyet: int = None) -> Tuple[bool, str, Optional[str]]:
        if not app_state().admin_mi: return False, "Sadece Admin.", None
        if not etiket or not etiket.strip(): return False, "Etiket zorunludur.", None
        if not alan_anahtari or not alan_anahtari.strip(): return False, "Anahtar zorunludur.", None
        if tip not in GECERLI_TIPLER:
            return False, f"Geçersiz tip: {tip}", None
        mevcut = self.urun_repo.alanlari_getir(urun_id)
        for a in mevcut:
            if a["alan_anahtari"] == alan_anahtari.strip():
                return False, f"'{alan_anahtari}' anahtarı zaten mevcut.", None
        alan_id = self.urun_repo.alan_ekle(urun_id, etiket.strip(),
            alan_anahtari.strip(), tip, zorunlu, sira, min_deger, max_deger, hassasiyet)
        return True, "Alan eklendi.", alan_id

    def alan_guncelle(self, alan_id: str, **kwargs) -> Tuple[bool, str]:
        if not app_state().admin_mi: return False, "Sadece Admin."
        self.urun_repo.alan_guncelle(alan_id, **kwargs)
        return True, "Alan güncellendi."

    def alan_sil(self, alan_id: str) -> Tuple[bool, str]:
        if not app_state().admin_mi: return False, "Sadece Admin."
        self.urun_repo.alan_sil(alan_id)
        return True, "Alan silindi."

    def alanlari_getir(self, urun_id: str) -> list[dict]:
        return self.urun_repo.alanlari_getir(urun_id)

    # ── SEÇENEK YÖNETİMİ ──
    def secenek_ekle(self, alan_id: str, deger: str, sira: int = 0) -> Tuple[bool, str, Optional[str]]:
        if not app_state().admin_mi: return False, "Sadece Admin.", None
        alan = self.urun_repo.alan_getir(alan_id)
        if not alan: return False, "Alan bulunamadı.", None
        if alan["tip"] not in ("choice", "multi-choice"):
            return False, "Seçenek sadece choice/multi-choice alanlara eklenebilir.", None
        if not deger or not deger.strip(): return False, "Değer zorunludur.", None
        sec_id = self.urun_repo.secenek_ekle(alan_id, deger.strip(), sira)
        return True, "Seçenek eklendi.", sec_id

    def secenek_sil(self, sec_id: str) -> Tuple[bool, str]:
        if not app_state().admin_mi: return False, "Sadece Admin."
        self.urun_repo.secenek_sil(sec_id)
        return True, "Seçenek silindi."

    def secenekleri_getir(self, alan_id: str) -> list[dict]:
        return self.urun_repo.secenekleri_getir(alan_id)

    # ── ALT KALEM YÖNETİMİ ──
    def alt_kalem_olustur(self, ad: str) -> Tuple[bool, str, Optional[str]]:
        if not app_state().admin_mi: return False, "Sadece Admin.", None
        if not ad or not ad.strip(): return False, "Ad zorunludur.", None
        ak_id = self.urun_repo.alt_kalem_olustur(ad.strip())
        return True, "Alt kalem oluşturuldu.", ak_id

    def alt_kalem_listele(self) -> list[dict]:
        return self.urun_repo.alt_kalem_listele()

    def urun_alt_kalem_bagla(self, urun_id: str, alt_kalem_id: str,
                              fiyat: float = 0.0) -> Tuple[bool, str]:
        if not app_state().admin_mi: return False, "Sadece Admin."
        self.urun_repo.urun_alt_kalem_bagla(urun_id, alt_kalem_id, fiyat)
        return True, "Alt kalem bağlandı."

    def urun_alt_kalem_kopar(self, kayit_id: str) -> Tuple[bool, str]:
        if not app_state().admin_mi: return False, "Sadece Admin."
        self.urun_repo.urun_alt_kalem_kopar(kayit_id)
        return True, "Alt kalem koparıldı."

    def urun_alt_kalemleri(self, urun_id: str) -> list[dict]:
        return self.urun_repo.urun_alt_kalemleri(urun_id)
