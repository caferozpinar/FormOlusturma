#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proje Detay Sayfası — Backend entegreli.
Proje bilgileri, doküman listesi, özet, loglar.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableView, QTabWidget, QFrame, QGridLayout, QMessageBox,
    QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal

from uygulama.arayuz.ui_yardimcilar import (
    SimpleTableModel, make_badge, make_stat_card, setup_table
)
from uygulama.domain.modeller import ProjeDurumu
from uygulama.ortak.app_state import app_state
from uygulama.ortak.yardimcilar import tarih_formatla


class ProjectDetailPage(QWidget):
    """Proje detay sayfası — veritabanı bağlantılı."""

    go_back = pyqtSignal()
    open_document = pyqtSignal(str)  # belge_id

    def __init__(self, proje_servisi, belge_servisi, log_repo,
                 teklif_srv=None, em_repo=None,
                 belge_olusturma_srv=None, parent=None):
        super().__init__(parent)
        self.proje_servisi = proje_servisi
        self.belge_servisi = belge_servisi
        self.log_repo = log_repo
        self.teklif_srv = teklif_srv
        self.belge_olusturma_srv = belge_olusturma_srv
        self.em_repo = em_repo
        self._proje_id = None
        self._proje = None
        self._belgeler = []
        self._build()

    def _build(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(24, 16, 24, 16)
        self.layout.setSpacing(16)

        # ── Header ──
        self.header = QFrame()
        self.header.setObjectName("toolbar")
        hl = QHBoxLayout(self.header)
        hl.setContentsMargins(16, 12, 16, 12)

        # Sol bilgiler
        left = QVBoxLayout()
        left.setSpacing(4)
        self.proje_baslik = QLabel("")
        self.proje_baslik.setObjectName("title")
        self.proje_baslik.setStyleSheet("font-size: 18px;")
        left.addWidget(self.proje_baslik)

        hash_row = QHBoxLayout()
        self.hash_label = QLabel("")
        self.hash_label.setObjectName("subtitle")
        btn_copy = QPushButton("Kopyala")
        btn_copy.setFixedHeight(28)
        btn_copy.setStyleSheet("font-size: 11px; padding: 2px 10px;")
        btn_copy.clicked.connect(self._hash_kopyala)
        hash_row.addWidget(self.hash_label)
        hash_row.addWidget(btn_copy)
        hash_row.addStretch()
        left.addLayout(hash_row)

        self.badge_container = QHBoxLayout()
        self.badge_container.setAlignment(Qt.AlignLeft)
        left.addLayout(self.badge_container)

        # Sağ butonlar
        right = QVBoxLayout()
        right.setAlignment(Qt.AlignTop)
        br = QHBoxLayout()
        br.setSpacing(8)

        self.btn_edit = QPushButton("Düzenle")
        self.btn_edit.clicked.connect(self._duzenle)

        self.btn_close_project = QPushButton("Projeyi Kapat")
        self.btn_close_project.setObjectName("danger")
        self.btn_close_project.clicked.connect(self._proje_kapat)

        self.btn_activate = QPushButton("Aktifleştir")
        self.btn_activate.setObjectName("success")
        self.btn_activate.clicked.connect(self._proje_aktifle)

        self.btn_delete = QPushButton("Sil")
        self.btn_delete.setObjectName("danger")
        self.btn_delete.clicked.connect(self._proje_sil)

        btn_back = QPushButton("← Geri")
        btn_back.clicked.connect(self.go_back.emit)

        br.addWidget(self.btn_edit)
        br.addWidget(self.btn_close_project)
        br.addWidget(self.btn_activate)
        br.addWidget(self.btn_delete)
        br.addWidget(btn_back)
        right.addLayout(br)

        hl.addLayout(left, 1)
        hl.addLayout(right)
        self.layout.addWidget(self.header)

        # ── Tabs ──
        self.tabs = QTabWidget()

        # TAB 1: Teklifler / Keşifler (ana çalışma alanı)
        from uygulama.arayuz.teklif_sayfa import TeklifSayfasi
        self.teklif_sayfasi = TeklifSayfasi(
            self.teklif_srv, self.em_repo,
            belge_srv=self.belge_olusturma_srv)
        self.tabs.addTab(self.teklif_sayfasi, "Teklifler / Keşifler")

        # TAB 2: Özet
        sw = QWidget()
        self.summary_layout = QVBoxLayout(sw)
        self.summary_layout.setContentsMargins(16, 16, 16, 16)
        self.summary_layout.setSpacing(16)
        self.summary_grid = QGridLayout()
        self.summary_grid.setSpacing(16)
        self.summary_layout.addLayout(self.summary_grid)
        self.summary_layout.addStretch()
        self.tabs.addTab(sw, "Özet")

        # TAB 3: Loglar
        lw = QWidget()
        ll = QVBoxLayout(lw)
        ll.setContentsMargins(16, 16, 16, 16)
        self.log_table = QTableView()
        setup_table(self.log_table)
        self.log_model = SimpleTableModel(["Tarih", "Kullanıcı", "İşlem"])
        self.log_table.setModel(self.log_model)
        ll.addWidget(self.log_table)
        self.tabs.addTab(lw, "Loglar (Admin)")

        self.layout.addWidget(self.tabs)

    # ─────────────────────────────────────────
    # VERİ YÜKLEME
    # ─────────────────────────────────────────

    def proje_yukle(self, proje_id: str):
        """Proje verilerini yükler ve gösterir."""
        self._proje_id = proje_id
        self._proje = self.proje_servisi.getir(proje_id)

        if not self._proje:
            QMessageBox.warning(self, "Hata", "Proje bulunamadı.")
            self.go_back.emit()
            return

        p = self._proje
        state = app_state()

        # Başlık
        self.proje_baslik.setText(f"{p.firma} – {p.konum} – {p.tesis}")
        self.hash_label.setText(f"Hash: {p.hash_kodu}")

        # Badge güncelle
        while self.badge_container.count():
            item = self.badge_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        variant = "active" if p.durum == ProjeDurumu.ACTIVE else "closed"
        self.badge_container.addWidget(make_badge(p.durum.value, variant))

        # Buton görünürlüğü
        kapali = p.durum == ProjeDurumu.CLOSED
        self.btn_close_project.setVisible(not kapali)
        self.btn_activate.setVisible(kapali and state.admin_mi)

        # Belgeleri yükle — artık Teklifler tab'ında
        # (eski doküman sistemi kaldırıldı)

        # Teklifleri yükle
        if hasattr(self, 'teklif_sayfasi'):
            self.teklif_sayfasi.yukle(proje_id)

        # Özet kartları
        self._ozet_guncelle()

        # Loglar
        self._loglari_yukle()

        # Admin tab görünürlüğü (Loglar = tab index 2)
        self.tabs.setTabVisible(2, state.admin_mi)

    def _ozet_guncelle(self):
        """Özet sekmesindeki kartları günceller."""
        # Mevcut kartları temizle
        while self.summary_grid.count():
            item = self.summary_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self._proje:
            p = self._proje
            stats = self.belge_servisi.proje_belge_istatistikleri(p.id)
            self.summary_grid.addWidget(
                make_stat_card(p.hash_kodu, "Proje Hash"), 0, 0)
            self.summary_grid.addWidget(
                make_stat_card(p.durum.value, "Durum"), 0, 1)
            self.summary_grid.addWidget(
                make_stat_card(tarih_formatla(p.olusturma_tarihi, "%d.%m.%Y"),
                               "Oluşturma Tarihi"), 0, 2)
            self.summary_grid.addWidget(
                make_stat_card(str(stats["toplam_belge"]), "Toplam Doküman"), 1, 0)
            self.summary_grid.addWidget(
                make_stat_card(str(stats["onaylanan"]), "Onaylanan"), 1, 1)
            toplam_m = stats["toplam_maliyet"]
            self.summary_grid.addWidget(
                make_stat_card(f"₺{toplam_m:,.2f}" if toplam_m else "—",
                               "Toplam Maliyet"), 1, 2)

    def _loglari_yukle(self):
        """Proje loglarını yükler."""
        if not self._proje_id:
            return
        loglar = self.log_repo.hedef_icin_getir(
            "projeler", self._proje_id, limit=50)
        veri = []
        for log in loglar:
            veri.append([
                tarih_formatla(log.get("tarih", "")),
                log.get("kullanici_adi", ""),
                log.get("detay", ""),
            ])
        self.log_model.veri_guncelle(veri)

    # ─────────────────────────────────────────
    # İŞLEMLER
    # ─────────────────────────────────────────

    def _hash_kopyala(self):
        if self._proje:
            QApplication.clipboard().setText(self._proje.hash_kodu)

    def _duzenle(self):
        if not self._proje:
            return
        from uygulama.arayuz.proje_dialog import ProjeDialog
        dialog = ProjeDialog(
            self.proje_servisi, proje=self._proje, parent=self)
        if dialog.exec_():
            self.proje_yukle(self._proje_id)

    def _proje_kapat(self):
        if not self._proje:
            return
        cevap = QMessageBox.question(
            self, "Proje Kapat",
            f"Bu projeyi kapatmak istediğinize emin misiniz?\n"
            f"Kapalı projede yeni belge oluşturulamaz.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if cevap == QMessageBox.Yes:
            basarili, mesaj = self.proje_servisi.kapat(self._proje_id)
            if basarili:
                self.proje_yukle(self._proje_id)
            else:
                QMessageBox.warning(self, "Hata", mesaj)

    def _proje_aktifle(self):
        if not self._proje:
            return
        basarili, mesaj = self.proje_servisi.aktifle(self._proje_id)
        if basarili:
            self.proje_yukle(self._proje_id)
        else:
            QMessageBox.warning(self, "Hata", mesaj)

    def _proje_sil(self):
        if not self._proje:
            return
        cevap = QMessageBox.question(
            self, "Proje Sil",
            f"Bu projeyi silmek istediğinize emin misiniz?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if cevap == QMessageBox.Yes:
            basarili, mesaj = self.proje_servisi.sil(self._proje_id)
            if basarili:
                self.go_back.emit()
            else:
                QMessageBox.warning(self, "Hata", mesaj)

    # Eski belge işlemleri (Dokümanlar tab'ı) kaldırıldı.
    # Tüm teklif/keşif işlemleri artık TeklifSayfasi widget'ında.
