#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analitik Sayfası — Dashboard, istatistikler, AI veri export."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableView, QTabWidget, QFrame, QMessageBox, QFileDialog,
    QScrollArea, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal

from uygulama.arayuz.ui_yardimcilar import SimpleTableModel, setup_table, make_stat_card


class AnalitikPage(QWidget):
    go_back = pyqtSignal()

    def __init__(self, analitik_servisi=None, parent=None):
        super().__init__(parent)
        self.analitik_servisi = analitik_servisi
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        t = QLabel("Analitik Dashboard"); t.setObjectName("title")
        bb = QPushButton("← Geri"); bb.clicked.connect(self.go_back.emit)
        header.addWidget(t); header.addStretch()

        b_rapor = QPushButton("📄 Rapor"); b_rapor.clicked.connect(self._rapor_goster)
        header.addWidget(b_rapor)
        b_json = QPushButton("🤖 AI Export (JSON)"); b_json.clicked.connect(self._ai_json_export)
        header.addWidget(b_json)
        b_csv = QPushButton("📊 AI Export (CSV)"); b_csv.clicked.connect(self._ai_csv_export)
        header.addWidget(b_csv)
        header.addWidget(bb)
        layout.addLayout(header)

        # Scroll area
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        content = QWidget()
        cl = QVBoxLayout(content); cl.setSpacing(16)

        # İstatistik kartları
        self.cards_grid = QGridLayout(); self.cards_grid.setSpacing(12)
        cl.addLayout(self.cards_grid)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_teklif_tab(), "Teklif Analizi")
        self.tabs.addTab(self._build_firma_tab(), "Firma Analizi")
        self.tabs.addTab(self._build_urun_tab(), "Ürün Popülerliği")
        self.tabs.addTab(self._build_maliyet_tab(), "Maliyet Trendi")
        self.tabs.addTab(self._build_konum_tab(), "Konum Analizi")
        cl.addWidget(self.tabs)

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _build_teklif_tab(self):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(12, 12, 12, 12)
        self.teklif_label = QLabel(""); l.addWidget(self.teklif_label)
        self.belge_table = QTableView(); setup_table(self.belge_table)
        self.belge_model = SimpleTableModel(["Tür", "Durum", "Sayı"])
        self.belge_table.setModel(self.belge_model); l.addWidget(self.belge_table)
        return w

    def _build_firma_tab(self):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(12, 12, 12, 12)
        self.firma_table = QTableView(); setup_table(self.firma_table)
        self.firma_model = SimpleTableModel(
            ["Firma", "Proje", "Belge", "Onaylanan", "Kabul %", "Toplam Maliyet"])
        self.firma_table.setModel(self.firma_model); l.addWidget(self.firma_table)
        return w

    def _build_urun_tab(self):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(12, 12, 12, 12)
        self.urun_table = QTableView(); setup_table(self.urun_table)
        self.urun_model = SimpleTableModel(["Kod", "Ürün Adı", "Kullanım", "Toplam Miktar"])
        self.urun_table.setModel(self.urun_model); l.addWidget(self.urun_table)
        return w

    def _build_maliyet_tab(self):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(12, 12, 12, 12)
        self.maliyet_stat_label = QLabel(""); l.addWidget(self.maliyet_stat_label)
        self.trend_table = QTableView(); setup_table(self.trend_table)
        self.trend_model = SimpleTableModel(["Ay", "Belge Sayısı", "Toplam Maliyet", "Ortalama"])
        self.trend_table.setModel(self.trend_model); l.addWidget(self.trend_table)
        return w

    def _build_konum_tab(self):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(12, 12, 12, 12)
        self.konum_table = QTableView(); setup_table(self.konum_table)
        self.konum_model = SimpleTableModel(["Konum", "Proje Sayısı", "Toplam Maliyet"])
        self.konum_table.setModel(self.konum_model); l.addWidget(self.konum_table)
        return w

    # ═════════════════════════════════════════
    # VERİ YÜKLEME
    # ═════════════════════════════════════════

    def sayfa_gosterildi(self):
        if not self.analitik_servisi:
            return
        self._kartlari_yukle()
        self._teklif_yukle()
        self._firma_yukle()
        self._urun_yukle()
        self._maliyet_yukle()
        self._konum_yukle()

    def _kartlari_yukle(self):
        d = self.analitik_servisi.dashboard_verileri()
        oz = d["ozet"]; to = d["teklif_orani"]; ml = d["maliyet"]

        # Mevcut kartları temizle
        while self.cards_grid.count():
            w = self.cards_grid.takeAt(0).widget()
            if w: w.deleteLater()

        kartlar = [
            ("Projeler", str(oz["proje_sayisi"]), "#3B82F6"),
            ("Belgeler", str(oz["belge_sayisi"]), "#8B5CF6"),
            ("Ürünler", str(oz["urun_sayisi"]), "#10B981"),
            ("Kabul Oranı", f"%{to['kabul_orani']}", "#F59E0B"),
            ("Toplam Maliyet", f"₺{ml['toplam']:,.0f}", "#EF4444"),
            ("Ort. Maliyet", f"₺{ml['ortalama']:,.0f}", "#6366F1"),
        ]
        for i, (baslik, deger, renk) in enumerate(kartlar):
            kart = make_stat_card(baslik, deger, renk)
            self.cards_grid.addWidget(kart, 0, i)

    def _teklif_yukle(self):
        to = self.analitik_servisi.repo.teklif_kabul_orani()
        self.teklif_label.setText(
            f"Toplam Teklif: {to['toplam']}  |  "
            f"Onaylanan: {to['onaylanan']}  |  "
            f"Reddedilen: {to['reddedilen']}  |  "
            f"Kabul Oranı: %{to['kabul_orani']}")

        dagilim = self.analitik_servisi.repo.belge_tur_dagilimi()
        self.belge_model.veri_guncelle(
            [[d["tur"], d["durum"], str(d["sayi"])] for d in dagilim])

    def _firma_yukle(self):
        firmalar = self.analitik_servisi.firma_raporu()
        self.firma_model.veri_guncelle([
            [f["firma"], str(f["proje_sayisi"]), str(f["belge_sayisi"]),
             str(f["onaylanan"]), f"%{f['kabul_orani']}",
             f"₺{f['toplam_maliyet']:,.0f}"]
            for f in firmalar])

    def _urun_yukle(self):
        urunler = self.analitik_servisi.urun_raporu()
        self.urun_model.veri_guncelle([
            [u["kod"], u["ad"], str(u["kullanim_sayisi"]),
             str(u["toplam_miktar"])]
            for u in urunler])

    def _maliyet_yukle(self):
        ml = self.analitik_servisi.repo.maliyet_dagilimi()
        self.maliyet_stat_label.setText(
            f"Min: ₺{ml['min']:,.2f}  |  Max: ₺{ml['max']:,.2f}  |  "
            f"Ort: ₺{ml['ortalama']:,.2f}  |  Toplam: ₺{ml['toplam']:,.2f}")

        trend = self.analitik_servisi.maliyet_trend_raporu()
        self.trend_model.veri_guncelle([
            [t["ay"], str(t["belge_sayisi"]),
             f"₺{t['toplam_maliyet']:,.0f}",
             f"₺{t['ortalama_maliyet']:,.0f}"]
            for t in trend])

    def _konum_yukle(self):
        konumlar = self.analitik_servisi.konum_raporu()
        self.konum_model.veri_guncelle([
            [k["konum"], str(k["proje_sayisi"]),
             f"₺{k['toplam_maliyet']:,.0f}"]
            for k in konumlar])

    # ═════════════════════════════════════════
    # EXPORT İŞLEMLERİ
    # ═════════════════════════════════════════

    def _ai_json_export(self):
        if not self.analitik_servisi: return
        dizin = QFileDialog.getExistingDirectory(self, "Export Dizini")
        if not dizin: return
        ok, msg, yol = self.analitik_servisi.ai_verisi_export(dizin)
        if ok:
            QMessageBox.information(self, "AI Export", msg)
        else:
            QMessageBox.warning(self, "Hata", msg)

    def _ai_csv_export(self):
        if not self.analitik_servisi: return
        dizin = QFileDialog.getExistingDirectory(self, "Export Dizini")
        if not dizin: return
        ok, msg, yol = self.analitik_servisi.ai_verisi_csv_export(dizin)
        if ok:
            QMessageBox.information(self, "AI Export", msg)
        else:
            QMessageBox.warning(self, "Hata", msg)

    def _rapor_goster(self):
        if not self.analitik_servisi: return
        rapor = self.analitik_servisi.tam_rapor_metni()
        QMessageBox.information(self, "Analitik Rapor", rapor)
