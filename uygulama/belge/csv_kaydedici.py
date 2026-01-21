"""
CSV Kaydedici Modülü
====================

Oluşturulan her belge için CSV kayıt tutma sistemi.

Bu modül:
- Her belge için CSV'ye detaylı kayıt açar
- Proje bilgileri, ürünler, fiyatlar, durum takibi gibi verileri saklar
- Network senkronizasyonu için hazır format kullanır
- Veri analizi ve istatistik hesaplama için optimize edilmiştir

CSV Sütun Yapısı:
-----------------
- SeriNumarasi: Benzersiz belge tanımlayıcısı
- Tarih: Belge oluşturma tarihi
- ProjeAdi: Proje adı
- ProjeKonum: Proje konumu
- UrunKodlari: Ürün kodları (virgülle ayrılmış)
- UrunAdetleri: Ürün adetleri (virgülle ayrılmış)
- UrunBirimFiyatlari: Ürün birim fiyatları (virgülle ayrılmış)
- UrunToplamFiyatlari: Ürün toplam fiyatları (virgülle ayrılmış)
- GenelToplamFiyat: Projenin genel toplam fiyatı
- RevizyonNumarasi: Revizyon numarası
- DosyaAdi: Oluşturulan dosya adı
- OlusturanKisi: Belgeyi oluşturan kişi
- FormOnaylandi: Form onay durumu (Evet/Hayır)
- SonGuncellemeTarihi: En son güncelleme tarihi
- HatirlatmaDurumu: Hatırlatma durumu (Aktif/Pasif)
- DosyaYolu: Belgenin tam dosya yolu
- OlusturmaSaati: Belge oluşturulma saati
- KDVOrani: KDV oranı
- KDVliToplamFiyat: KDV'li toplam fiyat
"""

from __future__ import annotations

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from uygulama.yardimcilar.fiyat_formatlayici import FiyatFormatlayici

# Modül günlükleyicisi
gunluk = logging.getLogger(__name__)


