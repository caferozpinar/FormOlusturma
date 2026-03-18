#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZET Yapı - FormOlusturma Installer / Updater

İki mod:
  1. Kurulum modu (argümansız veya --install):
     GitHub'dan son sürümü indirir, %APPDATA%'ya kurar, kısayol oluşturur.

  2. Güncelleme modu (--update --pid=<PID>):
     FormOlusturma.exe tarafından arkaplanda çağrılır.
     GitHub'da yeni sürüm varsa kullanıcıya sorar, onaylanırsa günceller.
"""

import argparse
import ctypes
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import zipfile
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk
import tkinter as tk

import requests

# ─────────────────────────────────────────────
# SABİTLER
# ─────────────────────────────────────────────

GITHUB_REPO = "caferozpinar/FormOlusturma"
APP_NAME = "FormOlusturma"
APP_INSTALL_DIR = os.path.join(os.environ.get("APPDATA", ""), "ZETYapı", APP_NAME)
MAIN_EXE = os.path.join(APP_INSTALL_DIR, "FormOlusturma.exe")
INSTALLER_EXE = os.path.join(APP_INSTALL_DIR, "installer.exe")
VERSION_FILE = os.path.join(APP_INSTALL_DIR, "version.txt")
UPDATE_FLAG = os.path.join(APP_INSTALL_DIR, "update_requested.flag")
LOG_FILE = os.path.join(APP_INSTALL_DIR, "loglar", "installer.log")


# ─────────────────────────────────────────────
# YARDIMCI FONKSİYONLAR
# ─────────────────────────────────────────────

def _log(mesaj: str) -> None:
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{zaman} | {mesaj}\n")


def yerel_versiyon() -> str:
    if os.path.exists(VERSION_FILE):
        return Path(VERSION_FILE).read_text(encoding="utf-8").strip()
    return "0.0.0"


def github_son_surum() -> tuple[str, str]:
    """(versiyon_str, zip_download_url) döndürür."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    yanit = requests.get(url, timeout=15, headers={"Accept": "application/vnd.github+json"})
    yanit.raise_for_status()
    veri = yanit.json()
    tag = veri["tag_name"].lstrip("v")
    for asset in veri.get("assets", []):
        if "Windows" in asset["name"] and asset["name"].endswith(".zip"):
            return tag, asset["browser_download_url"]
    raise ValueError(f"Release içinde Windows zip bulunamadı. Assetler: {[a['name'] for a in veri.get('assets', [])]}")


def versiyon_kucuk_mu(a: str, b: str) -> bool:
    """a < b mi? (semver karşılaştırması)"""
    def parse(v: str):
        parcalar = v.split(".")
        return tuple(int(x) for x in parcalar if x.isdigit())
    try:
        return parse(a) < parse(b)
    except Exception:
        return a != b


def process_calisiyor_mu(pid: int) -> bool:
    """Windows API ile process hâlâ çalışıyor mu?"""
    PROCESS_QUERY_INFORMATION = 0x0400
    STILL_ACTIVE = 259
    handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, False, pid)
    if not handle:
        return False
    exit_code = ctypes.c_ulong()
    ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
    ctypes.windll.kernel32.CloseHandle(handle)
    return exit_code.value == STILL_ACTIVE


def zip_indir(url: str, hedef: str, ilerleme_cb=None) -> None:
    """URL'den dosyayı stream ile indirir. ilerleme_cb(0-100) çağrılır."""
    yanit = requests.get(url, stream=True, timeout=120)
    yanit.raise_for_status()
    toplam = int(yanit.headers.get("content-length", 0))
    indirilen = 0
    with open(hedef, "wb") as f:
        for parca in yanit.iter_content(chunk_size=65536):
            f.write(parca)
            indirilen += len(parca)
            if ilerleme_cb and toplam:
                ilerleme_cb(indirilen / toplam * 100)


