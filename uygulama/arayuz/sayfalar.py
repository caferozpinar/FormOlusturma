#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Placeholder Sayfalar — Faz 2+ backend entegrasyonu sırasıyla yapılacak.
Şu an mevcut UI kodundan taşınmış statik demo verileri kullanır.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QDateEdit, QTableView, QTabWidget, QSplitter, QScrollArea,
    QSpinBox, QDoubleSpinBox, QListWidget, QListWidgetItem, QProgressBar,
    QFrame, QCheckBox, QMenu, QGridLayout, QFormLayout
)
from PyQt5.QtCore import Qt, QDate, QSortFilterProxyModel, pyqtSignal
from PyQt5.QtGui import QCursor

from uygulama.arayuz.ui_yardimcilar import (
    SimpleTableModel, make_separator, make_badge,
    make_stat_card, setup_table
)


# ═════════════════════════════════════════════
# PROJECT LIST PAGE
# ═════════════════════════════════════════════

class ProjectListPage(QWidget):
    open_project = pyqtSignal()
    open_sync = pyqtSignal()
    open_admin = pyqtSignal()
    new_project = pyqtSignal()
    cikis_yap = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(16)

        # Filtre Bar
        filter_frame = QFrame()
        filter_frame.setObjectName("toolbar")
        fl = QHBoxLayout(filter_frame)
        fl.setContentsMargins(16, 12, 16, 12)
        fl.setSpacing(12)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Ara: Firma, Konum, Hash...")
        self.search.setMinimumWidth(220)

        self.status_filter = QComboBox()
        self.status_filter.addItems(["Tümü", "ACTIVE", "CLOSED"])

        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDate(QDate.currentDate().addMonths(-6))
        self.date_start.setDisplayFormat("dd.MM.yyyy")

        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDate(QDate.currentDate())
        self.date_end.setDisplayFormat("dd.MM.yyyy")

        fl.addWidget(self.search)
        fl.addWidget(self.status_filter)
        fl.addWidget(QLabel("Başlangıç:"))
        fl.addWidget(self.date_start)
        fl.addWidget(QLabel("Bitiş:"))
        fl.addWidget(self.date_end)
        fl.addStretch()

        self.btn_new_project = QPushButton("+ Yeni Proje")
        self.btn_new_project.setObjectName("primary")
        self.btn_new_project.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_new_project.clicked.connect(self.new_project.emit)

        self.btn_sync = QPushButton("⟳")
        self.btn_sync.setObjectName("syncGreen")
        self.btn_sync.setToolTip("Senkronizasyon")
        self.btn_sync.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_sync.clicked.connect(self.open_sync.emit)

        self.btn_user = QPushButton("☰")
        self.btn_user.setFixedSize(36, 36)
        self.btn_user.setCursor(QCursor(Qt.PointingHandCursor))

        user_menu = QMenu(self)
        user_menu.addAction("Admin Paneli", self.open_admin.emit)
        user_menu.addSeparator()
        user_menu.addAction("Çıkış Yap", self.cikis_yap.emit)
        self.btn_user.setMenu(user_menu)

        fl.addWidget(self.btn_new_project)
        fl.addWidget(self.btn_sync)
        fl.addWidget(self.btn_user)
        layout.addWidget(filter_frame)

        # Proje Tablosu (demo veri)
        self.table = QTableView()
        setup_table(self.table)
        self.table.doubleClicked.connect(lambda: self.open_project.emit())

        headers = ["Firma", "Konum", "Tesis", "Ürün Seti", "Hash",
                    "Durum", "Son İşlem", "Son Kullanıcı"]
        sample = [
            ["Acme Corp", "İstanbul", "Tesis-A", "Set-1", "a3f9c2",
             "ACTIVE", "12.02.2026", "admin"],
            ["Beta Ltd", "Ankara", "Tesis-B", "Set-2", "b7d1e4",
             "CLOSED", "10.02.2026", "editor1"],
            ["Gamma AŞ", "İzmir", "Tesis-C", "Set-3", "c5a8f1",
             "ACTIVE", "11.02.2026", "admin"],
        ]
        model = SimpleTableModel(headers, sample)
        proxy = QSortFilterProxyModel()
        proxy.setSourceModel(model)
        self.table.setModel(proxy)
        layout.addWidget(self.table)


# ═════════════════════════════════════════════
# PROJECT DETAIL PAGE
# ═════════════════════════════════════════════

