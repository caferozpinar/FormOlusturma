#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Placeholder Yönetim Arayüzü.
Sol: Placeholder listesi + CRUD
Sağ: Seçili placeholder kuralları
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QLineEdit, QComboBox, QCheckBox, QMessageBox, QDialog,
    QFormLayout, QGroupBox, QSplitter, QTextEdit, QInputDialog
)
from PyQt5.QtCore import Qt

from uygulama.ortak.yardimcilar import logger_olustur
from uygulama.arayuz.admin_urun_sayfa import _tablo_ayarla, _tablo_butonu

logger = logger_olustur("placeholder_sayfa")


class PlaceholderYonetimWidget(QWidget):
    """Admin Placeholder yönetim ekranı."""

    def __init__(self, placeholder_srv=None, em_repo=None,
                 urun_servisi=None, parent=None):
        super().__init__(parent)
        self.ph_srv = placeholder_srv
        self.em_repo = em_repo
        self.urun_servisi = urun_servisi
        self._placeholders = []
        self._secili_ph_id = None
        self._kurallar = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        splitter = QSplitter(Qt.Horizontal)

        # ── SOL: Placeholder listesi ──
        sol = QWidget()
        sl = QVBoxLayout(sol); sl.setSpacing(8)
        sl.addWidget(QLabel("Placeholder Listesi"))

        self.ph_table = QTableWidget()
        _tablo_ayarla(self.ph_table)
        self.ph_table.setColumnCount(3)
        self.ph_table.setHorizontalHeaderLabels(["Kod", "Ad", ""])
        self.ph_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.ph_table.setColumnWidth(1, 150)
        self.ph_table.setColumnWidth(2, 40)
        self.ph_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ph_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ph_table.clicked.connect(self._ph_secildi)
        sl.addWidget(self.ph_table)

        pb = QHBoxLayout()
        self.btn_ph_ekle = QPushButton("+ Yeni Placeholder")
        self.btn_ph_ekle.setObjectName("primary")
        self.btn_ph_ekle.clicked.connect(self._ph_ekle)
        pb.addWidget(self.btn_ph_ekle); pb.addStretch()
        sl.addLayout(pb)
        splitter.addWidget(sol)

        # ── SAĞ: Kural detay ──
        sag = QWidget()
        sgl = QVBoxLayout(sag); sgl.setSpacing(8)

        self.kural_baslik = QLabel("Placeholder seçin")
        self.kural_baslik.setStyleSheet("font-size: 14px; font-weight: bold;")
        sgl.addWidget(self.kural_baslik)

        self.kural_aciklama = QLabel("")
        self.kural_aciklama.setStyleSheet("color: #666;")
        sgl.addWidget(self.kural_aciklama)

        sgl.addWidget(QLabel("Kurallar (sıralı — ilk eşleşen çalışır):"))
        self.kural_table = QTableWidget()
        _tablo_ayarla(self.kural_table)
        self.kural_table.setColumnCount(6)
        self.kural_table.setHorizontalHeaderLabels(
            ["Sıra", "Tip", "Parametre", "Koşul", "Sonuç", ""])
        self.kural_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.kural_table.setColumnWidth(0, 40)
        self.kural_table.setColumnWidth(5, 40)
        self.kural_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        sgl.addWidget(self.kural_table)

        kb = QHBoxLayout()
        self.btn_kural_ekle = QPushButton("+ Kural Ekle")
        self.btn_kural_ekle.clicked.connect(self._kural_ekle)
        kb.addWidget(self.btn_kural_ekle); kb.addStretch()
        sgl.addLayout(kb)
        splitter.addWidget(sag)

        splitter.setSizes([300, 500])
        layout.addWidget(splitter)

    def yukle(self):
        if not self.ph_srv: return
        self._placeholders = self.ph_srv.placeholder_listele(sadece_aktif=True)
        self.ph_table.setRowCount(len(self._placeholders))
        for i, p in enumerate(self._placeholders):
            self.ph_table.setItem(i, 0, QTableWidgetItem(p["kod"]))
            self.ph_table.setItem(i, 1, QTableWidgetItem(p["ad"]))
            btn = _tablo_butonu("✕")
            btn.clicked.connect(
                lambda _, pid=p["id"]: self._ph_sil(pid))
            self.ph_table.setCellWidget(i, 2, btn)

    def _ph_secildi(self, idx=None):
        row = self.ph_table.currentRow()
        if 0 <= row < len(self._placeholders):
            ph = self._placeholders[row]
            self._secili_ph_id = ph["id"]
            self.kural_baslik.setText(ph["kod"])
            self.kural_aciklama.setText(ph.get("aciklama", ""))
            self._kurallari_yukle()

    def _kurallari_yukle(self):
        if not self._secili_ph_id or not self.ph_srv: return
        self._kurallar = self.ph_srv.kurallar(self._secili_ph_id)
        self.kural_table.setRowCount(len(self._kurallar))

        TIP_LABEL = {
            "dogrudan": "Doğrudan Al",
            "esitlik": "Eşitlik",
            "karsilastirma": "Karşılaştırma",
            "birlestirme": "Birleştirme",
            "sablon": "Şablon",
        }

        for i, k in enumerate(self._kurallar):
            self.kural_table.setItem(i, 0, QTableWidgetItem(str(k["sira"])))
            tip_txt = TIP_LABEL.get(k["kural_tipi"], k["kural_tipi"])
            if k["varsayilan_mi"]:
                tip_txt += " ★"
            self.kural_table.setItem(i, 1, QTableWidgetItem(tip_txt))
            self.kural_table.setItem(i, 2, QTableWidgetItem(k["parametre_adi"]))
            kosul = f"{k['operator']} {k['kosul_degeri']}" if k["kural_tipi"] in ("esitlik", "karsilastirma") else "—"
            self.kural_table.setItem(i, 3, QTableWidgetItem(kosul))
            sonuc = k["sonuc_metni"][:50] + ("..." if len(k["sonuc_metni"]) > 50 else "")
            self.kural_table.setItem(i, 4, QTableWidgetItem(sonuc))
            btn = _tablo_butonu("✕")
            btn.clicked.connect(
                lambda _, kid=k["id"]: self._kural_sil(kid))
            self.kural_table.setCellWidget(i, 5, btn)

    def _ph_ekle(self):
        if not self.ph_srv: return
        dialog = PlaceholderEkleDialog(self)
        if dialog.exec_():
            veri = dialog.veri()
            ok, msg, _ = self.ph_srv.placeholder_olustur(
                veri["kod"], veri["ad"], veri["aciklama"])
            if not ok:
                QMessageBox.warning(self, "Hata", msg)
            self.yukle()

    def _ph_sil(self, pid):
        if QMessageBox.question(self, "Sil", "Placeholder silinsin mi?") == QMessageBox.Yes:
            self.ph_srv.placeholder_sil(pid)
            self._secili_ph_id = None
            self.kural_table.setRowCount(0)
            self.kural_baslik.setText("Placeholder seçin")
            self.yukle()

    def _kural_ekle(self):
        if not self._secili_ph_id or not self.ph_srv: return
        # Parametre listesi hazırla
        param_listesi = self._parametre_listesi_hazirla()
        dialog = KuralEkleDialog(param_listesi, self)
        if dialog.exec_():
            v = dialog.veri()
            ok, msg, _ = self.ph_srv.kural_ekle(
                self._secili_ph_id, v["kural_tipi"], v["parametre_kaynak"],
                v["parametre_adi"], v["operator"], v["kosul_degeri"],
                v["sonuc_metni"], v["varsayilan_mi"])
            if not ok:
                QMessageBox.warning(self, "Hata", msg)
            self._kurallari_yukle()

    def _kural_sil(self, kid):
        self.ph_srv.kural_sil(kid)
        self._kurallari_yukle()

    def _parametre_listesi_hazirla(self) -> list[tuple[str, str, str]]:
        """[(kaynak, parametre_adi, gorunen_ad), ...]"""
        params = []
        # Proje bilgileri
        from uygulama.altyapi.placeholder_repo import PROJE_BILGI_ALANLARI
        for p in PROJE_BILGI_ALANLARI:
            params.append(("proje_bilgi", p, f"📋 {p}"))

        # Ürün parametreleri (tüm ürünlerden)
        if self.em_repo:
            if self.urun_servisi:
                urunler = self.urun_servisi.listele(sadece_aktif=True)
                for u in urunler:
                    ver = self.em_repo.aktif_urun_versiyon(u.id)
                    if ver:
                        for p in self.em_repo.urun_parametreleri(ver["id"]):
                            params.append(("urun_param", p["ad"],
                                           f"📦 {u.kod} → {p['ad']}"))
                        # Alt kalem parametreleri
                        for ak in self.em_repo.urun_versiyonuna_bagli_alt_kalemler(ver["id"]):
                            for akp in self.em_repo.alt_kalem_parametreleri(ak["id"]):
                                params.append(("alt_kalem_param", akp["ad"],
                                               f"🔧 {ak['alt_kalem_adi']} → {akp['ad']}"))
        return params


