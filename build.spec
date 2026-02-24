# -*- mode: python ; coding: utf-8 -*-
"""
FormOluşturma — PyInstaller Build Spec
Kullanım: pyinstaller build.spec
"""

import os
import sys

block_cipher = None
PROJE = os.path.abspath('.')

a = Analysis(
    ['main.py'],
    pathex=[PROJE],
    binaries=[],
    datas=[
        ('sablonlar', 'sablonlar'),
        ('veri', 'veri'),
    ],
    hiddenimports=[
        'PyQt5',
        'PyQt5.QtWidgets',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.sip',
        'openpyxl',
        'openpyxl.cell',
        'openpyxl.styles',
        'openpyxl.utils',
        'openpyxl.worksheet',
        'bcrypt',
        'sqlite3',
        'json',
        'hashlib',
        'uuid',
        're',
        'math',
        'copy',
        'shutil',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'pandas', 'scipy', 'PIL',
        'tkinter', 'test', 'unittest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FormOlusturma',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI uygulama — konsol penceresi açılmaz
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # İkon eklemek istersen: icon='icon.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FormOlusturma',
)
