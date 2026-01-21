"""
Oturum Yönetimi Modülü
======================

Uygulama oturum verilerinin yönetimi.

Bu modül, form verilerinin önbelleğe alınması ve
standart girdilerin yönetimi için sınıf sağlar.

Özellikler:
-----------
- Form verisi kaydetme/geri alma
- Standart girdilerin yönetimi
- Oturum temizleme
- Gelecekte çoklu oturum desteği için hazır
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from uygulama.sabitler import STANDART_GIRDI_VARSAYILAN

# Modül günlükleyicisi
gunluk = logging.getLogger(__name__)


@dataclass
class OturumYoneticisi:
    """
    Oturum verilerini yöneten sınıf.
    
    Bu sınıf, global değişkenler yerine kullanılarak:
    - Test edilebilirlik artırılır
    - Bağımlılıklar netleşir
    - Gelecekte çoklu oturum desteği eklenebilir
    
    Özellikler:
    -----------
    form_onbellegi : dict
        Ürün formlarından toplanan veriler
        Anahtar: Form/ürün adı (örn: "LK", "ZR20")
        Değer: Widget verileri dictionary'si
    
    standart_girdiler : dict
        Ana formdan toplanan standart veriler
        (tarih, proje adı, konum vb.)
    
    Kullanım:
    ---------
    >>> oturum = OturumYoneticisi()
    >>> oturum.form_verisini_kaydet("LK", {"adet_line_1": "10"})
    >>> veri = oturum.form_verisini_al("LK")
    >>> veri["adet_line_1"]
    '10'
    """
    
    form_onbellegi: dict[str, dict[str, Any]] = field(default_factory=dict)
    standart_girdiler: dict[str, str] = field(
        default_factory=lambda: STANDART_GIRDI_VARSAYILAN.copy()
    )
    
    # Gelecekte kullanıcı bilgileri için
    kullanici_adi: Optional[str] = None
    kullanici_rolu: Optional[str] = None
    
    def form_verisini_kaydet(self, form_adi: str, veri: dict[str, Any]) -> None:
        """
        Form verisini önbelleğe kaydeder.
        
        Parametreler:
        -------------
        form_adi : str
            Form/ürün adı (örn: "LK", "ZR20")
        veri : dict[str, Any]
            Widget verileri dictionary'si
        """
        self.form_onbellegi[form_adi] = veri.copy()
        gunluk.debug(f"Form verisi kaydedildi: {form_adi} ({len(veri)} alan)")
    
    def form_verisini_al(self, form_adi: str) -> Optional[dict[str, Any]]:
        """
        Önbellekten form verisini alır.
        
        Parametreler:
        -------------
        form_adi : str
            Form/ürün adı
        
        Döndürür:
        ---------
        Optional[dict[str, Any]]
            Form verisi veya None (bulunamazsa)
        """
        return self.form_onbellegi.get(form_adi)
    
    def form_verisi_var_mi(self, form_adi: str) -> bool:
        """
        Belirtilen form için önbellekte veri var mı kontrol eder.
        
        Parametreler:
        -------------
        form_adi : str
            Form/ürün adı
        
        Döndürür:
        ---------
        bool
            Veri varsa True
        """
        return form_adi in self.form_onbellegi
    
    def form_verisini_sil(self, form_adi: str) -> bool:
        """
        Belirtilen formun verisini önbellekten siler.
        
        Parametreler:
        -------------
        form_adi : str
            Form/ürün adı
        
        Döndürür:
        ---------
        bool
            Silme başarılı ise True
        """
        if form_adi in self.form_onbellegi:
            del self.form_onbellegi[form_adi]
            gunluk.debug(f"Form verisi silindi: {form_adi}")
            return True
        return False
    
    def kayitli_form_listesi(self) -> list[str]:
        """
        Önbellekte kayıtlı form adlarını döndürür.
        
        Döndürür:
        ---------
        list[str]
            Form adları listesi
        """
        return list(self.form_onbellegi.keys())
    
    def standart_girdi_guncelle(self, anahtar: str, deger: str) -> None:
        """
        Standart girdi değerini günceller.
        
        Parametreler:
        -------------
        anahtar : str
            Girdi anahtarı (örn: "PROJEADI", "PROJEKONUM")
        deger : str
            Yeni değer
        """
        self.standart_girdiler[anahtar] = deger
        gunluk.debug(f"Standart girdi güncellendi: {anahtar}")
    
    def standart_girdi_al(self, anahtar: str, varsayilan: str = "") -> str:
        """
        Standart girdi değerini alır.
        
        Parametreler:
        -------------
        anahtar : str
            Girdi anahtarı
        varsayilan : str, optional
            Bulunamazsa döndürülecek değer (varsayılan: "")
        
        Döndürür:
        ---------
        str
            Girdi değeri veya varsayılan
        """
        return self.standart_girdiler.get(anahtar, varsayilan)
    
    def tum_standart_girdileri_guncelle(self, girdiler: dict[str, str]) -> None:
        """
        Tüm standart girdileri toplu günceller.
        
        Parametreler:
        -------------
        girdiler : dict[str, str]
            Güncellenecek girdi dictionary'si
        """
        self.standart_girdiler.update(girdiler)
        gunluk.debug(f"Standart girdiler toplu güncellendi: {len(girdiler)} alan")
    
    def standart_girdileri_sifirla(self) -> None:
        """Standart girdileri varsayılan değerlere sıfırlar."""
        self.standart_girdiler = STANDART_GIRDI_VARSAYILAN.copy()
        gunluk.debug("Standart girdiler sıfırlandı")
    
    def form_onbellegini_temizle(self) -> None:
        """Tüm form önbelleğini temizler."""
        self.form_onbellegi.clear()
        gunluk.info("Form önbelleği temizlendi")
    
    def temizle(self) -> None:
        """
        Tüm oturum verilerini temizler.
        
        Form önbelleği ve standart girdiler sıfırlanır.
        """
        self.form_onbellegi.clear()
        self.standart_girdiler = STANDART_GIRDI_VARSAYILAN.copy()
        gunluk.info("Tüm oturum verileri temizlendi")
    
    def urun_ebat_cikar(self, urun_adi: str) -> str:
        """
        Ürün için ebat bilgisini çıkarır.
        
        Öncelik sırası:
        1. kasaolc_line (hazır ebat)
        2. kapaken_line + kapakboy_line (hesaplanmış ebat)
        3. "-" (varsayılan)
        
        Parametreler:
        -------------
        urun_adi : str
            Ürün adı/kodu
        
        Döndürür:
        ---------
        str
            Ebat metni veya "-"
        """
        veri = self.form_verisini_al(urun_adi) or {}
        
        # Hazır ebat alanı
        ebat = str(veri.get("kasaolc_line", "")).strip()
        if ebat:
            return ebat
        
        # Kapak en/boy'dan hesapla
        en = str(veri.get("kapaken_line", "")).strip()
        boy = str(veri.get("kapakboy_line", "")).strip()
        if en and boy:
            try:
                en_f = float(en)
                boy_f = float(boy)
                return f"{en_f} x {boy_f} cm"
            except ValueError:
                pass
        
        return "-"
    
    def ozet(self) -> dict[str, Any]:
        """
        Oturum durumunun özetini döndürür.
        
        Döndürür:
        ---------
        dict[str, Any]
            Oturum özet bilgileri
        """
        return {
            "kayitli_form_sayisi": len(self.form_onbellegi),
            "kayitli_formlar": self.kayitli_form_listesi(),
            "standart_girdi_sayisi": len(self.standart_girdiler),
            "kullanici_adi": self.kullanici_adi,
            "kullanici_rolu": self.kullanici_rolu,
        }


# =============================================================================
# Global Oturum Nesnesi
# =============================================================================

# Varsayılan global oturum nesnesi
# Dependency injection ile değiştirilebilir
oturum = OturumYoneticisi()
