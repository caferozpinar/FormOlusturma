# 📋 Form Oluşturma Uygulaması

PyQt5 tabanlı profesyonel form ve belge oluşturma uygulaması.

## 🎯 Özellikler

- ✅ Çoklu ürün seçimi ve form oluşturma
- ✅ Dinamik alt form yükleme (.ui dosyalarından)
- ✅ Oturum önbelleği ile veri koruma
- ✅ Word belgesi (.docx) oluşturma
- ✅ Şablon tabanlı belge birleştirme
- 🔄 Çoklu sekme desteği (planlanan)
- 🔄 Ayarlar sayfası (planlanan)
- 🔄 Google Drive entegrasyonu (planlanan)
- 🔄 Kullanıcı rolleri (planlanan)

## 📁 Proje Yapısı

```
FormOlusturma/
├── main.py                 # Ana giriş noktası
├── uygulama/               # Ana uygulama paketi
│   ├── pencereler/         # UI pencereleri
│   ├── veri/               # Veri yönetimi
│   ├── yardimcilar/        # Yardımcı fonksiyonlar
│   ├── belge/              # Belge oluşturma
│   ├── kodlama/            # Kod üretimi
│   └── esleme/             # Placeholder eşleme
├── kaynaklar/              # Statik kaynaklar
│   ├── ui/                 # PyQt5 .ui dosyaları
│   ├── sablonlar/          # Word şablonları
│   ├── veriler/            # CSV ve yapılandırma dosyaları
│   └── logo/               # Logo görselleri
├── ciktilar/               # Oluşturulan belgeler
├── gecici/                 # Geçici dosyalar
├── loglar/                 # Log dosyaları
└── testler/                # Birim testleri
```

## 🚀 Kurulum

### Gereksinimler

- Python 3.10+
- PyQt5

### Adımlar

```bash
# 1. Depoyu klonla
git clone <repo-url>
cd FormOlusturma

# 2. Sanal ortam oluştur (önerilen)
python -m venv venv
source venv/bin/activate  # Linux/macOS
# veya
venv\Scripts\activate     # Windows

# 3. Bağımlılıkları kur
pip install -r requirements.txt

# 4. Uygulamayı çalıştır
python main.py
```

## 💻 Kullanım

### Temel Kullanım

1. Uygulamayı başlatın
2. Proje bilgilerini girin (ad, konum, tarih)
3. Ürün seçin ve detay butonuna tıklayın
4. Ürün formunu doldurun ve kaydedin
5. "Keşif Formu Oluştur" butonuna tıklayın
6. Belge `ciktilar/` klasöründe oluşturulur

### Yapılandırma

`config.txt` dosyasında yolları özelleştirebilirsiniz:

```txt
{{URUN_LISTESI}} = "./kaynaklar/veriler/UrunListesi.csv"
{{BASLIK_TEMPLATE}} = "./kaynaklar/sablonlar/STANDART_BASLIK.docx"
{{URUN_BASLIKLARI}} = "./kaynaklar/veriler/urunbasliklari.txt"
{{MAPPING_RULES}} = "./kaynaklar/veriler/mapping_rules.txt"
```

## 🧪 Test

```bash
# Tüm testleri çalıştır
pytest

# Belirli bir test dosyasını çalıştır
pytest testler/test_hesaplamalar.py

# Detaylı çıktı ile
pytest -v
```

## 📝 Geliştirme

### Kod Stili

```bash
# Kod formatlama
black uygulama/

# Kod kalite kontrolü
flake8 uygulama/

# Tip kontrolü
mypy uygulama/
```

### Yeni Ürün Ekleme

1. `kaynaklar/ui/` altına `URUN_KODU.ui` dosyası ekleyin
2. `kaynaklar/sablonlar/` altına şablonları ekleyin:
   - `URUN_KODU_TANIM.docx`
   - `URUN_KODU_TABLO.docx`
3. `kaynaklar/veriler/UrunListesi.csv` dosyasına ürünü ekleyin
4. `kaynaklar/veriler/urunbasliklari.txt` dosyasına başlık ekleyin
5. `kaynaklar/veriler/mapping_rules.txt` dosyasına eşleme kuralları ekleyin

## 📄 Lisans

[Lisans türünü belirtin]

## 👥 Katkıda Bulunanlar

- [Geliştirici Adı]

## 📞 İletişim

[İletişim bilgileri]
