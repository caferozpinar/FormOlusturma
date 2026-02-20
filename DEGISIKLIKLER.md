# FormOlusturma — Değişiklik Raporu

**Tarih:** 20 Şubat 2026  
**Kapsam:** Enterprise Ürün Yönetimi Arayüzü + Placeholder Sistemi  
**Migration:** v25 → v34 (10 yeni migration)

---

## 1. Enterprise Maliyet Motoru (Backend)

### Yeni Dosyalar

| Dosya | Satır | Açıklama |
|-------|-------|----------|
| `altyapi/enterprise_maliyet_repo.py` | 324 | Versiyonlu maliyet CRUD — 31 metod |
| `servisler/enterprise_maliyet_servisi.py` | 275 | Güvenli formül parser + hesaplama — 16 metod |

### Migration v25–v30: Maliyet Tabloları

| Versiyon | Tablo | Açıklama |
|----------|-------|----------|
| v25 | `parametre_tipler` | 9 tip kataloğu (int, float, string, dropdown, para, ölçü, boolean, tarih, yüzde) |
| v25 | `urun_versiyonlar` | Ürün versiyon geçmişi (aktif/pasif) |
| v26 | `urun_parametreler` | Ürün parametre tanımları (tip, zorunlu, varsayılan, sıra) |
| v26 | `parametre_dropdown_degerler` | Seçenek listesi değerleri |
| v27 | `alt_kalem_versiyonlar` | Alt kalem versiyon geçmişi |
| v27 | `alt_kalem_parametreler` | Alt kalem parametreleri (ürün param referansı destekli) |
| v28 | `maliyet_sablonlar` | Formül şablonları (formül ifadesi, kar oranı) |
| v28 | `maliyet_parametreler` | Formül değişkenleri (A, B, C kodları) |
| v29 | `konum_fiyatlar` | Konum bazlı sabit fiyatlar (7 şehir seed) |
| v30 | `proje_maliyet_snapshot` | İmmutable maliyet kaydı (6 index) |

### Güvenli Formül Parser

- AST tabanlı (Python `ast.parse` → güvenli eval)
- İzinli operatörler: `+`, `-`, `*`, `/`, `**`, `%`
- İzinli fonksiyonlar: `min`, `max`, `abs`, `round`, `ceil`, `floor`, `sqrt`
- Engellenen: `import`, `exec`, `eval`, `__builtins__`, `open`, `os.`, `sys.`
- Sıfıra bölme koruması
- Örnek: `A * B + C + KF` → `{A:50, B:2, C:200, KF:1500}` → `1800.0`

### Versiyon Sistemi

- Yeni versiyon oluşturulduğunda eski pasife alınır (tek aktif versiyon)
- Versiyon kopyalama: parametreler + alt kalem parametreleri + formül + değişkenler cascade kopyalanır
- Snapshot immutability: geçmiş kayıtlar asla değişmez

---

## 2. Admin Ürün Yönetim Arayüzü

### Yeni Dosya

| Dosya | Satır | Açıklama |
|-------|-------|----------|
| `arayuz/admin_urun_sayfa.py` | 967 | Enterprise ürün yönetim arayüzü — 8 sınıf |

### Kaldırılan Tab'lar (admin_sayfa.py)

- ❌ **Ürün Alanları** tab'ı kaldırıldı (enterprise parametreler ile değiştirildi)
- ❌ **Alt Kalemler** tab'ı kaldırıldı (ürün detay içine taşındı)
- ❌ `AlanEkleDialog` sınıfı kaldırıldı
- ❌ Eski ürün/alan/seçenek/alt kalem CRUD metodları kaldırıldı

### Yeni Stacked Layout (Modal Pencere Yok)

```
Seviye 1: UrunListeWidget
  ├── Ürün tablosu (Kod, Ad, Aktif, Versiyon, Tarih)
  ├── Yeni Ürün / Düzenle / Aktif-Pasif / Sil butonları
  └── Çift tıkla → Seviye 2

Seviye 2: UrunDetayWidget
  ├── Sol: Ürün Parametreleri tablosu + Parametre Ekle
  ├── Sağ: Alt Kalemler tablosu + Alt Kalem Ekle
  ├── Alt: VersiyonYoneticiComponent (versiyon geçmişi)
  ├── Yeni Versiyon Oluştur butonu
  └── Alt kalem çift tıkla → Seviye 3

Seviye 3: AltKalemDetayWidget
  ├── Alt Kalem Parametreleri tablosu
  ├── MaliyetFormulEditor (formül + değişken eşleşme)
  └── Yeni Alt Kalem Versiyonu butonu
```

### UI Bileşenleri

