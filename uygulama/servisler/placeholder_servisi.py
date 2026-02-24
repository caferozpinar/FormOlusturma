#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Placeholder Servisi — Kural motoru ve çözümleme.

Kural Tipleri:
  - dogrudan:      Parametrenin değerini aynen yaz
  - esitlik:       parametre = "değer" → sonuç metni
  - karsilastirma: parametre > 300 → sonuç metni
  - birlestirme:   Birden fazla parametreyi birleştir (şablon)
  - sablon:        Serbest şablon metni {PARAM_ADI} ile

Parametre Kaynakları:
  - urun_param:      Ürün parametresi
  - alt_kalem_param:  Alt kalem parametresi
  - proje_bilgi:     Proje bilgileri (ad, konum, tesis türü vb.)
"""

import re
from typing import Optional
from uygulama.altyapi.placeholder_repo import (
    PlaceholderRepository, KURAL_TIPLERI, OPERATORLER, PROJE_BILGI_ALANLARI
)
from uygulama.ortak.yardimcilar import logger_olustur

logger = logger_olustur("placeholder_srv")


class PlaceholderServisi:
    def __init__(self, placeholder_repo: PlaceholderRepository):
        self.repo = placeholder_repo

    # ═══════════════════════════════════════
    # ADMIN — Placeholder CRUD
    # ═══════════════════════════════════════

    def placeholder_olustur(self, kod: str, ad: str = "",
                              aciklama: str = "") -> tuple[bool, str, str]:
        return self.repo.olustur(kod, ad, aciklama)

    def placeholder_listele(self, sadece_aktif: bool = True) -> list[dict]:
        return self.repo.listele(sadece_aktif)

    def placeholder_guncelle(self, pid: str, **kwargs) -> None:
        self.repo.guncelle(pid, **kwargs)

    def placeholder_sil(self, pid: str) -> None:
        self.repo.sil(pid)

    # ═══════════════════════════════════════
    # ADMIN — Kural CRUD
    # ═══════════════════════════════════════

    def kural_ekle(self, placeholder_id: str, kural_tipi: str,
                    parametre_kaynak: str, parametre_adi: str,
                    operator: str = "=", kosul_degeri: str = "",
                    sonuc_metni: str = "", varsayilan_mi: bool = False,
                    parametre_ref_id: str = None) -> tuple[bool, str, str]:
        return self.repo.kural_ekle(
            placeholder_id, kural_tipi, parametre_kaynak, parametre_adi,
            operator, kosul_degeri, sonuc_metni, varsayilan_mi, parametre_ref_id)

    def kurallar(self, placeholder_id: str) -> list[dict]:
        return self.repo.kurallar(placeholder_id)

    def kural_sil(self, kural_id: str) -> None:
        self.repo.kural_sil(kural_id)

    # ═══════════════════════════════════════
    # ÇÖZÜMLEME MOTORU
    # ═══════════════════════════════════════

    def cozumle(self, placeholder_kod: str, baglamlar: dict) -> str:
        """
        Tek bir placeholder'ı çözümler.

        baglamlar: {
            "urun_param":      {"KANAT MALZEMESİ": "XXX", "MOTOR MALZEMESİ": "YYY"},
            "alt_kalem_param": {"İŞÇİLİK": 500},
            "proje_bilgi":     {"PROJE_ADI": "Acme", "PROJE_KONUM": "İstanbul", ...},
            "teklif_param":    {"__ADET__": "5", "__BIRIM_FIYAT__": "1200.50",
                                "__TOPLAM_FIYAT__": "6002.50", "__ALT_KALEM_NO__": "3",
                                "__TEKLIF_TOPLAM__": "45000", "__TEKLIF_KDV__": "9000",
                                "__TEKLIF_GENEL_TOPLAM__": "54000"},
        }
        """
        ph = self.repo.kod_ile_getir(placeholder_kod)
        if not ph:
            return placeholder_kod  # Çözümlenemedi, kodu aynen döndür

        kurallar = self.repo.kurallar(ph["id"])
        if not kurallar:
            return ""

        # Kuralları sırayla dene (varsayılan en sona)
        varsayilan_sonuc = ""
        for kural in sorted(kurallar, key=lambda k: (k["varsayilan_mi"], k["sira"])):
            if kural["varsayilan_mi"]:
                varsayilan_sonuc = kural["sonuc_metni"]
                continue

            sonuc = self._kural_degerlendir(kural, baglamlar)
            if sonuc is not None:
                return sonuc

        return varsayilan_sonuc

    def toplu_cozumle(self, metin: str, baglamlar: dict) -> str:
        """
        Metin içindeki tüm {/XXX/} placeholder'ları çözümler.
        Form şablonunda kullanılır.
        """
        def _degistir(match):
            kod = match.group(0)
            return self.cozumle(kod, baglamlar)

        return re.sub(r'\{/[A-ZÇĞİÖŞÜa-zçğıöşü0-9_ ]+/\}', _degistir, metin)

    def _kural_degerlendir(self, kural: dict, baglamlar: dict) -> str | None:
        """Tek bir kuralı değerlendirir. None döndürürse kural tutmadı."""
        tip = kural["kural_tipi"]
        kaynak = kural["parametre_kaynak"]
        param_adi = kural["parametre_adi"]

        # Parametre değerini al
        kaynak_dict = baglamlar.get(kaynak, {})

        if tip == "dogrudan":
            deger = kaynak_dict.get(param_adi)
            if deger is not None:
                return str(deger)
            return None

        elif tip == "esitlik":
            deger = kaynak_dict.get(param_adi)
            if deger is None:
                return None
            op = kural["operator"]
            kosul = kural["kosul_degeri"]
            if self._karsilastir_metin(str(deger), op, kosul):
                return kural["sonuc_metni"]
            return None

        elif tip == "karsilastirma":
            deger = kaynak_dict.get(param_adi)
            if deger is None:
                return None
            try:
                deger_num = float(deger)
                kosul_num = float(kural["kosul_degeri"])
            except (ValueError, TypeError):
                return None
            if self._karsilastir_sayi(deger_num, kural["operator"], kosul_num):
                return kural["sonuc_metni"]
            return None

        elif tip == "birlestirme":
            # sonuc_metni şablon: "{KANAT MALZEMESİ} x {MOTOR MALZEMESİ}"
            sablon = kural["sonuc_metni"]
            # Tüm kaynaklardan birleşik dict
            tum = {}
            for k, v in baglamlar.items():
                if isinstance(v, dict):
                    tum.update(v)
            return self._sablon_cozumle(sablon, tum)

        elif tip == "sablon":
            sablon = kural["sonuc_metni"]
            tum = {}
            for k, v in baglamlar.items():
                if isinstance(v, dict):
                    tum.update(v)
            return self._sablon_cozumle(sablon, tum)

        return None

    def _karsilastir_metin(self, deger: str, op: str, kosul: str) -> bool:
        if op == "=":
            return deger == kosul
        elif op == "!=":
            return deger != kosul
        elif op == "icerir":
            return kosul.lower() in deger.lower()
        elif op == "baslar":
            return deger.lower().startswith(kosul.lower())
        elif op == "biter":
            return deger.lower().endswith(kosul.lower())
        return False

    def _karsilastir_sayi(self, deger: float, op: str, kosul: float) -> bool:
        if op == "=":
            return deger == kosul
        elif op == "!=":
            return deger != kosul
        elif op == ">":
            return deger > kosul
        elif op == "<":
            return deger < kosul
        elif op == ">=":
            return deger >= kosul
        elif op == "<=":
            return deger <= kosul
        return False

    def _sablon_cozumle(self, sablon: str, parametreler: dict) -> str:
        """
        Şablon metni içindeki {PARAM_ADI} ifadelerini çözümler.
        Örn: "{KANAT MALZEMESİ} x {MOTOR MALZEMESİ}" → "Çelik x Alüminyum"
        """
        def _degistir(match):
            anahtar = match.group(1)
            return str(parametreler.get(anahtar, f"[{anahtar}]"))

        return re.sub(r'\{([^/][^}]*)\}', _degistir, sablon)

    # ═══════════════════════════════════════
    # YARDIMCI — KAYNAK LİSTELERİ
    # ═══════════════════════════════════════

    @staticmethod
    def proje_bilgi_alanlari() -> list[str]:
        return list(PROJE_BILGI_ALANLARI)

    @staticmethod
    def kural_tipleri_listesi() -> list[tuple[str, str]]:
        """Kural tipleri: [(kod, açıklama), ...]"""
        return [
            ("dogrudan", "Doğrudan Al — Parametrenin değerini aynen yaz"),
            ("esitlik", "Eşitlik Koşulu — Parametre belirli değere eşitse → metin"),
            ("karsilastirma", "Sayısal Karşılaştırma — Parametre > < = → metin"),
            ("birlestirme", "Birleştirme — Birden fazla parametreyi birleştir"),
            ("sablon", "Serbest Şablon — Parametreleri metin içine yerleştir"),
        ]

    @staticmethod
    def operator_listesi() -> list[tuple[str, str]]:
        """Operatörler: [(kod, açıklama), ...]"""
        return [
            ("=", "Eşittir"),
            ("!=", "Eşit Değildir"),
            (">", "Büyüktür"),
            ("<", "Küçüktür"),
            (">=", "Büyük veya Eşit"),
            ("<=", "Küçük veya Eşit"),
            ("icerir", "İçerir (metin)"),
            ("baslar", "İle Başlar"),
            ("biter", "İle Biter"),
        ]
