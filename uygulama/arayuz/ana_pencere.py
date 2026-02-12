#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ana Pencere — Tüm servisler ve sayfa navigasyonu.
"""

from PyQt5.QtWidgets import QMainWindow, QStackedWidget

from uygulama.arayuz.login_sayfa import LoginPage
from uygulama.arayuz.proje_listesi_sayfa import ProjectListPage
from uygulama.arayuz.proje_detay_sayfa import ProjectDetailPage
from uygulama.arayuz.sayfalar import DocumentPage, SyncPage, AdminPanelPage
from uygulama.ortak.app_state import app_state


class AnaPencere(QMainWindow):
    """Uygulamanın ana penceresi."""

    LOGIN = 0
    PROJE_LISTESI = 1
    PROJE_DETAY = 2
    DOKUMAN = 3
    SYNC = 4
    ADMIN = 5

    def __init__(self, kimlik_servisi, proje_servisi, log_repo):
        super().__init__()
        self.kimlik_servisi = kimlik_servisi
        self.proje_servisi = proje_servisi
        self.log_repo = log_repo

        self.setWindowTitle("Proje Yönetim Sistemi")
        self.setMinimumSize(1200, 780)
        self.resize(1400, 900)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self._sayfalari_olustur()
        self._sinyalleri_bagla()

    def _sayfalari_olustur(self):
        self.login_sayfa = LoginPage(self.kimlik_servisi)
        self.proje_listesi_sayfa = ProjectListPage(self.proje_servisi)
        self.proje_detay_sayfa = ProjectDetailPage(
            self.proje_servisi, self.log_repo)
        self.dokuman_sayfa = DocumentPage()
        self.sync_sayfa = SyncPage()
        self.admin_sayfa = AdminPanelPage()

        self.stack.addWidget(self.login_sayfa)           # 0
        self.stack.addWidget(self.proje_listesi_sayfa)   # 1
        self.stack.addWidget(self.proje_detay_sayfa)     # 2
        self.stack.addWidget(self.dokuman_sayfa)         # 3
        self.stack.addWidget(self.sync_sayfa)            # 4
        self.stack.addWidget(self.admin_sayfa)           # 5

    def _sinyalleri_bagla(self):
        self.login_sayfa.login_basarili.connect(self._giris_sonrasi)

        self.proje_listesi_sayfa.open_project.connect(self._proje_ac)
        self.proje_listesi_sayfa.open_sync.connect(
            lambda: self._sayfaya_git(self.SYNC))
        self.proje_listesi_sayfa.open_admin.connect(
            lambda: self._sayfaya_git(self.ADMIN))
        self.proje_listesi_sayfa.cikis_yap.connect(self._cikis_yap)

        self.proje_detay_sayfa.go_back.connect(self._proje_listesine_don)
        self.proje_detay_sayfa.open_document.connect(
            lambda _: self._sayfaya_git(self.DOKUMAN))

        self.dokuman_sayfa.go_back.connect(
            lambda: self._sayfaya_git(self.PROJE_DETAY))
        self.sync_sayfa.go_back.connect(self._proje_listesine_don)
        self.admin_sayfa.go_back.connect(self._proje_listesine_don)

    def _sayfaya_git(self, index: int):
        self.stack.setCurrentIndex(index)

    def _giris_sonrasi(self):
        self._sayfaya_git(self.PROJE_LISTESI)
        self.proje_listesi_sayfa.sayfa_gosterildi()

    def _proje_ac(self, proje_id: str):
        self.proje_detay_sayfa.proje_yukle(proje_id)
        self._sayfaya_git(self.PROJE_DETAY)

    def _proje_listesine_don(self):
        self._sayfaya_git(self.PROJE_LISTESI)
        self.proje_listesi_sayfa.sayfa_gosterildi()

    def _cikis_yap(self):
        self.kimlik_servisi.cikis_yap()
        self.login_sayfa.sifirla()
        self._sayfaya_git(self.LOGIN)
