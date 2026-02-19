#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enterprise Admin Ürün Yönetimi — Stacked Layout.
Seviye 1: Ürün Listesi
Seviye 2: Ürün Detay (Parametreler + Alt Kalemler)
Seviye 3: Alt Kalem Detay (Parametreler + Formül)
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QLineEdit, QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox,
    QFormLayout, QScrollArea, QFrame, QMessageBox,
    QStackedWidget, QGroupBox, QTextEdit, QInputDialog, QSplitter
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QCursor

from uygulama.ortak.yardimcilar import logger_olustur

logger = logger_olustur("admin_urun_sayfa")


# ═══════════════════════════════════════════
# DİNAMİK PARAMETRE RENDERER
# ═══════════════════════════════════════════

class DinamikParametreRenderer:
    """Parametre tipine göre widget üretir."""

    TIP_WIDGET_MAP = {
        "int": "spinbox",
        "float": "doublespinbox",
        "string": "text",
        "dropdown": "combobox",
        "para": "doublespinbox",
        "olcu_birimi": "doublespinbox",
        "boolean": "checkbox",
        "tarih": "dateedit",
        "yuzde": "doublespinbox",
    }

    @staticmethod
    def widget_olustur(tip_kodu: str, varsayilan: str = "") -> QWidget:
        """Parametre tipine göre uygun widget döndürür."""
        if tip_kodu in ("int",):
            w = QSpinBox(); w.setRange(-999999, 999999)
            try: w.setValue(int(varsayilan or 0))
            except: pass
            return w
        elif tip_kodu in ("float", "para", "olcu_birimi"):
            w = QDoubleSpinBox(); w.setRange(-999999, 999999)
            w.setDecimals(4 if tip_kodu == "olcu_birimi" else 2)
            try: w.setValue(float(varsayilan or 0))
            except: pass
            return w
        elif tip_kodu == "yuzde":
            w = QDoubleSpinBox(); w.setRange(0, 100); w.setSuffix(" %")
            try: w.setValue(float(varsayilan or 0))
            except: pass
            return w
        elif tip_kodu == "boolean":
            w = QCheckBox()
            w.setChecked(varsayilan.lower() in ("true", "1", "evet") if varsayilan else False)
            return w
        elif tip_kodu == "dropdown":
            w = QComboBox(); w.setEditable(False)
            return w
        else:
            w = QLineEdit()
            w.setText(varsayilan or "")
            return w


# ═══════════════════════════════════════════
# ÜRÜN LİSTESİ (SEVİYE 1)
# ═══════════════════════════════════════════

