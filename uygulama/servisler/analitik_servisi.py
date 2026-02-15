#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analitik Servisi — Analiz, rapor, AI veri hazırlığı ve export."""

import json
import os
from typing import Tuple, Optional

from uygulama.altyapi.analitik_repo import AnalitikRepository
from uygulama.ortak.yardimcilar import logger_olustur, simdi_iso

logger = logger_olustur("analitik_servisi")


class AnalitikServisi:
    def __init__(self, analitik_repo: AnalitikRepository):
        self.repo = analitik_repo

    # ═════════════════════════════════════════
    # DASHBOARD VERİLERİ
    # ═════════════════════════════════════════

    def dashboard_verileri(self) -> dict:
        """Tek çağrıda dashboard için tüm verileri toplar."""
        return {
            "ozet": self.repo.genel_ozet(),
            "teklif_orani": self.repo.teklif_kabul_orani(),
            "belge_dagilimi": self.repo.belge_tur_dagilimi(),
            "maliyet": self.repo.maliyet_dagilimi(),
            "revizyon": self.repo.revizyon_istatistikleri(),
        }

    # ═════════════════════════════════════════
    # ANALİZ RAPORLARI
    # ═════════════════════════════════════════

    def firma_raporu(self) -> list[dict]:
        """Firma bazlı detaylı analiz."""
        firmalar = self.repo.firma_bazli_analiz()
        for f in firmalar:
            belge = f.get("belge_sayisi", 0)
            onay = f.get("onaylanan", 0)
            f["kabul_orani"] = round(onay / belge * 100, 1) if belge > 0 else 0
        return firmalar

    def konum_raporu(self) -> list[dict]:
        return self.repo.konum_bazli_analiz()

    def urun_raporu(self) -> list[dict]:
        return self.repo.urun_populerlik()

    def maliyet_trend_raporu(self) -> list[dict]:
        return self.repo.aylik_maliyet_trendi()

    # ═════════════════════════════════════════
    # AI VERİ HAZIRLAMA
    # ═════════════════════════════════════════

    def ai_egitim_verisi_hazirla(self) -> dict:
        """AI eğitim seti: belgeler + firma profilleri."""
        belgeler = self.repo.ai_egitim_verisi()
        profiller = self.repo.ai_firma_profili()
        return {
            "meta": {
                "olusturma_tarihi": simdi_iso(),
                "belge_sayisi": len(belgeler),
                "firma_sayisi": len(profiller),
                "format_versiyonu": "1.0",
            },
            "belgeler": belgeler,
            "firma_profilleri": profiller,
        }

    def ai_verisi_export(self, dizin: str = "") -> Tuple[bool, str, Optional[str]]:
        """AI eğitim verisini JSON dosyasına yazar."""
        try:
            if not dizin:
                dizin = os.path.expanduser("~")

            veri = self.ai_egitim_verisi_hazirla()
            ts = simdi_iso().replace(":", "-")[:19]
            dosya = os.path.join(dizin, f"ai_egitim_verisi_{ts}.json")

            with open(dosya, "w", encoding="utf-8") as f:
                json.dump(veri, f, ensure_ascii=False, indent=2, default=str)

            logger.info(f"AI eğitim verisi export: {dosya} "
                        f"({veri['meta']['belge_sayisi']} belge)")
            return True, f"Export başarılı: {os.path.basename(dosya)}", dosya

        except Exception as e:
            logger.error(f"AI export hatası: {e}")
            return False, f"Export hatası: {e}", None

    def ai_verisi_csv_export(self, dizin: str = "") -> Tuple[bool, str, Optional[str]]:
        """AI eğitim verisini CSV dosyasına yazar (tabular format)."""
        try:
            if not dizin:
                dizin = os.path.expanduser("~")

            belgeler = self.repo.ai_egitim_verisi()
            ts = simdi_iso().replace(":", "-")[:19]
            dosya = os.path.join(dizin, f"ai_egitim_verisi_{ts}.csv")

            baslik = ("belge_id;tur;durum;revizyon;maliyet;kar_orani;kdv;"
                      "firma;konum;tesis;urun_sayisi;olusturma_tarihi")
            satirlar = [baslik]
            for b in belgeler:
                satirlar.append(
                    f"{b['belge_id']};{b['tur']};{b['durum']};"
                    f"{b['revizyon_no']};{b.get('toplam_maliyet',0)};"
                    f"{b.get('kar_orani',0)};{b.get('kdv_orani',0)};"
                    f"{b['firma']};{b['konum']};{b['tesis']};"
                    f"{len(b.get('urunler',[]))};{b['olusturma_tarihi']}")

            with open(dosya, "w", encoding="utf-8") as f:
                f.write("\n".join(satirlar))

            return True, f"CSV export: {os.path.basename(dosya)}", dosya

        except Exception as e:
            return False, f"CSV export hatası: {e}", None

    # ═════════════════════════════════════════
    # METIN RAPOR
    # ═════════════════════════════════════════

    def tam_rapor_metni(self) -> str:
        """İnsan okunabilir metin rapor."""
        d = self.dashboard_verileri()
        oz = d["ozet"]
        to = d["teklif_orani"]
        ml = d["maliyet"]
        rv = d["revizyon"]

        satir = []
        satir.append("═" * 50)
        satir.append("SİSTEM ANALİTİK RAPORU")
        satir.append(f"Tarih: {simdi_iso()[:10]}")
        satir.append("═" * 50)

        satir.append(f"\n▸ Genel Özet")
        satir.append(f"  Projeler: {oz['proje_sayisi']}")
        satir.append(f"  Belgeler: {oz['belge_sayisi']}")
        satir.append(f"  Ürünler:  {oz['urun_sayisi']}")
        satir.append(f"  Kullanıcılar: {oz['kullanici_sayisi']}")

        satir.append(f"\n▸ Teklif Kabul Analizi")
        satir.append(f"  Toplam: {to['toplam']}")
        satir.append(f"  Onaylanan: {to['onaylanan']} "
                     f"({to['kabul_orani']}%)")
        satir.append(f"  Reddedilen: {to['reddedilen']}")
        satir.append(f"  Bekleyen: {to['bekleyen']}")

        satir.append(f"\n▸ Maliyet İstatistikleri")
        satir.append(f"  Min:      ₺{ml['min']:,.2f}")
        satir.append(f"  Max:      ₺{ml['max']:,.2f}")
        satir.append(f"  Ortalama: ₺{ml['ortalama']:,.2f}")
        satir.append(f"  Toplam:   ₺{ml['toplam']:,.2f}")

        satir.append(f"\n▸ Revizyon")
        satir.append(f"  Ortalama revizyon: {rv['ortalama_revizyon']}")
        satir.append(f"  Maks revizyon:     {rv['max_revizyon']}")

        firmalar = self.firma_raporu()
        if firmalar:
            satir.append(f"\n▸ Firma Analizi (Top 5)")
            for f in firmalar[:5]:
                satir.append(
                    f"  {f['firma']}: {f['proje_sayisi']} proje, "
                    f"₺{f['toplam_maliyet']:,.0f}, "
                    f"kabul %{f['kabul_orani']}")

        satir.append("\n" + "═" * 50)
        return "\n".join(satir)