class ProjectDetailPage(QWidget):
    go_back = pyqtSignal()
    open_document = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(16)

        # Header
        header = QFrame()
        header.setObjectName("toolbar")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 12, 16, 12)

        left = QVBoxLayout()
        left.setSpacing(4)
        title = QLabel("Acme Corp – İstanbul – Tesis-A")
        title.setObjectName("title")
        title.setStyleSheet("font-size: 18px;")
        left.addWidget(title)

        hr = QHBoxLayout()
        hr.addWidget(QLabel("Hash: a3f9c2"))
        btn_copy = QPushButton("Kopyala")
        btn_copy.setFixedHeight(28)
        btn_copy.setStyleSheet("font-size: 11px; padding: 2px 10px;")
        hr.addWidget(btn_copy)
        hr.addStretch()
        left.addLayout(hr)
        left.addWidget(make_badge("ACTIVE", "active"), alignment=Qt.AlignLeft)

        right = QVBoxLayout()
        right.setAlignment(Qt.AlignTop)
        br = QHBoxLayout()
        br.setSpacing(8)
        br.addWidget(QPushButton("Düzenle"))
        d = QPushButton("Projeyi Kapat")
        d.setObjectName("danger")
        br.addWidget(d)
        btn_back = QPushButton("← Geri")
        btn_back.clicked.connect(self.go_back.emit)
        br.addWidget(btn_back)
        right.addLayout(br)

        hl.addLayout(left, 1)
        hl.addLayout(right)
        layout.addWidget(header)

        # Tabs
        tabs = QTabWidget()

        # Dokümanlar
        doc_w = QWidget()
        dl = QVBoxLayout(doc_w)
        dl.setContentsMargins(16, 16, 16, 16)
        dl.setSpacing(12)
        doc_t = QTableView()
        setup_table(doc_t)
        doc_t.setModel(SimpleTableModel(
            ["Tür", "Revizyon", "Durum", "Toplam", "Oluşturan", "Tarih"],
            [["TEKLİF", "Rev.3", "ONAYLANDI", "₺125,000", "admin", "10.02.2026"],
             ["KEŞİF", "Rev.1", "TASLAK", "₺98,500", "editor1", "11.02.2026"]]))
        doc_t.doubleClicked.connect(lambda: self.open_document.emit())
        dl.addWidget(doc_t)
        dbr = QHBoxLayout()
        nt = QPushButton("+ Yeni Teklif")
        nt.setObjectName("primary")
        nt.clicked.connect(self.open_document.emit)
        dbr.addWidget(nt)
        dbr.addWidget(QPushButton("+ Yeni Keşif"))
        dbr.addWidget(QPushButton("+ Yeni Tanım"))
        dbr.addStretch()
        dl.addLayout(dbr)
        tabs.addTab(doc_w, "Dokümanlar")

        # Özet
        sw = QWidget()
        sl = QVBoxLayout(sw)
        sl.setContentsMargins(16, 16, 16, 16)
        g = QGridLayout()
        g.setSpacing(16)
        g.addWidget(make_stat_card("12", "Toplam Doküman"), 0, 0)
        g.addWidget(make_stat_card("34", "Toplam Revizyon"), 0, 1)
        g.addWidget(make_stat_card("8", "Onaylanan"), 0, 2)
        g.addWidget(make_stat_card("%18.5", "Ort. Kâr Oranı"), 1, 0)
        sl.addLayout(g)
        sl.addStretch()
        tabs.addTab(sw, "Özet")

        # Loglar
        lw = QWidget()
        ll = QVBoxLayout(lw)
        ll.setContentsMargins(16, 16, 16, 16)
        lt = QTableView()
        setup_table(lt)
        lt.setModel(SimpleTableModel(
            ["Tarih", "Kullanıcı", "İşlem"],
            [["12.02.2026 14:30", "admin", "Proje oluşturuldu"],
             ["12.02.2026 15:00", "editor1", "Teklif eklendi (Rev.1)"]]))
        ll.addWidget(lt)
        tabs.addTab(lw, "Loglar (Admin)")

        layout.addWidget(tabs)


# ═════════════════════════════════════════════
# DOCUMENT PAGE
# ═════════════════════════════════════════════

