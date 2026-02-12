#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Login Sayfası — Kimlik servisi ile entegre.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QCheckBox, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QCursor


class LoginPage(QWidget):
    """Giriş sayfası widget'ı."""

    login_basarili = pyqtSignal()

    def __init__(self, kimlik_servisi, parent=None):
        super().__init__(parent)
        self.kimlik_servisi = kimlik_servisi
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setObjectName("card")
        card.setFixedWidth(400)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(16)
        card_layout.setContentsMargins(32, 40, 32, 32)

        # Başlık
        title = QLabel("Proje Yönetim Sistemi")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("Devam etmek için giriş yapın")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignCenter)

        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(8)

        # Alanlar
        self.username = QLineEdit()
        self.username.setPlaceholderText("Kullanıcı Adı")

        self.password = QLineEdit()
        self.password.setPlaceholderText("Şifre")
        self.password.setEchoMode(QLineEdit.Password)
        self.password.returnPressed.connect(self._giris_yap)

        self.remember = QCheckBox("Beni Hatırla")

        card_layout.addWidget(QLabel("Kullanıcı Adı"))
        card_layout.addWidget(self.username)
        card_layout.addWidget(QLabel("Şifre"))
        card_layout.addWidget(self.password)
        card_layout.addWidget(self.remember)
        card_layout.addSpacing(8)

        # Giriş butonu
        self.btn_login = QPushButton("Giriş Yap")
        self.btn_login.setObjectName("primary")
        self.btn_login.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_login.setMinimumHeight(42)
        self.btn_login.clicked.connect(self._giris_yap)
        card_layout.addWidget(self.btn_login)

        # Hata mesajı
        self.error_label = QLabel("")
        self.error_label.setObjectName("error")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.hide()
        card_layout.addWidget(self.error_label)

        outer.addWidget(card)

        # Versiyon
        from uygulama.ortak.app_state import app_state
        version = QLabel(f"v{app_state().uygulama_surumu}")
        version.setObjectName("version")
        version.setAlignment(Qt.AlignRight)
        outer.addWidget(version)

        # İlk odak
        self.username.setFocus()

    def _giris_yap(self):
        """Giriş butonuna basıldığında çağrılır."""
        kullanici_adi = self.username.text().strip()
        sifre = self.password.text()

        # Butonu devre dışı bırak
        self.btn_login.setEnabled(False)
        self.btn_login.setText("Giriş yapılıyor...")
        self.error_label.hide()

        try:
            basarili, mesaj = self.kimlik_servisi.giris_yap(kullanici_adi, sifre)

            if basarili:
                self.error_label.hide()
                self.password.clear()
                self.login_basarili.emit()
            else:
                self.error_label.setText(mesaj)
                self.error_label.show()
                self.password.setFocus()
                self.password.selectAll()
        finally:
            self.btn_login.setEnabled(True)
            self.btn_login.setText("Giriş Yap")

    def sifirla(self):
        """Sayfayı sıfırlar (çıkış yapıldığında)."""
        self.username.clear()
        self.password.clear()
        self.error_label.hide()
        self.username.setFocus()