class CSVKaydedici:
    """
    CSV kayıt sistemi yöneticisi.
    
    Kullanım:
    ---------
    >>> kaydedici = CSVKaydedici('/path/to/kayitlar/belgeler.csv')
    >>> kayit = {
    ...     'SeriNumarasi': 'SN:251225-FIRMA-KONUM-ZR20_LK-ABC123-R01',
    ...     'ProjeAdi': 'Test Projesi',
    ...     'GenelToplamFiyat': '125000.50',
    ... }
    >>> kaydedici.kayit_ekle(kayit)
    """
    
    # Maksimum ürün sayısı (6 ürün kodu * 5 ürün/kod = 30 ürün)
    MAKSIMUM_URUN_SAYISI = 30
    
    # CSV başlıkları
    # Temel bilgiler
    TEMEL_BASLIKLAR = [
        "SeriNumarasi",
        "Tarih",
        "ProjeAdi",
        "ProjeKonum",
        "UrunKodlari",
        "RevizyonNumarasi",
        "DosyaAdi",
        "OlusturanKisi",
        "FormOnaylandi",
        "SonGuncellemeTarihi",
        "HatirlatmaDurumu",
        "DosyaYolu",
        "OlusturmaSaati",
        "KDVOrani",
        "KDVliToplamFiyat",
    ]
    
    # Fiyat tablosu ürün sütunları (30 ürün için)
    # Her ürün için: İsim, Adet, Birim Fiyat, Toplam Fiyat
    URUN_BASLIKLAR = []
    for i in range(1, MAKSIMUM_URUN_SAYISI + 1):
        URUN_BASLIKLAR.extend([
            f"Urun{i}Adi",
            f"Urun{i}Adet",
            f"Urun{i}BirimFiyat",
            f"Urun{i}ToplamFiyat",
        ])
    
    # Tüm başlıkları birleştir
    BASLIKLAR = TEMEL_BASLIKLAR + URUN_BASLIKLAR
    
    def __init__(self, csv_yolu: str | Path):
        """
        CSV Kaydedici başlatıcısı.
        
        Parametreler:
        -------------
        csv_yolu : str | Path
            CSV dosyası yolu
        """
        self.csv_yolu = Path(csv_yolu)
        self.fiyat_formatlayici = FiyatFormatlayici()
        
        # CSV dosyası yoksa oluştur
        if not self.csv_yolu.exists():
            self._csv_olustur()
    
    def _csv_olustur(self) -> None:
        """Başlıklarla yeni CSV dosyası oluşturur."""
        try:
            # Dizini oluştur
            self.csv_yolu.parent.mkdir(parents=True, exist_ok=True)
            
            # CSV dosyası oluştur
            with self.csv_yolu.open('w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=self.BASLIKLAR)
                writer.writeheader()
            
            gunluk.info(f"✓ CSV dosyası oluşturuldu: {self.csv_yolu}")
            
        except Exception as e:
            gunluk.error(f"HATA: CSV dosyası oluşturulamadı: {e}")
            raise
    
    def kayit_ekle(
        self,
        standart_girdiler: dict[str, str],
        oturum_onbellegi: dict[str, dict[str, Any]],
        urun_kodlari: list[str],
        seri_numarasi: str,
        dosya_adi: str,
        dosya_yolu: str | Path,
        logger: Optional[logging.Logger] = None
    ) -> bool:
        """
        CSV'ye yeni kayıt ekler.
        
        Parametreler:
        -------------
        standart_girdiler : dict[str, str]
            Ana pencereden toplanan standart girdiler
        oturum_onbellegi : dict[str, dict[str, Any]]
            Ürünlere ait form verileri
        urun_kodlari : list[str]
            Seçili ürün kodları
        seri_numarasi : str
            Belge seri numarası
        dosya_adi : str
            Oluşturulan dosya adı
        dosya_yolu : str | Path
            Belgenin tam dosya yolu
        logger : Optional[logging.Logger]
            Logger referansı
        
        Döndürür:
        ---------
        bool
            Başarılı ise True
        """
        log = logger or gunluk
        
        try:
            # Fiyat tablosu ürünlerini topla
            fiyat_tablosu_urunleri = self._fiyat_tablosu_urunlerini_topla(
                urun_kodlari,
                oturum_onbellegi,
                log
            )
            
            # KDV bilgilerini al (ilk üründen)
            kdv_orani = "0"
            kdvli_toplam = "0,00"
            
            # GenelToplamFiyat'ı fiyat tablosu ürünlerinden hesapla
            genel_toplam = 0.0
            for i in range(1, self.MAKSIMUM_URUN_SAYISI + 1):
                toplam_fiyat_str = fiyat_tablosu_urunleri.get(f"Urun{i}ToplamFiyat", "")
                if toplam_fiyat_str:
                    try:
                        toplam_float = float(toplam_fiyat_str.replace(".", "").replace(",", "."))
                        genel_toplam += toplam_float
                    except:
                        pass
            
            if urun_kodlari and urun_kodlari[0] in oturum_onbellegi:
                ilk_urun_verisi = oturum_onbellegi[urun_kodlari[0]]
                kdv_orani = ilk_urun_verisi.get("kdv_line", "0")
                
                # KDV'li toplamı hesapla
                try:
                    kdv_float = self.fiyat_formatlayici.metin_sayiya_donustur(kdv_orani)
                    kdvli_toplam_float = genel_toplam * (1 + kdv_float / 100)
                    kdvli_toplam = f"{kdvli_toplam_float:.2f}".replace(".", ",")
                except:
                    kdvli_toplam = f"{genel_toplam:.2f}".replace(".", ",")
            
            # Kayıt satırı oluştur
            simdi = datetime.now()
            
            kayit = {
                "SeriNumarasi": seri_numarasi,
                "Tarih": standart_girdiler.get("CURDATE", simdi.strftime("%Y-%m-%d")),
                "ProjeAdi": standart_girdiler.get("PROJEADI", ""),
                "ProjeKonum": standart_girdiler.get("PROJEKONUM", ""),
                "UrunKodlari": ", ".join(urun_kodlari),
                "RevizyonNumarasi": standart_girdiler.get("REVIZYON", "R01"),
                "DosyaAdi": dosya_adi,
                "OlusturanKisi": standart_girdiler.get("DUZENLEYEN", ""),
                "FormOnaylandi": "Hayır",  # Varsayılan
                "SonGuncellemeTarihi": standart_girdiler.get("CURDATE", simdi.strftime("%Y-%m-%d")),
                "HatirlatmaDurumu": "Pasif",  # Varsayılan
                "DosyaYolu": str(Path(dosya_yolu).absolute()),
                "OlusturmaSaati": simdi.strftime("%H:%M:%S"),
                "KDVOrani": kdv_orani,
                "KDVliToplamFiyat": kdvli_toplam,
            }
            
            # Fiyat tablosu ürünlerini ekle (30 ürün için boş alanlar)
            kayit.update(fiyat_tablosu_urunleri)
            
            # CSV'ye yaz
            with self.csv_yolu.open('a', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=self.BASLIKLAR)
                writer.writerow(kayit)
            
            log.info(f"✓ CSV kaydı eklendi: {seri_numarasi}")
            return True
            
        except Exception as e:
            log.error(f"HATA: CSV kayıt ekleme başarısız: {e}")
            return False
    
    def _fiyat_tablosu_urunlerini_topla(
        self,
        urun_kodlari: list[str],
        oturum_onbellegi: dict[str, dict[str, Any]],
        logger: logging.Logger
    ) -> dict[str, str]:
        """
        Fiyat tablosundaki tüm ürünleri toplar ve CSV formatına hazırlar.
        
        Her ürün kodu için en fazla 5 ürün (satır) olabilir.
        Toplam 30 ürün için sütunlar oluşturulur (6 kod * 5 ürün).
        
        Her ürün için 4 sütun:
        - UrunNAdi: Ürün açıklaması (urun_label_N)
        - UrunNAdet: Ürün adedi (adet_line_N)
        - UrunNBirimFiyat: Birim fiyat (brmfiyat_line_N)
        - UrunNToplamFiyat: Toplam fiyat (top_line_N)
        
        Döndürür:
        ---------
        dict[str, str]
            30 ürün için 120 sütun (her biri boş string veya dolu)
        """
        import re
        
        # 30 ürün için boş sözlük hazırla
        sonuc = {}
        for i in range(1, self.MAKSIMUM_URUN_SAYISI + 1):
            sonuc[f"Urun{i}Adi"] = ""
            sonuc[f"Urun{i}Adet"] = ""
            sonuc[f"Urun{i}BirimFiyat"] = ""
            sonuc[f"Urun{i}ToplamFiyat"] = ""
        
        # Tüm ürünleri sırayla topla
        urun_sayaci = 1
        
        for urun_kodu in urun_kodlari:
            if urun_kodu not in oturum_onbellegi:
                logger.warning(f"Ürün kodu verisi bulunamadı: {urun_kodu}")
                continue
            
            urun_verisi = oturum_onbellegi[urun_kodu]
            
            # Bu ürün kodunda hangi satırlar dolu?
            # adet_line_* veya brmfiyat_line_* alanlarında dolu olan satırları bul
            dolu_satirlar = set()
            
            for anahtar in urun_verisi.keys():
                # adet_line_1, adet_line_2, ... kontrol et
                adet_match = re.match(r'^adet_line_(\d+)$', anahtar)
                if adet_match and str(urun_verisi[anahtar]).strip():
                    dolu_satirlar.add(int(adet_match.group(1)))
                
                # brmfiyat_line_1, brmfiyat_line_2, ... kontrol et
                fiyat_match = re.match(r'^brmfiyat_line_(\d+)$', anahtar)
                if fiyat_match and str(urun_verisi[anahtar]).strip():
                    dolu_satirlar.add(int(fiyat_match.group(1)))
            
            # Dolu satırları sıralı şekilde işle
            for satir_no in sorted(dolu_satirlar):
                if urun_sayaci > self.MAKSIMUM_URUN_SAYISI:
                    logger.warning(f"Maksimum ürün sayısı ({self.MAKSIMUM_URUN_SAYISI}) aşıldı!")
                    break
                
                # Ürün adı (urun_label_N)
                urun_adi_key = f"urun_label_{satir_no}"
                urun_adi = str(urun_verisi.get(urun_adi_key, "")).strip()
                if not urun_adi:
                    # Fallback: ürün kodu kullan
                    urun_adi = f"{urun_kodu} - Ürün {satir_no}"
                
                # Adet (adet_line_N)
                adet_key = f"adet_line_{satir_no}"
                adet = str(urun_verisi.get(adet_key, "")).strip()
                if not adet:
                    adet = "0"
                
                # Birim fiyat (brmfiyat_line_N)
                birim_fiyat_key = f"brmfiyat_line_{satir_no}"
                birim_fiyat = str(urun_verisi.get(birim_fiyat_key, "")).strip()
                if not birim_fiyat:
                    birim_fiyat = "0,00"
                
                # Toplam fiyat (top_line_N)
                toplam_fiyat_key = f"top_line_{satir_no}"
                toplam_fiyat = str(urun_verisi.get(toplam_fiyat_key, "")).strip()
                if not toplam_fiyat:
                    toplam_fiyat = "0,00"
                
                # CSV'ye ekle
                sonuc[f"Urun{urun_sayaci}Adi"] = urun_adi
                sonuc[f"Urun{urun_sayaci}Adet"] = adet
                sonuc[f"Urun{urun_sayaci}BirimFiyat"] = birim_fiyat
                sonuc[f"Urun{urun_sayaci}ToplamFiyat"] = toplam_fiyat
                
                urun_sayaci += 1
            
            # Eğer maksimum sayıya ulaştıysak dur
            if urun_sayaci > self.MAKSIMUM_URUN_SAYISI:
                break
        
        logger.info(f"Fiyat tablosu: {urun_sayaci - 1} ürün CSV'ye eklendi")
        return sonuc
    
    def kayit_guncelle(
        self,
        seri_numarasi: str,
        guncellemeler: dict[str, str],
        logger: Optional[logging.Logger] = None
    ) -> bool:
        """
        Var olan kaydı günceller.
        
        Parametreler:
        -------------
        seri_numarasi : str
            Güncellenecek kaydın seri numarası
        guncellemeler : dict[str, str]
            Güncellenecek alanlar ve yeni değerler
        logger : Optional[logging.Logger]
            Logger referansı
        
        Döndürür:
        ---------
        bool
            Başarılı ise True
        """
        log = logger or gunluk
        
        try:
            # Tüm kayıtları oku
            kayitlar = []
            with self.csv_yolu.open('r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                kayitlar = list(reader)
            
            # İlgili kaydı bul ve güncelle
            bulundu = False
            for kayit in kayitlar:
                if kayit["SeriNumarasi"] == seri_numarasi:
                    kayit.update(guncellemeler)
                    
                    # Son güncelleme tarihini otomatik güncelle
                    if "SonGuncellemeTarihi" not in guncellemeler:
                        kayit["SonGuncellemeTarihi"] = datetime.now().strftime("%Y-%m-%d")
                    
                    bulundu = True
                    break
            
            if not bulundu:
                log.warning(f"Kayıt bulunamadı: {seri_numarasi}")
                return False
            
            # Tüm kayıtları geri yaz
            with self.csv_yolu.open('w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=self.BASLIKLAR)
                writer.writeheader()
                writer.writerows(kayitlar)
            
            log.info(f"✓ CSV kaydı güncellendi: {seri_numarasi}")
            return True
            
        except Exception as e:
            log.error(f"HATA: CSV kayıt güncelleme başarısız: {e}")
            return False
    
    def kayit_sil(
        self,
        seri_numarasi: str,
        logger: Optional[logging.Logger] = None
    ) -> bool:
        """
        Kaydı siler.
        
        Parametreler:
        -------------
        seri_numarasi : str
            Silinecek kaydın seri numarası
        logger : Optional[logging.Logger]
            Logger referansı
        
        Döndürür:
        ---------
        bool
            Başarılı ise True
        """
        log = logger or gunluk
        
        try:
            # Tüm kayıtları oku
            kayitlar = []
            with self.csv_yolu.open('r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                kayitlar = list(reader)
            
            # İlgili kaydı filtrele
            onceki_sayi = len(kayitlar)
            kayitlar = [k for k in kayitlar if k["SeriNumarasi"] != seri_numarasi]
            
            if len(kayitlar) == onceki_sayi:
                log.warning(f"Kayıt bulunamadı: {seri_numarasi}")
                return False
            
            # Tüm kayıtları geri yaz
            with self.csv_yolu.open('w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=self.BASLIKLAR)
                writer.writeheader()
                writer.writerows(kayitlar)
            
            log.info(f"✓ CSV kaydı silindi: {seri_numarasi}")
            return True
            
        except Exception as e:
            log.error(f"HATA: CSV kayıt silme başarısız: {e}")
            return False
    
    def kayit_ara(
        self,
        seri_numarasi: str,
        logger: Optional[logging.Logger] = None
    ) -> Optional[dict[str, str]]:
        """
        Kaydı arar ve döndürür.
        
        Parametreler:
        -------------
        seri_numarasi : str
            Aranacak kaydın seri numarası
        logger : Optional[logging.Logger]
            Logger referansı
        
        Döndürür:
        ---------
        Optional[dict[str, str]]
            Kayıt sözlüğü veya None (bulunamazsa)
        """
        log = logger or gunluk
        
        try:
            with self.csv_yolu.open('r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for kayit in reader:
                    if kayit["SeriNumarasi"] == seri_numarasi:
                        log.debug(f"Kayıt bulundu: {seri_numarasi}")
                        return kayit
            
            log.warning(f"Kayıt bulunamadı: {seri_numarasi}")
            return None
            
        except Exception as e:
            log.error(f"HATA: CSV kayıt arama başarısız: {e}")
            return None
    
    def tum_kayitlari_al(
        self,
        logger: Optional[logging.Logger] = None
    ) -> list[dict[str, str]]:
        """
        Tüm kayıtları döndürür.
        
        Parametreler:
        -------------
        logger : Optional[logging.Logger]
            Logger referansı
        
        Döndürür:
        ---------
        list[dict[str, str]]
            Kayıt listesi
        """
        log = logger or gunluk
        
        try:
            with self.csv_yolu.open('r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                kayitlar = list(reader)
            
            log.debug(f"{len(kayitlar)} kayıt okundu")
            return kayitlar
            
        except Exception as e:
            log.error(f"HATA: CSV kayıt okuma başarısız: {e}")
            return []
