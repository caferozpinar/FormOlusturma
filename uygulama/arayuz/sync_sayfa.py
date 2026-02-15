#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sync Sayfası — Backend entegreli snapshot, conflict, otomatik kontrol."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableView, QProgressBar, QFrame, QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer

from uygulama.arayuz.ui_yardimcilar import SimpleTableModel, setup_table
from uygulama.ortak.yardimcilar import tarih_formatla


class SyncPage(QWidget):
    go_back = pyqtSignal()

    def __init__(self, sync_servisi=None, parent=None):
        super().__init__(parent)
        self.sync_servisi = sync_servisi
        self._son_sync_id = None
        self._conflictler = []

        # Otomatik sync timer (10 dk)
        self._auto_timer = QTimer(self)
        self._auto_timer.setInterval(600_000)  # 10 dakika
        self._auto_timer.timeout.connect(self._otomatik_sync_kontrol)

        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 24, 32, 24)
        outer.setSpacing(20)

        # Header
        header = QHBoxLayout()
        t = QLabel("Senkronizasyon"); t.setObjectName("title")
        bb = QPushButton("← Geri"); bb.clicked.connect(self.go_back.emit)
        header.addWidget(t); header.addStretch(); header.addWidget(bb)
        outer.addLayout(header)

        # Durum kartı
        status_card = QFrame(); status_card.setObjectName("card")
        sl = QVBoxLayout(status_card); sl.setContentsMargins(24, 20, 24, 20)

        self.status_label = QLabel("Hazır")
        self.status_label.setObjectName("subtitle")
        self.status_label.setAlignment(Qt.AlignCenter)
        sl.addWidget(self.status_label)

        self.son_sync_label = QLabel("Son sync: —")
        self.son_sync_label.setAlignment(Qt.AlignCenter)
        sl.addWidget(self.son_sync_label)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False); self.progress.setFixedHeight(6)
        self.progress.setValue(0)
        sl.addWidget(self.progress)

        outer.addWidget(status_card)

        # Butonlar
        btn_row = QHBoxLayout()
        self.btn_snapshot = QPushButton("📸 Snapshot Al")
        self.btn_snapshot.setObjectName("primary")
        self.btn_snapshot.clicked.connect(self._snapshot_al)
        btn_row.addWidget(self.btn_snapshot)

        self.btn_sync = QPushButton("🔄 Sync Başlat")
        self.btn_sync.setObjectName("primary")
        self.btn_sync.clicked.connect(self._sync_baslat)
        btn_row.addWidget(self.btn_sync)

        self.btn_sync_dosya = QPushButton("📂 Dosyadan Sync")
        self.btn_sync_dosya.clicked.connect(self._dosyadan_sync)
        btn_row.addWidget(self.btn_sync_dosya)

        btn_row.addStretch()

        self.btn_auto = QPushButton("⏱ Otomatik: Kapalı")
        self.btn_auto.setCheckable(True)
        self.btn_auto.clicked.connect(self._otomatik_toggle)
        btn_row.addWidget(self.btn_auto)
        outer.addLayout(btn_row)

        # Snapshot listesi
        outer.addWidget(QLabel("Snapshot Geçmişi:"))
        self.snap_table = QTableView(); setup_table(self.snap_table)
        self.snap_model = SimpleTableModel(["Dosya", "Boyut (MB)", "Tarih"])
        self.snap_table.setModel(self.snap_model)
        self.snap_table.setMaximumHeight(140)
        outer.addWidget(self.snap_table)

        # Conflict tablosu
        outer.addWidget(QLabel("Çakışmalar:"))
        self.conflict_table = QTableView(); setup_table(self.conflict_table)
        self.conflict_model = SimpleTableModel(
            ["Tablo", "Alan", "Yerel Değer", "Uzak Değer", "Çözüm"])
        self.conflict_table.setModel(self.conflict_model)
        self.conflict_table.setMaximumHeight(180)
        outer.addWidget(self.conflict_table)

        # Conflict çözüm butonları
        cr = QHBoxLayout()
        self.btn_yerel = QPushButton("Yereli Koru")
        self.btn_yerel.clicked.connect(lambda: self._tum_conflictleri_coz("YEREL"))
        self.btn_uzak = QPushButton("Uzağı Al")
        self.btn_uzak.clicked.connect(lambda: self._tum_conflictleri_coz("UZAK"))
        cr.addWidget(self.btn_yerel); cr.addWidget(self.btn_uzak)
        cr.addStretch()
        outer.addLayout(cr)

        # Sync geçmişi
        outer.addWidget(QLabel("Sync Geçmişi:"))
        self.history_table = QTableView(); setup_table(self.history_table)
        self.history_model = SimpleTableModel(["Tür", "Durum", "Detay", "Tarih"])
        self.history_table.setModel(self.history_model)
        self.history_table.setMaximumHeight(160)
        outer.addWidget(self.history_table)

    # ═════════════════════════════════════════
    # VERİ YÜKLEME
    # ═════════════════════════════════════════

    def sayfa_gosterildi(self):
        self._durum_guncelle()
        self._snapshot_listesini_yukle()
        self._conflict_yukle()
        self._gecmis_yukle()

    def _durum_guncelle(self):
        if not self.sync_servisi:
            return
        son = self.sync_servisi.son_sync()
        if son:
            tarih = tarih_formatla(son.get("sync_tarihi", ""))
            durum = son.get("durum", "")
            self.son_sync_label.setText(f"Son sync: {tarih} — {durum}")
            self.progress.setValue(100 if durum == "TAMAMLANDI" else 50)
            self.status_label.setText(
                "✅ Senkron" if durum == "TAMAMLANDI"
                else "⚠ Çakışma bekliyor" if durum == "CONFLICT_BEKLIYOR"
                else "Hazır")
        else:
            self.son_sync_label.setText("Son sync: Henüz yapılmadı")
            self.progress.setValue(0)

    def _snapshot_listesini_yukle(self):
        if not self.sync_servisi:
            return
        snaps = self.sync_servisi.snapshot_listele()
        veri = [[s["dosya"], str(s["boyut_mb"]), s["tarih"]] for s in snaps]
        self.snap_model.veri_guncelle(veri)

    def _conflict_yukle(self):
        if not self.sync_servisi:
            return
        self._conflictler = self.sync_servisi.bekleyen_conflictler()
        veri = [[c["tablo"], c["alan"], c["yerel_deger"][:30],
                 c["uzak_deger"][:30], c["cozum"]]
                for c in self._conflictler]
        self.conflict_model.veri_guncelle(veri)
        has_conflict = len(self._conflictler) > 0
        self.btn_yerel.setEnabled(has_conflict)
        self.btn_uzak.setEnabled(has_conflict)

    def _gecmis_yukle(self):
        if not self.sync_servisi:
            return
        gecmis = self.sync_servisi.sync_gecmisi(10)
        veri = [[g["tur"], g["durum"], g.get("detay", "")[:50],
                 tarih_formatla(g["sync_tarihi"])]
                for g in gecmis]
        self.history_model.veri_guncelle(veri)

    # ═════════════════════════════════════════
    # İŞLEMLER
    # ═════════════════════════════════════════

    def _snapshot_al(self):
        if not self.sync_servisi:
            return
        self.status_label.setText("⏳ Snapshot alınıyor...")
        self.progress.setValue(30)
        ok, msg, yol = self.sync_servisi.snapshot_olustur()
        if ok:
            self.progress.setValue(100)
            self.status_label.setText("✅ Snapshot alındı")
            self._snapshot_listesini_yukle()
        else:
            self.progress.setValue(0)
            QMessageBox.warning(self, "Hata", msg)
        self._durum_guncelle()

    def _sync_baslat(self):
        if not self.sync_servisi:
            return
        self.status_label.setText("⏳ Senkronizasyon başlatılıyor...")
        self.progress.setValue(20)

        ok, msg, sync_id = self.sync_servisi.sync_baslat()
        self._son_sync_id = sync_id

        if ok:
            self.progress.setValue(100)
        else:
            QMessageBox.warning(self, "Sync Hatası", msg)

        self.sayfa_gosterildi()

    def _dosyadan_sync(self):
        if not self.sync_servisi:
            return
        yol, _ = QFileDialog.getOpenFileName(
            self, "Uzak Veritabanı Seç", "",
            "SQLite Dosyaları (*.db);;Tüm Dosyalar (*)")
        if not yol:
            return

        self.status_label.setText("⏳ Dosyadan sync başlatılıyor...")
        self.progress.setValue(20)

        ok, msg, sync_id = self.sync_servisi.sync_baslat(uzak_db_yolu=yol)
        self._son_sync_id = sync_id

        if ok:
            self.progress.setValue(100)
        else:
            QMessageBox.warning(self, "Sync Hatası", msg)

        self.sayfa_gosterildi()

    def _tum_conflictleri_coz(self, cozum: str):
        if not self.sync_servisi or not self._son_sync_id:
            return
        ok, msg = self.sync_servisi.tum_conflictleri_coz(
            self._son_sync_id, cozum)
        if ok:
            QMessageBox.information(self, "Çakışma Çözümü", msg)
        else:
            QMessageBox.warning(self, "Hata", msg)
        self.sayfa_gosterildi()

    def _otomatik_toggle(self):
        if self._auto_timer.isActive():
            self._auto_timer.stop()
            self.btn_auto.setText("⏱ Otomatik: Kapalı")
            self.btn_auto.setChecked(False)
        else:
            self._auto_timer.start()
            self.btn_auto.setText("⏱ Otomatik: Açık (10dk)")
            self.btn_auto.setChecked(True)

    def _otomatik_sync_kontrol(self):
        """10 dakikada bir otomatik snapshot ve durum kontrolü."""
        if not self.sync_servisi:
            return
        if self.sync_servisi.sync_aktif:
            return
        self.sync_servisi.snapshot_olustur()
        self._snapshot_listesini_yukle()
        self._durum_guncelle()
