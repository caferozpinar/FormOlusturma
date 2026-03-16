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
    print(f"KRİTİK HATA: Google Modülü Yüklenemedi -> {e}")
    _GOOGLE_OK = False

# ═══════════════════════════════════════
# MERGE TABLOSU TANIMLARI
# ═══════════════════════════════════════

MERGE_TABLOLARI = [
    {
        "tablo": "projeler",
        "pk": "id",
        "zaman": "guncelleme_tarihi",
        "olusturma": "olusturma_tarihi",
        "etiket_col": "firma",  # çakışma dialogunda gösterilecek
        "alt_tablolar": ["proje_urunleri"],
    },
    {
        "tablo": "proje_urunleri",
        "pk": "id",
        "zaman": "guncelleme_tarihi",
        "olusturma": "olusturma_tarihi",
        "etiket_col": "urun_id",
        "ust_fk": ("proje_id", "projeler"),
    },
    {
        "tablo": "teklifler",
        "pk": "id",
        "zaman": "guncelleme_tarihi",
        "olusturma": "olusturma_tarihi",
        "etiket_col": "baslik",
        "alt_tablolar": ["teklif_kalemleri"],
    },
    {
        "tablo": "teklif_kalemleri",
        "pk": "id",
        "zaman": "guncelleme_tarihi",
        "olusturma": "olusturma_tarihi",
        "etiket_col": "id",
        "ust_fk": ("teklif_id", "teklifler"),
        "alt_tablolar": ["teklif_parametre_degerleri"],
    },
    {
        "tablo": "teklif_parametre_degerleri",
        "pk": "id",
        "zaman": "guncelleme_tarihi",
        "olusturma": "olusturma_tarihi",
        "etiket_col": "parametre_adi",
        "ust_fk": ("kalem_id", "teklif_kalemleri"),
    },
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
                creds.refresh(_GRequest())
                with open(self._token_yolu, 'w') as f:
                    f.write(creds.to_json())

            if creds and creds.valid:
                self._creds = creds
                self._service = _gbuild('drive', 'v3', credentials=creds)
                logger.info("Google Drive: kaydedilmiş token ile bağlantı kuruldu.")
        except Exception as e:
            logger.warning(f"Google Drive token yükleme başarısız: {e}")

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
                    return False, ("credentials.json bulunamadı.\n"
                                   "Google Cloud Console'dan OAuth credential indirin.")

                flow = _GFlow.from_client_secrets_file(
                    credentials_yolu, SCOPES)
                creds = flow.run_local_server(port=0)

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
        """Drive'da dosya ara."""
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
        lock = self._dosya_bul(".sync_lock")
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
        lock = self._dosya_bul(".sync_lock")
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
        """Lokal DB'yi Drive'a yükle."""
        veri_klasor = self._klasor_bul_veya_olustur("veri")
        self._dosya_yukle(self.db_yolu, "proje_yonetimi.db", veri_klasor)

    def merge(self, cakisma_callback: Callable = None,
              ilerleme_callback: Callable = None) -> tuple[bool, str, dict]:
        """
        Ana merge işlemi.

        cakisma_callback(tablo, lokal_kayit, drive_kayit) -> 'lokal' | 'drive' | 'atla'
        ilerleme_callback(mesaj)

        Returns: (ok, mesaj, istatistik)
        """
        def _ilerleme(msg):
            logger.info(msg)
            if ilerleme_callback:
                ilerleme_callback(msg)

        stats = {"eklenen": 0, "guncellenen": 0, "cakisma": 0, "degisiklik_yok": 0}

        _ilerleme("Drive'dan veritabanı indiriliyor...")
        drive_db_yolu = self._db_indir()

        if not drive_db_yolu:
            # İlk sync — lokali direkt yükle
            _ilerleme("Drive'da veritabanı yok — lokal yükleniyor...")
            self._db_yukle()
            return True, "İlk senkronizasyon tamamlandı (lokal → Drive).", stats

        try:
            drive_conn = sqlite3.connect(drive_db_yolu)
            drive_conn.row_factory = sqlite3.Row

            for tbl_meta in MERGE_TABLOLARI:
                tablo = tbl_meta["tablo"]
                pk = tbl_meta["pk"]
                zaman_col = tbl_meta["zaman"]
                olusturma_col = tbl_meta.get("olusturma", "olusturma_tarihi")
                etiket = tbl_meta.get("etiket_col", pk)

                _ilerleme(f"Tablo merge: {tablo}...")

                # Tüm kayıtları çek
                try:
                    lokal_rows = {r[pk]: dict(r) for r in
                                  self.db.getir_hepsi(f"SELECT * FROM {tablo}")}
                except Exception:
                    lokal_rows = {}

                try:
                    drive_rows = {dict(r)[pk]: dict(r) for r in
                                  drive_conn.execute(f"SELECT * FROM {tablo}").fetchall()}
                except Exception:
                    drive_rows = {}

                lokal_ids = set(lokal_rows.keys())
                drive_ids = set(drive_rows.keys())

                # 1. Sadece lokal'de var → Drive'a ekle
                sadece_lokal = lokal_ids - drive_ids
                for rid in sadece_lokal:
                    row = lokal_rows[rid]
                    self._kayit_ekle(drive_conn, tablo, row)
                    stats["eklenen"] += 1

                # 2. Sadece Drive'da var → Lokal'e ekle
                sadece_drive = drive_ids - lokal_ids
                for rid in sadece_drive:
                    row = drive_rows[rid]
                    self._kayit_ekle_lokal(tablo, row)
                    stats["eklenen"] += 1

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
                            self._kayit_guncelle(drive_conn, tablo, pk, lr)
                            stats["guncellenen"] += 1
                        elif dz > lz:
                            # Drive daha yeni → Lokal'i güncelle
                            self._kayit_guncelle_lokal(tablo, pk, dr)
                            stats["guncellenen"] += 1
                    elif lr != dr:
                        # Zaman bilgisi yok veya eşit ama içerik farklı → çakışma
                        stats["cakisma"] += 1
                        karar = "lokal"
                        if cakisma_callback:
                            karar = cakisma_callback(tablo, lr, dr)

                        if karar == "lokal":
                            self._kayit_guncelle(drive_conn, tablo, pk, lr)
                        elif karar == "drive":
                            self._kayit_guncelle_lokal(tablo, pk, dr)
                        # "atla" → hiçbir şey yapma

            drive_conn.commit()
            drive_conn.close()

            # Merge edilmiş Drive DB'yi yükle
            _ilerleme("Merge edilmiş veritabanı yükleniyor...")
            veri_klasor = self._klasor_bul_veya_olustur("veri")
            self._dosya_yukle(drive_db_yolu, "proje_yonetimi.db", veri_klasor)

        except Exception as e:
            logger.error(f"Merge hatası: {e}")
            return False, f"Merge hatası: {e}", stats
        finally:
            if drive_db_yolu and os.path.exists(drive_db_yolu):
                os.remove(drive_db_yolu)

        # Lokal DB'yi de güncelle (Drive'dan eklenenler için)
        _ilerleme("Lokal veritabanı güncelleniyor...")
        self._db_yukle()

        toplam = stats["eklenen"] + stats["guncellenen"]
        if toplam == 0:
            return True, "Zaten güncel — değişiklik yok.", stats
        return True, (f"Senkronizasyon tamamlandı.\n"
                       f"Eklenen: {stats['eklenen']}, "
                       f"Güncellenen: {stats['guncellenen']}, "
                       f"Çakışma: {stats['cakisma']}"), stats

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
        """Drive DB'ye kayıt ekle."""
        cols = list(row.keys())
        vals = [row[c] for c in cols]
        ph = ",".join(["?"] * len(cols))
        col_str = ",".join(cols)
        try:
            conn.execute(f"INSERT OR IGNORE INTO {tablo} ({col_str}) VALUES ({ph})", vals)
        except Exception as e:
            logger.warning(f"Drive'a ekleme hatası ({tablo}): {e}")

    def _kayit_ekle_lokal(self, tablo: str, row: dict):
        """Lokal DB'ye kayıt ekle."""
        cols = list(row.keys())
        vals = [row[c] for c in cols]
        ph = ",".join(["?"] * len(cols))
        col_str = ",".join(cols)
        try:
            with self.db.transaction() as c:
                c.execute(f"INSERT OR IGNORE INTO {tablo} ({col_str}) VALUES ({ph})", vals)
        except Exception as e:
            logger.warning(f"Lokal'e ekleme hatası ({tablo}): {e}")

    def _kayit_guncelle(self, conn, tablo: str, pk: str, row: dict):
        """Drive DB'de kayıt güncelle."""
        sets = []
        vals = []
        for k, v in row.items():
            if k != pk:
                sets.append(f"{k}=?")
                vals.append(v)
        vals.append(row[pk])
        try:
            conn.execute(
                f"UPDATE {tablo} SET {','.join(sets)} WHERE {pk}=?", vals)
        except Exception as e:
            logger.warning(f"Drive güncelleme hatası ({tablo}): {e}")

    def _kayit_guncelle_lokal(self, tablo: str, pk: str, row: dict):
        """Lokal DB'de kayıt güncelle."""
        sets = []
        vals = []
        for k, v in row.items():
            if k != pk:
                sets.append(f"{k}=?")
                vals.append(v)
        vals.append(row[pk])
        try:
            with self.db.transaction() as c:
                c.execute(
                    f"UPDATE {tablo} SET {','.join(sets)} WHERE {pk}=?", vals)
        except Exception as e:
            logger.warning(f"Lokal güncelleme hatası ({tablo}): {e}")

    # ═══════════════════════════════════════
    # DOSYA SYNC (Şablonlar + Belgeler)
    # ═══════════════════════════════════════

    def dosya_sync(self, ilerleme_callback: Callable = None) -> tuple[bool, str]:
        """Şablon ve belge dosyalarını sync et."""
        def _ilerleme(msg):
            logger.info(msg)
            if ilerleme_callback:
                ilerleme_callback(msg)

        proje_kok = os.path.dirname(self.db_yolu)

        # Şablonlar sync
        _ilerleme("Şablonlar senkronize ediliyor...")
        sablon_lokal = os.path.join(proje_kok, "sablonlar")
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

        try:
            # 2. DB Merge
            ok, msg, stats = self.merge(cakisma_callback, ilerleme_callback)
            if not ok:
                return False, msg

            # 3. Dosya sync
            ok2, msg2 = self.dosya_sync(ilerleme_callback)

            # 4. Log sync
            _ilerleme("─── Log senkronizasyonu başlıyor ───")
            ok3, msg3 = self.log_sync(ilerleme_callback)

            _ilerleme("Tamamlandı!")
            return True, msg

        except Exception as e:
            logger.error(f"Sync hatası: {e}")
            return False, f"Senkronizasyon hatası: {e}"
        finally:
            # 4. Lock bırak
            try:
                self._lock_birak()
            except Exception as e:
                logger.warning(f"Lock bırakma hatası: {e}")
