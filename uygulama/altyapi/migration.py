#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Veritabanı Migration Sistemi.
Sıralı migration dosyaları ile şema versiyonlama.
"""

from uygulama.altyapi.veritabani import Veritabani
from uygulama.ortak.yardimcilar import logger_olustur

logger = logger_olustur("migration")

# ─────────────────────────────────────────────
# MİGRATION TANIMLARI
# ─────────────────────────────────────────────

MIGRATIONS: list[tuple[int, str, str]] = [
    # (versiyon, açıklama, sql)

    (1, "Şema sürüm tablosu", """
        CREATE TABLE IF NOT EXISTS schema_surumu (
            surum INTEGER PRIMARY KEY,
            aciklama TEXT NOT NULL,
            uygulama_tarihi TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """),

    (2, "Kullanıcılar tablosu", """
        CREATE TABLE IF NOT EXISTS kullanicilar (
            id TEXT PRIMARY KEY,
            kullanici_adi TEXT NOT NULL UNIQUE,
            sifre_hash TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'Editor',
            aktif INTEGER NOT NULL DEFAULT 1,
            olusturma_tarihi TEXT NOT NULL DEFAULT (datetime('now')),
            guncelleme_tarihi TEXT NOT NULL DEFAULT (datetime('now')),
            silinme_tarihi TEXT
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_kullanici_adi
            ON kullanicilar(kullanici_adi) WHERE silinme_tarihi IS NULL;
    """),

    (3, "Projeler tablosu", """
        CREATE TABLE IF NOT EXISTS projeler (
            id TEXT PRIMARY KEY,
            firma TEXT NOT NULL,
            konum TEXT NOT NULL,
            tesis TEXT NOT NULL,
            urun_seti TEXT NOT NULL DEFAULT '',
            hash_kodu TEXT NOT NULL UNIQUE,
            durum TEXT NOT NULL DEFAULT 'ACTIVE',
            olusturan_id TEXT NOT NULL,
            olusturma_tarihi TEXT NOT NULL DEFAULT (datetime('now')),
            guncelleme_tarihi TEXT NOT NULL DEFAULT (datetime('now')),
            silinme_tarihi TEXT,
            FOREIGN KEY (olusturan_id) REFERENCES kullanicilar(id)
        );
        CREATE INDEX IF NOT EXISTS idx_proje_durum
            ON projeler(durum) WHERE silinme_tarihi IS NULL;
        CREATE INDEX IF NOT EXISTS idx_proje_hash
            ON projeler(hash_kodu);
    """),

    (4, "Belgeler tablosu", """
        CREATE TABLE IF NOT EXISTS belgeler (
            id TEXT PRIMARY KEY,
            proje_id TEXT NOT NULL,
            tur TEXT NOT NULL,
            revizyon_no INTEGER NOT NULL DEFAULT 1,
            durum TEXT NOT NULL DEFAULT 'DRAFT',
            toplam_maliyet REAL NOT NULL DEFAULT 0.0,
            kar_orani REAL NOT NULL DEFAULT 0.0,
            kdv_orani REAL NOT NULL DEFAULT 20.0,
            olusturan_id TEXT NOT NULL,
            olusturma_tarihi TEXT NOT NULL DEFAULT (datetime('now')),
            guncelleme_tarihi TEXT NOT NULL DEFAULT (datetime('now')),
            silinme_tarihi TEXT,
            snapshot_veri TEXT,
            FOREIGN KEY (proje_id) REFERENCES projeler(id),
            FOREIGN KEY (olusturan_id) REFERENCES kullanicilar(id)
        );
        CREATE INDEX IF NOT EXISTS idx_belge_proje
            ON belgeler(proje_id) WHERE silinme_tarihi IS NULL;
    """),

    (5, "Ürünler tablosu", """
        CREATE TABLE IF NOT EXISTS urunler (
            id TEXT PRIMARY KEY,
            kod TEXT NOT NULL UNIQUE,
            ad TEXT NOT NULL,
            aktif INTEGER NOT NULL DEFAULT 1,
            olusturma_tarihi TEXT NOT NULL DEFAULT (datetime('now')),
            silinme_tarihi TEXT
        );
    """),

    (6, "Ürün alanları tablosu", """
        CREATE TABLE IF NOT EXISTS urun_alanlari (
            id TEXT PRIMARY KEY,
            urun_id TEXT NOT NULL,
            etiket TEXT NOT NULL,
            alan_anahtari TEXT NOT NULL,
            tip TEXT NOT NULL DEFAULT 'text',
            zorunlu INTEGER NOT NULL DEFAULT 0,
            sira INTEGER NOT NULL DEFAULT 0,
            min_deger REAL,
            max_deger REAL,
            hassasiyet INTEGER,
            silinme_tarihi TEXT,
            FOREIGN KEY (urun_id) REFERENCES urunler(id)
        );
        CREATE INDEX IF NOT EXISTS idx_urun_alan_urun
            ON urun_alanlari(urun_id) WHERE silinme_tarihi IS NULL;
    """),

    (7, "Ürün alan seçenekleri tablosu", """
        CREATE TABLE IF NOT EXISTS urun_alan_secenekleri (
            id TEXT PRIMARY KEY,
            alan_id TEXT NOT NULL,
            deger TEXT NOT NULL,
            sira INTEGER NOT NULL DEFAULT 0,
            silinme_tarihi TEXT,
            FOREIGN KEY (alan_id) REFERENCES urun_alanlari(id)
        );
    """),

    (8, "Alt kalemler tablosu", """
        CREATE TABLE IF NOT EXISTS alt_kalemler (
            id TEXT PRIMARY KEY,
            ad TEXT NOT NULL,
            aktif INTEGER NOT NULL DEFAULT 1,
            silinme_tarihi TEXT
        );
    """),

    (9, "Ürün alt kalemleri tablosu", """
        CREATE TABLE IF NOT EXISTS urun_alt_kalemleri (
            id TEXT PRIMARY KEY,
            urun_id TEXT NOT NULL,
            alt_kalem_id TEXT NOT NULL,
            varsayilan_birim_fiyat REAL NOT NULL DEFAULT 0.0,
            silinme_tarihi TEXT,
            FOREIGN KEY (urun_id) REFERENCES urunler(id),
            FOREIGN KEY (alt_kalem_id) REFERENCES alt_kalemler(id)
        );
    """),

    (10, "Belge ürünleri tablosu", """
        CREATE TABLE IF NOT EXISTS belge_urunleri (
            id TEXT PRIMARY KEY,
            belge_id TEXT NOT NULL,
            urun_id TEXT NOT NULL,
            miktar INTEGER NOT NULL DEFAULT 1,
            alan_verileri TEXT NOT NULL DEFAULT '{}',
            silinme_tarihi TEXT,
            FOREIGN KEY (belge_id) REFERENCES belgeler(id),
            FOREIGN KEY (urun_id) REFERENCES urunler(id)
        );
        CREATE INDEX IF NOT EXISTS idx_belge_urun_belge
            ON belge_urunleri(belge_id) WHERE silinme_tarihi IS NULL;
    """),

    (11, "Belge alt kalemleri tablosu", """
        CREATE TABLE IF NOT EXISTS belge_alt_kalemleri (
            id TEXT PRIMARY KEY,
            belge_id TEXT NOT NULL,
            belge_urun_id TEXT NOT NULL,
            alt_kalem_id TEXT NOT NULL,
            dahil INTEGER NOT NULL DEFAULT 1,
            miktar INTEGER NOT NULL DEFAULT 1,
            birim_fiyat REAL NOT NULL DEFAULT 0.0,
            silinme_tarihi TEXT,
            FOREIGN KEY (belge_id) REFERENCES belgeler(id),
            FOREIGN KEY (belge_urun_id) REFERENCES belge_urunleri(id),
            FOREIGN KEY (alt_kalem_id) REFERENCES alt_kalemler(id)
        );
    """),

    (12, "Hareket logları tablosu", """
        CREATE TABLE IF NOT EXISTS hareket_loglari (
            id TEXT PRIMARY KEY,
            kullanici_id TEXT NOT NULL,
            islem TEXT NOT NULL,
            hedef_tablo TEXT NOT NULL DEFAULT '',
            hedef_id TEXT NOT NULL DEFAULT '',
            detay TEXT NOT NULL DEFAULT '',
            tarih TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (kullanici_id) REFERENCES kullanicilar(id)
        );
        CREATE INDEX IF NOT EXISTS idx_log_tarih
            ON hareket_loglari(tarih DESC);
        CREATE INDEX IF NOT EXISTS idx_log_hedef
            ON hareket_loglari(hedef_tablo, hedef_id);
    """),

    # ─── MALİYET MOTORU V2 ───

    (13, "Parametre kombinasyonları tablosu", """
        CREATE TABLE IF NOT EXISTS alt_kalem_parametre_kombinasyonlari (
            id TEXT PRIMARY KEY,
            alt_kalem_id TEXT NOT NULL,
            kombinasyon_hash TEXT NOT NULL,
            parametre_json TEXT NOT NULL DEFAULT '{}',
            aktif_mi INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (alt_kalem_id) REFERENCES alt_kalemler(id)
        );
        CREATE INDEX IF NOT EXISTS idx_komb_alt_kalem
            ON alt_kalem_parametre_kombinasyonlari(alt_kalem_id, kombinasyon_hash)
            WHERE aktif_mi = 1;
    """),

    (14, "Maliyet versiyonlama tabloları", """
        CREATE TABLE IF NOT EXISTS alt_kalem_maliyet_versiyonlari (
            id TEXT PRIMARY KEY,
            kombinasyon_id TEXT NOT NULL,
            versiyon_no INTEGER NOT NULL DEFAULT 1,
            aktif_mi INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (kombinasyon_id)
                REFERENCES alt_kalem_parametre_kombinasyonlari(id)
        );
        CREATE INDEX IF NOT EXISTS idx_mv_komb
            ON alt_kalem_maliyet_versiyonlari(kombinasyon_id)
            WHERE aktif_mi = 1;

        CREATE TABLE IF NOT EXISTS alt_kalem_maliyet_girdi_degerleri (
            id TEXT PRIMARY KEY,
            versiyon_id TEXT NOT NULL,
            girdi_adi TEXT NOT NULL,
            deger TEXT NOT NULL DEFAULT '',
            FOREIGN KEY (versiyon_id)
                REFERENCES alt_kalem_maliyet_versiyonlari(id)
        );
        CREATE INDEX IF NOT EXISTS idx_mg_versiyon
            ON alt_kalem_maliyet_girdi_degerleri(versiyon_id);

        CREATE TABLE IF NOT EXISTS alt_kalem_maliyet_formulleri (
            id TEXT PRIMARY KEY,
            versiyon_id TEXT NOT NULL,
            alan_adi TEXT NOT NULL,
            formul TEXT NOT NULL DEFAULT '',
            FOREIGN KEY (versiyon_id)
                REFERENCES alt_kalem_maliyet_versiyonlari(id)
        );
        CREATE INDEX IF NOT EXISTS idx_mf_versiyon
            ON alt_kalem_maliyet_formulleri(versiyon_id);
    """),

    (15, "Konum maliyet çarpanları tablosu", """
        CREATE TABLE IF NOT EXISTS konum_maliyet_carpanlari (
            id TEXT PRIMARY KEY,
            konum TEXT NOT NULL,
            tasima_carpani REAL NOT NULL DEFAULT 1.0,
            iscilik_carpani REAL NOT NULL DEFAULT 1.0,
            yil INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_konum_yil
            ON konum_maliyet_carpanlari(konum, yil);
    """),

    (16, "Belge alt kalemine kar override ve kombinasyon referansı", """
        ALTER TABLE belge_alt_kalemleri ADD COLUMN kar_orani_override REAL;
        ALTER TABLE belge_alt_kalemleri ADD COLUMN kombinasyon_id TEXT;
        ALTER TABLE belge_alt_kalemleri ADD COLUMN versiyon_id TEXT;

        ALTER TABLE projeler ADD COLUMN kar_orani REAL NOT NULL DEFAULT 0.0;
    """),

    # ─── SYNC SİSTEMİ ───

    (17, "Sync metadata tablosu", """
        CREATE TABLE IF NOT EXISTS sync_metadata (
            id TEXT PRIMARY KEY,
            tur TEXT NOT NULL DEFAULT 'MANUAL',
            durum TEXT NOT NULL DEFAULT 'BASLATILDI',
            hedef TEXT NOT NULL DEFAULT '',
            detay TEXT NOT NULL DEFAULT '',
            sync_tarihi TEXT NOT NULL DEFAULT (datetime('now')),
            tamamlanma_tarihi TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_sync_tarih
            ON sync_metadata(sync_tarihi DESC);
    """),

    (18, "Sync conflict tablosu", """
        CREATE TABLE IF NOT EXISTS sync_conflicts (
            id TEXT PRIMARY KEY,
            sync_id TEXT NOT NULL,
            tablo TEXT NOT NULL,
            kayit_id TEXT NOT NULL,
            alan TEXT NOT NULL DEFAULT '',
            yerel_deger TEXT NOT NULL DEFAULT '',
            uzak_deger TEXT NOT NULL DEFAULT '',
            cozum TEXT NOT NULL DEFAULT 'BEKLIYOR',
            tarih TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (sync_id) REFERENCES sync_metadata(id)
        );
        CREATE INDEX IF NOT EXISTS idx_conflict_sync
            ON sync_conflicts(sync_id);
    """),

    # ─── LOOKUP TABLOLARI (DB-Tabanlı Refactor) ───

    (19, "Ülkeler tablosu", """
        CREATE TABLE IF NOT EXISTS ulkeler (
            id TEXT PRIMARY KEY,
            ad TEXT NOT NULL,
            aktif INTEGER NOT NULL DEFAULT 1,
            olusturma_tarihi TEXT NOT NULL DEFAULT (datetime('now')),
            silindi INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_ulkeler_ad ON ulkeler(ad);
    """),

    (20, "Şehirler tablosu", """
        CREATE TABLE IF NOT EXISTS sehirler (
            id TEXT PRIMARY KEY,
            ulke_id TEXT NOT NULL,
            ad TEXT NOT NULL,
            aktif INTEGER NOT NULL DEFAULT 1,
            olusturma_tarihi TEXT NOT NULL DEFAULT (datetime('now')),
            silindi INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (ulke_id) REFERENCES ulkeler(id)
        );
        CREATE INDEX IF NOT EXISTS idx_sehirler_ulke ON sehirler(ulke_id);
        CREATE INDEX IF NOT EXISTS idx_sehirler_ad ON sehirler(ad);
    """),

    (21, "Tesis türleri tablosu", """
        CREATE TABLE IF NOT EXISTS tesis_turleri (
            id TEXT PRIMARY KEY,
            ad TEXT NOT NULL,
            aktif INTEGER NOT NULL DEFAULT 1,
            olusturma_tarihi TEXT NOT NULL DEFAULT (datetime('now')),
            silindi INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_tesis_ad ON tesis_turleri(ad);
    """),

    (22, "Proje-ürün bağlantısı tablosu", """
        CREATE TABLE IF NOT EXISTS proje_urunleri (
            id TEXT PRIMARY KEY,
            proje_id TEXT NOT NULL,
            urun_id TEXT NOT NULL,
            urun_snapshot TEXT NOT NULL DEFAULT '{}',
            silinme_tarihi TEXT,
            FOREIGN KEY (proje_id) REFERENCES projeler(id),
            FOREIGN KEY (urun_id) REFERENCES urunler(id)
        );
        CREATE INDEX IF NOT EXISTS idx_proje_urun_proje
            ON proje_urunleri(proje_id) WHERE silinme_tarihi IS NULL;
    """),

    (23, "Seed data: Ülke, Şehir, Tesis Türleri", """
        INSERT OR IGNORE INTO ulkeler (id, ad) VALUES
            ('ulke-tr', 'Türkiye'),
            ('ulke-de', 'Almanya'),
            ('ulke-gb', 'İngiltere'),
            ('ulke-nl', 'Hollanda'),
            ('ulke-fr', 'Fransa');

        INSERT OR IGNORE INTO sehirler (id, ulke_id, ad) VALUES
            ('shr-ist', 'ulke-tr', 'İstanbul'),
            ('shr-ank', 'ulke-tr', 'Ankara'),
            ('shr-izm', 'ulke-tr', 'İzmir'),
            ('shr-brs', 'ulke-tr', 'Bursa'),
            ('shr-ant', 'ulke-tr', 'Antalya'),
            ('shr-kny', 'ulke-tr', 'Konya'),
            ('shr-adn', 'ulke-tr', 'Adana'),
            ('shr-ber', 'ulke-de', 'Berlin'),
            ('shr-mun', 'ulke-de', 'Münih'),
            ('shr-ham', 'ulke-de', 'Hamburg'),
            ('shr-lon', 'ulke-gb', 'Londra'),
            ('shr-man', 'ulke-gb', 'Manchester'),
            ('shr-ams', 'ulke-nl', 'Amsterdam'),
            ('shr-rot', 'ulke-nl', 'Rotterdam'),
            ('shr-par', 'ulke-fr', 'Paris'),
            ('shr-lyo', 'ulke-fr', 'Lyon');

        INSERT OR IGNORE INTO tesis_turleri (id, ad) VALUES
            ('tt-fabrika', 'Fabrika'),
            ('tt-depo', 'Depo'),
            ('tt-ofis', 'Ofis'),
            ('tt-magaza', 'Mağaza'),
            ('tt-hastane', 'Hastane'),
            ('tt-okul', 'Okul'),
            ('tt-otel', 'Otel'),
            ('tt-avm', 'AVM'),
            ('tt-rezidans', 'Rezidans'),
            ('tt-diger', 'Diğer');
    """),

    (24, "Proje-ürün tablosuna sıra kolonu ve unique constraint", """
        ALTER TABLE proje_urunleri ADD COLUMN sira INTEGER NOT NULL DEFAULT 0;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_proje_urun_unique
            ON proje_urunleri(proje_id, urun_id) WHERE silinme_tarihi IS NULL;
    """),

    # ─── ENTERPRISE VERSİYONLU MALİYET SİSTEMİ ───

    (25, "Parametre tip kataloğu ve ürün versiyonları", """
        CREATE TABLE IF NOT EXISTS parametre_tipler (
            id TEXT PRIMARY KEY,
            kod TEXT NOT NULL UNIQUE,
            python_tipi TEXT NOT NULL DEFAULT 'str',
            ui_bilesen TEXT NOT NULL DEFAULT 'text',
            json_schema TEXT NOT NULL DEFAULT '{}',
            olusturma_tarihi TEXT NOT NULL DEFAULT (datetime('now'))
        );
        INSERT OR IGNORE INTO parametre_tipler (id, kod, python_tipi, ui_bilesen) VALUES
            ('pt-int','int','int','spinbox'),
            ('pt-float','float','float','doublespinbox'),
            ('pt-str','string','str','text'),
            ('pt-dropdown','dropdown','str','combobox'),
            ('pt-para','para','float','doublespinbox'),
            ('pt-olcu','olcu_birimi','float','doublespinbox'),
            ('pt-bool','boolean','bool','checkbox'),
            ('pt-tarih','tarih','str','dateedit'),
            ('pt-yuzde','yuzde','float','doublespinbox');

        CREATE TABLE IF NOT EXISTS urun_versiyonlar (
            id TEXT PRIMARY KEY,
            urun_id TEXT NOT NULL,
            versiyon_no INTEGER NOT NULL DEFAULT 1,
            aktif_mi INTEGER NOT NULL DEFAULT 1,
            olusturma_tarihi TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (urun_id) REFERENCES urunler(id)
        );
        CREATE INDEX IF NOT EXISTS idx_urun_ver_urun ON urun_versiyonlar(urun_id);
        CREATE INDEX IF NOT EXISTS idx_urun_ver_aktif ON urun_versiyonlar(urun_id, aktif_mi);
    """),

    (26, "Ürün parametreleri ve dropdown değerleri", """
        CREATE TABLE IF NOT EXISTS urun_parametreler (
            id TEXT PRIMARY KEY,
            urun_versiyon_id TEXT NOT NULL,
            ad TEXT NOT NULL,
            tip_id TEXT NOT NULL,
            zorunlu INTEGER NOT NULL DEFAULT 0,
            varsayilan_deger TEXT NOT NULL DEFAULT '',
            aktif_mi INTEGER NOT NULL DEFAULT 1,
            sira INTEGER NOT NULL DEFAULT 0,
            olusturma_tarihi TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (urun_versiyon_id) REFERENCES urun_versiyonlar(id),
            FOREIGN KEY (tip_id) REFERENCES parametre_tipler(id)
        );
        CREATE INDEX IF NOT EXISTS idx_urun_param_ver ON urun_parametreler(urun_versiyon_id);

        CREATE TABLE IF NOT EXISTS parametre_dropdown_degerler (
            id TEXT PRIMARY KEY,
            parametre_id TEXT NOT NULL,
            deger TEXT NOT NULL,
            sira INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (parametre_id) REFERENCES urun_parametreler(id)
        );
    """),

    (27, "Alt kalem versiyonları ve parametreleri", """
        CREATE TABLE IF NOT EXISTS alt_kalem_versiyonlar (
            id TEXT PRIMARY KEY,
            alt_kalem_id TEXT NOT NULL,
            urun_versiyon_id TEXT NOT NULL,
            versiyon_no INTEGER NOT NULL DEFAULT 1,
            aktif_mi INTEGER NOT NULL DEFAULT 1,
            olusturma_tarihi TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (alt_kalem_id) REFERENCES alt_kalemler(id),
            FOREIGN KEY (urun_versiyon_id) REFERENCES urun_versiyonlar(id)
        );
        CREATE INDEX IF NOT EXISTS idx_akv_ak ON alt_kalem_versiyonlar(alt_kalem_id);
        CREATE INDEX IF NOT EXISTS idx_akv_uv ON alt_kalem_versiyonlar(urun_versiyon_id);

        CREATE TABLE IF NOT EXISTS alt_kalem_parametreler (
            id TEXT PRIMARY KEY,
            alt_kalem_versiyon_id TEXT NOT NULL,
            ad TEXT NOT NULL,
            tip_id TEXT NOT NULL,
            zorunlu INTEGER NOT NULL DEFAULT 0,
            varsayilan_deger TEXT NOT NULL DEFAULT '',
            aktif_mi INTEGER NOT NULL DEFAULT 1,
            urun_param_ref_id TEXT,
            sira INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (alt_kalem_versiyon_id) REFERENCES alt_kalem_versiyonlar(id),
            FOREIGN KEY (tip_id) REFERENCES parametre_tipler(id),
            FOREIGN KEY (urun_param_ref_id) REFERENCES urun_parametreler(id)
        );
        CREATE INDEX IF NOT EXISTS idx_akp_ver ON alt_kalem_parametreler(alt_kalem_versiyon_id);
    """),

    (28, "Maliyet şablonları ve formül parametreleri", """
        CREATE TABLE IF NOT EXISTS maliyet_sablonlar (
            id TEXT PRIMARY KEY,
            alt_kalem_versiyon_id TEXT NOT NULL,
            formul_ifadesi TEXT NOT NULL DEFAULT '0',
            varsayilan_formul_mu INTEGER NOT NULL DEFAULT 1,
            aktif_mi INTEGER NOT NULL DEFAULT 1,
            kar_orani REAL NOT NULL DEFAULT 0,
            olusturma_tarihi TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (alt_kalem_versiyon_id) REFERENCES alt_kalem_versiyonlar(id)
        );
        CREATE INDEX IF NOT EXISTS idx_ms_akv ON maliyet_sablonlar(alt_kalem_versiyon_id);

        CREATE TABLE IF NOT EXISTS maliyet_parametreler (
            id TEXT PRIMARY KEY,
            maliyet_sablon_id TEXT NOT NULL,
            ad TEXT NOT NULL,
            degisken_kodu TEXT NOT NULL,
            varsayilan_deger REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (maliyet_sablon_id) REFERENCES maliyet_sablonlar(id)
        );
        CREATE INDEX IF NOT EXISTS idx_mp_sablon ON maliyet_parametreler(maliyet_sablon_id);
    """),

    (29, "Konum fiyat tablosu", """
        CREATE TABLE IF NOT EXISTS konum_fiyatlar (
            id TEXT PRIMARY KEY,
            ulke TEXT NOT NULL,
            sehir TEXT NOT NULL,
            fiyat REAL NOT NULL DEFAULT 0,
            olusturma_tarihi TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_kf_sehir ON konum_fiyatlar(ulke, sehir);

        INSERT OR IGNORE INTO konum_fiyatlar (id, ulke, sehir, fiyat) VALUES
            ('kf-ist','Türkiye','İstanbul',1500),
            ('kf-ank','Türkiye','Ankara',1200),
            ('kf-izm','Türkiye','İzmir',1300),
            ('kf-brs','Türkiye','Bursa',1100),
            ('kf-ber','Almanya','Berlin',3500),
            ('kf-mun','Almanya','Münih',3800),
            ('kf-lon','İngiltere','Londra',4200);
    """),

    (30, "Proje maliyet snapshot tablosu", """
        CREATE TABLE IF NOT EXISTS proje_maliyet_snapshot (
            id TEXT PRIMARY KEY,
            proje_id TEXT NOT NULL,
            belge_id TEXT,
            revizyon_no INTEGER NOT NULL DEFAULT 1,
            urun_id TEXT NOT NULL,
            urun_versiyon_id TEXT NOT NULL,
            alt_kalem_id TEXT NOT NULL,
            alt_kalem_versiyon_id TEXT NOT NULL,
            parametre_degerleri TEXT NOT NULL DEFAULT '{}',
            formul_ifadesi TEXT NOT NULL DEFAULT '0',
            birim_fiyat REAL NOT NULL DEFAULT 0,
            miktar INTEGER NOT NULL DEFAULT 1,
            toplam_fiyat REAL NOT NULL DEFAULT 0,
            kar_orani REAL NOT NULL DEFAULT 0,
            konum_fiyat REAL NOT NULL DEFAULT 0,
            opsiyon_mu INTEGER NOT NULL DEFAULT 0,
            olusturma_yili INTEGER NOT NULL DEFAULT 2026,
            olusturma_tarihi TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (proje_id) REFERENCES projeler(id)
        );
        CREATE INDEX IF NOT EXISTS idx_pms_proje ON proje_maliyet_snapshot(proje_id);
        CREATE INDEX IF NOT EXISTS idx_pms_urun ON proje_maliyet_snapshot(urun_id);
        CREATE INDEX IF NOT EXISTS idx_pms_ak ON proje_maliyet_snapshot(alt_kalem_id);
        CREATE INDEX IF NOT EXISTS idx_pms_yil ON proje_maliyet_snapshot(olusturma_yili);
        CREATE INDEX IF NOT EXISTS idx_pms_opsiyon ON proje_maliyet_snapshot(opsiyon_mu);
        CREATE INDEX IF NOT EXISTS idx_pms_rev ON proje_maliyet_snapshot(proje_id, revizyon_no);
    """),
]


# ─────────────────────────────────────────────
# MİGRATION MOTORU
# ─────────────────────────────────────────────

class MigrationMotoru:
    """Veritabanı migration yöneticisi."""

    def __init__(self, db: Veritabani):
        self.db = db

    def mevcut_surum(self) -> int:
        """Veritabanının mevcut şema sürümünü döndürür."""
        try:
            row = self.db.getir_tek(
                "SELECT MAX(surum) as son FROM schema_surumu"
            )
            return row["son"] if row and row["son"] else 0
        except Exception:
            return 0

    def uygula(self) -> int:
        """
        Bekleyen tüm migration'ları uygular.
        Kaç migration uygulandığını döndürür.
        """
        mevcut = self.mevcut_surum()
        uygulanan = 0

        for surum, aciklama, sql in MIGRATIONS:
            if surum <= mevcut:
                continue

            logger.info(f"Migration v{surum} uygulanıyor: {aciklama}")

            with self.db.transaction() as conn:
                # Çoklu SQL ifadelerini ayrı ayrı çalıştır
                for ifade in sql.strip().split(";"):
                    ifade = ifade.strip()
                    if ifade:
                        conn.execute(ifade)

                # Sürümü kaydet (v1 kendi tablosunu oluşturduğu için
                # ilk migration'dan sonra tabloya yazabiliriz)
                if surum >= 1:
                    conn.execute(
                        "INSERT INTO schema_surumu (surum, aciklama) VALUES (?, ?)",
                        (surum, aciklama)
                    )

            uygulanan += 1
            logger.info(f"Migration v{surum} tamamlandı.")

        if uygulanan == 0:
            logger.info("Tüm migration'lar güncel.")
        else:
            logger.info(f"Toplam {uygulanan} migration uygulandı. "
                        f"Mevcut sürüm: v{self.mevcut_surum()}")

        return uygulanan