# ═══════════════════════════════════════
# DİALOGLAR
# ═══════════════════════════════════════

class PlaceholderEkleDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Yeni Placeholder")
        self.setFixedWidth(440); self.setModal(True)
        layout = QVBoxLayout(self); layout.setSpacing(12)
        layout.setContentsMargins(24, 20, 24, 20)

        form = QFormLayout(); form.setSpacing(10)
        self.kod_edit = QLineEdit()
        self.kod_edit.setPlaceholderText("Örn: BASLIK, URUNTIPI, SERI_NO")
        form.addRow("Placeholder Kodu *:", self.kod_edit)
        info = QLabel("Otomatik {/KOD/} formatına çevrilir")
        info.setStyleSheet("color: #888; font-size: 11px;")
        form.addRow("", info)
        self.ad_edit = QLineEdit()
        self.ad_edit.setPlaceholderText("Görünen ad (opsiyonel)")
        form.addRow("Ad:", self.ad_edit)
        self.aciklama_edit = QLineEdit()
        self.aciklama_edit.setPlaceholderText("Ne işe yaradığını açıklayın")
        form.addRow("Açıklama:", self.aciklama_edit)
        layout.addLayout(form)

        br = QHBoxLayout()
        btn_iptal = QPushButton("İptal"); btn_iptal.clicked.connect(self.reject)
        btn_ok = QPushButton("Oluştur"); btn_ok.setObjectName("primary")
        btn_ok.clicked.connect(self._kaydet)
        br.addWidget(btn_iptal); br.addWidget(btn_ok)
        layout.addLayout(br)

    def _kaydet(self):
        if not self.kod_edit.text().strip():
            QMessageBox.warning(self, "Uyarı", "Kod boş olamaz."); return
        self.accept()

    def veri(self):
        return {
            "kod": self.kod_edit.text().strip(),
            "ad": self.ad_edit.text().strip(),
            "aciklama": self.aciklama_edit.text().strip(),
        }