class UrunListeWidget(QWidget):
    urun_sec = pyqtSignal(str)  # urun_id

    def __init__(self, urun_servisi=None, em_repo=None, parent=None):
        super().__init__(parent)
        self.urun_servisi = urun_servisi
        self.em_repo = em_repo
        self._urunler = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self); layout.setSpacing(12)
        layout.addWidget(QLabel("Ürün Listesi"))

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Kod", "Ad", "Aktif", "Aktif Versiyon", "Güncelleme"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.doubleClicked.connect(self._cift_tikla)
        layout.addWidget(self.table)

        br = QHBoxLayout()
        self.btn_ekle = QPushButton("+ Yeni Ürün"); self.btn_ekle.setObjectName("primary")
        self.btn_ekle.clicked.connect(self._yeni_urun)
        self.btn_duzenle = QPushButton("Düzenle")
        self.btn_duzenle.clicked.connect(self._duzenle)
        self.btn_aktif = QPushButton("Aktif/Pasif")
        self.btn_aktif.clicked.connect(self._aktif_toggle)
        self.btn_sil = QPushButton("Sil"); self.btn_sil.setObjectName("danger")
        self.btn_sil.clicked.connect(self._sil)
        for b in [self.btn_ekle, self.btn_duzenle, self.btn_aktif, self.btn_sil]:
            br.addWidget(b)
        br.addStretch(); layout.addLayout(br)

    def yukle(self):
        if not self.urun_servisi: return
        self._urunler = self.urun_servisi.listele(sadece_aktif=False)
        self.table.setRowCount(len(self._urunler))
        for i, u in enumerate(self._urunler):
            self.table.setItem(i, 0, QTableWidgetItem(u.kod))
            self.table.setItem(i, 1, QTableWidgetItem(u.ad))
            self.table.setItem(i, 2, QTableWidgetItem("✓" if u.aktif else "—"))
            # Aktif versiyon
            ver = self.em_repo.aktif_urun_versiyon(u.id) if self.em_repo else None
            vno = f"v{ver['versiyon_no']}" if ver else "—"
            self.table.setItem(i, 3, QTableWidgetItem(vno))
            self.table.setItem(i, 4, QTableWidgetItem(u.olusturma_tarihi[:10]))

    def _secili_urun(self):
        row = self.table.currentRow()
        return self._urunler[row] if 0 <= row < len(self._urunler) else None

    def _cift_tikla(self, idx):
        u = self._secili_urun()
        if u: self.urun_sec.emit(u.id)

    def _duzenle(self):
        u = self._secili_urun()
        if u: self.urun_sec.emit(u.id)

    def _yeni_urun(self):
        if not self.urun_servisi: return
        kod, ok1 = QInputDialog.getText(self, "Ürün Kodu", "Kod:")
        if not ok1 or not kod: return
        ad, ok2 = QInputDialog.getText(self, "Ürün Adı", "Ad:")
        if not ok2 or not ad: return
        ok, msg, _ = self.urun_servisi.olustur(kod, ad)
        if not ok: QMessageBox.warning(self, "Hata", msg)
        self.yukle()

    def _aktif_toggle(self):
        u = self._secili_urun()
        if not u: return
        u_db = self.urun_servisi.urun_repo.id_ile_getir(u.id)
        if u_db:
            from uygulama.domain.modeller import Urun
            u_db.aktif = not u_db.aktif
            self.urun_servisi.urun_repo.guncelle(u_db)
        self.yukle()

    def _sil(self):
        u = self._secili_urun()
        if not u: return
        ret = QMessageBox.question(self, "Sil", f"{u.kod} silinsin mi?")
        if ret == QMessageBox.Yes:
            self.urun_servisi.urun_repo.soft_delete(u.id)
            self.yukle()


# ═══════════════════════════════════════════
# ÜRÜN DETAY (SEVİYE 2)
# ═══════════════════════════════════════════

