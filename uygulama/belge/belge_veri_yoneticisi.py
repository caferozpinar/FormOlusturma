"""
Belge Veri Yöneticisi - SQLite Backend (v2.0)
==============================================

Word belgelerinin form verilerini merkezi SQLite veritabanında saklar.

Değişiklikler (v1.0 → v2.0):
- ✗ Artık .ztf dosyası oluşturulmaz
- ✓ Tüm veriler SQLite'da saklanır
- ✓ Geriye dönük uyumluluk: Eski .ztf dosyalarını okuyabilir
- ✓ Hızlı sorgulama (dosya adı, seri numarası)

Avantajlar:
- Merkezi veri yönetimi
- Platform bağımsız (SQLite built-in)
- Minimal disk kullanımı
- Concurrent-safe
"""

import json
import gzip
from pathlib import Path
from datetime import datetime
from typing import Any, Optional
import logging

# SQLite backend'i import et
try:
    from uygulama.veri.belge_onbellegi import BelgeOnbellegi
except ImportError:
    try:
        # Geliştirme ortamı için
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent / 'veri'))
        from belge_onbellegi import BelgeOnbellegi
    except ImportError:
        # Test için
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from belge_onbellegi import BelgeOnbellegi

gunluk = logging.getLogger(__name__)


class BelgeVeriYoneticisi:
    """
    Word belgelerinin form verilerini SQLite veritabanında saklar.
    
    v2.0 Değişiklikleri:
    -------------------
    - Artık .ztf dosyası oluşturmaz
    - Tüm veriler merkezi SQLite veritabanında
    - Eski .ztf dosyalarını okuyabilir (geriye dönük uyumluluk)
    
    Kullanım:
    ---------
    >>> yonetici = BelgeVeriYoneticisi()
    >>> 
    >>> # Veri yazma (SQLite'a kaydeder)
    >>> yonetici.veri_kaydet(
    ...     belge_yolu='PROJE-123.docx',
    ...     standart_girdiler={...},
    ...     oturum_onbellegi={...},
    ...     urun_kodlari=[...]
    ... )
    >>> 
    >>> # Veri okuma (SQLite'dan okur, bulamazsa .ztf'den okur)
    >>> veriler = yonetici.veri_yukle('PROJE-123.docx')
    """
    
    def __init__(self, veritabani_yolu: Optional[str | Path] = None):
        """
        Parametreler:
        -------------
        veritabani_yolu : str | Path | None
            SQLite veritabanı yolu. None ise varsayılan: ./veri/belge_onbellegi.db
        """
        # SQLite backend
        self.onbellek = BelgeOnbellegi(veritabani_yolu)
        
        gunluk.debug("BelgeVeriYoneticisi (v2.0) - SQLite backend aktif")
    
    def _ztf_yolu_al(self, belge_yolu: str | Path) -> Path:
        """
        Belge yolundan .ztf dosya yolunu oluşturur.
        
        Not: Sadece geriye dönük uyumluluk için kullanılır.
        """
        belge_yolu = Path(belge_yolu)
        ztf_yolu = belge_yolu.with_suffix('.ztf')
        return ztf_yolu
    
    def _ztf_dosyasindan_oku(
        self,
        ztf_yolu: Path,
        logger: Optional[logging.Logger] = None
    ) -> Optional[dict[str, Any]]:
        """
        Eski .ztf dosyasından veri okur (geriye dönük uyumluluk).
        
        Parametreler:
        -------------
        ztf_yolu : Path
            .ztf dosya yolu
        logger : Logger
            Logger referansı
        
        Döndürür:
        ---------
        Optional[dict]
            Veri veya None
        """
        log = logger or gunluk
        
        try:
            if not ztf_yolu.exists():
                return None
            
            log.info(f"Eski .ztf dosyası okunuyor: {ztf_yolu.name}")
            
            # İlk 2 byte'ı kontrol et (gzip magic number)
            ilk_byteler = ztf_yolu.read_bytes()[:2]
            
            if ilk_byteler == b'\x1f\x8b':  # GZIP
                sikistirilmis = ztf_yolu.read_bytes()
                json_bytes = gzip.decompress(sikistirilmis)
                json_str = json_bytes.decode('utf-8')
            else:
                # Düz JSON
                json_str = ztf_yolu.read_text(encoding='utf-8')
            
            veri = json.loads(json_str)
            
            log.info(f"✓ Eski .ztf dosyası okundu: {ztf_yolu.name}")
            log.warning("  Not: Bu veri SQLite'a aktarılmalı")
            
            return veri
            
        except Exception as e:
            log.error(f"HATA: .ztf okuma başarısız: {e}")
            return None
    
    def veri_kaydet(
        self,
        belge_yolu: str | Path,
        standart_girdiler: dict[str, str],
        oturum_onbellegi: dict[str, dict[str, Any]],
        urun_kodlari: list[str],
        seri_numarasi: str,
        dosya_adi: str,
        logger: Optional[logging.Logger] = None
    ) -> bool:
        """
        Belge verilerini SQLite veritabanına kaydeder.
        
        Not: Artık .ztf dosyası oluşturulmaz!
        
        Parametreler:
        -------------
        belge_yolu : str | Path
            Word belgesi yolu
        standart_girdiler : dict
            Form standart girdileri
        oturum_onbellegi : dict
            Ürün form verileri
        urun_kodlari : list
            Seçili ürün kodları
        seri_numarasi : str
            Belge seri numarası
        dosya_adi : str
            Belge dosya adı
        logger : Logger
            Logger referansı
        
        Döndürür:
        ---------
        bool
            Başarılı ise True
        """
        log = logger or gunluk
        
        try:
            # Veri yapısını oluştur
            veri = {
                'standart_girdiler': standart_girdiler,
                'oturum_onbellegi': oturum_onbellegi,
                'urun_kodlari': urun_kodlari,
            }
            
            # SQLite'a kaydet
            basarili = self.onbellek.kaydet(
                dosya_adi=dosya_adi,
                seri_numarasi=seri_numarasi,
                veri=veri,
                logger=log
            )
            
            if basarili:
                log.info(f"✓ Belge SQLite'a kaydedildi: {dosya_adi}")
            else:
                log.error(f"✗ Belge kaydedilemedi: {dosya_adi}")
            
            return basarili
            
        except Exception as e:
            log.error(f"HATA: Veri kaydetme başarısız: {e}")
            import traceback
            log.error(traceback.format_exc())
            return False
    
    def veri_yukle(
        self,
        belge_yolu: str | Path,
        logger: Optional[logging.Logger] = None
    ) -> Optional[dict[str, Any]]:
        """
        Belge verilerini yükler.
        
        Arama sırası:
        1. SQLite veritabanından ara
        2. Bulamazsa eski .ztf dosyasından oku (geriye dönük uyumluluk)
        
        Parametreler:
        -------------
        belge_yolu : str | Path
            Word belgesi yolu veya dosya adı
        logger : Logger
            Logger referansı
        
        Döndürür:
        ---------
        Optional[dict]
            Belge verileri veya None (hata durumunda)
            
        Dönen yapı:
        {
            'dosya_adi': '...',
            'seri_numarasi': '...',
            'olusturma_tarihi': '...',
            'standart_girdiler': {...},
            'oturum_onbellegi': {...},
            'urun_kodlari': [...]
        }
        """
        log = logger or gunluk
        
        try:
            # Dosya adını al
            belge_yolu = Path(belge_yolu)
            dosya_adi = belge_yolu.stem  # .docx olmadan
            
            # 1. SQLite'dan yükle
            veri = self.onbellek.yukle(dosya_adi, logger=log)
            
            if veri:
                return veri
            
            # 2. Eski .ztf dosyasından yükle (geriye dönük uyumluluk)
            log.info(f"SQLite'da bulunamadı, .ztf dosyası aranıyor...")
            ztf_yolu = self._ztf_yolu_al(belge_yolu)
            veri = self._ztf_dosyasindan_oku(ztf_yolu, logger=log)
            
            if veri:
                log.warning("⚠ Eski .ztf dosyası kullanıldı. SQLite'a aktarılması önerilir.")
                return veri
            
            # 3. Hiçbir yerde bulunamadı
            log.warning(f"Belge verisi bulunamadı: {dosya_adi}")
            return None
            
        except Exception as e:
            log.error(f"HATA: Veri yükleme başarısız: {e}")
            import traceback
            log.error(traceback.format_exc())
            return None
    
    def veri_var_mi(
        self,
        belge_yolu: str | Path,
        logger: Optional[logging.Logger] = None
    ) -> bool:
        """
        Belge için veri var mı kontrol eder.
        
        SQLite veya .ztf dosyasında arar.
        
        Parametreler:
        -------------
        belge_yolu : str | Path
            Word belgesi yolu
        logger : Logger
            Logger referansı
        
        Döndürür:
        ---------
        bool
            Veri varsa True
        """
        log = logger or gunluk
        
        try:
            belge_yolu = Path(belge_yolu)
            dosya_adi = belge_yolu.stem
            
            # SQLite'da var mı?
            if self.onbellek.var_mi(dosya_adi, logger=log):
                return True
            
            # Eski .ztf dosyası var mı?
            ztf_yolu = self._ztf_yolu_al(belge_yolu)
            return ztf_yolu.exists()
            
        except Exception as e:
            log.error(f"HATA: Varlık kontrolü başarısız: {e}")
            return False
    
    def veri_sil(
        self,
        belge_yolu: str | Path,
        logger: Optional[logging.Logger] = None
    ) -> bool:
        """
        Belge verilerini siler (hem SQLite hem .ztf).
        
        Parametreler:
        -------------
        belge_yolu : str | Path
            Word belgesi yolu
        logger : Logger
            Logger referansı
        
        Döndürür:
        ---------
        bool
            Başarılı ise True
        """
        log = logger or gunluk
        
        try:
            belge_yolu = Path(belge_yolu)
            dosya_adi = belge_yolu.stem
            
            # SQLite'dan sil
            sqlite_silindi = self.onbellek.sil(dosya_adi, logger=log)
            
            # Eski .ztf dosyasını da sil (varsa)
            ztf_yolu = self._ztf_yolu_al(belge_yolu)
            ztf_silindi = True
            
            if ztf_yolu.exists():
                try:
                    ztf_yolu.unlink()
                    log.info(f"✓ Eski .ztf dosyası silindi: {ztf_yolu.name}")
                except Exception as e:
                    log.warning(f"⚠ .ztf silme başarısız: {e}")
                    ztf_silindi = False
            
            return sqlite_silindi and ztf_silindi
            
        except Exception as e:
            log.error(f"HATA: Veri silme başarısız: {e}")
            return False
    
    # Yeni metodlar: SQLite'ın gücünden yararlanma
    
    def seri_ile_yukle(
        self,
        seri_numarasi: str,
        logger: Optional[logging.Logger] = None
    ) -> Optional[dict[str, Any]]:
        """
        Seri numarası ile belge verilerini yükler.
        
        Not: Sadece SQLite'dan yükler, .ztf desteği yok.
        
        Parametreler:
        -------------
        seri_numarasi : str
            Belge seri numarası
        logger : Logger
            Logger referansı
        
        Döndürür:
        ---------
        Optional[dict]
            Belge verileri veya None
        """
        return self.onbellek.seri_ile_yukle(seri_numarasi, logger=logger)
    
    def tum_belgeleri_listele(
        self,
        limit: Optional[int] = None,
        logger: Optional[logging.Logger] = None
    ) -> list[dict[str, str]]:
        """
        Tüm belgeleri listeler (metadata).
        
        Not: Sadece SQLite'dan listeler.
        
        Parametreler:
        -------------
        limit : int | None
            Maksimum kayıt sayısı
        logger : Logger
            Logger referansı
        
        Döndürür:
        ---------
        list[dict]
            Belge metadata listesi
        """
        return self.onbellek.tum_belgeleri_listele(limit=limit, logger=logger)
    
    def istatistikler(
        self,
        logger: Optional[logging.Logger] = None
    ) -> dict[str, Any]:
        """
        Veritabanı istatistiklerini döner.
        
        Döndürür:
        ---------
        dict
            İstatistikler
        """
        return self.onbellek.istatistikler(logger=logger)


