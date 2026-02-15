#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Proje Dialog — DB-tabanlı Ülke→Şehir, Tesis Türü, Ürün çoklu seçim."""

import json
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QListWidget, QListWidgetItem, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor

from uygulama.domain.modeller import Proje


class ProjeDialog(QDialog):
    """Proje oluşturma ve düzenleme dialog'u — DB-tabanlı lookup."""

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

        duzenleme = proje is not None
        self.setWindowTitle("Proje Düzenle" if duzenleme else "Yeni Proje")
        self.setFixedWidth(520)
        self.setModal(True)
        self._build(duzenleme)
        self._verileri_yukle(duzenleme)

    def _build(self, duzenleme: bool):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Proje Düzenle" if duzenleme else "Yeni Proje Oluştur")
        title.setObjectName("sectionTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        form = QFormLayout(); form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Firma (serbest giriş)
        self.firma_edit = QLineEdit()
        self.firma_edit.setPlaceholderText("Firma adını giriniz...")
        form.addRow("Firma *:", self.firma_edit)

        # Ülke dropdown (DB)
        self.ulke_combo = QComboBox(); self.ulke_combo.setMinimumWidth(280)
        self.ulke_combo.currentIndexChanged.connect(self._ulke_secildi)
        form.addRow("Ülke *:", self.ulke_combo)

        # Şehir dropdown (DB, ülkeye bağlı)
        self.sehir_combo = QComboBox(); self.sehir_combo.setMinimumWidth(280)
        form.addRow("Şehir *:", self.sehir_combo)

        # Tesis Türü dropdown (DB)
        self.tesis_combo = QComboBox(); self.tesis_combo.setMinimumWidth(280)
        form.addRow("Tesis Türü *:", self.tesis_combo)

        # Tesis Adı (serbest giriş)
        self.tesis_adi_edit = QLineEdit()
        self.tesis_adi_edit.setPlaceholderText("Tesis adı (opsiyonel)")
        form.addRow("Tesis Adı:", self.tesis_adi_edit)

        layout.addLayout(form)

        # Ürün Seti — çoklu seçim
        layout.addWidget(QLabel("Ürün Seti (çoklu seçim):"))
        self.urun_arama = QLineEdit()
        self.urun_arama.setPlaceholderText("Ürün ara...")
        self.urun_arama.textChanged.connect(self._urun_filtrele)
        layout.addWidget(self.urun_arama)

        self.urun_listesi = QListWidget()
        self.urun_listesi.setMaximumHeight(140)
        self.urun_listesi.setSelectionMode(QListWidget.MultiSelection)
        layout.addWidget(self.urun_listesi)

        # Hata mesajı
        self.error_label = QLabel("")
        self.error_label.setObjectName("error")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        # Butonlar
        btn_layout = QHBoxLayout(); btn_layout.setSpacing(12)
        btn_iptal = QPushButton("İptal")
        btn_iptal.clicked.connect(self.reject)
        self.btn_kaydet = QPushButton("Güncelle" if duzenleme else "Oluştur")
        self.btn_kaydet.setObjectName("primary")
        self.btn_kaydet.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kaydet.setMinimumHeight(38)
        self.btn_kaydet.clicked.connect(self._kaydet)
        btn_layout.addWidget(btn_iptal)
        btn_layout.addWidget(self.btn_kaydet)
        layout.addLayout(btn_layout)
        self.firma_edit.setFocus()

    def _verileri_yukle(self, duzenleme: bool):
        """Dropdown'ları DB'den doldur."""
        # Ülkeler
        if self.konum_servisi:
            self.ulke_combo.blockSignals(True)
            self.ulke_combo.clear()
            self.ulke_combo.addItem("— Seçiniz —", "")
            for u in self.konum_servisi.ulke_listesi():
                self.ulke_combo.addItem(u["ad"], u["id"])
            self.ulke_combo.blockSignals(False)

        # Tesis Türleri
        if self.tesis_servisi:
            self.tesis_combo.clear()
            self.tesis_combo.addItem("— Seçiniz —", "")
            for t in self.tesis_servisi.listele():
                self.tesis_combo.addItem(t["ad"], t["id"])

        # Ürünler
        self._urunleri_yukle()

        # Düzenleme modunda mevcut değerleri doldur
        if duzenleme and self.mevcut_proje:
            self.firma_edit.setText(self.mevcut_proje.firma)
            self.tesis_adi_edit.setText(self.mevcut_proje.tesis)

            # Konum → Ülke/Şehir parse (eskiden text, yeni format: "Ülke > Şehir")
            konum = self.mevcut_proje.konum or ""
            if " > " in konum:
                # Yeni format
                parts = konum.split(" > ", 1)
                self._select_combo_by_text(self.ulke_combo, parts[0])
                self._ulke_secildi()
                if len(parts) > 1:
                    self._select_combo_by_text(self.sehir_combo, parts[1])
            else:
                # Eski format (düz text) — şehir combo'ya ekleme yapma
                pass

            # Ürün seti (eski format: text)
            urun_seti = self.mevcut_proje.urun_seti or ""
            if urun_seti:
                for i in range(self.urun_listesi.count()):
                    item = self.urun_listesi.item(i)
                    if item.text().split(" — ")[0] in urun_seti:
                        item.setSelected(True)

    def _select_combo_by_text(self, combo: QComboBox, text: str):
        for i in range(combo.count()):
            if combo.itemText(i) == text:
                combo.setCurrentIndex(i)
                return

    def _ulke_secildi(self):
        """Ülke değişince şehir listesini güncelle."""
        self.sehir_combo.clear()
        ulke_id = self.ulke_combo.currentData()
        if not ulke_id or not self.konum_servisi:
            self.sehir_combo.addItem("— Önce ülke seçin —", "")
            return
        self.sehir_combo.addItem("— Seçiniz —", "")
        for s in self.konum_servisi.sehir_listesi(ulke_id):
            self.sehir_combo.addItem(s["ad"], s["id"])

    def _urunleri_yukle(self, filtre: str = ""):
        """Aktif ürünleri listele."""
        self.urun_listesi.clear()
        if not self.urun_servisi:
            return
        urunler = self.urun_servisi.listele(sadece_aktif=True)
        for u in urunler:
            text = f"{u.kod} — {u.ad}"
            if filtre and filtre.lower() not in text.lower():
                continue
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, u.id)
            self.urun_listesi.addItem(item)

    def _urun_filtrele(self, text: str):
        self._urunleri_yukle(text)

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

            # Validasyon
            if not firma:
                self._hata("Firma adı zorunludur."); return
            if not ulke_id:
                self._hata("Ülke seçiniz."); return
            if not sehir_id:
                self._hata("Şehir seçiniz."); return
            if not tesis_id:
                self._hata("Tesis türü seçiniz."); return

            # Konum string: "Ülke > Şehir"
            konum = f"{ulke_adi} > {sehir_adi}"
            # Tesis: Tür + özel ad
            tesis = f"{tesis_adi}" + (f" ({tesis_ozel})" if tesis_ozel else "")

            # Seçili ürünler
            secili_urunler = []
            for i in range(self.urun_listesi.count()):
                item = self.urun_listesi.item(i)
                if item.isSelected():
                    secili_urunler.append({
                        "id": item.data(Qt.UserRole),
                        "text": item.text(),
                    })

            urun_seti_str = ", ".join(u["text"].split(" — ")[0]
                                       for u in secili_urunler)

            # Snapshot verisi
            snapshot = {
                "ulke_id": ulke_id, "ulke_adi": ulke_adi,
                "sehir_id": sehir_id, "sehir_adi": sehir_adi,
                "tesis_id": tesis_id, "tesis_adi": tesis_adi,
                "tesis_ozel": tesis_ozel,
                "urunler": secili_urunler,
            }

            if self.mevcut_proje:
                basarili, mesaj = self.proje_servisi.guncelle(
                    self.mevcut_proje.id,
                    firma=firma, konum=konum,
                    tesis=tesis, urun_seti=urun_seti_str)
                if basarili:
                    self.sonuc_proje = self.proje_servisi.getir(
                        self.mevcut_proje.id)
                    self.accept()
                else:
                    self._hata(mesaj)
            else:
                basarili, mesaj, proje = self.proje_servisi.olustur(
                    firma, konum, tesis, urun_seti_str)
                if basarili:
                    self.sonuc_proje = proje
                    # Proje-ürün bağlantılarını kaydet
                    self._urun_baglantilari_kaydet(
                        proje.id, secili_urunler, snapshot)
                    self.accept()
                else:
                    self._hata(mesaj)
        finally:
            self.btn_kaydet.setEnabled(True)

    def _urun_baglantilari_kaydet(self, proje_id: str,
                                    urunler: list[dict],
                                    snapshot: dict):
        """Proje-ürün bağlantılarını ve snapshot'ı DB'ye yazar."""
        if not self.urun_servisi:
            return
        try:
            from uygulama.domain.modeller import _yeni_uuid
            from uygulama.ortak.yardimcilar import simdi_iso
            db = self.urun_servisi.urun_repo.db
            with db.transaction() as conn:
                for u in urunler:
                    conn.execute(
                        """INSERT INTO proje_urunleri
                           (id, proje_id, urun_id, urun_snapshot)
                           VALUES (?,?,?,?)""",
                        (_yeni_uuid(), proje_id, u["id"],
                         json.dumps(u, ensure_ascii=False)))
        except Exception as e:
            pass  # Log hata — proje zaten oluştu

    def _hata(self, mesaj: str):
        self.error_label.setText(mesaj)
        self.error_label.show()
        self.btn_kaydet.setEnabled(True)
