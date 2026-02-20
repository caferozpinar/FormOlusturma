#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teklif/Keşif Yönetim Sayfası.
Stacked layout:
  Seviye 1 — Liste: Proje altındaki tüm teklif/keşifler
  Seviye 2 — Detay: Ürün-alt kalem ağacı + parametre girişi + fiyat
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox, QLineEdit,
    QStackedWidget, QScrollArea, QMessageBox, QSplitter,
    QGridLayout, QSizePolicy, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont

from uygulama.ortak.yardimcilar import logger_olustur

logger = logger_olustur("teklif_sayfa")

# ─── Yardımcılar ───

def _setup_table(table, row_h=34):
    table.verticalHeader().setDefaultSectionSize(row_h)
    table.verticalHeader().setVisible(False)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.setStyleSheet("""
        QTableWidget { gridline-color: #E0E0E0; border: 1px solid #ddd; }
        QTableWidget::item { padding: 4px; }
        QTableWidget::item:selected { background: #BBDEFB; color: #000; }
    """)


# ═════════════════════════════════════════════
# ANA KONTEYNER — Stacked
# ═════════════════════════════════════════════

class TeklifSayfasi(QWidget):
    go_back = pyqtSignal()

    def __init__(self, teklif_srv=None, em_repo=None, parent=None):
        super().__init__(parent)
        self.teklif_srv = teklif_srv
        self.em_repo = em_repo
        self._proje_id = None
        self._build()

    def _build(self):
        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        self.liste = TeklifListeWidget(self.teklif_srv)
        self.detay = TeklifDetayWidget(self.teklif_srv, self.em_repo)
        self.stack.addWidget(self.liste)
        self.stack.addWidget(self.detay)
        lo.addWidget(self.stack)
        self.liste.teklif_ac.connect(self._ac)
        self.detay.geri.connect(self._don)

    def yukle(self, proje_id: str):
        self._proje_id = proje_id
        self.liste.yukle(proje_id)
        self.stack.setCurrentIndex(0)

    def _ac(self, tid):
        self.detay.yukle(tid)
        self.stack.setCurrentIndex(1)

    def _don(self):
        if self._proje_id:
            self.liste.yukle(self._proje_id)
        self.stack.setCurrentIndex(0)


# ═════════════════════════════════════════════
# SEVİYE 1 — TEKLİF LİSTESİ
# ═════════════════════════════════════════════