class DocumentPage(QWidget):
    go_back = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        ml = QVBoxLayout(self)
        ml.setContentsMargins(16, 12, 16, 12)
        ml.setSpacing(8)

        # Üst bar
        tb = QHBoxLayout()
        t = QLabel("Doküman Düzenleme")
        t.setObjectName("sectionTitle")
        btn_back = QPushButton("← Geri")
        btn_back.clicked.connect(self.go_back.emit)
        btn_save = QPushButton("Kaydet")
        btn_save.setObjectName("primary")
        tb.addWidget(t)
        tb.addStretch()
        tb.addWidget(btn_save)
        tb.addWidget(btn_back)
        ml.addLayout(tb)

        # Splitter
        splitter = QSplitter(Qt.Horizontal)

        # Sol: Ürünler
        lw = QWidget()
        ll = QVBoxLayout(lw)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(8)
        ll.addWidget(QLabel("Ürünler"))
        pt = QTableView()
        setup_table(pt)
        pt.setModel(SimpleTableModel(
            ["Ürün Kodu", "Miktar", "Toplam"],
            [["PRD-001", "5", "₺12,500"], ["PRD-002", "10", "₺8,300"]]))
        ll.addWidget(pt)
        pbr = QHBoxLayout()
        ap = QPushButton("+ Ürün Ekle")
        ap.setObjectName("primary")
        rp = QPushButton("− Ürün Çıkar")
        rp.setObjectName("danger")
        pbr.addWidget(ap)
        pbr.addWidget(rp)
        pbr.addStretch()
        ll.addLayout(pbr)
        splitter.addWidget(lw)

        # Sağ: Dinamik alanlar
        rw = QWidget()
        rl = QVBoxLayout(rw)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)
        rl.addWidget(QLabel("Seçili Ürün: PRD-001"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        sc = QWidget()
        form = QFormLayout(sc)
        form.setSpacing(12)
        form.setContentsMargins(8, 8, 8, 8)

        f = QDoubleSpinBox()
        f.setRange(0, 999999)
        f.setDecimals(2)
        f.setSuffix(" m²")
        form.addRow("Alan (m²):", f)
        i = QSpinBox()
        i.setRange(0, 9999)
        form.addRow("Adet:", i)
        form.addRow("Montaj:", QCheckBox("Montaj dahil"))
        tx = QLineEdit()
        tx.setPlaceholderText("Açıklama giriniz...")
        form.addRow("Açıklama:", tx)
        ch = QComboBox()
        ch.addItems(["Seçiniz...", "Tip A", "Tip B", "Tip C"])
        form.addRow("Malzeme Tipi:", ch)

        scroll.setWidget(sc)
        rl.addWidget(scroll)

        # Alt kalemler
        rl.addWidget(QLabel("Alt Kalemler"))
        at = QTableView()
        setup_table(at)
        at.setModel(SimpleTableModel(
            ["Dahil", "Alt Kalem Adı", "Miktar", "Birim Fiyat", "Toplam"],
            [["✓", "Montaj İşçiliği", "5", "₺500", "₺2,500"],
             ["✓", "Nakliye", "1", "₺1,200", "₺1,200"]]))
        at.setMaximumHeight(160)
        rl.addWidget(at)
        splitter.addWidget(rw)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        ml.addWidget(splitter, 1)

        # Toplam
        ml.addWidget(make_separator())
        tf = QFrame()
        tf.setObjectName("card")
        tl = QGridLayout(tf)
        tl.setSpacing(8)
        tl.setContentsMargins(16, 12, 16, 12)
        tl.setColumnStretch(0, 1)
        ls = "font-weight: 500; color: #374151;"
        vs = "font-weight: 600; color: #1E1E2E; font-size: 14px;"

        r = 0
        for lbl, val in [("Toplam Maliyet:", "₺65,800.00"),
                          ("Kâr Tutarı:", "₺12,173.00"),
                          ("Ara Toplam:", "₺77,973.00"),
                          ("KDV Tutarı:", "₺15,594.60")]:
            l = QLabel(lbl)
            l.setStyleSheet(ls)
            l.setAlignment(Qt.AlignRight)
            v = QLabel(val)
            v.setStyleSheet(vs)
            tl.addWidget(l, r, 1)
            tl.addWidget(v, r, 2)
            r += 1

        tl.addWidget(make_separator(), r, 0, 1, 3)
        r += 1
        gl = QLabel("Genel Toplam:")
        gl.setStyleSheet("font-weight: 700; font-size: 16px;")
        gl.setAlignment(Qt.AlignRight)
        gv = QLabel("₺93,567.60")
        gv.setStyleSheet("font-weight: 700; color: #3B82F6; font-size: 18px;")
        tl.addWidget(gl, r, 1)
        tl.addWidget(gv, r, 2)
        ml.addWidget(tf)


# ═════════════════════════════════════════════
# SYNC PAGE
# ═════════════════════════════════════════════

class SyncPage(QWidget):
    go_back = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setObjectName("card")
        card.setFixedWidth(650)
        cl = QVBoxLayout(card)
        cl.setSpacing(16)
        cl.setContentsMargins(32, 32, 32, 32)

        t = QLabel("Senkronizasyon")
        t.setObjectName("title")
        t.setAlignment(Qt.AlignCenter)
        cl.addWidget(t)

        self.status_label = QLabel("Senkronizasyon tamamlandı.")
        self.status_label.setObjectName("subtitle")
        self.status_label.setAlignment(Qt.AlignCenter)
        cl.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setValue(100)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        cl.addWidget(self.progress)

        cl.addSpacing(8)
        cl.addWidget(QLabel("Çakışmalar"))

        ct = QTableView()
        setup_table(ct)
        ct.setModel(SimpleTableModel(
            ["Çakışma Türü", "Yerel", "Uzak", "Aksiyon"],
            [["Doküman Güncelleme", "editor1 / 12.02", "admin / 12.02", "Yerel Koru"]]))
        ct.setMaximumHeight(120)
        cl.addWidget(ct)

        bc = QPushButton("Kapat")
        bc.setObjectName("primary")
        bc.clicked.connect(self.go_back.emit)
        cl.addWidget(bc)

        outer.addWidget(card)


# ═════════════════════════════════════════════
# ADMIN PANEL PAGE
# ═════════════════════════════════════════════

# AdminPanelPage artık admin_sayfa.py'de backend bağlantılı olarak tanımlı.
