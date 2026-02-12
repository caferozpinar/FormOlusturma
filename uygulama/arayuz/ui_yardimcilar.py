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
