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
    QFormLayout, QScrollArea, QFrame, QMessageBox, QDialog,
    QStackedWidget, QGroupBox, QTextEdit, QInputDialog, QSplitter
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QCursor

from uygulama.ortak.yardimcilar import logger_olustur

logger = logger_olustur("admin_urun_sayfa")


def _tablo_ayarla(table: QTableWidget, satir_yuksekligi: int = 32):
    """Tüm tablolara ortak ayar: satır yüksekliği, seçim davranışı."""
    table.verticalHeader().setDefaultSectionSize(satir_yuksekligi)
    table.verticalHeader().setVisible(False)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)


def _tablo_butonu(text: str = "✕", genislik: int = 32) -> QPushButton:
    """Tablo hücresine sığan küçük buton oluşturur."""
    btn = QPushButton(text)
    btn.setFixedSize(genislik, 24)
    btn.setStyleSheet(
        "QPushButton { font-size: 11px; padding: 0px; margin: 1px; }")
    return btn


# ═══════════════════════════════════════════
# KULLANICI DOSTU PARAMETRE EKLEME DİALOG
# ═══════════════════════════════════════════

class ParametreEkleDialog(QDialog):
    """
    Kullanıcı dostu parametre ekleme penceresi.
    Seçenek Listesi tipinde seçenekler de aynı anda tanımlanır.
    """

    def __init__(self, tipler: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Yeni Parametre Ekle")
        self.setMinimumWidth(500)
        self.setModal(True)
        self._tipler = tipler
        self._secenekler = []  # ["Çift Cidarlı", "Üç Cidarlı", ...]
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 20, 24, 20)

        baslik = QLabel("Bu parametre ile kullanıcıdan ne tür bir bilgi alacaksınız?")
        baslik.setWordWrap(True)
        baslik.setStyleSheet("font-size: 13px; color: #555; margin-bottom: 4px;")
        layout.addWidget(baslik)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Parametre Adı
        self.ad_edit = QLineEdit()
        self.ad_edit.setPlaceholderText("Örn: Kapak Tipi, Boya Rengi, Tavan Yüksekliği...")
        form.addRow("Parametre Adı *:", self.ad_edit)

        # Veri Tipi
        self.tip_combo = QComboBox()
        self.tip_combo.setMinimumHeight(32)
        for t in self._tipler:
            gorunen = t.get("gorunen_ad") or t["kod"]
            self.tip_combo.addItem(gorunen, t["id"])
        self.tip_combo.currentIndexChanged.connect(self._tip_degisti)
        form.addRow("Kullanıcı ne girecek? *:", self.tip_combo)

        # Açıklama
        self.aciklama_label = QLabel("")
        self.aciklama_label.setWordWrap(True)
        self.aciklama_label.setStyleSheet(
            "color: #888; font-size: 11px; padding: 4px 8px; "
            "background: #f8f8f8; border-radius: 4px;")
        form.addRow("", self.aciklama_label)

        # Zorunlu
        self.zorunlu_cb = QCheckBox("Bu alan zorunlu olsun (kullanıcı boş bırakamasın)")
        form.addRow("", self.zorunlu_cb)

        # Varsayılan değer
        self.varsayilan_edit = QLineEdit()
        self.varsayilan_edit.setPlaceholderText("Boş bırakılabilir")
        form.addRow("Başlangıç değeri:", self.varsayilan_edit)

        # Birim seçimi
        self.birim_combo = QComboBox()
        self.birim_combo.setMinimumHeight(28)
        self.birim_combo.addItem("— Birim yok —", "")
        self._birim_listesi = [
            ("adet", "Adet"), ("m", "Metre (m)"), ("cm", "Santimetre (cm)"),
            ("mm", "Milimetre (mm)"), ("m²", "Metrekare (m²)"),
            ("m³", "Metreküp (m³)"), ("kg", "Kilogram (kg)"),
            ("g", "Gram (g)"), ("ton", "Ton"), ("lt", "Litre (lt)"),
            ("₺", "Türk Lirası (₺)"), ("€", "Euro (€)"),
            ("$", "Dolar ($)"), ("£", "Sterlin (£)"),
            ("%", "Yüzde (%)"), ("kW", "Kilowatt (kW)"),
            ("HP", "Beygir Gücü (HP)"), ("BTU", "BTU"),
        ]
        for kod, ad in self._birim_listesi:
            self.birim_combo.addItem(ad, kod)
        form.addRow("Birim:", self.birim_combo)

        layout.addLayout(form)

        # ── SEÇENEK ALANI (sadece dropdown tipinde görünür) ──
        self.secenek_group = QGroupBox("Seçenekler")
        self.secenek_group.setStyleSheet(
            "QGroupBox { font-weight: bold; margin-top: 8px; }")
        sg_layout = QVBoxLayout(self.secenek_group)
        sg_layout.setSpacing(8)

        sg_layout.addWidget(QLabel(
            "Kullanıcının seçebileceği değerleri tek tek ekleyin:"))

        # Seçenek listesi
        self.secenek_listesi = QTableWidget()
        _tablo_ayarla(self.secenek_listesi)
        self.secenek_listesi.setColumnCount(2)
        self.secenek_listesi.setHorizontalHeaderLabels(["Seçenek", ""])
        self.secenek_listesi.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch)
        self.secenek_listesi.setColumnWidth(1, 40)
        self.secenek_listesi.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.secenek_listesi.setMaximumHeight(140)
        sg_layout.addWidget(self.secenek_listesi)

        # Yeni seçenek ekleme satırı
        ekle_row = QHBoxLayout()
        self.secenek_input = QLineEdit()
        self.secenek_input.setPlaceholderText("Yeni seçenek yazın...")
        self.secenek_input.returnPressed.connect(self._secenek_ekle)
        self.btn_secenek_ekle = QPushButton("+ Ekle")
        self.btn_secenek_ekle.clicked.connect(self._secenek_ekle)
        ekle_row.addWidget(self.secenek_input)
        ekle_row.addWidget(self.btn_secenek_ekle)
        sg_layout.addLayout(ekle_row)

        self.secenek_group.hide()  # Başta gizli
        layout.addWidget(self.secenek_group)

        # Butonlar
        br = QHBoxLayout()
        btn_iptal = QPushButton("İptal")
        btn_iptal.clicked.connect(self.reject)
        self.btn_kaydet = QPushButton("Ekle")
        self.btn_kaydet.setObjectName("primary")
        self.btn_kaydet.setMinimumHeight(36)
        self.btn_kaydet.clicked.connect(self._kaydet)
        br.addWidget(btn_iptal)
        br.addWidget(self.btn_kaydet)
        layout.addLayout(br)

        self._tip_degisti()
        self.ad_edit.setFocus()

    def _secili_tip_kodu(self) -> str:
        idx = self.tip_combo.currentIndex()
        if 0 <= idx < len(self._tipler):
            return self._tipler[idx]["kod"]
        return ""

    def _tip_degisti(self):
        idx = self.tip_combo.currentIndex()
        if 0 <= idx < len(self._tipler):
            t = self._tipler[idx]
            aciklama = t.get("aciklama") or ""
            birim = t.get("birim") or ""
            text = aciklama
            if birim:
                text += f"\nVarsayılan birim: {birim}"
            if not aciklama:
                _ACIKLAMA = {
                    "int": "Adet, kat sayısı gibi tam sayı değerler",
                    "float": "Ölçüm sonuçları, katsayılar gibi noktalı sayılar",
                    "string": "Serbest yazı alanı (açıklama, not, isim vb.)",
                    "dropdown": "Önceden tanımlı seçeneklerden biri seçilir",
                    "para": "Para tutarı girilir (TL, Euro, Dolar vb.)",
                    "olcu_birimi": "Uzunluk, alan, hacim, ağırlık gibi ölçü değerleri",
                    "boolean": "Açık/Kapalı, Var/Yok gibi iki seçenekli değer",
                    "tarih": "Gün/Ay/Yıl formatında tarih seçimi",
                    "yuzde": "Yüzde oranı (ör: %15 kar, %18 KDV)",
                }
                text = _ACIKLAMA.get(t["kod"], "")
            self.aciklama_label.setText(text)

        # Seçenek alanı: sadece dropdown tipinde göster
        dropdown_mu = self._secili_tip_kodu() == "dropdown"
        self.secenek_group.setVisible(dropdown_mu)
        if dropdown_mu:
            self.varsayilan_edit.setPlaceholderText(
                "Seçeneklerden birinin adını yazın (opsiyonel)")
        else:
            self.varsayilan_edit.setPlaceholderText("Boş bırakılabilir")

    def _secenek_ekle(self):
        deger = self.secenek_input.text().strip()
        if not deger:
            return
        if deger in self._secenekler:
            QMessageBox.information(self, "Uyarı", "Bu seçenek zaten ekli.")
            return
        self._secenekler.append(deger)
        self._secenek_tablosu_guncelle()
        self.secenek_input.clear()
        self.secenek_input.setFocus()

    def _secenek_sil(self, idx: int):
        if 0 <= idx < len(self._secenekler):
            self._secenekler.pop(idx)
            self._secenek_tablosu_guncelle()

    def _secenek_tablosu_guncelle(self):
        self.secenek_listesi.setRowCount(len(self._secenekler))
        for i, s in enumerate(self._secenekler):
            self.secenek_listesi.setItem(i, 0, QTableWidgetItem(s))
            btn = _tablo_butonu("✕")
            btn.clicked.connect(lambda _, idx=i: self._secenek_sil(idx))
            self.secenek_listesi.setCellWidget(i, 1, btn)

    def _kaydet(self):
        ad = self.ad_edit.text().strip()
        if not ad:
            QMessageBox.warning(self, "Uyarı", "Parametre adı boş olamaz.")
            return
        if self._secili_tip_kodu() == "dropdown" and len(self._secenekler) < 2:
            QMessageBox.warning(
                self, "Uyarı",
                "Seçenek Listesi tipi için en az 2 seçenek eklemelisiniz.")
            return
        self.accept()

    def veri(self) -> dict:
        return {
            "ad": self.ad_edit.text().strip(),
            "tip_id": self.tip_combo.currentData(),
            "zorunlu": self.zorunlu_cb.isChecked(),
            "varsayilan": self.varsayilan_edit.text().strip(),
            "secenekler": list(self._secenekler),
            "birim": self.birim_combo.currentData() or "",
        }


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
        _tablo_ayarla(self.table)
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
        _tablo_ayarla(self.param_table)
        self.param_table.setColumnCount(6)
        self.param_table.setHorizontalHeaderLabels(
            ["Ad", "Tip", "Birim", "Zorunlu", "Varsayılan", ""])
        self.param_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.param_table.setColumnWidth(2, 60)
        self.param_table.setColumnWidth(5, 50)
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
        _tablo_ayarla(self.ak_table)
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
            tip_gorunen = self._tip_gorunen_ad(p.get("tip_kodu", ""))
            self.param_table.setItem(i, 1, QTableWidgetItem(tip_gorunen))
            self.param_table.setItem(i, 2, QTableWidgetItem(p.get("birim", "") or "—"))
            self.param_table.setItem(i, 3, QTableWidgetItem("✓" if p["zorunlu"] else "—"))
            self.param_table.setItem(i, 4, QTableWidgetItem(p["varsayilan_deger"]))
            btn = _tablo_butonu("✕")
            btn.clicked.connect(lambda _, pid=p["id"]: self._parametre_sil(pid))
            self.param_table.setCellWidget(i, 5, btn)

    def _tip_gorunen_ad(self, tip_kodu: str) -> str:
        """Teknik tip kodunu kullanıcı dostu isme çevirir."""
        for t in self._tipler:
            if t["kod"] == tip_kodu:
                return t.get("gorunen_ad") or tip_kodu
        # Fallback — gorunen_ad yoksa (eski DB) elle eşle
        _FALLBACK = {
            "int": "Tam Sayı (Adet)", "float": "Ondalıklı Sayı",
            "string": "Metin", "dropdown": "Seçenek Listesi",
            "para": "Para (₺/€/$)", "olcu_birimi": "Ölçü (m, m², m³, kg)",
            "boolean": "Evet / Hayır", "tarih": "Tarih", "yuzde": "Yüzde (%)",
        }
        return _FALLBACK.get(tip_kodu, tip_kodu)

    def _alt_kalemleri_yukle(self):
        if not self._urun_ver_id or not self.em_repo: return
        self._alt_kalemler = self.em_repo.urun_versiyonuna_bagli_alt_kalemler(
            self._urun_ver_id)
        self.ak_table.setRowCount(len(self._alt_kalemler))
        for i, ak in enumerate(self._alt_kalemler):
            self.ak_table.setItem(i, 0, QTableWidgetItem(ak["alt_kalem_adi"]))
            self.ak_table.setItem(i, 1, QTableWidgetItem("✓" if ak["aktif_mi"] else "—"))
            self.ak_table.setItem(i, 2, QTableWidgetItem(f"v{ak['versiyon_no']}"))
            btn = _tablo_butonu("Aç", 42)
            btn.clicked.connect(
                lambda _, akid=ak["alt_kalem_id"], vid=self._urun_ver_id:
                self.alt_kalem_sec.emit(akid, vid))
            self.ak_table.setCellWidget(i, 3, btn)

    def _parametre_ekle(self):
        if not self._urun_ver_id or not self.em_repo: return

        dialog = ParametreEkleDialog(self._tipler, self)
        if dialog.exec_():
            veri = dialog.veri()
            param_id = self.em_repo.urun_parametre_ekle(
                self._urun_ver_id, veri["ad"], veri["tip_id"],
                1 if veri["zorunlu"] else 0, veri["varsayilan"],
                len(self._params) + 1, birim=veri.get("birim", ""))
            # Dropdown seçeneklerini kaydet
            for i, sec in enumerate(veri.get("secenekler", [])):
                self.em_repo.dropdown_deger_ekle(param_id, sec, i + 1)
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
        _tablo_ayarla(self.table)
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
                btn = _tablo_butonu("Gör", 38)
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
        _tablo_ayarla(self.degisken_table)
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
        _tablo_ayarla(self.param_table)
        self.param_table.setColumnCount(7)
        self.param_table.setHorizontalHeaderLabels(
            ["Ad", "Tip", "Birim", "Zorunlu", "Varsayılan", "Ürün Ref", ""])
        self.param_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.param_table.setColumnWidth(2, 55)
        self.param_table.setColumnWidth(6, 40)
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
            tip_gorunen = self._tip_gorunen_ad(p.get("tip_kodu", ""))
            self.param_table.setItem(i, 1, QTableWidgetItem(tip_gorunen))
            self.param_table.setItem(i, 2, QTableWidgetItem(p.get("birim", "") or "—"))
            self.param_table.setItem(i, 3, QTableWidgetItem("✓" if p["zorunlu"] else "—"))
            self.param_table.setItem(i, 4, QTableWidgetItem(p["varsayilan_deger"]))
            ref = p.get("urun_param_ref_id") or ""
            self.param_table.setItem(i, 5, QTableWidgetItem("Ref" if ref else "—"))
            btn = _tablo_butonu("✕")
            btn.clicked.connect(lambda _, pid=p["id"]: self._parametre_sil(pid))
            self.param_table.setCellWidget(i, 6, btn)

    def _tip_gorunen_ad(self, tip_kodu: str) -> str:
        for t in self._tipler:
            if t["kod"] == tip_kodu:
                return t.get("gorunen_ad") or tip_kodu
        _FALLBACK = {
            "int": "Tam Sayı (Adet)", "float": "Ondalıklı Sayı",
            "string": "Metin", "dropdown": "Seçenek Listesi",
            "para": "Para (₺/€/$)", "olcu_birimi": "Ölçü (m, m², m³, kg)",
            "boolean": "Evet / Hayır", "tarih": "Tarih", "yuzde": "Yüzde (%)",
        }
        return _FALLBACK.get(tip_kodu, tip_kodu)

    def _parametre_ekle(self):
        if not self._akv_id or not self.em_repo: return
        dialog = ParametreEkleDialog(self._tipler, self)
        if dialog.exec_():
            veri = dialog.veri()
            param_id = self.em_repo.alt_kalem_parametre_ekle(
                self._akv_id, veri["ad"], veri["tip_id"],
                1 if veri["zorunlu"] else 0, veri["varsayilan"],
                sira=len(self._params) + 1,
                birim=veri.get("birim", ""))
            for i, sec in enumerate(veri.get("secenekler", [])):
                self.em_repo.dropdown_deger_ekle(param_id, sec, i + 1)
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