class UrunDetayWidget(QWidget):
    geri = pyqtSignal()
    alt_kalem_sec = pyqtSignal(str, str)  # alt_kalem_id, urun_versiyon_id

    def __init__(self, urun_servisi=None, em_repo=None, em_srv=None, parent=None):
        super().__init__(parent)
        self.urun_servisi = urun_servisi
        self.em_repo = em_repo
        self.em_srv = em_srv
        self._urun_id = None
        self._urun_ver_id = None
        self._tipler = []
        self._params = []
        self._alt_kalemler = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self); layout.setSpacing(10)

        # Header
        h = QHBoxLayout()
        self.btn_geri = QPushButton("← Ürün Listesi")
        self.btn_geri.clicked.connect(self.geri.emit)
        self.baslik = QLabel(""); self.baslik.setObjectName("sectionTitle")
        self.ver_label = QLabel("")
        h.addWidget(self.btn_geri); h.addWidget(self.baslik)
        h.addStretch(); h.addWidget(self.ver_label)
        layout.addLayout(h)

        # Splitter: Parametreler | Alt Kalemler
        splitter = QSplitter(Qt.Horizontal)

        # SOL: Parametreler
        param_grp = QGroupBox("Ürün Parametreleri")
        pl = QVBoxLayout(param_grp); pl.setSpacing(8)

        self.param_table = QTableWidget()
        self.param_table.setColumnCount(5)
        self.param_table.setHorizontalHeaderLabels(
            ["Ad", "Tip", "Zorunlu", "Varsayılan", ""])
        self.param_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.param_table.setColumnWidth(4, 50)
        self.param_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        pl.addWidget(self.param_table)

        pb = QHBoxLayout()
        self.btn_param_ekle = QPushButton("+ Parametre")
        self.btn_param_ekle.clicked.connect(self._parametre_ekle)
        pb.addWidget(self.btn_param_ekle); pb.addStretch()
        pl.addLayout(pb)
        splitter.addWidget(param_grp)

        # SAĞ: Alt Kalemler
        ak_grp = QGroupBox("Alt Kalemler")
        al = QVBoxLayout(ak_grp); al.setSpacing(8)

        self.ak_table = QTableWidget()
        self.ak_table.setColumnCount(4)
        self.ak_table.setHorizontalHeaderLabels(
            ["Ad", "Aktif", "Versiyon", ""])
        self.ak_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.ak_table.setColumnWidth(3, 70)
        self.ak_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ak_table.doubleClicked.connect(self._ak_cift_tikla)
        al.addWidget(self.ak_table)

        ab = QHBoxLayout()
        self.btn_ak_ekle = QPushButton("+ Alt Kalem")
        self.btn_ak_ekle.clicked.connect(self._alt_kalem_ekle)
        self.btn_ak_duzenle = QPushButton("Düzenle")
        self.btn_ak_duzenle.clicked.connect(self._ak_duzenle)
        ab.addWidget(self.btn_ak_ekle); ab.addWidget(self.btn_ak_duzenle)
        ab.addStretch(); al.addLayout(ab)
        splitter.addWidget(ak_grp)

        splitter.setSizes([400, 400])
        layout.addWidget(splitter)

        # Versiyon geçmişi + yeni versiyon butonu
        ver_row = QHBoxLayout()
        self.versiyon_gecmisi = VersiyonYoneticiComponent("Ürün Versiyon Geçmişi")
        ver_row.addWidget(self.versiyon_gecmisi)
        layout.addLayout(ver_row)

        vg = QHBoxLayout()
        self.btn_yeni_ver = QPushButton("Yeni Versiyon Oluştur")
        self.btn_yeni_ver.clicked.connect(self._yeni_versiyon)
        vg.addStretch(); vg.addWidget(self.btn_yeni_ver)
        layout.addLayout(vg)

    def urun_yukle(self, urun_id: str):
        self._urun_id = urun_id
        urun = self.urun_servisi.urun_repo.id_ile_getir(urun_id) if self.urun_servisi else None
        if not urun: return

        self.baslik.setText(f"{urun.kod} — {urun.ad}")

        # Aktif versiyon
        ver = self.em_repo.aktif_urun_versiyon(urun_id) if self.em_repo else None
        if not ver:
            # İlk versiyonu otomatik oluştur
            if self.em_repo:
                vid, vno = self.em_repo.urun_versiyon_olustur(urun_id)
                ver = self.em_repo.aktif_urun_versiyon(urun_id)
        self._urun_ver_id = ver["id"] if ver else None
        vno = ver["versiyon_no"] if ver else 0
        self.ver_label.setText(f"Aktif Versiyon: v{vno}")

        # Tipler
        self._tipler = self.em_repo.parametre_tipleri() if self.em_repo else []

        self._parametreleri_yukle()
        self._alt_kalemleri_yukle()
        # Versiyon geçmişi
        if self.em_repo:
            versiyonlar = self.em_repo.urun_versiyonlar(urun_id)
            self.versiyon_gecmisi.yukle(versiyonlar)

    def _parametreleri_yukle(self):
        if not self._urun_ver_id or not self.em_repo: return
        self._params = self.em_repo.urun_parametreleri(self._urun_ver_id)
        self.param_table.setRowCount(len(self._params))
        for i, p in enumerate(self._params):
            self.param_table.setItem(i, 0, QTableWidgetItem(p["ad"]))
            self.param_table.setItem(i, 1, QTableWidgetItem(p.get("tip_kodu", "")))
            self.param_table.setItem(i, 2, QTableWidgetItem("✓" if p["zorunlu"] else "—"))
            self.param_table.setItem(i, 3, QTableWidgetItem(p["varsayilan_deger"]))
            btn = QPushButton("✕"); btn.setFixedWidth(36)
            btn.clicked.connect(lambda _, pid=p["id"]: self._parametre_sil(pid))
            self.param_table.setCellWidget(i, 4, btn)

    def _alt_kalemleri_yukle(self):
        if not self._urun_ver_id or not self.em_repo: return
        self._alt_kalemler = self.em_repo.urun_versiyonuna_bagli_alt_kalemler(
            self._urun_ver_id)
        self.ak_table.setRowCount(len(self._alt_kalemler))
        for i, ak in enumerate(self._alt_kalemler):
            self.ak_table.setItem(i, 0, QTableWidgetItem(ak["alt_kalem_adi"]))
            self.ak_table.setItem(i, 1, QTableWidgetItem("✓" if ak["aktif_mi"] else "—"))
            self.ak_table.setItem(i, 2, QTableWidgetItem(f"v{ak['versiyon_no']}"))
            btn = QPushButton("Aç"); btn.setFixedWidth(50)
            btn.clicked.connect(
                lambda _, akid=ak["alt_kalem_id"], vid=self._urun_ver_id:
                self.alt_kalem_sec.emit(akid, vid))
            self.ak_table.setCellWidget(i, 3, btn)

    def _parametre_ekle(self):
        if not self._urun_ver_id or not self.em_repo: return
        ad, ok = QInputDialog.getText(self, "Parametre Ekle", "Parametre Adı:")
        if not ok or not ad: return

        tip_isimleri = [t["kod"] for t in self._tipler]
        tip, ok2 = QInputDialog.getItem(self, "Tip Seçimi", "Tip:", tip_isimleri, 0, False)
        if not ok2: return

        tip_obj = [t for t in self._tipler if t["kod"] == tip]
        if not tip_obj: return

        varsayilan, ok3 = QInputDialog.getText(self, "Varsayılan", "Varsayılan değer:")
        if not ok3: varsayilan = ""

        self.em_repo.urun_parametre_ekle(
            self._urun_ver_id, ad, tip_obj[0]["id"], 0, varsayilan,
            len(self._params) + 1)
        self._parametreleri_yukle()

    def _parametre_sil(self, param_id):
        self.em_repo.urun_parametre_sil(param_id)
        self._parametreleri_yukle()

    def _alt_kalem_ekle(self):
        if not self.urun_servisi or not self._urun_ver_id: return
        ad, ok = QInputDialog.getText(self, "Alt Kalem Ekle", "Alt Kalem Adı:")
        if not ok or not ad: return
        ak_id = self.urun_servisi.urun_repo.alt_kalem_olustur(ad)
        self.em_repo.alt_kalem_versiyon_olustur(ak_id, self._urun_ver_id)
        self._alt_kalemleri_yukle()

    def _ak_cift_tikla(self, idx):
        row = idx.row()
        if 0 <= row < len(self._alt_kalemler):
            ak = self._alt_kalemler[row]
            self.alt_kalem_sec.emit(ak["alt_kalem_id"], self._urun_ver_id)

    def _ak_duzenle(self):
        row = self.ak_table.currentRow()
        if 0 <= row < len(self._alt_kalemler):
            ak = self._alt_kalemler[row]
            self.alt_kalem_sec.emit(ak["alt_kalem_id"], self._urun_ver_id)

    def _yeni_versiyon(self):
        if not self._urun_id or not self.em_srv: return
        vid, vno = self.em_srv.yeni_urun_versiyonu(self._urun_id)
        QMessageBox.information(self, "Versiyon", f"v{vno} oluşturuldu.")
        self.urun_yukle(self._urun_id)


