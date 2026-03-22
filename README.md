# FormOlusturma — Proje Yönetim Sistemi

**Versiyon:** v3.0.6
**Platform:** Windows 10+ (PyQt5)
**Lisans:** Proprietary — ZET Yapı © 2026

---

## 📋 İçindekiler

- [Hızlı Başlangıç](#hızlı-başlangıç)
- [Kurulum](#kurulum)
- [Varsayılan Giriş Bilgileri](#varsayılan-giriş-bilgileri)
- [Özellikler](#özellikler)
- [Google Drive Senkronizasyonu](#google-drive-senkronizasyonu)
- [Otomatik Güncelleme](#otomatik-güncelleme)
- [Sorun Giderme](#sorun-giderme)

---

## 🚀 Hızlı Başlangıç

```bash
# 1. Bağımlılıkları kur
pip install -r requirements.txt

# 2. Uygulamayı başlat
python main.py
```

İlk çalıştırmada veritabanı otomatik oluşturulur, migration'lar uygulanır ve admin kullanıcısı oluşturulur.

---

## 📦 Kurulum

### Sistem Gereksinimleri

| | |
|---|---|
| **Python** | 3.9+ |
| **İşletim Sistemi** | Windows 10+ |
| **RAM** | 512 MB boş RAM |
| **Disk** | 1 GB boş alan |

### Adım Adım

1. **Repository'yi klonla**
   ```bash
   git clone https://github.com/caferozpinar/FormOlusturma.git
   cd FormOlusturma
   ```

2. **Sanal ortam oluştur (önerilir)**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Bağımlılıkları yükle**
   ```bash
   pip install -r requirements.txt
   ```

4. **Uygulamayı başlat**
   ```bash
   python main.py
   ```

---

## 👤 Varsayılan Giriş Bilgileri

| Alan | Değer |
|------|-------|
| Kullanıcı | `admin` |
| Şifre | `admin123` |
| Rol | Admin |

> İlk girişten sonra şifreyi değiştir: ☰ menüsü → Şifre Değiştir

---

## ✨ Özellikler

### Proje Yönetimi
- Proje oluşturma, düzenleme, durum izleme
- Ürün seti atama ve proje bazlı ürün yönetimi
- Maliyet snapshot'ları

### Kullanıcı Yönetimi & RBAC
- Rol tabanlı erişim kontrolü (Admin / Editor / Viewer)
- Yetki bazlı buton/widget kontrolü
- Kullanıcı oluşturma, şifre değiştirme

### Ürün & Maliyet Motoru
- Ürün kataloğu (parametreler, alt kalemler, versiyonlar)
- 9 parametre tipi (Tam Sayı, Para, Ölçü, Yüzde, vb.)
- AST tabanlı güvenli formül parser
- Versiyon sistemi (pasif/aktif yönetimi)
- Maliyet şablonları ve kombinasyon hesaplama

### Teklif Sistemi
- Dinamik kalem ekleme/düzenleme
- Otomatik maliyet hesaplama
- Excel/DOCX dışa aktarma

### Belge Yönetimi
- Belge türleri (Teklif, Keşif, Tanım)
- Şablon atama, bölüm yönetimi
- Placeholder sistemi (5 kural tipi, 9 operatör)

### Analitik
- Proje ve teklif istatistikleri
- Grafik görselleştirmeler

### Google Drive Senkronizasyonu
- Tüm iş verisi tabloları çift yönlü merge (34 tablo)
- Çakışma çözümü (lokal / drive / atla)
- Şablon dosyaları sync
- Log dosyaları Drive'a yükleme
- Sync geçmişi ve per-row detay loglama

---

## ☁️ Google Drive Senkronizasyonu

### Kurulum

1. [Google Cloud Console](https://console.cloud.google.com)'da bir proje oluştur
2. Drive API'yi etkinleştir
3. OAuth 2.0 kimlik bilgilerini indir → `veri/credentials.json` olarak kaydet
4. Uygulamada: **Senkronizasyon** → **Google'a Bağlan**
5. Drive'da paylaşımlı bir klasör oluştur → **Klasör ID Ayarla**

### Nasıl Çalışır

- Sync sırasında lokal ve Drive veritabanları birleştirilir (union merge)
- Her tabloda: sadece lokalde olan → Drive'a eklenir; sadece Drive'da olan → lokale eklenir
- Aynı kayıt ikisinde de varsa: daha yeni zaman damgası kazanır
- Zaman bilgisi yoksa veya eşitse: çakışma dialogu açılır
- Sync sonucu **Sync Geçmişi** tablosunda saklanır; çift tıkla per-row detay görüntülenir

### Veri Güvenliği

- Sync sırasında Drive'da `.sync_lock` dosyası oluşturulur (eş zamanlı sync engellenir)
- Lock 30 dakika sonra otomatik sona erer
- Drive verisi, lokalde olmayan bir kayıt nedeniyle **asla silinmez** (sadece ekleme/güncelleme)

---

## 🔄 Otomatik Güncelleme

`installer.exe` uygulaması [GitHub Releases](https://github.com/caferozpinar/FormOlusturma/releases)'dan son sürümü kontrol eder.

- Güncelleme varsa ZIP indirir ve uygular
- Kullanıcı verileri (`Documents/ZET/FormOlusturma/`) güncelleme sırasında korunur

---

## 💾 Veritabanı

### Dosya Konumları

| Dosya | Konum |
|-------|-------|
| Uygulama DB | `veri/proje_yonetimi.db` |
| Drive Token | `veri/drive_token.json` |
| Drive Kimlik Bilgisi | `veri/credentials.json` |
| Log dosyaları | `loglar/YYYY-MM-DD.log` |

### Sıfırlama

> ⚠️ Tüm veriler silinir!

```bash
# Uygulamayı kapat, sonra:
del veri\proje_yonetimi.db
python main.py
```

---

## 🛠️ Sorun Giderme

### "database is locked" hatası

Birden fazla uygulama örneği açık kalmış olabilir.

```bash
taskkill /F /IM python.exe
# Ardından uygulamayı yeniden başlat
```

### Migration hatası

```
Error: no such table...
```

`veri/proje_yonetimi.db` dosyasını sil ve yeniden başlat. Migration'lar v1–v46 sırayla uygulanacak.

### Google Drive bağlantısı kurulamıyor

- `veri/credentials.json` dosyasının var olduğundan emin ol
- Drive API'nin Google Cloud Console'da etkinleştirildiğini kontrol et
- `veri/drive_token.json` dosyasını silerek yeniden yetkilendir

### Sync sonrası Drive verisi eksik görünüyor

v3.0.6 ile giderildi. Sürümün güncel olduğundan emin ol.

---

## 📝 Sürüm Geçmişi

| Sürüm | Tarih | Özet |
|-------|-------|------|
| **v3.0.6** | Mart 2026 | Drive sync veri silme hatası giderildi (SQLite thread fix), per-row sync loglama, sync geçmişi ekranı |
| v3.0.5 | Mart 2026 | GitHub API rate limit fix (installer), sync thread core dump fix, yetki butonu fix |
| v3.0.4 | Mart 2026 | QApplication instance fix |
| v3.0.2–3 | Şubat 2026 | Otomatik güncelleme penceresi, loglama iyileştirmeleri, RBAC yardımcı fonksiyonlar |
| v34 ve öncesi | Ocak–Şubat 2026 | Enterprise maliyet motoru, placeholder sistemi, teklif sistemi, Drive sync altyapısı |

---

## 📞 Destek

Bug raporları ve öneriler için: [Issues](https://github.com/caferozpinar/FormOlusturma/issues)
