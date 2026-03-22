#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI Yardımcı fonksiyonlar ve widget'lar.
"""

from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QTableView,
    QHeaderView, QAbstractItemView
)
from PyQt5.QtCore import Qt, QAbstractTableModel, QVariant


# ─────────────────────────────────────────────
# SIMPLE TABLE MODEL
# ─────────────────────────────────────────────

class SimpleTableModel(QAbstractTableModel):
    """Basit tablo modeli — header + data list."""

    def __init__(self, headers, data=None, parent=None):
        super().__init__(parent)
        self._headers = headers
        self._data = data or []

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and index.isValid():
            row = self._data[index.row()]
            if index.column() < len(row):
                return str(row[index.column()])
        if role == Qt.TextAlignmentRole:
            return Qt.AlignVCenter | Qt.AlignLeft
        return QVariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            if section < len(self._headers):
                return self._headers[section]
        return QVariant()

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def veri_guncelle(self, yeni_data):
        """Tablo verisini günceller."""
        self.beginResetModel()
        self._data = yeni_data
        self.endResetModel()


# ─────────────────────────────────────────────
# WIDGET YARDIMCILARI
# ─────────────────────────────────────────────

def make_separator():
    """Yatay ayırıcı çizgi."""
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Plain)
    line.setStyleSheet("background-color: #E2E4E9; max-height: 1px;")
    return line


def make_badge(text, variant="active"):
    """Durum badge'i oluşturur."""
    badge = QLabel(text)
    badge.setAlignment(Qt.AlignCenter)
    badge.setFixedHeight(24)
    if variant == "active":
        badge.setObjectName("badgeActive")
    elif variant == "closed":
        badge.setObjectName("badgeClosed")
    else:
        badge.setObjectName("badgePending")
    return badge


def make_stat_card(value, label):
    """İstatistik kartı oluşturur."""
    frame = QFrame()
    frame.setObjectName("statCard")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(4)

    val_lbl = QLabel(str(value))
    val_lbl.setObjectName("statValue")
    val_lbl.setAlignment(Qt.AlignLeft)

    desc_lbl = QLabel(label)
    desc_lbl.setObjectName("statLabel")
    desc_lbl.setAlignment(Qt.AlignLeft)

    layout.addWidget(val_lbl)
    layout.addWidget(desc_lbl)
    return frame


def setup_table(table: QTableView):
    """Standart tablo ayarlarını uygular."""
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setStretchLastSection(True)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    table.setShowGrid(False)
    table.setSortingEnabled(True)


# ─────────────────────────────────────────────
# YETKİ KONTROLÜ YARDIMCILARı
# ─────────────────────────────────────────────

def kontrol_yetki(islem: str, yetki_servisi) -> bool:
    """
    Belirtilen işlem için kullanıcı yetkisi olup olmadığını kontrol eder.
    
    Args:
        islem: Yetki işlem kodu (ör: 'proje_olustur', 'belge_guncelle')
        yetki_servisi: YetkiServisi örneği
        
    Returns:
        True eğer izinli, False eğer izinsiz
    """
    if not yetki_servisi:
        return False
    
    ok, _ = yetki_servisi.kontrol(islem)
    return ok


def goster_eğer_yetkili(widget, islem: str, yetki_servisi, 
                        varsayilan=False) -> bool:
    """
    Widget'ı sadece kullanıcı yetkili ise gösterir.
    
    Args:
        widget: Gösterilecek widget
        islem: Yetki kontrolü yapılacak işlem kodu
        yetki_servisi: YetkiServisi örneği
        varsayilan: Yetki servisi None ise widget'ı göster mi?
        
    Returns:
        True eğer widget gösterildi, False eğer gizlendi
    """
    if not yetki_servisi:
        widget.setVisible(varsayilan)
        return varsayilan
    
    yetkili = kontrol_yetki(islem, yetki_servisi)
    widget.setVisible(yetkili)
    return yetkili


def dısablele_eğer_yetkisiz(button, islem: str, yetki_servisi,
                             tooltip_ekleme: str = "") -> bool:
    """
    Düğmeyi yetkisiz ise devre dışı bırakır ve tooltip eklenir.
    
    Args:
        button: Kontrol edilecek button (QPushButton vb)
        islem: Yetki kontrolü yapılacak işlem kodu
        yetki_servisi: YetkiServisi örneği
        tooltip_ekleme: Tooltip'e eklenecek ek metin
        
    Returns:
        True eğer button aktif, False eğer devre dışı
    """
    if not yetki_servisi:
        button.setEnabled(True)
        return True

    from uygulama.ortak.app_state import app_state
    if not app_state().giris_yapildi:
        # Henüz giriş yapılmamış — butonu açık bırak, tık anında kontrol edilir
        button.setEnabled(True)
        return True

    yetkili = kontrol_yetki(islem, yetki_servisi)
    button.setEnabled(yetkili)
    
    if not yetkili:
        from uygulama.ortak.app_state import app_state
        state = app_state()
        kullanici_rolu = state.aktif_kullanici.rol.value if state.aktif_kullanici else "?"
        tooltip = f"⛔ Yetkisiz işlem\nSizin rol: {kullanici_rolu}"
        if tooltip_ekleme:
            tooltip += f"\n{tooltip_ekleme}"
        button.setToolTip(tooltip)
    elif button.toolTip() and "⛔" in button.toolTip():
        # Eğer önceki yetki hatası tooltip'i varsa temizle
        button.setToolTip("")
    
    return yetkili


def sarma_buton_yetkisi(button, islem: str, yetki_servisi, 
                        handler_func, gizle: bool = False):
    """
    Button click'ine yetki kontrolü sarmalı koyar.
    Yetkisiz ise handler çalışmaz ve uyarı gösterilir.
    
    Args:
        button: Button widget'ı
        islem: Yetki işlem kodu
        yetki_servisi: YetkiServisi örneği
        handler_func: Button tıklandığında çalışması gereken function
        gizle: True ise buton yetkisiz olduğunda gizlenir
        
    Example:
        sarma_buton_yetkisi(self.btn_guncelle, "belge_guncelle", 
                            self.yetki_servisi, self._belge_guncelle)
    """
    def wrapped_handler():
        yetkili = kontrol_yetki(islem, yetki_servisi)
        if not yetkili:
            from PyQt5.QtWidgets import QMessageBox
            from uygulama.ortak.app_state import app_state
            state = app_state()
            rol = state.aktif_kullanici.rol.value if state.aktif_kullanici else "?"
            QMessageBox.warning(
                button.parent(),
                "Yetkisiz İşlem",
                f"Bu işlem için yetkiniz bulunmuyor.\n\nSizin rol: {rol}\n"
                f"İşlem: {islem}"
            )
            return
        
        handler_func()
    
    if gizle:
        goster_eğer_yetkili(button, islem, yetki_servisi)
    else:
        dısablele_eğer_yetkisiz(button, islem, yetki_servisi)
    
    button.clicked.connect(wrapped_handler)