class TeklifListeWidget(QWidget):
    teklif_ac = pyqtSignal(str)

    def __init__(self, teklif_srv=None, parent=None):
        super().__init__(parent)
        self.srv = teklif_srv
        self._proje_id = None
        self._data = []
        self._build()

    def _build(self):
        lo = QVBoxLayout(self)
        lo.setContentsMargins(16, 12, 16, 12)
        lo.setSpacing(10)

        # ── Başlık satırı ──
        bar = QHBoxLayout()
        lbl = QLabel("Teklifler / Keşifler")
        lbl.setStyleSheet("font-size: 14px; font-weight: bold;")
        bar.addWidget(lbl)
        bar.addStretch()

        bar.addWidget(QLabel("Para Birimi:"))
        self.para_cmb = QComboBox()
        self.para_cmb.setFixedWidth(155)
        self.para_cmb.setFixedHeight(28)
        from uygulama.altyapi.teklif_repo import PARA_BIRIMLERI
        for kod, sembol, ad in PARA_BIRIMLERI:
            self.para_cmb.addItem(f"{sembol}  {ad}", kod)
        bar.addWidget(self.para_cmb)
        bar.addSpacing(16)

        for text, tur, obj in [
            ("+ Yeni Teklif", "TEKLİF", "primary"),
            ("+ Yeni Keşif", "KEŞİF", None),
        ]:
            b = QPushButton(text)
            b.setFixedHeight(28)
            if obj:
                b.setObjectName(obj)
            b.clicked.connect(lambda _, t=tur: self._olustur(t))
            bar.addWidget(b)

        lo.addLayout(bar)

        # ── Tablo ──
        self.tbl = QTableWidget()
        _setup_table(self.tbl, 34)
        self.tbl.setColumnCount(6)
        self.tbl.setHorizontalHeaderLabels(
            ["Tür", "Başlık", "Rev.", "Para", "Toplam", "Durum"])
        self.tbl.setColumnWidth(0, 65)
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tbl.setColumnWidth(2, 42)
        self.tbl.setColumnWidth(3, 50)
        self.tbl.setColumnWidth(4, 110)
        self.tbl.setColumnWidth(5, 90)
        self.tbl.doubleClicked.connect(self._dbl)
        lo.addWidget(self.tbl)

        # ── Alt butonlar ──
        bbar = QHBoxLayout()
        for txt, slot, obj in [
            ("Aç", self._secili_ac, None),
            ("Sil", self._sil, "danger"),
        ]:
            b = QPushButton(txt)
            b.setFixedSize(60, 26)
            if obj:
                b.setObjectName(obj)
            b.clicked.connect(slot)
            bbar.addWidget(b)
        bbar.addStretch()
        lo.addLayout(bbar)

    # ── Veri ──

    def yukle(self, proje_id):
        self._proje_id = proje_id
        if not self.srv:
            return
        self._data = self.srv.proje_teklifleri(proje_id)
        self.tbl.setRowCount(len(self._data))
        durum_renk = {
            "TASLAK": "#757575", "GONDERILDI": "#1565C0",
            "ONAYLANDI": "#2E7D32", "REDDEDILDI": "#C62828",
        }
        for i, t in enumerate(self._data):
            s = self.srv.para_birimi_sembol(t["para_birimi"])
            self.tbl.setItem(i, 0, QTableWidgetItem(t["tur"]))
            self.tbl.setItem(i, 1, QTableWidgetItem(t["baslik"]))
            self.tbl.setItem(i, 2, QTableWidgetItem(str(t["revizyon_no"])))
            self.tbl.setItem(i, 3, QTableWidgetItem(s))
            it_t = QTableWidgetItem(f"{s}{t['toplam_fiyat']:,.2f}")
            it_t.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.tbl.setItem(i, 4, it_t)
            it_d = QTableWidgetItem(t["durum"])
            it_d.setForeground(QColor(durum_renk.get(t["durum"], "#333")))
            self.tbl.setItem(i, 5, it_d)

    def _sel(self):
        r = self.tbl.currentRow()
        return self._data[r] if 0 <= r < len(self._data) else None

    def _dbl(self):
        t = self._sel()
        if t:
            self.teklif_ac.emit(t["id"])

    def _secili_ac(self):
        t = self._sel()
        if t:
            self.teklif_ac.emit(t["id"])

    def _olustur(self, tur):
        if not self._proje_id or not self.srv:
            return
        para = self.para_cmb.currentData() or "TRY"
        ok, msg, tid = self.srv.teklif_olustur(self._proje_id, tur, para)
        if ok:
            self.yukle(self._proje_id)
            self.teklif_ac.emit(tid)
        else:
            QMessageBox.warning(self, "Hata", msg)

    def _sil(self):
        t = self._sel()
        if not t:
            return
        if QMessageBox.question(
                self, "Sil",
                f"'{t['baslik']}' silinsin mi?",
                QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            self.srv.sil(t["id"])
            self.yukle(self._proje_id)


# ═════════════════════════════════════════════
# SEVİYE 2 — TEKLİF DETAY
#
# Layout:
# ┌─────────────────────────────────────────────┐
# │  ← Geri   TEKLİF Rev.1           ₺12,500   │  header
# ├─────────────────────────────────────────────┤
# │ Ürün / Alt Kalem Listesi          [Hesapla] │
# │ ┌───┬──────────────┬────┬────────┬────────┐ │
# │ │ ✓ │ Ad           │Mkt.│ Birim  │ Toplam │ │  kalem tablosu
# │ │   │  📦 Klima    │    │        │        │ │
# │ │ ☑ │   Kompresör  │ 1  │ ₺1,725 │ ₺1,725 │ │
# │ │ ☐ │   Evaporatör │ 1  │  —     │  —     │ │
# │ └───┴──────────────┴────┴────────┴────────┘ │
# ├─────────────────────────────────────────────┤
# │ Parametreler — Kompresör                     │
# │ ┌──────────┬────────┬──────────┬──────────┐ │
# │ │ Ağırlık: │ [100]  │ BirimFyt: │ [10.00] │ │  2-sütun grid
# │ │ Güç:     │ [5.00] │          │         │ │
# │ └──────────┴────────┴──────────┴──────────┘ │
# └─────────────────────────────────────────────┘
# ═════════════════════════════════════════════

class TeklifDetayWidget(QWidget):
    geri = pyqtSignal()

    def __init__(self, teklif_srv=None, em_repo=None, parent=None):
        super().__init__(parent)
        self.srv = teklif_srv
        self.em_repo = em_repo
        self._tid = None
        self._teklif = None
        self._kalemler = []
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 10, 16, 10)
        root.setSpacing(0)

        # ── HEADER ──
        hdr = QHBoxLayout()
        hdr.setSpacing(10)
        btn_geri = QPushButton("← Listeye Dön")
        btn_geri.setFixedSize(110, 28)
        btn_geri.clicked.connect(self.geri.emit)
        hdr.addWidget(btn_geri)

        self.lbl_baslik = QLabel()
        self.lbl_baslik.setStyleSheet("font-size: 14px; font-weight: bold;")
        hdr.addWidget(self.lbl_baslik)

        self.lbl_durum = QLabel()
        self.lbl_durum.setStyleSheet(
            "font-size: 11px; padding: 2px 8px; border-radius: 3px;"
            "background: #E3F2FD; color: #1565C0;")
        hdr.addWidget(self.lbl_durum)
        hdr.addStretch()

        self.lbl_toplam = QLabel()
        self.lbl_toplam.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #2E7D32;"
            "padding: 4px 14px; background: #E8F5E9; border-radius: 4px;")
        hdr.addWidget(self.lbl_toplam)
        root.addLayout(hdr)
        root.addSpacing(8)

        # ── SPLITTER: Üst=Kalem tablo | Alt=Param form ──
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setHandleWidth(5)

        # ─ ÜST: Kalem tablosu ─
        ust = QWidget()
        ul = QVBoxLayout(ust)
        ul.setContentsMargins(0, 0, 0, 0)
        ul.setSpacing(6)

        # Başlık + Hesapla butonu aynı satırda
        ust_bar = QHBoxLayout()
        ust_lbl = QLabel("Ürün ve Alt Kalem Listesi")
        ust_lbl.setStyleSheet("font-weight: bold; color: #444;")
        ust_bar.addWidget(ust_lbl)
        ust_bar.addStretch()
        self.btn_hesapla = QPushButton("Fiyatları Hesapla")
        self.btn_hesapla.setObjectName("primary")
        self.btn_hesapla.setFixedSize(140, 28)
        self.btn_hesapla.clicked.connect(self._hesapla)
        ust_bar.addWidget(self.btn_hesapla)
        ul.addLayout(ust_bar)

        self.kalem_tbl = QTableWidget()
        _setup_table(self.kalem_tbl, 32)
        self.kalem_tbl.setColumnCount(5)
        self.kalem_tbl.setHorizontalHeaderLabels(
            ["Seç", "Ürün / Alt Kalem", "Miktar", "Birim Fiyat", "Toplam Fiyat"])
        self.kalem_tbl.setColumnWidth(0, 38)
        self.kalem_tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.kalem_tbl.setColumnWidth(2, 65)
        self.kalem_tbl.setColumnWidth(3, 105)
        self.kalem_tbl.setColumnWidth(4, 105)
        self.kalem_tbl.clicked.connect(self._kalem_tiklandi)
        ul.addWidget(self.kalem_tbl)
        self.splitter.addWidget(ust)

        # ─ ALT: Parametre giriş paneli ─
        alt = QWidget()
        al = QVBoxLayout(alt)
        al.setContentsMargins(0, 4, 0, 0)
        al.setSpacing(4)

        self.lbl_param_baslik = QLabel("Bir kalem seçerek parametrelerini görüntüleyin")
        self.lbl_param_baslik.setStyleSheet(
            "font-weight: bold; color: #444; padding: 2px 0;")
        al.addWidget(self.lbl_param_baslik)

        # Çerçeveli scroll alan
        self.param_scroll = QScrollArea()
        self.param_scroll.setWidgetResizable(True)
        self.param_scroll.setMinimumHeight(80)
        self.param_scroll.setStyleSheet(
            "QScrollArea { border: 1px solid #ddd; border-radius: 3px;"
            "background: #FAFAFA; }")

        self.param_w = QWidget()
        self.param_grid = QGridLayout(self.param_w)
        self.param_grid.setContentsMargins(12, 10, 12, 10)
        self.param_grid.setHorizontalSpacing(12)
        self.param_grid.setVerticalSpacing(8)
        # 4 kolon: label1 widget1 label2 widget2
        self.param_grid.setColumnMinimumWidth(0, 120)
        self.param_grid.setColumnMinimumWidth(2, 120)
        self.param_grid.setColumnStretch(1, 1)
        self.param_grid.setColumnStretch(3, 1)
        self.param_scroll.setWidget(self.param_w)
        al.addWidget(self.param_scroll)
        self.splitter.addWidget(alt)

        self.splitter.setSizes([340, 180])
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)
        root.addWidget(self.splitter)

    # ─────────────────────────────────────
    # VERİ YÜKLEME
    # ─────────────────────────────────────

    def yukle(self, teklif_id):
        self._tid = teklif_id
        self._teklif = self.srv.getir(teklif_id) if self.srv else None
        if not self._teklif:
            return
        s = self.srv.para_birimi_sembol(self._teklif["para_birimi"])
        self.lbl_baslik.setText(self._teklif["baslik"])
        self.lbl_durum.setText(self._teklif["durum"])
        self._toplam_goster()
        self._kalem_yukle()
        self._param_temizle()

    def _toplam_goster(self):
        if not self._teklif:
            return
        s = self.srv.para_birimi_sembol(self._teklif["para_birimi"])
        self.lbl_toplam.setText(f"Toplam: {s}{self._teklif['toplam_fiyat']:,.2f}")

    def _kalem_yukle(self):
        if not self.srv:
            return
        self._kalemler = self.srv.zenginlestirilmis_kalemler(self._tid)
        s = self.srv.para_birimi_sembol(
            self._teklif["para_birimi"]) if self._teklif else "₺"

        self.kalem_tbl.setRowCount(len(self._kalemler))
        for i, k in enumerate(self._kalemler):
            is_urun = k["tip"] == "urun"

            # ── Kolon 0: Checkbox (ortalanmış) ──
            cw = QWidget()
            cl = QHBoxLayout(cw)
            cl.setContentsMargins(0, 0, 0, 0)
            cl.setAlignment(Qt.AlignCenter)
            cb = QCheckBox()
            cb.setChecked(bool(k["secili_mi"]))
            if is_urun:
                cb.setEnabled(False)
            else:
                cb.stateChanged.connect(
                    lambda st, kid=k["id"]: self._secim(kid, st))
            cl.addWidget(cb)
            self.kalem_tbl.setCellWidget(i, 0, cw)

            # ── Kolon 1: Ad (ürün bold+arkaplan, alt kalem girintili) ──
            if is_urun:
                it = QTableWidgetItem(f"  {k['urun_kod']} — {k['urun_ad']}")
                f = it.font()
                f.setBold(True)
                it.setFont(f)
                it.setBackground(QColor(235, 242, 250))
            else:
                it = QTableWidgetItem(f"      {k['alt_kalem_ad']}")
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            self.kalem_tbl.setItem(i, 1, it)

            # ── Kolon 2: Miktar (alt kalem = SpinBox, ürün = boş) ──
            if not is_urun:
                sp = QSpinBox()
                sp.setRange(1, 9999)
                sp.setValue(k["miktar"])
                sp.setFixedSize(58, 24)
                sp.setAlignment(Qt.AlignCenter)
                sp.valueChanged.connect(
                    lambda v, kid=k["id"]: self._miktar(kid, v))
                self.kalem_tbl.setCellWidget(i, 2, sp)
            else:
                self.kalem_tbl.setItem(i, 2, QTableWidgetItem(""))

            # ── Kolon 3-4: Birim fiyat, Toplam ──
            if not is_urun and k["birim_fiyat"]:
                for col, val in [(3, k["birim_fiyat"]), (4, k["toplam_fiyat"])]:
                    it_f = QTableWidgetItem(f"{s}{val:,.2f}")
                    it_f.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    if col == 4 and not k["secili_mi"]:
                        it_f.setForeground(QColor("#BDBDBD"))
                    self.kalem_tbl.setItem(i, col, it_f)
            else:
                for col in (3, 4):
                    it_e = QTableWidgetItem("—" if not is_urun else "")
                    it_e.setTextAlignment(Qt.AlignCenter)
                    if not is_urun:
                        it_e.setForeground(QColor("#BDBDBD"))
                    self.kalem_tbl.setItem(i, col, it_e)

    # ─────────────────────────────────────
    # PARAMETRE PANELİ
    # ─────────────────────────────────────

    def _kalem_tiklandi(self):
        r = self.kalem_tbl.currentRow()
        if 0 <= r < len(self._kalemler):
            self._param_goster(self._kalemler[r])

    def _param_goster(self, kalem):
        self._param_temizle()

        if kalem["tip"] == "urun":
            self.lbl_param_baslik.setText(
                f"Parametreler — {kalem['urun_kod']}  {kalem['urun_ad']}")
        else:
            self.lbl_param_baslik.setText(
                f"Parametreler — {kalem['alt_kalem_ad']}")

        if not self.srv:
            return
        vals = self.srv.parametre_degerleri(kalem["id"])
        if not vals:
            lbl = QLabel("Bu kalemde parametre tanımlı değil.")
            lbl.setStyleSheet("color: #999; font-style: italic; padding: 8px;")
            self.param_grid.addWidget(lbl, 0, 0, 1, 4)
            return

        row, col = 0, 0
        for d in vals:
            info = self._param_info(d["parametre_id"])
            tip = info.get("tip_kodu", "string") if info else "string"

            lbl = QLabel(f"{d['parametre_adi']}:")
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lbl.setStyleSheet("color: #333; padding-right: 4px;")

            w = self._make_widget(
                kalem["id"], d["parametre_id"],
                d["parametre_adi"], d["deger"], tip, info)
            w.setFixedHeight(28)

            self.param_grid.addWidget(lbl, row, col * 2)
            self.param_grid.addWidget(w, row, col * 2 + 1)

            col += 1
            if col >= 2:
                col = 0
                row += 1

    def _param_info(self, pid):
        if not self.em_repo:
            return None
        for tbl in ("urun_parametreler", "alt_kalem_parametreler"):
            alias = "up" if "urun" in tbl else "akp"
            q = (f"SELECT {alias}.*, pt.kod as tip_kodu, pt.gorunen_ad "
                 f"FROM {tbl} {alias} "
                 f"LEFT JOIN parametre_tipler pt ON {alias}.tip_id = pt.id "
                 f"WHERE {alias}.id=?")
            r = self.em_repo.db.getir_tek(q, (pid,))
            if r:
                return dict(r)
        return None

    def _make_widget(self, kid, pid, padi, val, tip, info):
        def save(v):
            if self.srv:
                self.srv.parametre_kaydet(kid, pid, padi, str(v))

        if tip == "int":
            w = QSpinBox()
            w.setRange(0, 999999)
            try:
                w.setValue(int(float(val)))
            except (ValueError, TypeError):
                pass
            w.valueChanged.connect(save)
            return w

        if tip in ("float", "para", "olcu_birimi", "yuzde"):
            w = QDoubleSpinBox()
            w.setDecimals(2)
            w.setRange(0, 99999999)
            try:
                w.setValue(float(val))
            except (ValueError, TypeError):
                pass
            if tip == "para":
                w.setPrefix("₺ ")
            elif tip == "yuzde":
                w.setSuffix(" %")
                w.setRange(0, 100)
            elif tip == "olcu_birimi":
                w.setSuffix(" m²")
            w.valueChanged.connect(save)
            return w

        if tip == "boolean":
            w = QCheckBox("Evet")
            w.setChecked(str(val).lower() in ("1", "true", "evet"))
            w.stateChanged.connect(lambda s: save("1" if s else "0"))
            return w

        if tip == "dropdown":
            w = QComboBox()
            if self.em_repo:
                for dd in self.em_repo.dropdown_degerleri(pid):
                    w.addItem(dd["deger"])
            if val:
                ix = w.findText(str(val))
                if ix >= 0:
                    w.setCurrentIndex(ix)
            w.currentTextChanged.connect(save)
            return w

        # string, tarih, diğer
        w = QLineEdit(str(val) if val else "")
        w.setPlaceholderText("Değer girin")
        w.editingFinished.connect(lambda: save(w.text()))
        return w

    # ─────────────────────────────────────
    # EYLEMLER
    # ─────────────────────────────────────

    def _secim(self, kid, state):
        if self.srv:
            self.srv.kalem_secim_degistir(kid, state == 2)

    def _miktar(self, kid, val):
        if self.srv:
            self.srv.kalem_miktar_degistir(kid, val)

    def _hesapla(self):
        if not self._tid or not self.srv:
            return

        konum_fiyat = 0
        if self._teklif and self.srv.em_srv and self.srv.proje_srv:
            proje = self.srv.proje_srv.getir(self._teklif["proje_id"])
            if proje:
                konum_fiyat = self.srv.em_srv.konum_fiyat(
                    getattr(proje, "ulke", "") or "",
                    getattr(proje, "konum", "") or "")

        ok, msg, toplam = self.srv.teklif_hesapla(self._tid, konum_fiyat)
        self._teklif = self.srv.getir(self._tid)
        self._toplam_goster()
        self._kalem_yukle()
        if not ok:
            QMessageBox.warning(self, "Hesaplama", msg)

    def _param_temizle(self):
        while self.param_grid.count():
            it = self.param_grid.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        self.lbl_param_baslik.setText(
            "Bir kalem seçerek parametrelerini görüntüleyin")
