#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Belge Admin Sayfası — Şablon dosya yönetimi, belge türü düzenleme,
bölüm yönetimi ve şablon ataması.

Layout: Sol (Şablon dosyalar + Belge türleri) | Orta (Bölümler) | Sağ (Atamalar)
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QComboBox, QSpinBox, QLineEdit, QFileDialog, QMessageBox,
    QDialog, QFormLayout, QDialogButtonBox, QGroupBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor

from uygulama.altyapi.belge_repo import BOLUM_TURLERI
from uygulama.ortak.yardimcilar import logger_olustur

logger = logger_olustur("belge_admin")


def _tbl(t, rh=28):
    t.verticalHeader().setDefaultSectionSize(rh)
    t.verticalHeader().setVisible(False)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setAlternatingRowColors(True)
    t.setStyleSheet(
        "QTableWidget{gridline-color:#E0E0E0;border:1px solid #ddd;}"
        "QTableWidget::item{padding:2px 4px;}"
        "QTableWidget::item:selected{background:#BBDEFB;color:#000;}")


class BelgeAdminSayfasi(QWidget):
    """Admin paneline tab olarak eklenen belge yönetim widget'ı."""

    def __init__(self, belge_srv=None, urun_srv=None, em_repo=None, parent=None):
        super().__init__(parent)
        self.srv = belge_srv
        self.urun_srv = urun_srv
        self.em_repo = em_repo
        self._secili_tur_id = None
        self._secili_bolum_id = None
        self._sablonlar = []
        self._bolumler = []
        self._atamalar = []
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sp = QSplitter(Qt.Horizontal)

        # ═══ SOL PANEL: Şablon Dosyalar + Belge Türleri ═══
        sol = QWidget()
        sl = QVBoxLayout(sol)
        sl.setContentsMargins(4, 4, 4, 4)
        sl.setSpacing(6)

        # ── Şablon Dosyalar ──
        g1 = QGroupBox("📁 Şablon Dosyaları")
        g1l = QVBoxLayout(g1)
        g1l.setSpacing(4)
        sb = QHBoxLayout()
        b_yukle = QPushButton("+ Yükle")
        b_yukle.setFixedHeight(26)
        b_yukle.clicked.connect(self._sablon_yukle)
        b_sil = QPushButton("Sil")
        b_sil.setFixedHeight(26)
        b_sil.clicked.connect(self._sablon_sil)
        sb.addWidget(b_yukle)
        sb.addWidget(b_sil)
        sb.addStretch()
        g1l.addLayout(sb)

        self.tbl_sablon = QTableWidget()
        _tbl(self.tbl_sablon)
        self.tbl_sablon.setColumnCount(3)
        self.tbl_sablon.setHorizontalHeaderLabels(["Ad", "Sheet", "Dosya"])
        self.tbl_sablon.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_sablon.setColumnWidth(1, 70)
        self.tbl_sablon.setColumnWidth(2, 100)
        g1l.addWidget(self.tbl_sablon)
        sl.addWidget(g1)

        # ── Belge Türleri ──
        g2 = QGroupBox("📄 Belge Türleri")
        g2l = QVBoxLayout(g2)
        g2l.setSpacing(4)
        self.cmb_tur = QComboBox()
        self.cmb_tur.currentIndexChanged.connect(self._tur_secildi)
        g2l.addWidget(self.cmb_tur)

        sf = QHBoxLayout()
        sf.addWidget(QLabel("Sütun:"))
        self.edt_sutun = QLineEdit("A:I")
        self.edt_sutun.setFixedWidth(50)
        self.edt_sutun.editingFinished.connect(self._sutun_kaydet)
        sf.addWidget(self.edt_sutun)
        sf.addStretch()
        g2l.addLayout(sf)
        sl.addWidget(g2)
        sl.addStretch()
        sp.addWidget(sol)

        # ═══ ORTA PANEL: Bölümler ═══
        orta = QWidget()
        ol = QVBoxLayout(orta)
        ol.setContentsMargins(4, 4, 4, 4)
        ol.setSpacing(4)

        g3 = QGroupBox("📑 Bölümler")
        g3l = QVBoxLayout(g3)
        g3l.setSpacing(4)
        bb = QHBoxLayout()
        b_bolum_ekle = QPushButton("+ Bölüm")
        b_bolum_ekle.setFixedHeight(26)
        b_bolum_ekle.clicked.connect(self._bolum_ekle)
        b_bolum_sil = QPushButton("Sil")
        b_bolum_sil.setFixedHeight(26)
        b_bolum_sil.clicked.connect(self._bolum_sil)
        b_yukari = QPushButton("↑")
        b_yukari.setFixedSize(26, 26)
        b_yukari.clicked.connect(lambda: self._bolum_tasi(-1))
        b_asagi = QPushButton("↓")
        b_asagi.setFixedSize(26, 26)
        b_asagi.clicked.connect(lambda: self._bolum_tasi(1))
        bb.addWidget(b_bolum_ekle)
        bb.addWidget(b_bolum_sil)
        bb.addStretch()
        bb.addWidget(b_yukari)
        bb.addWidget(b_asagi)
        g3l.addLayout(bb)

        self.tbl_bolum = QTableWidget()
        _tbl(self.tbl_bolum)
        self.tbl_bolum.setColumnCount(3)
        self.tbl_bolum.setHorizontalHeaderLabels(["Sıra", "Bölüm Adı", "Tür"])
        self.tbl_bolum.setColumnWidth(0, 35)
        self.tbl_bolum.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tbl_bolum.setColumnWidth(2, 100)
        self.tbl_bolum.clicked.connect(self._bolum_secildi)
        g3l.addWidget(self.tbl_bolum)
        g3.setLayout(g3l)
        ol.addWidget(g3)
        sp.addWidget(orta)

        # ═══ SAĞ PANEL: Şablon Atamaları ═══
        sag = QWidget()
        rl = QVBoxLayout(sag)
        rl.setContentsMargins(4, 4, 4, 4)
        rl.setSpacing(4)

        g4 = QGroupBox("🔗 Şablon Atamaları")
        g4l = QVBoxLayout(g4)
        g4l.setSpacing(4)
        self.lbl_bolum_adi = QLabel("Bölüm seçin")
        self.lbl_bolum_adi.setStyleSheet("font-weight:bold;color:#1565C0;")
        g4l.addWidget(self.lbl_bolum_adi)

        ab = QHBoxLayout()
        b_atama_ekle = QPushButton("+ Atama")
        b_atama_ekle.setFixedHeight(26)
        b_atama_ekle.clicked.connect(self._atama_ekle)
        b_atama_sil = QPushButton("Sil")
        b_atama_sil.setFixedHeight(26)
        b_atama_sil.clicked.connect(self._atama_sil)
        ab.addWidget(b_atama_ekle)
        ab.addWidget(b_atama_sil)
        ab.addStretch()
        g4l.addLayout(ab)

        self.tbl_atama = QTableWidget()
        _tbl(self.tbl_atama)
        self.tbl_atama.setColumnCount(6)
        self.tbl_atama.setHorizontalHeaderLabels(
            ["Ürün", "Alt Kalem", "Şablon", "Sheet", "Satır", "Sıra"])
        self.tbl_atama.setColumnWidth(0, 60)
        self.tbl_atama.setColumnWidth(1, 90)
        self.tbl_atama.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tbl_atama.setColumnWidth(3, 60)
        self.tbl_atama.setColumnWidth(4, 55)
        self.tbl_atama.setColumnWidth(5, 35)
        g4l.addWidget(self.tbl_atama)
        g4.setLayout(g4l)
        rl.addWidget(g4)
        sp.addWidget(sag)

        sp.setSizes([220, 260, 340])
        root.addWidget(sp)

    # ═══════════════════════════════════════
    # VERİ YÜKLEME
    # ═══════════════════════════════════════

    def yukle(self):
        """Sayfa gösterildiğinde çağrılır."""
        self._sablonlari_yukle()
        self._turleri_yukle()

    def _sablonlari_yukle(self):
        if not self.srv:
            return
        self._sablonlar = self.srv.repo.sablon_dosyalar()
        self.tbl_sablon.setRowCount(len(self._sablonlar))
        for i, s in enumerate(self._sablonlar):
            self.tbl_sablon.setItem(i, 0, QTableWidgetItem(s["ad"]))
            self.tbl_sablon.setItem(i, 1, QTableWidgetItem(s["sheet_adi"]))
            import os
            self.tbl_sablon.setItem(i, 2, QTableWidgetItem(
                os.path.basename(s["dosya_yolu"])))

    def _turleri_yukle(self):
        if not self.srv:
            return
        self.cmb_tur.blockSignals(True)
        self.cmb_tur.clear()
        turleri = self.srv.repo.belge_turleri()
        for t in turleri:
            self.cmb_tur.addItem(f"{t['kod']} — {t['ad']}", t["id"])
        self.cmb_tur.blockSignals(False)
        if turleri:
            self.cmb_tur.setCurrentIndex(0)
            self._tur_secildi(0)

    def _tur_secildi(self, idx):
        tid = self.cmb_tur.currentData()
        if not tid:
            return
        self._secili_tur_id = tid
        tur = self.srv.repo.belge_turu_getir(tid) if self.srv else None
        if tur:
            self.edt_sutun.setText(tur.get("sutun_araligi", "A:I"))
        self._bolumleri_yukle()

    def _bolumleri_yukle(self):
        if not self.srv or not self._secili_tur_id:
            return
        self._bolumler = self.srv.repo.bolumler(self._secili_tur_id)
        self.tbl_bolum.setRowCount(len(self._bolumler))
        tur_renk = {"sabit": "#4CAF50", "urun_bazli": "#1565C0",
                    "alt_kalem_bazli": "#FF8F00", "urun_alt_kalem": "#7B1FA2"}
        tur_label = {"sabit": "Sabit", "urun_bazli": "Ürün bazlı",
                     "alt_kalem_bazli": "Alt kalem", "urun_alt_kalem": "Ürün+AK"}
        for i, b in enumerate(self._bolumler):
            si = QTableWidgetItem(str(b["sira"]))
            si.setTextAlignment(Qt.AlignCenter)
            self.tbl_bolum.setItem(i, 0, si)
            self.tbl_bolum.setItem(i, 1, QTableWidgetItem(b["ad"]))
            ti = QTableWidgetItem(tur_label.get(b["tur"], b["tur"]))
            ti.setForeground(QColor(tur_renk.get(b["tur"], "#333")))
            self.tbl_bolum.setItem(i, 2, ti)
        # Seçim temizle
        self._secili_bolum_id = None
        self.lbl_bolum_adi.setText("Bölüm seçin")
        self.tbl_atama.setRowCount(0)

    def _bolum_secildi(self, idx=None):
        r = self.tbl_bolum.currentRow()
        if 0 <= r < len(self._bolumler):
            b = self._bolumler[r]
            self._secili_bolum_id = b["id"]
            tur_label = {"sabit": "Sabit", "urun_bazli": "Ürün bazlı",
                        "alt_kalem_bazli": "Alt kalem", "urun_alt_kalem": "Ürün+AK"}
            self.lbl_bolum_adi.setText(
                f"{b['ad']}  ({tur_label.get(b['tur'], b['tur'])})")
            self._atamalari_yukle()

    def _atamalari_yukle(self):
        if not self.srv or not self._secili_bolum_id:
            return
        self._atamalar = self.srv.repo.atamalar(self._secili_bolum_id)
        self.tbl_atama.setRowCount(len(self._atamalar))
        for i, a in enumerate(self._atamalar):
            # Ürün adı
            urun_ad = "—"
            if a.get("urun_id") and self.em_repo:
                u = self.em_repo.db.getir_tek(
                    "SELECT kod FROM urunler WHERE id=?", (a["urun_id"],))
                if u:
                    urun_ad = u["kod"]
            self.tbl_atama.setItem(i, 0, QTableWidgetItem(urun_ad))

            # Alt kalem adı
            ak_ad = "—"
            if a.get("alt_kalem_id") and self.em_repo:
                ak = self.em_repo.db.getir_tek(
                    "SELECT ad FROM alt_kalemler WHERE id=?", (a["alt_kalem_id"],))
                if ak:
                    ak_ad = ak["ad"]
            self.tbl_atama.setItem(i, 1, QTableWidgetItem(ak_ad))

            self.tbl_atama.setItem(i, 2, QTableWidgetItem(a.get("sablon_adi", "")))
            self.tbl_atama.setItem(i, 3, QTableWidgetItem(a.get("sheet_adi", "")))
            self.tbl_atama.setItem(i, 4, QTableWidgetItem(
                f"{a['satir_baslangic']}-{a['satir_bitis']}"))
            si = QTableWidgetItem(str(a.get("sira", 0)))
            si.setTextAlignment(Qt.AlignCenter)
            self.tbl_atama.setItem(i, 5, si)

    # ═══════════════════════════════════════
    # ŞABLON DOSYA İŞLEMLERİ
    # ═══════════════════════════════════════

    def _sablon_yukle(self):
        if not self.srv:
            return
        yol, _ = QFileDialog.getOpenFileName(
            self, "Excel Şablon Seç", "", "Excel (*.xlsx *.xls)")
        if not yol:
            return

        # Sheet seçimi
        sheets = self.srv.sablon_sheetleri(yol)
        if not sheets:
            sheets = ["Sheet1"]

        dlg = QDialog(self)
        dlg.setWindowTitle("Şablon Yükle")
        fl = QFormLayout(dlg)

        edt_ad = QLineEdit()
        import os
        edt_ad.setText(os.path.splitext(os.path.basename(yol))[0])
        fl.addRow("Şablon Adı:", edt_ad)

        cmb_sheet = QComboBox()
        for s in sheets:
            cmb_sheet.addItem(s)
        fl.addRow("Sheet:", cmb_sheet)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        fl.addRow(bb)

        if dlg.exec_():
            ad = edt_ad.text().strip() or "Şablon"
            sheet = cmb_sheet.currentText()
            ok, msg, _ = self.srv.sablon_yukle(yol, ad, sheet)
            if ok:
                self._sablonlari_yukle()
            else:
                QMessageBox.warning(self, "Hata", msg)

    def _sablon_sil(self):
        r = self.tbl_sablon.currentRow()
        if 0 <= r < len(self._sablonlar):
            s = self._sablonlar[r]
            if QMessageBox.question(
                    self, "Sil", f"'{s['ad']}' silinsin mi?",
                    QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                self.srv.repo.sablon_dosya_sil(s["id"])
                self._sablonlari_yukle()

    # ═══════════════════════════════════════
    # SÜTUN ARALIĞI
    # ═══════════════════════════════════════

    def _sutun_kaydet(self):
        if not self.srv or not self._secili_tur_id:
            return
        val = self.edt_sutun.text().strip().upper()
        if ":" not in val:
            return
        self.srv.repo.belge_turu_guncelle(self._secili_tur_id, sutun_araligi=val)

    # ═══════════════════════════════════════
    # BÖLÜM İŞLEMLERİ
    # ═══════════════════════════════════════

    def _bolum_ekle(self):
        if not self.srv or not self._secili_tur_id:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Bölüm Ekle")
        fl = QFormLayout(dlg)

        edt_ad = QLineEdit()
        fl.addRow("Bölüm Adı:", edt_ad)

        cmb_tur = QComboBox()
        for kod, label in [("sabit", "Sabit"),
                           ("urun_bazli", "Ürün bazlı"),
                           ("alt_kalem_bazli", "Alt kalem bazlı"),
                           ("urun_alt_kalem", "Ürün + Alt kalem")]:
            cmb_tur.addItem(label, kod)
        fl.addRow("Tür:", cmb_tur)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        fl.addRow(bb)

        if dlg.exec_():
            ad = edt_ad.text().strip()
            if not ad:
                return
            tur = cmb_tur.currentData()
            sira = len(self._bolumler) + 1
            self.srv.repo.bolum_ekle(self._secili_tur_id, ad, tur, sira)
            self._bolumleri_yukle()

    def _bolum_sil(self):
        r = self.tbl_bolum.currentRow()
        if 0 <= r < len(self._bolumler):
            b = self._bolumler[r]
            if QMessageBox.question(
                    self, "Sil", f"'{b['ad']}' silinsin mi?",
                    QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                self.srv.repo.bolum_sil(b["id"])
                self._bolumleri_yukle()

    def _bolum_tasi(self, yon):
        r = self.tbl_bolum.currentRow()
        if r < 0 or r >= len(self._bolumler):
            return
        nr = r + yon
        if nr < 0 or nr >= len(self._bolumler):
            return
        # Swap sıra
        b1 = self._bolumler[r]
        b2 = self._bolumler[nr]
        s1, s2 = b1["sira"], b2["sira"]
        self.srv.repo.bolum_sira_degistir(b1["id"], s2)
        self.srv.repo.bolum_sira_degistir(b2["id"], s1)
        self._bolumleri_yukle()
        self.tbl_bolum.selectRow(nr)

    # ═══════════════════════════════════════
    # ATAMA İŞLEMLERİ
    # ═══════════════════════════════════════

    def _atama_ekle(self):
        if not self.srv or not self._secili_bolum_id:
            QMessageBox.information(self, "Bilgi", "Önce bir bölüm seçin.")
            return

        bolum = self.srv.repo.bolum_getir(self._secili_bolum_id)
        if not bolum:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Şablon Ataması Ekle")
        dlg.setMinimumWidth(400)
        fl = QFormLayout(dlg)

        # Şablon dosyası seçimi
        cmb_sablon = QComboBox()
        sablonlar = self.srv.repo.sablon_dosyalar()
        for s in sablonlar:
            cmb_sablon.addItem(f"{s['ad']} ({s['sheet_adi']})", s["id"])
        fl.addRow("Şablon Dosyası:", cmb_sablon)

        # Ürün seçimi (urun_bazli veya alt_kalem_bazli ise)
        cmb_urun = QComboBox()
        cmb_urun.addItem("— Yok —", None)
        urunler = self.urun_srv.listele(sadece_aktif=True) if self.urun_srv else []
        for u in urunler:
            cmb_urun.addItem(f"{u.kod} — {u.ad}", u.id)
        cmb_urun.setEnabled(bolum["tur"] != "sabit")
        fl.addRow("Ürün:", cmb_urun)

        # Alt kalem seçimi (alt_kalem_bazli veya urun_alt_kalem ise)
        cmb_ak = QComboBox()
        cmb_ak.addItem("— Yok —", None)
        cmb_ak.setEnabled(bolum["tur"] in ("alt_kalem_bazli", "urun_alt_kalem"))

        def _urun_degisti(idx):
            cmb_ak.clear()
            cmb_ak.addItem("— Yok —", None)
            uid = cmb_urun.currentData()
            if uid and self.em_repo:
                ver = self.em_repo.aktif_urun_versiyon(uid)
                if ver:
                    for ak in self.em_repo.urun_versiyonuna_bagli_alt_kalemler(ver["id"]):
                        cmb_ak.addItem(ak["alt_kalem_adi"], ak["alt_kalem_id"])

        cmb_urun.currentIndexChanged.connect(_urun_degisti)
        fl.addRow("Alt Kalem:", cmb_ak)

        # Satır aralığı
        sp_bas = QSpinBox()
        sp_bas.setRange(1, 9999)
        sp_bas.setValue(1)
        fl.addRow("Satır Başlangıç:", sp_bas)

        sp_bit = QSpinBox()
        sp_bit.setRange(1, 9999)
        sp_bit.setValue(1)
        fl.addRow("Satır Bitiş:", sp_bit)

        sp_sira = QSpinBox()
        sp_sira.setRange(0, 999)
        sp_sira.setValue(len(self._atamalar) + 1)
        fl.addRow("Sıra:", sp_sira)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        fl.addRow(bb)

        if dlg.exec_():
            sablon_id = cmb_sablon.currentData()
            if not sablon_id:
                return
            urun_id = cmb_urun.currentData()
            ak_id = cmb_ak.currentData()
            self.srv.repo.atama_ekle(
                self._secili_bolum_id, sablon_id,
                sp_bas.value(), sp_bit.value(),
                urun_id, ak_id, sp_sira.value())
            self._atamalari_yukle()

    def _atama_sil(self):
        r = self.tbl_atama.currentRow()
        if 0 <= r < len(self._atamalar):
            a = self._atamalar[r]
            if QMessageBox.question(
                    self, "Sil", "Bu atama silinsin mi?",
                    QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                self.srv.repo.atama_sil(a["id"])
                self._atamalari_yukle()
