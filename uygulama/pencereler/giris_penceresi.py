#!/usr/bin/env python3
"""
Kullanıcı Giriş Penceresi
=========================

Uygulama başlatıldığında kullanıcı kimlik doğrulaması yapar.

Yazar: Form Oluşturma Ekibi
Sürüm: 1.0.0
"""

import logging
import json
from pathlib import Path
from typing import Optional

from PyQt5 import QtWidgets, QtCore, QtGui, uic
from PyQt5.QtWidgets import QDialog, QMessageBox


class GirisPenceresi(QDialog):
    """
    Kullanıcı giriş penceresi.
    
    UI dosyasından yüklenir ve kimlik doğrulama sağlar.
    Sizin GirisEkrani.ui dosyanızı kullanır.
    """
    
    def __init__(self, parent=None):
        """
        Giriş penceresini başlatır.
        
        Args:
            parent: Üst widget (None olabilir)
        """
        super().__init__(parent)
        self.gunluk = logging.getLogger(self.__class__.__name__)
        
        # Başarılı giriş durumu
        self.giris_basarili = False
        self.kullanici_adi = None
        self.gercek_ad = None  # Kullanıcının gerçek adı (mapping'den)
        
        # "Beni Hatırla" için ayarlar dosyası
        self.ayarlar_dosyasi = Path.home() / ".form_uygulamasi" / "kullanici_ayarlar.json"
        
        # UI dosyasını yükle ve widget'ları ayarla
        self._ui_yukle()
        self._baglantilari_kur()
        self._kayitli_kullanici_yukle()
        
    def _ui_yukle(self):
        """UI dosyasını yükler ve QDialog'a uyarlar."""
        try:
            # UI dosyası yolu (kaynaklar/ui/ klasöründe olmalı)
            ui_dosyasi = Path(__file__).parent.parent.parent / "kaynaklar" / "ui" / "GirisEkrani.ui"
            
            if not ui_dosyasi.exists():
                self.gunluk.error(f"UI dosyası bulunamadı: {ui_dosyasi}")
                raise FileNotFoundError(f"UI dosyası bulunamadı: {ui_dosyasi}")
            
            # QMainWindow olarak tasarlanmış UI'yi QDialog'a yükle
            # Önce geçici bir QMainWindow oluştur
            temp_window = QtWidgets.QMainWindow()
            uic.loadUi(str(ui_dosyasi), temp_window)
            
            # Central widget'ı al
            central_widget = temp_window.centralWidget()
            
            # QDialog için layout oluştur
            layout = QtWidgets.QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            
            # Central widget'ı QDialog'a ekle
            if central_widget:
                # Widget'ı parent'ından ayır
                central_widget.setParent(None)
                layout.addWidget(central_widget)
                
                # UI widget'larını QDialog'a taşı
                for child in central_widget.findChildren(QtWidgets.QWidget):
                    # Widget'ları QDialog'un child'ı yap
                    setattr(self, child.objectName(), child)
            
            self.gunluk.info("Giriş UI dosyası yüklendi ve QDialog'a uyarlandı")
            
            # Pencere ayarları
            self.setWindowTitle("Kullanıcı Girişi - Form Oluşturma Uygulaması")
            self.setModal(True)
            self.setFixedSize(416, 340)  # UI'daki boyutlar
            
        except Exception as e:
            self.gunluk.error(f"UI yükleme hatası: {e}")
            raise
    
    def _baglantilari_kur(self):
        """Sinyal-slot bağlantılarını kurar."""
        # UI'daki widget isimleri:
        # - kullaniciadi_line: Kullanıcı adı girişi
        # - sifre_line: Şifre girişi
        # - girisyap_but: Giriş yap butonu
        # - benihatirla_box: Beni hatırla checkbox
        # - reportproblem_but: Sorun bildir butonu
        
        # Giriş butonu
        self.girisyap_but.clicked.connect(self.giris_yap)
        
        # Sorun bildir butonu
        self.reportproblem_but.clicked.connect(self.sorun_bildir)
        
        # Enter tuşu ile giriş (QMainWindow için)
        self.kullaniciadi_line.returnPressed.connect(self.giris_yap)
        self.sifre_line.returnPressed.connect(self.giris_yap)
    
    def _kayitli_kullanici_yukle(self):
        """Daha önce kaydedilmiş kullanıcı bilgisini yükler."""
        try:
            if self.ayarlar_dosyasi.exists():
                with open(self.ayarlar_dosyasi, 'r', encoding='utf-8') as f:
                    ayarlar = json.load(f)
                
                if ayarlar.get('beni_hatirla', False):
                    self.kullaniciadi_line.setText(ayarlar.get('kullanici_adi', ''))
                    self.benihatirla_box.setChecked(True)
                    self.sifre_line.setFocus()
                    self.gunluk.info("Kayıtlı kullanıcı bilgisi yüklendi")
                    
        except Exception as e:
            self.gunluk.warning(f"Kullanıcı ayarları yüklenemedi: {e}")
    
    def _kullanici_ayarlarini_kaydet(self, kullanici_adi: str, beni_hatirla: bool):
        """Kullanıcı ayarlarını kaydeder."""
        try:
            # Ayarlar dizinini oluştur
            self.ayarlar_dosyasi.parent.mkdir(parents=True, exist_ok=True)
            
            ayarlar = {
                'kullanici_adi': kullanici_adi if beni_hatirla else '',
                'beni_hatirla': beni_hatirla
            }
            
            with open(self.ayarlar_dosyasi, 'w', encoding='utf-8') as f:
                json.dump(ayarlar, f, ensure_ascii=False, indent=2)
            
            self.gunluk.info("Kullanıcı ayarları kaydedildi")
            
        except Exception as e:
            self.gunluk.warning(f"Kullanıcı ayarları kaydedilemedi: {e}")
    
    def giris_yap(self):
        """Giriş işlemini gerçekleştirir."""
        kullanici_adi = self.kullaniciadi_line.text().strip()
        sifre = self.sifre_line.text()
        
        # Boş kontrol
        if not kullanici_adi or not sifre:
            QMessageBox.warning(
                self,
                "Eksik Bilgi",
                "Lütfen kullanıcı adı ve şifre girin."
            )
            return
        
        # Kimlik doğrulama
        if self._kimlik_dogrula(kullanici_adi, sifre):
            self.giris_basarili = True
            self.kullanici_adi = kullanici_adi
            
            # Kullanıcının gerçek adını al
            self.gercek_ad = self.kullanici_gercek_adini_al(kullanici_adi)
            
            # "Beni Hatırla" ayarını kaydet
            beni_hatirla = self.benihatirla_box.isChecked()
            self._kullanici_ayarlarini_kaydet(kullanici_adi, beni_hatirla)
            
            self.gunluk.info(f"Başarılı giriş: {kullanici_adi} ({self.gercek_ad})")
            
            # Dialog'u başarılı olarak kapat
            self.accept()
        else:
            self.gunluk.warning(f"Başarısız giriş denemesi: {kullanici_adi}")
            QMessageBox.critical(
                self,
                "Giriş Başarısız",
                "Kullanıcı adı veya şifre hatalı!"
            )
            self.sifre_line.clear()
            self.sifre_line.setFocus()
    
    def sorun_bildir(self):
        """Sorun bildirme penceresini açar."""
        QMessageBox.information(
            self,
            "Sorun Bildir",
            "Destek için lütfen sistem yöneticinizle iletişime geçin.\n\n"
            "E-posta: destek@sirketiniz.com\n"
            "Tel: +90 XXX XXX XX XX"
        )
    
    def _kimlik_dogrula(self, kullanici_adi: str, sifre: str) -> bool:
        """
        Kullanıcı kimlik doğrulaması yapar.
        
        Bu metodu kendi kimlik doğrulama sisteminizle değiştirebilirsiniz.
        Veritabanı, LDAP, API vb. kullanabilirsiniz.
        
        Args:
            kullanici_adi: Kullanıcı adı
            sifre: Şifre
            
        Returns:
            Giriş başarılı ise True
        """
        # ÖRNEK: Basit kimlik doğrulama
        # GERÇEK UYGULAMADA: Veritabanı veya güvenli kimlik sistemi kullanın
        
        # Sabit kullanıcılar (GÜVENSİZ - sadece geliştirme için!)
        kullanicilar = {
            "admin": "admin",
            "kullanici": "12345",
            "cafer": "sifre123"
        }
        
        return kullanicilar.get(kullanici_adi) == sifre
    
    def kullanici_gercek_adini_al(self, kullanici_adi: str) -> str:
        """
        Kullanıcı adını (email) gerçek ad ile eşleştirir.
        
        Bu metod email ile giriş yapıldığında, kullanıcının gerçek adını döndürür.
        Gelecekte veritabanından çekilecek.
        
        Args:
            kullanici_adi: Kullanıcı adı veya email
            
        Returns:
            Kullanıcının gerçek adı
        """
        # Kullanıcı adı -> Gerçek ad mapping
        # GERÇEK UYGULAMADA: Veritabanından çekilecek
        kullanici_mapping = {
            "admin": "Cafer Umut Özpınar",
            "admin@firma.com": "Cafer",
            "kullanici": "Ahmet Yılmaz",
            "kullanici@firma.com": "Ahmet Yılmaz",
        }
        
        # Mapping'de varsa gerçek adı döndür, yoksa kullanıcı adını döndür
        return kullanici_mapping.get(kullanici_adi, kullanici_adi)
    
    def closeEvent(self, event):
        """Pencere kapatılırken çağrılır."""
        # Eğer giriş başarılı değilse, dialog reject edilecek
        if not self.giris_basarili:
            self.gunluk.info("Giriş penceresi iptal edildi")
            self.reject()
        event.accept()
    
    @staticmethod
    def giris_kontrolu(parent=None) -> Optional[tuple]:
        """
        Statik metod: Giriş penceresini gösterir ve sonucu döndürür.
        
        Args:
            parent: Üst widget
            
        Returns:
            Başarılı ise (kullanici_adi, gercek_ad) tuple'ı, iptal ise None
        """
        pencere = GirisPenceresi(parent)
        
        # Modal dialog olarak göster ve sonucu bekle
        sonuc = pencere.exec_()
        
        # Başarılı giriş kontrolü
        if sonuc == QDialog.Accepted and pencere.giris_basarili:
            return (pencere.kullanici_adi, pencere.gercek_ad)
        
        return None
