"""
Belge Önbellek Yöneticisi - SQLite Backend (v3.0)
=================================================

Birleşik veritabanı yapısı:
- belgeler: Ana belge tablosu (UYGULAMA + MANUEL)
- belge_urunler: Ürün detayları (1-N ilişki)

Değişiklikler (v2.x → v3.0):
- ✅ Tek ana tablo: belgeler
- ✅ Esnek ürün sayısı: belge_urunler (1-N)
- ✅ Geriye uyumsuz: Eski tablolar kaldırıldı
- ✅ Daha basit API
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Optional
import logging
from contextlib import contextmanager

gunluk = logging.getLogger(__name__)


class BelgeOnbellegi:
    """
    Belge verilerini SQLite veritabanında saklar (LOW-LEVEL).
    
    Tablolar:
    ---------
    1. belgeler: Ana belge kayıtları
    2. belge_urunler: Ürün detayları (1-N)
    
    Kullanım:
    ---------
    >>> onbellek = BelgeOnbellegi()
    >>> belge_id = onbellek.belge_ekle({
    ...     'seri_numarasi': 'SN:...',
    ...     'tarih': '2026-01-28',
    ...     'proje_adi': 'Test',
    ...     'proje_konum': 'İstanbul',
    ...     'belge_kaynak': 'UYGULAMA'
    ... })
    >>> onbellek.belge_urun_ekle(belge_id, 1, {
    ...     'urun_kodu': 'LK',
    ...     'urun_adi': 'HAVALANDIRMA',
    ...     'urun_adet': '10'
    ... })
    """
    
    UYGULAMA_SURUMU = "3.0.0"
    
    def __init__(self, veritabani_yolu: Optional[str | Path] = None):
        """
        Parametreler:
        -------------
        veritabani_yolu : str | Path | None
            SQLite veritabanı yolu. None ise: ./veri/belge_onbellegi.db
        """
        if veritabani_yolu is None:
            veri_klasoru = Path('./veri')
            veri_klasoru.mkdir(exist_ok=True)
            self.veritabani_yolu = veri_klasoru / 'belge_onbellegi.db'
        else:
            self.veritabani_yolu = Path(veritabani_yolu)
            self.veritabani_yolu.parent.mkdir(parents=True, exist_ok=True)
        
        # Veritabanını başlat
        self._veritabani_baslat()
        gunluk.info(f"BelgeOnbellegi v{self.UYGULAMA_SURUMU} hazır: {self.veritabani_yolu}")
    
    @contextmanager
    def _baglanti_al(self):
        """Veritabanı bağlantısı context manager."""
        baglanti = sqlite3.connect(str(self.veritabani_yolu))
        baglanti.row_factory = sqlite3.Row  # Dict-like access
        try:
            yield baglanti
            baglanti.commit()
        except Exception as e:
            baglanti.rollback()
            gunluk.error(f"Veritabanı hatası: {e}")
            raise e
        finally:
            baglanti.close()
    
    def _veritabani_baslat(self):
        """
        Veritabanı tablolarını oluşturur.
        
        Not: Eski tabloları SİLMEZ, sadece yenilerini oluşturur.
        Eski tabloları silmek için: python yeni_veritabani_olustur.py
        """
        with self._baglanti_al() as baglanti:
            imlec = baglanti.cursor()
            
            # TABLO: belgeler
            imlec.execute("""
                CREATE TABLE IF NOT EXISTS belgeler (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    seri_numarasi TEXT UNIQUE NOT NULL,
                    tarih DATE NOT NULL,
                    proje_adi TEXT NOT NULL,
                    proje_konum TEXT NOT NULL,
                    belge_kaynak TEXT NOT NULL CHECK(belge_kaynak IN ('UYGULAMA', 'MANUEL')),
                    belge_tipi TEXT,
                    revizyon_numarasi TEXT DEFAULT 'R00',
                    form_onaylandi TEXT DEFAULT 'Hayır' CHECK(form_onaylandi IN ('Evet', 'Hayır')),
                    hatirlatma_durumu TEXT DEFAULT 'Pasif' CHECK(hatirlatma_durumu IN ('Aktif', 'Pasif')),
                    dosya_adi TEXT,
                    dosya_yolu TEXT,
                    kdv_orani TEXT,
                    kdvli_toplam_fiyat TEXT,
                    olusturan_kisi TEXT,
                    olusturma_saati TEXT,
                    kayit_zamani TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    son_guncelleme_tarihi DATE,
                    notlar TEXT,
                    ztf_veri_json TEXT,
                    uygulama_surumu TEXT
                )
            """)
            
            # Index'ler
            imlec.execute("CREATE INDEX IF NOT EXISTS idx_seri_numarasi ON belgeler(seri_numarasi)")
            imlec.execute("CREATE INDEX IF NOT EXISTS idx_tarih ON belgeler(tarih)")
            imlec.execute("CREATE INDEX IF NOT EXISTS idx_proje_adi ON belgeler(proje_adi)")
            imlec.execute("CREATE INDEX IF NOT EXISTS idx_belge_kaynak ON belgeler(belge_kaynak)")
            
            # TABLO: belge_urunler
            imlec.execute("""
                CREATE TABLE IF NOT EXISTS belge_urunler (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    belge_id INTEGER NOT NULL,
                    sira_no INTEGER NOT NULL,
                    urun_kodu TEXT,
                    urun_adi TEXT,
                    urun_adet TEXT,
                    urun_ozellik TEXT,
                    urun_birim_fiyat TEXT,
                    urun_toplam_fiyat TEXT,
                    FOREIGN KEY (belge_id) REFERENCES belgeler(id) ON DELETE CASCADE,
                    UNIQUE(belge_id, sira_no)
                )
            """)
            
            imlec.execute("CREATE INDEX IF NOT EXISTS idx_belge_id ON belge_urunler(belge_id)")
            
            gunluk.debug("Veritabanı tabloları kontrol edildi")
    
    # =========================================================================
    # BELGE KAYITLARI - CRUD
    # =========================================================================
    
    def belge_ekle(
        self,
        kayit: dict[str, Any],
        logger: Optional[logging.Logger] = None
    ) -> Optional[int]:
        """
        Yeni belge kaydı ekler.
        
        Parametreler:
        -------------
        kayit : dict
            Belge verileri. Zorunlu alanlar:
            - seri_numarasi
            - tarih
            - proje_adi
            - proje_konum
            - belge_kaynak ('UYGULAMA' veya 'MANUEL')
        logger : Logger
        
        Döndürür:
        ---------
        int | None
            Eklenen belge ID'si veya None (hata)
        
        Örnek:
        ------
        >>> belge_id = onbellek.belge_ekle({
        ...     'seri_numarasi': 'SN:280126-TEST-IST-R00',
        ...     'tarih': '2026-01-28',
        ...     'proje_adi': 'Test Projesi',
        ...     'proje_konum': 'İstanbul',
        ...     'belge_kaynak': 'UYGULAMA',
        ...     'kdvli_toplam_fiyat': '1000,00'
        ... })
        """
        log = logger or gunluk
        
        try:
            with self._baglanti_al() as baglanti:
                imlec = baglanti.cursor()
                
                # SQL hazırla
                kolonlar = ', '.join(kayit.keys())
                placeholders = ', '.join(['?' for _ in kayit])
                sql = f"INSERT INTO belgeler ({kolonlar}) VALUES ({placeholders})"
                
                # Çalıştır
                imlec.execute(sql, list(kayit.values()))
                belge_id = imlec.lastrowid
                
                log.info(f"✓ Belge eklendi: ID={belge_id}, Seri={kayit.get('seri_numarasi')}")
                return belge_id
        
        except sqlite3.IntegrityError as e:
            log.error(f"Belge ekleme hatası (unique constraint): {e}")
            return None
        except Exception as e:
            log.error(f"Belge ekleme hatası: {e}")
            return None
    
    def belge_urun_ekle(
        self,
        belge_id: int,
        sira_no: int,
        urun: dict[str, str],
        logger: Optional[logging.Logger] = None
    ) -> bool:
        """
        Belgeye ürün ekler.
        
        Parametreler:
        -------------
        belge_id : int
            Belge ID
        sira_no : int
            Ürün sıra numarası (1, 2, 3, ...)
        urun : dict
            Ürün verileri:
            - urun_kodu
            - urun_adi
            - urun_adet
            - urun_ozellik
            - urun_birim_fiyat
            - urun_toplam_fiyat
        logger : Logger
        
        Döndürür:
        ---------
        bool
            Başarılı ise True
        
        Örnek:
        ------
        >>> onbellek.belge_urun_ekle(1, 1, {
        ...     'urun_kodu': 'LK',
        ...     'urun_adi': 'HAVALANDIRMA KAPAK SETİ',
        ...     'urun_adet': '10',
        ...     'urun_birim_fiyat': '50,00',
        ...     'urun_toplam_fiyat': '500,00'
        ... })
        """
        log = logger or gunluk
        
        try:
            with self._baglanti_al() as baglanti:
                imlec = baglanti.cursor()
                
                imlec.execute("""
                    INSERT INTO belge_urunler (
                        belge_id, sira_no, urun_kodu, urun_adi, urun_adet,
                        urun_ozellik, urun_birim_fiyat, urun_toplam_fiyat
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    belge_id,
                    sira_no,
                    urun.get('urun_kodu', ''),
                    urun.get('urun_adi', ''),
                    urun.get('urun_adet', ''),
                    urun.get('urun_ozellik', ''),
                    urun.get('urun_birim_fiyat', ''),
                    urun.get('urun_toplam_fiyat', '')
                ))
                
                log.debug(f"✓ Ürün eklendi: Belge={belge_id}, Sıra={sira_no}")
                return True
        
        except Exception as e:
            log.error(f"Ürün ekleme hatası: {e}")
            return False
    
    def belge_ara(
        self,
        **filtreler
    ) -> list[dict[str, Any]]:
        """
        Belge arar (çok yönlü).
        
        Parametreler:
        -------------
        **filtreler : dict
            Arama kriterleri:
            - seri_numarasi: str
            - proje_adi: str (LIKE)
            - proje_konum: str (LIKE)
            - belge_kaynak: str ('UYGULAMA' veya 'MANUEL')
            - tarih_baslangic: str (>=)
            - tarih_bitis: str (<=)
            - limit: int
        
        Döndürür:
        ---------
        list[dict]
            Bulunan belgeler
        
        Örnek:
        ------
        >>> belgeler = onbellek.belge_ara(
        ...     proje_adi='TEST',
        ...     belge_kaynak='UYGULAMA',
        ...     limit=10
        ... )
        """
        try:
            with self._baglanti_al() as baglanti:
                imlec = baglanti.cursor()
                
                # WHERE clause oluştur
                kosullar = []
                parametreler = []
                
                if 'seri_numarasi' in filtreler:
                    kosullar.append("seri_numarasi = ?")
                    parametreler.append(filtreler['seri_numarasi'])
                
                if 'proje_adi' in filtreler:
                    kosullar.append("proje_adi LIKE ?")
                    parametreler.append(f"%{filtreler['proje_adi']}%")
                
                if 'proje_konum' in filtreler:
                    kosullar.append("proje_konum LIKE ?")
                    parametreler.append(f"%{filtreler['proje_konum']}%")
                
                if 'belge_kaynak' in filtreler:
                    kosullar.append("belge_kaynak = ?")
                    parametreler.append(filtreler['belge_kaynak'])
                
                if 'tarih_baslangic' in filtreler:
                    kosullar.append("tarih >= ?")
                    parametreler.append(filtreler['tarih_baslangic'])
                
                if 'tarih_bitis' in filtreler:
                    kosullar.append("tarih <= ?")
                    parametreler.append(filtreler['tarih_bitis'])
                
                # SQL oluştur
                sql = "SELECT * FROM belgeler"
                if kosullar:
                    sql += " WHERE " + " AND ".join(kosullar)
                sql += " ORDER BY tarih DESC"
                
                if 'limit' in filtreler:
                    sql += f" LIMIT {filtreler['limit']}"
                
                # Çalıştır
                imlec.execute(sql, parametreler)
                satirlar = imlec.fetchall()
                
                # Dict'e çevir
                return [dict(satir) for satir in satirlar]
        
        except Exception as e:
            gunluk.error(f"Belge arama hatası: {e}")
            return []
    
    def belge_urunlerini_getir(
        self,
        belge_id: int,
        logger: Optional[logging.Logger] = None
    ) -> list[dict[str, Any]]:
        """
        Belgenin tüm ürünlerini getirir.
        
        Parametreler:
        -------------
        belge_id : int
            Belge ID
        logger : Logger
        
        Döndürür:
        ---------
        list[dict]
            Ürün listesi (sıra_no'ya göre sıralı)
        """
        log = logger or gunluk
        
        try:
            with self._baglanti_al() as baglanti:
                imlec = baglanti.cursor()
                
                imlec.execute("""
                    SELECT * FROM belge_urunler
                    WHERE belge_id = ?
                    ORDER BY sira_no
                """, (belge_id,))
                
                satirlar = imlec.fetchall()
                return [dict(satir) for satir in satirlar]
        
        except Exception as e:
            log.error(f"Ürün getirme hatası: {e}")
            return []
    
    def belge_sil(
        self,
        belge_id: int,
        logger: Optional[logging.Logger] = None
    ) -> bool:
        """
        Belgeyi siler (ürünler CASCADE ile otomatik silinir).
        
        Parametreler:
        -------------
        belge_id : int
            Belge ID
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
                imlec.execute("DELETE FROM belgeler WHERE id = ?", (belge_id,))
                
                log.info(f"✓ Belge silindi: ID={belge_id}")
                return True
        
        except Exception as e:
            log.error(f"Belge silme hatası: {e}")
            return False
    
    def belge_guncelle(
        self,
        belge_id: int,
        guncellemeler: dict[str, Any],
        logger: Optional[logging.Logger] = None
    ) -> bool:
        """
        Belgeyi günceller (kısmi güncelleme).
        
        Parametreler:
        -------------
        belge_id : int
            Belge ID
        guncellemeler : dict
            Güncellenecek alan-değer çiftleri
            Örnek: {'form_onaylandi': 'Evet', 'hatirlatma_durumu': 'Aktif'}
        logger : Logger
        
        Döndürür:
        ---------
        bool
            Başarılı ise True
        
        Örnek:
        ------
        >>> onbellek.belge_guncelle(5, {'form_onaylandi': 'Evet'})
        True
        """
        log = logger or gunluk
        
        if not guncellemeler:
            log.warning("Güncelleme yapılacak alan yok")
            return False
        
        try:
            with self._baglanti_al() as baglanti:
                imlec = baglanti.cursor()
                
                # SQL oluştur
                set_clause = ', '.join([f"{alan} = ?" for alan in guncellemeler.keys()])
                sql = f"UPDATE belgeler SET {set_clause} WHERE id = ?"
                
                # Parametreleri hazırla
                parametreler = list(guncellemeler.values()) + [belge_id]
                
                # Çalıştır
                imlec.execute(sql, parametreler)
                
                if imlec.rowcount > 0:
                    log.info(f"✓ Belge güncellendi: ID={belge_id}, Alanlar={list(guncellemeler.keys())}")
                    return True
                else:
                    log.warning(f"Belge bulunamadı: ID={belge_id}")
                    return False
        
        except Exception as e:
            log.error(f"Belge güncelleme hatası: {e}")
            return False
    
    # =========================================================================
    # İSTATİSTİKLER
    # =========================================================================
    
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
        try:
            with self._baglanti_al() as baglanti:
                imlec = baglanti.cursor()
                
                # Toplam belge
                imlec.execute("SELECT COUNT(*) FROM belgeler")
                toplam_belge = imlec.fetchone()[0]
                
                # Uygulama belgeleri
                imlec.execute("SELECT COUNT(*) FROM belgeler WHERE belge_kaynak = 'UYGULAMA'")
                uygulama_belge = imlec.fetchone()[0]
                
                # Manuel belgeler
                imlec.execute("SELECT COUNT(*) FROM belgeler WHERE belge_kaynak = 'MANUEL'")
                manuel_belge = imlec.fetchone()[0]
                
                # Toplam ürün
                imlec.execute("SELECT COUNT(*) FROM belge_urunler")
                toplam_urun = imlec.fetchone()[0]
                
                return {
                    'toplam_belge': toplam_belge,
                    'uygulama_belge': uygulama_belge,
                    'manuel_belge': manuel_belge,
                    'toplam_urun': toplam_urun
                }
        
        except Exception as e:
            gunluk.error(f"İstatistik hatası: {e}")
            return {}


# Test
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("=" * 60)
    print("BELGE ÖNBELLEĞİ v3.0 - TEST")
    print("=" * 60)
    
    onbellek = BelgeOnbellegi()
    
    print("\n1. Test belgesi ekleme...")
    belge_id = onbellek.belge_ekle({
        'seri_numarasi': 'SN:280126-TEST-ISTANBUL-LK-ABC123-R00',
        'tarih': '2026-01-28',
        'proje_adi': 'TEST PROJESİ V3',
        'proje_konum': 'İstanbul',
        'belge_kaynak': 'MANUEL',
        'belge_tipi': 'FİYAT_TEKLİFİ',
        'kdvli_toplam_fiyat': '1500,00'
    })
    
    if belge_id:
        print(f"✓ Belge ID: {belge_id}")
        
        print("\n2. Test ürünleri ekleme...")
        onbellek.belge_urun_ekle(belge_id, 1, {
            'urun_kodu': 'LK',
            'urun_adi': 'HAVALANDIRMA KAPAK SETİ',
            'urun_adet': '10',
            'urun_birim_fiyat': '75,00',
            'urun_toplam_fiyat': '750,00'
        })
        
        onbellek.belge_urun_ekle(belge_id, 2, {
            'urun_kodu': 'ZP30',
            'urun_adi': 'DUMAN TAHLIYE FANI',
            'urun_adet': '5',
            'urun_birim_fiyat': '150,00',
            'urun_toplam_fiyat': '750,00'
        })
        
        print("\n3. Belge arama...")
        belgeler = onbellek.belge_ara(proje_adi='TEST', limit=5)
        print(f"✓ {len(belgeler)} belge bulundu")
        
        print("\n4. Ürünleri getirme...")
        urunler = onbellek.belge_urunlerini_getir(belge_id)
        print(f"✓ {len(urunler)} ürün bulundu")
        for u in urunler:
            print(f"  - {u['urun_kodu']}: {u['urun_adi']} x{u['urun_adet']}")
        
        print("\n5. İstatistikler...")
        stats = onbellek.istatistikler()
        print(f"✓ Toplam belge: {stats['toplam_belge']}")
        print(f"✓ Manuel belge: {stats['manuel_belge']}")
        print(f"✓ Toplam ürün: {stats['toplam_urun']}")
        
        print("\n✅ TEST BAŞARILI!")
