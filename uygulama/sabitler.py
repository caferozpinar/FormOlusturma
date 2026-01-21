"""
Sabitler Modülü
===============

Uygulama genelinde kullanılan tüm sabit değerler.

Bu dosya merkezi bir yapılandırma noktası sağlar ve
gelecekte Ayarlar sayfası ile entegre edilebilir.
"""

from pathlib import Path

# =============================================================================
# Sürüm Bilgisi
# =============================================================================

UYGULAMA_ADI = "Form Oluşturma Uygulaması"
SURUM = "2.0.0"
GELISTIRICI = "Form Oluşturma Ekibi"

# =============================================================================
# Dizin Yolları
# =============================================================================

# Ana dizin (bu dosyanın iki üst klasörü)
KOK_DIZIN = Path(__file__).parent.parent

# Alt dizinler
UYGULAMA_DIZINI = KOK_DIZIN / "uygulama"
KAYNAKLAR_DIZINI = KOK_DIZIN / "kaynaklar"
CIKTILAR_DIZINI = KOK_DIZIN / "ciktilar"
GECICI_DIZINI = KOK_DIZIN / "gecici"
LOGLAR_DIZINI = KOK_DIZIN / "loglar"
TESTLER_DIZINI = KOK_DIZIN / "testler"
KAYITLAR_DIZINI = KOK_DIZIN / "kayitlar"  # Belge kayıtları CSV'si

# Kaynak alt dizinleri
UI_DIZINI = KAYNAKLAR_DIZINI / "ui"
SABLONLAR_DIZINI = KAYNAKLAR_DIZINI / "sablonlar"
VERILER_DIZINI = KAYNAKLAR_DIZINI / "veriler"
LOGO_DIZINI = KAYNAKLAR_DIZINI / "logo"

# =============================================================================
# Varsayılan Dosya Yolları
# =============================================================================

VARSAYILAN_YOLLAR = {
    # UI dosyaları
    "ANA_UI": UI_DIZINI / "FormOlusturmaApp.ui",

    # Şablon dosyaları
    "BASLIK_SABLONU": SABLONLAR_DIZINI / "STANDART_BASLIK.docx",
    "SARTLAR_SABLONU": SABLONLAR_DIZINI / "SARTLAR.docx",
    "FIYAT_SABLONU": SABLONLAR_DIZINI / "FIYAT_TABLO.docx",

    # Veri dosyaları
    "URUN_LISTESI": VERILER_DIZINI / "UrunListesi.csv",
    "ULKELER": VERILER_DIZINI / "Countries.csv",
    "URUN_BASLIKLARI": VERILER_DIZINI / "urunbasliklari.txt",
    "ESLEME_KURALLARI": VERILER_DIZINI / "mapping_rules.txt",
    
    # Kayıt dosyaları
    "BELGE_KAYITLARI": KAYITLAR_DIZINI / "belge_kayitlari.csv",

    # Yapılandırma
    "YAPILANDIRMA": KOK_DIZIN / "config.txt",
}

# =============================================================================
# Standart Girdi Varsayılanları
# =============================================================================

STANDART_GIRDI_VARSAYILAN = {
    "SONTRH": "",
    "TERMIN": "",
    "MONTAJ": "",
    "GIRDI1": "",
    "GIRDI2": "",
    "GIRDI3": "",
    "GIRDI4": "",
    "GIRDI5": "",
    "GIRDI6": "",
    "GIRDI7": "",
    "GIRDI8": "",
    "PROJEADI": "",
    "PROJEKONUM": "",
    "DUZENLEYEN": "",
    "CURDATE": "",
}

# =============================================================================
# UI Sabitleri
# =============================================================================

# ComboBox sayıları
URUN_COMBOBOX_SAYISI = 6

# Fiyat hesaplama satır sayısı
MAKSIMUM_FIYAT_SATIRI = 4

# Tarih sınırları
MINIMUM_YIL = 1900
MAKSIMUM_YIL = 2100

# =============================================================================
# Belge Sabitleri
# =============================================================================

# Varsayılan form son eki
VARSAYILAN_FORM_SONEKI = "FİYAT TEKLİFİ"

# Varsayılan revizyon
VARSAYILAN_REVIZYON = "R00"

# Ebat hesaplama kenar payı (cm)
VARSAYILAN_KENAR_PAYI = 20.0

# =============================================================================
# Loglama Sabitleri
# =============================================================================

# Log dosyası maksimum sayısı
MAKSIMUM_LOG_SAYISI = 50

# Log dosyası maksimum yaşı (gün)
MAKSIMUM_LOG_YASI_GUN = 30

# Log formatı
LOG_FORMATI = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_TARIH_FORMATI = "%Y-%m-%d %H:%M:%S"

# =============================================================================
# Dosya Uzantıları
# =============================================================================

UI_UZANTISI = ".ui"
BELGE_UZANTISI = ".docx"
CSV_UZANTISI = ".csv"
LOG_UZANTISI = ".log"

# =============================================================================
# Hata Mesajları
# =============================================================================

HATA_MESAJLARI = {
    "DOSYA_BULUNAMADI": "Dosya bulunamadı: {yol}",
    "GECERSIZ_TARIH": "Geçersiz tarih: {tarih}",
    "GECERSIZ_YIL": "Geçersiz yıl: {yil}. {min}-{max} arasında olmalı.",
    "GECERSIZ_AY": "Geçersiz ay: {ay}. 1-12 arasında olmalı.",
    "GECERSIZ_GUN": "Geçersiz gün: {gun}. 1-31 arasında olmalı.",
    "URUN_SECILMEDI": "Lütfen en az bir ürün seçin.",
    "SABLON_BULUNAMADI": "Şablon dosyası bulunamadı: {yol}",
    "CSV_BASLIK_YOK": "CSV dosyasında başlık bulunamadı: {yol}",
    "CSV_KOLON_YOK": "Gerekli kolon bulunamadı: {kolon}",
}

# =============================================================================
# Başarı Mesajları
# =============================================================================

BASARI_MESAJLARI = {
    "BELGE_OLUSTURULDU": "Belge başarıyla oluşturuldu!\n\nDosya: {dosya}\nKonum: {konum}",
    "FORM_KAYDEDILDI": "Form verileri kaydedildi.",
    "YAPILANDIRMA_GUNCELLENDI": "Yapılandırma güncellendi.",
}

# =============================================================================
# Türkçe Karakter Dönüşüm Tablosu
# =============================================================================

TURKCE_KARAKTER_DONUSUMU = str.maketrans(
    "çğıöşüÇĞİÖŞÜ",
    "cgiosuCGIOSU"
)

# =============================================================================
# Seri Numarası Sabitleri
# =============================================================================

# Seri numarası hash'i için kullanılacak karakter kümesi
# Sayılar (0-9) + Büyük harfler (A-Z) - J harfi - Türkçe karakterler
SERI_HASH_KARAKTER_KUMESI = "0123456789ABCDEFGHIKLMNOPQRSTUVWXYZ"

# Seri numarası hash uzunluğu
SERI_HASH_UZUNLUGU = 6

# Varsayılan revizyon
VARSAYILAN_SERI_REVIZYON = "R01"
