"""
Veritabanı Kaydedici Modülü (v3.0)
==================================

HIGH-LEVEL API: İş mantığı ve validasyon katmanı.

Yeni Yapı:
---------
- Tek ana tablo: belgeler (UYGULAMA + MANUEL)
- Esnek ürün: belge_urunler (1-N)
- Basit API

Değişiklikler (v2.x → v3.0):
- ✅ kayit_ekle() → Yeni tablo yapısı
- ✅ tab2_kaydi_ekle() → Aynı tabloya MANUEL olarak
- ✅ Arama metodları birleştirildi
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
    Belge kayıtlarını veritabanına kaydeder (HIGH-LEVEL).
    
    İki kayıt tipi:
    1. Uygulama belgesi (belge_kaynak='UYGULAMA')
    2. Manuel belge (belge_kaynak='MANUEL')
    
    Her ikisi de aynı tabloya kaydedilir: belgeler
    """
    
    def __init__(self, veritabani_yolu: Optional[str | Path] = None):
        """
        Parametreler:
        -------------
        veritabani_yolu : str | Path | None
            SQLite veritabanı yolu (None ise varsayılan)
        """
        self.onbellek = BelgeOnbellegi(veritabani_yolu)
        self.fiyat_formatlayici = FiyatFormatlayici()
        gunluk.info("VeritabanıKaydedici v3.0 hazır")
    
    # =========================================================================
    # UYGULAMA BELGESİ KAYDETME (Ana Uygulama)
    # =========================================================================
    
    def kayit_ekle(
        self,
        standart_girdiler: dict[str, str],
        oturum_onbellegi: dict[str, dict[str, Any]],
        urun_kodlari: list[str],
        seri_numarasi: str,
        dosya_adi: str,
        dosya_yolu: str | Path,
        ztf_veri_json: Optional[str] = None,
        logger: Optional[logging.Logger] = None
    ) -> bool:
        """
        Uygulama belgesi kaydeder (belge_kaynak='UYGULAMA').
        
        Parametreler:
        -------------
        standart_girdiler : dict
            Ana pencereden gelen standart girdiler
            - PROJEADI, PROJEKONUM, CURDATE, DUZENLEYEN, REVIZYON
        oturum_onbellegi : dict
            Ürün form verileri {urun_kodu: {form_verileri}}
        urun_kodlari : list
            Seçili ürün kodları ['LK', 'ZP30', ...]
        seri_numarasi : str
            Belge seri numarası
        dosya_adi : str
            Oluşturulan dosya adı (uzantısız)
        dosya_yolu : str | Path
            Belgenin tam yolu
        ztf_veri_json : str | None
            ZTF JSON verisi (form verileri)
        logger : Logger
        
        Döndürür:
        ---------
        bool
            Başarılı ise True
        
        Örnek:
        ------
        >>> kaydedici.kayit_ekle(
        ...     standart_girdiler={'PROJEADI': 'Test', ...},
        ...     oturum_onbellegi={'LK': {...}},
        ...     urun_kodlari=['LK', 'ZP30'],
        ...     seri_numarasi='SN:...',
        ...     dosya_adi='TEST-280126',
        ...     dosya_yolu='/ciktilar/TEST-280126.docx'
        ... )
        """
        log = logger or gunluk
        
        try:
            # Ürün detaylarını topla
            urun_detaylari = self._fiyat_tablosu_urunlerini_topla(
                urun_kodlari,
                oturum_onbellegi,
                log
            )
            
            # KDV bilgilerini hesapla
            kdv_orani, kdvli_toplam = self._kdv_hesapla(
                urun_detaylari,
                urun_kodlari,
                oturum_onbellegi
            )
            
            # Tarih işle
            from uygulama.yardimcilar.tarih_yardimcilari import tarih_donustur, bugun
            
            curdate = standart_girdiler.get('CURDATE', '')
            if curdate:
                # CURDATE varsa, veritabanı formatına çevir
                basarili, tarih_veritabani, _ = tarih_donustur(curdate, "veritabani")
                if not basarili:
                    # Formatlanamadıysa bugünü kullan
                    tarih_veritabani = bugun("veritabani")
            else:
                # CURDATE yoksa bugünü kullan
                tarih_veritabani = bugun("veritabani")
            
            # Belge kaydını hazırla
            simdi = datetime.now()
            
            belge_kaydi = {
                'seri_numarasi': seri_numarasi,
                'tarih': tarih_veritabani,  # Veritabanı formatı: YYYY-MM-DD
                'proje_adi': standart_girdiler.get('PROJEADI', ''),
                'proje_konum': standart_girdiler.get('PROJEKONUM', ''),
                'belge_kaynak': 'UYGULAMA',  # UYGULAMA belgesi
                'belge_tipi': 'FİYAT_TEKLİFİ',  # Varsayılan
                'revizyon_numarasi': standart_girdiler.get('REVIZYON', 'R00'),
                'dosya_adi': dosya_adi,
                'dosya_yolu': str(Path(dosya_yolu).absolute()),
                'kdv_orani': kdv_orani,
                'kdvli_toplam_fiyat': kdvli_toplam,
                'olusturan_kisi': standart_girdiler.get('DUZENLEYEN', ''),
                'olusturma_saati': simdi.strftime("%H:%M:%S"),
                'ztf_veri_json': ztf_veri_json,  # ZTF JSON
                'uygulama_surumu': self.onbellek.UYGULAMA_SURUMU
            }
            
            # Belgeyi ekle
            belge_id = self.onbellek.belge_ekle(belge_kaydi, log)
            
            if not belge_id:
                log.error("Belge eklenemedi")
                return False
            
            # Ürünleri ekle
            for sira_no, urun in enumerate(urun_detaylari, 1):
                basarili = self.onbellek.belge_urun_ekle(belge_id, sira_no, urun, log)
                if not basarili:
                    log.warning(f"Ürün eklenemedi: sıra={sira_no}")
            
            log.info(f"✓ Uygulama belgesi kaydedildi: {seri_numarasi} ({len(urun_detaylari)} ürün)")
            return True
        
        except Exception as e:
            log.error(f"UYGULAMA belgesi kayıt hatası: {e}")
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
        Fiyat tablosu ürünlerini toplar (UYGULAMA için).
        
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
            Ürün detayları (sınırsız)
        """
        import re
        
        urun_detaylari = []
        
        for urun_kodu in urun_kodlari:
            if urun_kodu not in oturum_onbellegi:
                continue
            
            urun_verisi = oturum_onbellegi[urun_kodu]
            
            # Dolu satırları bul
            dolu_satirlar = set()
            
            for anahtar in urun_verisi.keys():
                # urun_label_1, urun_label_2, ...
                label_match = re.match(r'^urun_label_(\d+)$', anahtar)
                if label_match and str(urun_verisi[anahtar]).strip():
                    dolu_satirlar.add(int(label_match.group(1)))
                
                # adet_line_1, adet_line_2, ...
                adet_match = re.match(r'^adet_line_(\d+)$', anahtar)
                if adet_match and str(urun_verisi[anahtar]).strip():
                    dolu_satirlar.add(int(adet_match.group(1)))
                
                # brmfiyat_line_1, brmfiyat_line_2, ...
                fiyat_match = re.match(r'^brmfiyat_line_(\d+)$', anahtar)
                if fiyat_match and str(urun_verisi[anahtar]).strip():
                    dolu_satirlar.add(int(fiyat_match.group(1)))
            
            # Dolu satırları işle
            for satir_no in sorted(dolu_satirlar):
                urun_adi = str(urun_verisi.get(f"urun_label_{satir_no}", "")).strip()
                if not urun_adi:
                    urun_adi = f"{urun_kodu} - Ürün {satir_no}"
                
                adet = str(urun_verisi.get(f"adet_line_{satir_no}", "0")).strip()
                birim_fiyat = str(urun_verisi.get(f"brmfiyat_line_{satir_no}", "0,00")).strip()
                toplam_fiyat = str(urun_verisi.get(f"top_line_{satir_no}", "0,00")).strip()
                
                urun_detaylari.append({
                    'urun_kodu': urun_kodu,
                    'urun_adi': urun_adi,
                    'urun_adet': adet,
                    'urun_ozellik': '',  # Opsiyonel
                    'urun_birim_fiyat': birim_fiyat,
                    'urun_toplam_fiyat': toplam_fiyat
                })
        
        logger.debug(f"Fiyat tablosu: {len(urun_detaylari)} ürün toplandı")
        return urun_detaylari
    
    def _kdv_hesapla(
        self,
        urun_detaylari: list[dict],
        urun_kodlari: list[str],
        oturum_onbellegi: dict
    ) -> tuple[str, str]:
        """
        KDV hesaplar.
        
        Döndürür:
        ---------
        tuple[str, str]
            (kdv_orani, kdvli_toplam)
        """
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
                kdvli_toplam = f"{kdvli_toplam_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            except:
                kdvli_toplam = f"{genel_toplam:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        return kdv_orani, kdvli_toplam
    
    # =========================================================================
    # MANUEL BELGE KAYDETME (Tab_2)
    # =========================================================================
    
    def tab2_kaydi_ekle(
        self,
        tab2_verileri: dict[str, Any],
        logger: Optional[logging.Logger] = None
    ) -> bool:
        """
        Manuel belge kaydeder (belge_kaynak='MANUEL').
        
        Tab_2 formundan gelen verileri belgeler tablosuna ekler.
        
        Parametreler:
        -------------
        tab2_verileri : dict
            Tab_2 form girdileri:
            - belge_tarih_line
            - belge_projeadi_line
            - belge_projeyeri_line
            - seri_numarasi (YENİ!)
            - urun1_kod_line ... urun6_kod_line
            - urun1_adet_line ... urun6_adet_line
            - urun1_ozl_line ... urun6_ozl_line
            - toplamteklif_line
            - teklif_radio, kesif_radio, tanim_radio
            - notlar_textEdit
        logger : Logger
        
        Döndürür:
        ---------
        bool
            Başarılı ise True
        
        Örnek:
        ------
        >>> kaydedici.tab2_kaydi_ekle({
        ...     'belge_tarih_line': '2026-01-28',
        ...     'belge_projeadi_line': 'Manuel Proje',
        ...     'belge_projeyeri_line': 'Ankara',
        ...     'seri_numarasi': 'SN:...',
        ...     'urun1_kod_line': 'LK',
        ...     'urun1_adet_line': '5',
        ...     'urun1_ozl_line': 'Özellik 1',
        ...     'toplamteklif_line': '500,00',
        ...     'notlar_textEdit': 'Test notları'
        ... })
        """
        log = logger or gunluk
        
        try:
            # Belge kaydını hazırla
            simdi = datetime.now()
            
            # Belge tipi (radio button)
            belge_tipi = ''
            if tab2_verileri.get('teklif_radio', False):
                belge_tipi = 'FİYAT_TEKLİFİ'
            elif tab2_verileri.get('kesif_radio', False):
                belge_tipi = 'KEŞİF_ÖZETİ'
            elif tab2_verileri.get('tanim_radio', False):
                belge_tipi = 'TANIM'
            
            # Tarih işle
            from uygulama.yardimcilar.tarih_yardimcilari import tarih_donustur, bugun
            
            belge_tarih_line = tab2_verileri.get('belge_tarih_line', '')
            if belge_tarih_line:
                # belge_tarih_line varsa, veritabanı formatına çevir
                basarili, tarih_veritabani, _ = tarih_donustur(belge_tarih_line, "veritabani")
                if not basarili:
                    # Formatlanamadıysa bugünü kullan
                    tarih_veritabani = bugun("veritabani")
                    log.warning(f"MANUEL belge tarihi formatlanamadı: {belge_tarih_line}")
            else:
                # Tarih yoksa bugünü kullan
                tarih_veritabani = bugun("veritabani")
            
            belge_kaydi = {
                'seri_numarasi': tab2_verileri.get('seri_numarasi', f'MANUEL-{simdi.strftime("%Y%m%d%H%M%S")}'),
                'tarih': tarih_veritabani,  # Veritabanı formatı: YYYY-MM-DD
                'proje_adi': tab2_verileri.get('belge_projeadi_line', ''),
                'proje_konum': tab2_verileri.get('belge_projeyeri_line', ''),
                'belge_kaynak': 'MANUEL',  # MANUEL belgesi
                'belge_tipi': belge_tipi,
                'kdvli_toplam_fiyat': tab2_verileri.get('toplamteklif_line', ''),
                'notlar': tab2_verileri.get('notlar_textEdit', ''),
                'uygulama_surumu': self.onbellek.UYGULAMA_SURUMU
            }
            
            # Belgeyi ekle
            belge_id = self.onbellek.belge_ekle(belge_kaydi, log)
            
            if not belge_id:
                log.error("Manuel belge eklenemedi")
                return False
            
            # Ürünleri ekle (6 ürün)
            urun_sayisi = 0
            for i in range(1, 7):
                urun_kod = tab2_verileri.get(f'urun{i}_kod_line', '').strip()
                if not urun_kod:
                    continue
                
                urun = {
                    'urun_kodu': urun_kod,
                    'urun_adi': '',  # Manuel girişte ürün adı yok
                    'urun_adet': tab2_verileri.get(f'urun{i}_adet_line', ''),
                    'urun_ozellik': tab2_verileri.get(f'urun{i}_ozl_line', ''),
                    'urun_birim_fiyat': '',
                    'urun_toplam_fiyat': ''
                }
                
                basarili = self.onbellek.belge_urun_ekle(belge_id, i, urun, log)
                if basarili:
                    urun_sayisi += 1
            
            log.info(f"✓ Manuel belge kaydedildi: {belge_kaydi['seri_numarasi']} ({urun_sayisi} ürün)")
            return True
        
        except Exception as e:
            log.error(f"MANUEL belge kayıt hatası: {e}")
            import traceback
            log.error(traceback.format_exc())
            return False
    
    # =========================================================================
    # ARAMA METODLARI
    # =========================================================================
    
    def kayit_ara(
        self,
        **filtreler
    ) -> list[dict[str, Any]]:
        """
        Belge arar (tüm belgeler).
        
        Parametreler:
        -------------
        **filtreler : dict
            Arama kriterleri (belge_onbellegi.belge_ara() ile aynı)
            - seri_numarasi
            - proje_adi
            - proje_konum
            - belge_kaynak
            - tarih_baslangic
            - tarih_bitis
            - limit
        
        Döndürür:
        ---------
        list[dict]
            Bulunan belgeler
        """
        return self.onbellek.belge_ara(**filtreler)
    
    def tab2_kayitlari_ara(
        self,
        **filtreler
    ) -> list[dict[str, Any]]:
        """
        Manuel belgeleri arar (sadece belge_kaynak='MANUEL').
        
        Parametreler:
        -------------
        **filtreler : dict
            Arama kriterleri
        
        Döndürür:
        ---------
        list[dict]
            Bulunan manuel belgeler
        """
        # MANUEL filtresi ekle
        filtreler['belge_kaynak'] = 'MANUEL'
        return self.onbellek.belge_ara(**filtreler)
    
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
            İstatistik bilgileri
        """
        return self.onbellek.istatistikler(logger)


