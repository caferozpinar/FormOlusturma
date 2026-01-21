"""
Yapılandırma Yönetimi Modülü
============================

Uygulama yapılandırması ve yol yönetimi.

Bu modül, uygulama yolları ve ayarlarının
yönetimi için sınıf sağlar.

Gelecekte Ayarlar sayfası ile entegre edilebilir.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from uygulama.sabitler import VARSAYILAN_YOLLAR, KOK_DIZIN

# Modül günlükleyicisi
gunluk = logging.getLogger(__name__)


@dataclass
class YapilandirmaYoneticisi:
    """
    Uygulama yapılandırmasını yöneten sınıf.
    
    Bu sınıf, uygulama yolları ve ayarlarının
    merkezi yönetimi için kullanılır.
    
    Gelecekte:
    - Ayarlar sayfasından değiştirilebilir
    - JSON/YAML dosyasına kaydedilebilir
    - Kullanıcı tercihleri saklanabilir
    
    Özellikler:
    -----------
    yollar : dict
        Uygulama yol yapılandırmaları
    ayarlar : dict
        Genel uygulama ayarları
    
    Kullanım:
    ---------
    >>> yapilandirma = YapilandirmaYoneticisi()
    >>> ui_yolu = yapilandirma.yol_al("ANA_UI")
    >>> yapilandirma.yol_ayarla("CIKTI", Path("./yeni_cikti"))
    """
    
    yollar: dict[str, Path] = field(default_factory=lambda: VARSAYILAN_YOLLAR.copy())
    ayarlar: dict[str, Any] = field(default_factory=dict)
    
    # Yapılandırma dosyası yolu
    yapilandirma_dosyasi: Optional[Path] = None
    
    def __post_init__(self):
        """Başlangıç sonrası işlemler."""
        # Varsayılan yapılandırma dosyası
        if self.yapilandirma_dosyasi is None:
            self.yapilandirma_dosyasi = KOK_DIZIN / "config.txt"
    
    def yol_al(self, anahtar: str) -> Optional[Path]:
        """
        Yapılandırılmış yolu döndürür.
        
        Parametreler:
        -------------
        anahtar : str
            Yol anahtarı (örn: "ANA_UI", "BASLIK_SABLONU")
        
        Döndürür:
        ---------
        Optional[Path]
            Path nesnesi veya None (bulunamazsa)
        """
        return self.yollar.get(anahtar)
    
    def yol_ayarla(self, anahtar: str, yol: Path | str) -> None:
        """
        Yapılandırma yolunu ayarlar.
        
        Parametreler:
        -------------
        anahtar : str
            Yol anahtarı
        yol : Path | str
            Yeni yol değeri
        """
        if isinstance(yol, str):
            yol = Path(yol)
        
        self.yollar[anahtar] = yol
        gunluk.info(f"Yapılandırma yolu güncellendi: {anahtar} = {yol}")
    
    def yol_var_mi(self, anahtar: str) -> bool:
        """
        Belirtilen yolun fiziksel olarak var olup olmadığını kontrol eder.
        
        Parametreler:
        -------------
        anahtar : str
            Yol anahtarı
        
        Döndürür:
        ---------
        bool
            Dosya/klasör varsa True
        """
        yol = self.yollar.get(anahtar)
        return yol.exists() if yol else False
    
    def ayar_al(self, anahtar: str, varsayilan: Any = None) -> Any:
        """
        Ayar değerini alır.
        
        Parametreler:
        -------------
        anahtar : str
            Ayar anahtarı
        varsayilan : Any, optional
            Bulunamazsa döndürülecek değer
        
        Döndürür:
        ---------
        Any
            Ayar değeri veya varsayılan
        """
        return self.ayarlar.get(anahtar, varsayilan)
    
    def ayar_ayarla(self, anahtar: str, deger: Any) -> None:
        """
        Ayar değerini ayarlar.
        
        Parametreler:
        -------------
        anahtar : str
            Ayar anahtarı
        deger : Any
            Yeni değer
        """
        self.ayarlar[anahtar] = deger
        gunluk.debug(f"Ayar güncellendi: {anahtar}")
    
    def config_txt_oku(self, dosya_yolu: Optional[Path] = None) -> dict[str, str]:
        """
        config.txt dosyasından yapılandırmaları okur.
        
        Dosya formatı:
        {{ANAHTAR}} = "değer"
        
        Parametreler:
        -------------
        dosya_yolu : Path, optional
            Okunacak dosya yolu (varsayılan: self.yapilandirma_dosyasi)
        
        Döndürür:
        ---------
        dict[str, str]
            Anahtar-değer çiftleri
        """
        dosya = dosya_yolu or self.yapilandirma_dosyasi
        
        if dosya is None or not dosya.exists():
            gunluk.warning(f"Yapılandırma dosyası bulunamadı: {dosya}")
            return {}
        
        sonuc: dict[str, str] = {}
        
        try:
            with dosya.open("r", encoding="utf-8") as f:
                for satir in f:
                    satir = satir.strip()
                    
                    # Boş satır veya yorum
                    if not satir or satir.startswith("#"):
                        continue
                    
                    # {{ANAHTAR}} = "değer" formatı
                    eslesme = re.match(r'\{\{(\w+)\}\}\s*=\s*"([^"]*)"', satir)
                    if eslesme:
                        anahtar = eslesme.group(1)
                        deger = eslesme.group(2)
                        sonuc[anahtar] = deger
            
            gunluk.debug(f"Yapılandırma okundu: {len(sonuc)} kayıt")
            return sonuc
        
        except Exception as e:
            gunluk.error(f"Yapılandırma okuma hatası: {e}")
            return {}
    
    def config_txt_deger_al(self, anahtar: str) -> Optional[str]:
        """
        config.txt dosyasından tek bir değer okur.
        
        Parametreler:
        -------------
        anahtar : str
            Okunacak anahtar ({{}} olmadan)
        
        Döndürür:
        ---------
        Optional[str]
            Değer veya None
        """
        yapilandirma = self.config_txt_oku()
        return yapilandirma.get(anahtar)
    
    def urun_ui_yolu(self, urun_kodu: str) -> Path:
        """
        Ürün UI dosyası yolunu döndürür.
        
        Parametreler:
        -------------
        urun_kodu : str
            Ürün kodu (örn: "LK", "ZR20")
        
        Döndürür:
        ---------
        Path
            UI dosyası yolu
        """
        from uygulama.sabitler import UI_DIZINI, UI_UZANTISI
        return UI_DIZINI / f"{urun_kodu}{UI_UZANTISI}"
    
    def urun_sablon_yolu(self, urun_kodu: str, sablon_tipi: str) -> Path:
        """
        Ürün şablon dosyası yolunu döndürür.
        
        Parametreler:
        -------------
        urun_kodu : str
            Ürün kodu (örn: "LK", "ZR20")
        sablon_tipi : str
            Şablon tipi (örn: "TANIM", "TABLO")
        
        Döndürür:
        ---------
        Path
            Şablon dosyası yolu
        """
        from uygulama.sabitler import SABLONLAR_DIZINI, BELGE_UZANTISI
        return SABLONLAR_DIZINI / f"{urun_kodu}_{sablon_tipi}{BELGE_UZANTISI}"
    
    def il_csv_yolu(self, ulke_kodu: str) -> Path:
        """
        Ülke il dosyası yolunu döndürür.
        
        Parametreler:
        -------------
        ulke_kodu : str
            ISO2 ülke kodu (örn: "TR", "DE")
        
        Döndürür:
        ---------
        Path
            İl CSV dosyası yolu
        """
        from uygulama.sabitler import VERILER_DIZINI, CSV_UZANTISI
        return VERILER_DIZINI / f"{ulke_kodu}_provinces{CSV_UZANTISI}"
    
    def dizinleri_olustur(self) -> None:
        """
        Gerekli dizinleri oluşturur (yoksa).
        
        Oluşturulan dizinler:
        - ciktilar/
        - gecici/
        - loglar/
        """
        from uygulama.sabitler import CIKTILAR_DIZINI, GECICI_DIZINI, LOGLAR_DIZINI
        
        dizinler = [CIKTILAR_DIZINI, GECICI_DIZINI, LOGLAR_DIZINI]
        
        for dizin in dizinler:
            if not dizin.exists():
                dizin.mkdir(parents=True, exist_ok=True)
                gunluk.debug(f"Dizin oluşturuldu: {dizin}")
    
    def ozet(self) -> dict[str, Any]:
        """
        Yapılandırma durumunun özetini döndürür.
        
        Döndürür:
        ---------
        dict[str, Any]
            Yapılandırma özet bilgileri
        """
        return {
            "yol_sayisi": len(self.yollar),
            "ayar_sayisi": len(self.ayarlar),
            "yapilandirma_dosyasi": str(self.yapilandirma_dosyasi),
            "mevcut_yollar": [
                anahtar for anahtar, yol in self.yollar.items()
                if yol and yol.exists()
            ],
        }


# =============================================================================
# Global Yapılandırma Nesnesi
# =============================================================================

# Varsayılan global yapılandırma nesnesi
# Dependency injection ile değiştirilebilir
yapilandirma = YapilandirmaYoneticisi()
