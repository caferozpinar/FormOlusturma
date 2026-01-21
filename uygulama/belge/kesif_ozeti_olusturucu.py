"""
Keşif Özeti Oluşturucu
======================

Keşif özeti belgesi oluşturma ana fonksiyonu.

Bu modül, şablon dosyasından başlayarak:
- Global placeholder'ları doldurur
- Ürüne özel placeholder'ları doldurur
- Opsiyon işaretleme ve numaralandırma uygular
- Nihai belgeyi kaydeder
"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from uygulama.sabitler import (
    SABLONLAR_DIZINI,
    GECICI_DIZINI,
    CIKTILAR_DIZINI,
    VERILER_DIZINI,
)
from uygulama.belge.log_yoneticisi import LogYoneticisi
from uygulama.belge.belge_veri_yoneticisi import BelgeVeriYoneticisi
from uygulama.belge.csv_kaydedici import CSVKaydedici
from uygulama.belge.sablon_islemleri import (
    global_placeholder_uygula,
    gecici_dizini_temizle,
)
from uygulama.belge.yardimcilar import (
    config_deger_oku,
    seri_numarasi_olustur,
    seri_dosya_adi_olustur,
    deterministik_hash_olustur,
)
from uygulama.belge.kesif_ozeti_isleyici import opsiyon_ve_numaralama_uygula

# Modül günlükleyicisi
gunluk = logging.getLogger(__name__)


class EslemeKurallarıAyrıştırıcı:
    """Eşleme kurallarını ayrıştırır ve uygular."""

    def __init__(self, kurallar_yolu: str | Path, gunluk_ref: Optional[logging.Logger] = None):
        self.kurallar_yolu = Path(kurallar_yolu)
        self.kurallar: dict[str, dict[str, str]] = {}
        self.gunluk = gunluk_ref
        self._kurallari_ayristir()

    def _kurallari_ayristir(self) -> None:
        """mapping_rules.txt dosyasını ayrıştırır."""
        if not self.kurallar_yolu.exists():
            if self.gunluk:
                self.gunluk.warning(f"UYARI: Eşleme kuralları dosyası bulunamadı: {self.kurallar_yolu}")
            return

        mevcut_bolum = None

        try:
            with self.kurallar_yolu.open("r", encoding="utf-8") as f:
                for satir_no, satir in enumerate(f, 1):
                    satir = satir.strip()

                    if not satir or satir.startswith("#"):
                        continue

                    # Bölüm başlığı
                    if satir.startswith("[") and satir.endswith("]"):
                        mevcut_bolum = satir[1:-1].strip()
                        self.kurallar[mevcut_bolum] = {}
                        continue

                    # Kural satırı
                    if "=" in satir and mevcut_bolum:
                        parcalar = satir.split("=", 1)
                        placeholder = parcalar[0].strip()
                        kural = parcalar[1].strip()
                        self.kurallar[mevcut_bolum][placeholder] = kural

            if self.gunluk:
                toplam = sum(len(k) for k in self.kurallar.values())
                self.gunluk.info(f"{len(self.kurallar)} bölüm, {toplam} kural yüklendi")

        except Exception as e:
            if self.gunluk:
                self.gunluk.error(f"HATA: Eşleme kuralları ayrıştırılamadı: {e}")
            raise ValueError(f"Eşleme kuralları ayrıştırılamadı: {e}")

    def esleme_olustur(self, bolum: str, veri_dict: dict[str, Any]) -> dict[str, str]:
        """Belirli bir bölüm için placeholder eşlemesi oluşturur."""
        if bolum not in self.kurallar:
            return {}

        esleme = {}
        for placeholder, kural in self.kurallar[bolum].items():
            deger = veri_dict.get(kural, "")
            esleme[placeholder] = str(deger) if deger is not None else ""

        return esleme


def kesif_ozeti_olustur(
    veri_dizini: str | Path = "./kaynaklar",
    cikti_dizini: str | Path = "./ciktilar",
    urun_kodlari: list[str] = None,
    oturum_onbellegi: dict[str, dict] = None,
    standart_girdiler: dict[str, str] = None,
    gecici_dizin: str | Path = "./gecici",
    sablonlar_altdizin: str = "sablonlar",
    kesif_sablon_adi: str = "KESIF_OZETI.docx",
    kod_degeri: str = "EMPTY",
    config_yolu: str | Path = "./config.txt",
    gecici_temizle: bool = True,
    metadata_yaz: bool = True,
    csv_kayit: bool = True,
    csv_yolu: Optional[str | Path] = None,
    opsiyon_renkleri: tuple[str, str] = ("FFF2CC", "D9E1F2"),
) -> Path:
    """
    Keşif özeti belgesi oluşturur.
    
    İşlem Adımları:
    1. Şablon dosyasını kopyalar
    2. Global placeholder'ları doldurur
    3. Ürüne özel placeholder'ları doldurur
    4. Opsiyon işaretleme ve numaralandırma uygular
    5. Metadata ve CSV kaydı yapar
    
    Parametreler:
    -------------
    veri_dizini : str | Path
        Veri dizini yolu
    cikti_dizini : str | Path
        Çıktı dizini yolu
    urun_kodlari : list[str]
        Dahil edilecek ürün kodları
    oturum_onbellegi : dict[str, dict]
        Ürüne özel form verileri
    standart_girdiler : dict[str, str]
        Standart girdiler
    gecici_dizin : str | Path
        Geçici dosyalar dizini
    sablonlar_altdizin : str
        Şablonlar alt dizin adı
    kesif_sablon_adi : str
        Keşif özeti şablon dosya adı
    kod_degeri : str
        Kodlama için değer
    config_yolu : str | Path
        Config dosyası yolu
    gecici_temizle : bool
        İşlem bitince geçici dosyaları temizle
    metadata_yaz : bool
        Word belgesine metadata yaz
    csv_kayit : bool
        CSV'ye kayıt ekle
    csv_yolu : Optional[str | Path]
        Özel CSV yolu (None ise varsayılan kullanılır)
    opsiyon_renkleri : tuple[str, str]
        Opsiyon renk çifti (hex, # olmadan)
    
    Returns:
        Path: Oluşturulan belgenin yolu
    """
    # Log yöneticisi başlat
    log_yoneticisi = LogYoneticisi(
        log_dizini="./loglar",
        maksimum_log=5 * 1024 * 1024,
        maksimum_yas_gun=7
    )
    logger = log_yoneticisi.gunlukleyici

    try:
        logger.info("=" * 60)
        logger.info("KEŞİF ÖZETİ OLUŞTURMA BAŞLATILDI")
        logger.info("=" * 60)

        # Varsayılan değerler
        urun_kodlari = urun_kodlari or []
        oturum_onbellegi = oturum_onbellegi or {}
        standart_girdiler = standart_girdiler or {}

        # Yolları hazırla
        veri_dizini = Path(veri_dizini)
        cikti_dizini = Path(cikti_dizini)
        gecici_dizin = Path(gecici_dizin)
        sablonlar_dizini = veri_dizini / sablonlar_altdizin

        # Geçici dizini temizle
        if gecici_temizle:
            logger.info("Geçici dizin temizleniyor...")
            gecici_dizini_temizle(gecici_dizin, logger)

        # Config'den yolları yükle
        config_yolu = Path(config_yolu)
        kurallar_yolu = Path(
            config_deger_oku(config_yolu, "{{MAPPING_RULES}}") or 
            str(VERILER_DIZINI / "mapping_rules.txt")
        )

        logger.info(f"Veri dizini: {veri_dizini}")
        logger.info(f"Şablonlar dizini: {sablonlar_dizini}")
        logger.info(f"Çıktı dizini: {cikti_dizini}")
        logger.info(f"Ürünler: {', '.join(urun_kodlari)}")

        # Şablon yolu kontrolü
        kesif_sablon = sablonlar_dizini / kesif_sablon_adi
        if not kesif_sablon.exists():
            hata = f"Keşif özeti şablonu bulunamadı: {kesif_sablon}"
            logger.error(f"HATA: {hata}")
            log_yoneticisi.kritik_isaretle()
            raise FileNotFoundError(hata)

        # Eşleme kurallarını yükle
        logger.info("Eşleme kuralları yükleniyor...")
        try:
            kural_ayristirici = EslemeKurallarıAyrıştırıcı(kurallar_yolu, logger)
        except Exception as e:
            logger.warning(f"UYARI: Eşleme kuralları yüklenemedi: {e}")
            kural_ayristirici = None

        # Global placeholder eşlemesi oluştur
        logger.info("Global placeholder eşlemesi oluşturuluyor...")
        if kural_ayristirici:
            global_esleme = kural_ayristirici.esleme_olustur("GLOBAL", standart_girdiler)
        else:
            global_esleme = {
                "{/DATE/}": standart_girdiler.get("CURDATE", ""),
                "{/PROJEADI/}": standart_girdiler.get("PROJEADI", ""),
                "{/PROJEYERI/}": standart_girdiler.get("PROJEKONUM", ""),
                "{/DUZENLEYENISIM/}": standart_girdiler.get("DUZENLEYEN", ""),
            }

        logger.info(f"Global eşleme: {len(global_esleme)} placeholder")

        # Ürüne özel placeholder eşlemeleri
        logger.info("Ürüne özel placeholder eşlemeleri oluşturuluyor...")
        urun_esleme_map: dict[str, dict[str, str]] = {}

        for urun in urun_kodlari:
            durum = oturum_onbellegi.get(urun, {})
            if kural_ayristirici:
                urun_esleme = kural_ayristirici.esleme_olustur("GLOBAL", standart_girdiler)
                urun_ozel = kural_ayristirici.esleme_olustur(urun, durum)
                urun_esleme.update(urun_ozel)
                urun_esleme_map[urun] = urun_esleme
            else:
                urun_esleme_map[urun] = global_esleme.copy()

            logger.info(f"  Ürün '{urun}': {len(urun_esleme_map[urun])} placeholder")

        # Tüm ürün eşlemelerini birleştir (sonradan eklenenler öncelikli)
        tam_esleme = global_esleme.copy()
        for urun_esleme in urun_esleme_map.values():
            tam_esleme.update(urun_esleme)

        # ADIM 1: Şablonu geçici dizine kopyala
        logger.info("=" * 60)
        logger.info("ADIM 1: ŞABLON KOPYALANIYOR")
        logger.info("=" * 60)
        
        gecici_dizin.mkdir(parents=True, exist_ok=True)
        gecici_belge = gecici_dizin / f"temp_kesif_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        shutil.copy2(kesif_sablon, gecici_belge)
        logger.info(f"✓ Şablon kopyalandı: {gecici_belge.name}")

        # ADIM 2: Global placeholder'ları uygula
        logger.info("=" * 60)
        logger.info("ADIM 2: PLACEHOLDER'LAR DOLDURULUYOR")
        logger.info("=" * 60)
        
        # Geçici bir çıktı dosyası oluştur
        gecici_cikti = gecici_dizin / f"temp_kesif_processed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        
        global_placeholder_uygula(
            giris_docx=gecici_belge,
            global_esleme=tam_esleme,
            cikti_docx=gecici_cikti,
            gunluk_ref=logger
        )
        logger.info("✓ Placeholder'lar dolduruldu")
        
        # İşlenmiş belgeyi kullan
        gecici_belge = gecici_cikti

        # ADIM 3: Opsiyon bayraklarını hazırla
        logger.info("=" * 60)
        logger.info("ADIM 3: OPSİYON BAYRAKLARI HAZIRLANIYOR")
        logger.info("=" * 60)
        
        opsiyon_alt_bayraklari: dict[str, bool] = {}
        
        for urun in urun_kodlari:
            durum = oturum_onbellegi.get(urun, {})
            # urun_ops_1 -> urun_ops_8 alanlarını kontrol et
            for i in range(1, 9):
                opsiyon_key = f"urun_ops_{i}"
                if opsiyon_key in durum:
                    alt_key = f"{urun.upper()}_{i}"
                    opsiyon_alt_bayraklari[alt_key] = bool(durum[opsiyon_key])
                    if durum[opsiyon_key]:
                        logger.info(f"  Opsiyon: {alt_key} = True")

        logger.info(f"✓ Toplam {sum(opsiyon_alt_bayraklari.values())} opsiyon işaretlendi")

        # ADIM 4: Opsiyon ve numaralandırma uygula
        logger.info("=" * 60)
        logger.info("ADIM 4: OPSİYON VE NUMARALAMA UYGULAMASI")
        logger.info("=" * 60)
        
        # Tarih formatını hazırla (DDMMYY)
        tarih = datetime.now().strftime("%d%m%y")
        
        # Nihai dosya adını oluştur
        seri_numarasi = seri_numarasi_olustur(
            tarih=tarih,
            firma=standart_girdiler.get("DUZENLEYEN", ""),
            konum=standart_girdiler.get("PROJEKONUM", ""),
            urunler=urun_kodlari,
            revizyon="R01"  # TODO: UI'dan al
        )
        
        # Seri numarasından hash çıkar: SN:TARIH-FIRMA-KONUM-URUNLER-HASH-RVZ
        # Örnek: SN:070126-DHB-TR-ISTANBUL-LK-ABC123-R01
        seri_parcalari = seri_numarasi.split("-")
        if len(seri_parcalari) >= 6:
            hash_degeri = seri_parcalari[-2]  # Sondan ikinci: hash
            firma_kisa = seri_parcalari[1]    # İkinci parça: firma
        else:
            # Fallback
            hash_degeri = deterministik_hash_olustur(str(urun_kodlari))
            firma_kisa = standart_girdiler.get("DUZENLEYEN", "UNKNOWN")[:10].upper()
        
        dosya_adi = seri_dosya_adi_olustur(
            firma=firma_kisa,
            tarih=tarih,
            hash_degeri=hash_degeri,
            revizyon="R01"
        )
        
        # KEŞİF ÖZETİ sonekini ekle
        dosya_adi = f"{dosya_adi}_KEŞİF ÖZETİ.docx"
        
        cikti_yolu = cikti_dizini / dosya_adi
        cikti_dizini.mkdir(parents=True, exist_ok=True)

        # Opsiyon işaretleme ve numaralandırma uygula
        opsiyon_ve_numaralama_uygula(
            belge_yolu=gecici_belge,
            cikti_yolu=cikti_yolu,
            tablo_index=0,
            opsiyon_alt_bayraklari=opsiyon_alt_bayraklari,
            opsiyon_urun_bayraklari={},  # İsteğe göre eklenebilir
            opsiyon_renkleri=opsiyon_renkleri,
            logger=logger
        )

        # ADIM 5: Metadata yaz (opsiyonel)
        if metadata_yaz:
            logger.info("=" * 60)
            logger.info("ADIM 5: METADATA YAZILIYOR")
            logger.info("=" * 60)
            
            try:
                yonetici = BelgeVeriYoneticisi(sikistir=True)
                
                # ZTF dosya adı
                ztf_dosya_adi = cikti_yolu.stem + ".ztf"
                ztf_yolu = cikti_dizini / ztf_dosya_adi
                
                # Metadata hazırla
                metadata = {
                    "kod": kod_degeri,
                    "seri_numarasi": seri_numarasi,
                    "olusturma_zamani": datetime.now().isoformat(),
                    "urun_kodlari": urun_kodlari,
                    "standart_girdiler": standart_girdiler,
                    "oturum_onbellegi": oturum_onbellegi,
                    "opsiyon_bayraklari": opsiyon_alt_bayraklari,
                }
                
                yonetici.veri_kaydet(
                    cikti_yolu=ztf_yolu,
                    veriler=metadata,
                    logger=logger
                )
                logger.info(f"✓ Metadata kaydedildi: {ztf_yolu.name}")
                
            except Exception as e:
                logger.warning(f"UYARI: Metadata yazılamadı: {e}")

        # ADIM 6: CSV kaydı (opsiyonel)
        if csv_kayit:
            logger.info("=" * 60)
            logger.info("ADIM 6: CSV KAYDI YAPILIYOR")
            logger.info("=" * 60)
            
            try:
                kaydedici = CSVKaydedici(csv_yolu=csv_yolu)
                kaydedici.kayit_ekle(
                    kod=kod_degeri,
                    seri_numarasi=seri_numarasi,
                    dosya_adi=dosya_adi,
                    urun_kodlari=urun_kodlari,
                    standart_girdiler=standart_girdiler,
                    oturum_onbellegi=oturum_onbellegi,
                    logger=logger
                )
                logger.info("✓ CSV kaydı eklendi")
                
            except Exception as e:
                logger.warning(f"UYARI: CSV kaydı yapılamadı: {e}")

        # Geçici dosyayı temizle
        if gecici_temizle:
            try:
                gecici_belge.unlink()
                logger.info("✓ Geçici dosya temizlendi")
            except Exception as e:
                logger.warning(f"UYARI: Geçici dosya silinemedi: {e}")

        logger.info("=" * 60)
        logger.info("✓ KEŞİF ÖZETİ BAŞARIYLA OLUŞTURULDU")
        logger.info(f"✓ Dosya: {cikti_yolu.name}")
        logger.info(f"✓ Konum: {cikti_yolu.parent}")
        logger.info("=" * 60)

        return cikti_yolu

    except Exception as e:
        logger.exception(f"HATA: Keşif özeti oluşturulamadı: {e}")
        log_yoneticisi.kritik_isaretle()
        raise