| Sınıf | Açıklama |
|-------|----------|
| `AdminUrunSayfasi` | QStackedWidget konteyner (3 seviye navigasyon) |
| `UrunListeWidget` | Ürün CRUD + tablo |
| `UrunDetayWidget` | Splitter: parametreler + alt kalemler |
| `AltKalemDetayWidget` | ScrollArea: parametreler + formül editör |
| `MaliyetFormulEditor` | Formül input, kar oranı, değişken eşleşme tablosu |
| `VersiyonYoneticiComponent` | Versiyon geçmişi tablosu |
| `DinamikParametreRenderer` | Tip → widget eşleşme (9 tip) |
| `ParametreEkleDialog` | Kullanıcı dostu parametre ekleme |

### Kullanıcı Dostu Parametre Tipleri (Migration v31)

| Eski (Teknik) | Yeni (Kullanıcı Görüntüsü) | Açıklama |
|----------------|------------------------------|----------|
| `int` | Tam Sayı (Adet) | Adet, kat sayısı gibi tam sayı |
| `float` | Ondalıklı Sayı | Ölçüm sonuçları, katsayılar |
| `string` | Metin | Serbest yazı alanı |
| `dropdown` | Seçenek Listesi | Önceden tanımlı seçeneklerden biri |
| `para` | Para (₺/€/$) | Para tutarı (birim: ₺) |
| `olcu_birimi` | Ölçü (m, m², m³, kg) | Uzunluk, alan, hacim (birim: m²) |
| `boolean` | Evet / Hayır | Açık/Kapalı, Var/Yok |
| `tarih` | Tarih | Gün/Ay/Yıl formatı |
| `yuzde` | Yüzde (%) | Yüzde oranı (birim: %) |

### Dropdown Seçenek Desteği (ParametreEkleDialog)

Tip olarak "Seçenek Listesi" seçildiğinde aynı dialog içinde seçenekler tanımlanır:

- Seçenek yazıp Enter veya "+ Ekle" ile ekleme
- Her seçeneğin yanında ✕ silme butonu
- Duplicate kontrol (aynı seçenek tekrar eklenemez)
- Minimum 2 seçenek validasyonu
- Seçenekler `parametre_dropdown_degerler` tablosuna sıralı kaydedilir

### Migration v32: FK Düzeltme

`parametre_dropdown_degerler` tablosundaki FK constraint kaldırıldı. Eski yapıda sadece `urun_parametreler` tablosuna FK vardı, alt kalem parametreleri için çalışmıyordu. Artık hem ürün hem alt kalem parametreleri dropdown seçenek kullanabilir.

---

## 3. Placeholder Sistemi

### Yeni Dosyalar

| Dosya | Satır | Açıklama |
|-------|-------|----------|
| `altyapi/placeholder_repo.py` | 161 | Placeholder + kural CRUD — 13 metod |
| `servisler/placeholder_servisi.py` | 244 | Kural motoru + çözümleme — 19 metod |
| `arayuz/placeholder_sayfa.py` | 374 | Admin UI — 3 sınıf |

### Migration v33–v34

| Versiyon | Tablo | Açıklama |
|----------|-------|----------|
| v33 | `placeholders` | Genel placeholder havuzu (kod UNIQUE) |
| v34 | `placeholder_kurallar` | Sıralı kurallar (tip, kaynak, operatör, koşul, sonuç) |

### Placeholder Yapısı

- Placeholder kodları `{/BASLIK/}` formatında (otomatik düzeltme)
- Tüm placeholder'lar genel havuzda, unique isimli
- İlgili parametre varsa otomatik eşleşir
- Başka placeholder'ı referans etmez (zincir yok)
- Form/belge şablonunda (PDF/DOCX çıktısı) kullanılacak

### 5 Kural Tipi

| Tip | Açıklama | Örnek |
|-----|----------|-------|
| **Doğrudan** | Parametre değerini aynen yaz | KAPAK TİPİ → "Çift Cidarlı" |
| **Eşitlik** | Parametre = değer → metin | KANAT = "Çelik" → "Çelik kanat sistemi" |
| **Karşılaştırma** | Sayısal koşul → metin | ÖLÇÜ > 300 → "Büyük kanat" |
| **Birleştirme** | Parametreleri concat | `{KANAT} x {MOTOR}` → "Çelik x Alüminyum" |
| **Şablon** | Serbest metin + parametre | `Kanat: {KANAT}, Ölçü: {ÖLÇÜ}mm` |

### 9 Operatör

`=`, `!=`, `>`, `<`, `>=`, `<=`, `içerir`, `ile başlar`, `ile biter`

### 3 Parametre Kaynağı

