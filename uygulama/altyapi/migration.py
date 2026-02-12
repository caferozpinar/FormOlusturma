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
