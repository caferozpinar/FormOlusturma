#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proje Oluşturma / Düzenleme Dialog Penceresi.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor

from uygulama.domain.modeller import Proje


class ProjeDialog(QDialog):
    """Proje oluşturma ve düzenleme dialog'u."""

    def __init__(self, proje_servisi, proje: Proje = None, parent=None):
        super().__init__(parent)
        self.proje_servisi = proje_servisi
        self.mevcut_proje = proje
        self.sonuc_proje = None

        duzenleme = proje is not None
        self.setWindowTitle("Proje Düzenle" if duzenleme else "Yeni Proje")
        self.setFixedWidth(480)
        self.setModal(True)
        self._build(duzenleme)

    def _build(self, duzenleme: bool):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Başlık
        title = QLabel("Proje Düzenle" if duzenleme else "Yeni Proje Oluştur")
        title.setObjectName("sectionTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Form
        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.firma_edit = QLineEdit()
        self.firma_edit.setPlaceholderText("Firma adını giriniz...")
        form.addRow("Firma *:", self.firma_edit)

        self.konum_edit = QLineEdit()
        self.konum_edit.setPlaceholderText("Şehir veya konum...")
        form.addRow("Konum *:", self.konum_edit)

        self.tesis_edit = QLineEdit()
        self.tesis_edit.setPlaceholderText("Tesis adı...")
        form.addRow("Tesis *:", self.tesis_edit)

        self.urun_seti_edit = QLineEdit()
        self.urun_seti_edit.setPlaceholderText("Ürün seti (opsiyonel)")
        form.addRow("Ürün Seti:", self.urun_seti_edit)

        layout.addLayout(form)

        # Mevcut projeyi doldur
        if duzenleme and self.mevcut_proje:
            self.firma_edit.setText(self.mevcut_proje.firma)
            self.konum_edit.setText(self.mevcut_proje.konum)
            self.tesis_edit.setText(self.mevcut_proje.tesis)
            self.urun_seti_edit.setText(self.mevcut_proje.urun_seti)

        # Hata mesajı
        self.error_label = QLabel("")
        self.error_label.setObjectName("error")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        # Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

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

        # Enter ile kaydet
        self.urun_seti_edit.returnPressed.connect(self._kaydet)
        self.firma_edit.setFocus()

    def _kaydet(self):
        """Kaydet butonuna basıldığında."""
        self.error_label.hide()
        self.btn_kaydet.setEnabled(False)

        try:
            firma = self.firma_edit.text().strip()
            konum = self.konum_edit.text().strip()
            tesis = self.tesis_edit.text().strip()
            urun_seti = self.urun_seti_edit.text().strip()

            if self.mevcut_proje:
                # Düzenleme modu
                basarili, mesaj = self.proje_servisi.guncelle(
                    self.mevcut_proje.id,
                    firma=firma, konum=konum,
                    tesis=tesis, urun_seti=urun_seti
                )
                if basarili:
                    self.sonuc_proje = self.proje_servisi.getir(
                        self.mevcut_proje.id)
                    self.accept()
                else:
                    self.error_label.setText(mesaj)
                    self.error_label.show()
            else:
                # Yeni proje
                basarili, mesaj, proje = self.proje_servisi.olustur(
                    firma, konum, tesis, urun_seti
                )
                if basarili:
                    self.sonuc_proje = proje
                    self.accept()
                else:
                    self.error_label.setText(mesaj)
                    self.error_label.show()
        finally:
            self.btn_kaydet.setEnabled(True)
