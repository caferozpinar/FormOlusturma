#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Domain Modelleri — Saf veri sınıfları, Enum ve durumlar.
Hiçbir iş kuralı veya veritabanı bağımlılığı içermez.
"""

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import uuid4


# ─────────────────────────────────────────────
# ENUM TANIMLARI
# ─────────────────────────────────────────────

class ProjeDurumu(enum.Enum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class BelgeDurumu(enum.Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class KullaniciRolu(enum.Enum):
    ADMIN = "Admin"
    EDITOR = "Editor"
    VIEWER = "Viewer"


class AlanTipi(enum.Enum):
    FLOAT = "float"
    INT = "int"
    BOOL = "bool"
    TEXT = "text"
    CHOICE = "choice"
    MULTI_CHOICE = "multi-choice"
    DATE = "date"
    DECIMAL = "decimal"


class IslemTipi(enum.Enum):
    """Audit log için işlem türleri."""
    # Proje
    PROJE_OLUSTUR = "PROJE_OLUSTUR"
    PROJE_GUNCELLE = "PROJE_GUNCELLE"
    PROJE_KAPAT = "PROJE_KAPAT"
    PROJE_AKTIFLE = "PROJE_AKTIFLE"
    PROJE_SIL = "PROJE_SIL"
    # Belge
    BELGE_OLUSTUR = "BELGE_OLUSTUR"
    BELGE_GUNCELLE = "BELGE_GUNCELLE"
    BELGE_ONAYLA = "BELGE_ONAYLA"
    BELGE_REDDET = "BELGE_REDDET"
    BELGE_GONDER = "BELGE_GONDER"
    BELGE_SIL = "BELGE_SIL"
    REVIZYON_AC = "REVIZYON_AC"
    # Kullanıcı
    KULLANICI_OLUSTUR = "KULLANICI_OLUSTUR"
    KULLANICI_GUNCELLE = "KULLANICI_GUNCELLE"
    KULLANICI_SIL = "KULLANICI_SIL"
    KULLANICI_ROL_DEGISTIR = "KULLANICI_ROL_DEGISTIR"
    KULLANICI_DEAKTIF = "KULLANICI_DEAKTIF"
    GIRIS_BASARILI = "GIRIS_BASARILI"
    GIRIS_BASARISIZ = "GIRIS_BASARISIZ"
    # Ürün ve Alan
    URUN_OLUSTUR = "URUN_OLUSTUR"
    URUN_GUNCELLE = "URUN_GUNCELLE"
    URUN_SIL = "URUN_SIL"
    ALAN_EKLE = "ALAN_EKLE"
    ALAN_SIL = "ALAN_SIL"
    ALT_KALEM_OLUSTUR = "ALT_KALEM_OLUSTUR"
    # Maliyet
    MALIYET_VERSIYON = "MALIYET_VERSIYON"
    MALIYET_HESAPLA = "MALIYET_HESAPLA"
    # Sync
    SYNC_BASLAT = "SYNC_BASLAT"
    SYNC_TAMAMLA = "SYNC_TAMAMLA"
    SYNC_CONFLICT = "SYNC_CONFLICT"
    # Yetki
    YETKI_REDDEDILDI = "YETKI_REDDEDILDI"


# ─────────────────────────────────────────────
# VERİ SINIFLARI (Dataclass)
# ─────────────────────────────────────────────

def _yeni_uuid() -> str:
    return str(uuid4())


def _simdi() -> str:
    return datetime.now().isoformat()


@dataclass
class Kullanici:
    id: str = field(default_factory=_yeni_uuid)
    kullanici_adi: str = ""
    sifre_hash: str = ""
    rol: KullaniciRolu = KullaniciRolu.EDITOR
    aktif: bool = True
    olusturma_tarihi: str = field(default_factory=_simdi)
    guncelleme_tarihi: str = field(default_factory=_simdi)
    silinme_tarihi: Optional[str] = None


@dataclass
class Proje:
    id: str = field(default_factory=_yeni_uuid)
    firma: str = ""
    konum: str = ""
    tesis: str = ""
    urun_seti: str = ""
    hash_kodu: str = ""
    durum: ProjeDurumu = ProjeDurumu.ACTIVE
    kar_orani: float = 0.0
    olusturan_id: str = ""
    olusturma_tarihi: str = field(default_factory=_simdi)
    guncelleme_tarihi: str = field(default_factory=_simdi)
    silinme_tarihi: Optional[str] = None


@dataclass
class Belge:
    id: str = field(default_factory=_yeni_uuid)
    proje_id: str = ""
    tur: str = ""  # TEKLİF, KEŞİF, TANIM
    revizyon_no: int = 1
    durum: BelgeDurumu = BelgeDurumu.DRAFT
    toplam_maliyet: float = 0.0
    kar_orani: float = 0.0
    kdv_orani: float = 20.0
    olusturan_id: str = ""
    olusturma_tarihi: str = field(default_factory=_simdi)
    guncelleme_tarihi: str = field(default_factory=_simdi)
    silinme_tarihi: Optional[str] = None
    snapshot_veri: Optional[str] = None  # JSON snapshot


@dataclass
class Urun:
    id: str = field(default_factory=_yeni_uuid)
    kod: str = ""
    ad: str = ""
    aktif: bool = True
    olusturma_tarihi: str = field(default_factory=_simdi)
    silinme_tarihi: Optional[str] = None


@dataclass
class UrunAlani:
    id: str = field(default_factory=_yeni_uuid)
    urun_id: str = ""
    etiket: str = ""
    alan_anahtari: str = ""
    tip: AlanTipi = AlanTipi.TEXT
    zorunlu: bool = False
    sira: int = 0
    min_deger: Optional[float] = None
    max_deger: Optional[float] = None
    hassasiyet: Optional[int] = None  # decimal precision
    silinme_tarihi: Optional[str] = None


@dataclass
class UrunAlanSecenegi:
    id: str = field(default_factory=_yeni_uuid)
    alan_id: str = ""
    deger: str = ""
    sira: int = 0
    silinme_tarihi: Optional[str] = None


@dataclass
class AltKalem:
    id: str = field(default_factory=_yeni_uuid)
    ad: str = ""
    aktif: bool = True
    silinme_tarihi: Optional[str] = None


@dataclass
class UrunAltKalemi:
    id: str = field(default_factory=_yeni_uuid)
    urun_id: str = ""
    alt_kalem_id: str = ""
    varsayilan_birim_fiyat: float = 0.0
    silinme_tarihi: Optional[str] = None


@dataclass
class BelgeUrunu:
    id: str = field(default_factory=_yeni_uuid)
    belge_id: str = ""
    urun_id: str = ""
    miktar: int = 1
    alan_verileri: str = "{}"  # JSON
    silinme_tarihi: Optional[str] = None


@dataclass
class BelgeAltKalemi:
    id: str = field(default_factory=_yeni_uuid)
    belge_id: str = ""
    belge_urun_id: str = ""
    alt_kalem_id: str = ""
    dahil: bool = True
    miktar: int = 1
    birim_fiyat: float = 0.0
    kar_orani_override: Optional[float] = None
    kombinasyon_id: Optional[str] = None
    versiyon_id: Optional[str] = None
    silinme_tarihi: Optional[str] = None


# ─────────────────────────────────────────────
# MALİYET MOTORU V2 MODELLERİ
# ─────────────────────────────────────────────

@dataclass
class ParametreKombinasyonu:
    id: str = field(default_factory=_yeni_uuid)
    alt_kalem_id: str = ""
    kombinasyon_hash: str = ""
    parametre_json: str = "{}"
    aktif_mi: bool = True
    created_at: str = field(default_factory=_simdi)


@dataclass
class MaliyetVersiyonu:
    id: str = field(default_factory=_yeni_uuid)
    kombinasyon_id: str = ""
    versiyon_no: int = 1
    aktif_mi: bool = True
    created_at: str = field(default_factory=_simdi)


@dataclass
class MaliyetGirdiDegeri:
    id: str = field(default_factory=_yeni_uuid)
    versiyon_id: str = ""
    girdi_adi: str = ""
    deger: str = ""


@dataclass
class MaliyetFormulu:
    id: str = field(default_factory=_yeni_uuid)
    versiyon_id: str = ""
    alan_adi: str = ""
    formul: str = ""


@dataclass
class KonumMaliyetCarpani:
    id: str = field(default_factory=_yeni_uuid)
    konum: str = ""
    tasima_carpani: float = 1.0
    iscilik_carpani: float = 1.0
    yil: int = 2026
    created_at: str = field(default_factory=_simdi)


# ─────────────────────────────────────────────
# ENTERPRISE VERSİYONLU MALİYET MODELLERİ
# ─────────────────────────────────────────────

@dataclass
class ParametreTip:
    id: str = field(default_factory=_yeni_uuid)
    kod: str = ""
    python_tipi: str = "str"
    ui_bilesen: str = "text"
    json_schema: str = "{}"

@dataclass
class UrunVersiyon:
    id: str = field(default_factory=_yeni_uuid)
    urun_id: str = ""
    versiyon_no: int = 1
    aktif_mi: bool = True
    olusturma_tarihi: str = field(default_factory=_simdi)

@dataclass
class UrunParametre:
    id: str = field(default_factory=_yeni_uuid)
    urun_versiyon_id: str = ""
    ad: str = ""
    tip_id: str = ""
    zorunlu: bool = False
    varsayilan_deger: str = ""
    aktif_mi: bool = True
    sira: int = 0

@dataclass
class AltKalemVersiyon:
    id: str = field(default_factory=_yeni_uuid)
    alt_kalem_id: str = ""
    urun_versiyon_id: str = ""
    versiyon_no: int = 1
    aktif_mi: bool = True
    olusturma_tarihi: str = field(default_factory=_simdi)

@dataclass
class AltKalemParametre:
    id: str = field(default_factory=_yeni_uuid)
    alt_kalem_versiyon_id: str = ""
    ad: str = ""
    tip_id: str = ""
    zorunlu: bool = False
    varsayilan_deger: str = ""
    aktif_mi: bool = True
    urun_param_ref_id: Optional[str] = None
    sira: int = 0

@dataclass
class MaliyetSablon:
    id: str = field(default_factory=_yeni_uuid)
    alt_kalem_versiyon_id: str = ""
    formul_ifadesi: str = "0"
    varsayilan_formul_mu: bool = True
    aktif_mi: bool = True
    kar_orani: float = 0.0
    olusturma_tarihi: str = field(default_factory=_simdi)

@dataclass
class MaliyetParametre:
    id: str = field(default_factory=_yeni_uuid)
    maliyet_sablon_id: str = ""
    ad: str = ""
    degisken_kodu: str = ""
    varsayilan_deger: float = 0.0

@dataclass
class KonumFiyat:
    id: str = field(default_factory=_yeni_uuid)
    ulke: str = ""
    sehir: str = ""
    fiyat: float = 0.0

@dataclass
class ProjeMaliyetSnapshot:
    id: str = field(default_factory=_yeni_uuid)
    proje_id: str = ""
    belge_id: Optional[str] = None
    revizyon_no: int = 1
    urun_id: str = ""
    urun_versiyon_id: str = ""
    alt_kalem_id: str = ""
    alt_kalem_versiyon_id: str = ""
    parametre_degerleri: str = "{}"
    formul_ifadesi: str = "0"
    birim_fiyat: float = 0.0
    miktar: int = 1
    toplam_fiyat: float = 0.0
    kar_orani: float = 0.0
    konum_fiyat: float = 0.0
    opsiyon_mu: bool = False
    olusturma_yili: int = 2026
    olusturma_tarihi: str = field(default_factory=_simdi)


@dataclass
class HareketLogu:
    id: str = field(default_factory=_yeni_uuid)
    kullanici_id: str = ""
    islem: IslemTipi = IslemTipi.PROJE_OLUSTUR
    hedef_tablo: str = ""
    hedef_id: str = ""
    detay: str = ""
    tarih: str = field(default_factory=_simdi)
