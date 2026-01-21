"""
CSV Yükleyici Modülü
====================

CSV dosya okuma ve ComboBox yükleme fonksiyonları.

Bu modül, CSV dosyalarından veri okumak ve
PyQt5 ComboBox widget'larına yüklemek için
fonksiyonlar sağlar.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any, Callable, Optional

from PyQt5 import QtWidgets

# Modül günlükleyicisi
gunluk = logging.getLogger(__name__)


def csv_satirlarini_oku(
    csv_yolu: Path,
    kodlama: str = "utf-8-sig"
) -> list[dict[str, str]]:
    """
    CSV dosyasını okur ve satırları dictionary listesi olarak döndürür.
    
    Parametreler:
    -------------
    csv_yolu : Path
        CSV dosya yolu
    kodlama : str, optional
        Dosya kodlaması (varsayılan: "utf-8-sig" - BOM destekli)
    
    Döndürür:
    ---------
    list[dict[str, str]]
        Her satır için kolon adı -> değer eşlemesi
    
    Örnekler:
    ---------
    >>> satirlar = csv_satirlarini_oku(Path("ulkeler.csv"))
    >>> satirlar[0]
    {'id': '1', 'iso2': 'TR', 'ulke_tr': 'Türkiye'}
    """
    if not csv_yolu.exists():
        gunluk.warning(f"CSV dosyası bulunamadı: {csv_yolu}")
        return []
    
    try:
        with csv_yolu.open("r", encoding=kodlama, newline="") as f:
            okuyucu = csv.DictReader(f)
            return list(okuyucu)
    
    except Exception as e:
        gunluk.error(f"CSV okuma hatası ({csv_yolu}): {e}")
        return []


def csv_kolon_degerlerini_al(
    csv_yolu: Path,
    kolon_adi: str,
    benzersiz: bool = True,
    kodlama: str = "utf-8-sig"
) -> list[str]:
    """
    CSV dosyasından belirli bir kolonun değerlerini alır.
    
    Parametreler:
    -------------
    csv_yolu : Path
        CSV dosya yolu
    kolon_adi : str
        Okunacak kolon adı
    benzersiz : bool, optional
        Sadece benzersiz değerleri döndür (varsayılan: True)
    kodlama : str, optional
        Dosya kodlaması
    
    Döndürür:
    ---------
    list[str]
        Kolon değerleri listesi
    """
    satirlar = csv_satirlarini_oku(csv_yolu, kodlama)
    
    degerler = []
    for satir in satirlar:
        deger = (satir.get(kolon_adi) or "").strip()
        if deger:
            if benzersiz:
                if deger not in degerler:
                    degerler.append(deger)
            else:
                degerler.append(deger)
    
    return degerler


def csv_combobox_yukle(
    combo: QtWidgets.QComboBox,
    csv_yolu: Path,
    metin_kolonu: str,
    veri_kolonu: Optional[str] = None,
    alternatif_kolonlar: Optional[list[str]] = None,
    bos_secim_ekle: bool = False,
    bos_secim_metni: str = "",
    kodlama: str = "utf-8-sig"
) -> bool:
    """
    CSV dosyasından ComboBox'a veri yükler.
    
    Parametreler:
    -------------
    combo : QComboBox
        Hedef ComboBox widget'ı
    csv_yolu : Path
        CSV dosya yolu
    metin_kolonu : str
        Görüntülenecek metin için kolon adı
    veri_kolonu : str, optional
        userData için kolon adı (opsiyonel)
    alternatif_kolonlar : list[str], optional
        metin_kolonu bulunamazsa denenecek alternatifler
    bos_secim_ekle : bool, optional
        İlk öğe olarak boş seçim ekle (varsayılan: False)
    bos_secim_metni : str, optional
        Boş seçim için gösterilecek metin (varsayılan: "")
    kodlama : str, optional
        Dosya kodlaması
    
    Döndürür:
    ---------
    bool
        Başarılı ise True
    
    Örnekler:
    ---------
    >>> csv_combobox_yukle(
    ...     combo=self.ulke_box,
    ...     csv_yolu=Path("Countries.csv"),
    ...     metin_kolonu="ulke_tr",
    ...     veri_kolonu="iso2",
    ...     bos_secim_ekle=True
    ... )
    True
    """
    combo.clear()
    
    if not csv_yolu.exists():
        gunluk.warning(f"CSV dosyası bulunamadı: {csv_yolu}")
        return False
    
    try:
        with csv_yolu.open("r", encoding=kodlama, newline="") as f:
            okuyucu = csv.DictReader(f)
            
            if not okuyucu.fieldnames:
                gunluk.warning(f"CSV başlıkları bulunamadı: {csv_yolu}")
                return False
            
            # Kolon adlarını normalize et (küçük harf, boşluk temizle)
            alan_esleme = {
                ad.strip().lower(): ad 
                for ad in okuyucu.fieldnames
            }
            
            # Metin kolonunu bul
            metin_kol = alan_esleme.get(metin_kolonu.lower())
            
            # Alternatif kolonları dene
            if not metin_kol and alternatif_kolonlar:
                for alternatif in alternatif_kolonlar:
                    metin_kol = alan_esleme.get(alternatif.lower())
                    if metin_kol:
                        gunluk.debug(f"Alternatif kolon kullanıldı: {alternatif}")
                        break
            
            if not metin_kol:
                gunluk.error(
                    f"Metin kolonu bulunamadı: {metin_kolonu} "
                    f"(mevcut: {list(alan_esleme.keys())})"
                )
                return False
            
            # Veri kolonunu bul (opsiyonel)
            veri_kol = None
            if veri_kolonu:
                veri_kol = alan_esleme.get(veri_kolonu.lower())
                if not veri_kol:
                    gunluk.warning(f"Veri kolonu bulunamadı: {veri_kolonu}")
            
            # Boş seçim ekle
            if bos_secim_ekle:
                combo.addItem(bos_secim_metni, None)
            
            # Verileri yükle
            yuklenen = 0
            for satir in okuyucu:
                metin = (satir.get(metin_kol) or "").strip()
                if not metin:
                    continue
                
                # userData
                veri = None
                if veri_kol:
                    ham_veri = (satir.get(veri_kol) or "").strip()
                    try:
                        veri = int(ham_veri) if ham_veri.isdigit() else ham_veri
                    except ValueError:
                        veri = ham_veri
                
                combo.addItem(metin, veri)
                yuklenen += 1
            
            gunluk.debug(f"{yuklenen} kayıt yüklendi: {csv_yolu.name}")
            return True
    
    except Exception as e:
        gunluk.error(f"CSV yükleme hatası ({csv_yolu}): {e}")
        return False


def csv_combobox_yukle_formatsiz(
    combo: QtWidgets.QComboBox,
    csv_yolu: Path,
    metin_kolonu: str,
    format_fonksiyonu: Optional[Callable[[dict], str]] = None,
    veri_kolonu: Optional[str] = None,
    kodlama: str = "utf-8-sig"
) -> bool:
    """
    CSV'den ComboBox'a özel formatlama ile veri yükler.
    
    Parametreler:
    -------------
    combo : QComboBox
        Hedef ComboBox
    csv_yolu : Path
        CSV dosya yolu
    metin_kolonu : str
        Fallback metin kolonu
    format_fonksiyonu : Callable, optional
        Her satır için metin üreten fonksiyon
        Fonksiyon satır dictionary'si alır, string döndürür
    veri_kolonu : str, optional
        userData için kolon adı
    kodlama : str, optional
        Dosya kodlaması
    
    Döndürür:
    ---------
    bool
        Başarılı ise True
    
    Örnekler:
    ---------
    >>> def format_ulke(satir):
    ...     return f"{satir['iso2']} - {satir['ulke_tr']}"
    >>> 
    >>> csv_combobox_yukle_formatsiz(
    ...     combo=self.ulke_box,
    ...     csv_yolu=Path("Countries.csv"),
    ...     metin_kolonu="ulke_tr",
    ...     format_fonksiyonu=format_ulke,
    ...     veri_kolonu="iso2"
    ... )
    """
    combo.clear()
    
    if not csv_yolu.exists():
        gunluk.warning(f"CSV dosyası bulunamadı: {csv_yolu}")
        return False
    
    try:
        satirlar = csv_satirlarini_oku(csv_yolu, kodlama)
        
        if not satirlar:
            return False
        
        yuklenen = 0
        for satir in satirlar:
            # Metin oluştur
            if format_fonksiyonu:
                try:
                    metin = format_fonksiyonu(satir)
                except Exception as e:
                    gunluk.warning(f"Format fonksiyonu hatası: {e}")
                    metin = (satir.get(metin_kolonu) or "").strip()
            else:
                metin = (satir.get(metin_kolonu) or "").strip()
            
            if not metin:
                continue
            
            # Veri
            veri = None
            if veri_kolonu:
                ham_veri = (satir.get(veri_kolonu) or "").strip()
                veri = ham_veri if ham_veri else None
            
            combo.addItem(metin, veri)
            yuklenen += 1
        
        gunluk.debug(f"{yuklenen} kayıt yüklendi (formatli): {csv_yolu.name}")
        return True
    
    except Exception as e:
        gunluk.error(f"CSV yükleme hatası ({csv_yolu}): {e}")
        return False


def ulkeler_combobox_yukle(
    combo: QtWidgets.QComboBox,
    csv_yolu: Path
) -> bool:
    """
    Ülkeler CSV'sini ComboBox'a yükler (özel format).
    
    Format: "ISO2 - Ülke Adı" (örn: "TR - Türkiye")
    userData: ISO2 kodu
    
    Parametreler:
    -------------
    combo : QComboBox
        Hedef ComboBox
    csv_yolu : Path
        Countries.csv dosya yolu
    
    Döndürür:
    ---------
    bool
        Başarılı ise True
    """
    def format_ulke(satir: dict) -> str:
        iso2 = (satir.get("iso2") or "").strip()
        ulke = (satir.get("ulke_tr") or "").strip()
        return f"{iso2} - {ulke}" if iso2 and ulke else ""
    
    return csv_combobox_yukle_formatsiz(
        combo=combo,
        csv_yolu=csv_yolu,
        metin_kolonu="ulke_tr",
        format_fonksiyonu=format_ulke,
        veri_kolonu="iso2"
    )


def iller_combobox_yukle(
    combo: QtWidgets.QComboBox,
    csv_yolu: Path
) -> bool:
    """
    İller CSV'sini ComboBox'a yükler.
    
    Parametreler:
    -------------
    combo : QComboBox
        Hedef ComboBox
    csv_yolu : Path
        XX_provinces.csv dosya yolu
    
    Döndürür:
    ---------
    bool
        Başarılı ise True
    """
    return csv_combobox_yukle(
        combo=combo,
        csv_yolu=csv_yolu,
        metin_kolonu="province",
        veri_kolonu="id",
        alternatif_kolonlar=["province_tr", "il_tr", "il"]
    )
