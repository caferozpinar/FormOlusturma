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
    PROJE_OLUSTUR = "PROJE_OLUSTUR"
    PROJE_GUNCELLE = "PROJE_GUNCELLE"
    PROJE_KAPAT = "PROJE_KAPAT"
    PROJE_AKTIFLE = "PROJE_AKTIFLE"
    PROJE_SIL = "PROJE_SIL"
    BELGE_OLUSTUR = "BELGE_OLUSTUR"
    BELGE_GUNCELLE = "BELGE_GUNCELLE"
    BELGE_ONAYLA = "BELGE_ONAYLA"
    BELGE_REDDET = "BELGE_REDDET"
    BELGE_GONDER = "BELGE_GONDER"
    BELGE_SIL = "BELGE_SIL"
    REVIZYON_AC = "REVIZYON_AC"
    KULLANICI_OLUSTUR = "KULLANICI_OLUSTUR"
    KULLANICI_GUNCELLE = "KULLANICI_GUNCELLE"
    KULLANICI_SIL = "KULLANICI_SIL"
    GIRIS_BASARILI = "GIRIS_BASARILI"
    GIRIS_BASARISIZ = "GIRIS_BASARISIZ"
    SYNC_BASLAT = "SYNC_BASLAT"
    SYNC_TAMAMLA = "SYNC_TAMAMLA"


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
    silinme_tarihi: Optional[str] = None


@dataclass
class HareketLogu:
    id: str = field(default_factory=_yeni_uuid)
    kullanici_id: str = ""
    islem: IslemTipi = IslemTipi.PROJE_OLUSTUR
    hedef_tablo: str = ""
    hedef_id: str = ""
    detay: str = ""
    tarih: str = field(default_factory=_simdi)
