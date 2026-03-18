#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ana Pencere — Tüm servisler ve sayfa navigasyonu.
"""

from PyQt5.QtWidgets import QMainWindow, QStackedWidget

from uygulama.arayuz.login_sayfa import LoginPage
from uygulama.arayuz.proje_listesi_sayfa import ProjectListPage
from uygulama.arayuz.proje_detay_sayfa import ProjectDetailPage
from uygulama.arayuz.sayfalar import DocumentPage
from uygulama.arayuz.sync_sayfa import SyncPage
from uygulama.arayuz.admin_sayfa import AdminPanelPage
from uygulama.arayuz.analitik_sayfa import AnalitikPage
from uygulama.ortak.app_state import app_state
from uygulama.ortak.oturum_yoneticisi import OturumYoneticisi


class AnaPencere(QMainWindow):
    """Uygulamanın ana penceresi."""

    LOGIN = 0
    PROJE_LISTESI = 1
    PROJE_DETAY = 2
    DOKUMAN = 3
    SYNC = 4
    ADMIN = 5
    ANALITIK = 6

    def __init__(self, kimlik_servisi, proje_servisi, belge_servisi,
                 urun_servisi, sync_servisi, yetki_servisi, log_repo,
                 analitik_servisi=None, konum_servisi=None,
                 tesis_servisi=None, em_repo=None, em_srv=None,
                 placeholder_srv=None, teklif_srv=None,
                 belge_olusturma_srv=None,
                 drive_sync_srv=None):
        super().__init__()
        self.kimlik_servisi = kimlik_servisi
        self.proje_servisi = proje_servisi
        self.belge_servisi = belge_servisi
        self.urun_servisi = urun_servisi
        self.sync_servisi = sync_servisi
        self.yetki_servisi = yetki_servisi
        self.log_repo = log_repo
        self.analitik_servisi = analitik_servisi
        self.konum_servisi = konum_servisi
        self.tesis_servisi = tesis_servisi
        self.em_repo = em_repo
        self.em_srv = em_srv
        self.placeholder_srv = placeholder_srv
        self.teklif_srv = teklif_srv
        self.belge_olusturma_srv = belge_olusturma_srv
        self.drive_sync_srv = drive_sync_srv

        self.setWindowTitle("Proje Yönetim Sistemi")
        self.setMinimumSize(1200, 780)
        self.resize(1400, 900)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self._sayfalari_olustur()
        self._sinyalleri_bagla()
        self._otomatik_giris_dene()

    def _sayfalari_olustur(self):
        self.login_sayfa = LoginPage(self.kimlik_servisi)
        self.proje_listesi_sayfa = ProjectListPage(
            self.proje_servisi, self.konum_servisi,
            self.tesis_servisi, self.urun_servisi, self.yetki_servisi)
        self.proje_detay_sayfa = ProjectDetailPage(
            self.proje_servisi, self.belge_servisi, self.log_repo,
            self.teklif_srv, self.em_repo, self.yetki_servisi,
            belge_olusturma_srv=self.belge_olusturma_srv)
        self.dokuman_sayfa = DocumentPage()
        self.sync_sayfa = SyncPage(self.sync_servisi, self.yetki_servisi,
                                    drive_sync_srv=self.drive_sync_srv)
        self.admin_sayfa = AdminPanelPage(
            self.urun_servisi, self.kimlik_servisi, self.yetki_servisi,
            self.log_repo,
            self.konum_servisi, self.tesis_servisi,
            self.em_repo, self.em_srv, self.placeholder_srv,
            belge_srv=self.belge_olusturma_srv)
        self.analitik_sayfa = AnalitikPage(self.analitik_servisi)

        self.stack.addWidget(self.login_sayfa)           # 0
        self.stack.addWidget(self.proje_listesi_sayfa)   # 1
        self.stack.addWidget(self.proje_detay_sayfa)     # 2
        self.stack.addWidget(self.dokuman_sayfa)         # 3
        self.stack.addWidget(self.sync_sayfa)            # 4
        self.stack.addWidget(self.admin_sayfa)           # 5
        self.stack.addWidget(self.analitik_sayfa)        # 6

    def _sinyalleri_bagla(self):
        self.login_sayfa.login_basarili.connect(self._giris_sonrasi)

        self.proje_listesi_sayfa.open_project.connect(self._proje_ac)
        self.proje_listesi_sayfa.open_sync.connect(self._sync_ac)
        self.proje_listesi_sayfa.open_admin.connect(self._admin_ac)
        self.proje_listesi_sayfa.open_analitik.connect(self._analitik_ac)
        self.proje_listesi_sayfa.cikis_yap.connect(self._cikis_yap)

        self.proje_detay_sayfa.go_back.connect(self._proje_listesine_don)
        self.proje_detay_sayfa.open_document.connect(
            lambda _: self._sayfaya_git(self.DOKUMAN))

        self.dokuman_sayfa.go_back.connect(
            lambda: self._sayfaya_git(self.PROJE_DETAY))
        self.sync_sayfa.go_back.connect(self._proje_listesine_don)
        self.admin_sayfa.go_back.connect(self._proje_listesine_don)
        self.analitik_sayfa.go_back.connect(self._proje_listesine_don)

    def _sayfaya_git(self, index: int):
        self.stack.setCurrentIndex(index)

    def _giris_sonrasi(self):
        self._sayfaya_git(self.PROJE_LISTESI)
        self.proje_listesi_sayfa.sayfa_gosterildi()

    def _proje_ac(self, proje_id: str):
        self.proje_detay_sayfa.proje_yukle(proje_id)
        self._sayfaya_git(self.PROJE_DETAY)

    def _admin_ac(self):
        self.admin_sayfa.sayfa_gosterildi()
        self._sayfaya_git(self.ADMIN)

    def _sync_ac(self):
        self.sync_sayfa.sayfa_gosterildi()
        self._sayfaya_git(self.SYNC)

    def _analitik_ac(self):
        self.analitik_sayfa.sayfa_gosterildi()
        self._sayfaya_git(self.ANALITIK)

    def _proje_listesine_don(self):
        self._sayfaya_git(self.PROJE_LISTESI)
        self.proje_listesi_sayfa.sayfa_gosterildi()

    def _otomatik_giris_dene(self):
        """Kayıtlı oturum varsa otomatik giriş yapar."""
        kaydedilmis = OturumYoneticisi.yukle()
        if not kaydedilmis:
            return
        kullanici_adi, sifre = kaydedilmis
        basarili, _ = self.kimlik_servisi.giris_yap(kullanici_adi, sifre)
        if basarili:
            self._giris_sonrasi()

    def _cikis_yap(self):
        OturumYoneticisi.sil()
        self.kimlik_servisi.cikis_yap()
        self.login_sayfa.sifirla()
        self._sayfaya_git(self.LOGIN)
