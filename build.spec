# -*- mode: python ; coding: utf-8 -*-
"""
FormOluşturma — Güncellenmiş & Google API Fix
"""

import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None
PROJE = os.path.abspath('.')

# 1. Google paketlerinin ALT MODÜLLERİNİ topla
google_hidden = (
    collect_submodules('googleapiclient') +
    collect_submodules('google_auth_oauthlib') +
    collect_submodules('google.auth') +
    collect_submodules('google.oauth2') +
    collect_submodules('googleapiclient.discovery')
)

# 2. Google paketlerinin VERİ DOSYALARINI (JSON, Cert vb.) topla -> KRİTİK ADIM
google_datas = (
    collect_data_files('googleapiclient') +
    collect_data_files('google_auth_oauthlib') +
    collect_data_files('google.auth') +
    collect_data_files('google.oauth2') +
    collect_data_files('googleapiclient.discovery', excludes=['*.txt', '**/__pycache__'])
)

a = Analysis(
    ['main.py'],
    pathex=[PROJE],
    binaries=[],
    datas=[
        ('sablonlar', 'sablonlar'),
        ('veri', 'veri'),
    ] + google_datas, # Google verilerini buraya ekledik
    hiddenimports=[
        # GUI ve Temel sistem
        'PyQt5',
        'PyQt5.QtWidgets',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.sip',
        'sip', 

        # Uyarı veren tablolar
        'pycparser.lextab',
        'pycparser.yacctab',

        # Excel & Utils
        'openpyxl',
        'openpyxl.cell',
        'openpyxl.styles',
        'bcrypt',
        'sqlite3',

        # Google API (Ana modüller)
        'googleapiclient.discovery',
        'googleapiclient.errors',
        'googleapiclient.http',
        'google.auth',
        'google.auth.transport.requests',
        'google.oauth2.credentials',
        'google_auth_oauthlib.flow',

        # Bağımlılıklar
        'httplib2',
        'uritemplate',
        'requests',
        'cachetools',
        'pyasn1',
        'rsa',
        'certifi',
    ] + google_hidden,
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
    console=False, # Hata ayıklarken True yapabilirsin
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
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
