"""
Format Ayarları Dialog Modülü
==============================

Belge üretiminde kullanılan format ayarlarını yönetir.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QMessageBox

gunluk = logging.getLogger(__name__)


class FormatAyarlariDialog(QtWidgets.QMainWindow):
    """
    Format Ayarları Dialog Penceresi.
    
    Bu pencere, belge üretiminde kullanılan formatların
    ayarlarını saklar ve düzenler.
    """
    
    def __init__(self, parent=None):
        """Dialog başlatıcı."""
        super().__init__(parent)
        
        # UI dosyasını yükle
        ui_yolu = Path(__file__).parent.parent.parent / 'kaynaklar' / 'ui' / 'FormatAyarlari.ui'
        
        try:
            uic.loadUi(str(ui_yolu), self)
            gunluk.info(f"Format Ayarları UI yüklendi: {ui_yolu}")
        except Exception as e:
            gunluk.error(f"Format Ayarları UI yükleme hatası: {e}")
            raise
        
        # Yolları tanımla
        proje_kokü = Path(__file__).parent.parent.parent
        self.config_yolu = proje_kokü / 'kaynaklar' / 'veriler' / 'format_ayarlari.json'
        self.sablonlar_dizini = proje_kokü / 'kaynaklar' / 'sablonlar'
        self.urun_listesi_yolu = proje_kokü / 'kaynaklar' / 'veriler' / 'UrunListesi.csv'
        
        # Ayarları yükle
        self.ayarlar = self._ayarlari_yukle()
        
        # Başlangıç ayarları
        self._baslangic_ayarlarini_yukle()
        
        # Sinyalleri bağla
        self._sinyalleri_bagla()
    
    def _ayarlari_yukle(self) -> dict:
        """JSON dosyasından ayarları yükler."""
        try:
            if self.config_yolu.exists():
                with open(self.config_yolu, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                gunluk.warning(f"Ayar dosyası bulunamadı: {self.config_yolu}")
                return self._varsayilan_ayarlari_olustur()
        except Exception as e:
            gunluk.error(f"Ayar yükleme hatası: {e}")
            return self._varsayilan_ayarlari_olustur()
    
    def _varsayilan_ayarlari_olustur(self) -> dict:
        """Varsayılan ayarları oluşturur."""
        gunluk.info("Varsayılan ayarlar oluşturuluyor...")
        
        # Ürün listesini yükle
        urun_kodlari = self._urun_kodlarini_yukle()
        
        return {
            "formlar": {
                "Fiyat Teklifi": {
                    "duzen": [
                        "Başlık",
                        "Ürün Açıklama Metinleri",
                        "Ürün Tanım Tabloları",
                        "Fiyat Tablosu",
                        "Şartlar"
                    ],
                    "urun_siralamasi": urun_kodlari
                },
                "Keşif Özeti": {
                    "duzen": [
                        "Başlık",
                        "Ürün Tanım Tabloları",
                        "Fiyat Tablosu"
                    ],
                    "urun_siralamasi": urun_kodlari
                },
                "Tanım Formu": {
                    "duzen": [
                        "Başlık",
                        "Ürün Açıklama Metinleri",
                        "Şartlar"
                    ],
                    "urun_siralamasi": urun_kodlari
                }
            },
            "sablon_esleme": {
                "Başlık": "STANDART_BASLIK.docx",
                "Fiyat Tablosu": "FIYAT_TABLO.docx",
                "Şartlar": "SARTLAR.docx"
            }
        }
    
    def _urun_kodlarini_yukle(self) -> list[str]:
        """UrunListesi.csv'den ürün kodlarını yükler."""
        try:
            if not self.urun_listesi_yolu.exists():
                gunluk.warning(f"Ürün listesi bulunamadı: {self.urun_listesi_yolu}")
                return []
            
            urun_kodlari = []
            with open(self.urun_listesi_yolu, 'r', encoding='utf-8') as f:
                # İlk satırı atla (başlık)
                next(f)
                for satir in f:
                    parcalar = satir.strip().split(',')
                    if len(parcalar) >= 2:
                        urun_kodu = parcalar[1].strip()
                        if urun_kodu:
                            urun_kodlari.append(urun_kodu)
            
            gunluk.info(f"✓ {len(urun_kodlari)} ürün kodu yüklendi")
            return urun_kodlari
        
        except Exception as e:
            gunluk.error(f"Ürün kodu yükleme hatası: {e}")
            return []
    
    def _baslangic_ayarlarini_yukle(self):
        """Başlangıç ayarlarını yükler."""
        try:
            # ComboBox 1: Şablonlar (sablonlar/ klasöründen)
            self._sablonlari_yukle()
            
            # ComboBox 2: Formlar (JSON'dan)
            self._formlari_yukle()
            
            # İLK YÜKLEME: Form düzenini manuel olarak yükle
            self._form_duzeni_yukle()
            
            gunluk.info("✓ Başlangıç ayarları yüklendi")
        
        except Exception as e:
            gunluk.error(f"Başlangıç ayarları yükleme hatası: {e}")
    
    def _sablonlari_yukle(self):
        """Şablonları sablon_comboBox'a yükler."""
        try:
            combo = getattr(self, 'sablon_comboBox', None)
            if combo is None:
                return
            
            combo.clear()
            
            if not self.sablonlar_dizini.exists():
                gunluk.warning(f"Şablonlar dizini bulunamadı: {self.sablonlar_dizini}")
                return
            
            # .docx dosyalarını bul
            docx_dosyalar = sorted(self.sablonlar_dizini.glob('*.docx'))
            
            for dosya in docx_dosyalar:
                # Dosya adını (uzantısız) ekle
                combo.addItem(dosya.stem)
            
            gunluk.debug(f"{len(docx_dosyalar)} şablon yüklendi")
        
        except Exception as e:
            gunluk.error(f"Şablon yükleme hatası: {e}")
    
    def _formlari_yukle(self):
        """Formları formlar_comboBox'ye yükler."""
        try:
            combo = getattr(self, 'formlar_comboBox', None)
            if combo is None:
                return
            
            combo.clear()
            
            form_adlari = list(self.ayarlar.get('formlar', {}).keys())
            combo.addItems(form_adlari)
            
            gunluk.debug(f"{len(form_adlari)} form yüklendi")
        
        except Exception as e:
            gunluk.error(f"Form yükleme hatası: {e}")
    
    def _sinyalleri_bagla(self):
        """UI sinyallerini bağlar."""
        try:
            # Şablon Düzenle butonu (formatduzenle_buton)
            btn_sablon = getattr(self, 'formatduzenle_buton', None)
            if btn_sablon is not None:
                btn_sablon.clicked.connect(self._sablon_duzenle)
                gunluk.debug("Şablon Düzenle butonu bağlandı")
            
            # Form Düzeni Değiştir butonu (formduzen_button)
            btn_duzen = getattr(self, 'formduzen_button', None)
            if btn_duzen is not None:
                btn_duzen.clicked.connect(self._form_duzeni_yukle)
                gunluk.debug("Form Düzeni butonu bağlandı")
            
            # Form seçimi değiştiğinde düzeni yükle
            combo_form = getattr(self, 'formlar_comboBox', None)
            if combo_form is not None:
                combo_form.currentTextChanged.connect(lambda: self._form_duzeni_yukle())
            
            # Form düzeni listesi seçimi değiştiğinde ürün sıralamasını yükle
            list_duzen = getattr(self, 'formduzen_list', None)
            if list_duzen is not None:
                list_duzen.itemSelectionChanged.connect(self._urun_siralamasi_yukle)
            
            # OK/Cancel butonları
            button_box = getattr(self, 'buttonBox', None)
            if button_box is not None:
                button_box.accepted.connect(self._kaydet)
                button_box.rejected.connect(self._iptal)
                gunluk.debug("OK/Cancel butonları bağlandı")
            
            gunluk.info("✓ Sinyaller bağlandı")
        
        except Exception as e:
            gunluk.error(f"Sinyal bağlama hatası: {e}")
    
    def _sablon_duzenle(self):
        """Seçili şablonu Word/LibreOffice ile açar."""
        try:
            combo = getattr(self, 'sablon_comboBox', None)
            if combo is None or combo.count() == 0:
                QMessageBox.warning(
                    self,
                    "Uyarı",
                    "Şablon seçilmedi!",
                    QMessageBox.Ok
                )
                return
            
            secili_sablon = combo.currentText()
            dosya_yolu = self.sablonlar_dizini / f"{secili_sablon}.docx"
            
            if not dosya_yolu.exists():
                QMessageBox.critical(
                    self,
                    "Hata",
                    f"Şablon dosyası bulunamadı:\n{dosya_yolu}",
                    QMessageBox.Ok
                )
                return
            
            # İşletim sistemine göre aç
            if sys.platform == 'win32':
                os.startfile(str(dosya_yolu))
            elif sys.platform == 'darwin':  # macOS
                subprocess.call(['open', str(dosya_yolu)])
            else:  # Linux
                subprocess.call(['xdg-open', str(dosya_yolu)])
            
            gunluk.info(f"✓ Şablon açıldı: {secili_sablon}")
        
        except Exception as e:
            gunluk.error(f"Şablon açma hatası: {e}")
            QMessageBox.critical(
                self,
                "Hata",
                f"Şablon açılamadı:\n{str(e)}",
                QMessageBox.Ok
            )
    
    def _form_duzeni_yukle(self):
        """Seçili formun düzenini formduzen_list'a yükler."""
        try:
            combo = getattr(self, 'formlar_comboBox', None)
            list_widget = getattr(self, 'formduzen_list', None)
            
            if combo is None or list_widget is None:
                return
            
            secili_form = combo.currentText()
            if not secili_form:
                return
            
            # Form düzenini al
            form_verisi = self.ayarlar.get('formlar', {}).get(secili_form, {})
            duzen = form_verisi.get('duzen', [])
            
            # ListWidget'ı doldur
            list_widget.clear()
            list_widget.addItems(duzen)
            
            # urunsiralama_list'yi temizle
            list_widget_2 = getattr(self, 'urunsiralama_list', None)
            if list_widget_2 is not None:
                list_widget_2.clear()
            
            gunluk.info(f"✓ Form düzeni yüklendi: {secili_form} ({len(duzen)} öğe)")
        
        except Exception as e:
            gunluk.error(f"Form düzeni yükleme hatası: {e}")
    
    def _urun_siralamasi_yukle(self):
        """Seçili öğenin ürün sıralamasını urunsiralama_list'ye yükler."""
        try:
            list_duzen = getattr(self, 'formduzen_list', None)
            list_urun = getattr(self, 'urunsiralama_list', None)
            combo_form = getattr(self, 'formlar_comboBox', None)
            
            if not all([list_duzen, list_urun, combo_form]):
                return
            
            # Seçili öğeyi al
            secili_itemler = list_duzen.selectedItems()
            if not secili_itemler:
                list_urun.clear()
                return
            
            secili_oge = secili_itemler[0].text()
            
            # Sadece belirli öğeler için ürün sıralaması göster
            urun_siralamasi_gereken = [
                "Ürün Açıklama Metinleri",
                "Ürün Tanım Tabloları"
            ]
            
            if secili_oge not in urun_siralamasi_gereken:
                list_urun.clear()
                return
            
            # Form verisini al
            secili_form = combo_form.currentText()
            form_verisi = self.ayarlar.get('formlar', {}).get(secili_form, {})
            urun_siralamasi = form_verisi.get('urun_siralamasi', [])
            
            # ListWidget_2'yi doldur
            list_urun.clear()
            list_urun.addItems(urun_siralamasi)
            
            gunluk.debug(f"✓ Ürün sıralaması yüklendi: {secili_oge} ({len(urun_siralamasi)} ürün)")
        
        except Exception as e:
            gunluk.error(f"Ürün sıralaması yükleme hatası: {e}")
    
    def _kaydet(self):
        """OK butonu - Ayarları JSON dosyasına kaydet."""
        try:
            # Güncel durumu ayarlara yaz
            self._ayarlari_guncelle()
            
            # JSON dosyasına kaydet
            self.config_yolu.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_yolu, 'w', encoding='utf-8') as f:
                json.dump(self.ayarlar, f, ensure_ascii=False, indent=2)
            
            gunluk.info(f"✓ Ayarlar kaydedildi: {self.config_yolu}")
            
            QMessageBox.information(
                self,
                "Başarılı",
                "Format ayarları başarıyla kaydedildi!",
                QMessageBox.Ok
            )
            
            self.close()
        
        except Exception as e:
            gunluk.error(f"Kaydetme hatası: {e}")
            import traceback
            gunluk.error(traceback.format_exc())
            QMessageBox.critical(
                self,
                "Hata",
                f"Ayarlar kaydedilemedi:\n{str(e)}",
                QMessageBox.Ok
            )
    
    def _ayarlari_guncelle(self):
        """Mevcut UI durumunu ayarlara yazar."""
        try:
            combo_form = getattr(self, 'formlar_comboBox', None)
            list_duzen = getattr(self, 'formduzen_list', None)
            list_urun = getattr(self, 'urunsiralama_list', None)
            
            if not all([combo_form, list_duzen, list_urun]):
                return
            
            secili_form = combo_form.currentText()
            if not secili_form:
                return
            
            # Form düzenini güncelle
            duzen = []
            for i in range(list_duzen.count()):
                duzen.append(list_duzen.item(i).text())
            
            # Ürün sıralamasını güncelle
            urun_siralamasi = []
            for i in range(list_urun.count()):
                urun_siralamasi.append(list_urun.item(i).text())
            
            # Ayarlara yaz
            if 'formlar' not in self.ayarlar:
                self.ayarlar['formlar'] = {}
            
            if secili_form not in self.ayarlar['formlar']:
                self.ayarlar['formlar'][secili_form] = {}
            
            self.ayarlar['formlar'][secili_form]['duzen'] = duzen
            
            if urun_siralamasi:
                self.ayarlar['formlar'][secili_form]['urun_siralamasi'] = urun_siralamasi
            
            gunluk.debug(f"Ayarlar güncellendi: {secili_form}")
        
        except Exception as e:
            gunluk.error(f"Ayar güncelleme hatası: {e}")
    
    def _iptal(self):
        """Cancel butonu - Değişiklikleri iptal et."""
        try:
            gunluk.info("Format ayarları iptal edildi")
            self.close()
        except Exception as e:
            gunluk.error(f"İptal hatası: {e}")


# Test
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
    
    app = QApplication(sys.argv)
    dialog = FormatAyarlariDialog()
    dialog.show()
    sys.exit(app.exec_())
