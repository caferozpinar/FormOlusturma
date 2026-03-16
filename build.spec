# -*- mode: python ; coding: utf-8 -*-
"""
FormOluşturma — PyInstaller Build Spec
Kullanım:
    pyinstaller build.spec
"""

import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None
PROJE = os.path.abspath('.')

# Google paketleri lazy import kullandığı için
# PyInstaller statik analizle göremez. Tüm alt modülleri topluyoruz.
google_hidden = (
    collect_submodules('google') +
    collect_submodules('googleapiclient') +
    collect_submodules('google_auth_oauthlib') +
    collect_submodules('google.auth') +
    collect_submodules('google.oauth2')
)

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

        # Google API
        'googleapiclient.discovery',
        'googleapiclient.errors',
        'googleapiclient.http',

        'google.auth',
        'google.auth.transport.requests',
        'google.oauth2.credentials',
        'google.oauth2.service_account',
        'google_auth_oauthlib.flow',

        # dolaylı bağımlılıklar
        'httplib2',
        'uritemplate',
        'requests',
        'requests.adapters',
        'requests.auth',
        'cachetools',
        'pyasn1',
        'pyasn1_modules',
        'rsa',
        'certifi',
        'charset_normalizer',
        'urllib3',
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
    console=False,  # GUI uygulama
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
