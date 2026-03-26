#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Drive Sync Servisi

Manuel tetikleme ile çift yönlü DB merge:
- Lock mekanizması (aynı anda tek kullanıcı)
- Tablo bazlı merge (UUID ile eşleştirme, zaman damgası ile çakışma tespiti)
- Şablon + belge dosyaları sync
"""

import os
import json
import shutil
import socket
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Callable

from uygulama.ortak.yardimcilar import logger_olustur, simdi_iso

logger = logger_olustur("drive_sync")

# ── Google API — modül seviyesinde import (PyInstaller statik analiz için şart) ──
# Kurulu değilse Drive özellikleri sessizce devre dışı kalır.
try:
    from google.oauth2.credentials import Credentials as _GCredentials
    from google_auth_oauthlib.flow import InstalledAppFlow as _GFlow
    from google.auth.transport.requests import Request as _GRequest
    from googleapiclient.discovery import build as _gbuild
    from googleapiclient.http import MediaFileUpload as _GMediaUpload
    from googleapiclient.http import MediaIoBaseDownload as _GMediaDownload
    _GOOGLE_OK = True
except ImportError as e:
    hatali_kutuphanele = str(e)
    logger.error(
        f"KRITIK HATA: Google API kütüphaneleri yüklenemedi.\n"
        f"Hata detayı: {hatali_kutuphanele}\n"
        f"Çözüm: Aşağıdaki komutu çalıştırın:\n"
        f"  pip install google-auth google-auth-oauthlib google-api-python-client\n"
        f"Kurulabilene kadar, Google Drive senkronizasyonu devre dışı olacaktır."
    )
    _GOOGLE_OK = False

# ═══════════════════════════════════════
# MERGE TABLOSU TANIMLARI
# ═══════════════════════════════════════

MERGE_TABLOLARI = [
    # ─── KATALOG / SEED ───
    {"tablo": "parametre_tipler",      "pk": "id", "zaman": "olusturma_tarihi", "olusturma": "olusturma_tarihi", "etiket_col": "kod"},
    {"tablo": "birimler",              "pk": "id", "zaman": "guncelleme_tarihi","olusturma": "guncelleme_tarihi","etiket_col": "kod"},
    {"tablo": "belge_turleri",         "pk": "id", "zaman": "guncelleme_tarihi","olusturma": "guncelleme_tarihi","etiket_col": "kod"},

    # ─── YER LOOKUP ───
    {"tablo": "ulkeler",               "pk": "id", "zaman": "olusturma_tarihi", "olusturma": "olusturma_tarihi", "etiket_col": "ad"},
    {"tablo": "sehirler",              "pk": "id", "zaman": "olusturma_tarihi", "olusturma": "olusturma_tarihi", "etiket_col": "ad",          "ust_fk": ("ulke_id", "ulkeler")},
    {"tablo": "tesis_turleri",         "pk": "id", "zaman": "olusturma_tarihi", "olusturma": "olusturma_tarihi", "etiket_col": "ad"},
    {"tablo": "konum_fiyatlar",        "pk": "id", "zaman": "olusturma_tarihi", "olusturma": "olusturma_tarihi", "etiket_col": "sehir"},
    {"tablo": "konum_maliyet_carpanlari", "pk": "id", "zaman": "created_at",    "olusturma": "created_at",       "etiket_col": "konum"},

    # ─── KULLANICILER ───
    {"tablo": "kullanicilar",          "pk": "id", "zaman": "guncelleme_tarihi","olusturma": "olusturma_tarihi", "etiket_col": "kullanici_adi"},

    # ─── ÜRÜN KATALOĞU ───
    {"tablo": "urunler",               "pk": "id", "zaman": "olusturma_tarihi", "olusturma": "olusturma_tarihi", "etiket_col": "ad"},
    {"tablo": "urun_alanlari",         "pk": "id", "zaman": "guncelleme_tarihi","olusturma": "guncelleme_tarihi","etiket_col": "etiket",       "ust_fk": ("urun_id", "urunler")},
    {"tablo": "urun_alan_secenekleri", "pk": "id", "zaman": "guncelleme_tarihi","olusturma": "guncelleme_tarihi","etiket_col": "deger",        "ust_fk": ("alan_id", "urun_alanlari")},
    {"tablo": "urun_versiyonlar",      "pk": "id", "zaman": "olusturma_tarihi", "olusturma": "olusturma_tarihi", "etiket_col": "urun_id",      "ust_fk": ("urun_id", "urunler")},
    {"tablo": "urun_parametreler",     "pk": "id", "zaman": "olusturma_tarihi", "olusturma": "olusturma_tarihi", "etiket_col": "ad",           "ust_fk": ("urun_versiyon_id", "urun_versiyonlar")},
    {"tablo": "parametre_dropdown_degerler", "pk": "id", "zaman": "guncelleme_tarihi", "olusturma": "guncelleme_tarihi", "etiket_col": "deger","ust_fk": ("parametre_id", "urun_parametreler")},

    # ─── ALT KALEMLER ───
    {"tablo": "alt_kalemler",          "pk": "id", "zaman": "guncelleme_tarihi","olusturma": "guncelleme_tarihi","etiket_col": "ad"},
    {"tablo": "urun_alt_kalemleri",    "pk": "id", "zaman": "guncelleme_tarihi","olusturma": "guncelleme_tarihi","etiket_col": "id",           "ust_fk": ("urun_id", "urunler")},
    {"tablo": "alt_kalem_versiyonlar", "pk": "id", "zaman": "olusturma_tarihi", "olusturma": "olusturma_tarihi", "etiket_col": "id",           "ust_fk": ("alt_kalem_id", "alt_kalemler")},
    {"tablo": "alt_kalem_parametreler","pk": "id", "zaman": "guncelleme_tarihi","olusturma": "guncelleme_tarihi","etiket_col": "ad",           "ust_fk": ("alt_kalem_versiyon_id", "alt_kalem_versiyonlar")},

    # ─── MALİYET ───
    {"tablo": "maliyet_sablonlar",     "pk": "id", "zaman": "olusturma_tarihi", "olusturma": "olusturma_tarihi", "etiket_col": "id",           "ust_fk": ("alt_kalem_versiyon_id", "alt_kalem_versiyonlar")},
    {"tablo": "maliyet_parametreler",  "pk": "id", "zaman": "guncelleme_tarihi","olusturma": "guncelleme_tarihi","etiket_col": "ad",           "ust_fk": ("maliyet_sablon_id", "maliyet_sablonlar")},
    {"tablo": "alt_kalem_parametre_kombinasyonlari", "pk": "id", "zaman": "created_at", "olusturma": "created_at", "etiket_col": "id",         "ust_fk": ("alt_kalem_id", "alt_kalemler")},
    {"tablo": "alt_kalem_maliyet_versiyonlari",      "pk": "id", "zaman": "created_at", "olusturma": "created_at", "etiket_col": "id",         "ust_fk": ("kombinasyon_id", "alt_kalem_parametre_kombinasyonlari")},
    {"tablo": "alt_kalem_maliyet_girdi_degerleri",   "pk": "id", "zaman": "guncelleme_tarihi", "olusturma": "guncelleme_tarihi", "etiket_col": "girdi_adi", "ust_fk": ("versiyon_id", "alt_kalem_maliyet_versiyonlari")},
    {"tablo": "alt_kalem_maliyet_formulleri",        "pk": "id", "zaman": "guncelleme_tarihi", "olusturma": "guncelleme_tarihi", "etiket_col": "alan_adi",  "ust_fk": ("versiyon_id", "alt_kalem_maliyet_versiyonlari")},

    # ─── PLACEHOLDER ───
    {"tablo": "placeholders",          "pk": "id", "zaman": "olusturma_tarihi", "olusturma": "olusturma_tarihi", "etiket_col": "kod"},
    {"tablo": "placeholder_kurallar",  "pk": "id", "zaman": "olusturma_tarihi", "olusturma": "olusturma_tarihi", "etiket_col": "id",           "ust_fk": ("placeholder_id", "placeholders")},

    # ─── PROJELER ───
    {"tablo": "projeler",              "pk": "id", "zaman": "guncelleme_tarihi","olusturma": "olusturma_tarihi", "etiket_col": "firma",        "alt_tablolar": ["proje_urunleri"]},
    {"tablo": "proje_urunleri",        "pk": "id", "zaman": "guncelleme_tarihi","olusturma": "olusturma_tarihi", "etiket_col": "urun_id",      "ust_fk": ("proje_id", "projeler")},
    {"tablo": "proje_maliyet_snapshot","pk": "id", "zaman": "olusturma_tarihi", "olusturma": "olusturma_tarihi", "etiket_col": "id",           "ust_fk": ("proje_id", "projeler")},

    # ─── BELGELER ───
    {"tablo": "belgeler",              "pk": "id", "zaman": "guncelleme_tarihi","olusturma": "olusturma_tarihi", "etiket_col": "tur",          "ust_fk": ("proje_id", "projeler")},
    {"tablo": "belge_urunleri",        "pk": "id", "zaman": "guncelleme_tarihi","olusturma": "guncelleme_tarihi","etiket_col": "id",           "ust_fk": ("belge_id", "belgeler")},
    {"tablo": "belge_alt_kalemleri",   "pk": "id", "zaman": "guncelleme_tarihi","olusturma": "guncelleme_tarihi","etiket_col": "id",           "ust_fk": ("belge_id", "belgeler")},

    # ─── TEKLİFLER ───
    {"tablo": "teklifler",             "pk": "id", "zaman": "guncelleme_tarihi","olusturma": "olusturma_tarihi", "etiket_col": "baslik",       "alt_tablolar": ["teklif_kalemleri"]},
    {"tablo": "teklif_kalemleri",      "pk": "id", "zaman": "guncelleme_tarihi","olusturma": "olusturma_tarihi", "etiket_col": "id",           "ust_fk": ("teklif_id", "teklifler"), "alt_tablolar": ["teklif_parametre_degerleri"]},
    {"tablo": "teklif_parametre_degerleri", "pk": "id", "zaman": "guncelleme_tarihi", "olusturma": "olusturma_tarihi", "etiket_col": "parametre_adi", "ust_fk": ("teklif_kalem_id", "teklif_kalemleri")},
    {"tablo": "belge_uretim_kayitlari","pk": "id", "zaman": "olusturma_tarihi", "olusturma": "olusturma_tarihi", "etiket_col": "dosya_adi",   "ust_fk": ("teklif_id", "teklifler")},

    # ─── BELGE ŞABLONLARI ───
    {"tablo": "belge_sablon_dosyalar", "pk": "id", "zaman": "yuklenme_tarihi",  "olusturma": "yuklenme_tarihi",  "etiket_col": "ad"},
    {"tablo": "belge_bolumler",        "pk": "id", "zaman": "guncelleme_tarihi","olusturma": "guncelleme_tarihi","etiket_col": "ad"},
    {"tablo": "belge_sablon_atamalari","pk": "id", "zaman": "guncelleme_tarihi","olusturma": "guncelleme_tarihi","etiket_col": "id",           "ust_fk": ("bolum_id", "belge_bolumler")},
]

# Lock süresi — bu süreden eski lock'lar geçersiz sayılır
LOCK_TIMEOUT_DAKIKA = 10


class DriveSyncServisi:
    """Google Drive üzerinden DB merge + dosya sync."""

    def __init__(self, db, db_yolu: str, drive_klasor_id: str = ""):
        self.db = db
        self.db_yolu = db_yolu
        self.drive_klasor_id = drive_klasor_id
        self._creds = None
        self._service = None
        self._token_yolu = os.path.join(
            os.path.dirname(db_yolu), "drive_token.json")
        self._token_ile_baglan()

    # ═══════════════════════════════════════
    # GOOGLE AUTH
    # ═══════════════════════════════════════

    def baglanti_durumu(self) -> bool:
        return self._service is not None

    def _token_ile_baglan(self) -> None:
        """
        Kaydedilmiş token dosyası varsa sessizce bağlanmayı dener.
        Kullanıcı etkileşimi gerektirmez; token süresi dolmuşsa yeniler.
        """
        if not os.path.exists(self._token_yolu):
            return
        if not _GOOGLE_OK:
            return
        try:
            SCOPES = ['https://www.googleapis.com/auth/drive']
            creds = _GCredentials.from_authorized_user_file(
                self._token_yolu, SCOPES)

            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(_GRequest())
                    with open(self._token_yolu, 'w') as f:
                        f.write(creds.to_json())
                    logger.debug("Google Drive token yenilendi.")
                except Exception as refresh_error:
                    logger.warning(
                        f"Google Drive token yenileme başarısız: {type(refresh_error).__name__}: {refresh_error}\n"
                        f"Token dosyası yolu: {self._token_yolu}"
                    )
                    return

            if creds and creds.valid:
                self._creds = creds
                self._service = _gbuild('drive', 'v3', credentials=creds)
                logger.info("Google Drive: kaydedilmiş token ile bağlantı kuruldu.")
        except FileNotFoundError as fnf:
            logger.debug(f"Token dosyası okunamadı (ilk başlatma?): {self._token_yolu} - {fnf}")
        except json.JSONDecodeError as jde:
            logger.warning(
                f"Token dosyası hatalı JSON: {self._token_yolu}\n"
                f"Detay: {jde}\n"
                "Token dosyası silinecek ve yeniden oluşturulacak."
            )
            try:
                os.remove(self._token_yolu)
            except Exception as cleanup_error:
                logger.error(f"Token dosyası silinemiyor: {cleanup_error}")
        except Exception as e:
            logger.warning(
                f"Google Drive token yükleme başarısız: {type(e).__name__}\n"
                f"Token dosyası: {self._token_yolu}\n"
                f"Hata: {e}\n"
                "Lütfen Google OAuth'u yeniden yetkilendirin."
            )

    def baglan(self, credentials_yolu: str = None) -> tuple[bool, str]:
        """Google OAuth ile bağlan."""
        if not _GOOGLE_OK:
            return False, ("Google API kütüphaneleri yüklü değil.\n"
                           "pip install google-auth google-auth-oauthlib "
                           "google-api-python-client")

        SCOPES = ['https://www.googleapis.com/auth/drive']

        creds = None
        if os.path.exists(self._token_yolu):
            try:
                creds = _GCredentials.from_authorized_user_file(
                    self._token_yolu, SCOPES)
            except Exception:
                pass

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(_GRequest())
                except Exception:
                    creds = None

            if not creds:
                if not credentials_yolu:
                    # Proje kökünde ara
                    for ad in ["credentials.json", "client_secret.json"]:
                        yol = os.path.join(os.path.dirname(self.db_yolu), "..", ad)
                        if os.path.exists(yol):
                            credentials_yolu = yol
                            break
                if not credentials_yolu or not os.path.exists(credentials_yolu):
                    proje_koku = os.path.dirname(os.path.dirname(self.db_yolu))
                    expected_path = os.path.join(proje_koku, "credentials.json")
                    return False, (
                        "credentials.json dosyası bulunamadı.\n\n"
                        f"Arama yapılan konumlar:\n"
                        f"  • {os.path.join(proje_koku, 'credentials.json')}\n"
                        f"  • {os.path.join(proje_koku, 'client_secret.json')}\n\n"
                        "Çözüm:\n"
                        "1. Google Cloud Console'dan OAuth 2.0 Client ID (Desktop) oluşturun\n"
                        "2. JSON dosyasını indirin ve aşağıdaki konuma yerleştirin:\n"
                        f"   {expected_path}\n\n"
                        "3. Dosya adı 'credentials.json' veya 'client_secret.json' olmalıdır.\n"
                        "4. Uygulamayı yeniden başlatın."
                    )

                try:
                    flow = _GFlow.from_client_secrets_file(
                        credentials_yolu, SCOPES)
                except FileNotFoundError as fnf:
                    logger.error(f"credentials.json okunamadı: {credentials_yolu} - {fnf}")
                    return False, (
                        f"credentials.json dosyası okunabilir değil.\n"
                        f"Dosya yolu: {credentials_yolu}\n"
                        f"Lütfen dosyanın var ve okunabilir olduğunu kontrol edin."
                    )
                except json.JSONDecodeError as jde:
                    logger.error(f"credentials.json JSON hatalı: {credentials_yolu} - {jde}")
                    return False, (
                        f"credentials.json dosyası geçersiz JSON içeridir.\n"
                        f"Dosya yolu: {credentials_yolu}\n"
                        f"Hata: {str(jde)}\n"
                        f"Dosyayı Google Cloud Console'dan yeniden indirin."
                    )
                except Exception as e:
                    logger.error(f"credentials.json işlenemiyor: {credentials_yolu} - {type(e).__name__}: {e}")
                    return False, (
                        f"credentials.json dosyası işlenemiyor.\n"
                        f"Dosya yolu: {credentials_yolu}\n"
                        f"Hata tipi: {type(e).__name__}\n"
                        f"Hata: {str(e)}"
                    )
                
                try:
                    creds = flow.run_local_server(port=0)
                except Exception as auth_error:
                    logger.error(f"Google OAuth yetkilendirmesi başarısız: {type(auth_error).__name__} - {auth_error}")
                    return False, (
                        f"Google OAuth yetkilendirmesi başarısız.\n"
                        f"Hata tipi: {type(auth_error).__name__}\n"
                        f"Hata: {str(auth_error)}\n\n"
                        "Tarayıcı pencerenizde Google hesabınıza giriş yapabildiğiniz "
                        "kontrol edin ve yetkilendirmeyi tamamlayın."
                    )

            with open(self._token_yolu, 'w') as f:
                f.write(creds.to_json())

        self._creds = creds
        self._service = _gbuild('drive', 'v3', credentials=creds)
        logger.info("Google Drive bağlantısı kuruldu.")
        return True, "Bağlantı başarılı."

    # ═══════════════════════════════════════
    # DRIVE DOSYA İŞLEMLERİ
    # ═══════════════════════════════════════

    def _dosya_bul(self, ad: str, klasor_id: str = None) -> Optional[dict]:
        """Drive'da dosya ara. Hata durumunda exception fırlatır."""
        kid = klasor_id or self.drive_klasor_id
        q = f"name='{ad}' and '{kid}' in parents and trashed=false"
        r = self._service.files().list(
            q=q, fields="files(id,name,modifiedTime)", spaces='drive'
        ).execute()
        files = r.get('files', [])
        return files[0] if files else None

    def _klasor_bul_veya_olustur(self, ad: str, ust_id: str = None) -> str:
        """Alt klasörü bul veya oluştur."""
        kid = ust_id or self.drive_klasor_id
        mevcut = self._dosya_bul(ad, kid)
        if mevcut:
            return mevcut['id']
        meta = {
            'name': ad,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [kid]
        }
        f = self._service.files().create(body=meta, fields='id').execute()
        return f['id']

    def _dosya_indir(self, file_id: str, hedef_yol: str):
        """Drive'dan dosya indir."""
        import io
        request = self._service.files().get_media(fileId=file_id)
        with open(hedef_yol, 'wb') as f:
            downloader = _GMediaDownload(f, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

    def _dosya_yukle(self, lokal_yol: str, ad: str, klasor_id: str = None) -> str:
        """Dosyayı Drive'a yükle (varsa güncelle)."""
        kid = klasor_id or self.drive_klasor_id
        mevcut = self._dosya_bul(ad, kid)
        media = _GMediaUpload(lokal_yol, resumable=True)

        if mevcut:
            f = self._service.files().update(
                fileId=mevcut['id'], media_body=media, fields='id'
            ).execute()
            return f['id']
        else:
            meta = {'name': ad, 'parents': [kid]}
            f = self._service.files().create(
                body=meta, media_body=media, fields='id'
            ).execute()
            return f['id']

    # ═══════════════════════════════════════
    # LOCK MEKANİZMASI
    # ═══════════════════════════════════════

    def _lock_kontrol(self) -> Optional[dict]:
        """Drive'da aktif lock var mı kontrol et."""
        try:
            lock = self._dosya_bul(".sync_lock")
        except Exception as e:
            logger.warning(f"Lock kontrol hatası: {type(e).__name__}: {e}")
            return None
        if not lock:
            return None

        # Lock içeriğini oku
        try:
            tmp = tempfile.mktemp(suffix='.json')
            self._dosya_indir(lock['id'], tmp)
            with open(tmp, 'r') as f:
                data = json.load(f)
            os.remove(tmp)
        except Exception:
            return None

        # Timeout kontrolü
        lock_zaman = datetime.fromisoformat(data.get("zaman", "2000-01-01"))
        if datetime.now() - lock_zaman > timedelta(minutes=LOCK_TIMEOUT_DAKIKA):
            logger.warning(f"Eski lock siliniyor: {data}")
            self._service.files().delete(fileId=lock['id']).execute()
            return None

        return data

    def _lock_al(self, kullanici: str) -> tuple[bool, str]:
        """Lock oluştur."""
        mevcut = self._lock_kontrol()
        if mevcut:
            return False, (f"Senkronizasyon devam ediyor!\n\n"
                           f"Kullanıcı: {mevcut.get('kullanici', '?')}\n"
                           f"Başlangıç: {mevcut.get('zaman', '?')}\n\n"
                           f"Lütfen bekleyin veya {LOCK_TIMEOUT_DAKIKA} dk sonra "
                           f"otomatik açılır.")

        data = {
            "kullanici": kullanici,
            "zaman": datetime.now().isoformat(),
            "makine": os.environ.get("COMPUTERNAME", os.environ.get("HOSTNAME", "?")),
        }
        tmp = tempfile.mktemp(suffix='.json')
        with open(tmp, 'w') as f:
            json.dump(data, f)
        self._dosya_yukle(tmp, ".sync_lock")
        os.remove(tmp)
        logger.info(f"Lock alındı: {kullanici}")
        return True, "Lock alındı."

    def _lock_birak(self):
        """Lock sil."""
        try:
            lock = self._dosya_bul(".sync_lock")
        except Exception as e:
            logger.warning(f"Lock bırakma hatası: {type(e).__name__}: {e}")
            return
        if lock:
            self._service.files().delete(fileId=lock['id']).execute()
            logger.info("Lock bırakıldı.")

    # ═══════════════════════════════════════
    # DB MERGE MOTORU
    # ═══════════════════════════════════════

    def _db_indir(self) -> Optional[str]:
        """Drive'dan DB'yi geçici dosyaya indir."""
        veri_klasor = self._klasor_bul_veya_olustur("veri")
        dosya = self._dosya_bul("proje_yonetimi.db", veri_klasor)
        if not dosya:
            return None  # Drive'da DB yok — ilk sync
        tmp = tempfile.mktemp(suffix='.db')
        self._dosya_indir(dosya['id'], tmp)
        return tmp

    def _db_yukle(self):
        """Lokal DB'yi Drive'a yükle (WAL-safe backup)."""
        import sqlite3 as _sqlite3
        tmp_backup = tempfile.mktemp(suffix='.db')
        try:
            src = _sqlite3.connect(self.db_yolu)
            dst = _sqlite3.connect(tmp_backup)
            src.backup(dst)
            src.close()
            dst.close()
            veri_klasor = self._klasor_bul_veya_olustur("veri")
            self._dosya_yukle(tmp_backup, "proje_yonetimi.db", veri_klasor)
        finally:
            if os.path.exists(tmp_backup):
                os.remove(tmp_backup)

    def merge(self, cakisma_callback: Callable = None,
              ilerleme_callback: Callable = None) -> tuple[bool, str, dict]:
        """
        Ana merge işlemi.

        cakisma_callback(tablo, lokal_kayit, drive_kayit) -> 'lokal' | 'drive' | 'atla'
        ilerleme_callback(mesaj)

        Returns: (ok, mesaj, istatistik)
        """
        islem_log: list[str] = []

        def _ilerleme(msg):
            logger.info(msg)
            if ilerleme_callback:
                ilerleme_callback(msg)

        def _log(msg):
            """Hem UI'a ilet hem kalıcı log'a ekle."""
            islem_log.append(msg)
            _ilerleme(msg)

        def _ozet(row: dict, maks=4) -> str:
            """Kayıt verisini kısa özet string'e çevirir."""
            items = list(row.items())[:maks]
            return " | ".join(f"{k}={str(v)[:30]}" for k, v in items)

        stats = {"eklenen": 0, "guncellenen": 0, "cakisma": 0, "degisiklik_yok": 0}

        # Drive'dan lokal'e eklenemeyen ID'leri takip et (UNIQUE çakışma veya FK hatası).
        # Çocuk tablolar, ebeveyn Drive ID'si burada kayıtlıysa atlanır.
        eksik_idler: dict[str, set] = {}

        _ilerleme("Drive'dan veritabanı indiriliyor...")
        drive_db_yolu = self._db_indir()

        if not drive_db_yolu:
            # İlk sync — lokali direkt yükle
            _log("Drive'da veritabanı yok — lokal yükleniyor (ilk sync)...")
            self._db_yukle()
            stats["islem_log"] = islem_log
            return True, "İlk senkronizasyon tamamlandı (lokal → Drive).", stats

        try:
            drive_conn = sqlite3.connect(drive_db_yolu)
            drive_conn.row_factory = sqlite3.Row

            for tbl_meta in MERGE_TABLOLARI:
                tablo = tbl_meta["tablo"]
                pk = tbl_meta["pk"]
                zaman_col = tbl_meta["zaman"]
                olusturma_col = tbl_meta.get("olusturma", "olusturma_tarihi")

                # Tüm kayıtları çek
                try:
                    lokal_rows = {r[pk]: dict(r) for r in
                                  self.db.getir_hepsi(f"SELECT * FROM {tablo}")}
                except Exception as e:
                    _log(f"[{tablo}] ⚠ lokal okunamadı: {e}")
                    lokal_rows = {}

                try:
                    drive_rows = {dict(r)[pk]: dict(r) for r in
                                  drive_conn.execute(f"SELECT * FROM {tablo}").fetchall()}
                except Exception as e:
                    _log(f"[{tablo}] ⚠ drive okunamadı: {e}")
                    drive_rows = {}

                lokal_ids = set(lokal_rows.keys())
                drive_ids = set(drive_rows.keys())

                _log(f"[{tablo}] lokal={len(lokal_rows)} satır, drive={len(drive_rows)} satır")

                # 1. Sadece lokal'de var → Drive'a ekle
                sadece_lokal = lokal_ids - drive_ids
                for rid in sadece_lokal:
                    row = lokal_rows[rid]
                    try:
                        self._kayit_ekle(drive_conn, tablo, row)
                        _log(f"  ↑LOKAL→DRIVE [{tablo}] id={rid}: {_ozet(row)}")
                        stats["eklenen"] += 1
                    except Exception as e:
                        _log(f"  ❌LOKAL→DRIVE [{tablo}] id={rid} HATA: {type(e).__name__}: {e} | veri={_ozet(row)}")

                # 2. Sadece Drive'da var → Lokal'e ekle
                sadece_drive = drive_ids - lokal_ids
                ust_fk = tbl_meta.get("ust_fk")  # (fk_col, ust_tablo) veya None
                for rid in sadece_drive:
                    row = drive_rows[rid]

                    # Üst FK kontrolü: üst tablonun Drive ID'si lokal'e eklenememişse bu
                    # satırı da atla ve takip listesine ekle (FK hatası oluşmadan önce).
                    if ust_fk:
                        fk_col, ust_tablo = ust_fk
                        fk_deger = row.get(fk_col)
                        if fk_deger and fk_deger in eksik_idler.get(ust_tablo, set()):
                            _log(
                                f"  ⏭ATLANDI [{tablo}] id={rid}: "
                                f"üst {ust_tablo}.{fk_deger} Drive'dan lokale eklenemedi"
                            )
                            eksik_idler.setdefault(tablo, set()).add(rid)
                            continue

                    try:
                        eklendi = self._kayit_ekle_lokal(tablo, row)
                        if eklendi:
                            _log(f"  ↓DRIVE→LOKAL [{tablo}] id={rid}: {_ozet(row)}")
                            stats["eklenen"] += 1
                        else:
                            _log(
                                f"  ⏭UNIQUE-ATLA [{tablo}] id={rid}: "
                                f"lokal'de başka UUID ile zaten mevcut"
                            )
                            eksik_idler.setdefault(tablo, set()).add(rid)
                    except Exception as e:
                        _log(f"  ❌DRIVE→LOKAL [{tablo}] id={rid} HATA: {type(e).__name__}: {e} | veri={_ozet(row)}")
                        eksik_idler.setdefault(tablo, set()).add(rid)

                # 3. İkisinde de var → karşılaştır
                ortak = lokal_ids & drive_ids
                for rid in ortak:
                    lr = lokal_rows[rid]
                    dr = drive_rows[rid]

                    # İçerik aynı mı?
                    if self._kayitlar_ayni(lr, dr):
                        stats["degisiklik_yok"] += 1
                        continue

                    # Zaman karşılaştır
                    lz = lr.get(zaman_col, "") or lr.get(olusturma_col, "") or ""
                    dz = dr.get(zaman_col, "") or dr.get(olusturma_col, "") or ""

                    if lz and dz and lz != dz:
                        if lz > dz:
                            # Lokal daha yeni → Drive'ı güncelle
                            try:
                                self._kayit_guncelle(drive_conn, tablo, pk, lr)
                                _log(f"  ✎LOKAL→DRIVE [{tablo}] id={rid}: lokal={lz} > drive={dz}")
                                stats["guncellenen"] += 1
                            except Exception as e:
                                _log(f"  ❌GÜNCELLE LOKAL→DRIVE [{tablo}] id={rid} HATA: {e}")
                        elif dz > lz:
                            # Drive daha yeni → Lokal'i güncelle
                            try:
                                self._kayit_guncelle_lokal(tablo, pk, dr)
                                _log(f"  ✎DRIVE→LOKAL [{tablo}] id={rid}: drive={dz} > lokal={lz}")
                                stats["guncellenen"] += 1
                            except Exception as e:
                                _log(f"  ❌GÜNCELLE DRIVE→LOKAL [{tablo}] id={rid} HATA: {e}")
                    elif lr != dr:
                        # Zaman bilgisi yok veya eşit ama içerik farklı → çakışma
                        stats["cakisma"] += 1
                        karar = "lokal"
                        if cakisma_callback:
                            karar = cakisma_callback(tablo, lr, dr)

                        _log(f"  ⚠ÇAKIŞMA [{tablo}] id={rid}: karar={karar} | "
                             f"lokal={_ozet(lr)} | drive={_ozet(dr)}")

                        if karar == "lokal":
                            try:
                                self._kayit_guncelle(drive_conn, tablo, pk, lr)
                            except Exception as e:
                                _log(f"  ❌ÇAKIŞMA LOKAL→DRIVE [{tablo}] id={rid} HATA: {e}")
                        elif karar == "drive":
                            try:
                                self._kayit_guncelle_lokal(tablo, pk, dr)
                            except Exception as e:
                                _log(f"  ❌ÇAKIŞMA DRIVE→LOKAL [{tablo}] id={rid} HATA: {e}")
                        # "atla" → hiçbir şey yapma

            drive_conn.commit()
            drive_conn.close()

            # Merge edilmiş Drive DB'yi yükle
            _ilerleme("Merge edilmiş veritabanı Drive'a yükleniyor...")
            veri_klasor = self._klasor_bul_veya_olustur("veri")
            self._dosya_yukle(drive_db_yolu, "proje_yonetimi.db", veri_klasor)

        except Exception as e:
            logger.error(f"Merge hatası: {e}")
            stats["islem_log"] = islem_log
            return False, f"Merge hatası: {e}", stats
        finally:
            if drive_db_yolu and os.path.exists(drive_db_yolu):
                os.remove(drive_db_yolu)

        # Lokal DB'yi de güncelle (Drive'dan eklenenler için)
        _ilerleme("Lokal veritabanı güncelleniyor...")
        self._db_yukle()

        toplam = stats["eklenen"] + stats["guncellenen"]
        if toplam == 0:
            msg = "Zaten güncel — değişiklik yok."
        else:
            msg = (f"Senkronizasyon tamamlandı.\n"
                   f"Eklenen: {stats['eklenen']}, "
                   f"Güncellenen: {stats['guncellenen']}, "
                   f"Çakışma: {stats['cakisma']}")
        stats["islem_log"] = islem_log
        return True, msg, stats

    def _kayitlar_ayni(self, r1: dict, r2: dict) -> bool:
        """İki kayıt aynı mı? (zaman hariç karşılaştır)"""
        ignore = {"guncelleme_tarihi", "olusturma_tarihi"}
        for k in r1:
            if k in ignore:
                continue
            if str(r1.get(k, "")) != str(r2.get(k, "")):
                return False
        return True

    def _kayit_ekle(self, conn, tablo: str, row: dict):
        """Drive DB'ye kayıt ekle. Hata durumunda exception fırlatır."""
        cols = list(row.keys())
        vals = [row[c] for c in cols]
        ph = ",".join(["?"] * len(cols))
        col_str = ",".join(cols)
        conn.execute(f"INSERT OR IGNORE INTO {tablo} ({col_str}) VALUES ({ph})", vals)

    def _kayit_ekle_lokal(self, tablo: str, row: dict) -> bool:
        """Lokal DB'ye kayıt ekle. True → eklendi, False → UNIQUE çakışma (atlandı)."""
        cols = list(row.keys())
        vals = [row[c] for c in cols]
        ph = ",".join(["?"] * len(cols))
        col_str = ",".join(cols)
        with self.db.transaction() as c:
            c.execute(f"INSERT OR IGNORE INTO {tablo} ({col_str}) VALUES ({ph})", vals)
            return c.rowcount > 0

    def _kayit_guncelle(self, conn, tablo: str, pk: str, row: dict):
        """Drive DB'de kayıt güncelle. Hata durumunda exception fırlatır."""
        sets = []
        vals = []
        for k, v in row.items():
            if k != pk:
                sets.append(f"{k}=?")
                vals.append(v)
        vals.append(row[pk])
        conn.execute(f"UPDATE {tablo} SET {','.join(sets)} WHERE {pk}=?", vals)

    def _kayit_guncelle_lokal(self, tablo: str, pk: str, row: dict):
        """Lokal DB'de kayıt güncelle. Hata durumunda exception fırlatır."""
        sets = []
        vals = []
        for k, v in row.items():
            if k != pk:
                sets.append(f"{k}=?")
                vals.append(v)
        vals.append(row[pk])
        with self.db.transaction() as c:
            c.execute(f"UPDATE {tablo} SET {','.join(sets)} WHERE {pk}=?", vals)

    # ═══════════════════════════════════════
    # DOSYA SYNC (Şablonlar + Belgeler)
    # ═══════════════════════════════════════

    def dosya_sync(self, ilerleme_callback: Callable = None) -> tuple[bool, str]:
        """Şablon ve belge dosyalarını sync et."""
        def _ilerleme(msg):
            logger.info(msg)
            if ilerleme_callback:
                ilerleme_callback(msg)

        # Şablonlar sync
        _ilerleme("Şablonlar senkronize ediliyor...")
        from uygulama.ortak.yardimcilar import kullanici_veri_dizini
        sablon_lokal = os.path.join(kullanici_veri_dizini(), "sablonlar")
        if os.path.isdir(sablon_lokal):
            sablon_drive = self._klasor_bul_veya_olustur("sablonlar")
            self._klasor_sync(sablon_lokal, sablon_drive, _ilerleme)

        return True, "Dosya senkronizasyonu tamamlandı."

    # ═══════════════════════════════════════
    # LOG SYNC
    # ═══════════════════════════════════════

    @staticmethod
    def _makine_adi() -> str:
        """Geçerli makine adını döndürür (Drive klasör adı için temizlenmiş)."""
        try:
            ad = socket.gethostname()
        except Exception:
            ad = (os.environ.get("COMPUTERNAME") or
                  os.environ.get("HOSTNAME") or "unknown")
        # Drive klasör adında güvenli olmayan karakterleri kaldır
        ad = "".join(c for c in ad if c.isalnum() or c in "-_.")[:50]
        return ad or "unknown"

    def log_sync(self, ilerleme_callback: Callable = None) -> tuple[bool, str]:
        """
        Lokal log dosyalarını Drive'a makineye özgü klasör altında yükler.

        Drive yapısı: loglar/{makine_adi}/YYYY-MM-DD.log

        Kurallar:
        - Aynı isimli dosya Drive'da varsa: Drive'dakini sil, lokali yükle (lokal kazanır).
        - Lokal'de 30 günden eski loglar silinir.
        - Drive'dan hiçbir zaman silme yapılmaz.
        - Bugün hâlâ yazılan aktif log da yüklenir (bir sonraki sync'te üstüne yazılır).
        """
        def _ilerleme(msg: str):
            logger.info(msg)
            if ilerleme_callback:
                ilerleme_callback(msg)

        makine = self._makine_adi()

        # Lokal log dizini: db_yolu = .../veri/proje.db → loglar/ bir üst dizinde
        log_lokal_dizin = Path(self.db_yolu).parent.parent / "loglar"
        if not log_lokal_dizin.is_dir():
            _ilerleme("Log dizini bulunamadı, log sync atlanıyor.")
            return True, "Log dizini yok."

        bugun = datetime.now().date()
        sinir = bugun - timedelta(days=30)

        lokal_loglar: list[Path] = []   # yüklenecek
        eski_loglar:  list[Path] = []   # silinecek (30 günden eski)

        for f in sorted(log_lokal_dizin.glob("*.log")):
            try:
                log_tarihi = datetime.strptime(f.stem, "%Y-%m-%d").date()
                if log_tarihi < sinir:
                    eski_loglar.append(f)
                else:
                    lokal_loglar.append(f)
            except ValueError:
                # Tarih formatına uymayan log dosyası → yükle, silme
                lokal_loglar.append(f)

        if not lokal_loglar and not eski_loglar:
            return True, "Yüklenecek log yok."

        # Drive'da loglar/{makine}/ klasörünü hazırla
        _ilerleme(f"Drive log klasörü hazırlanıyor: loglar/{makine}/")
        try:
            loglar_klas = self._klasor_bul_veya_olustur("loglar")
            makine_klas = self._klasor_bul_veya_olustur(makine, loglar_klas)
        except Exception as e:
            return False, f"Drive klasör oluşturulamadı: {e}"

        # Drive'daki mevcut log dosyalarını listele
        try:
            q = (f"'{makine_klas}' in parents and trashed=false "
                 f"and mimeType!='application/vnd.google-apps.folder'")
            r = self._service.files().list(
                q=q, fields="files(id,name)", spaces='drive'
            ).execute()
            # Ad → [id, ...] (teorik olarak aynı isimli birden fazla olabilir)
            drive_dosyalar: dict[str, list[str]] = {}
            for fi in r.get('files', []):
                drive_dosyalar.setdefault(fi['name'], []).append(fi['id'])
        except Exception as e:
            return False, f"Drive dosya listesi alınamadı: {e}"

        # Lokal logları yükle
        yuklenen = 0
        for log_f in lokal_loglar:
            ad = log_f.name
            _ilerleme(f"  ↑ {ad}")

            # Drive'da varsa tümünü sil (üst üste yığılmayı önle)
            for fid in drive_dosyalar.get(ad, []):
                try:
                    self._service.files().delete(fileId=fid).execute()
                except Exception as e:
                    logger.warning(f"Drive log silme hatası ({ad}): {e}")

            # Yükle
            try:
                media = _GMediaUpload(str(log_f), mimetype='text/plain',
                                      resumable=False)
                meta = {'name': ad, 'parents': [makine_klas]}
                self._service.files().create(
                    body=meta, media_body=media, fields='id'
                ).execute()
                yuklenen += 1
            except Exception as e:
                logger.warning(f"Log yükleme hatası ({ad}): {e}")

        # Lokal'de 30 günden eski logları sil
        silinen = 0
        for f in eski_loglar:
            try:
                f.unlink()
                silinen += 1
                _ilerleme(f"  🗑 Eski log silindi (lokal): {f.name}")
            except Exception as e:
                logger.warning(f"Lokal log silme hatası ({f.name}): {e}")

        ozet = (f"Log sync tamamlandı — Makine: {makine} | "
                f"Yüklenen: {yuklenen} | Lokal'den silinen: {silinen}")
        _ilerleme(ozet)
        return True, ozet

    def _klasor_sync(self, lokal_klasor: str, drive_klasor_id: str,
                     ilerleme: Callable = None):
        """Klasör içindeki dosyaları çift yönlü sync et."""
        # Lokal dosyaları listele
        lokal_dosyalar = {}
        if os.path.isdir(lokal_klasor):
            for f in os.listdir(lokal_klasor):
                yol = os.path.join(lokal_klasor, f)
                if os.path.isfile(yol):
                    lokal_dosyalar[f] = {
                        "yol": yol,
                        "mtime": datetime.fromtimestamp(os.path.getmtime(yol))
                    }

        # Drive dosyalarını listele
        q = f"'{drive_klasor_id}' in parents and trashed=false"
        r = self._service.files().list(
            q=q, fields="files(id,name,modifiedTime)", spaces='drive'
        ).execute()
        drive_dosyalar = {}
        for f in r.get('files', []):
            drive_dosyalar[f['name']] = {
                "id": f['id'],
                "mtime": datetime.fromisoformat(
                    f['modifiedTime'].replace('Z', '+00:00')).replace(tzinfo=None)
            }

        tum_dosyalar = set(lokal_dosyalar.keys()) | set(drive_dosyalar.keys())

        for ad in tum_dosyalar:
            l = lokal_dosyalar.get(ad)
            d = drive_dosyalar.get(ad)

            if l and not d:
                # Sadece lokal → yükle
                if ilerleme: ilerleme(f"  ↑ {ad}")
                self._dosya_yukle(l["yol"], ad, drive_klasor_id)

            elif d and not l:
                # Sadece Drive → indir
                if ilerleme: ilerleme(f"  ↓ {ad}")
                hedef = os.path.join(lokal_klasor, ad)
                self._dosya_indir(d["id"], hedef)

            elif l and d:
                # İkisinde de var → son değişen kazanır
                if l["mtime"] > d["mtime"]:
                    if ilerleme: ilerleme(f"  ↑ {ad} (lokal daha yeni)")
                    self._dosya_yukle(l["yol"], ad, drive_klasor_id)
                elif d["mtime"] > l["mtime"]:
                    if ilerleme: ilerleme(f"  ↓ {ad} (Drive daha yeni)")
                    hedef = os.path.join(lokal_klasor, ad)
                    self._dosya_indir(d["id"], hedef)

    def _sync_log_kaydet(self, kullanici: str, ok: bool, mesaj: str, stats: dict):
        """Sync sonucunu sync_log tablosuna kaydet."""
        import json
        log_satirlari = stats.pop("islem_log", []) if stats else []
        try:
            with self.db.transaction() as c:
                c.execute(
                    "INSERT INTO sync_log "
                    "(tarih, kullanici, sonuc, mesaj, stats, detay_log) "
                    "VALUES (datetime('now'), ?, ?, ?, ?, ?)",
                    (kullanici,
                     "basarili" if ok else "hata",
                     mesaj,
                     json.dumps({k: v for k, v in stats.items()
                                 if k != "islem_log"}, ensure_ascii=False),
                     "\n".join(log_satirlari))
                )
        except Exception as e:
            logger.warning(f"Sync log kaydedilemedi: {e}")

    # ═══════════════════════════════════════
    # ANA SYNC METODU
    # ═══════════════════════════════════════

    def sync(self, kullanici: str,
             cakisma_callback: Callable = None,
             ilerleme_callback: Callable = None) -> tuple[bool, str]:
        """
        Ana senkronizasyon — UI'dan çağrılır.

        1. Lock al
        2. DB merge
        3. Dosya sync
        4. Lock bırak
        """
        def _ilerleme(msg):
            if ilerleme_callback:
                ilerleme_callback(msg)

        if not self._service:
            return False, "Google Drive bağlantısı yok.\nÖnce bağlanın."

        if not self.drive_klasor_id:
            return False, "Drive klasör ID'si ayarlanmamış.\nAdmin → Ayarlar'dan girin."

        # 1. Lock
        _ilerleme("Lock kontrol ediliyor...")
        ok, msg = self._lock_al(kullanici)
        if not ok:
            return False, msg

        stats: dict = {}
        try:
            # 2. DB Merge
            ok, msg, stats = self.merge(cakisma_callback, ilerleme_callback)
            if not ok:
                self._sync_log_kaydet(kullanici, False, msg, stats)
                return False, msg

            # 3. Dosya sync
            ok2, msg2 = self.dosya_sync(ilerleme_callback)

            # 4. Log sync
            _ilerleme("─── Log senkronizasyonu başlıyor ───")
            ok3, msg3 = self.log_sync(ilerleme_callback)

            _ilerleme("Tamamlandı!")
            self._sync_log_kaydet(kullanici, True, msg, stats)
            return True, msg

        except Exception as e:
            logger.error(f"Sync hatası: {e}")
            self._sync_log_kaydet(kullanici, False, str(e), stats)
            return False, f"Senkronizasyon hatası: {e}"
        finally:
            # Lock bırak
            try:
                self._lock_birak()
            except Exception as e:
                logger.warning(f"Lock bırakma hatası: {e}")