# ═══════════════════════════════════════════
# VERSİYON YÖNETİCİ COMPONENT
# ═══════════════════════════════════════════

class VersiyonYoneticiComponent(QGroupBox):
    """Versiyon geçmişi görüntüleme bileşeni."""

    versiyon_sec = pyqtSignal(str)  # versiyon_id

    def __init__(self, baslik: str = "Versiyon Geçmişi", parent=None):
        super().__init__(baslik, parent)
        self._versiyonlar = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self); layout.setSpacing(6)
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            ["Versiyon", "Durum", "Tarih", ""])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 70); self.table.setColumnWidth(1, 60)
        self.table.setColumnWidth(3, 50)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setMaximumHeight(130)
        layout.addWidget(self.table)

    def yukle(self, versiyonlar: list[dict]):
        """Versiyon listesini gösterir. [{versiyon_no, aktif_mi, olusturma_tarihi, id}]"""
        self._versiyonlar = versiyonlar
        self.table.setRowCount(len(versiyonlar))
        for i, v in enumerate(versiyonlar):
            self.table.setItem(i, 0, QTableWidgetItem(f"v{v['versiyon_no']}"))
            durum = "Aktif" if v.get("aktif_mi") else "Pasif"
            self.table.setItem(i, 1, QTableWidgetItem(durum))
            tarih = v.get("olusturma_tarihi", "")[:16]
            self.table.setItem(i, 2, QTableWidgetItem(tarih))
            if not v.get("aktif_mi"):
                btn = QPushButton("Gör"); btn.setFixedWidth(40)
                btn.clicked.connect(
                    lambda _, vid=v["id"]: self.versiyon_sec.emit(vid))
                self.table.setCellWidget(i, 3, btn)


