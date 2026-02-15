#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analitik Repository — Cross-table istatistikler, trend, AI veri çıkarımı."""

from uygulama.altyapi.veritabani import Veritabani
from uygulama.ortak.yardimcilar import logger_olustur

logger = logger_olustur("analitik_repo")


class AnalitikRepository:
    def __init__(self, db: Veritabani):
        self.db = db

    # ═════════════════════════════════════════
    # GENEL İSTATİSTİKLER
    # ═════════════════════════════════════════

    def genel_ozet(self) -> dict:
        """Sistem geneli özet istatistikler."""
        p = self.db.getir_tek(
            "SELECT COUNT(*) as c FROM projeler WHERE silinme_tarihi IS NULL")
        b = self.db.getir_tek(
            "SELECT COUNT(*) as c FROM belgeler WHERE silinme_tarihi IS NULL")
        u = self.db.getir_tek(
            "SELECT COUNT(*) as c FROM urunler WHERE silinme_tarihi IS NULL")
        k = self.db.getir_tek(
            "SELECT COUNT(*) as c FROM kullanicilar WHERE silinme_tarihi IS NULL")
        l = self.db.getir_tek("SELECT COUNT(*) as c FROM hareket_loglari")
        return {
            "proje_sayisi": p["c"] if p else 0,
            "belge_sayisi": b["c"] if b else 0,
            "urun_sayisi": u["c"] if u else 0,
            "kullanici_sayisi": k["c"] if k else 0,
            "log_sayisi": l["c"] if l else 0,
        }

    # ═════════════════════════════════════════
    # TEKLİF KABUL ORANI ANALİZİ
    # ═════════════════════════════════════════

    def teklif_kabul_orani(self) -> dict:
        """Teklif belgelerinin kabul/red/bekleyen oranları."""
        rows = self.db.getir_hepsi(
            """SELECT durum, COUNT(*) as sayi FROM belgeler
               WHERE tur = 'TEKLİF' AND silinme_tarihi IS NULL
               GROUP BY durum""")
        sonuc = {"toplam": 0, "onaylanan": 0, "reddedilen": 0,
                 "bekleyen": 0, "kabul_orani": 0.0}
        for r in rows:
            sayi = r["sayi"]
            sonuc["toplam"] += sayi
            if r["durum"] == "APPROVED": sonuc["onaylanan"] = sayi
            elif r["durum"] == "REJECTED": sonuc["reddedilen"] = sayi
            else: sonuc["bekleyen"] += sayi
        if sonuc["toplam"] > 0:
            sonuc["kabul_orani"] = round(
                sonuc["onaylanan"] / sonuc["toplam"] * 100, 1)
        return sonuc

    def belge_tur_dagilimi(self) -> list[dict]:
        """Belge türlerine göre dağılım."""
        rows = self.db.getir_hepsi(
            """SELECT tur, durum, COUNT(*) as sayi FROM belgeler
               WHERE silinme_tarihi IS NULL
               GROUP BY tur, durum ORDER BY tur, durum""")
        return [dict(r) for r in rows]

    # ═════════════════════════════════════════
    # FİRMA ANALİZİ
    # ═════════════════════════════════════════

    def firma_bazli_analiz(self) -> list[dict]:
        """Firma bazlı proje sayıları ve toplam maliyet."""
        rows = self.db.getir_hepsi(
            """SELECT p.firma,
                      COUNT(DISTINCT p.id) as proje_sayisi,
                      COUNT(b.id) as belge_sayisi,
                      COALESCE(SUM(b.toplam_maliyet), 0) as toplam_maliyet,
                      SUM(CASE WHEN b.durum = 'APPROVED' THEN 1 ELSE 0 END) as onaylanan
               FROM projeler p
               LEFT JOIN belgeler b ON b.proje_id = p.id AND b.silinme_tarihi IS NULL
               WHERE p.silinme_tarihi IS NULL
               GROUP BY p.firma ORDER BY toplam_maliyet DESC""")
        return [dict(r) for r in rows]

    def konum_bazli_analiz(self) -> list[dict]:
        """Konum bazlı proje dağılımı."""
        rows = self.db.getir_hepsi(
            """SELECT p.konum,
                      COUNT(DISTINCT p.id) as proje_sayisi,
                      COALESCE(SUM(b.toplam_maliyet), 0) as toplam_maliyet
               FROM projeler p
               LEFT JOIN belgeler b ON b.proje_id = p.id AND b.silinme_tarihi IS NULL
               WHERE p.silinme_tarihi IS NULL
               GROUP BY p.konum ORDER BY proje_sayisi DESC""")
        return [dict(r) for r in rows]

    # ═════════════════════════════════════════
    # ÜRÜN ANALİZİ
    # ═════════════════════════════════════════

    def urun_populerlik(self) -> list[dict]:
        """Ürünlerin belgelerde kullanım sıklığı."""
        rows = self.db.getir_hepsi(
            """SELECT u.kod, u.ad,
                      COUNT(bu.id) as kullanim_sayisi,
                      COALESCE(SUM(bu.miktar), 0) as toplam_miktar
               FROM urunler u
               LEFT JOIN belge_urunleri bu ON bu.urun_id = u.id
                   AND bu.silinme_tarihi IS NULL
               WHERE u.silinme_tarihi IS NULL
               GROUP BY u.id ORDER BY kullanim_sayisi DESC""")
        return [dict(r) for r in rows]

    # ═════════════════════════════════════════
    # MALİYET TREND ANALİZİ
    # ═════════════════════════════════════════

    def aylik_maliyet_trendi(self) -> list[dict]:
        """Aylık toplam maliyet trendi."""
        rows = self.db.getir_hepsi(
            """SELECT strftime('%Y-%m', olusturma_tarihi) as ay,
                      COUNT(*) as belge_sayisi,
                      COALESCE(SUM(toplam_maliyet), 0) as toplam_maliyet,
                      COALESCE(AVG(toplam_maliyet), 0) as ortalama_maliyet
               FROM belgeler
               WHERE silinme_tarihi IS NULL AND toplam_maliyet > 0
               GROUP BY ay ORDER BY ay DESC LIMIT 24""")
        return [dict(r) for r in rows]

    def maliyet_dagilimi(self) -> dict:
        """Maliyet istatistikleri (min, max, ortalama, medyan)."""
        row = self.db.getir_tek(
            """SELECT MIN(toplam_maliyet) as min_m,
                      MAX(toplam_maliyet) as max_m,
                      AVG(toplam_maliyet) as ort_m,
                      COUNT(*) as sayi,
                      SUM(toplam_maliyet) as toplam
               FROM belgeler
               WHERE silinme_tarihi IS NULL AND toplam_maliyet > 0""")
        if not row or row["sayi"] == 0:
            return {"min": 0, "max": 0, "ortalama": 0, "toplam": 0, "sayi": 0}
        return {
            "min": round(row["min_m"] or 0, 2),
            "max": round(row["max_m"] or 0, 2),
            "ortalama": round(row["ort_m"] or 0, 2),
            "toplam": round(row["toplam"] or 0, 2),
            "sayi": row["sayi"],
        }

    # ═════════════════════════════════════════
    # REVİZYON ANALİZİ
    # ═════════════════════════════════════════

    def revizyon_istatistikleri(self) -> dict:
        """Revizyon sayısı analizi."""
        row = self.db.getir_tek(
            """SELECT AVG(revizyon_no) as ort,
                      MAX(revizyon_no) as max_r,
                      COUNT(*) as toplam
               FROM belgeler WHERE silinme_tarihi IS NULL""")
        return {
            "ortalama_revizyon": round(row["ort"] or 0, 1) if row else 0,
            "max_revizyon": row["max_r"] or 0 if row else 0,
            "toplam_belge": row["toplam"] or 0 if row else 0,
        }

    # ═════════════════════════════════════════
    # AI EĞİTİM VERİSİ ÇIKARIMI
    # ═════════════════════════════════════════

    def ai_egitim_verisi(self) -> list[dict]:
        """
        AI model eğitimi için yapılandırılmış veri.
        Her belge için: firma, konum, tesis, tür, durum, maliyet, revizyon,
        ürünler, alan değerleri.
        """
        rows = self.db.getir_hepsi(
            """SELECT b.id as belge_id, b.tur, b.durum, b.revizyon_no,
                      b.toplam_maliyet, b.kar_orani, b.kdv_orani,
                      b.olusturma_tarihi,
                      p.firma, p.konum, p.tesis, p.urun_seti
               FROM belgeler b
               JOIN projeler p ON p.id = b.proje_id
               WHERE b.silinme_tarihi IS NULL
               ORDER BY b.olusturma_tarihi""")
        sonuc = []
        for r in rows:
            kayit = dict(r)
            # Belge ürünlerini ekle
            urunler = self.db.getir_hepsi(
                """SELECT bu.miktar, bu.alan_verileri,
                          u.kod as urun_kodu, u.ad as urun_adi
                   FROM belge_urunleri bu
                   JOIN urunler u ON u.id = bu.urun_id
                   WHERE bu.belge_id = ? AND bu.silinme_tarihi IS NULL""",
                (r["belge_id"],))
            kayit["urunler"] = [dict(u) for u in urunler]
            # Belge alt kalemlerini ekle
            alt_kalemler = self.db.getir_hepsi(
                """SELECT bak.miktar, bak.birim_fiyat, bak.dahil,
                          ak.ad as alt_kalem_adi
                   FROM belge_alt_kalemleri bak
                   JOIN alt_kalemler ak ON ak.id = bak.alt_kalem_id
                   WHERE bak.belge_id = ? AND bak.silinme_tarihi IS NULL""",
                (r["belge_id"],))
            kayit["alt_kalemler"] = [dict(a) for a in alt_kalemler]
            sonuc.append(kayit)
        return sonuc

    def ai_firma_profili(self) -> list[dict]:
        """Firma bazlı AI profil verisi."""
        rows = self.db.getir_hepsi(
            """SELECT p.firma, p.konum,
                      COUNT(DISTINCT p.id) as proje_sayisi,
                      COUNT(b.id) as belge_sayisi,
                      SUM(CASE WHEN b.durum='APPROVED' THEN 1 ELSE 0 END) as onay,
                      SUM(CASE WHEN b.durum='REJECTED' THEN 1 ELSE 0 END) as red,
                      COALESCE(AVG(b.toplam_maliyet), 0) as ort_maliyet,
                      COALESCE(AVG(b.revizyon_no), 1) as ort_revizyon
               FROM projeler p
               LEFT JOIN belgeler b ON b.proje_id = p.id AND b.silinme_tarihi IS NULL
               WHERE p.silinme_tarihi IS NULL
               GROUP BY p.firma, p.konum""")
        return [dict(r) for r in rows]