# Test
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("=" * 60)
    print("VERİTABANI KAYDEDİCİ v3.0 - TEST")
    print("=" * 60)
    
    kaydedici = VeritabaniKaydedici()
    
    print("\n1. Manuel belge kaydetme testi...")
    basarili = kaydedici.tab2_kaydi_ekle({
        'belge_tarih_line': '2026-01-28',
        'belge_projeadi_line': 'Test Manuel Proje',
        'belge_projeyeri_line': 'İstanbul',
        'seri_numarasi': 'SN:280126-MANUEL-TEST-R00',
        'urun1_kod_line': 'LK',
        'urun1_adet_line': '5',
        'urun1_ozl_line': 'Test özellik',
        'urun2_kod_line': 'ZP30',
        'urun2_adet_line': '3',
        'toplamteklif_line': '850,00',
        'teklif_radio': True,
        'notlar_textEdit': 'Test manuel belge notları'
    })
    
    if basarili:
        print("✓ Manuel belge kaydedildi")
        
        print("\n2. Arama testi...")
        belgeler = kaydedici.kayit_ara(proje_adi='Manuel', limit=5)
        print(f"✓ {len(belgeler)} belge bulundu")
        
        print("\n3. Sadece manuel belgeler...")
        manuel_belgeler = kaydedici.tab2_kayitlari_ara(limit=5)
        print(f"✓ {len(manuel_belgeler)} manuel belge bulundu")
        
        print("\n4. İstatistikler...")
        stats = kaydedici.istatistikler()
        print(f"✓ Toplam belge: {stats['toplam_belge']}")
        print(f"✓ Manuel belge: {stats['manuel_belge']}")
        
        print("\n✅ TEST BAŞARILI!")
    else:
        print("❌ Test başarısız")