# Test
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("=" * 60)
    print("BELGE VERİ YÖNETİCİSİ v2.0 - TEST")
    print("=" * 60)
    
    # Test verileri
    standart_girdiler = {
        'PROJEADI': 'Test Projesi v2',
        'PROJEKONUM': 'İstanbul',
        'DUZENLEYEN': 'Cafer',
        'CURDATE': '2025-12-31',
    }
    
    oturum_onbellegi = {
        'ZR20': {
            'urun_label_1': 'Panel 100x200',
            'adet_line_1': '10',
        }
    }
    
    urun_kodlari = ['ZR20', 'LK']
    
    # Yönetici oluştur
    yonetici = BelgeVeriYoneticisi()
    
    print("\n1. Veri kaydetme (SQLite)...")
    basarili = yonetici.veri_kaydet(
        belge_yolu='TEST-V2-123.docx',
        standart_girdiler=standart_girdiler,
        oturum_onbellegi=oturum_onbellegi,
        urun_kodlari=urun_kodlari,
        seri_numarasi='V2TEST',
        dosya_adi='TEST-V2-123'
    )
    
    if basarili:
        print("\n2. Veri yükleme (SQLite)...")
        veriler = yonetici.veri_yukle('TEST-V2-123.docx')
        
        if veriler:
            print("\n3. Karşılaştırma...")
            if veriler['standart_girdiler'] == standart_girdiler:
                print("   ✓ Standart girdiler eşleşiyor")
            if veriler['oturum_onbellegi'] == oturum_onbellegi:
                print("   ✓ Oturum önbelleği eşleşiyor")
            if veriler['urun_kodlari'] == urun_kodlari:
                print("   ✓ Ürün kodları eşleşiyor")
            
            print("\n4. Seri ile yükleme...")
            veriler2 = yonetici.seri_ile_yukle('V2TEST')
            if veriler2:
                print(f"   ✓ Seri ile yüklendi: {veriler2['dosya_adi']}")
            
            print("\n5. İstatistikler...")
            istatistikler = yonetici.istatistikler()
            print(f"   ✓ Toplam belge: {istatistikler['toplam_belge']}")
            
            print("\n✅ TEST BAŞARILI!")
        else:
            print("❌ Veri yükleme başarısız")
    else:
        print("❌ Veri kaydetme başarısız")
