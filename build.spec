# -*- mode: python ; coding: utf-8 -*-
"""
FormOluşturma — PyInstaller Build Spec
Kullanım: pyinstaller build.spec
"""

import os
import sys
from PyInstaller.utils.hooks import collect_all

block_cipher = None
PROJE = os.path.abspath('.')

# Google API paketleri try/except içinde lazy import edildiği için
# PyInstaller statik analizle göremez — collect_all ile zorla topla
gapi_datas,   gapi_binaries,   gapi_hiddenimports   = collect_all('googleapiclient')
goauth_datas, goauth_binaries, goauth_hiddenimports  = collect_all('google_auth_oauthlib')

a = Analysis(
    ['main.py'],
    pathex=[PROJE],
    binaries=[] + gapi_binaries + goauth_binaries,
    datas=[
        ('sablonlar', 'sablonlar'),
        ('veri', 'veri'),
    ] + gapi_datas + goauth_datas,
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
        # ── Google Drive API ──────────────────────────────────────────────
        # Tüm importlar try/except içinde olduğu için statik analiz kaçırır;
        # burada açıkça listeliyoruz.
        'google',
        'google.auth',
        'google.auth.credentials',
        'google.auth.exceptions',
        'google.auth.transport',
        'google.auth.transport.requests',
        'google.oauth2',
        'google.oauth2.credentials',
        'google.oauth2.service_account',
        'google_auth_oauthlib',
        'google_auth_oauthlib.flow',
        'googleapiclient',
        'googleapiclient.discovery',
        'googleapiclient.errors',
        'googleapiclient.http',
        # ── Dolaylı bağımlılıklar ─────────────────────────────────────────
        'httplib2',
        'uritemplate',
        'requests',
        'requests.adapters',
        'requests.auth',
        'cachetools',
        'cachetools.func',
        'pyasn1',
        'pyasn1.type',
        'pyasn1.codec',
        'pyasn1_modules',
        'rsa',
        'certifi',
        'charset_normalizer',
        'urllib3',
        'urllib3.util',
        'urllib3.util.retry',
    ] + gapi_hiddenimports + goauth_hiddenimports,
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