# ═══════════════════════════════════════════
# ALT KALEM DETAY (SEVİYE 3) + FORMÜL EDİTÖR
# ═══════════════════════════════════════════

class MaliyetFormulEditor(QGroupBox):
    """Maliyet formül tasarım alanı."""

    def __init__(self, em_repo=None, parent=None):
        super().__init__("Maliyet Formülü", parent)
        self.em_repo = em_repo
        self._akv_id = None
        self._sablon_id = None
        self._build()

    def _build(self):
        layout = QVBoxLayout(self); layout.setSpacing(8)

        fl = QFormLayout()
        self.formul_edit = QLineEdit()
        self.formul_edit.setPlaceholderText("Örn: A * B + C + KF")
        fl.addRow("Formül:", self.formul_edit)

        self.kar_spin = QDoubleSpinBox()
        self.kar_spin.setRange(0, 100); self.kar_spin.setSuffix(" %")
        fl.addRow("Kar Oranı:", self.kar_spin)

        self.varsayilan_cb = QCheckBox("Varsayılan formül")
        self.varsayilan_cb.setChecked(True)
        fl.addRow("", self.varsayilan_cb)
        layout.addLayout(fl)

        layout.addWidget(QLabel("Değişken Eşleşmeleri:"))
        self.degisken_table = QTableWidget()
        self.degisken_table.setColumnCount(3)
        self.degisken_table.setHorizontalHeaderLabels(
            ["Değişken", "Parametre Adı", "Varsayılan"])
        self.degisken_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.degisken_table.setMaximumHeight(120)
        layout.addWidget(self.degisken_table)

        bb = QHBoxLayout()
        self.btn_degisken_ekle = QPushButton("+ Değişken")
        self.btn_degisken_ekle.clicked.connect(self._degisken_ekle)
        self.btn_kaydet = QPushButton("Formülü Kaydet")
        self.btn_kaydet.setObjectName("primary")
        self.btn_kaydet.clicked.connect(self._kaydet)
        bb.addWidget(self.btn_degisken_ekle); bb.addStretch()
        bb.addWidget(self.btn_kaydet)
        layout.addLayout(bb)

        self.durum_label = QLabel("")
        layout.addWidget(self.durum_label)

    def yukle(self, akv_id: str):
        self._akv_id = akv_id
        sablon = self.em_repo.aktif_sablon(akv_id) if self.em_repo else None

        if sablon:
            self._sablon_id = sablon["id"]
            self.formul_edit.setText(sablon["formul_ifadesi"])
            self.kar_spin.setValue(sablon["kar_orani"])
            self.varsayilan_cb.setChecked(bool(sablon["varsayilan_formul_mu"]))
            self._degiskenleri_yukle()
            self.durum_label.setText(f"Aktif şablon: {sablon['id'][:8]}")
        else:
            self._sablon_id = None
            self.formul_edit.setText("A * B + KF")
            self.kar_spin.setValue(0)
            self.degisken_table.setRowCount(0)
            self.durum_label.setText("Şablon yok — varsayılan formül")

    def _degiskenleri_yukle(self):
        if not self._sablon_id: return
        params = self.em_repo.sablon_parametreleri(self._sablon_id)
        self.degisken_table.setRowCount(len(params))
        for i, p in enumerate(params):
            self.degisken_table.setItem(i, 0, QTableWidgetItem(p["degisken_kodu"]))
            self.degisken_table.setItem(i, 1, QTableWidgetItem(p["ad"]))
            self.degisken_table.setItem(i, 2, QTableWidgetItem(str(p["varsayilan_deger"])))

    def _degisken_ekle(self):
        kodlar = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        mevcut = self.degisken_table.rowCount()
        if mevcut >= 26: return
        yeni_kod = kodlar[mevcut]
        row = self.degisken_table.rowCount()
        self.degisken_table.setRowCount(row + 1)
        self.degisken_table.setItem(row, 0, QTableWidgetItem(yeni_kod))
        self.degisken_table.setItem(row, 1, QTableWidgetItem(""))
        self.degisken_table.setItem(row, 2, QTableWidgetItem("0"))

    def _kaydet(self):
        if not self._akv_id or not self.em_repo: return
        formul = self.formul_edit.text().strip()
        kar = self.kar_spin.value()
        if not formul:
            QMessageBox.warning(self, "Hata", "Formül boş olamaz."); return

        # Eski şablonu pasifle
        if self._sablon_id:
            self.em_repo.sablon_sil(self._sablon_id)

        sid = self.em_repo.sablon_olustur(self._akv_id, formul, True, kar)

        # Değişkenleri kaydet
        for row in range(self.degisken_table.rowCount()):
            kod_item = self.degisken_table.item(row, 0)
            ad_item = self.degisken_table.item(row, 1)
            vars_item = self.degisken_table.item(row, 2)
            if kod_item and ad_item:
                try: v = float(vars_item.text()) if vars_item else 0
                except: v = 0
                self.em_repo.sablon_parametre_ekle(
                    sid, ad_item.text(), kod_item.text(), v)

        self._sablon_id = sid
        self.durum_label.setText(f"Kaydedildi: {sid[:8]}")