def zip_ac_guncelle(zip_yolu: str, hedef_dir: str) -> None:
    """
    Zip içindeki FormOlusturma.exe ve _internal/ klasörünü günceller.
    Diğer dosyalara (veri/, loglar/, sablonlar/, installer.exe) dokunmaz.
    Zip yapısı: FormOlusturma/FormOlusturma.exe + FormOlusturma/_internal/...
    """
    with zipfile.ZipFile(zip_yolu, "r") as z:
        # Önce eski app dosyalarını temizle
        internal_dir = os.path.join(hedef_dir, "_internal")
        if os.path.isdir(internal_dir):
            shutil.rmtree(internal_dir)
        exe_path = os.path.join(hedef_dir, "FormOlusturma.exe")
        if os.path.exists(exe_path):
            os.remove(exe_path)

        # Zip içeriğini çıkart (ilk klasör adını (FormOlusturma/) atlayarak)
        for uye in z.namelist():
            parcalar = Path(uye).parts
            if len(parcalar) < 2:
                continue  # kök dizin girişi, atla
            goreli = str(Path(*parcalar[1:]))
            hedef = os.path.join(hedef_dir, goreli)
            if uye.endswith("/"):
                os.makedirs(hedef, exist_ok=True)
            else:
                os.makedirs(os.path.dirname(hedef), exist_ok=True)
                with z.open(uye) as kaynak, open(hedef, "wb") as cikis:
                    shutil.copyfileobj(kaynak, cikis)


def masaustu_kisayol_olustur() -> None:
    desktop = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
    kisayol = os.path.join(desktop, f"{APP_NAME}.lnk")
    ps_script = (
        f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{kisayol}');"
        f"$s.TargetPath='{MAIN_EXE}';"
        f"$s.WorkingDirectory='{APP_INSTALL_DIR}';"
        f"$s.Save()"
    )
    subprocess.run(
        ["powershell", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", ps_script],
        capture_output=True,
    )


# ─────────────────────────────────────────────
# KURULUM MODU
# ─────────────────────────────────────────────

class KurulumPenceresi:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} Kurulum")
        self.root.geometry("440x190")
        self.root.resizable(False, False)
        self.root.eval("tk::PlaceWindow . center")
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)  # kapatmayı engelle

        tk.Label(
            self.root, text=f"{APP_NAME} kuruluyor...", font=("Segoe UI", 11, "bold")
        ).pack(pady=(22, 6))

        self.durum_var = tk.StringVar(value="Bağlanılıyor...")
        tk.Label(
            self.root, textvariable=self.durum_var, font=("Segoe UI", 9), fg="#555"
        ).pack()

        self.pb = ttk.Progressbar(self.root, length=380, mode="determinate")
        self.pb.pack(pady=14)

    def durum(self, mesaj: str) -> None:
        self.durum_var.set(mesaj)
        self.root.update_idletasks()

    def ilerleme(self, yuzde: float) -> None:
        self.pb["value"] = yuzde
        self.root.update_idletasks()

    def kapat(self) -> None:
        self.root.destroy()


def kurulum_modu() -> None:
    pencere = KurulumPenceresi()
    hata_kutusu: list[str] = []

    def _kur():
        try:
            pencere.durum("GitHub'dan son sürüm kontrol ediliyor...")
            _log("Kurulum başladı.")
            tag, url = github_son_surum()
            _log(f"Son sürüm: {tag}, URL: {url}")

            os.makedirs(APP_INSTALL_DIR, exist_ok=True)
            zip_gecici = os.path.join(APP_INSTALL_DIR, "_kurulum_temp.zip")

            pencere.durum(f"v{tag} indiriliyor...")
            zip_indir(url, zip_gecici, ilerleme_cb=pencere.ilerleme)

            pencere.durum("Dosyalar çıkartılıyor...")
            zip_ac_guncelle(zip_gecici, APP_INSTALL_DIR)
            os.remove(zip_gecici)

            # installer.exe kendisini uygulama dizinine kopyala
            kendi_yol = sys.executable if getattr(sys, "frozen", False) else __file__
            if os.path.abspath(kendi_yol) != os.path.abspath(INSTALLER_EXE):
                shutil.copy2(kendi_yol, INSTALLER_EXE)

            # version.txt yaz
            Path(VERSION_FILE).write_text(tag, encoding="utf-8")

            pencere.durum("Kısayol oluşturuluyor...")
            masaustu_kisayol_olustur()

            _log(f"Kurulum tamamlandı: v{tag}")
            pencere.root.after(0, pencere.kapat)

            messagebox.showinfo(
                "Kurulum Tamamlandı",
                f"{APP_NAME} v{tag} başarıyla kuruldu!\n"
                f"Konum: {APP_INSTALL_DIR}\n"
                f"Masaüstünde kısayol oluşturuldu.",
            )
            subprocess.Popen([MAIN_EXE], cwd=APP_INSTALL_DIR)

        except Exception as e:
            _log(f"Kurulum hatası: {e}")
            hata_kutusu.append(str(e))
            pencere.root.after(0, pencere.kapat)

    t = threading.Thread(target=_kur, daemon=True)
    t.start()
    pencere.root.mainloop()

    if hata_kutusu:
        messagebox.showerror("Kurulum Hatası", f"Kurulum başarısız:\n{hata_kutusu[0]}")
        sys.exit(1)


