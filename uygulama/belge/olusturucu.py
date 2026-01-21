"""
Belge Oluşturucu Modülü
=======================

Ana belge oluşturma fonksiyonu.

Bu modül, tüm şablonları birleştirerek
nihai teklif belgesini oluşturur.

YENİ: Geçici dosyaları otomatik temizleme özelliği eklendi.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from uygulama.sabitler import (
    SABLONLAR_DIZINI,
    GECICI_DIZINI,
    CIKTILAR_DIZINI,
    VERILER_DIZINI,
    VARSAYILAN_FORM_SONEKI,
    VARSAYILAN_YOLLAR,
)
from uygulama.belge.fiyat_tablosu import fiyat_tablosu_uret_ve_doldur
from uygulama.belge.log_yoneticisi import LogYoneticisi
from uygulama.belge.belge_veri_yoneticisi import BelgeVeriYoneticisi
from uygulama.belge.csv_kaydedici import CSVKaydedici
from uygulama.belge.sablon_islemleri import (
    gecici_dosyaya_render_et,
    belgeleri_birlestir,
    global_placeholder_uygula,
    gecici_dizini_temizle,  # YENİ: Temizlik fonksiyonu
    footer_seri_numarasi_yaz,  # YENİ: Seri numarası yazma
)
from uygulama.belge.yardimcilar import (
    config_deger_oku,
    urun_basliklarini_yukle,
    basliklari_turkce_birlestir,
    guvenli_dosya_adi_olustur,
    seri_numarasi_olustur,  # YENİ: Seri numarası oluşturma
    seri_dosya_adi_olustur,  # YENİ: Seri dosya adı oluşturma
    deterministik_hash_olustur,  # YENİ: Hash oluşturma
)

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

    def esleme_olustur(
        self,
        bolum: str,
        veri_kaynagi: dict[str, Any],
        dinamik_degerler: Optional[dict[str, str]] = None
    ) -> dict[str, str]:
        """Kurallardan placeholder eşleme oluşturur."""
        if bolum not in self.kurallar:
            if self.gunluk:
                self.gunluk.warning(f"UYARI: [{bolum}] bölümü kurallar içinde bulunamadı")
            return {}

        esleme = {}
        dinamik_degerler = dinamik_degerler or {}

        for placeholder, kural in self.kurallar[bolum].items():
            try:
                deger = self._kural_uygula(kural, veri_kaynagi, dinamik_degerler)
                if deger is not None:
                    esleme[placeholder] = str(deger)
            except Exception as e:
                if self.gunluk:
                    self.gunluk.warning(f"UYARI: Kural uygulanamadı '{placeholder}': {e}")

        return esleme

    def _kural_uygula(
        self,
        kural: str,
        veri_kaynagi: dict[str, Any],
        dinamik_degerler: dict[str, str]
    ) -> Optional[str]:
        """Tek bir eşleme kuralını uygular."""
        kural = kural.strip()

        # field: formatı
        if kural.startswith("field:"):
            alan_adi = kural[6:].strip()
            return veri_kaynagi.get(alan_adi, "")

        # dynamic: formatı
        if kural.startswith("dynamic:"):
            anahtar = kural[8:].strip()
            return dinamik_degerler.get(anahtar, "")

        # format: formatı
        if kural.startswith("format:"):
            return self._format_kural_uygula(kural, veri_kaynagi)

        return None

    def _format_kural_uygula(self, kural: str, veri_kaynagi: dict[str, Any]) -> str:
        """Format kuralını uygular."""
        import re
        esleme = re.match(r'format:"([^"]+)"\s+using\s+(.+)', kural)
        if not esleme:
            return ""

        sablon = esleme.group(1)
        parametreler_str = esleme.group(2)

        parametreler = {}
        for param in parametreler_str.split(","):
            param = param.strip()
            if ":" in param:
                degisken, alan = param.split(":", 1)
                parametreler[degisken.strip()] = veri_kaynagi.get(alan.strip(), "")

        try:
            return sablon.format(**parametreler)
        except KeyError:
            return sablon


def teklif_formu_olustur(
    veri_dizini: str | Path = "./kaynaklar",
    cikti_dizini: str | Path = "./ciktilar",
    urun_kodlari: list[str] = None,
    oturum_onbellegi: dict[str, dict] = None,
    standart_girdiler: dict[str, str] = None,
    form_soneki: str = VARSAYILAN_FORM_SONEKI,
    gecici_dizin: str | Path = "./gecici",
    sablonlar_altdizin: str = "sablonlar",
    baslik_sablon_adi: str = "STANDART_BASLIK.docx",
    sartlar_adi: str = "SARTLAR.docx",
    fiyat_dahil: bool = True,
    fiyat_adi: str = "FIYAT_TABLO.docx",
    kod_degeri: str = "EMPTY",
    config_yolu: str | Path = "./config.txt",
    gecici_temizle: bool = True,  # Geçici dosyaları temizleme seçeneği
    metadata_yaz: bool = True,  # YENİ: Metadata yazma seçeneği
    csv_kayit: bool = True,  # YENİ: CSV kayıt seçeneği
    csv_yolu: Optional[str | Path] = None  # YENİ: Özel CSV yolu
) -> Path:
    """
    Şablonları birleştirerek tam teklif formu belgesi oluşturur.

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
    form_soneki : str
        Form tipi son eki (varsayılan: "KEŞİF ÖZETİ")
    gecici_dizin : str | Path
        Geçici dosyalar dizini
    sablonlar_altdizin : str
        Şablonlar alt dizin adı
    baslik_sablon_adi : str
        Başlık şablon dosya adı
    sartlar_adi : str
        Şartlar ve koşullar şablon adı
    fiyat_dahil : bool
        Fiyat tablosunu dahil et (varsayılan: False)
    fiyat_adi : str
        Fiyat tablosu şablon adı
    kod_degeri : str
        Kodlama için değer
    config_yolu : str | Path
        Config dosyası yolu
    gecici_temizle : bool
        İşlem bitince geçici dosyaları temizle (varsayılan: True)
    metadata_yaz : bool
        Word belgesine metadata yaz (varsayılan: True)
    csv_kayit : bool
        CSV'ye kayıt ekle (varsayılan: True)
    csv_yolu : Optional[str | Path]
        Özel CSV yolu (None ise varsayılan kullanılır)

    Döndürür:
    ---------
    Path
        Oluşturulan belgenin yolu
    """
    # Log yöneticisi başlat
    log_yoneticisi = LogYoneticisi(
        log_dizini="./loglar",
        maksimum_log=5 * 1024 * 1024,   # istersen değiştir
        maksimum_yas_gun=7              # istersen değiştir
    )
    logger = log_yoneticisi.gunlukleyici

    try:
        logger.info("=" * 60)
        logger.info("TEKLİF FORMU OLUŞTURMA BAŞLATILDI")
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

        # YENİ: İşlem başında geçici dizini temizle
        if gecici_temizle:
            logger.info("Geçici dizin temizleniyor...")
            gecici_dizini_temizle(gecici_dizin, logger)

        # Config'den yolları yükle
        config_yolu = Path(config_yolu)
        kurallar_yolu = Path(config_deger_oku(config_yolu, "{{MAPPING_RULES}}") or str(VERILER_DIZINI / "mapping_rules.txt"))
        basliklar_yolu = Path(config_deger_oku(config_yolu, "{{URUN_BASLIKLARI}}") or str(VERILER_DIZINI / "urunbasliklari.txt"))

        logger.info(f"Veri dizini: {veri_dizini}")
        logger.info(f"Şablonlar dizini: {sablonlar_dizini}")
        logger.info(f"Çıktı dizini: {cikti_dizini}")

        # Şablonlar dizinini doğrula
        if not sablonlar_dizini.exists():
            hata = f"Şablonlar dizini bulunamadı: {sablonlar_dizini}"
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
                "{/TERMIN/}": standart_girdiler.get("TERMIN", ""),
                "{/MONTAJ/}": standart_girdiler.get("MONTAJ", ""),
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

        # Başlık metni oluştur
        logger.info("Başlık metni oluşturuluyor...")
        basliklar_map = urun_basliklarini_yukle(basliklar_yolu, logger)
        basliklar = [(basliklar_map.get(p) or p) for p in urun_kodlari]
        baslik_metni = f"{basliklari_turkce_birlestir(basliklar)} {form_soneki}".strip()
        fiyat_tablosu_baslik_metni = f"{basliklari_turkce_birlestir(basliklar)}".strip()
        logger.info(f"Başlık metni: '{baslik_metni}'")

        # Başlık şablonunu render et
        logger.info("=" * 60)
        logger.info("ADIM 1: BAŞLIK ŞABLONU RENDER EDİLİYOR")
        logger.info("=" * 60)
        baslik_sablon = sablonlar_dizini / baslik_sablon_adi
        baslik_esleme = global_esleme.copy()
        baslik_esleme["{/BASLIK/}"] = baslik_metni
        baslik_gecici = gecici_dosyaya_render_et(baslik_sablon, baslik_esleme, gecici_dizin, logger)
        logger.info(f"✓ Başlık render edildi: {baslik_gecici.name}")

        # Ürün TANIM ve TABLO dosyalarını render et
        logger.info("=" * 60)
        logger.info("ADIM 2: ÜRÜN ŞABLONLARI RENDER EDİLİYOR")
        logger.info("=" * 60)
        tanim_belgeler: list[Path] = []
        tablo_belgeler: list[Path] = []

        for i, urun in enumerate(urun_kodlari, 1):
            logger.info(f"Ürün işleniyor [{i}/{len(urun_kodlari)}]: {urun}")
            pm = urun_esleme_map.get(urun, {})

            tanim_kaynak = sablonlar_dizini / f"{urun}_TANIM.docx"
            tablo_kaynak = sablonlar_dizini / f"{urun}_TABLO.docx"

            if tanim_kaynak.exists():
                tanim_gecici = gecici_dosyaya_render_et(tanim_kaynak, pm, gecici_dizin, logger)
                tanim_belgeler.append(tanim_gecici)
                logger.info(f"  ✓ TANIM render edildi: {tanim_gecici.name}")
            else:
                logger.warning(f"  UYARI: TANIM şablonu bulunamadı: {tanim_kaynak.name}")

            if tablo_kaynak.exists():
                tablo_gecici = gecici_dosyaya_render_et(tablo_kaynak, pm, gecici_dizin, logger)
                tablo_belgeler.append(tablo_gecici)
                logger.info(f"  ✓ TABLO render edildi: {tablo_gecici.name}")
            else:
                logger.warning(f"  UYARI: TABLO şablonu bulunamadı: {tablo_kaynak.name}")

        # Ek listesi hazırla
        logger.info("=" * 60)
        logger.info("ADIM 3: BELGE BİRLEŞTİRME HAZIRLANIYOR")
        logger.info("=" * 60)
        ekler: list[Path] = []

        logger.info(f"{len(tanim_belgeler)} TANIM belgesi ekleniyor")
        ekler.extend(tanim_belgeler)

        logger.info(f"{len(tablo_belgeler)} TABLO belgesi ekleniyor")
        ekler.extend(tablo_belgeler)

        # Fiyat tablosu (opsiyonel)
        if fiyat_dahil:
            logger.info("-" * 60)
            logger.info("EK: FİYAT TABLOSU OLUŞTURULUYOR (SATIR SATIR)")
            logger.info("-" * 60)

            fiyat_tpl = config_deger_oku(config_yolu, "{{FIYAT_TEMPLATE}}")
            fiyat_sablon = Path(fiyat_tpl) if fiyat_tpl else (sablonlar_dizini / fiyat_adi)

            if not fiyat_sablon.exists():
                logger.warning(f"UYARI: Fiyat tablosu bulunamadı: {fiyat_sablon}")
            else:
                # Config'ten tablo parametreleri (hardcode yok)
                table_idx = int(config_deger_oku(config_yolu, "{{FIYAT_TABLE_IDX}}") or "0")
                template_row_idx = int(config_deger_oku(config_yolu, "{{FIYAT_TEMPLATE_ROW_IDX}}") or "1")
                total_anchor_row_idx = int(config_deger_oku(config_yolu, "{{FIYAT_TOTAL_ANCHOR_ROW_IDX}}") or "0")

                fiyat_gecici = gecici_dizin / f"FIYAT__{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"

                fiyat_tablosu_uret_ve_doldur(
                    fiyat_sablon_yolu=fiyat_sablon,
                    cikti_yolu=fiyat_gecici,
                    urun_kodlari=urun_kodlari,
                    oturum_onbellegi=oturum_onbellegi,
                    table_idx=table_idx,
                    template_row_idx=template_row_idx,
                    total_anchor_row_idx=total_anchor_row_idx,
                    logger=logger,
                    baslik_metni = fiyat_tablosu_baslik_metni,
                )

                ekler.append(fiyat_gecici)
                logger.info(f"✓ Fiyat tablosu oluşturuldu: {fiyat_gecici.name}")


        # Şartlar ve koşullar
        sartlar_yolu = sablonlar_dizini / sartlar_adi
        if sartlar_yolu.exists():
            ekler.append(sartlar_yolu)
            logger.info(f"Şartlar ekleniyor: {sartlar_adi}")
        else:
            logger.warning(f"UYARI: Şartlar dosyası bulunamadı: {sartlar_yolu}")

        logger.info(f"Toplam birleştirilecek: {len(ekler) + 1} belge (başlık + {len(ekler)} ek)")

        # Dosya adı oluştur
        logger.info("=" * 60)
        logger.info("ADIM 4: ÇIKTI DOSYA ADI OLUŞTURULUYOR")
        logger.info("=" * 60)

        # Tarih bilgisini al ve DDMMYY formatına çevir
        tarih_ham = standart_girdiler.get("TARIH") or standart_girdiler.get("CURDATE") or ""

        if tarih_ham:
            # Tarih formatını DDMMYY'ye çevir
            # Desteklenen formatlar: YYYY-MM-DD, DD/MM/YYYY, DD.MM.YYYY, DDMMYY
            tarih_temiz = tarih_ham.replace("/", "").replace("-", "").replace(".", "")

            if len(tarih_temiz) == 8:
                # YYYYMMDD veya DDMMYYYY formatı
                # Eğer ilk 4 karakter yıl gibi görünüyorsa (2000-2100 arası)
                if tarih_temiz[:4].isdigit() and 2000 <= int(tarih_temiz[:4]) <= 2100:
                    # YYYYMMDD formatı -> DDMMYY'ye çevir
                    yil = tarih_temiz[2:4]  # Son 2 rakam
                    ay = tarih_temiz[4:6]
                    gun = tarih_temiz[6:8]
                    tarih_ddmmyy = f"{gun}{ay}{yil}"
                else:
                    # DDMMYYYY formatı -> DDMMYY'ye çevir
                    tarih_ddmmyy = tarih_temiz[:4] + tarih_temiz[-2:]
            elif len(tarih_temiz) == 6:
                # Zaten DDMMYY formatında
                tarih_ddmmyy = tarih_temiz
            else:
                # Geçersiz format, bugünün tarihini kullan
                logger.warning(f"Geçersiz tarih formatı: {tarih_ham}, bugünün tarihi kullanılıyor")
                tarih_ddmmyy = datetime.now().strftime("%d%m%y")
        else:
            # Tarih yoksa bugünün tarihini kullan
            tarih_ddmmyy = datetime.now().strftime("%d%m%y")

        # Firma ve konum bilgilerini al
        firma_ham = standart_girdiler.get("PROJEADI") or standart_girdiler.get("DUZENLEYEN") or "FIRMA"
        konum_ham = standart_girdiler.get("PROJEKONUM") or "KONUM"

        # Revizyon bilgisi
        rev_ham = standart_girdiler.get("REVIZYON") or "R01"

        # Seri numarası oluştur
        logger.info("Seri numarası oluşturuluyor...")
        seri_numarasi = seri_numarasi_olustur(
            tarih=tarih_ddmmyy,
            firma=firma_ham,
            konum=konum_ham,
            urunler=urun_kodlari,
            revizyon=rev_ham
        )
        logger.info(f"Seri numarası: {seri_numarasi}")

        # Hash değerini çıkar (seri numarasından)
        # Format: SN:TARIH-FIRMA-KONUM-URUNLER-HASH-RVZ
        seri_parcalari = seri_numarasi.split("-")
        hash_degeri = seri_parcalari[-2] if len(seri_parcalari) >= 2 else "HASH"

        # Dosya adı oluştur: FIRMA-TARIH-HASH-RVZ
        dosya_adi = seri_dosya_adi_olustur(
            firma=firma_ham,
            tarih=tarih_ddmmyy,
            hash_degeri=hash_degeri,
            revizyon=rev_ham
        )
        logger.info(f"Dosya adı: {dosya_adi}.docx")

        # Belgeleri birleştir
        logger.info("=" * 60)
        logger.info("ADIM 5: BELGELER BİRLEŞTİRİLİYOR")
        logger.info("=" * 60)
        birlesmis_yol = gecici_dizin / f"{dosya_adi}__MERGED.docx"
        belgeleri_birlestir(baslik_gecici, ekler, birlesmis_yol, logger)
        logger.info(f"✓ Belgeler birleştirildi: {birlesmis_yol.name}")

        # Son global placeholder'ları uygula
        logger.info("=" * 60)
        logger.info("ADIM 6: SON GLOBAL PLACEHOLDER'LAR UYGULANIYOR")
        logger.info("=" * 60)
        cikti_yolu = cikti_dizini / f"{dosya_adi}.docx"
        cikti_dizini.mkdir(parents=True, exist_ok=True)
        global_placeholder_uygula(birlesmis_yol, global_esleme, cikti_yolu, logger)
        logger.info(f"✓ Son belge kaydedildi: {cikti_yolu}")

        # Footer'a seri numarası yaz
        logger.info("=" * 60)
        logger.info("ADIM 7: SERİ NUMARASI FOOTER'A YAZILIYOR")
        logger.info("=" * 60)
        footer_seri_numarasi_yaz(cikti_yolu, seri_numarasi, logger)
        logger.info(f"✓ Seri numarası eklendi: {seri_numarasi}")

        # YENİ: ZTF dosyasına veri kaydet (metadata yerine)
        if metadata_yaz:
            logger.info("=" * 60)
            logger.info("ADIM 8: BELGE VERİLERİ ZTF DOSYASINA KAYDEDILIYOR")
            logger.info("=" * 60)
            belge_veri_yoneticisi = BelgeVeriYoneticisi()
            ztf_basarili = belge_veri_yoneticisi.veri_kaydet(
                belge_yolu=cikti_yolu,
                standart_girdiler=standart_girdiler,
                oturum_onbellegi=oturum_onbellegi,
                urun_kodlari=urun_kodlari,
                seri_numarasi=seri_numarasi,
                dosya_adi=dosya_adi,
                logger=logger
            )
            if ztf_basarili:
                logger.info("✓ Belge verileri ZTF dosyasına kaydedildi")
            else:
                logger.warning("⚠ ZTF kaydetme başarısız")

        # YENİ: CSV kayıt ekle
        if csv_kayit:
            logger.info("=" * 60)
            logger.info("ADIM 9: CSV KAYDI EKLENİYOR")
            logger.info("=" * 60)
            
            # CSV yolu belirle
            if csv_yolu is None:
                csv_yolu = VARSAYILAN_YOLLAR.get("BELGE_KAYITLARI")
            
            csv_kaydedici = CSVKaydedici(csv_yolu)
            csv_basarili = csv_kaydedici.kayit_ekle(
                standart_girdiler=standart_girdiler,
                oturum_onbellegi=oturum_onbellegi,
                urun_kodlari=urun_kodlari,
                seri_numarasi=seri_numarasi,
                dosya_adi=dosya_adi,
                dosya_yolu=cikti_yolu,
                logger=logger
            )
            if csv_basarili:
                logger.info(f"✓ CSV kaydı eklendi: {csv_yolu}")
            else:
                logger.warning("⚠ CSV kayıt ekleme başarısız")

        # YENİ: İşlem bittikten sonra geçici dosyaları temizle
        if gecici_temizle:
            logger.info("=" * 60)
            logger.info("GEÇİCİ DOSYALAR TEMİZLENİYOR")
            logger.info("=" * 60)
            gecici_dizini_temizle(gecici_dizin, logger)

        # Başarı özeti
        logger.info("=" * 60)
        logger.info("TEKLİF FORMU OLUŞTURMA BAŞARIYLA TAMAMLANDI")
        logger.info("=" * 60)
        logger.info(f"Çıktı dosyası: {cikti_yolu}")
        logger.info(f"Dosya boyutu: {cikti_yolu.stat().st_size / 1024:.2f} KB")
        logger.info(f"Dahil edilen ürünler: {', '.join(urun_kodlari)}")
        logger.info(f"Seri numarası: {seri_numarasi}")
        logger.info(f"Kod: {kod_degeri}")
        logger.info("=" * 60)

        return cikti_yolu

    except ValueError as e:
        logger.error(f"HATA: Girdi doğrulama başarısız: {e}")
        logger.error("=" * 60)
        raise

    except FileNotFoundError as e:
        logger.error(f"HATA: Gerekli dosya bulunamadı: {e}")
        logger.error("=" * 60)
        raise

    except Exception as e:
        logger.error(f"HATA: Beklenmeyen hata: {e}")
        logger.error("=" * 60)
        log_yoneticisi.kritik_isaretle()
        raise


# =============================================================================
# Geriye Uyumluluk İçin Alias
# =============================================================================

# Eski: DocumentGenerator.build_offer_form(...)
# Yeni: olusturucu.teklif_formu_olustur(...)
build_offer_form = teklif_formu_olustur
