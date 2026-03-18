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
    """
    pip ile paket kurmayı dener. Hata durumunda hata detaylarını açık bir şekilde döndürür.
    """
    try:
        cmd = [sys.executable, "-m", "pip", "install", paket, "-q"]
        # Linux'ta --break-system-packages gerekebilir
        if platform.system() == "Linux":
            cmd.append("--break-system-packages")
        
        # Hata çıkışını yakalaması için stderr'ı PIPE olarak ayarla
        result = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True,
            timeout=120  # 2 dakika timeout
        )
        
        if result.returncode == 0:
            return True, None
        else:
            # pip hatası — detaylı bilgi döndür
            hata_cikti = result.stderr.strip() if result.stderr else result.stdout.strip()
            return False, hata_cikti
            
    except subprocess.TimeoutExpired as timeout_err:
        return False, f"Kurulum zaman aşımına uğradı (120 saniye). Paket: {paket}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


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
    basarili = 0
    basarisiz = []
    
    for dep in eksik:
        print(f"  → {dep} kuruluyor...", end=" ", flush=True)
        kurulum_ok, hata_mesaji = pip_kur(dep)
        if kurulum_ok:
            print(renkli("✓", "yesil"))
            basarili += 1
        else:
            print(renkli("✗ HATA", "kirmizi"))
            basarisiz.append((dep, hata_mesaji))

    if basarisiz:
        print(renkli(f"\n  ✗ {len(basarisiz)} paket kurulamadı:", "kirmizi"))
        for paket, hata in basarisiz:
            print(renkli(f"\n  Paket: {paket}", "kirmizi"))
            if hata:
                # Hatayı satır satır göster
                hata_satirlari = hata.split('\n')[:5]  # İlk 5 satırı göster
                for satir in hata_satirlari:
                    if satir.strip():
                        print(f"    {satir}")
            print(f"\n  Elle kurmak için: pip install {paket}")
        return False

    print(renkli(f"\n  ✓ {basarili} paket kuruldu", "yesil"))
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
