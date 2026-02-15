#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Maliyet Motoru V2 Servisleri.

- ParametreHashServisi: Parametre kombinasyonu oluşturma/bulma
- MaliyetVersiyonServisi: Versiyon CRUD, girdi ve formül yönetimi
- MaliyetHesapServisi: Formül motoru ve maliyet hesaplama
- KarHiyerarsiServisi: Kâr oranı hiyerarşi çözümleme
"""

import hashlib
import json
import re
from typing import Optional, Tuple

from uygulama.altyapi.maliyet_repo import MaliyetRepository
from uygulama.altyapi.proje_repo import ProjeRepository
from uygulama.ortak.yardimcilar import logger_olustur

logger = logger_olustur("maliyet_servisi")

# Sistem varsayılan kâr oranı
SISTEM_VARSAYILAN_KAR_ORANI = 15.0


# ═════════════════════════════════════════════
# 1) PARAMETRE HASH SERVİSİ
# ═════════════════════════════════════════════

class ParametreHashServisi:
    """Parametre kombinasyonlarını yönetir."""

    def __init__(self, maliyet_repo: MaliyetRepository):
        self.repo = maliyet_repo

    @staticmethod
    def hash_uret(parametreler: dict) -> str:
        """Parametre dict'inden deterministik hash üretir."""
        # Sıralı JSON → SHA256 → 12 karakter
        canonical = json.dumps(parametreler, sort_keys=True,
                                ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]

    def bul_veya_olustur(self, alt_kalem_id: str,
                          parametreler: dict) -> Tuple[str, bool]:
        """
        Parametre kombinasyonunu bul veya oluştur.
        Returns: (kombinasyon_id, yeni_mi)
        """
        komb_hash = self.hash_uret(parametreler)
        param_json = json.dumps(parametreler, ensure_ascii=False)

        # Mevcut mu?
        mevcut = self.repo.kombinasyon_hash_ile_getir(
            alt_kalem_id, komb_hash)
        if mevcut:
            return mevcut["id"], False

        # Yoksa oluştur
        komb_id = self.repo.kombinasyon_olustur(
            alt_kalem_id, komb_hash, param_json)
        logger.info(f"Yeni parametre kombinasyonu: {komb_hash} "
                     f"(alt_kalem: {alt_kalem_id})")
        return komb_id, True

    def kombinasyon_getir(self, komb_id: str) -> Optional[dict]:
        return self.repo.kombinasyon_getir(komb_id)

    def listele(self, alt_kalem_id: str) -> list[dict]:
        return self.repo.kombinasyonlari_listele(alt_kalem_id)

    def pasif_yap(self, komb_id: str) -> None:
        self.repo.kombinasyon_pasif_yap(komb_id)


# ═════════════════════════════════════════════
# 2) MALİYET VERSİYON SERVİSİ
# ═════════════════════════════════════════════

class MaliyetVersiyonServisi:
    """Maliyet versiyonlarını yönetir."""

    def __init__(self, maliyet_repo: MaliyetRepository):
        self.repo = maliyet_repo

    def yeni_versiyon(self, kombinasyon_id: str,
                       girdiler: dict[str, str] = None,
                       formuller: dict[str, str] = None
                       ) -> Tuple[bool, str, Optional[str]]:
        """
        Yeni maliyet versiyonu oluşturur.
        Önceki aktif versiyon otomatik pasif yapılır.
        Returns: (başarılı_mı, mesaj, versiyon_id)
        """
        son_no = self.repo.son_versiyon_no(kombinasyon_id)
        yeni_no = son_no + 1

        versiyon_id = self.repo.versiyon_olustur(kombinasyon_id, yeni_no)

        if girdiler:
            self.repo.girdileri_toplu_ekle(versiyon_id, girdiler)

        if formuller:
            self.repo.formulleri_toplu_ekle(versiyon_id, formuller)

        logger.info(f"Yeni maliyet versiyonu: v{yeni_no} "
                     f"(komb: {kombinasyon_id})")
        return True, f"Versiyon {yeni_no} oluşturuldu.", versiyon_id

    def aktif_versiyon(self, kombinasyon_id: str) -> Optional[dict]:
        return self.repo.aktif_versiyon_getir(kombinasyon_id)

    def versiyon_detay(self, versiyon_id: str) -> dict:
        """Versiyon + girdiler + formüller."""
        return self.repo.versiyon_tam_snapshot(versiyon_id)

    def versiyonlar(self, kombinasyon_id: str) -> list[dict]:
        return self.repo.versiyonlari_listele(kombinasyon_id)

    def pasif_yap(self, versiyon_id: str) -> None:
        self.repo.versiyon_pasif_yap(versiyon_id)


# ═════════════════════════════════════════════
# 3) MALİYET HESAP SERVİSİ
# ═════════════════════════════════════════════

