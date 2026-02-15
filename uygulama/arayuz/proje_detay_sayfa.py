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

    def __init__(self, proje_servisi, belge_servisi, log_repo, parent=None):
        super().__init__(parent)
        self.proje_servisi = proje_servisi
        self.belge_servisi = belge_servisi
        self.log_repo = log_repo
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

        # TAB 1: Dokümanlar (şimdilik placeholder, Faz 3'te entegre edilecek)
        doc_w = QWidget()
        dl = QVBoxLayout(doc_w)
        dl.setContentsMargins(16, 16, 16, 16)
        dl.setSpacing(12)

        self.doc_table = QTableView()
        setup_table(self.doc_table)
        self.doc_model = SimpleTableModel(
            ["Tür", "Revizyon", "Durum", "Toplam", "Oluşturan", "Tarih"])
        self.doc_table.setModel(self.doc_model)
        self.doc_table.doubleClicked.connect(self._belge_ac)
        dl.addWidget(self.doc_table)

        doc_btn_row = QHBoxLayout()
        self.btn_new_teklif = QPushButton("+ Yeni Teklif")
        self.btn_new_teklif.setObjectName("primary")
        self.btn_new_teklif.clicked.connect(lambda: self._belge_olustur("TEKLİF"))
        self.btn_new_kesif = QPushButton("+ Yeni Keşif")
        self.btn_new_kesif.clicked.connect(lambda: self._belge_olustur("KEŞİF"))
        self.btn_new_tanim = QPushButton("+ Yeni Tanım")
        self.btn_new_tanim.clicked.connect(lambda: self._belge_olustur("TANIM"))
        self.btn_revizyon = QPushButton("Revizyon Aç")
        self.btn_revizyon.clicked.connect(self._revizyon_ac)

        self.btn_gonder = QPushButton("Gönder")
        self.btn_gonder.setObjectName("success")
        self.btn_gonder.clicked.connect(self._belge_gonder)

        self.btn_onayla = QPushButton("Onayla")
        self.btn_onayla.setObjectName("success")
        self.btn_onayla.clicked.connect(self._belge_onayla)

        self.btn_reddet = QPushButton("Reddet")
        self.btn_reddet.setObjectName("danger")
        self.btn_reddet.clicked.connect(self._belge_reddet)

        btn_doc_delete = QPushButton("Sil")
        btn_doc_delete.setObjectName("danger")
        btn_doc_delete.clicked.connect(self._belge_sil)

        doc_btn_row.addWidget(self.btn_new_teklif)
        doc_btn_row.addWidget(self.btn_new_kesif)
        doc_btn_row.addWidget(self.btn_new_tanim)
        doc_btn_row.addStretch()
        doc_btn_row.addWidget(self.btn_gonder)
        doc_btn_row.addWidget(self.btn_onayla)
        doc_btn_row.addWidget(self.btn_reddet)
        doc_btn_row.addWidget(self.btn_revizyon)
        doc_btn_row.addWidget(btn_doc_delete)
        dl.addLayout(doc_btn_row)
        self.tabs.addTab(doc_w, "Dokümanlar")

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
        self.btn_new_teklif.setEnabled(not kapali)
        self.btn_new_kesif.setEnabled(not kapali)
        self.btn_new_tanim.setEnabled(not kapali)

        # Belgeleri yükle
        self._belgeleri_yukle()

        # Özet kartları
        self._ozet_guncelle()

        # Loglar
        self._loglari_yukle()

        # Admin tab görünürlüğü
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

    # ─────────────────────────────────────────
    # BELGE İŞLEMLERİ
    # ─────────────────────────────────────────

    def _belgeleri_yukle(self):
        """Proje belgelerini veritabanından yükler."""
        if not self._proje_id:
            return
        self._belgeler = self.belge_servisi.proje_belgeleri(self._proje_id)
        veri = []
        for b in self._belgeler:
            toplam = self.belge_servisi.maliyet_hesapla(
                b.toplam_maliyet, b.kar_orani, b.kdv_orani)
            veri.append([
                b.tur,
                f"Rev.{b.revizyon_no}",
                b.durum.value,
                f"₺{toplam['genel_toplam']:,.2f}",
                "",  # oluşturan — join ile doldurulabilir
                tarih_formatla(b.olusturma_tarihi, "%d.%m.%Y"),
            ])
        self.doc_model.veri_guncelle(veri)

    def _secili_belge(self):
        """Tabloda seçili belgeyi döndürür."""
        idx = self.doc_table.currentIndex()
        if idx.isValid() and idx.row() < len(self._belgeler):
            return self._belgeler[idx.row()]
        return None

    def _belge_olustur(self, tur: str):
        """Yeni belge oluşturur."""
        if not self._proje_id:
            return
        basarili, mesaj, belge = self.belge_servisi.olustur(
            self._proje_id, tur)
        if basarili:
            self._belgeleri_yukle()
            self._ozet_guncelle()
            # Yeni belgeyi doküman sayfasında aç
            self.open_document.emit(belge.id)
        else:
            QMessageBox.warning(self, "Belge Oluşturulamadı", mesaj)

    def _belge_ac(self):
        """Seçili belgeyi doküman sayfasında açar."""
        belge = self._secili_belge()
        if belge:
            self.open_document.emit(belge.id)

    def _revizyon_ac(self):
        """Seçili belge için yeni revizyon açar."""
        belge = self._secili_belge()
        if not belge:
            QMessageBox.information(self, "Uyarı", "Lütfen bir belge seçin.")
            return
        cevap = QMessageBox.question(
            self, "Yeni Revizyon",
            f"{belge.tur} Rev.{belge.revizyon_no} için\n"
            f"yeni revizyon açmak istiyor musunuz?\n\n"
            f"Mevcut revizyon snapshot olarak korunacaktır.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if cevap == QMessageBox.Yes:
            basarili, mesaj, yeni = self.belge_servisi.revizyon_ac(belge.id)
            if basarili:
                self._belgeleri_yukle()
                self._ozet_guncelle()
                QMessageBox.information(self, "Revizyon", mesaj)
            else:
                QMessageBox.warning(self, "Hata", mesaj)

    def _belge_gonder(self):
        """Seçili belgeyi SENT durumuna geçirir."""
        belge = self._secili_belge()
        if not belge:
            QMessageBox.information(self, "Uyarı", "Lütfen bir belge seçin.")
            return
        basarili, mesaj = self.belge_servisi.gonder(belge.id)
        if basarili:
            self._belgeleri_yukle()
        else:
            QMessageBox.warning(self, "Hata", mesaj)

    def _belge_onayla(self):
        """Seçili belgeyi onaylar. Proje otomatik kapanır."""
        belge = self._secili_belge()
        if not belge:
            QMessageBox.information(self, "Uyarı", "Lütfen bir belge seçin.")
            return
        cevap = QMessageBox.question(
            self, "Belge Onayla",
            f"{belge.tur} Rev.{belge.revizyon_no}\n\n"
            f"Bu belgeyi onaylamak istiyor musunuz?\n"
            f"Onaylanan belge düzenlenemez ve proje otomatik kapatılır.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if cevap == QMessageBox.Yes:
            basarili, mesaj = self.belge_servisi.onayla(belge.id)
            if basarili:
                # Proje kapatılmış olabilir, sayfayı yenile
                self.proje_yukle(self._proje_id)
            else:
                QMessageBox.warning(self, "Hata", mesaj)

    def _belge_reddet(self):
        """Seçili belgeyi reddeder."""
        belge = self._secili_belge()
        if not belge:
            QMessageBox.information(self, "Uyarı", "Lütfen bir belge seçin.")
            return
        basarili, mesaj = self.belge_servisi.reddet(belge.id)
        if basarili:
            self._belgeleri_yukle()
        else:
            QMessageBox.warning(self, "Hata", mesaj)

    def _belge_sil(self):
        """Seçili belgeyi siler."""
        belge = self._secili_belge()
        if not belge:
            QMessageBox.information(self, "Uyarı", "Lütfen bir belge seçin.")
            return
        cevap = QMessageBox.question(
            self, "Belge Sil",
            f"{belge.tur} Rev.{belge.revizyon_no}\n"
            f"Bu belgeyi silmek istediğinize emin misiniz?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if cevap == QMessageBox.Yes:
            basarili, mesaj = self.belge_servisi.sil(belge.id)
            if basarili:
                self._belgeleri_yukle()
                self._ozet_guncelle()
            else:
                QMessageBox.warning(self, "Hata", mesaj)
