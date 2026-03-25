#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Admin Paneli — Backend entegreli ürün, alan, seçenek, kullanıcı yönetimi."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableView, QTabWidget, QFrame, QMessageBox, QLineEdit,
    QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox,
    QFormLayout, QDialog, QDialogButtonBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from uygulama.arayuz.ui_yardimcilar import SimpleTableModel, setup_table, sarma_buton_yetkisi


# ═══════════════════════════════════════════════════════
# DIALOG SINIFLARI
# ═══════════════════════════════════════════════════════

class KullaniciEkleDialog(QDialog):
    """Yeni kullanıcı ekleme formu."""

    def __init__(self, parent=None):
        super().__init__(parent)
        from uygulama.domain.modeller import KullaniciRolu
        self.setWindowTitle("Kullanıcı Ekle")
        self.setModal(True)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(16)

        baslik = QLabel("Yeni Kullanıcı")
        baslik.setObjectName("sectionTitle")
        layout.addWidget(baslik)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setSpacing(10)

        self._ad = QLineEdit()
        self._ad.setPlaceholderText("İsim")
        form.addRow("İsim *", self._ad)

        self._soyad = QLineEdit()
        self._soyad.setPlaceholderText("Soy İsim")
        form.addRow("Soy İsim", self._soyad)

        self._email = QLineEdit()
        self._email.setPlaceholderText("ornek@sirket.com")
        form.addRow("E-posta *", self._email)

        sifre_row = QHBoxLayout()
        self._sifre = QLineEdit()
        self._sifre.setPlaceholderText("En az 6 karakter")
        self._sifre.setEchoMode(QLineEdit.Password)
        self._goster_btn = QPushButton("Göster")
        self._goster_btn.setCheckable(True)
        self._goster_btn.setFixedWidth(64)
        self._goster_btn.toggled.connect(
            lambda checked: self._sifre.setEchoMode(
                QLineEdit.Normal if checked else QLineEdit.Password
            )
        )
        sifre_row.addWidget(self._sifre)
        sifre_row.addWidget(self._goster_btn)
        form.addRow("Şifre *", sifre_row)

        self._rol = QComboBox()
        for r in KullaniciRolu:
            self._rol.addItem(r.value, r)
        self._rol.setCurrentIndex(1)  # Editor varsayılan
        form.addRow("Rol", self._rol)

        layout.addLayout(form)

        self._hata = QLabel("")
        self._hata.setObjectName("error")
        self._hata.hide()
        layout.addWidget(self._hata)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        iptal = QPushButton("İptal")
        iptal.clicked.connect(self.reject)
        self._olustur_btn = QPushButton("Kullanıcı Oluştur")
        self._olustur_btn.setObjectName("primary")
        self._olustur_btn.setMinimumHeight(36)
        self._olustur_btn.setEnabled(False)
        self._olustur_btn.clicked.connect(self._dogrula_ve_kabul)
        btn_row.addWidget(iptal)
        btn_row.addWidget(self._olustur_btn)
        layout.addLayout(btn_row)

        for w in [self._ad, self._email, self._sifre]:
            w.textChanged.connect(self._validasyon_guncelle)

    def _validasyon_guncelle(self):
        dolu = all([
            self._ad.text().strip(),
            self._email.text().strip(),
            self._sifre.text(),
        ])
        self._olustur_btn.setEnabled(dolu)

    def _dogrula_ve_kabul(self):
        email = self._email.text().strip()
        if "@" not in email:
            self._hata.setText("Geçerli bir e-posta adresi girin.")
            self._hata.show()
            return
        if len(self._sifre.text()) < 6:
            self._hata.setText("Şifre en az 6 karakter olmalıdır.")
            self._hata.show()
            return
        self._hata.hide()
        self.accept()

    def veri(self) -> dict:
        return {
            "ad": self._ad.text().strip(),
            "soyad": self._soyad.text().strip(),
            "email": self._email.text().strip(),
            "sifre": self._sifre.text(),
            "rol": self._rol.currentData(),
        }


