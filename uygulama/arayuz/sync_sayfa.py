#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sync Sayfası — Google Drive DB Merge + Dosya Sync.
Manuel tetikleme, lock mekanizması, çakışma dialogu.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QMessageBox, QDialog, QFormLayout,
    QLineEdit, QDialogButtonBox, QGroupBox, QTextEdit, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread

from uygulama.ortak.yardimcilar import logger_olustur
from uygulama.ortak.app_state import app_state

logger = logger_olustur("sync_sayfa")


class CakismaDialog(QDialog):
    """Çakışan kayıt için lokal/drive seçimi."""

    def __init__(self, tablo, lokal, drive, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Çakışma — {tablo}")
        self.setMinimumWidth(500)
        self.karar = "atla"

        lo = QVBoxLayout(self)
        lo.addWidget(QLabel(f"<b>{tablo}</b> tablosunda çakışma tespit edildi:"))
        lo.addSpacing(8)

        fark_text = ""
        for k in lokal:
            lv = str(lokal.get(k, ""))
            dv = str(drive.get(k, ""))
            if lv != dv and k not in ("guncelleme_tarihi", "olusturma_tarihi"):
                fark_text += (f"<b>{k}:</b><br>"
                              f"  Lokal: <span style='color:#1565C0'>{lv[:80]}</span><br>"
                              f"  Drive: <span style='color:#C62828'>{dv[:80]}</span><br><br>")

        if not fark_text:
            fark_text = "Zaman damgası farklı (içerik aynı görünüyor)"

        lz = lokal.get("guncelleme_tarihi", "") or lokal.get("olusturma_tarihi", "")
        dz = drive.get("guncelleme_tarihi", "") or drive.get("olusturma_tarihi", "")
        fark_text += f"<hr>Lokal zaman: {lz}<br>Drive zaman: {dz}"

        te = QTextEdit()
        te.setReadOnly(True)
        te.setHtml(fark_text)
        te.setMaximumHeight(200)
        lo.addWidget(te)
        lo.addSpacing(8)

        bb = QHBoxLayout()
        for text, val in [("✅ Lokal Kalsın", "lokal"),
                          ("☁️ Drive Kalsın", "drive"),
                          ("Atla", "atla")]:
            b = QPushButton(text)
            b.setFixedHeight(32)
            b.clicked.connect(lambda _, v=val: self._sec(v))
            bb.addWidget(b)
        lo.addLayout(bb)

    def _sec(self, karar):
        self.karar = karar
        self.accept()


class SyncWorker(QThread):
    """Arka planda sync çalıştırır."""
    ilerleme = pyqtSignal(str)
    bitti = pyqtSignal(bool, str)
    cakisma = pyqtSignal(str, dict, dict)

    def __init__(self, drive_srv, kullanici):
        super().__init__()
        self.drive_srv = drive_srv
        self.kullanici = kullanici
        self._cakisma_karar = None

    def run(self):
        try:
            ok, msg = self.drive_srv.sync(
                self.kullanici,
                cakisma_callback=self._cakisma_handler,
                ilerleme_callback=lambda m: self.ilerleme.emit(m))
            self.bitti.emit(ok, msg)
        except Exception as e:
            self.bitti.emit(False, f"Beklenmeyen hata: {type(e).__name__}: {e}")

    def _cakisma_handler(self, tablo, lokal, drive):
        self._cakisma_karar = None
        self.cakisma.emit(tablo, lokal, drive)
        import time
        while self._cakisma_karar is None:
            time.sleep(0.1)
        return self._cakisma_karar


class SyncPage(QWidget):
    go_back = pyqtSignal()

    def __init__(self, sync_servisi=None, yetki_servisi=None, drive_sync_srv=None, parent=None):
        super().__init__(parent)
        self.sync_servisi = sync_servisi
        self.yetki_servisi = yetki_servisi
        self.drive_srv = drive_sync_srv
        self._worker = None
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 24, 32, 24)
        outer.setSpacing(16)

        header = QHBoxLayout()
        t = QLabel("Google Drive Senkronizasyon")
        t.setObjectName("title")
        bb = QPushButton("← Geri")
        bb.clicked.connect(self.go_back.emit)
        header.addWidget(t); header.addStretch(); header.addWidget(bb)
        outer.addLayout(header)

        # Bağlantı
        g1 = QGroupBox("☁️ Google Drive Bağlantısı")
        g1l = QVBoxLayout(g1)
        self.lbl_durum = QLabel("Bağlı değil")
        self.lbl_durum.setStyleSheet(
            "font-size:14px;font-weight:bold;color:#C62828;padding:8px;")
        g1l.addWidget(self.lbl_durum)

        br = QHBoxLayout()
        self.btn_baglan = QPushButton("🔗 Google'a Bağlan")
        self.btn_baglan.setFixedHeight(32)
        self.btn_baglan.clicked.connect(self._baglan)
        br.addWidget(self.btn_baglan)
        self.btn_ayar = QPushButton("⚙ Klasör ID Ayarla")
        self.btn_ayar.setFixedHeight(32)
        self.btn_ayar.clicked.connect(self._klasor_ayarla)
        br.addWidget(self.btn_ayar)
        br.addStretch()
        g1l.addLayout(br)
        outer.addWidget(g1)

        # Sync
        g2 = QGroupBox("🔄 Senkronizasyon")
        g2l = QVBoxLayout(g2)
        self.lbl_sync = QLabel("Hazır")
        self.lbl_sync.setStyleSheet("font-size:13px;padding:6px;color:#333;")
        self.lbl_sync.setAlignment(Qt.AlignCenter)
        g2l.addWidget(self.lbl_sync)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        g2l.addWidget(self.progress)

        self.btn_sync = QPushButton("🔄 Senkronize Et")
        self.btn_sync.setObjectName("primary")
        self.btn_sync.setFixedHeight(40)
        self.btn_sync.setStyleSheet("font-size:14px;font-weight:bold;")
        self.btn_sync.clicked.connect(self._sync_baslat)
        g2l.addWidget(self.btn_sync)
        outer.addWidget(g2)

        # Log Sync bilgisi
        g_log = QGroupBox("📁 Log Senkronizasyonu")
        g_log_l = QVBoxLayout(g_log)
        from uygulama.servisler.drive_sync_servisi import DriveSyncServisi
        makine = DriveSyncServisi._makine_adi()
        self.lbl_log_sync = QLabel(
            f"Sync sırasında bu makinenin logları Drive'a yüklenir.\n"
            f"Klasör: loglar/{makine}/\n"
            f"• Lokal'de 30 günden eski loglar otomatik silinir\n"
            f"• Drive'daki loglar hiçbir zaman silinmez"
        )
        self.lbl_log_sync.setStyleSheet("font-size:12px;color:#555;padding:4px;")
        g_log_l.addWidget(self.lbl_log_sync)
        outer.addWidget(g_log)

        # Log
        g3 = QGroupBox("📋 Sync Günlüğü")
        g3l = QVBoxLayout(g3)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        self.log_text.setStyleSheet(
            "font-family:monospace;font-size:11px;background:#FAFAFA;")
        g3l.addWidget(self.log_text)
        outer.addWidget(g3)
        outer.addStretch()

    def sayfa_gosterildi(self):
        self._durum_guncelle()
        # Kaydedilmiş klasör ID'sini yükle
        if self.drive_srv and not self.drive_srv.drive_klasor_id:
            try:
                r = self.drive_srv.db.getir_tek(
                    "SELECT deger FROM sync_meta WHERE anahtar='drive_klasor_id'")
                if r:
                    self.drive_srv.drive_klasor_id = r["deger"]
            except Exception:
                pass
        self._durum_guncelle()

    def _durum_guncelle(self):
        if self.drive_srv and self.drive_srv.baglanti_durumu():
            self.lbl_durum.setText("✅ Google Drive'a bağlı")
            self.lbl_durum.setStyleSheet(
                "font-size:14px;font-weight:bold;color:#2E7D32;padding:8px;")
            self.btn_baglan.setText("✅ Bağlı")
            self.btn_baglan.setEnabled(False)
            self.btn_sync.setEnabled(True)
            kid = self.drive_srv.drive_klasor_id
            if kid:
                self.btn_ayar.setText(f"⚙ Klasör: ...{kid[-8:]}")
        else:
            self.lbl_durum.setText("❌ Google Drive'a bağlı değil")
            self.lbl_durum.setStyleSheet(
                "font-size:14px;font-weight:bold;color:#C62828;padding:8px;")
            self.btn_baglan.setText("🔗 Google'a Bağlan")
            self.btn_baglan.setEnabled(True)
            self.btn_sync.setEnabled(False)

    def _baglan(self):
        if not self.drive_srv:
            QMessageBox.warning(self, "Hata",
                                "Drive sync servisi yapılandırılmamış.")
            return
        self._log("Google'a bağlanılıyor...")
        ok, msg = self.drive_srv.baglan()
        self._log(msg)
        if ok:
            self._durum_guncelle()
        else:
            QMessageBox.warning(self, "Bağlantı Hatası", msg)

    def _klasor_ayarla(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Drive Klasör ID")
        fl = QFormLayout(dlg)
        fl.addRow(QLabel(
            "Google Drive'da paylaşımlı klasörün ID'sini girin.\n"
            "ID, klasör URL'sinin son kısmıdır:\n"
            "drive.google.com/drive/folders/BU_KISIM"))
        edt = QLineEdit()
        if self.drive_srv:
            edt.setText(self.drive_srv.drive_klasor_id or "")
        fl.addRow("Klasör ID:", edt)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        fl.addRow(bb)
        if dlg.exec_() and self.drive_srv:
            kid = edt.text().strip()
            if kid:
                self.drive_srv.drive_klasor_id = kid
                try:
                    with self.drive_srv.db.transaction() as c:
                        c.execute(
                            "INSERT OR REPLACE INTO sync_meta "
                            "(anahtar, deger, guncelleme_tarihi) "
                            "VALUES ('drive_klasor_id', ?, datetime('now'))",
                            (kid,))
                except Exception:
                    pass
                self._durum_guncelle()
                self._log(f"Klasör ID kaydedildi: ...{kid[-8:]}")

    def _sync_baslat(self):
        if not self.drive_srv:
            return
        if self._worker and self._worker.isRunning():
            QMessageBox.information(self, "Bilgi", "Sync zaten çalışıyor.")
            return

        state = app_state()
        kullanici = "admin"
        if state.aktif_kullanici:
            kullanici = state.aktif_kullanici.kullanici_adi

        self.btn_sync.setEnabled(False)
        self.progress.setVisible(True)
        self.lbl_sync.setText("⏳ Senkronize ediliyor...")
        self.log_text.clear()
        self._log("Sync başlatıldı...")

        self._worker = SyncWorker(self.drive_srv, kullanici)
        self._worker.ilerleme.connect(self._on_ilerleme)
        self._worker.bitti.connect(self._on_bitti)
        self._worker.cakisma.connect(self._on_cakisma)
        self._worker.start()

    def _on_ilerleme(self, msg):
        self._log(msg)
        self.lbl_sync.setText(f"⏳ {msg}")
        QApplication.processEvents()

    def _on_bitti(self, ok, msg):
        self.progress.setVisible(False)
        self.btn_sync.setEnabled(True)
        if ok:
            self.lbl_sync.setText("✅ Tamamlandı")
            self._log(f"✅ {msg}")
            QMessageBox.information(self, "Senkronizasyon", msg)
        else:
            self.lbl_sync.setText("❌ Hata")
            self._log(f"❌ {msg}")
            QMessageBox.warning(self, "Sync Hatası", msg)
        self._worker = None

    def _on_cakisma(self, tablo, lokal, drive):
        dlg = CakismaDialog(tablo, lokal, drive, self)
        dlg.exec_()
        if self._worker:
            self._worker._cakisma_karar = dlg.karar
        self._log(f"Çakışma ({tablo}): {dlg.karar}")

    def _log(self, msg):
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{ts}] {msg}")
        logger.info(msg)
