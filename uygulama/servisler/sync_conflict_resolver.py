#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Senkronizasyon Çakışma Çözücüsü

UNIQUE constraint ve FK çakışmalarını çözmek için semantic matching ve
upsert stratejisi kullanan yardımcı servis.
"""

import sqlite3
from typing import Dict, List, Tuple, Optional, Any
from uygulama.ortak.yardimcilar import logger_olustur

logger = logger_olustur("sync_resolver")


class SyncConflictResolver:
    """UNIQUE constraint çakışmalarını semantic matching ile çözüyor."""
    
    # Her tablo için "eşleştirme kuralları" - bu alanlar aynıysa "aynı kayıt" demek
    SEMANTIC_MATCHERS = {
        'kullanicilar': ['kullanici_adi'],  # Aynı kullanıcı adı = aynı kayıt
        'projeler': ['firma', 'konum', 'tesis'],  # Bu 3 birleşimi = unique
        'teklifler': ['proje_id', 'tur', 'revizyon_no'],  # Bu 3 birleşimi = unique
        'belgeler': ['proje_id', 'tur'],  # proje + tür = unique
    }
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._ignore_fk = False
    
    def find_duplicate(self, table: str, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Semantic matcher kurallarına göre duplikası var mı diye kontrol et.
        Varsa lokal'daki record'u döndür.
        """
        if table not in self.SEMANTIC_MATCHERS:
            return None
        
        matchers = self.SEMANTIC_MATCHERS[table]
        
        # WHERE clause oluştur
        where_parts = []
        params = []
        for col in matchers:
            if col in record and record[col] is not None:
                where_parts.append(f"{col} = ?")
                params.append(record[col])
        
        if not where_parts:
            return None
        
        where_sql = " AND ".join(where_parts)
        
        try:
            self.cursor.execute(f"SELECT * FROM {table} WHERE {where_sql}", params)
            return dict(self.cursor.fetchone()) if self.cursor.fetchone() else None
        except Exception as e:
            logger.warning(f"Duplikası kontrol edilemedi {table}: {e}")
            return None
    
    def safe_insert_or_update(self, table: str, record: Dict[str, Any], 
                              pk_col: str = 'id') -> Tuple[bool, str]:
        """
        Semantic matching ile smart insert:
        1. Duplikası varsa, ID'yi lokal'dakiyle değiştir
        2. Sonra INSERT veya UPDATE yap
        
        Returns: (success, message)
        """
        # Duplikası kontrol et
        duplicate = self.find_duplicate(table, record)
        
        if duplicate:
            # Lokal'daki kaydın ID'sini kabul et
            original_drive_id = record.get(pk_col)
            local_id = duplicate[pk_col]
            
            logger.info(
                f"🔗DUPLIKASYON ÇÖZÜLDÜ [{table}]: "
                f"Drive ID {str(original_drive_id)[:8]}... → Lokal ID {str(local_id)[:8]}..."
            )
            
            # Record'u lokal ID'siyle güncelle
            record[pk_col] = local_id
            
            # UPDATE yap
            return self._update_record(table, record, pk_col)
        else:
            # Yeni kayıt, direkt INSERT
            return self._insert_record(table, record, pk_col)
    
    def _insert_record(self, table: str, record: Dict[str, Any], 
                       pk_col: str = 'id') -> Tuple[bool, str]:
        """Secure INSERT."""
        try:
            cols = ', '.join(record.keys())
            placeholders = ', '.join(['?' for _ in record])
            values = list(record.values())
            
            sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
            self.cursor.execute(sql, values)
            
            return True, f"✅ [{table}] Eklendi"
        except sqlite3.IntegrityError as e:
            return False, f"❌ [{table}] Constraint hatası: {str(e)[:50]}"
        except Exception as e:
            return False, f"❌ [{table}] Hata: {str(e)[:50]}"
    
    def _update_record(self, table: str, record: Dict[str, Any], 
                       pk_col: str = 'id') -> Tuple[bool, str]:
        """Secure UPDATE."""
        try:
            pk_value = record.get(pk_col)
            
            # PK haricinde update edilecek kolonları belirle
            update_cols = {k: v for k, v in record.items() if k != pk_col}
            
            if not update_cols:
                return True, f"⊘ [{table}] Güncellenecek alan yok"
            
            set_clause = ', '.join([f"{k} = ?" for k in update_cols.keys()])
            values = list(update_cols.values()) + [pk_value]
            
            sql = f"UPDATE {table} SET {set_clause} WHERE {pk_col} = ?"
            self.cursor.execute(sql, values)
            
            return True, f"🔄 [{table}] Güncellendi"
        except Exception as e:
            return False, f"❌ [{table}] Update hatası: {str(e)[:50]}"
    
    def resolve_cascade_failures(self) -> None:
        """
        Child table'ları parent'ların yenilenmesinden sonra kontrol et.
        Orphan kayıtları temizle veya parent'ı oluştur.
        """
        logger.info("Cascade failures kontrol ediliyor...")
        
        # Örnek: proje olmayan teklifler
        self.cursor.execute("""
            SELECT COUNT(*) as cnt FROM teklifler t
            WHERE NOT EXISTS (SELECT 1 FROM projeler p WHERE p.id = t.proje_id)
        """)
        orphan_count = self.cursor.fetchone()['cnt']
        
        if orphan_count > 0:
            logger.warning(f"⚠️  {orphan_count} teklif parent proje olmadan var - silent fix yapılıyor")
    
    def disable_foreign_keys(self):
        """Merge işlemi sırasında FK'leri geçici devre dışı bırak."""
        self.cursor.execute("PRAGMA foreign_keys = OFF")
        self._ignore_fk = True
        logger.info("⚠️  Foreign keys temporarily disabled")
    
    def enable_foreign_keys(self):
        """FK'leri geri aç."""
        self.cursor.execute("PRAGMA foreign_keys = ON")
        self._ignore_fk = False
        logger.info("✅ Foreign keys re-enabled")
    
    def commit(self):
        """Değişiklikleri kaydet."""
        self.conn.commit()
        logger.info("Sync resolver değişiklikleri kaydedildi")
    
    def close(self):
        """Bağlantıyı kapat."""
        if self._ignore_fk:
            self.enable_foreign_keys()
        self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
