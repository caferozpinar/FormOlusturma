#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sync Repository — SQLite snapshot yedekleme, sync metadata, conflict kayıtları.
"""

import os
import shutil
import sqlite3
from pathlib import Path
from typing import Optional

from uygulama.altyapi.veritabani import Veritabani
from uygulama.domain.modeller import _yeni_uuid
from uygulama.ortak.yardimcilar import logger_olustur, simdi_iso

logger = logger_olustur("sync_repo")


class SyncRepository:
    """Senkronizasyon veritabanı ve dosya işlemleri."""

    def __init__(self, db: Veritabani, sync_dizin: str = ""):
        self.db = db
        self.sync_dizin = sync_dizin or os.path.join(
            os.path.dirname(db.db_yolu), "sync")
        Path(self.sync_dizin).mkdir(parents=True, exist_ok=True)

    # ═════════════════════════════════════════
    # SNAPSHOT (SQLite Backup API)
    # ═════════════════════════════════════════

    def snapshot_olustur(self, hedef_yol: str = None) -> str:
        """
        Veritabanının tam snapshot'ını oluşturur (SQLite backup API).
        Returns: snapshot dosya yolu
        """
        if hedef_yol is None:
            ts = simdi_iso().replace(":", "-").replace("T", "_")[:19]
            # Aynı saniyede çakışmayı önlemek için uuid kısa suffix
            from uygulama.domain.modeller import _yeni_uuid
            suffix = _yeni_uuid()[:4]
            hedef_yol = os.path.join(
                self.sync_dizin, f"snapshot_{ts}_{suffix}.db")

        conn = self.db.baglan()
        hedef = sqlite3.connect(hedef_yol)
        try:
            conn.backup(hedef)
            logger.info(f"Snapshot oluşturuldu: {hedef_yol}")
        finally:
            hedef.close()

        return hedef_yol

    def snapshot_listele(self) -> list[dict]:
        """Mevcut snapshot dosyalarını listeler."""
        snapshots = []
        if not os.path.exists(self.sync_dizin):
            return snapshots
        for f in sorted(os.listdir(self.sync_dizin), reverse=True):
            if f.startswith("snapshot_") and f.endswith(".db"):
                tam_yol = os.path.join(self.sync_dizin, f)
                boyut = os.path.getsize(tam_yol)
                snapshots.append({
                    "dosya": f,
                    "yol": tam_yol,
                    "boyut": boyut,
                    "boyut_mb": round(boyut / (1024 * 1024), 2),
                    "tarih": f.replace("snapshot_", "").replace(".db", "")
                              .replace("_", "T").replace("-", ":", 2),
                })
        return snapshots

    def snapshot_sil(self, snapshot_yol: str) -> bool:
        """Snapshot dosyasını siler."""
        try:
            if os.path.exists(snapshot_yol):
                os.remove(snapshot_yol)
                logger.info(f"Snapshot silindi: {snapshot_yol}")
                return True
        except OSError as e:
            logger.error(f"Snapshot silinemedi: {e}")
        return False

    def eski_snapshotlari_temizle(self, sakla: int = 5) -> int:
        """En yeni N snapshot hariç diğerlerini siler."""
        snapshots = self.snapshot_listele()
        silinen = 0
        if len(snapshots) > sakla:
            for s in snapshots[sakla:]:
                if self.snapshot_sil(s["yol"]):
                    silinen += 1
        return silinen

    # ═════════════════════════════════════════
    # UZAK SYNC METADATA
    # ═════════════════════════════════════════

    def son_sync_bilgisi(self) -> Optional[dict]:
        """En son sync kaydını getirir."""
        row = self.db.getir_tek(
            """SELECT * FROM sync_metadata
               ORDER BY sync_tarihi DESC LIMIT 1""")
        return dict(row) if row else None

    def sync_kaydi_olustur(self, tur: str, durum: str, hedef: str = "",
                            detay: str = "") -> str:
        kayit_id = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO sync_metadata
                   (id, tur, durum, hedef, detay, sync_tarihi)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (kayit_id, tur, durum, hedef, detay, simdi_iso()))
        return kayit_id

    def sync_kaydi_guncelle(self, kayit_id: str, durum: str,
                             detay: str = "") -> None:
        with self.db.transaction() as conn:
            conn.execute(
                """UPDATE sync_metadata SET durum = ?, detay = ?,
                   tamamlanma_tarihi = ? WHERE id = ?""",
                (durum, detay, simdi_iso(), kayit_id))

    def sync_gecmisi(self, limit: int = 20) -> list[dict]:
        rows = self.db.getir_hepsi(
            """SELECT * FROM sync_metadata
               ORDER BY sync_tarihi DESC LIMIT ?""", (limit,))
        return [dict(r) for r in rows]

    # ═════════════════════════════════════════
    # CONFLICT KAYITLARI
    # ═════════════════════════════════════════

    def conflict_kaydet(self, sync_id: str, tablo: str, kayit_id: str,
                         alan: str, yerel_deger: str, uzak_deger: str,
                         cozum: str = "BEKLIYOR") -> str:
        c_id = _yeni_uuid()
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO sync_conflicts
                   (id, sync_id, tablo, kayit_id, alan,
                    yerel_deger, uzak_deger, cozum, tarih)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (c_id, sync_id, tablo, kayit_id, alan,
                 yerel_deger, uzak_deger, cozum, simdi_iso()))
        return c_id

    def conflict_coz(self, conflict_id: str, cozum: str) -> None:
        """Conflict'i çözümle. cozum: YEREL, UZAK, BIRLESTIR"""
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE sync_conflicts SET cozum = ? WHERE id = ?",
                (cozum, conflict_id))

    def bekleyen_conflictler(self, sync_id: str = None) -> list[dict]:
        if sync_id:
            rows = self.db.getir_hepsi(
                """SELECT * FROM sync_conflicts
                   WHERE sync_id = ? AND cozum = 'BEKLIYOR'
                   ORDER BY tarih""", (sync_id,))
        else:
            rows = self.db.getir_hepsi(
                """SELECT * FROM sync_conflicts
                   WHERE cozum = 'BEKLIYOR' ORDER BY tarih""")
        return [dict(r) for r in rows]

    def sync_conflictleri(self, sync_id: str) -> list[dict]:
        rows = self.db.getir_hepsi(
            "SELECT * FROM sync_conflicts WHERE sync_id = ? ORDER BY tarih",
            (sync_id,))
        return [dict(r) for r in rows]

    # ═════════════════════════════════════════
    # DEĞİŞİKLİK TAKİBİ
    # ═════════════════════════════════════════

    def son_sync_tarihinden_sonraki_degisiklikler(self) -> dict:
        """Son sync'ten sonra değişen kayıtları tespit eder."""
        son = self.son_sync_bilgisi()
        son_tarih = son["sync_tarihi"] if son else "2000-01-01"

        degisiklikler = {}
        tablolar = ["projeler", "belgeler", "belge_urunleri",
                     "belge_alt_kalemleri", "urunler", "urun_alanlari",
                     "urun_alan_secenekleri", "alt_kalemler"]

        for tablo in tablolar:
            try:
                rows = self.db.getir_hepsi(
                    f"""SELECT id, guncelleme_tarihi FROM {tablo}
                        WHERE guncelleme_tarihi > ?""",
                    (son_tarih,))
                if rows:
                    degisiklikler[tablo] = [dict(r) for r in rows]
            except Exception as timestamp_err:
                # Bazı tablolarda guncelleme_tarihi yoksa atla
                logger.debug(
                    f"Tablo '{tablo}' için timestamp sütunu bulunamadı. "
                    f"Fallback yapılıyor. Hata: {type(timestamp_err).__name__}"
                )
                try:
                    rows = self.db.getir_hepsi(
                        f"""SELECT id FROM {tablo}
                            WHERE rowid > (SELECT COALESCE(MAX(rowid), 0)
                            FROM {tablo} WHERE 1=0)""")
                except Exception as fallback_err:
                    logger.warning(
                        f"Tablo '{tablo}' okunması tamamen başarısız: {type(fallback_err).__name__} - {fallback_err}"
                    )

        return degisiklikler
