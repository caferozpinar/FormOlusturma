#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kullanıcı Repository — Veritabanı erişim katmanı.
Sadece SQL sorguları ve Row → Domain model dönüşümü.
"""

import sqlite3
from typing import Optional

from uygulama.altyapi.veritabani import Veritabani
from uygulama.domain.modeller import Kullanici, KullaniciRolu
from uygulama.ortak.yardimcilar import logger_olustur, simdi_iso

logger = logger_olustur("kullanici_repo")


class KullaniciRepository:
    """Kullanıcı veritabanı işlemleri."""

    def __init__(self, db: Veritabani):
        self.db = db

    @staticmethod
    def _row_to_model(row: sqlite3.Row) -> Kullanici:
        """Veritabanı satırını domain modeline dönüştürür."""
        keys = row.keys() if hasattr(row, 'keys') else []
        return Kullanici(
            id=row["id"],
            kullanici_adi=row["kullanici_adi"],
            sifre_hash=row["sifre_hash"],
            rol=KullaniciRolu(row["rol"]),
            aktif=bool(row["aktif"]),
            ad=row["ad"] if "ad" in keys else "",
            soyad=row["soyad"] if "soyad" in keys else "",
            email=row["email"] if "email" in keys else "",
            olusturma_tarihi=row["olusturma_tarihi"],
            guncelleme_tarihi=row["guncelleme_tarihi"],
            silinme_tarihi=row["silinme_tarihi"],
        )

    def adi_ile_getir(self, kullanici_adi: str) -> Optional[Kullanici]:
        """Kullanıcı adına göre aktif kullanıcı getirir."""
        row = self.db.getir_tek(
            """SELECT * FROM kullanicilar
               WHERE kullanici_adi = ? AND silinme_tarihi IS NULL""",
            (kullanici_adi,)
        )
        return self._row_to_model(row) if row else None

    def id_ile_getir(self, kullanici_id: str) -> Optional[Kullanici]:
        """ID ile kullanıcı getirir."""
        row = self.db.getir_tek(
            """SELECT * FROM kullanicilar
               WHERE id = ? AND silinme_tarihi IS NULL""",
            (kullanici_id,)
        )
        return self._row_to_model(row) if row else None

    def tumu(self, aktif_sadece: bool = True) -> list[Kullanici]:
        """Tüm kullanıcıları listeler."""
        if aktif_sadece:
            rows = self.db.getir_hepsi(
                """SELECT * FROM kullanicilar
                   WHERE silinme_tarihi IS NULL AND aktif = 1
                   ORDER BY kullanici_adi"""
            )
        else:
            rows = self.db.getir_hepsi(
                """SELECT * FROM kullanicilar
                   WHERE silinme_tarihi IS NULL
                   ORDER BY kullanici_adi"""
            )
        return [self._row_to_model(r) for r in rows]

    def olustur(self, kullanici: Kullanici) -> Kullanici:
        """Yeni kullanıcı oluşturur."""
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO kullanicilar
                   (id, kullanici_adi, sifre_hash, rol, aktif,
                    ad, soyad, email,
                    olusturma_tarihi, guncelleme_tarihi)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    kullanici.id,
                    kullanici.kullanici_adi,
                    kullanici.sifre_hash,
                    kullanici.rol.value,
                    int(kullanici.aktif),
                    kullanici.ad,
                    kullanici.soyad,
                    kullanici.email,
                    kullanici.olusturma_tarihi,
                    kullanici.guncelleme_tarihi,
                )
            )
        logger.info(f"Kullanıcı oluşturuldu: {kullanici.kullanici_adi}")
        return kullanici

    def email_ile_getir(self, email: str) -> Optional[Kullanici]:
        """E-posta adresine göre aktif kullanıcı getirir."""
        row = self.db.getir_tek(
            """SELECT * FROM kullanicilar
               WHERE email = ? AND silinme_tarihi IS NULL""",
            (email,)
        )
        return self._row_to_model(row) if row else None

    def guncelle(self, kullanici: Kullanici) -> None:
        """Kullanıcı bilgilerini günceller."""
        with self.db.transaction() as conn:
            conn.execute(
                """UPDATE kullanicilar SET
                   kullanici_adi = ?, sifre_hash = ?, rol = ?,
                   aktif = ?, ad = ?, soyad = ?, email = ?,
                   guncelleme_tarihi = ?
                   WHERE id = ?""",
                (
                    kullanici.kullanici_adi,
                    kullanici.sifre_hash,
                    kullanici.rol.value,
                    int(kullanici.aktif),
                    kullanici.ad,
                    kullanici.soyad,
                    kullanici.email,
                    simdi_iso(),
                    kullanici.id,
                )
            )
        logger.info(f"Kullanıcı güncellendi: {kullanici.kullanici_adi}")

    def soft_delete(self, kullanici_id: str) -> None:
        """Kullanıcıyı soft delete ile siler."""
        with self.db.transaction() as conn:
            conn.execute(
                """UPDATE kullanicilar SET
                   silinme_tarihi = ?, guncelleme_tarihi = ?
                   WHERE id = ?""",
                (simdi_iso(), simdi_iso(), kullanici_id)
            )
        logger.info(f"Kullanıcı silindi (soft): {kullanici_id}")

    def kullanici_adi_mevcut_mu(self, kullanici_adi: str, haric_id: str = "") -> bool:
        """Kullanıcı adının zaten alınıp alınmadığını kontrol eder."""
        if haric_id:
            row = self.db.getir_tek(
                """SELECT COUNT(*) as sayi FROM kullanicilar
                   WHERE kullanici_adi = ? AND id != ?
                   AND silinme_tarihi IS NULL""",
                (kullanici_adi, haric_id)
            )
        else:
            row = self.db.getir_tek(
                """SELECT COUNT(*) as sayi FROM kullanicilar
                   WHERE kullanici_adi = ? AND silinme_tarihi IS NULL""",
                (kullanici_adi,)
            )
        return row["sayi"] > 0 if row else False