class MaliyetHesapServisi:
    """Formül motoru ve maliyet hesaplama."""

    def __init__(self, maliyet_repo: MaliyetRepository):
        self.repo = maliyet_repo

    # ─────────────────────────────────────────
    # FORMÜL MOTORU
    # ─────────────────────────────────────────

    # İzin verilen: sayılar, +, -, *, /, %, (, ), boşluk, değişken adları
    _GUVENLI_PATTERN = re.compile(
        r'^[\d\s\+\-\*\/\%\(\)\.\,a-zA-Z_çğıöşüÇĞİÖŞÜ]+$'
    )

    @classmethod
    def formul_hesapla(cls, formul: str, degiskenler: dict) -> float:
        """
        Güvenli formül hesaplama.
        Sadece +, -, *, /, %, () destekler.
        Değişkenler dict ile sağlanır.
        """
        if not formul or not formul.strip():
            return 0.0

        # Güvenlik kontrolü
        if not cls._GUVENLI_PATTERN.match(formul):
            raise ValueError(f"Güvensiz formül: {formul}")

        # Değişkenleri yerleştir
        ifade = formul
        # Uzun değişkenleri önce değiştir (kısa olanı uzunun içinde değiştirmesin)
        for ad in sorted(degiskenler.keys(), key=len, reverse=True):
            deger = degiskenler[ad]
            try:
                deger_f = float(deger)
            except (ValueError, TypeError):
                deger_f = 0.0
            ifade = ifade.replace(ad, str(deger_f))

        # eval güvenlik — sadece sayılar ve operatörler kalmış olmalı
        temiz = ifade.replace(" ", "")
        if not re.match(r'^[\d\s\+\-\*\/\%\(\)\.]+$', temiz):
            raise ValueError(f"Hesaplanamayan ifade: {ifade}")

        try:
            sonuc = eval(temiz)  # noqa: S307
            return round(float(sonuc), 4)
        except (ZeroDivisionError, SyntaxError, NameError) as e:
            raise ValueError(f"Formül hatası: {e}")

    # ─────────────────────────────────────────
    # TAM MALİYET HESABI
    # ─────────────────────────────────────────

    def alt_kalem_maliyet_hesapla(self, versiyon_id: str,
                                   ek_degiskenler: dict = None
                                   ) -> dict:
        """
        Bir maliyet versiyonunun tam hesaplamasını yapar.
        Returns: {alan_adi: hesaplanan_deger, ...}
        """
        girdiler = self.repo.girdileri_getir(versiyon_id)
        formuller = self.repo.formulleri_getir(versiyon_id)

        # Girdi değerlerini dict'e çevir
        degiskenler = {}
        for g in girdiler:
            try:
                degiskenler[g["girdi_adi"]] = float(g["deger"])
            except (ValueError, TypeError):
                degiskenler[g["girdi_adi"]] = g["deger"]

        # Ek değişkenler (konum çarpanları vb.)
        if ek_degiskenler:
            degiskenler.update(ek_degiskenler)

        # Formülleri hesapla
        sonuclar = {}
        for f in formuller:
            try:
                sonuc = self.formul_hesapla(f["formul"], degiskenler)
                sonuclar[f["alan_adi"]] = sonuc
                # Hesaplanan değeri de değişken olarak ekle (zincirleme formül)
                degiskenler[f["alan_adi"]] = sonuc
            except ValueError as e:
                sonuclar[f["alan_adi"]] = f"HATA: {e}"
                logger.warning(f"Formül hatası [{f['alan_adi']}]: {e}")

        return sonuclar

    def konum_carpanli_hesapla(self, versiyon_id: str, konum: str,
                                yil: int = None) -> dict:
        """Konum çarpanlarını uygulayarak hesaplama yapar."""
        ek = {}
        carpan = self.repo.konum_carpani_getir(konum, yil)
        if carpan:
            ek["tasima_carpani"] = carpan["tasima_carpani"]
            ek["iscilik_carpani"] = carpan["iscilik_carpani"]
        else:
            ek["tasima_carpani"] = 1.0
            ek["iscilik_carpani"] = 1.0

        return self.alt_kalem_maliyet_hesapla(versiyon_id, ek)


# ═════════════════════════════════════════════
# 4) KAR HİYERARŞİ SERVİSİ
# ═════════════════════════════════════════════

class KarHiyerarsiServisi:
    """
    Kâr oranı hiyerarşi çözümleme.
    Öncelik: Alt kalem override > Proje > Sistem varsayılan
    """

    def __init__(self, proje_repo: ProjeRepository):
        self.proje_repo = proje_repo

    def kar_orani_cozumle(self, proje_id: str,
                           alt_kalem_override: float = None) -> float:
        """
        Kâr oranını hiyerarşik olarak çözümler.
        1. Alt kalem override (belge_alt_kalemleri.kar_orani_override)
        2. Proje bazlı kâr oranı (projeler.kar_orani)
        3. Sistem varsayılan (%15)
        """
        # 1. Alt kalem override
        if alt_kalem_override is not None and alt_kalem_override > 0:
            return alt_kalem_override

        # 2. Proje bazlı
        proje = self.proje_repo.id_ile_getir(proje_id)
        if proje and proje.kar_orani > 0:
            return proje.kar_orani

        # 3. Sistem varsayılan
        return SISTEM_VARSAYILAN_KAR_ORANI

    @staticmethod
    def kar_hesapla(maliyet: float, kar_orani: float) -> dict:
        """Maliyet üzerinden kâr hesaplar."""
        kar_tutari = maliyet * (kar_orani / 100.0)
        return {
            "maliyet": round(maliyet, 2),
            "kar_orani": round(kar_orani, 2),
            "kar_tutari": round(kar_tutari, 2),
            "toplam": round(maliyet + kar_tutari, 2),
        }
