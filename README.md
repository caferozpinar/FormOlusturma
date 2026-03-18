# FormOlusturma — Proje Yönetim Sistemi

**Versiyon:** v34  
**Tarih:** 20 Şubat 2026  
**Platform:** Windows (PyQt5)

---

## 📋 İçindekiler

- [Hızlı Başlangıç](#hızlı-başlangıç)
- [Kurulum](#kurulum)
- [Başlama](#başlama)
- [Veritabanı Yönetimi](#veritabanı-yönetimi)
- [Varsayılan Giriş Bilgileri](#varsayılan-giriş-bilgileri)
- [Özellikler](#özellikler)
- [Sorun Giderme](#sorun-giderme)

---

## 🚀 Hızlı Başlangıç

```bash
# 1. Bağımlılıkları kur
pip install -r requirements.txt

# 2. Uygulamayı başlat
python main.py
```

**Not:** İlk çalıştırmada veritabanı otomatik oluşturulur ve migration'lar uygulanır.

---

## 📦 Kurulum

### Sistem Gereksinimleri

- **Python:** 3.9+
- **OS:** Windows 10+
- **RAM:** 4GB+ önerilir
- **Disk:** 1GB boş alan

### Adım Adım

1. **Repository'yi klonla**
   ```bash
   git clone <repo-url>
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

## 🔑 Başlama

### İlk Çalıştırma

1. Uygulamayı açtığında otomatik olarak:
   - Veritabanı oluşturulur (`veri/proje_yonetimi.db`)
   - v1–v44 migration'ları uygulanır
   - Admin kullanıcısı oluşturulur (yoksa)
   - Temel placeholder'lar seed'lenir

2. **Admin Paneline Gir**
   - Kullanıcı: `admin`
   - Şifre: `admin123`

### Şifre Değiştirme

Admin olarak giriş yaptıktan sonra:
1. ☰ menüsünü aç (sağ üst)
2. "Şifre Değiştir" seçene basın
3. Eski ve yeni şifreni gir

---

## 💾 Veritabanı Yönetimi

### Veritabanı Yolları

| Amaç | Yol |
|------|-----|
| Uygulama DB | `veri/proje_yonetimi.db` |
| Drive Token | `veri/drive_token.json` |
| Senkronizasyon | `veri/sync/` |

### Veritabanı Sıfırlama

⚠️ **Dikkat:** Bu tüm verileri siler!

```bash
# 1. Uygulamayı kapat
# 2. veri/proje_yonetimi.db dosyasını sil
del veri\proje_yonetimi.db

# 3. Uygulamayı yeniden başlat
python main.py
```

### Veritabanı Yedekleme

```bash
# Bash/PowerShell
copy veri\proje_yonetimi.db proje_yonetimi_backup_$(Get-Date -Format yyyyMMdd_HHmmss).db
```

---

## 👤 Varsayılan Giriş Bilgileri

| Alan | Değer |
|------|-------|
| Kullanıcı | `admin` |
| Şifre | `admin123` |
| Rol | Admin |

**Tavsiye:** İlk giriş yapıldıktan sonra şifreyi değiştir!

---

## ✨ Özellikler

### v25–v34 (En Son)

- **Enterprise Maliyet Motoru**
  - 9 parametre tipi (Tam Sayı, Para, Ölçü, vb.)
  - Güvenli formül parser (AST tabanlı)
  - Versiyon sistemi (ürün/alt kalem pasif-aktif)
  
- **Admin Ürün Yönetimi** *(Yeni ui)*
  - 3 seviye stacked layout (modal yok)
  - Ürün parametreleri + alt kalemler
  - Dropdown seçenek yönetimi
  
- **Placeholder Sistemi** *(Yeni)*
  - 5 kural tipi (Doğrudan, Eşitlik, Karşılaştırma, Birleştirme, Şablon)
  - 9 operatör (=, !=, >, <, >=, <=, içerir, ile başlar, ile biter)
  - 3 parametre kaynağı (Ürün, Alt Kalem, Proje)

- **Teklif Sistemi**
  - Dinamik kalem ekleme/düzenleme
  - Otomatik maliyet hesaplaması
  - PDF/DOCX dışa aktarma *(hazırlık*

### Önceki Sürümler

- Proje yönetimi (CRUD, durum izleme)
- Kullanıcı yönetimi (roller + izinler)
- Google Drive senkronizasyonu
- Belge yönetimi (ürün katalogları)
- Analitik ve raporlama
- Merge altyapısı (çevrimdışı düzenleme)

---

## 🛠️ Sorun Giderme

### "Veritabanı kilidi" hatası

```
Error: database is locked
```

**Çözüm:**
1. Uygulamayı kapat
2. Başka Python işlemini kapat (`taskkill /F /IM python.exe`)
3. Uygulamayı yeniden başlat

### "Migration başarısız" hatası

```
Error: no such table...
```

**Çözüm:**
1. `veri/proje_yonetimi.db` dosyasını sil
2. Uygulamayı yeniden başlat
3. Migration'lar yeniden uygulanacak

### Admin kullanıcısı giriş yapamıyor

```
Login failed: Kullanıcı bulunamadı
```

**Çözüm:**
1. `veri/proje_yonetimi.db` sil ve yeniden başlat (admin otomatik oluşturulacak)
2. Veya admin kullanıcı manuel olarak create et: `INSERT INTO kullanicilar (id, kullanici_adi, sifre_hash, rol) VALUES (uuid(), 'admin', hash('admin123'), 'Admin')`

### Çok yavaş başlıyor

- RAM'da yeterli yer var mı kontrol et
- Antivirus'u geçici olarak kapat
- `veri/` dizini SSD'de olduğundan emin ol

---

## 📞 Destek

Sorular veya bug raporları için [Issues](github.com/zenapi/FormOlusturma/issues) açın.

---

## 📝 Lisans

Proprietary — ZET Yapı © 2026
