"""
Log Yöneticisi Modülü
=====================

Otomatik temizlik ve kritik hata işaretleme ile log yönetimi.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

from uygulama.sabitler import (
    LOGLAR_DIZINI,
    MAKSIMUM_LOG_SAYISI,
    MAKSIMUM_LOG_YASI_GUN,
    LOG_FORMATI,
    LOG_TARIH_FORMATI,
)


class LogYoneticisi:
    """
    Otomatik dosya temizliği ve kritik hata işaretleme ile log yönetimi.
    
    Özellikler:
    -----------
    - Günlük log dosyası oluşturma
    - Eski logları otomatik temizleme (yaş ve sayıya göre)
    - Kritik hataları işaretleyerek koruma
    """
    
    def __init__(
        self,
        log_dizini: str | Path = LOGLAR_DIZINI,
        maksimum_log: int = MAKSIMUM_LOG_SAYISI,
        maksimum_yas_gun: int = MAKSIMUM_LOG_YASI_GUN
    ):
        self.log_dizini = Path(log_dizini)
        self.maksimum_log = maksimum_log
        self.maksimum_yas_gun = maksimum_yas_gun
        self.kritik_isaretleyici = ".CRITICAL"
        
        # Log dizinini oluştur
        self.log_dizini.mkdir(parents=True, exist_ok=True)
        
        # Logger'ı ayarla
        self.gunlukleyici = self._gunlukleyici_ayarla()
        
        # Eski logları temizle
        self._eski_loglari_temizle()
    
    def _gunlukleyici_ayarla(self) -> logging.Logger:
        """Logger'ı dosya handler ile ayarlar."""
        gunlukleyici = logging.getLogger("BelgeOlusturucu")
        gunlukleyici.setLevel(logging.DEBUG)
        
        # Tekrar handler eklemeyi önle
        if gunlukleyici.handlers:
            return gunlukleyici
        
        # Dosya handler
        log_dosya_adi = f"belge_olusturucu_{datetime.now().strftime('%Y%m%d')}.log"
        log_yolu = self.log_dizini / log_dosya_adi
        
        dosya_handler = logging.FileHandler(log_yolu, encoding='utf-8')
        dosya_handler.setLevel(logging.DEBUG)
        
        bicimleyici = logging.Formatter(LOG_FORMATI, datefmt=LOG_TARIH_FORMATI)
        dosya_handler.setFormatter(bicimleyici)
        
        gunlukleyici.addHandler(dosya_handler)
        return gunlukleyici
    
    def _eski_loglari_temizle(self) -> None:
        """Yaş ve sayıya göre eski log dosyalarını siler."""
        try:
            log_dosyalari = []
            kritik_dosyalar = []
            
            # Normal ve kritik logları ayır
            for dosya in self.log_dizini.glob("belge_olusturucu_*.log"):
                isaretleyici = self.log_dizini / f"{dosya.name}{self.kritik_isaretleyici}"
                if isaretleyici.exists():
                    kritik_dosyalar.append(dosya)
                else:
                    log_dosyalari.append(dosya)
            
            # Değişiklik zamanına göre sırala (en eski önce)
            log_dosyalari.sort(key=lambda x: x.stat().st_mtime)
            
            # Yaşa göre sil
            kesim_tarihi = datetime.now() - timedelta(days=self.maksimum_yas_gun)
            silinen = 0
            
            for log_dosya in log_dosyalari[:]:
                dosya_zamani = datetime.fromtimestamp(log_dosya.stat().st_mtime)
                if dosya_zamani < kesim_tarihi:
                    log_dosya.unlink()
                    log_dosyalari.remove(log_dosya)
                    silinen += 1
            
            if silinen > 0:
                self.gunlukleyici.info(f"Temizlik: {silinen} eski log dosyası silindi (>{self.maksimum_yas_gun} gün)")
            
            # Sayıya göre sil
            if len(log_dosyalari) > self.maksimum_log:
                fazla = len(log_dosyalari) - self.maksimum_log
                for log_dosya in log_dosyalari[:fazla]:
                    log_dosya.unlink()
                
                self.gunlukleyici.info(f"Temizlik: {fazla} fazla log dosyası silindi (max {self.maksimum_log})")
            
            if kritik_dosyalar:
                self.gunlukleyici.info(f"Temizlik: {len(kritik_dosyalar)} kritik log dosyası korundu")
        
        except Exception as e:
            self.gunlukleyici.warning(f"UYARI: Log temizleme başarısız: {e}")
    
    def kritik_isaretle(self) -> None:
        """Mevcut log dosyasını kritik olarak işaretler (otomatik silmeyi önler)."""
        log_dosya_adi = f"belge_olusturucu_{datetime.now().strftime('%Y%m%d')}.log"
        isaretleyici_yolu = self.log_dizini / f"{log_dosya_adi}{self.kritik_isaretleyici}"
        
        try:
            isaretleyici_yolu.touch()
            self.gunlukleyici.error("=" * 60)
            self.gunlukleyici.error("KRİTİK HATA OLUŞTU - LOG DOSYASI KORUNMAK ÜZERE İŞARETLENDİ")
            self.gunlukleyici.error("=" * 60)
        except Exception as e:
            self.gunlukleyici.error(f"HATA: Kritik işaretleme başarısız: {e}")
