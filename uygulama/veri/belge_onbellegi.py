"""
Belge Önbellek Yöneticisi - SQLite Backend
==========================================

Belge verilerini merkezi SQLite veritabanında saklar.
Her belge için ayrı .ztf dosyası yerine tek veritabanı.

Avantajlar:
- Merkezi veri yönetimi
- Hızlı sorgulama (dosya adı, seri numarası)
- Platform bağımsız (Python built-in)
- Concurrent-safe (SQLite locking)
- Minimal disk kullanımı
"""

import sqlite3
import json
import gzip
import base64
from pathlib import Path
from datetime import datetime
from typing import Any, Optional
import logging
from contextlib import contextmanager

gunluk = logging.getLogger(__name__)


class BelgeOnbellegi:
    """
    Belge verilerini SQLite veritabanında saklar ve yönetir.
    
    Kullanım:
    ---------
    >>> onbellek = BelgeOnbellegi()
    >>> 
    >>> # Veri kaydetme
    >>> onbellek.kaydet(
    ...     dosya_adi='IZELTAS-080126-59HOY1-R01',
    ...     seri_numarasi='59HOY1',
    ...     veri={'standart_girdiler': {...}, ...}
    ... )
    >>> 
    >>> # Dosya adı ile arama
    >>> veri = onbellek.yukle('IZELTAS-080126-59HOY1-R01')
    >>> 
    >>> # Seri numarası ile arama
    >>> veri = onbellek.seri_ile_yukle('59HOY1')
    >>> 
    >>> # Tüm belgeler
    >>> belgeler = onbellek.tum_belgeleri_listele()
    """
    
    def __init__(self, veritabani_yolu: Optional[str | Path] = None):
        """
        Parametreler:
        -------------
        veritabani_yolu : str | Path | None
            SQLite veritabanı dosya yolu.
            None ise varsayılan: ./veri/belge_onbellegi.db
        """
        if veritabani_yolu is None:
            # Varsayılan konum: ./veri/belge_onbellegi.db
            veri_klasoru = Path('./veri')
            veri_klasoru.mkdir(exist_ok=True)
            self.veritabani_yolu = veri_klasoru / 'belge_onbellegi.db'
        else:
            self.veritabani_yolu = Path(veritabani_yolu)
            self.veritabani_yolu.parent.mkdir(parents=True, exist_ok=True)
        
        # Veritabanını başlat
        self._veritabani_baslat()
    
    @contextmanager
    def _baglanti_al(self):
        """Veritabanı bağlantısı context manager"""
        baglanti = sqlite3.connect(str(self.veritabani_yolu))
        baglanti.row_factory = sqlite3.Row  # Dict-like access
        try:
            yield baglanti
            baglanti.commit()
        except Exception as e:
            baglanti.rollback()
            raise e
        finally:
            baglanti.close()
    
    def _veritabani_baslat(self):
        """Veritabanı tablolarını oluşturur (yoksa)"""
        with self._baglanti_al() as baglanti:
            imlec = baglanti.cursor()
            
            # Ana tablo
            imlec.execute("""
                CREATE TABLE IF NOT EXISTS belge_verileri (
                    dosya_adi TEXT PRIMARY KEY,
                    seri_numarasi TEXT NOT NULL,
                    veri_json TEXT NOT NULL,
                    olusturma_tarihi TEXT NOT NULL,
                    guncelleme_tarihi TEXT NOT NULL,
                    uygulama_surumu TEXT
                )
            """)
            
            # Seri numarası index
            imlec.execute("""
                CREATE INDEX IF NOT EXISTS idx_seri 
                ON belge_verileri(seri_numarasi)
            """)
            
            # Oluşturma tarihi index (sıralama için)
            imlec.execute("""
                CREATE INDEX IF NOT EXISTS idx_olusturma 
                ON belge_verileri(olusturma_tarihi DESC)
            """)
            
            gunluk.debug(f"Veritabanı hazır: {self.veritabani_yolu}")
    
    def _veriyi_sikistir(self, veri: dict) -> str:
        """
        Veriyi sıkıştırır ve base64 string'e çevirir.
        
        Parametreler:
        -------------
        veri : dict
            Sıkıştırılacak veri
        
        Döndürür:
        ---------
        str
            Base64 encoded, gzip compressed JSON
        """
        # JSON'a çevir
        json_str = json.dumps(veri, ensure_ascii=False)
        json_bytes = json_str.encode('utf-8')
        
        # GZIP ile sıkıştır
        sikistirilmis = gzip.compress(json_bytes, compresslevel=9)
        
        # Base64 encode (SQLite TEXT için)
        base64_str = base64.b64encode(sikistirilmis).decode('ascii')
        
        return base64_str
    
    def _veriyi_ac(self, sikistirilmis_str: str) -> dict:
        """
        Sıkıştırılmış veriyi açar.
        
        Parametreler:
        -------------
        sikistirilmis_str : str
            Base64 encoded, gzip compressed JSON
        
        Döndürür:
        ---------
        dict
            Açılmış veri
        """
        # Base64 decode
        sikistirilmis = base64.b64decode(sikistirilmis_str.encode('ascii'))
        
        # GZIP decompress
        json_bytes = gzip.decompress(sikistirilmis)
        json_str = json_bytes.decode('utf-8')
        
        # JSON parse
        veri = json.loads(json_str)
        
        return veri
    
    def kaydet(
        self,
        dosya_adi: str,
        seri_numarasi: str,
        veri: dict[str, Any],
        uygulama_surumu: str = '2.0.0',
        logger: Optional[logging.Logger] = None
    ) -> bool:
        """
        Belge verilerini veritabanına kaydeder.
        
        Parametreler:
        -------------
        dosya_adi : str
            Belge dosya adı (örn: 'IZELTAS-080126-59HOY1-R01')
        seri_numarasi : str
            Belge seri numarası (örn: '59HOY1')
        veri : dict
            Kaydedilecek veri yapısı:
            {
                'standart_girdiler': {...},
                'oturum_onbellegi': {...},
                'urun_kodlari': [...]
            }
        uygulama_surumu : str
            Uygulama sürüm numarası
        logger : Logger
            Logger referansı
        
        Döndürür:
        ---------
        bool
            Başarılı ise True
        """
        log = logger or gunluk
        
        try:
            # Mevcut kayıt var mı kontrol et
            mevcut = self.yukle(dosya_adi, logger=log)
            
            # Veriyi sıkıştır
            orijinal_boyut = len(json.dumps(veri, ensure_ascii=False).encode('utf-8'))
            sikistirilmis_veri = self._veriyi_sikistir(veri)
            sikistirilmis_boyut = len(sikistirilmis_veri)
            
            # Zaman damgaları
            simdi = datetime.now().isoformat()
            olusturma_tarihi = mevcut.get('olusturma_tarihi', simdi) if mevcut else simdi
            
            # Veritabanına kaydet
            with self._baglanti_al() as baglanti:
                imlec = baglanti.cursor()
                
                imlec.execute("""
                    INSERT OR REPLACE INTO belge_verileri
                    (dosya_adi, seri_numarasi, veri_json, olusturma_tarihi, 
                     guncelleme_tarihi, uygulama_surumu)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    dosya_adi,
                    seri_numarasi,
                    sikistirilmis_veri,
                    olusturma_tarihi,
                    simdi,
                    uygulama_surumu
                ))
            
            # İstatistikler
            oran = (1 - sikistirilmis_boyut / orijinal_boyut) * 100
            
            if mevcut:
                log.info(f"✓ Belge güncellendi: {dosya_adi}")
            else:
                log.info(f"✓ Belge kaydedildi: {dosya_adi}")
            
            log.info(f"  - Seri: {seri_numarasi}")
            log.info(f"  - Orijinal: {orijinal_boyut:,} byte")
            log.info(f"  - Sıkıştırılmış: {sikistirilmis_boyut:,} byte")
            log.info(f"  - Kazanç: %{oran:.1f}")
            
            return True
            
        except Exception as e:
            log.error(f"HATA: Belge kaydetme başarısız: {e}")
            import traceback
            log.error(traceback.format_exc())
            return False
    
    def yukle(
        self,
        dosya_adi: str,
        logger: Optional[logging.Logger] = None
    ) -> Optional[dict[str, Any]]:
        """
        Dosya adı ile belge verilerini yükler.
        
        Parametreler:
        -------------
        dosya_adi : str
            Belge dosya adı (örn: 'IZELTAS-080126-59HOY1-R01' veya 
                              'IZELTAS-080126-59HOY1-R01.docx')
        logger : Logger
            Logger referansı
        
        Döndürür:
        ---------
        Optional[dict]
            Belge verileri veya None (bulunamazsa)
            
        Dönen yapı:
        {
            'dosya_adi': '...',
            'seri_numarasi': '...',
            'olusturma_tarihi': '...',
            'guncelleme_tarihi': '...',
            'uygulama_surumu': '...',
            'standart_girdiler': {...},
            'oturum_onbellegi': {...},
            'urun_kodlari': [...]
        }
        """
        log = logger or gunluk
        
        try:
            # .docx uzantısını kaldır (varsa)
            if dosya_adi.endswith('.docx'):
                dosya_adi = dosya_adi[:-5]
            
            with self._baglanti_al() as baglanti:
                imlec = baglanti.cursor()
                
                imlec.execute("""
                    SELECT * FROM belge_verileri
                    WHERE dosya_adi = ?
                """, (dosya_adi,))
                
                satir = imlec.fetchone()
                
                if not satir:
                    log.warning(f"Belge bulunamadı: {dosya_adi}")
                    return None
                
                # Veriyi aç
                veri = self._veriyi_ac(satir['veri_json'])
                
                # Metadata ekle
                veri['dosya_adi'] = satir['dosya_adi']
                veri['seri_numarasi'] = satir['seri_numarasi']
                veri['olusturma_tarihi'] = satir['olusturma_tarihi']
                veri['guncelleme_tarihi'] = satir['guncelleme_tarihi']
                veri['uygulama_surumu'] = satir['uygulama_surumu']
                
                log.info(f"✓ Belge yüklendi: {dosya_adi}")
                log.info(f"  - Seri: {satir['seri_numarasi']}")
                log.info(f"  - Proje: {veri.get('standart_girdiler', {}).get('PROJEADI', 'N/A')}")
                log.info(f"  - Ürünler: {', '.join(veri.get('urun_kodlari', []))}")
                
                return veri
                
        except Exception as e:
            log.error(f"HATA: Belge yükleme başarısız: {e}")
            import traceback
            log.error(traceback.format_exc())
            return None
    
    def seri_ile_yukle(
        self,
        seri_numarasi: str,
        logger: Optional[logging.Logger] = None
    ) -> Optional[dict[str, Any]]:
        """
        Seri numarası ile belge verilerini yükler.
        
        Not: Aynı seri numarasına sahip birden fazla belge varsa,
        en son güncelleneni döner.
        
        Parametreler:
        -------------
        seri_numarasi : str
            Belge seri numarası (örn: '59HOY1')
        logger : Logger
            Logger referansı
        
        Döndürür:
        ---------
        Optional[dict]
            Belge verileri veya None (bulunamazsa)
        """
        log = logger or gunluk
        
        try:
            with self._baglanti_al() as baglanti:
                imlec = baglanti.cursor()
                
                imlec.execute("""
                    SELECT * FROM belge_verileri
                    WHERE seri_numarasi = ?
                    ORDER BY guncelleme_tarihi DESC
                    LIMIT 1
                """, (seri_numarasi,))
                
                satir = imlec.fetchone()
                
                if not satir:
                    log.warning(f"Seri numarası bulunamadı: {seri_numarasi}")
                    return None
                
                # Veriyi aç
                veri = self._veriyi_ac(satir['veri_json'])
                
                # Metadata ekle
                veri['dosya_adi'] = satir['dosya_adi']
                veri['seri_numarasi'] = satir['seri_numarasi']
                veri['olusturma_tarihi'] = satir['olusturma_tarihi']
                veri['guncelleme_tarihi'] = satir['guncelleme_tarihi']
                veri['uygulama_surumu'] = satir['uygulama_surumu']
                
                log.info(f"✓ Belge yüklendi (seri): {seri_numarasi}")
                log.info(f"  - Dosya: {satir['dosya_adi']}")
                log.info(f"  - Proje: {veri.get('standart_girdiler', {}).get('PROJEADI', 'N/A')}")
                
                return veri
                
        except Exception as e:
            log.error(f"HATA: Seri ile yükleme başarısız: {e}")
            import traceback
            log.error(traceback.format_exc())
            return None
    
    def var_mi(
        self,
        dosya_adi: str,
        logger: Optional[logging.Logger] = None
    ) -> bool:
        """
        Belge önbellekte var mı kontrol eder.
        
        Parametreler:
        -------------
        dosya_adi : str
            Belge dosya adı
        logger : Logger
            Logger referansı
        
        Döndürür:
        ---------
        bool
            Belge varsa True
        """
        try:
            # .docx uzantısını kaldır (varsa)
            if dosya_adi.endswith('.docx'):
                dosya_adi = dosya_adi[:-5]
            
            with self._baglanti_al() as baglanti:
                imlec = baglanti.cursor()
                
                imlec.execute("""
                    SELECT COUNT(*) FROM belge_verileri
                    WHERE dosya_adi = ?
                """, (dosya_adi,))
                
                adet = imlec.fetchone()[0]
                return adet > 0
                
        except Exception as e:
            log = logger or gunluk
            log.error(f"HATA: Varlık kontrolü başarısız: {e}")
            return False
    
    def sil(
        self,
        dosya_adi: str,
        logger: Optional[logging.Logger] = None
    ) -> bool:
        """
        Belge verilerini önbellekten siler.
        
        Parametreler:
        -------------
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
            # .docx uzantısını kaldır (varsa)
            if dosya_adi.endswith('.docx'):
                dosya_adi = dosya_adi[:-5]
            
            with self._baglanti_al() as baglanti:
                imlec = baglanti.cursor()
                
                imlec.execute("""
                    DELETE FROM belge_verileri
                    WHERE dosya_adi = ?
                """, (dosya_adi,))
                
                if imlec.rowcount > 0:
                    log.info(f"✓ Belge silindi: {dosya_adi}")
                    return True
                else:
                    log.warning(f"Belge zaten yok: {dosya_adi}")
                    return True
                
        except Exception as e:
            log.error(f"HATA: Belge silme başarısız: {e}")
            return False
    
    def tum_belgeleri_listele(
        self,
        limit: Optional[int] = None,
        logger: Optional[logging.Logger] = None
    ) -> list[dict[str, str]]:
        """
        Tüm belgeleri listeler (metadata).
        
        Parametreler:
        -------------
        limit : int | None
            Maksimum kayıt sayısı (None ise hepsi)
        logger : Logger
            Logger referansı
        
        Döndürür:
        ---------
        list[dict]
            Belge metadata listesi:
            [
                {
                    'dosya_adi': '...',
                    'seri_numarasi': '...',
                    'olusturma_tarihi': '...',
                    'guncelleme_tarihi': '...'
                },
                ...
            ]
        """
        log = logger or gunluk
        
        try:
            with self._baglanti_al() as baglanti:
                imlec = baglanti.cursor()
                
                if limit:
                    imlec.execute("""
                        SELECT dosya_adi, seri_numarasi, 
                               olusturma_tarihi, guncelleme_tarihi
                        FROM belge_verileri
                        ORDER BY guncelleme_tarihi DESC
                        LIMIT ?
                    """, (limit,))
                else:
                    imlec.execute("""
                        SELECT dosya_adi, seri_numarasi, 
                               olusturma_tarihi, guncelleme_tarihi
                        FROM belge_verileri
                        ORDER BY guncelleme_tarihi DESC
                    """)
                
                satirlar = imlec.fetchall()
                
                belgeler = [dict(satir) for satir in satirlar]
                
                log.info(f"Toplam {len(belgeler)} belge listelendi")
                
                return belgeler
                
        except Exception as e:
            log.error(f"HATA: Listeleme başarısız: {e}")
            return []
    
    def istatistikler(
        self,
        logger: Optional[logging.Logger] = None
    ) -> dict[str, Any]:
        """
        Veritabanı istatistiklerini döner.
        
        Döndürür:
        ---------
        dict
            {
                'toplam_belge': int,
                'veritabani_boyutu': int (bytes),
                'en_eski_belge': str (tarih),
                'en_yeni_belge': str (tarih)
            }
        """
        log = logger or gunluk
        
        try:
            with self._baglanti_al() as baglanti:
                imlec = baglanti.cursor()
                
                # Toplam belge sayısı
                imlec.execute("SELECT COUNT(*) FROM belge_verileri")
                toplam_belge = imlec.fetchone()[0]
                
                # Tarih aralığı
                imlec.execute("""
                    SELECT 
                        MIN(olusturma_tarihi) as en_eski,
                        MAX(guncelleme_tarihi) as en_yeni
                    FROM belge_verileri
                """)
                tarihler = imlec.fetchone()
                
                # Veritabanı boyutu
                veritabani_boyutu = self.veritabani_yolu.stat().st_size
                
                istatistikler = {
                    'toplam_belge': toplam_belge,
                    'veritabani_boyutu': veritabani_boyutu,
                    'en_eski_belge': tarihler['en_eski'],
                    'en_yeni_belge': tarihler['en_yeni']
                }
                
                log.info("Veritabanı istatistikleri:")
                log.info(f"  - Toplam belge: {toplam_belge:,}")
                log.info(f"  - Boyut: {veritabani_boyutu:,} byte")
                
                return istatistikler
                
        except Exception as e:
            log.error(f"HATA: İstatistik hesaplama başarısız: {e}")
            return {
                'toplam_belge': 0,
                'veritabani_boyutu': 0,
                'en_eski_belge': None,
                'en_yeni_belge': None
            }


# Test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("=" * 60)
    print("BELGE ÖNBELLEĞİ - TEST")
    print("=" * 60)
    
    # Test verileri
    test_veri = {
        'standart_girdiler': {
            'PROJEADI': 'Test Projesi',
            'PROJEKONUM': 'İstanbul',
            'DUZENLEYEN': 'Cafer',
            'CURDATE': '2025-12-31',
        },
        'oturum_onbellegi': {
            'ZR20': {
                'urun_label_1': 'Panel 100x200',
                'adet_line_1': '10',
            }
        },
        'urun_kodlari': ['ZR20', 'LK']
    }
    
    # Önbellek oluştur
    onbellek = BelgeOnbellegi()
    
    print("\n1. Veri kaydetme...")
    basarili = onbellek.kaydet(
        dosya_adi='TEST-080126-ABCDE-R01',
        seri_numarasi='ABCDE',
        veri=test_veri
    )
    
    if basarili:
        print("\n2. Dosya adı ile yükleme...")
        veri1 = onbellek.yukle('TEST-080126-ABCDE-R01')
        
        if veri1:
            print(f"   ✓ Proje: {veri1['standart_girdiler']['PROJEADI']}")
        
        print("\n3. Seri numarası ile yükleme...")
        veri2 = onbellek.seri_ile_yukle('ABCDE')
        
        if veri2:
            print(f"   ✓ Dosya: {veri2['dosya_adi']}")
        
        print("\n4. Varlık kontrolü...")
        var_mi = onbellek.var_mi('TEST-080126-ABCDE-R01')
        print(f"   ✓ Belge var mı: {var_mi}")
        
        print("\n5. İstatistikler...")
        istatistikler = onbellek.istatistikler()
        
        print("\n✅ TEST BAŞARILI!")
    else:
        print("❌ Test başarısız")