# ─────────────────────────────────────────────
# GÜNCELLEME MODU
# ─────────────────────────────────────────────

def guncelleme_modu(pid: int) -> None:
    try:
        yerel = yerel_versiyon()
        _log(f"Güncelleme kontrolü başladı. Yerel: {yerel}")
        tag, url = github_son_surum()
        _log(f"GitHub son sürüm: {tag}")

        if not versiyon_kucuk_mu(yerel, tag):
            _log("Güncelleme yok.")
            return

        # Güncelleme var — kullanıcıya sor
        root = tk.Tk()
        root.withdraw()
        cevap = messagebox.askyesno(
            "Güncelleme Mevcut",
            f"{APP_NAME} v{tag} mevcut (mevcut sürüm: v{yerel}).\n\n"
            f"Güncelleme yapılsın mı?\n"
            f"(Uygulama kapanıp güncellendikten sonra otomatik açılır.)",
        )
        root.destroy()

        if not cevap:
            _log("Kullanıcı güncellemeyi reddetti.")
            return

        _log("Güncelleme onaylandı. Flag oluşturuluyor.")
        Path(UPDATE_FLAG).write_text(tag, encoding="utf-8")

        # Ana uygulamanın kapanmasını bekle (max 30 saniye)
        for _ in range(60):
            if not process_calisiyor_mu(pid):
                break
            time.sleep(0.5)
        else:
            _log("Uygulama 30 saniyede kapanmadı, iptal ediliyor.")
            if os.path.exists(UPDATE_FLAG):
                os.remove(UPDATE_FLAG)
            return

        _log(f"İndirme başlıyor: {url}")
        zip_gecici = os.path.join(APP_INSTALL_DIR, "_guncelleme_temp.zip")
        zip_indir(url, zip_gecici)
        zip_ac_guncelle(zip_gecici, APP_INSTALL_DIR)
        os.remove(zip_gecici)

        Path(VERSION_FILE).write_text(tag, encoding="utf-8")

        if os.path.exists(UPDATE_FLAG):
            os.remove(UPDATE_FLAG)

        _log(f"Güncelleme tamamlandı: v{tag}")

        root2 = tk.Tk()
        root2.withdraw()
        messagebox.showinfo(
            "Güncelleme Tamamlandı",
            f"{APP_NAME} v{tag} sürümüne güncellendi.",
        )
        root2.destroy()

        subprocess.Popen([MAIN_EXE], cwd=APP_INSTALL_DIR)

    except Exception as e:
        _log(f"Güncelleme hatası: {e}")
        if os.path.exists(UPDATE_FLAG):
            os.remove(UPDATE_FLAG)


# ─────────────────────────────────────────────
# GİRİŞ NOKTASI
# ─────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"{APP_NAME} Installer/Updater")
    parser.add_argument("--update", action="store_true", help="Güncelleme modunda çalış")
    parser.add_argument("--pid", type=int, default=0, help="Ana uygulamanın PID'i")
    args = parser.parse_args()

    if args.update and args.pid:
        guncelleme_modu(args.pid)
    else:
        kurulum_modu()
