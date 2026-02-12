#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Uygulama Stil Dosyası — Tüm QSS tanımları.
"""

STYLESHEET = """
/* ── Global ── */
QMainWindow, QWidget {
    background-color: #F7F8FA;
    color: #1E1E2E;
    font-family: "Segoe UI", "Noto Sans", "Ubuntu", sans-serif;
    font-size: 13px;
}

/* ── Cards ── */
QFrame#card, QGroupBox#card {
    background-color: #FFFFFF;
    border: 1px solid #E2E4E9;
    border-radius: 8px;
    padding: 16px;
}

/* ── Line Edits ── */
QLineEdit, QDateEdit, QSpinBox, QDoubleSpinBox {
    background-color: #FFFFFF;
    border: 1px solid #D0D3DA;
    border-radius: 6px;
    padding: 8px 12px;
    min-height: 18px;
    selection-background-color: #3B82F6;
}
QLineEdit:focus, QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1.5px solid #3B82F6;
}
QLineEdit:disabled, QDateEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {
    background-color: #F0F1F3;
    color: #9CA3AF;
}

/* ── Combo Box ── */
QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #D0D3DA;
    border-radius: 6px;
    padding: 8px 12px;
    min-height: 18px;
}
QComboBox:focus { border: 1.5px solid #3B82F6; }
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border-left: 1px solid #E2E4E9;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}
QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    border: 1px solid #D0D3DA;
    border-radius: 4px;
    selection-background-color: #EBF2FF;
    selection-color: #1E1E2E;
}

/* ── Buttons ── */
QPushButton {
    background-color: #FFFFFF;
    color: #374151;
    border: 1px solid #D0D3DA;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 500;
    min-height: 18px;
}
QPushButton:hover {
    background-color: #F3F4F6;
    border-color: #B0B5C0;
}
QPushButton:pressed {
    background-color: #E5E7EB;
}
QPushButton:disabled {
    background-color: #F0F1F3;
    color: #9CA3AF;
    border-color: #E2E4E9;
}

QPushButton#primary {
    background-color: #3B82F6;
    color: #FFFFFF;
    border: none;
    font-weight: 600;
}
QPushButton#primary:hover { background-color: #2563EB; }
QPushButton#primary:pressed { background-color: #1D4ED8; }

QPushButton#danger {
    background-color: #FFFFFF;
    color: #DC2626;
    border: 1px solid #FCA5A5;
}
QPushButton#danger:hover { background-color: #FEF2F2; border-color: #DC2626; }

QPushButton#success {
    background-color: #059669;
    color: #FFFFFF;
    border: none;
}
QPushButton#success:hover { background-color: #047857; }

/* ── Table View ── */
QTableView {
    background-color: #FFFFFF;
    border: 1px solid #E2E4E9;
    border-radius: 6px;
    gridline-color: #F0F1F3;
    selection-background-color: #EBF2FF;
    selection-color: #1E1E2E;
    alternate-background-color: #FAFBFC;
}
QTableView::item {
    padding: 6px 10px;
    border-bottom: 1px solid #F0F1F3;
}
QTableView::item:selected {
    background-color: #EBF2FF;
}
QHeaderView::section {
    background-color: #F7F8FA;
    color: #6B7280;
    border: none;
    border-bottom: 2px solid #E2E4E9;
    padding: 8px 10px;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
}

/* ── Tab Widget ── */
QTabWidget::pane {
    border: 1px solid #E2E4E9;
    border-radius: 0 0 8px 8px;
    background-color: #FFFFFF;
    top: -1px;
}
QTabBar::tab {
    background-color: #F0F1F3;
    color: #6B7280;
    border: 1px solid #E2E4E9;
    border-bottom: none;
    border-radius: 6px 6px 0 0;
    padding: 10px 20px;
    margin-right: 2px;
    font-weight: 500;
}
QTabBar::tab:selected {
    background-color: #FFFFFF;
    color: #1E1E2E;
    font-weight: 600;
}
QTabBar::tab:hover:!selected {
    background-color: #E5E7EB;
}

