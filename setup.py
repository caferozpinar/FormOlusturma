#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FormOluşturma — Kurulum ve Başlatma Scripti

Kullanım:
    python setup.py          # Bağımlılıkları kur + uygulamayı başlat
    python setup.py install  # Sadece bağımlılıkları kur
    python setup.py run      # Sadece uygulamayı başlat
"""

import sys
import os
import subprocess
import platform

PROJE_KOKU = os.path.dirname(os.path.abspath(__file__))

BAGIMLILIKLAR = [
    "PyQt5>=5.15",
    "openpyxl>=3.1",
]

def renkli(mesaj, renk="yesil"):
    renkler = {"yesil": "\033[92m", "kirmizi": "\033[91m",
               "sari": "\033[93m", "mavi": "\033[94m", "reset": "\033[0m"}
    if platform.system() == "Windows":
        return mesaj
    return f"{renkler.get(renk, '')}{mesaj}{renkler['reset']}"


def python_kontrol():
    v = sys.version_info
    print(f"  Python: {v.major}.{v.minor}.{v.micro}")
    if v.major < 3 or (v.major == 3 and v.minor < 10):
        print(renkli("  ✗ Python 3.10+ gerekli!", "kirmizi"))
        sys.exit(1)
    print(renkli("  ✓ Python sürümü uygun", "yesil"))


def pip_kur(paket):
    try:
        cmd = [sys.executable, "-m", "pip", "install", paket, "-q"]
        # Linux'ta --break-system-packages gerekebilir
        if platform.system() == "Linux":
            cmd.append("--break-system-packages")
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False


def bagimliliklari_kur():
    print("\n📦 Bağımlılıklar kontrol ediliyor...\n")
    eksik = []
    for dep in BAGIMLILIKLAR:
        paket_adi = dep.split(">=")[0].split("==")[0]
        try:
            __import__(paket_adi.replace("-", "_").lower()
                       .replace("pyqt5", "PyQt5"))
            print(renkli(f"  ✓ {paket_adi}", "yesil"))
        except ImportError:
            eksik.append(dep)
            print(renkli(f"  ✗ {paket_adi} — kurulacak", "sari"))

    if not eksik:
        print(renkli("\n  Tüm bağımlılıklar mevcut ✓", "yesil"))
        return True

    print(f"\n  {len(eksik)} paket kuruluyor...")
    for dep in eksik:
        print(f"  → {dep} kuruluyor...", end=" ", flush=True)
        if pip_kur(dep):
            print(renkli("✓", "yesil"))
        else:
            print(renkli("✗ HATA", "kirmizi"))
            print(renkli(f"\n  Elle kurun: pip install {dep}", "kirmizi"))
            return False

    print(renkli("\n  Tüm bağımlılıklar kuruldu ✓", "yesil"))
    return True


def klasorleri_olustur():
    for d in ["veri", "loglar", "sablonlar"]:
        yol = os.path.join(PROJE_KOKU, d)
        os.makedirs(yol, exist_ok=True)


def uygulamayi_baslat():
    print(renkli("\n🚀 Uygulama başlatılıyor...\n", "mavi"))
    main_py = os.path.join(PROJE_KOKU, "main.py")
    os.chdir(PROJE_KOKU)
    subprocess.call([sys.executable, main_py])


def main():
    print("=" * 50)
    print("  FormOluşturma — Proje Yönetim Sistemi")
    print("  Kurulum ve Başlatma")
    print("=" * 50)

    python_kontrol()

    komut = sys.argv[1] if len(sys.argv) > 1 else "all"

    if komut in ("install", "all"):
        if not bagimliliklari_kur():
            sys.exit(1)
        klasorleri_olustur()

    if komut in ("run", "all"):
        uygulamayi_baslat()

    if komut == "install":
        print(renkli("\n✓ Kurulum tamamlandı!", "yesil"))
        print(f"  Başlatmak için: python main.py")


if __name__ == "__main__":
    main()
