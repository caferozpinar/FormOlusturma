"""
Veritabanı Kaydedici Modülü (SQLite Backend)
============================================

CSV kaydedici yerine SQLite veritabanı kullanır.
Geriye uyumlu API sağlar.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from uygulama.veri.belge_onbellegi import BelgeOnbellegi
from uygulama.yardimcilar.fiyat_formatlayici import FiyatFormatlayici

# Modül günlükleyicisi
gunluk = logging.getLogger(__name__)


class VeritabaniKaydedici:
    """
    Belge kayıtlarını SQLite veritabanına kaydeder.
    
    CSV kaydedicinin yerine geçer, aynı API'yi kullanır.
    """
    
    MAKSIMUM_URUN_SAYISI = 30
    
    def __init__(self, veritabani_yolu: Optional[str | Path] = None):
        """
        Parametreler:
        -------------
        veritabani_yolu : str | Path | None
            SQLite veritabanı yolu (None ise varsayılan)
        """
        self.onbellek = BelgeOnbellegi(veritabani_yolu)
        self.fiyat_formatlayici = FiyatFormatlayici()
        gunluk.info("Veritabanı kaydedici hazır")
    
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
        Belge kaydını veritabanına ekler.
        
        Parametreler:
        -------------
        standart_girdiler : dict
            Ana pencereden gelen standart girdiler
        oturum_onbellegi : dict
            Ürün form verileri
        urun_kodlari : list
            Seçili ürün kodları
        seri_numarasi : str
            Belge seri numarası
        dosya_adi : str
            Oluşturulan dosya adı
        dosya_yolu : str | Path
            Belgenin tam yolu
        logger : Logger
        
        Döndürür:
        ---------
        bool
            Başarılı ise True
        """
        log = logger or gunluk
        
        try:
            # Fiyat tablosu ürünlerini topla
            urun_detaylari = self._fiyat_tablosu_urunlerini_topla(
                urun_kodlari,
                oturum_onbellegi,
                log
            )
            
            # KDV bilgilerini al
            kdv_orani = "0"
            kdvli_toplam = "0,00"
            genel_toplam = 0.0
            
            # Toplam fiyatı hesapla
            for urun in urun_detaylari:
                toplam_fiyat_str = urun.get('urun_toplam_fiyat', '')
                if toplam_fiyat_str:
                    try:
                        toplam_float = float(toplam_fiyat_str.replace(".", "").replace(",", "."))
                        genel_toplam += toplam_float
                    except:
                        pass
            
            # KDV hesapla
            if urun_kodlari and urun_kodlari[0] in oturum_onbellegi:
                ilk_urun_verisi = oturum_onbellegi[urun_kodlari[0]]
                kdv_orani = ilk_urun_verisi.get("kdv_line", "0")
                
                try:
                    kdv_float = self.fiyat_formatlayici.metin_sayiya_donustur(kdv_orani)
                    kdvli_toplam_float = genel_toplam * (1 + kdv_float / 100)
                    kdvli_toplam = f"{kdvli_toplam_float:.2f}".replace(".", ",")
                except:
                    kdvli_toplam = f"{genel_toplam:.2f}".replace(".", ",")
            
            # Kayıt verilerini hazırla
            simdi = datetime.now()
            
            kayit_verileri = {
                'seri_numarasi': seri_numarasi,
                'tarih': standart_girdiler.get('CURDATE', simdi.strftime("%Y-%m-%d")),
                'proje_adi': standart_girdiler.get('PROJEADI', ''),
                'proje_konum': standart_girdiler.get('PROJEKONUM', ''),
                'urun_kodlari': ', '.join(urun_kodlari),
                'revizyon_numarasi': standart_girdiler.get('REVIZYON', 'R01'),
                'dosya_adi': dosya_adi,
                'dosya_yolu': str(Path(dosya_yolu).absolute()),
                'olusturan_kisi': standart_girdiler.get('DUZENLEYEN', ''),
                'olusturma_saati': simdi.strftime("%H:%M:%S"),
                'kdv_orani': kdv_orani,
                'kdvli_toplam_fiyat': kdvli_toplam,
            }
            
            # Veritabanına kaydet
            basarili = self.onbellek.belge_kaydi_ekle(
                kayit_verileri,
                urun_detaylari,
                log
            )
            
            if basarili:
                log.info(f"✓ Belge kaydı veritabanına eklendi: {seri_numarasi}")
            
            return basarili
            
        except Exception as e:
            log.error(f"HATA: Kayıt ekleme başarısız: {e}")
            import traceback
            log.error(traceback.format_exc())
            return False
    
    def _fiyat_tablosu_urunlerini_topla(
        self,
        urun_kodlari: list[str],
        oturum_onbellegi: dict[str, dict[str, Any]],
        logger: logging.Logger
    ) -> list[dict[str, str]]:
        """
        Fiyat tablosu ürünlerini toplar.
        
        Parametreler:
        -------------
        urun_kodlari : list
            Ürün kodları
        oturum_onbellegi : dict
            Ürün form verileri
        logger : Logger
        
        Döndürür:
        ---------
        list[dict]
            Ürün detayları listesi (max 30)
        """
        import re
        
        urun_detaylari = []
        
        for urun_kodu in urun_kodlari:
            if len(urun_detaylari) >= self.MAKSIMUM_URUN_SAYISI:
                logger.warning(f"Maksimum ürün sayısı ({self.MAKSIMUM_URUN_SAYISI}) aşıldı!")
                break
            
            if urun_kodu not in oturum_onbellegi:
                continue
            
            urun_verisi = oturum_onbellegi[urun_kodu]
            
            # Dolu satırları bul
            dolu_satirlar = set()
            
            for anahtar in urun_verisi.keys():
                # urun_label_1, urun_label_2, ... kontrol et
                label_match = re.match(r'^urun_label_(\d+)$', anahtar)
                if label_match and str(urun_verisi[anahtar]).strip():
                    dolu_satirlar.add(int(label_match.group(1)))
                
                # adet_line_1, adet_line_2, ... kontrol et
                adet_match = re.match(r'^adet_line_(\d+)$', anahtar)
                if adet_match and str(urun_verisi[anahtar]).strip():
                    dolu_satirlar.add(int(adet_match.group(1)))
                
                # brmfiyat_line_1, brmfiyat_line_2, ... kontrol et
                fiyat_match = re.match(r'^brmfiyat_line_(\d+)$', anahtar)
                if fiyat_match and str(urun_verisi[anahtar]).strip():
                    dolu_satirlar.add(int(fiyat_match.group(1)))
            
            # Dolu satırları işle
            for satir_no in sorted(dolu_satirlar):
                if len(urun_detaylari) >= self.MAKSIMUM_URUN_SAYISI:
                    break
                
                # Ürün bilgilerini al
                urun_adi = str(urun_verisi.get(f"urun_label_{satir_no}", "")).strip()
                if not urun_adi:
                    urun_adi = f"{urun_kodu} - Ürün {satir_no}"
                
                adet = str(urun_verisi.get(f"adet_line_{satir_no}", "")).strip()
                if not adet:
                    adet = "0"
                
                birim_fiyat = str(urun_verisi.get(f"brmfiyat_line_{satir_no}", "")).strip()
                if not birim_fiyat:
                    birim_fiyat = "0,00"
                
                toplam_fiyat = str(urun_verisi.get(f"top_line_{satir_no}", "")).strip()
                if not toplam_fiyat:
                    toplam_fiyat = "0,00"
                
                # Listeye ekle
                urun_detaylari.append({
                    'urun_adi': urun_adi,
                    'urun_adet': adet,
                    'urun_birim_fiyat': birim_fiyat,
                    'urun_toplam_fiyat': toplam_fiyat
                })
        
        logger.debug(f"Fiyat tablosu: {len(urun_detaylari)} ürün toplandı")
        return urun_detaylari
    
    def kayit_ara(
        self,
        **filtreler
    ) -> list[dict[str, Any]]:
        """
        Kayıt arar (çok yönlü).
        
        Parametreler:
        -------------
        **filtreler : dict
            seri_numarasi, proje_adi, proje_konum, 
            tarih_baslangic, tarih_bitis, urun_kodu, limit
        
        Döndürür:
        ---------
        list[dict]
            Bulunan kayıtlar
        """
        return self.onbellek.belge_kaydi_ara(**filtreler)
    
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
            Tab_2 form girdileri
        logger : Logger
        
        Döndürür:
        ---------
        bool
            Başarılı ise True
        """
        log = logger or gunluk
        
        # Veri formatını dönüştür (UI alanlarından → veritabanı kolonlarına)
        veritabani_verileri = {
            'belge_tarih': tab2_verileri.get('belge_tarih_line', ''),
            'proje_adi': tab2_verileri.get('belge_projeadi_line', ''),
            'proje_yeri': tab2_verileri.get('belge_projeyeri_line', ''),
            'toplam_teklif': tab2_verileri.get('toplamteklif_line', ''),
            'notlar': tab2_verileri.get('notlar_textEdit', ''),
        }
        
        # Belge tipi (radio button)
        belge_tipi = ''
        if tab2_verileri.get('teklif_radio', False):
            belge_tipi = 'Teklif'
        elif tab2_verileri.get('kesif_radio', False):
            belge_tipi = 'Keşif'
        elif tab2_verileri.get('tanim_radio', False):
            belge_tipi = 'Tanım'
        
        veritabani_verileri['belge_tipi'] = belge_tipi
        
        # Ürün bilgileri (6 ürün)
        for i in range(1, 7):
            veritabani_verileri[f'urun{i}_kod'] = tab2_verileri.get(f'urun{i}_kod_line', '')
            veritabani_verileri[f'urun{i}_adet'] = tab2_verileri.get(f'urun{i}_adet_line', '')
            veritabani_verileri[f'urun{i}_ozl'] = tab2_verileri.get(f'urun{i}_ozl_line', '')
        
        # Veritabanına kaydet
        return self.onbellek.tab2_kaydi_ekle(veritabani_verileri, log)
    
    def tab2_kayitlari_ara(
        self,
        **filtreler
    ) -> list[dict[str, Any]]:
        """
        Tab2 kayıtlarını arar.
        
        Parametreler:
        -------------
        **filtreler : dict
            proje_adi, proje_yeri, belge_tipi,
            tarih_baslangic, tarih_bitis, urun_kodu, limit
        
        Döndürür:
        ---------
        list[dict]
            Bulunan kayıtlar
        """
        return self.onbellek.tab2_kayitlari_ara(**filtreler)
    
    def istatistikler(
        self,
        logger: Optional[logging.Logger] = None
    ) -> dict[str, Any]:
        """
        Veritabanı istatistiklerini döner.
        
        Döndürür:
        ---------
        dict
            İstatistik bilgileri
        """
        return self.onbellek.istatistikler(logger)
