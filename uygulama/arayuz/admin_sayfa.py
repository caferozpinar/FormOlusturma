#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Admin Paneli — Backend entegreli ürün, alan, seçenek, kullanıcı yönetimi."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableView, QTabWidget, QFrame, QMessageBox, QLineEdit,
    QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox, QInputDialog,
    QFormLayout, QDialog
)
from PyQt5.QtCore import Qt, pyqtSignal
from uygulama.arayuz.ui_yardimcilar import SimpleTableModel, setup_table


class AdminPanelPage(QWidget):
    go_back = pyqtSignal()

    def __init__(self, urun_servisi=None, kimlik_servisi=None,
                 log_repo=None, yetki_servisi=None,
                 konum_servisi=None, tesis_servisi=None,
                 em_repo=None, em_srv=None,
                 placeholder_srv=None, parent=None):
        super().__init__(parent)
        self.urun_servisi = urun_servisi
        self.kimlik_servisi = kimlik_servisi
        self.log_repo = log_repo
        self.yetki_servisi = yetki_servisi
        self.konum_servisi = konum_servisi
        self.tesis_servisi = tesis_servisi
        self.em_repo = em_repo
        self.em_srv = em_srv
        self.placeholder_srv = placeholder_srv
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
        for txt, slot, obj in [("+ Kullanıcı Ekle", self._kullanici_ekle, "primary"),
                                ("Rol Değiştir", self._rol_degistir, None),
                                ("Deaktif Et", self._kullanici_deaktif, "danger")]:
            b = QPushButton(txt); b.clicked.connect(slot)
            if obj: b.setObjectName(obj)
            br.addWidget(b)
        br.addStretch(); l.addLayout(br)
        return w

    # ── VERİ YÜKLEME ──
    def sayfa_gosterildi(self):
        self.admin_urun.yukle()
        if hasattr(self, 'placeholder_widget'):
            self.placeholder_widget.yukle()
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
        from uygulama.domain.modeller import KullaniciRolu
        ad, ok1 = QInputDialog.getText(self, "Kullanıcı", "Kullanıcı Adı:")
        if not ok1 or not ad: return
        sifre, ok2 = QInputDialog.getText(self, "Kullanıcı", "Şifre:")
        if not ok2 or not sifre: return
        rol_str, ok3 = QInputDialog.getItem(self, "Rol", "Rol:", [r.value for r in KullaniciRolu], 1)
        if not ok3: return
        ok, msg, _ = self.kimlik_servisi.kullanici_olustur(ad, sifre, KullaniciRolu(rol_str))
        if not ok: QMessageBox.warning(self, "Hata", msg)
        self._kullanicilari_yukle()

    def _rol_degistir(self):
        if not self.kimlik_servisi: return
        from uygulama.domain.modeller import KullaniciRolu
        idx = self.user_table.currentIndex()
        if not idx.isValid() or idx.row() >= len(self._kullanicilar): return
        u = self._kullanicilar[idx.row()]
        rol_str, ok = QInputDialog.getItem(self, "Rol", f"{u.kullanici_adi}:", [r.value for r in KullaniciRolu])
        if ok: self.kimlik_servisi.rol_degistir(u.id, KullaniciRolu(rol_str)); self._kullanicilari_yukle()

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
        ad, ok = QInputDialog.getText(self, "Ülke Ekle", "Ülke Adı:")
        if ok and ad:
            ok, msg, _ = self.konum_servisi.ulke_ekle(ad)
            if not ok: QMessageBox.warning(self, "Hata", msg)
            self._konumlari_yukle()

    def _sehir_ekle(self):
        if not self.konum_servisi or not self._secili_ulke_konum: return
        ad, ok = QInputDialog.getText(self, "Şehir Ekle", "Şehir Adı:")
        if ok and ad:
            ok, msg, _ = self.konum_servisi.sehir_ekle(self._secili_ulke_konum, ad)
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
        ad, ok = QInputDialog.getText(self, "Tesis Türü Ekle", "Tesis Türü:")
        if ok and ad:
            ok, msg, _ = self.tesis_servisi.ekle(ad)
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



