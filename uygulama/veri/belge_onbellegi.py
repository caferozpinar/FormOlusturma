"""
Belge Önbellek Yöneticisi - SQLite Backend (Genişletilmiş)
===========================================================

Belge verilerini merkezi SQLite veritabanında saklar.
+ İki yeni tablo: belge_kayitlari ve tab2_kayitlari

Tablolar:
---------
1. belge_verileri: Orijinal belge önbelleği (mevcut)
2. belge_kayitlari: CSV kaydedici verilerinin veritabanı versiyonu (YENİ)
3. tab2_kayitlari: Tab_2 form girdileri (YENİ)
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
    
    Yeni Özellikler (v2.1):
    ----------------------
    - belge_kayitlari tablosu: Ana belge kayıtları (CSV yerine)
    - tab2_kayitlari tablosu: Tab_2 form girdileri
    - Hızlı sorgulama: tarih, proje adı, konum, ürün kodları
    - Index'li aramalar
    """
    
    UYGULAMA_SURUMU = "2.1.0"
    
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
            
            # =========================================================================
            # TABLO 1: belge_verileri (Orijinal - Mevcut)
            # =========================================================================
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
            
            # Index'ler
            imlec.execute("""
                CREATE INDEX IF NOT EXISTS idx_seri 
                ON belge_verileri(seri_numarasi)
            """)
            
            imlec.execute("""
                CREATE INDEX IF NOT EXISTS idx_olusturma 
                ON belge_verileri(olusturma_tarihi DESC)
            """)
            
            # =========================================================================
            # TABLO 2: belge_kayitlari (YENİ - CSV kaydedici yerine)
            # =========================================================================
            imlec.execute("""
                CREATE TABLE IF NOT EXISTS belge_kayitlari (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    seri_numarasi TEXT UNIQUE NOT NULL,
                    tarih TEXT NOT NULL,
                    proje_adi TEXT,
                    proje_konum TEXT,
                    urun_kodlari TEXT,
                    revizyon_numarasi TEXT,
                    dosya_adi TEXT,
                    dosya_yolu TEXT,
                    olusturan_kisi TEXT,
                    olusturma_saati TEXT,
                    kdv_orani TEXT,
                    kdvli_toplam_fiyat TEXT,
                    form_onaylandi TEXT DEFAULT 'Hayır',
                    son_guncelleme_tarihi TEXT,
                    hatirlatma_durumu TEXT DEFAULT 'Pasif',
                    kayit_zamani TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Index'ler (hızlı arama için)
            imlec.execute("""
                CREATE INDEX IF NOT EXISTS idx_belge_seri 
                ON belge_kayitlari(seri_numarasi)
            """)
            
            imlec.execute("""
                CREATE INDEX IF NOT EXISTS idx_belge_tarih 
                ON belge_kayitlari(tarih DESC)
            """)
            
            imlec.execute("""
                CREATE INDEX IF NOT EXISTS idx_belge_proje 
                ON belge_kayitlari(proje_adi)
            """)
            
            imlec.execute("""
                CREATE INDEX IF NOT EXISTS idx_belge_konum 
                ON belge_kayitlari(proje_konum)
            """)
            
            # Full-text search için (ürün kodları)
            imlec.execute("""
                CREATE INDEX IF NOT EXISTS idx_belge_urunler 
                ON belge_kayitlari(urun_kodlari)
            """)
            
            # =========================================================================
            # TABLO 2.5: belge_urun_detaylari (30 ürün için ayrı tablo - normalleştirme)
            # =========================================================================
            imlec.execute("""
                CREATE TABLE IF NOT EXISTS belge_urun_detaylari (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    belge_id INTEGER NOT NULL,
                    urun_sira INTEGER NOT NULL,
                    urun_adi TEXT,
                    urun_adet TEXT,
                    urun_birim_fiyat TEXT,
                    urun_toplam_fiyat TEXT,
                    FOREIGN KEY (belge_id) REFERENCES belge_kayitlari(id) ON DELETE CASCADE
                )
            """)
            
            imlec.execute("""
                CREATE INDEX IF NOT EXISTS idx_urun_belge 
                ON belge_urun_detaylari(belge_id)
            """)
            
            # =========================================================================
            # TABLO 3: tab2_kayitlari (YENİ - Tab_2 form girdileri)
            # =========================================================================
            imlec.execute("""
                CREATE TABLE IF NOT EXISTS tab2_kayitlari (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    belge_tarih TEXT,
                    proje_adi TEXT,
                    proje_yeri TEXT,
                    urun1_kod TEXT,
                    urun1_adet TEXT,
                    urun1_ozl TEXT,
                    urun2_kod TEXT,
                    urun2_adet TEXT,
                    urun2_ozl TEXT,
                    urun3_kod TEXT,
                    urun3_adet TEXT,
                    urun3_ozl TEXT,
                    urun4_kod TEXT,
                    urun4_adet TEXT,
                    urun4_ozl TEXT,
                    urun5_kod TEXT,
                    urun5_adet TEXT,
                    urun5_ozl TEXT,
                    urun6_kod TEXT,
                    urun6_adet TEXT,
                    urun6_ozl TEXT,
                    toplam_teklif TEXT,
                    belge_tipi TEXT,
                    notlar TEXT,
                    kayit_zamani TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Index'ler (hızlı arama için)
            imlec.execute("""
                CREATE INDEX IF NOT EXISTS idx_tab2_tarih 
                ON tab2_kayitlari(belge_tarih DESC)
            """)
            
            imlec.execute("""
                CREATE INDEX IF NOT EXISTS idx_tab2_proje 
                ON tab2_kayitlari(proje_adi)
            """)
            
            imlec.execute("""
                CREATE INDEX IF NOT EXISTS idx_tab2_yer 
                ON tab2_kayitlari(proje_yeri)
            """)
            
            imlec.execute("""
                CREATE INDEX IF NOT EXISTS idx_tab2_tip 
                ON tab2_kayitlari(belge_tipi)
            """)
            
            gunluk.debug(f"✓ Veritabanı hazır (3 tablo): {self.veritabani_yolu}")
    
    # =========================================================================
    # ORİJİNAL METODLAR (belge_verileri tablosu için)
    # =========================================================================
    
    def _veriyi_sikistir(self, veri: dict) -> str:
        """Veriyi sıkıştırır ve base64 string'e çevirir."""
        json_str = json.dumps(veri, ensure_ascii=False)
        json_bytes = json_str.encode('utf-8')
        sikistirilmis = gzip.compress(json_bytes, compresslevel=9)
        base64_str = base64.b64encode(sikistirilmis).decode('ascii')
        return base64_str
    
    def _veriyi_ac(self, sikistirilmis_str: str) -> dict:
        """Sıkıştırılmış veriyi açar."""
        sikistirilmis = base64.b64decode(sikistirilmis_str.encode('ascii'))
        json_bytes = gzip.decompress(sikistirilmis)
        json_str = json_bytes.decode('utf-8')
        veri = json.loads(json_str)
        return veri
    
    def kaydet(
        self,
        dosya_adi: str,
        seri_numarasi: str,
        veri: dict[str, Any],
        uygulama_surumu: str = None,
        logger: Optional[logging.Logger] = None
    ) -> bool:
        """
        Belge verilerini veritabanına kaydeder (orijinal tablo).
        
        Parametreler:
        -------------
        dosya_adi : str
            Belge dosya adı (örn: 'IZELTAS-080126-59HOY1-R01')
        seri_numarasi : str
            Belge seri numarası (örn: '59HOY1')
        veri : dict
            Kaydedilecek veri yapısı
        uygulama_surumu : str
            Uygulama sürüm numarası
        logger : Logger
            Logger referansı
        
        Döndürür:
        ---------
        bool
            Başarılı ise True
        """
        if uygulama_surumu is None:
            uygulama_surumu = self.UYGULAMA_SURUMU
        
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
            
            log.debug(f"  - Sıkıştırma: %{oran:.1f}")
            
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
        """Belge verilerini dosya adı ile yükler (orijinal tablo)."""
        log = logger or gunluk
        
        try:
            # .docx uzantısını kaldır (varsa)
            if dosya_adi.endswith('.docx'):
                dosya_adi = dosya_adi[:-5]
            
            with self._baglanti_al() as baglanti:
                imlec = baglanti.cursor()
                
                imlec.execute("""
                    SELECT veri_json, olusturma_tarihi, guncelleme_tarihi
                    FROM belge_verileri
                    WHERE dosya_adi = ?
                """, (dosya_adi,))
                
                satir = imlec.fetchone()
                
                if satir is None:
                    log.debug(f"Belge bulunamadı: {dosya_adi}")
                    return None
                
                # Veriyi aç
                veri = self._veriyi_ac(satir['veri_json'])
                veri['olusturma_tarihi'] = satir['olusturma_tarihi']
                veri['guncelleme_tarihi'] = satir['guncelleme_tarihi']
                
                log.debug(f"✓ Belge yüklendi: {dosya_adi}")
                return veri
                
        except Exception as e:
            log.error(f"HATA: Belge yükleme başarısız: {e}")
            return None
    
    def seri_ile_yukle(
        self,
        seri_numarasi: str,
        logger: Optional[logging.Logger] = None
    ) -> Optional[dict[str, Any]]:
        """Belge verilerini seri numarası ile yükler (orijinal tablo)."""
        log = logger or gunluk
        
        try:
            with self._baglanti_al() as baglanti:
                imlec = baglanti.cursor()
                
                imlec.execute("""
                    SELECT dosya_adi, veri_json, 
                           olusturma_tarihi, guncelleme_tarihi
                    FROM belge_verileri
                    WHERE seri_numarasi = ?
                    ORDER BY guncelleme_tarihi DESC
                    LIMIT 1
                """, (seri_numarasi,))
                
                satir = imlec.fetchone()
                
                if satir is None:
                    log.debug(f"Seri numarası bulunamadı: {seri_numarasi}")
                    return None
                
                # Veriyi aç
                veri = self._veriyi_ac(satir['veri_json'])
                veri['dosya_adi'] = satir['dosya_adi']
                veri['olusturma_tarihi'] = satir['olusturma_tarihi']
                veri['guncelleme_tarihi'] = satir['guncelleme_tarihi']
                
                log.debug(f"✓ Belge yüklendi (seri): {seri_numarasi}")
                return veri
                
        except Exception as e:
            log.error(f"HATA: Seri ile yükleme başarısız: {e}")
            return None
    
    def var_mi(
        self,
        dosya_adi: str,
        logger: Optional[logging.Logger] = None
    ) -> bool:
        """Belgenin veritabanında olup olmadığını kontrol eder."""
        try:
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
        """Belge verilerini önbellekten siler."""
        log = logger or gunluk
        
        try:
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
        """Tüm belgeleri listeler (metadata)."""
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
                
                log.debug(f"Toplam {len(belgeler)} belge listelendi")
                return belgeler
                
        except Exception as e:
            log.error(f"HATA: Listeleme başarısız: {e}")
            return []
    
    def istatistikler(
        self,
        logger: Optional[logging.Logger] = None
    ) -> dict[str, Any]:
        """Veritabanı istatistiklerini döner."""
        log = logger or gunluk
        
        try:
            with self._baglanti_al() as baglanti:
                imlec = baglanti.cursor()
                
                # belge_verileri
                imlec.execute("SELECT COUNT(*) FROM belge_verileri")
                toplam_belge = imlec.fetchone()[0]
                
                # belge_kayitlari
                imlec.execute("SELECT COUNT(*) FROM belge_kayitlari")
                toplam_kayit = imlec.fetchone()[0]
                
                # tab2_kayitlari
                imlec.execute("SELECT COUNT(*) FROM tab2_kayitlari")
                toplam_tab2 = imlec.fetchone()[0]
                
                # Veritabanı boyutu
                veritabani_boyutu = self.veritabani_yolu.stat().st_size
                
                istatistikler = {
                    'toplam_belge': toplam_belge,
                    'toplam_kayit': toplam_kayit,
                    'toplam_tab2': toplam_tab2,
                    'veritabani_boyutu': veritabani_boyutu,
                }
                
                log.info("Veritabanı istatistikleri:")
                log.info(f"  - Belge önbelleği: {toplam_belge:,}")
                log.info(f"  - Belge kayıtları: {toplam_kayit:,}")
                log.info(f"  - Tab2 kayıtları: {toplam_tab2:,}")
                log.info(f"  - Boyut: {veritabani_boyutu:,} byte")
                
                return istatistikler
                
        except Exception as e:
            log.error(f"HATA: İstatistik hesaplama başarısız: {e}")
            return {}
    
    # =========================================================================
    # YENİ METODLAR - TABLO 2: belge_kayitlari
    # =========================================================================
    
    def belge_kaydi_ekle(
        self,
        kayit_verileri: dict[str, Any],
        urun_detaylari: list[dict[str, str]],
        logger: Optional[logging.Logger] = None
    ) -> bool:
        """
        Belge kaydı ekler (CSV kaydedici yerine).
        
        Parametreler:
        -------------
        kayit_verileri : dict
            {
                'seri_numarasi': str,
                'tarih': str,
                'proje_adi': str,
                'proje_konum': str,
                'urun_kodlari': str (virgülle ayrılmış),
                'revizyon_numarasi': str,
                'dosya_adi': str,
                'dosya_yolu': str,
                'olusturan_kisi': str,
                'olusturma_saati': str,
                'kdv_orani': str,
                'kdvli_toplam_fiyat': str
            }
        urun_detaylari : list[dict]
            [
                {
                    'urun_adi': str,
                    'urun_adet': str,
                    'urun_birim_fiyat': str,
                    'urun_toplam_fiyat': str
                },
                ... (30 ürüne kadar)
            ]
        logger : Logger
        
        Döndürür:
        ---------
        bool
            Başarılı ise True
        """
        log = logger or gunluk
        
        try:
            simdi = datetime.now().strftime("%Y-%m-%d")
            
            with self._baglanti_al() as baglanti:
                imlec = baglanti.cursor()
                
                # Ana kayıt
                imlec.execute("""
                    INSERT OR REPLACE INTO belge_kayitlari
                    (seri_numarasi, tarih, proje_adi, proje_konum, urun_kodlari,
                     revizyon_numarasi, dosya_adi, dosya_yolu, olusturan_kisi,
                     olusturma_saati, kdv_orani, kdvli_toplam_fiyat,
                     son_guncelleme_tarihi)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    kayit_verileri.get('seri_numarasi'),
                    kayit_verileri.get('tarih', simdi),
                    kayit_verileri.get('proje_adi', ''),
                    kayit_verileri.get('proje_konum', ''),
                    kayit_verileri.get('urun_kodlari', ''),
                    kayit_verileri.get('revizyon_numarasi', 'R01'),
                    kayit_verileri.get('dosya_adi', ''),
                    kayit_verileri.get('dosya_yolu', ''),
                    kayit_verileri.get('olusturan_kisi', ''),
                    kayit_verileri.get('olusturma_saati', datetime.now().strftime("%H:%M:%S")),
                    kayit_verileri.get('kdv_orani', '0'),
                    kayit_verileri.get('kdvli_toplam_fiyat', '0,00'),
                    simdi
                ))
                
                belge_id = imlec.lastrowid
                
                # Ürün detayları (önce eski kayıtları sil)
                imlec.execute("DELETE FROM belge_urun_detaylari WHERE belge_id = ?", (belge_id,))
                
                # Yeni ürünleri ekle
                for sira, urun in enumerate(urun_detaylari, start=1):
                    if sira > 30:  # Maksimum 30 ürün
                        break
                    
                    imlec.execute("""
                        INSERT INTO belge_urun_detaylari
                        (belge_id, urun_sira, urun_adi, urun_adet, 
                         urun_birim_fiyat, urun_toplam_fiyat)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        belge_id,
                        sira,
                        urun.get('urun_adi', ''),
                        urun.get('urun_adet', ''),
                        urun.get('urun_birim_fiyat', ''),
                        urun.get('urun_toplam_fiyat', '')
                    ))
            
            log.info(f"✓ Belge kaydı eklendi: {kayit_verileri.get('seri_numarasi')}")
            log.debug(f"  - Ürün sayısı: {len(urun_detaylari)}")
            
            return True
            
        except Exception as e:
            log.error(f"HATA: Belge kaydı eklenemedi: {e}")
            import traceback
            log.error(traceback.format_exc())
            return False
    
    def belge_kaydi_ara(
        self,
        seri_numarasi: Optional[str] = None,
        proje_adi: Optional[str] = None,
        proje_konum: Optional[str] = None,
        tarih_baslangic: Optional[str] = None,
        tarih_bitis: Optional[str] = None,
        urun_kodu: Optional[str] = None,
        limit: int = 100,
        logger: Optional[logging.Logger] = None
    ) -> list[dict[str, Any]]:
        """
        Belge kayıtlarını sorgular (çok yönlü arama).
        
        Parametreler:
        -------------
        seri_numarasi : str | None
            Seri numarası ile arama
        proje_adi : str | None
            Proje adı ile arama (LIKE)
        proje_konum : str | None
            Proje konumu ile arama (LIKE)
        tarih_baslangic : str | None
            Başlangıç tarihi (YYYY-MM-DD)
        tarih_bitis : str | None
            Bitiş tarihi (YYYY-MM-DD)
        urun_kodu : str | None
            Ürün kodu ile arama (LIKE)
        limit : int
            Maksimum sonuç sayısı
        logger : Logger
        
        Döndürür:
        ---------
        list[dict]
            Bulunan kayıtlar
        """
        log = logger or gunluk
        
        try:
            with self._baglanti_al() as baglanti:
                imlec = baglanti.cursor()
                
                # Sorgu oluştur
                sorgu = "SELECT * FROM belge_kayitlari WHERE 1=1"
                parametreler = []
                
                if seri_numarasi:
                    sorgu += " AND seri_numarasi = ?"
                    parametreler.append(seri_numarasi)
                
                if proje_adi:
                    sorgu += " AND proje_adi LIKE ?"
                    parametreler.append(f"%{proje_adi}%")
                
                if proje_konum:
                    sorgu += " AND proje_konum LIKE ?"
                    parametreler.append(f"%{proje_konum}%")
                
                if tarih_baslangic:
                    sorgu += " AND tarih >= ?"
                    parametreler.append(tarih_baslangic)
                
                if tarih_bitis:
                    sorgu += " AND tarih <= ?"
                    parametreler.append(tarih_bitis)
                
                if urun_kodu:
                    sorgu += " AND urun_kodlari LIKE ?"
                    parametreler.append(f"%{urun_kodu}%")
                
                sorgu += " ORDER BY tarih DESC, kayit_zamani DESC LIMIT ?"
                parametreler.append(limit)
                
                imlec.execute(sorgu, tuple(parametreler))
                satirlar = imlec.fetchall()
                
                kayitlar = [dict(satir) for satir in satirlar]
                
                log.info(f"Belge arama: {len(kayitlar)} sonuç bulundu")
                return kayitlar
                
        except Exception as e:
            log.error(f"HATA: Belge arama başarısız: {e}")
            return []
    
    def belge_kaydi_urun_detaylari_al(
        self,
        belge_id: int,
        logger: Optional[logging.Logger] = None
    ) -> list[dict[str, str]]:
        """
        Belgeye ait ürün detaylarını getirir.
        
        Parametreler:
        -------------
        belge_id : int
            Belge ID
        logger : Logger
        
        Döndürür:
        ---------
        list[dict]
            Ürün detayları
        """
        log = logger or gunluk
        
        try:
            with self._baglanti_al() as baglanti:
                imlec = baglanti.cursor()
                
                imlec.execute("""
                    SELECT urun_sira, urun_adi, urun_adet, 
                           urun_birim_fiyat, urun_toplam_fiyat
                    FROM belge_urun_detaylari
                    WHERE belge_id = ?
                    ORDER BY urun_sira ASC
                """, (belge_id,))
                
                satirlar = imlec.fetchall()
                urunler = [dict(satir) for satir in satirlar]
                
                return urunler
                
        except Exception as e:
            log.error(f"HATA: Ürün detayları alınamadı: {e}")
            return []
    
    # =========================================================================
    # YENİ METODLAR - TABLO 3: tab2_kayitlari
    # =========================================================================
    
    def tab2_kaydi_ekle(
        self,
        tab2_verileri: dict[str, Any],
        logger: Optional[logging.Logger] = None
    ) -> bool:
        """
        Tab_2 form verilerini veritabanına kaydeder.
        
        Parametreler:
        -------------
        tab2_verileri : dict
            {
                'belge_tarih': str,
                'proje_adi': str,
                'proje_yeri': str,
                'urun1_kod': str,
                'urun1_adet': str,
                'urun1_ozl': str,
                ... (urun6'ya kadar)
                'toplam_teklif': str,
                'belge_tipi': str,
                'notlar': str
            }
        logger : Logger
        
        Döndürür:
        ---------
        bool
            Başarılı ise True
        """
        log = logger or gunluk
        
        try:
            with self._baglanti_al() as baglanti:
                imlec = baglanti.cursor()
                
                imlec.execute("""
                    INSERT INTO tab2_kayitlari
                    (belge_tarih, proje_adi, proje_yeri,
                     urun1_kod, urun1_adet, urun1_ozl,
                     urun2_kod, urun2_adet, urun2_ozl,
                     urun3_kod, urun3_adet, urun3_ozl,
                     urun4_kod, urun4_adet, urun4_ozl,
                     urun5_kod, urun5_adet, urun5_ozl,
                     urun6_kod, urun6_adet, urun6_ozl,
                     toplam_teklif, belge_tipi, notlar)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    tab2_verileri.get('belge_tarih', ''),
                    tab2_verileri.get('proje_adi', ''),
                    tab2_verileri.get('proje_yeri', ''),
                    tab2_verileri.get('urun1_kod', ''),
                    tab2_verileri.get('urun1_adet', ''),
                    tab2_verileri.get('urun1_ozl', ''),
                    tab2_verileri.get('urun2_kod', ''),
                    tab2_verileri.get('urun2_adet', ''),
                    tab2_verileri.get('urun2_ozl', ''),
                    tab2_verileri.get('urun3_kod', ''),
                    tab2_verileri.get('urun3_adet', ''),
                    tab2_verileri.get('urun3_ozl', ''),
                    tab2_verileri.get('urun4_kod', ''),
                    tab2_verileri.get('urun4_adet', ''),
                    tab2_verileri.get('urun4_ozl', ''),
                    tab2_verileri.get('urun5_kod', ''),
                    tab2_verileri.get('urun5_adet', ''),
                    tab2_verileri.get('urun5_ozl', ''),
                    tab2_verileri.get('urun6_kod', ''),
                    tab2_verileri.get('urun6_adet', ''),
                    tab2_verileri.get('urun6_ozl', ''),
                    tab2_verileri.get('toplam_teklif', ''),
                    tab2_verileri.get('belge_tipi', ''),
                    tab2_verileri.get('notlar', '')
                ))
            
            log.info(f"✓ Tab2 kaydı eklendi (ID: {imlec.lastrowid})")
            return True
            
        except Exception as e:
            log.error(f"HATA: Tab2 kaydı eklenemedi: {e}")
            import traceback
            log.error(traceback.format_exc())
            return False
    
    def tab2_kayitlari_ara(
        self,
        proje_adi: Optional[str] = None,
        proje_yeri: Optional[str] = None,
        belge_tipi: Optional[str] = None,
        tarih_baslangic: Optional[str] = None,
        tarih_bitis: Optional[str] = None,
        urun_kodu: Optional[str] = None,
        limit: int = 100,
        logger: Optional[logging.Logger] = None
    ) -> list[dict[str, Any]]:
        """
        Tab2 kayıtlarını sorgular.
        
        Parametreler:
        -------------
        proje_adi : str | None
            Proje adı (LIKE)
        proje_yeri : str | None
            Proje yeri (LIKE)
        belge_tipi : str | None
            Belge tipi (Teklif/Keşif/Tanım)
        tarih_baslangic : str | None
            Başlangıç tarihi
        tarih_bitis : str | None
            Bitiş tarihi
        urun_kodu : str | None
            Ürün kodu arama (tüm ürünlerde)
        limit : int
            Maksimum sonuç
        logger : Logger
        
        Döndürür:
        ---------
        list[dict]
            Bulunan kayıtlar
        """
        log = logger or gunluk
        
        try:
            with self._baglanti_al() as baglanti:
                imlec = baglanti.cursor()
                
                # Sorgu oluştur
                sorgu = "SELECT * FROM tab2_kayitlari WHERE 1=1"
                parametreler = []
                
                if proje_adi:
                    sorgu += " AND proje_adi LIKE ?"
                    parametreler.append(f"%{proje_adi}%")
                
                if proje_yeri:
                    sorgu += " AND proje_yeri LIKE ?"
                    parametreler.append(f"%{proje_yeri}%")
                
                if belge_tipi:
                    sorgu += " AND belge_tipi = ?"
                    parametreler.append(belge_tipi)
                
                if tarih_baslangic:
                    sorgu += " AND belge_tarih >= ?"
                    parametreler.append(tarih_baslangic)
                
                if tarih_bitis:
                    sorgu += " AND belge_tarih <= ?"
                    parametreler.append(tarih_bitis)
                
                if urun_kodu:
                    # Tüm ürün kod kolonlarında ara
                    sorgu += """ AND (
                        urun1_kod LIKE ? OR urun2_kod LIKE ? OR 
                        urun3_kod LIKE ? OR urun4_kod LIKE ? OR 
                        urun5_kod LIKE ? OR urun6_kod LIKE ?
                    )"""
                    parametreler.extend([f"%{urun_kodu}%"] * 6)
                
                sorgu += " ORDER BY belge_tarih DESC, kayit_zamani DESC LIMIT ?"
                parametreler.append(limit)
                
                imlec.execute(sorgu, tuple(parametreler))
                satirlar = imlec.fetchall()
                
                kayitlar = [dict(satir) for satir in satirlar]
                
                log.info(f"Tab2 arama: {len(kayitlar)} sonuç bulundu")
                return kayitlar
                
        except Exception as e:
            log.error(f"HATA: Tab2 arama başarısız: {e}")
            return []