class KuralEkleDialog(QDialog):
    """Placeholder kuralı ekleme dialog'u."""

    def __init__(self, param_listesi: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kural Ekle")
        self.setMinimumWidth(520); self.setModal(True)
        self._param_listesi = param_listesi
        self._build()

    def _build(self):
        layout = QVBoxLayout(self); layout.setSpacing(12)
        layout.setContentsMargins(24, 20, 24, 20)

        form = QFormLayout(); form.setSpacing(10)

        # Kural tipi
        self.tip_combo = QComboBox()
        from uygulama.servisler.placeholder_servisi import PlaceholderServisi
        for kod, aciklama in PlaceholderServisi.kural_tipleri_listesi():
            self.tip_combo.addItem(aciklama, kod)
        self.tip_combo.currentIndexChanged.connect(self._tip_degisti)
        form.addRow("Kural Tipi:", self.tip_combo)

        # Parametre seçimi
        self.param_combo = QComboBox()
        self.param_combo.setMinimumWidth(300)
        for kaynak, adi, gorunen in self._param_listesi:
            self.param_combo.addItem(gorunen, (kaynak, adi))
        # Boş (birleştirme/şablon için)
        self.param_combo.addItem("— (Şablon/Birleştirme için boş)", ("urun_param", ""))
        form.addRow("Parametre:", self.param_combo)

        # Operatör
        self.op_combo = QComboBox()
        for kod, aciklama in PlaceholderServisi.operator_listesi():
            self.op_combo.addItem(f"{kod}  ({aciklama})", kod)
        form.addRow("Operatör:", self.op_combo)

        # Koşul değeri
        self.kosul_edit = QLineEdit()
        self.kosul_edit.setPlaceholderText("Karşılaştırılacak değer")
        form.addRow("Koşul Değeri:", self.kosul_edit)

        # Sonuç metni
        self.sonuc_edit = QTextEdit()
        self.sonuc_edit.setMaximumHeight(80)
        self.sonuc_edit.setPlaceholderText(
            "Koşul sağlandığında yazılacak metin\n"
            "Birleştirme: {PARAM_ADI} x {PARAM_ADI2}\n"
            "Şablon: Kanat: {KANAT MALZEMESİ}, Motor: {MOTOR MALZEMESİ}")
        form.addRow("Sonuç Metni:", self.sonuc_edit)

        # Varsayılan mı
        self.varsayilan_cb = QCheckBox(
            "Varsayılan kural (hiçbir koşul tutmazsa bu çalışır)")
        form.addRow("", self.varsayilan_cb)

        layout.addLayout(form)

        # Açıklama
        self.aciklama = QLabel("")
        self.aciklama.setWordWrap(True)
        self.aciklama.setStyleSheet(
            "color: #666; font-size: 11px; padding: 6px; "
            "background: #f8f8f8; border-radius: 4px;")
        layout.addWidget(self.aciklama)

        br = QHBoxLayout()
        btn_iptal = QPushButton("İptal"); btn_iptal.clicked.connect(self.reject)
        btn_ok = QPushButton("Ekle"); btn_ok.setObjectName("primary")
        btn_ok.clicked.connect(self._kaydet)
        br.addWidget(btn_iptal); br.addWidget(btn_ok)
        layout.addLayout(br)

        self._tip_degisti()

    def _tip_degisti(self):
        tip = self.tip_combo.currentData()
        # Operatör ve koşul alanlarını göster/gizle
        gizle_kosul = tip in ("dogrudan", "birlestirme", "sablon")
        self.op_combo.setEnabled(not gizle_kosul)
        self.kosul_edit.setEnabled(not gizle_kosul)

        aciklamalar = {
            "dogrudan": "Seçilen parametrenin değeri aynen placeholder'a yazılır.",
            "esitlik": "Parametre belirli bir değere eşitse sonuç metni yazılır.\nÖrn: KANAT MALZEMESİ = 'Çelik' → 'Çelik kanat sistemi'",
            "karsilastirma": "Parametre sayısal koşulu sağlarsa sonuç metni yazılır.\nÖrn: KANAT ÖLÇÜSÜ > 300 → 'Büyük kanat'",
            "birlestirme": "Sonuç metninde {PARAM_ADI} şeklinde parametreleri birleştirin.\nÖrn: {KANAT MALZEMESİ} x {MOTOR MALZEMESİ}",
            "sablon": "Serbest şablon — Sonuç metnine {PARAM_ADI} yerleştirin.\nÖrn: Kanat: {KANAT MALZEMESİ}, Ölçü: {KANAT ÖLÇÜSÜ}mm",
        }
        self.aciklama.setText(aciklamalar.get(tip, ""))

    def _kaydet(self):
        tip = self.tip_combo.currentData()
        sonuc = self.sonuc_edit.toPlainText().strip()
        if tip not in ("dogrudan",) and not sonuc:
            QMessageBox.warning(self, "Uyarı", "Sonuç metni boş olamaz.")
            return
        self.accept()

    def veri(self) -> dict:
        param_data = self.param_combo.currentData() or ("urun_param", "")
        return {
            "kural_tipi": self.tip_combo.currentData(),
            "parametre_kaynak": param_data[0],
            "parametre_adi": param_data[1],
            "operator": self.op_combo.currentData() or "=",
            "kosul_degeri": self.kosul_edit.text().strip(),
            "sonuc_metni": self.sonuc_edit.toPlainText().strip(),
            "varsayilan_mi": self.varsayilan_cb.isChecked(),
        }