class KullaniciDuzenleDialog(QDialog):
    """Mevcut kullanıcı bilgilerini düzenleme formu."""

    def __init__(self, kullanici, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kullanıcı Düzenle")
        self.setModal(True)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(16)

        baslik = QLabel("Kullanıcıyı Düzenle")
        baslik.setObjectName("sectionTitle")
        layout.addWidget(baslik)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setSpacing(10)

        self._ad = QLineEdit(kullanici.ad)
        form.addRow("İsim *", self._ad)

        self._soyad = QLineEdit(kullanici.soyad)
        form.addRow("Soy İsim", self._soyad)

        self._email = QLineEdit(kullanici.email)
        form.addRow("E-posta *", self._email)

        sifre_row = QHBoxLayout()
        self._sifre = QLineEdit()
        self._sifre.setPlaceholderText("Boş bırakılırsa değişmez")
        self._sifre.setEchoMode(QLineEdit.Password)
        self._goster_btn = QPushButton("Göster")
        self._goster_btn.setCheckable(True)
        self._goster_btn.setFixedWidth(64)
        self._goster_btn.toggled.connect(
            lambda checked: self._sifre.setEchoMode(
                QLineEdit.Normal if checked else QLineEdit.Password
            )
        )
        sifre_row.addWidget(self._sifre)
        sifre_row.addWidget(self._goster_btn)
        form.addRow("Yeni Şifre", sifre_row)

        layout.addLayout(form)

        self._hata = QLabel("")
        self._hata.setObjectName("error")
        self._hata.hide()
        layout.addWidget(self._hata)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        iptal = QPushButton("İptal")
        iptal.clicked.connect(self.reject)
        self._kaydet_btn = QPushButton("Kaydet")
        self._kaydet_btn.setObjectName("primary")
        self._kaydet_btn.setMinimumHeight(36)
        self._kaydet_btn.clicked.connect(self._dogrula_ve_kabul)
        btn_row.addWidget(iptal)
        btn_row.addWidget(self._kaydet_btn)
        layout.addLayout(btn_row)

        for w in [self._ad, self._email]:
            w.textChanged.connect(self._validasyon_guncelle)
        self._validasyon_guncelle()

    def _validasyon_guncelle(self):
        dolu = bool(self._ad.text().strip() and self._email.text().strip())
        self._kaydet_btn.setEnabled(dolu)

    def _dogrula_ve_kabul(self):
        email = self._email.text().strip()
        if "@" not in email:
            self._hata.setText("Geçerli bir e-posta adresi girin.")
            self._hata.show()
            return
        sifre = self._sifre.text()
        if sifre and len(sifre) < 6:
            self._hata.setText("Şifre en az 6 karakter olmalıdır.")
            self._hata.show()
            return
        self._hata.hide()
        self.accept()

    def veri(self) -> dict:
        return {
            "ad": self._ad.text().strip(),
            "soyad": self._soyad.text().strip(),
            "email": self._email.text().strip(),
            "yeni_sifre": self._sifre.text(),
        }


class RolDegistirDialog(QDialog):
    """Kullanıcı rolü değiştirme formu."""

    def __init__(self, kullanici_adi: str, mevcut_rol, parent=None):
        super().__init__(parent)
        from uygulama.domain.modeller import KullaniciRolu
        self.setWindowTitle("Rol Değiştir")
        self.setModal(True)
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setSpacing(10)

        k_label = QLabel(kullanici_adi)
        k_label.setStyleSheet("font-weight: 600;")
        form.addRow("Kullanıcı", k_label)

        self._rol = QComboBox()
        for r in KullaniciRolu:
            self._rol.addItem(r.value, r)
            if r == mevcut_rol:
                self._rol.setCurrentIndex(self._rol.count() - 1)
        form.addRow("Yeni Rol", self._rol)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        iptal = QPushButton("İptal")
        iptal.clicked.connect(self.reject)
        kaydet = QPushButton("Kaydet")
        kaydet.setObjectName("primary")
        kaydet.setMinimumHeight(36)
        kaydet.clicked.connect(self.accept)
        btn_row.addWidget(iptal)
        btn_row.addWidget(kaydet)
        layout.addLayout(btn_row)

    def veri(self):
        return self._rol.currentData()


class AdEkleDialog(QDialog):
    """Tek alan gerektiren ekleme formu (Ülke, Şehir, Tesis Türü)."""

    def __init__(self, baslik: str, etiket: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(baslik)
        self.setModal(True)
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setSpacing(10)

        self._ad = QLineEdit()
        form.addRow(etiket, self._ad)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        iptal = QPushButton("İptal")
        iptal.clicked.connect(self.reject)
        self._ekle_btn = QPushButton("Ekle")
        self._ekle_btn.setObjectName("primary")
        self._ekle_btn.setMinimumHeight(36)
        self._ekle_btn.setEnabled(False)
        self._ekle_btn.clicked.connect(self.accept)
        btn_row.addWidget(iptal)
        btn_row.addWidget(self._ekle_btn)
        layout.addLayout(btn_row)

        self._ad.textChanged.connect(
            lambda t: self._ekle_btn.setEnabled(bool(t.strip()))
        )
        self._ad.returnPressed.connect(
            lambda: self.accept() if self._ekle_btn.isEnabled() else None
        )

    def veri(self) -> str:
        return self._ad.text().strip()


class AdminPanelPage(QWidget):
    go_back = pyqtSignal()

    def __init__(self, urun_servisi=None, kimlik_servisi=None, yetki_servisi=None,
                 log_repo=None,
                 konum_servisi=None, tesis_servisi=None,
                 em_repo=None, em_srv=None,
                 placeholder_srv=None, belge_srv=None, parent=None):
        super().__init__(parent)
        self.urun_servisi = urun_servisi
        self.kimlik_servisi = kimlik_servisi
        self.yetki_servisi = yetki_servisi
        self.log_repo = log_repo
        self.konum_servisi = konum_servisi
        self.tesis_servisi = tesis_servisi
        self.em_repo = em_repo
        self.em_srv = em_srv
        self.placeholder_srv = placeholder_srv
        self.belge_srv = belge_srv
        self._kullanicilar = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(16)

        header = QHBoxLayout()
        t = QLabel("Admin Paneli"); t.setObjectName("title")
        bb = QPushButton("← Geri"); bb.clicked.connect(self.go_back.emit)
        header.addWidget(t); header.addStretch(); header.addWidget(bb)
        layout.addLayout(header)

        self.tabs = QTabWidget()
        from uygulama.arayuz.admin_urun_sayfa import AdminUrunSayfasi
        self.admin_urun = AdminUrunSayfasi(
            self.urun_servisi, self.em_repo, self.em_srv)
        self.tabs.addTab(self.admin_urun, "Ürün Yönetimi")
        # Placeholder tab
        from uygulama.arayuz.placeholder_sayfa import PlaceholderYonetimWidget
        self.placeholder_widget = PlaceholderYonetimWidget(
            self.placeholder_srv, self.em_repo, self.urun_servisi)
        self.tabs.addTab(self.placeholder_widget, "Placeholder")
        # Belge Yönetimi tab
        from uygulama.arayuz.belge_admin_sayfa import BelgeAdminSayfasi
        self.belge_admin = BelgeAdminSayfasi(
            self.belge_srv, self.urun_servisi, self.em_repo, self.yetki_servisi)
        self.tabs.addTab(self.belge_admin, "Belge Şablonları")
        self.tabs.addTab(self._build_kullanicilar_tab(), "Kullanıcılar")
        self.tabs.addTab(self._build_konum_tab(), "Konum")
        self.tabs.addTab(self._build_tesis_tab(), "Tesis Türleri")
        self.tabs.addTab(self._build_loglar_tab(), "Audit Log")
        self.tabs.addTab(self._build_yetki_tab(), "Yetkiler")
        layout.addWidget(self.tabs)

    # ── TAB BUILDERS ──

    def _build_kullanicilar_tab(self):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(16, 16, 16, 16)
        self.user_table = QTableView(); setup_table(self.user_table)
        self.user_model = SimpleTableModel(["Kullanıcı Adı", "Rol", "Aktif"])
        self.user_table.setModel(self.user_model); l.addWidget(self.user_table)
        br = QHBoxLayout()
        
        b_ekle = QPushButton("+ Kullanıcı Ekle")
        b_ekle.setObjectName("primary")
        sarma_buton_yetkisi(b_ekle, "kullanici_olustur", self.yetki_servisi, self._kullanici_ekle)
        
        b_duzenle = QPushButton("Düzenle")
        sarma_buton_yetkisi(b_duzenle, "kullanici_guncelle", self.yetki_servisi, self._kullanici_duzenle)

        b_rol = QPushButton("Rol Değiştir")
        sarma_buton_yetkisi(b_rol, "kullanici_rol_degistir", self.yetki_servisi, self._rol_degistir)

        b_deaktif = QPushButton("Deaktif Et")
        b_deaktif.setObjectName("danger")
        sarma_buton_yetkisi(b_deaktif, "kullanici_sil", self.yetki_servisi, self._kullanici_deaktif)

        br.addWidget(b_ekle)
        br.addWidget(b_duzenle)
        br.addWidget(b_rol)
        br.addWidget(b_deaktif)
        br.addStretch()
        l.addLayout(br)
        return w

    # ── VERİ YÜKLEME ──
    def sayfa_gosterildi(self):
        self.admin_urun.yukle()
        if hasattr(self, 'placeholder_widget'):
            self.placeholder_widget.yukle()
        if hasattr(self, 'belge_admin'):
            self.belge_admin.yukle()
        self._kullanicilari_yukle(); self._konumlari_yukle()
        self._tesisleri_yukle(); self._loglari_yukle()
        self._yetkileri_yukle()

    def _kullanicilari_yukle(self):
        if not self.kimlik_servisi: return
        self._kullanicilar = self.kimlik_servisi.kullanici_listele()
        self.user_model.veri_guncelle([[u.kullanici_adi, u.rol.value, "✓" if u.aktif else "✗"] for u in self._kullanicilar])

    # ── KULLANICI İŞLEMLERİ ──
    def _kullanici_ekle(self):
        if not self.kimlik_servisi: return
        dlg = KullaniciEkleDialog(self)
        if dlg.exec_() != QDialog.Accepted: return
        v = dlg.veri()
        ok, msg, _ = self.kimlik_servisi.kullanici_olustur(
            v["email"], v["sifre"], v["rol"],
            ad=v["ad"], soyad=v["soyad"], email=v["email"]
        )
        if not ok:
            QMessageBox.warning(self, "Hata", msg)
        self._kullanicilari_yukle()

    def _kullanici_duzenle(self):
        if not self.kimlik_servisi: return
        idx = self.user_table.currentIndex()
        if not idx.isValid() or idx.row() >= len(self._kullanicilar): return
        u = self._kullanicilar[idx.row()]
        dlg = KullaniciDuzenleDialog(u, self)
        if dlg.exec_() != QDialog.Accepted: return
        v = dlg.veri()
        ok, msg = self.kimlik_servisi.kullanici_bilgi_guncelle(
            u.id, v["ad"], v["soyad"], v["email"], v["yeni_sifre"]
        )
        if not ok:
            QMessageBox.warning(self, "Hata", msg)
        self._kullanicilari_yukle()

    def _rol_degistir(self):
        if not self.kimlik_servisi: return
        idx = self.user_table.currentIndex()
        if not idx.isValid() or idx.row() >= len(self._kullanicilar): return
        u = self._kullanicilar[idx.row()]
        dlg = RolDegistirDialog(u.kullanici_adi, u.rol, self)
        if dlg.exec_() != QDialog.Accepted: return
        self.kimlik_servisi.rol_degistir(u.id, dlg.veri())
        self._kullanicilari_yukle()

    def _kullanici_deaktif(self):
        if not self.kimlik_servisi: return
        idx = self.user_table.currentIndex()
        if not idx.isValid() or idx.row() >= len(self._kullanicilar): return
        ok, msg = self.kimlik_servisi.kullanici_deaktif_et(self._kullanicilar[idx.row()].id)
        if not ok: QMessageBox.warning(self, "Hata", msg)
        self._kullanicilari_yukle()

    # ═════════════════════════════════════════
    # TAB 5: KONUM (ÜLKE / ŞEHİR)
    # ═════════════════════════════════════════

    def _build_konum_tab(self):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(16, 16, 16, 16)

        # Ülkeler
        uh = QHBoxLayout()
        uh.addWidget(QLabel("Ülkeler:")); uh.addStretch()
        b_ulke = QPushButton("+ Ülke"); b_ulke.clicked.connect(self._ulke_ekle)
        uh.addWidget(b_ulke)
        l.addLayout(uh)

        self.ulke_table = QTableView(); setup_table(self.ulke_table)
        self.ulke_model = SimpleTableModel(["Ad", "Aktif"])
        self.ulke_table.setModel(self.ulke_model)
        self.ulke_table.setMaximumHeight(150)
        self.ulke_table.clicked.connect(self._ulke_tiklandi)
        l.addWidget(self.ulke_table)

        # Şehirler (seçili ülkeye göre)
        sh = QHBoxLayout()
        self.sehir_baslik = QLabel("Şehirler:"); sh.addWidget(self.sehir_baslik)
        sh.addStretch()
        b_sehir = QPushButton("+ Şehir"); b_sehir.clicked.connect(self._sehir_ekle)
        sh.addWidget(b_sehir)
        l.addLayout(sh)

        self.sehir_table = QTableView(); setup_table(self.sehir_table)
        self.sehir_model = SimpleTableModel(["Ad", "Aktif"])
        self.sehir_table.setModel(self.sehir_model)
        l.addWidget(self.sehir_table)
        return w

    def _build_tesis_tab(self):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(16, 16, 16, 16)
        th = QHBoxLayout()
        th.addWidget(QLabel("Tesis Türleri:")); th.addStretch()
        b_ekle = QPushButton("+ Tesis Türü"); b_ekle.clicked.connect(self._tesis_ekle)
        th.addWidget(b_ekle)
        l.addLayout(th)

        self.tesis_table = QTableView(); setup_table(self.tesis_table)
        self.tesis_model = SimpleTableModel(["Ad", "Aktif"])
        self.tesis_table.setModel(self.tesis_model)
        l.addWidget(self.tesis_table)
        return w

    # ── KONUM VERİ ──
    _ulkeler = []
    _secili_ulke_konum = None
    _sehirler = []

    def _konumlari_yukle(self):
        if not self.konum_servisi: return
        self._ulkeler = self.konum_servisi.ulke_listesi(sadece_aktif=False)
        veri = [[u["ad"], "✓" if u["aktif"] else "—"] for u in self._ulkeler]
        self.ulke_model.veri_guncelle(veri)

    def _ulke_tiklandi(self, idx):
        if idx.row() >= len(self._ulkeler): return
        self._secili_ulke_konum = self._ulkeler[idx.row()]["id"]
        ulke_ad = self._ulkeler[idx.row()]["ad"]
        self.sehir_baslik.setText(f"Şehirler ({ulke_ad}):")
        self._sehirleri_yukle()

    def _sehirleri_yukle(self):
        if not self.konum_servisi or not self._secili_ulke_konum: return
        self._sehirler = self.konum_servisi.sehir_listesi(
            self._secili_ulke_konum, sadece_aktif=False)
        veri = [[s["ad"], "✓" if s["aktif"] else "—"] for s in self._sehirler]
        self.sehir_model.veri_guncelle(veri)

    def _ulke_ekle(self):
        if not self.konum_servisi: return
        dlg = AdEkleDialog("Ülke Ekle", "Ülke Adı:", self)
        if dlg.exec_() != QDialog.Accepted: return
        ok, msg, _ = self.konum_servisi.ulke_ekle(dlg.veri())
        if not ok: QMessageBox.warning(self, "Hata", msg)
        self._konumlari_yukle()

    def _sehir_ekle(self):
        if not self.konum_servisi or not self._secili_ulke_konum: return
        dlg = AdEkleDialog("Şehir Ekle", "Şehir Adı:", self)
        if dlg.exec_() != QDialog.Accepted: return
        ok, msg, _ = self.konum_servisi.sehir_ekle(self._secili_ulke_konum, dlg.veri())
        if not ok: QMessageBox.warning(self, "Hata", msg)
        self._sehirleri_yukle()

    # ── TESİS VERİ ──
    _tesisler = []

    def _tesisleri_yukle(self):
        if not self.tesis_servisi: return
        self._tesisler = self.tesis_servisi.listele(sadece_aktif=False)
        veri = [[t["ad"], "✓" if t["aktif"] else "—"] for t in self._tesisler]
        self.tesis_model.veri_guncelle(veri)

    def _tesis_ekle(self):
        if not self.tesis_servisi: return
        dlg = AdEkleDialog("Tesis Türü Ekle", "Tesis Türü:", self)
        if dlg.exec_() != QDialog.Accepted: return
        ok, msg, _ = self.tesis_servisi.ekle(dlg.veri())
        if not ok: QMessageBox.warning(self, "Hata", msg)
        self._tesisleri_yukle()

    # ═════════════════════════════════════════
    # TAB 7: AUDIT LOG
    # ═════════════════════════════════════════

    def _build_loglar_tab(self):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(16, 16, 16, 16)
        fr = QHBoxLayout()
        self.log_islem_filtre = QComboBox()
        self.log_islem_filtre.addItem("Tüm İşlemler", "")
        from uygulama.domain.modeller import IslemTipi
        for it in IslemTipi:
            self.log_islem_filtre.addItem(it.value, it.value)
        self.log_islem_filtre.currentIndexChanged.connect(self._loglari_yukle)
        fr.addWidget(QLabel("İşlem:")); fr.addWidget(self.log_islem_filtre)
        self.log_arama = QLineEdit(); self.log_arama.setPlaceholderText("Detayda ara...")
        self.log_arama.setMaximumWidth(200)
        self.log_arama.returnPressed.connect(self._loglari_yukle)
        fr.addWidget(self.log_arama); fr.addStretch()
        b_aktar = QPushButton("📋 CSV Aktar"); b_aktar.clicked.connect(self._log_csv_aktar)
        fr.addWidget(b_aktar)
        l.addLayout(fr)
        self.log_stat_label = QLabel("Toplam: —"); l.addWidget(self.log_stat_label)
        self.log_table = QTableView(); setup_table(self.log_table)
        self.log_model = SimpleTableModel(["Tarih", "Kullanıcı", "İşlem", "Tablo", "Detay"])
        self.log_table.setModel(self.log_model); l.addWidget(self.log_table)
        return w

    # ═════════════════════════════════════════
    # TAB 6: YETKİLER
    # ═════════════════════════════════════════

    def _build_yetki_tab(self):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(16, 16, 16, 16)
        l.addWidget(QLabel("Rol Bazlı İzin Matrisi:"))
        self.yetki_table = QTableView(); setup_table(self.yetki_table)
        self.yetki_model = SimpleTableModel(["İşlem", "Admin", "Editor", "Viewer"])
        self.yetki_table.setModel(self.yetki_model); l.addWidget(self.yetki_table)
        l.addWidget(QLabel("Son Yetki Reddi Logları:"))
        self.yetki_red_table = QTableView(); setup_table(self.yetki_red_table)
        self.yetki_red_model = SimpleTableModel(["Tarih", "Kullanıcı", "İşlem", "Detay"])
        self.yetki_red_table.setModel(self.yetki_red_model)
        self.yetki_red_table.setMaximumHeight(160); l.addWidget(self.yetki_red_table)
        return w

    # ── LOG VERİ YÜKLEME ──
    def _loglari_yukle(self):
        if not self.log_repo: return
        islem = self.log_islem_filtre.currentData() if hasattr(self, 'log_islem_filtre') else None
        arama = self.log_arama.text().strip() if hasattr(self, 'log_arama') else None
        loglar = self.log_repo.filtreli_getir(islem=islem or None, arama=arama or None, limit=200)
        from uygulama.ortak.yardimcilar import tarih_formatla
        veri = [[tarih_formatla(l.get("tarih","")), l.get("kullanici_adi",""),
                 l.get("islem",""), l.get("hedef_tablo",""),
                 l.get("detay","")[:60]] for l in loglar]
        self.log_model.veri_guncelle(veri)
        toplam = self.log_repo.toplam_log_sayisi()
        self.log_stat_label.setText(f"Gösterilen: {len(loglar)} / Toplam: {toplam}")

    def _yetkileri_yukle(self):
        if not self.yetki_servisi: return
        from uygulama.servisler.yetki_servisi import IZIN_MATRISI
        from uygulama.domain.modeller import KullaniciRolu
        veri = []
        for islem, roller in sorted(IZIN_MATRISI.items()):
            veri.append([islem,
                "✓" if KullaniciRolu.ADMIN in roller else "—",
                "✓" if KullaniciRolu.EDITOR in roller else "—",
                "✓" if KullaniciRolu.VIEWER in roller else "—"])
        self.yetki_model.veri_guncelle(veri)
        if self.log_repo:
            from uygulama.ortak.yardimcilar import tarih_formatla
            redler = self.log_repo.yetki_reddi_loglari(20)
            veri_r = [[tarih_formatla(r.get("tarih","")), r.get("kullanici_adi",""),
                       r.get("hedef_id",""), r.get("detay","")[:50]] for r in redler]
            self.yetki_red_model.veri_guncelle(veri_r)

    def _log_csv_aktar(self):
        if not self.log_repo: return
        satirlar = self.log_repo.csv_satirlari(500)
        try:
            import os
            yol = os.path.join(os.path.expanduser("~"), "audit_log.csv")
            with open(yol, "w", encoding="utf-8") as f:
                f.write("\n".join(satirlar))
            QMessageBox.information(self, "Dışa Aktarım", f"Kaydedildi: {yol}")
        except Exception as e:
            QMessageBox.warning(self, "Hata", str(e))



