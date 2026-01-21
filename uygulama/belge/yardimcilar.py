"""
Belge Yardımcıları Modülü
=========================

Belge oluşturma için yardımcı fonksiyonlar.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

from uygulama.sabitler import (
    TURKCE_KARAKTER_DONUSUMU,
    SERI_HASH_KARAKTER_KUMESI,
    SERI_HASH_UZUNLUGU,
    VARSAYILAN_SERI_REVIZYON,
)

# Modül günlükleyicisi
gunluk = logging.getLogger(__name__)


def config_deger_oku(config_yolu: str | Path, anahtar: str) -> Optional[str]:
    """
    config.txt dosyasından değer okur.

    Parametreler:
    -------------
    config_yolu : str | Path
        Config dosyası yolu
    anahtar : str
        Okunacak anahtar (örn: "{{URUN_LISTESI}}")

    Döndürür:
    ---------
    Optional[str]
        Değer veya None
    """
    try:
        config_yolu = Path(config_yolu)
        if not config_yolu.exists():
            return None

        with config_yolu.open("r", encoding="utf-8") as f:
            for satir in f:
                if anahtar in satir:
                    esleme = re.search(r'"([^"]+)"', satir)
                    if esleme:
                        return esleme.group(1)
        return None
    except Exception:
        return None


def urun_basliklarini_yukle(
    txt_yolu: str | Path,
    gunluk_ref: Optional[logging.Logger] = None
) -> dict[str, str]:
    """
    Ürün başlıklarını dosyadan yükler.

    Dosya Formatı:
    --------------
    URUN_KODU - Ürün Tam Adı
    Örnek: LK - ESSMANN DUMAN TAHLİYE KAPAKLARI

    Parametreler:
    -------------
    txt_yolu : str | Path
        Ürün başlıkları dosyası yolu
    gunluk_ref : Logger, optional
        Logger referansı

    Döndürür:
    ---------
    dict[str, str]
        Ürün kodu -> tam ad eşlemesi
    """
    txt_yolu = Path(txt_yolu)
    sonuc: dict[str, str] = {}

    if not txt_yolu.exists():
        if gunluk_ref:
            gunluk_ref.warning(f"UYARI: Ürün başlıkları dosyası bulunamadı: {txt_yolu}")
        return sonuc

    try:
        for satir_no, ham in enumerate(txt_yolu.read_text(encoding="utf-8").splitlines(), 1):
            satir = ham.strip()
            if not satir or satir.startswith("#"):
                continue

            esleme = re.match(r"^([A-Za-z0-9_]+)\s*-\s*(.+)$", satir)
            if not esleme:
                if gunluk_ref:
                    gunluk_ref.warning(f"UYARI: Geçersiz format (satır {satir_no}): {satir}")
                continue

            kod = esleme.group(1).strip()
            baslik = esleme.group(2).strip()
            sonuc[kod] = baslik

        if gunluk_ref:
            gunluk_ref.info(f"{len(sonuc)} ürün başlığı yüklendi: {txt_yolu.name}")

    except Exception as e:
        if gunluk_ref:
            gunluk_ref.error(f"HATA: Ürün başlıkları yüklenemedi: {e}")

    return sonuc


def basliklari_turkce_birlestir(basliklar: list[str]) -> str:
    """
    Başlıkları Türkçe dilbilgisi kurallarına göre birleştirir.

    Örnekler:
    ---------
    - ["A"] -> "A"
    - ["A", "B"] -> "A ve B"
    - ["A", "B", "C"] -> "A, B ve C"

    Parametreler:
    -------------
    basliklar : list[str]
        Birleştirilecek başlıklar

    Döndürür:
    ---------
    str
        Birleştirilmiş metin
    """
    if not basliklar:
        return ""
    if len(basliklar) == 1:
        return basliklar[0]
    if len(basliklar) == 2:
        return f"{basliklar[0]} ve {basliklar[1]}"
    return f"{', '.join(basliklar[:-1])} ve {basliklar[-1]}"


def guvenli_dosya_adi_olustur(metin: str) -> str:
    """
    Metni güvenli dosya adına dönüştürür.

    - Türkçe karakterleri ASCII'ye çevirir
    - Özel karakterleri kaldırır
    - Boşlukları alt çizgiye çevirir

    Parametreler:
    -------------
    metin : str
        Dönüştürülecek metin

    Döndürür:
    ---------
    str
        Güvenli dosya adı
    """
    if not metin:
        return ""

    # Türkçe karakterleri dönüştür
    metin = metin.translate(TURKCE_KARAKTER_DONUSUMU)

    # Sadece alfanumerik, boşluk ve alt çizgi tut
    metin = re.sub(r"[^A-Za-z0-9_ ]+", "", metin)

    # Temizle ve boşlukları değiştir
    metin = metin.strip().replace(" ", "_")

    return metin


def deterministik_hash_olustur(girdi: str, uzunluk: int = SERI_HASH_UZUNLUGU) -> str:
    """
    Deterministik hash oluşturur.

    Girdi metninden sabit uzunlukta hash üretir.
    Karakter kümesi: 0-9, A-Z (J hariç, Türkçe hariç)

    Parametreler:
    -------------
    girdi : str
        Hash'lenecek metin
    uzunluk : int
        Hash uzunluğu (varsayılan: 6)

    Döndürür:
    ---------
    str
        Sabit uzunlukta hash
    """
    import hashlib

    # SHA-256 hash hesapla
    hash_obj = hashlib.sha256(girdi.encode('utf-8'))
    hash_bytes = hash_obj.digest()

    # Hash byte'larını karakter kümesine dönüştür
    karakter_sayisi = len(SERI_HASH_KARAKTER_KUMESI)
    sonuc = []

    for i in range(uzunluk):
        # Her pozisyon için hash byte'larından değer al
        byte_index = i % len(hash_bytes)
        deger = hash_bytes[byte_index]

        # Daha iyi dağılım için birden fazla byte kullan
        if i + 1 < len(hash_bytes):
            deger = (deger + hash_bytes[i + 1]) % 256

        # Karaktere dönüştür
        karakter_index = deger % karakter_sayisi
        sonuc.append(SERI_HASH_KARAKTER_KUMESI[karakter_index])

    return ''.join(sonuc)


def seri_numarasi_olustur(
    tarih: str,
    firma: str,
    konum: str,
    urunler: list[str],
    revizyon: str = VARSAYILAN_SERI_REVIZYON
) -> str:
    """
    Seri numarası oluşturur.

    Format: SN:TARIH-FIRMA-KONUM-URUNLER-HASH-RVZ

    Parametreler:
    -------------
    tarih : str
        Tarih (DDMMYY formatında)
    firma : str
        Firma adı
    konum : str
        Konum bilgisi
    urunler : list[str]
        Ürün kodları listesi
    revizyon : str
        Revizyon numarası (varsayılan: R01)

    Döndürür:
    ---------
    str
        Seri numarası

    Örnek:
    ------
    >>> seri_numarasi_olustur("251225", "MILTEKSAN A.Ş.", "Türkiye - İstanbul", ["LK", "ZTK"], "R01")
    'SN:251225-MILTEKSAN-A.Ş.-Türkiye-İstanbul-LKZTK-A1B2C3-R01'
    """
    # Firma ve konum'u hazırla - boşlukları tire'ye çevir
    firma_temiz = firma.strip().replace(" ", "-").upper()
    konum_temiz = konum.strip().replace(" ", "-").replace("/", "-").upper()

    # Birden fazla ardışık tire'yi tek tire'ye indir
    firma_temiz = re.sub(r"-+", "-", firma_temiz)
    konum_temiz = re.sub(r"-+", "-", konum_temiz)

    # Ürünleri bitişik birleştir
    urunler_metin = "".join(urunler)

    # Hash için girdi hazırla - büyük harfe çevir
    hash_girdisi = f"{firma_temiz}-{konum_temiz}-{urunler_metin}".upper()

    # Hash oluştur
    hash_degeri = deterministik_hash_olustur(hash_girdisi)

    # Seri numarasını birleştir
    seri = f"SN:{tarih}-{firma_temiz}-{konum_temiz}-{urunler_metin}-{hash_degeri}-{revizyon}"
    return seri


def seri_dosya_adi_olustur(
    firma: str,
    tarih: str,
    hash_degeri: str,
    revizyon: str = VARSAYILAN_SERI_REVIZYON
) -> str:
    """
    Seri numarasına göre dosya adı oluşturur.

    Format: FIRMA-TARIH-HASH-RVZ

    Parametreler:
    -------------
    firma : str
        Firma adı
    tarih : str
        Tarih (DDMMYY formatında)
    hash_degeri : str
        Hash değeri
    revizyon : str
        Revizyon numarası

    Döndürür:
    ---------
    str
        Dosya adı (uzantısız)

    Örnek:
    ------
    >>> seri_dosya_adi_olustur("MILTEKSAN A.Ş.", "251225", "A1B2C3", "R01")
    'MILTEKSAN_A.Ş.-251225-A1B2C3-R01'
    """
    # Firma adını dosya adı için hazırla - boşlukları _ ile değiştir
    firma_temiz = firma.strip().replace(" ", "_")

    # Dosya adını birleştir
    dosya_adi = f"{firma_temiz}-{tarih}-{hash_degeri}-{revizyon}"

    return dosya_adi


# =============================================================================
# Geriye Uyumluluk İçin Alias'lar
# =============================================================================

extract_value_from_config = config_deger_oku
load_product_titles = urun_basliklarini_yukle
join_titles_tr = basliklari_turkce_birlestir
safe_filename = guvenli_dosya_adi_olustur