class AltKalemDetayWidget(QWidget):
    """Alt kalem detay ekranı — parametreler + formül editör."""
    geri = pyqtSignal()

    def __init__(self, urun_servisi=None, em_repo=None, em_srv=None, parent=None):
        super().__init__(parent)
        self.urun_servisi = urun_servisi
        self.em_repo = em_repo
        self.em_srv = em_srv
        self._ak_id = None
        self._akv_id = None
        self._tipler = []
        self._params = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self); layout.setSpacing(10)

        h = QHBoxLayout()
        self.btn_geri = QPushButton("← Ürün Detay")
        self.btn_geri.clicked.connect(self.geri.emit)
        self.baslik = QLabel(""); self.baslik.setObjectName("sectionTitle")
        self.ver_label = QLabel("")
        h.addWidget(self.btn_geri); h.addWidget(self.baslik)
        h.addStretch(); h.addWidget(self.ver_label)
        layout.addLayout(h)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        content = QWidget()
        cl = QVBoxLayout(content); cl.setSpacing(12)

        # Parametreler
        param_grp = QGroupBox("Alt Kalem Parametreleri")
        pl = QVBoxLayout(param_grp)
        self.param_table = QTableWidget()
        self.param_table.setColumnCount(6)
        self.param_table.setHorizontalHeaderLabels(
            ["Ad", "Tip", "Zorunlu", "Varsayılan", "Ürün Ref", ""])
        self.param_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.param_table.setColumnWidth(5, 40)
        self.param_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.param_table.setMaximumHeight(180)
        pl.addWidget(self.param_table)

        pb = QHBoxLayout()
        self.btn_param_ekle = QPushButton("+ Parametre")
        self.btn_param_ekle.clicked.connect(self._parametre_ekle)
        pb.addWidget(self.btn_param_ekle); pb.addStretch()
        pl.addLayout(pb)
        cl.addWidget(param_grp)

        # Formül editör
        self.formul_editor = MaliyetFormulEditor(self.em_repo)
        cl.addWidget(self.formul_editor)

        # Yeni versiyon
        vb = QHBoxLayout()
        self.btn_yeni_ver = QPushButton("Yeni Alt Kalem Versiyonu")
        self.btn_yeni_ver.clicked.connect(self._yeni_versiyon)
        vb.addStretch(); vb.addWidget(self.btn_yeni_ver)
        cl.addLayout(vb)

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def yukle(self, alt_kalem_id: str, urun_versiyon_id: str):
        self._ak_id = alt_kalem_id
        self._tipler = self.em_repo.parametre_tipleri() if self.em_repo else []

        # Alt kalem adı
        ak = self.urun_servisi.urun_repo.alt_kalem_getir(alt_kalem_id) if self.urun_servisi else None
        self.baslik.setText(ak["ad"] if ak else "Alt Kalem")

        # Aktif versiyon
        ver = self.em_repo.aktif_alt_kalem_versiyon(alt_kalem_id) if self.em_repo else None
        if not ver:
            vid, vno = self.em_repo.alt_kalem_versiyon_olustur(
                alt_kalem_id, urun_versiyon_id)
            ver = self.em_repo.aktif_alt_kalem_versiyon(alt_kalem_id)
        self._akv_id = ver["id"] if ver else None
        self.ver_label.setText(f"v{ver['versiyon_no']}" if ver else "—")

        self._parametreleri_yukle()
        self.formul_editor.yukle(self._akv_id)

    def _parametreleri_yukle(self):
        if not self._akv_id or not self.em_repo: return
        self._params = self.em_repo.alt_kalem_parametreleri(self._akv_id)
        self.param_table.setRowCount(len(self._params))
        for i, p in enumerate(self._params):
            self.param_table.setItem(i, 0, QTableWidgetItem(p["ad"]))
            self.param_table.setItem(i, 1, QTableWidgetItem(p.get("tip_kodu", "")))
            self.param_table.setItem(i, 2, QTableWidgetItem("✓" if p["zorunlu"] else "—"))
            self.param_table.setItem(i, 3, QTableWidgetItem(p["varsayilan_deger"]))
            ref = p.get("urun_param_ref_id") or ""
            self.param_table.setItem(i, 4, QTableWidgetItem("Ref" if ref else "—"))
            btn = QPushButton("✕"); btn.setFixedWidth(36)
            btn.clicked.connect(lambda _, pid=p["id"]: self._parametre_sil(pid))
            self.param_table.setCellWidget(i, 5, btn)

    def _parametre_ekle(self):
        if not self._akv_id or not self.em_repo: return
        ad, ok = QInputDialog.getText(self, "Parametre", "Parametre Adı:")
        if not ok or not ad: return
        tip_isimleri = [t["kod"] for t in self._tipler]
        tip, ok2 = QInputDialog.getItem(self, "Tip", "Tip:", tip_isimleri, 0, False)
        if not ok2: return
        tip_obj = [t for t in self._tipler if t["kod"] == tip]
        if not tip_obj: return
        self.em_repo.alt_kalem_parametre_ekle(
            self._akv_id, ad, tip_obj[0]["id"], 0, "",
            sira=len(self._params) + 1)
        self._parametreleri_yukle()

    def _parametre_sil(self, pid):
        with self.em_repo.db.transaction() as conn:
            conn.execute("UPDATE alt_kalem_parametreler SET aktif_mi=0 WHERE id=?", (pid,))
        self._parametreleri_yukle()

    def _yeni_versiyon(self):
        if not self._ak_id or not self.em_srv: return
        uv = self.em_repo.aktif_alt_kalem_versiyon(self._ak_id)
        uvid = uv["urun_versiyon_id"] if uv else None
        if uvid:
            vid, vno = self.em_srv.yeni_alt_kalem_versiyonu(self._ak_id, uvid)
            QMessageBox.information(self, "Versiyon", f"v{vno} oluşturuldu.")
            self.yukle(self._ak_id, uvid)