/* ── Check Box ── */
QCheckBox {
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1.5px solid #D0D3DA;
    border-radius: 4px;
    background-color: #FFFFFF;
}
QCheckBox::indicator:checked {
    background-color: #3B82F6;
    border-color: #3B82F6;
}

/* ── Progress Bar ── */
QProgressBar {
    border: none;
    border-radius: 4px;
    background-color: #E5E7EB;
    height: 8px;
    text-align: center;
}
QProgressBar::chunk {
    background-color: #3B82F6;
    border-radius: 4px;
}

/* ── Scroll Area ── */
QScrollArea {
    border: none;
    background-color: transparent;
}
QScrollBar:vertical {
    border: none;
    background-color: #F7F8FA;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background-color: #D0D3DA;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background-color: #9CA3AF; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

/* ── Splitter ── */
QSplitter::handle {
    background-color: #E2E4E9;
    width: 1px;
}

/* ── Labels ── */
QLabel#title {
    font-size: 22px;
    font-weight: 700;
    color: #1E1E2E;
}
QLabel#subtitle {
    font-size: 14px;
    color: #6B7280;
}
QLabel#error {
    color: #DC2626;
    font-size: 12px;
}
QLabel#sectionTitle {
    font-size: 16px;
    font-weight: 600;
    color: #1E1E2E;
}
QLabel#version {
    color: #9CA3AF;
    font-size: 11px;
}

/* ── Badges ── */
QLabel#badgeActive {
    background-color: #D1FAE5;
    color: #065F46;
    border-radius: 10px;
    padding: 3px 12px;
    font-size: 11px;
    font-weight: 600;
}
QLabel#badgeClosed {
    background-color: #FEE2E2;
    color: #991B1B;
    border-radius: 10px;
    padding: 3px 12px;
    font-size: 11px;
    font-weight: 600;
}
QLabel#badgePending {
    background-color: #FEF3C7;
    color: #92400E;
    border-radius: 10px;
    padding: 3px 12px;
    font-size: 11px;
    font-weight: 600;
}

/* ── Stat Cards ── */
QFrame#statCard {
    background-color: #FFFFFF;
    border: 1px solid #E2E4E9;
    border-radius: 8px;
    padding: 16px;
}
QLabel#statValue {
    font-size: 28px;
    font-weight: 700;
    color: #1E1E2E;
}
QLabel#statLabel {
    font-size: 12px;
    color: #6B7280;
    font-weight: 500;
}

/* ── Toolbar ── */
QFrame#toolbar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E2E4E9;
    padding: 8px 16px;
}

/* ── Sync button states ── */
QPushButton#syncGreen {
    background-color: #D1FAE5;
    color: #065F46;
    border: 1px solid #6EE7B7;
    border-radius: 18px;
    min-width: 36px; max-width: 36px;
    min-height: 36px; max-height: 36px;
    font-weight: 700;
    font-size: 16px;
}
QPushButton#syncRed {
    background-color: #FEE2E2;
    color: #991B1B;
    border: 1px solid #FCA5A5;
    border-radius: 18px;
    min-width: 36px; max-width: 36px;
    min-height: 36px; max-height: 36px;
    font-weight: 700;
    font-size: 16px;
}
QPushButton#syncYellow {
    background-color: #FEF3C7;
    color: #92400E;
    border: 1px solid #FCD34D;
    border-radius: 18px;
    min-width: 36px; max-width: 36px;
    min-height: 36px; max-height: 36px;
    font-weight: 700;
    font-size: 16px;
}

/* ── Group Box ── */
QGroupBox {
    font-weight: 600;
    border: 1px solid #E2E4E9;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 20px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #374151;
}

/* ── List Widget ── */
QListWidget {
    background-color: #FFFFFF;
    border: 1px solid #D0D3DA;
    border-radius: 6px;
    padding: 4px;
}
QListWidget::item {
    padding: 4px 8px;
    border-radius: 4px;
}
QListWidget::item:selected {
    background-color: #EBF2FF;
    color: #1E1E2E;
}
"""