| Kaynak | Açıklama | Örnekler |
|--------|----------|----------|
| `urun_param` | Ürün parametreleri | KANAT MALZEMESİ, MOTOR MALZEMESİ |
| `alt_kalem_param` | Alt kalem parametreleri | İŞÇİLİK, MALZEME |
| `proje_bilgi` | Proje bilgileri | PROJE_ADI, PROJE_KONUM, PROJE_TESIS_TURU, PROJE_ULKE, PROJE_SEHIR, PROJE_TARIHI, PROJE_KODU |

### Kural Çözümleme Mantığı

1. Placeholder kodu ile eşleşen kayıt bulunur
2. Kurallar sıra numarasına göre değerlendirilir
3. İlk eşleşen kural sonucu döndürülür
4. Hiçbir kural tutmazsa "varsayılan" (fallback) kural çalışır
5. Hiç kural yoksa boş string döner

### Toplu Çözümleme (Form Çıktısı)

```python
# Şablon metin
sablon = """
Proje: {/BASLIK/}
Ürün: {/URUNTIPI/}
Detay: {/DETAY/}
"""

# Bağlam
baglamlar = {
    "urun_param": {"KANAT MALZEMESİ": "Çelik", "MOTOR MALZEMESİ": "Alüminyum"},
    "alt_kalem_param": {"İŞÇİLİK": "500"},
    "proje_bilgi": {"PROJE_ADI": "Acme Tower", "PROJE_KONUM": "İstanbul"},
}

# Çözümleme
sonuc = ph_srv.toplu_cozumle(sablon, baglamlar)
# → "Proje: Acme Tower — İstanbul / Fabrika\nÜrün: Çelik kanat sistemi\n..."
```

### Admin UI (Placeholder Tab)

```
┌─────────────────────────┬────────────────────────────────────┐
│  Placeholder Listesi    │  {/URUNTIPI/}                      │
│                         │  Ürün tipini belirler               │
│  {/BASLIK/}        [✕]  │                                    │
│  {/DETAY/}         [✕]  │  Kurallar (sıralı):                │
│  {/SERI/}          [✕]  │  1  Eşitlik  KANAT = Çelik  → ... │
│  {/URUNTIPI/}      [✕]  │  2  Eşitlik  KANAT = Alüm.  → ... │
│                         │  3  Eşitlik ★ (varsayılan)   → ... │
│  [+ Yeni Placeholder]   │                                    │
│                         │  [+ Kural Ekle]                     │
└─────────────────────────┴────────────────────────────────────┘
```

---

## 4. Genel UI İyileştirmeleri

### Tablo Buton Düzeltmesi

Tüm `QTableWidget` hücre içi butonlar taşıyordu (yükseklik sınırsızdı, satırı patlatıyordu).

**Çözüm:**
- `_tablo_ayarla()` — 9 tabloya satır yüksekliği 32px + verticalHeader gizleme
- `_tablo_butonu()` — tüm hücre butonlarına `setFixedSize(genişlik, 24)` + kompakt stil

---

## 5. Dosya Yapısı (Değişen/Yeni)

```
FormOlusturma/
├── main.py                              (güncellendi — placeholder entegrasyonu)
└── uygulama/
    ├── altyapi/
    │   ├── migration.py                 (v25-v34 eklendi)
    │   ├── enterprise_maliyet_repo.py   (YENİ — 324 satır)
    │   └── placeholder_repo.py          (YENİ — 161 satır)
    ├── servisler/
    │   ├── enterprise_maliyet_servisi.py (YENİ — 275 satır)
    │   └── placeholder_servisi.py       (YENİ — 244 satır)
    └── arayuz/
        ├── admin_sayfa.py               (güncellendi — tab temizliği)
        ├── admin_urun_sayfa.py          (YENİ — 967 satır)
        ├── placeholder_sayfa.py         (YENİ — 374 satır)
        └── ana_pencere.py               (güncellendi — yeni servis aktarımları)
```

### Toplam Yeni Kod: ~2,345 satır

| Katman | Satır |
|--------|-------|
| Altyapı (repo + migration) | ~585 |
| Servis | ~519 |
| Arayüz | ~1,341 |

---

## 6. Önemli Notlar

- **DB silme gerekli:** Yeni migration'lar (v25-v34) eski DB'ye uygulanamayabilir. `veri/proje_yonetimi.db` dosyasını silip yeniden başlatın.
- **Versiyon mantığı:** Parametre/formül değiştiğinde otomatik versiyon oluşmaz — admin "Yeni Versiyon" butonuna basmalı.
- **Snapshot immutability:** Proje maliyet snapshot'ları geçmişe dönük değişmez.
- **Placeholder unique:** Aynı kodda iki placeholder oluşturulamaz.
- **Form çıktısı:** Placeholder'lar henüz sadece backend'de çözümlenir, form şablon entegrasyonu gelecek aşamada yapılacak.
