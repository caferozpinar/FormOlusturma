#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Proje Dialog — 2 panelli ürün seçim, DB-tabanlı lookup, sıralama."""

import json
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QSplitter,
    QLabel, QLineEdit, QPushButton, QComboBox, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QListWidget, QListWidgetItem, QMessageBox, QGroupBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor

from uygulama.domain.modeller import Proje


class ProjeDialog(QDialog):
    """Proje oluşturma/düzenleme — 2 panelli ürün seçim sistemi."""

    def __init__(self, proje_servisi, konum_servisi=None,
                 tesis_servisi=None, urun_servisi=None,
                 proje: Proje = None, parent=None):
        super().__init__(parent)
        self.proje_servisi = proje_servisi
        self.konum_servisi = konum_servisi
        self.tesis_servisi = tesis_servisi
        self.urun_servisi = urun_servisi
        self.mevcut_proje = proje
        self.sonuc_proje = None
        self._eklenen_urunler = []  # [{"urun_id", "kod", "ad"}, ...]

        duzenleme = proje is not None
        self.setWindowTitle("Proje Düzenle" if duzenleme else "Yeni Proje")
        self.setMinimumWidth(750)
        self.setMinimumHeight(580)
        self.setModal(True)
        self._build(duzenleme)
        self._verileri_yukle(duzenleme)

    def _build(self, duzenleme: bool):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        title = QLabel("Proje Düzenle" if duzenleme else "Yeni Proje Oluştur")
        title.setObjectName("sectionTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # ── FORM ──
        form = QFormLayout(); form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.firma_edit = QLineEdit()
        self.firma_edit.setPlaceholderText("Firma adını giriniz...")
        form.addRow("Firma *:", self.firma_edit)

        row_konum = QHBoxLayout()
        self.ulke_combo = QComboBox(); self.ulke_combo.setMinimumWidth(180)
        self.ulke_combo.currentIndexChanged.connect(self._ulke_secildi)
        self.sehir_combo = QComboBox(); self.sehir_combo.setMinimumWidth(180)
        row_konum.addWidget(self.ulke_combo)
        row_konum.addWidget(QLabel("→"))
        row_konum.addWidget(self.sehir_combo)
        form.addRow("Konum *:", row_konum)

        row_tesis = QHBoxLayout()
        self.tesis_combo = QComboBox(); self.tesis_combo.setMinimumWidth(180)
        self.tesis_adi_edit = QLineEdit()
        self.tesis_adi_edit.setPlaceholderText("Tesis adı (opsiyonel)")
        self.tesis_adi_edit.setMaximumWidth(200)
        row_tesis.addWidget(self.tesis_combo)
        row_tesis.addWidget(self.tesis_adi_edit)
        form.addRow("Tesis *:", row_tesis)
        layout.addLayout(form)

        # ── ÜRÜN SEÇİM ALANI — 2 PANEL ──
        urun_group = QGroupBox("Ürün Seçimi")
        urun_layout = QHBoxLayout(urun_group)
        urun_layout.setSpacing(12)

        # SOL PANEL — Ürün Havuzu
        sol = QVBoxLayout()
        sol.addWidget(QLabel("Ürün Havuzu:"))
        self.urun_arama = QLineEdit()
        self.urun_arama.setPlaceholderText("Ürün kodu veya adı ile ara...")
        self.urun_arama.textChanged.connect(self._urun_filtrele)
        sol.addWidget(self.urun_arama)

        self.havuz_listesi = QListWidget()
        self.havuz_listesi.setMaximumHeight(200)
        sol.addWidget(self.havuz_listesi)

        self.btn_ekle = QPushButton("→ Projeye Ekle")
        self.btn_ekle.setObjectName("primary")
        self.btn_ekle.clicked.connect(self._urun_ekle)
        sol.addWidget(self.btn_ekle)
        urun_layout.addLayout(sol)

        # SAĞ PANEL — Eklenen Ürünler
        sag = QVBoxLayout()
        sag.addWidget(QLabel("Projedeki Ürünler:"))

        self.eklenen_table = QTableWidget()
        self.eklenen_table.setColumnCount(4)
        self.eklenen_table.setHorizontalHeaderLabels(["Sıra", "Kod", "Ürün Adı", ""])
        self.eklenen_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.eklenen_table.setColumnWidth(0, 40)
        self.eklenen_table.setColumnWidth(1, 80)
        self.eklenen_table.setColumnWidth(3, 50)
        self.eklenen_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.eklenen_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.eklenen_table.setMaximumHeight(200)
        sag.addWidget(self.eklenen_table)

        # Sıralama butonları
        sira_row = QHBoxLayout()
        self.btn_yukari = QPushButton("↑"); self.btn_yukari.setFixedWidth(36)
        self.btn_yukari.clicked.connect(self._yukari_tasi)
        self.btn_asagi = QPushButton("↓"); self.btn_asagi.setFixedWidth(36)
        self.btn_asagi.clicked.connect(self._asagi_tasi)
        sira_row.addWidget(self.btn_yukari)
        sira_row.addWidget(self.btn_asagi)
        sira_row.addStretch()
        sag.addLayout(sira_row)
        urun_layout.addLayout(sag)

        layout.addWidget(urun_group)

        # ── HATA + BUTONLAR ──
        self.error_label = QLabel("")
        self.error_label.setObjectName("error")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        btn_layout = QHBoxLayout(); btn_layout.setSpacing(12)
        btn_iptal = QPushButton("İptal"); btn_iptal.clicked.connect(self.reject)
        self.btn_kaydet = QPushButton("Güncelle" if self.mevcut_proje else "Oluştur")
        self.btn_kaydet.setObjectName("primary")
        self.btn_kaydet.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kaydet.setMinimumHeight(38)
        self.btn_kaydet.clicked.connect(self._kaydet)
        btn_layout.addWidget(btn_iptal)
        btn_layout.addWidget(self.btn_kaydet)
        layout.addLayout(btn_layout)
        self.firma_edit.setFocus()

    # ═════════════════════════════════════════
    # VERİ YÜKLEME
    # ═════════════════════════════════════════

    def _verileri_yukle(self, duzenleme: bool):
        # Ülkeler
        if self.konum_servisi:
            self.ulke_combo.blockSignals(True); self.ulke_combo.clear()
            self.ulke_combo.addItem("— Ülke seçiniz —", "")
            for u in self.konum_servisi.ulke_listesi():
                self.ulke_combo.addItem(u["ad"], u["id"])
            self.ulke_combo.blockSignals(False)

        # Tesis Türleri
        if self.tesis_servisi:
            self.tesis_combo.clear()
            self.tesis_combo.addItem("— Tesis türü —", "")
            for t in self.tesis_servisi.listele():
                self.tesis_combo.addItem(t["ad"], t["id"])

        # Ürün havuzu
        self._havuzu_yukle()

        # Düzenleme
        if duzenleme and self.mevcut_proje:
            self.firma_edit.setText(self.mevcut_proje.firma)
            self.tesis_adi_edit.setText(
                self.mevcut_proje.tesis.split("(")[-1].rstrip(")")
                if "(" in self.mevcut_proje.tesis else "")

            konum = self.mevcut_proje.konum or ""
            if " > " in konum:
                parts = konum.split(" > ", 1)
                self._combo_text_sec(self.ulke_combo, parts[0])
                self._ulke_secildi()
                if len(parts) > 1:
                    self._combo_text_sec(self.sehir_combo, parts[1])

            tesis = self.mevcut_proje.tesis or ""
            tesis_tur = tesis.split("(")[0].strip() if "(" in tesis else tesis
            self._combo_text_sec(self.tesis_combo, tesis_tur)

            # Mevcut ürünleri yükle
            if self.proje_servisi.proje_urun_repo:
                for pu in self.proje_servisi.proje_urunleri(self.mevcut_proje.id):
                    self._eklenen_urunler.append({
                        "urun_id": pu["urun_id"],
                        "kod": pu["kod"],
                        "ad": pu["ad"],
                        "proje_urun_id": pu["id"],
                    })
                self._eklenen_tabloyu_guncelle()

    def _combo_text_sec(self, combo, text):
        for i in range(combo.count()):
            if combo.itemText(i) == text:
                combo.setCurrentIndex(i); return

    def _ulke_secildi(self):
        self.sehir_combo.clear()
        ulke_id = self.ulke_combo.currentData()
        if not ulke_id or not self.konum_servisi:
            self.sehir_combo.addItem("— Önce ülke seçin —", ""); return
        self.sehir_combo.addItem("— Şehir seçiniz —", "")
        for s in self.konum_servisi.sehir_listesi(ulke_id):
            self.sehir_combo.addItem(s["ad"], s["id"])

    # ═════════════════════════════════════════
    # ÜRÜN HAVUZU
    # ═════════════════════════════════════════

    def _havuzu_yukle(self, filtre: str = ""):
        self.havuz_listesi.clear()
        if not self.urun_servisi:
            return
        for u in self.urun_servisi.listele(sadece_aktif=True):
            text = f"{u.kod} — {u.ad}"
            if filtre and filtre.lower() not in text.lower():
                continue
            # Zaten ekliyse atla
            if any(e["urun_id"] == u.id for e in self._eklenen_urunler):
                continue
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, u.id)
            item.setData(Qt.UserRole + 1, u.kod)
            item.setData(Qt.UserRole + 2, u.ad)
            self.havuz_listesi.addItem(item)

    def _urun_filtrele(self, text: str):
        self._havuzu_yukle(text)

    # ═════════════════════════════════════════
    # ÜRÜN EKLEME / SİLME / SIRALAMA
    # ═════════════════════════════════════════

    def _urun_ekle(self):
        """Havuzdan seçili ürünü projeye ekler."""
        item = self.havuz_listesi.currentItem()
        if not item:
            QMessageBox.information(self, "Uyarı", "Önce bir ürün seçin.")
            return
        urun_id = item.data(Qt.UserRole)
        kod = item.data(Qt.UserRole + 1)
        ad = item.data(Qt.UserRole + 2)

        # Duplicate kontrol
        if any(e["urun_id"] == urun_id for e in self._eklenen_urunler):
            QMessageBox.warning(self, "Uyarı", "Bu ürün zaten ekli.")
            return

        self._eklenen_urunler.append({
            "urun_id": urun_id, "kod": kod, "ad": ad,
            "proje_urun_id": None,  # Yeni — henüz DB'de yok
        })
        self._eklenen_tabloyu_guncelle()
        self._havuzu_yukle(self.urun_arama.text())

    def _urun_sil_satir(self, idx: int):
        """Eklenen listeden ürün siler."""
        if 0 <= idx < len(self._eklenen_urunler):
            self._eklenen_urunler.pop(idx)
            self._eklenen_tabloyu_guncelle()
            self._havuzu_yukle(self.urun_arama.text())

    def _yukari_tasi(self):
        row = self.eklenen_table.currentRow()
        if row > 0:
            self._eklenen_urunler[row], self._eklenen_urunler[row - 1] = \
                self._eklenen_urunler[row - 1], self._eklenen_urunler[row]
            self._eklenen_tabloyu_guncelle()
            self.eklenen_table.selectRow(row - 1)

    def _asagi_tasi(self):
        row = self.eklenen_table.currentRow()
        if row < len(self._eklenen_urunler) - 1:
            self._eklenen_urunler[row], self._eklenen_urunler[row + 1] = \
                self._eklenen_urunler[row + 1], self._eklenen_urunler[row]
            self._eklenen_tabloyu_guncelle()
            self.eklenen_table.selectRow(row + 1)

    def _eklenen_tabloyu_guncelle(self):
        """Eklenen ürünler tablosunu yeniden çizer."""
        self.eklenen_table.setRowCount(len(self._eklenen_urunler))
        for i, u in enumerate(self._eklenen_urunler):
            self.eklenen_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.eklenen_table.setItem(i, 1, QTableWidgetItem(u["kod"]))
            self.eklenen_table.setItem(i, 2, QTableWidgetItem(u["ad"]))
            btn = QPushButton("✕")
            btn.setFixedWidth(36)
            btn.clicked.connect(lambda _, idx=i: self._urun_sil_satir(idx))
            self.eklenen_table.setCellWidget(i, 3, btn)

    # ═════════════════════════════════════════
    # KAYDETME
    # ═════════════════════════════════════════

    def _kaydet(self):
        self.error_label.hide()
        self.btn_kaydet.setEnabled(False)
        try:
            firma = self.firma_edit.text().strip()
            ulke_id = self.ulke_combo.currentData() or ""
            ulke_adi = self.ulke_combo.currentText()
            sehir_id = self.sehir_combo.currentData() or ""
            sehir_adi = self.sehir_combo.currentText()
            tesis_id = self.tesis_combo.currentData() or ""
            tesis_adi = self.tesis_combo.currentText()
            tesis_ozel = self.tesis_adi_edit.text().strip()

            if not firma: self._hata("Firma adı zorunludur."); return
            if not ulke_id: self._hata("Ülke seçiniz."); return
            if not sehir_id: self._hata("Şehir seçiniz."); return
            if not tesis_id: self._hata("Tesis türü seçiniz."); return

            konum = f"{ulke_adi} > {sehir_adi}"
            tesis = tesis_adi + (f" ({tesis_ozel})" if tesis_ozel else "")
            urun_seti_str = ", ".join(u["kod"] for u in self._eklenen_urunler)

            if self.mevcut_proje:
                # Düzenleme
                ok, mesaj = self.proje_servisi.guncelle(
                    self.mevcut_proje.id, firma=firma, konum=konum,
                    tesis=tesis, urun_seti=urun_seti_str)
                if ok:
                    self._urunleri_kaydet(self.mevcut_proje.id)
                    self.sonuc_proje = self.proje_servisi.getir(self.mevcut_proje.id)
                    self.accept()
                else:
                    self._hata(mesaj)
            else:
                # Yeni proje
                ok, mesaj, proje = self.proje_servisi.olustur(
                    firma, konum, tesis, urun_seti_str)
                if ok:
                    self._urunleri_kaydet(proje.id)
                    self.sonuc_proje = proje
                    self.accept()
                else:
                    self._hata(mesaj)
        finally:
            self.btn_kaydet.setEnabled(True)

    def _urunleri_kaydet(self, proje_id: str):
        """Eklenen ürünleri DB'ye yazar (transaction)."""
        if not self.proje_servisi.proje_urun_repo:
            return

        repo = self.proje_servisi.proje_urun_repo

        # Mevcut proje ürünlerini sil (düzenleme durumu)
        if self.mevcut_proje:
            mevcut = repo.proje_urunleri_getir(proje_id)
            for m in mevcut:
                repo.urun_sil(m["id"])

        # Yeni ürünleri ekle
        for i, u in enumerate(self._eklenen_urunler, 1):
            snapshot = {"urun_id": u["urun_id"], "kod": u["kod"],
                        "ad": u["ad"], "sira": i}
            repo.urun_ekle(proje_id, u["urun_id"], i, snapshot)

    def _hata(self, mesaj: str):
        self.error_label.setText(mesaj)
        self.error_label.show()
        self.btn_kaydet.setEnabled(True)
