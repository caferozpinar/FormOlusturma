#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proje Listesi Sayfası — Backend entegreli.
Filtreleme, arama, CRUD işlemleri.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QDateEdit, QTableView, QFrame, QMenu, QMessageBox,
    QApplication
)
from PyQt5.QtCore import Qt, QDate, QTimer, pyqtSignal
from PyQt5.QtGui import QCursor

from uygulama.arayuz.ui_yardimcilar import SimpleTableModel, setup_table
from uygulama.domain.modeller import ProjeDurumu
from uygulama.ortak.app_state import app_state
from uygulama.ortak.yardimcilar import tarih_sadece_gun


class ProjectListPage(QWidget):
    """Proje listesi sayfası — veritabanı bağlantılı."""

    open_project = pyqtSignal(str)      # proje_id gönderir
    open_sync = pyqtSignal()
    open_admin = pyqtSignal()
    open_analitik = pyqtSignal()
    cikis_yap = pyqtSignal()

    def __init__(self, proje_servisi, parent=None):
        super().__init__(parent)
        self.proje_servisi = proje_servisi
        self._projeler = []  # mevcut proje listesi cache
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(16)

        # ── Kullanıcı Bilgi Satırı ──
        info_bar = QHBoxLayout()
        self.kullanici_label = QLabel("")
        self.kullanici_label.setObjectName("subtitle")
        self.istatistik_label = QLabel("")
        self.istatistik_label.setObjectName("subtitle")
        info_bar.addWidget(self.kullanici_label)
        info_bar.addStretch()
        info_bar.addWidget(self.istatistik_label)
        layout.addLayout(info_bar)

        # ── Filtre Bar ──
        filter_frame = QFrame()
        filter_frame.setObjectName("toolbar")
        fl = QHBoxLayout(filter_frame)
        fl.setContentsMargins(16, 12, 16, 12)
        fl.setSpacing(12)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Ara: Firma, Konum, Hash...")
        self.search.setMinimumWidth(220)
        self.search.textChanged.connect(self._filtre_degisti)

        self.status_filter = QComboBox()
        self.status_filter.addItems(["Tümü", "ACTIVE", "CLOSED"])
        self.status_filter.currentIndexChanged.connect(self._filtre_degisti)

        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDate(QDate.currentDate().addMonths(-6))
        self.date_start.setDisplayFormat("dd.MM.yyyy")
        self.date_start.dateChanged.connect(self._filtre_degisti)

        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDate(QDate.currentDate())
        self.date_end.setDisplayFormat("dd.MM.yyyy")
        self.date_end.dateChanged.connect(self._filtre_degisti)

        fl.addWidget(self.search)
        fl.addWidget(self.status_filter)
        fl.addWidget(QLabel("Başlangıç:"))
        fl.addWidget(self.date_start)
        fl.addWidget(QLabel("Bitiş:"))
        fl.addWidget(self.date_end)
        fl.addStretch()

        # Yeni Proje butonu
        self.btn_new_project = QPushButton("+ Yeni Proje")
        self.btn_new_project.setObjectName("primary")
        self.btn_new_project.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_new_project.clicked.connect(self._yeni_proje)

        # Sync butonu
        self.btn_sync = QPushButton("⟳")
        self.btn_sync.setObjectName("syncGreen")
        self.btn_sync.setToolTip("Senkronizasyon")
        self.btn_sync.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_sync.clicked.connect(self.open_sync.emit)

        # Kullanıcı menüsü
        self.btn_user = QPushButton("☰")
        self.btn_user.setFixedSize(36, 36)
        self.btn_user.setCursor(QCursor(Qt.PointingHandCursor))
        user_menu = QMenu(self)
        self.admin_action = user_menu.addAction(
            "Admin Paneli", self.open_admin.emit)
        user_menu.addAction("📊 Analitik", self.open_analitik.emit)
        user_menu.addSeparator()
        user_menu.addAction("Çıkış Yap", self.cikis_yap.emit)
        self.btn_user.setMenu(user_menu)

        fl.addWidget(self.btn_new_project)
        fl.addWidget(self.btn_sync)
        fl.addWidget(self.btn_user)
        layout.addWidget(filter_frame)

        # ── Proje Tablosu ──
        self.table = QTableView()
        setup_table(self.table)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        self.table.doubleClicked.connect(self._proje_ac)

        self.headers = ["Firma", "Konum", "Tesis", "Ürün Seti", "Hash",
                        "Durum", "Oluşturma", "Oluşturan"]
        self.model = SimpleTableModel(self.headers)
        self.table.setModel(self.model)
        layout.addWidget(self.table)

        # Debounce timer (arama sırasında her tuşta sorgu atmamak için)
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(300)
        self._debounce_timer.timeout.connect(self._verileri_yukle)

    # ─────────────────────────────────────────
    # VERİ YÜKLEME
    # ─────────────────────────────────────────

    def sayfa_gosterildi(self):
        """Sayfa görüntülendiğinde çağrılır — verileri yeniler."""
        self._kullanici_guncelle()
        self._verileri_yukle()

    def _kullanici_guncelle(self):
        """Üst bilgi çubuğunu günceller."""
        state = app_state()
        if state.aktif_kullanici:
            k = state.aktif_kullanici
            self.kullanici_label.setText(
                f"👤 {k.kullanici_adi} ({k.rol.value})")
            # Admin paneli sadece Admin'e görünsün
            self.admin_action.setVisible(state.admin_mi)
        else:
            self.kullanici_label.setText("")

    def _verileri_yukle(self):
        """Filtrelere göre projeleri veritabanından yükler."""
        # Durum filtresi
        durum = None
        durum_idx = self.status_filter.currentIndex()
        if durum_idx == 1:
            durum = ProjeDurumu.ACTIVE
        elif durum_idx == 2:
            durum = ProjeDurumu.CLOSED

        # Arama
        arama = self.search.text().strip()

        # Tarih
        baslangic = self.date_start.date().toString("yyyy-MM-dd")
        bitis = self.date_end.date().toString("yyyy-MM-dd") + "T23:59:59"

        # Verileri çek
        self._projeler = self.proje_servisi.listele(
            durum=durum, arama=arama,
            baslangic_tarihi=baslangic, bitis_tarihi=bitis
        )

        # Tabloyu güncelle
        tablo_verisi = []
        for p in self._projeler:
            tablo_verisi.append([
                p.firma,
                p.konum,
                p.tesis,
                p.urun_seti,
                p.hash_kodu,
                p.durum.value,
                tarih_sadece_gun(p.olusturma_tarihi),
                "",  # Oluşturan — sonra join ile doldurulabilir
            ])
        self.model.veri_guncelle(tablo_verisi)

        # İstatistikler
        stats = self.proje_servisi.istatistikler()
        self.istatistik_label.setText(
            f"Toplam: {stats['toplam']}  |  "
            f"Aktif: {stats['aktif']}  |  "
            f"Kapalı: {stats['kapali']}"
        )

    def _filtre_degisti(self):
        """Filtre değiştiğinde debounce ile veri yükler."""
        self._debounce_timer.start()

    # ─────────────────────────────────────────
    # PROJE İŞLEMLERİ
    # ─────────────────────────────────────────

    def _yeni_proje(self):
        """Yeni proje dialog'unu açar."""
        from uygulama.arayuz.proje_dialog import ProjeDialog
        dialog = ProjeDialog(self.proje_servisi, parent=self)
        if dialog.exec_() and dialog.sonuc_proje:
            self._verileri_yukle()
            # Yeni projeyi direkt aç
            self.open_project.emit(dialog.sonuc_proje.id)

    def _proje_ac(self):
        """Tabloda çift tıklanan projeyi açar."""
        idx = self.table.currentIndex()
        if idx.isValid() and idx.row() < len(self._projeler):
            proje = self._projeler[idx.row()]
            self.open_project.emit(proje.id)

    def _secili_proje(self):
        """Tabloda seçili projeyi döndürür."""
        idx = self.table.currentIndex()
        if idx.isValid() and idx.row() < len(self._projeler):
            return self._projeler[idx.row()]
        return None

    def _context_menu(self, pos):
        """Sağ tık menüsü."""
        proje = self._secili_proje()
        if not proje:
            return

        menu = QMenu(self)

        menu.addAction("Projeyi Aç", lambda: self.open_project.emit(proje.id))

        # Hash kopyala
        def _hash_kopyala():
            clipboard = QApplication.clipboard()
            clipboard.setText(proje.hash_kodu)

        menu.addAction("Hash Kopyala", _hash_kopyala)
        menu.addSeparator()

        # Düzenle
        menu.addAction("Düzenle", lambda: self._proje_duzenle(proje))

        # Durum değiştir
        if proje.durum == ProjeDurumu.ACTIVE:
            menu.addAction("Projeyi Kapat", lambda: self._proje_kapat(proje))
        else:
            state = app_state()
            if state.admin_mi:
                menu.addAction("Aktifleştir", lambda: self._proje_aktifle(proje))

        menu.addSeparator()
        sil_action = menu.addAction("Sil", lambda: self._proje_sil(proje))
        sil_action.setProperty("objectName", "danger")

        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def _proje_duzenle(self, proje):
        """Proje düzenleme dialog'u."""
        from uygulama.arayuz.proje_dialog import ProjeDialog
        dialog = ProjeDialog(self.proje_servisi, proje=proje, parent=self)
        if dialog.exec_():
            self._verileri_yukle()

    def _proje_kapat(self, proje):
        """Proje kapatma onay ve işlemi."""
        cevap = QMessageBox.question(
            self, "Proje Kapat",
            f"{proje.firma} – {proje.hash_kodu}\n\n"
            f"Bu projeyi kapatmak istediğinize emin misiniz?\n"
            f"Kapalı projede yeni belge oluşturulamaz.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if cevap == QMessageBox.Yes:
            basarili, mesaj = self.proje_servisi.kapat(proje.id)
            if not basarili:
                QMessageBox.warning(self, "Hata", mesaj)
            self._verileri_yukle()

    def _proje_aktifle(self, proje):
        """Projeyi tekrar aktifleştir."""
        basarili, mesaj = self.proje_servisi.aktifle(proje.id)
        if not basarili:
            QMessageBox.warning(self, "Hata", mesaj)
        self._verileri_yukle()

    def _proje_sil(self, proje):
        """Proje silme onay ve işlemi."""
        cevap = QMessageBox.question(
            self, "Proje Sil",
            f"{proje.firma} – {proje.hash_kodu}\n\n"
            f"Bu projeyi silmek istediğinize emin misiniz?\n"
            f"Bu işlem geri alınamaz.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if cevap == QMessageBox.Yes:
            basarili, mesaj = self.proje_servisi.sil(proje.id)
            if not basarili:
                QMessageBox.warning(self, "Hata", mesaj)
            self._verileri_yukle()