# ═══════════════════════════════════════════
# ANA ADMIN ÜRÜN SAYFASI (STACKED)
# ═══════════════════════════════════════════

class AdminUrunSayfasi(QWidget):
    """Stacked layout: Liste → Detay → Alt Kalem Detay."""

    LISTE = 0
    DETAY = 1
    ALT_KALEM = 2

    def __init__(self, urun_servisi=None, em_repo=None, em_srv=None, parent=None):
        super().__init__(parent)
        self.urun_servisi = urun_servisi
        self.em_repo = em_repo
        self.em_srv = em_srv

        self.stack = QStackedWidget()
        layout = QVBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

        # Seviye 1
        self.liste = UrunListeWidget(urun_servisi, em_repo)
        self.liste.urun_sec.connect(self._urun_ac)
        self.stack.addWidget(self.liste)

        # Seviye 2
        self.detay = UrunDetayWidget(urun_servisi, em_repo, em_srv)
        self.detay.geri.connect(self._listeye_don)
        self.detay.alt_kalem_sec.connect(self._alt_kalem_ac)
        self.stack.addWidget(self.detay)

        # Seviye 3
        self.ak_detay = AltKalemDetayWidget(urun_servisi, em_repo, em_srv)
        self.ak_detay.geri.connect(self._detaya_don)
        self.stack.addWidget(self.ak_detay)

    def yukle(self):
        self.liste.yukle()
        self.stack.setCurrentIndex(self.LISTE)

    def _urun_ac(self, urun_id: str):
        self.detay.urun_yukle(urun_id)
        self.stack.setCurrentIndex(self.DETAY)

    def _alt_kalem_ac(self, ak_id: str, urun_ver_id: str):
        self.ak_detay.yukle(ak_id, urun_ver_id)
        self.stack.setCurrentIndex(self.ALT_KALEM)

    def _listeye_don(self):
        self.liste.yukle()
        self.stack.setCurrentIndex(self.LISTE)

    def _detaya_don(self):
        self.stack.setCurrentIndex(self.DETAY)
