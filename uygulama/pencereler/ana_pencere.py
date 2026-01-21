"""
Ana Pencere Modülü
==================

Uygulamanın ana penceresi.

Bu modül, ürün seçimi, standart girdilerin toplanması
ve belge oluşturma işlemlerini yöneten ana pencere sınıfını içerir.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Optional

from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QMessageBox, QFileDialog
from PyQt5.QtCore import QDate, Qt

from uygulama.sabitler import (
    URUN_COMBOBOX_SAYISI,
    UI_DIZINI,
    VERILER_DIZINI,
)
from uygulama.yardimcilar.donusturucular import guvenli_int_donustur
from uygulama.yardimcilar.dogrulayicilar import tarih_dogrula
from uygulama.veri.csv_yukleyici import (
    ulkeler_combobox_yukle,
    iller_combobox_yukle,
)
from uygulama.pencereler.urun_penceresi import UrunPenceresi
from uygulama.belge.belge_veri_yoneticisi import BelgeVeriYoneticisi

# Modül günlükleyicisi
gunluk = logging.getLogger(__name__)


class AnaPencere(QtWidgets.QMainWindow):
    """
    Uygulamanın ana penceresi.
    
    Sorumluluklar:
    - Ürün seçimi ve alt form yönetimi
    - Standart girdilerin toplanması
    - Belge oluşturma tetikleme
    
    Parametreler:
    -------------
    oturum_ref : OturumYoneticisi
        Oturum yöneticisi referansı
    yapilandirma_ref : YapilandirmaYoneticisi
        Yapılandırma yöneticisi referansı
    """
    
    def __init__(
        self,
        oturum_ref: Any,  # OturumYoneticisi
        yapilandirma_ref: Any  # YapilandirmaYoneticisi
    ):
        super().__init__()
        
        self.oturum = oturum_ref
        self.yapilandirma = yapilandirma_ref
        self.urun_penceresi: Optional[UrunPenceresi] = None
        
        # UI yükle
        ui_yolu = self.yapilandirma.yol_al("ANA_UI")
        if ui_yolu is None:
            ui_yolu = UI_DIZINI / "FormOlusturmaApp.ui"
        
        uic.loadUi(str(ui_yolu), self)
        gunluk.info(f"Ana pencere yüklendi: {ui_yolu}")
        
        # Başlatma
        self._comboboxlari_doldur()
        self._ulkeleri_yukle()
        self._bugunu_ayarla()
        self._sinyalleri_bagla()
        
        # ÖNEMLİ: Kullanıcı adını ayarla (UI yüklendikten SONRA!)
        self._kullanici_adini_ayarla()
    
    def _comboboxlari_doldur(self) -> None:
        """Ürün ComboBox'larını doldurur."""
        from uygulama.veri.urun_yukleyici import urun_listesi_al
        
        urun_listesi = urun_listesi_al()
        urun_listesi = [""] + urun_listesi  # Boş seçim ekle
        
        for i in range(1, URUN_COMBOBOX_SAYISI + 1):
            combo = getattr(self, f"comboBox_{i}", None)
            if combo is not None:
                combo.clear()
                combo.addItems(urun_listesi)
    
    def _ulkeleri_yukle(self) -> None:
        """Ülke ComboBox'ını doldurur."""
        combo = getattr(self, "country_box", None)
        if combo is None:
            gunluk.warning("country_box widget'ı bulunamadı")
            return
        
        csv_yolu = VERILER_DIZINI / "Countries.csv"
        
        if not csv_yolu.exists():
            gunluk.error(f"Ülkeler dosyası bulunamadı: {csv_yolu}")
            QMessageBox.critical(
                self,
                "Hata",
                f"Ülkeler dosyası bulunamadı:\n{csv_yolu}"
            )
            return
        
        basarili = ulkeler_combobox_yukle(combo, csv_yolu)
        if not basarili:
            gunluk.error("Ülkeler yüklenemedi")
    
    def _illeri_yukle(self, _index: int = 0) -> None:
        """Seçili ülkeye göre illeri yükler."""
        country_box = getattr(self, "country_box", None)
        province_box = getattr(self, "province_box", None)
        
        if country_box is None or province_box is None:
            return
        
        province_box.clear()
        
        secili_metin = country_box.currentText().strip()
        if secili_metin is None or not secili_metin:
            return
        
        # "TR - Türkiye" -> "TR"
        if "-" in secili_metin:
            iso2 = secili_metin.split("-", 1)[0].strip()
        else:
            iso2 = secili_metin
        
        csv_yolu = VERILER_DIZINI / f"{iso2}_provinces.csv"
        
        if not csv_yolu.exists():
            gunluk.warning(f"İller dosyası bulunamadı: {csv_yolu}")
            return
        
        iller_combobox_yukle(province_box, csv_yolu)
    
    def _bugunu_ayarla(self) -> None:
        """Tarih alanlarını bugünün tarihi ile doldurur."""
        bugun = date.today()
        
        gun_widget = getattr(self, "gun_line", None)
        ay_widget = getattr(self, "ay_line", None)
        yil_widget = getattr(self, "yil_line", None)
        
        if gun_widget is not None:
            gun_widget.setText(f"{bugun.day:02d}")
        if ay_widget is not None:
            ay_widget.setText(f"{bugun.month:02d}")
        if yil_widget is not None:
            yil_widget.setText(str(bugun.year))
    
    def _kullanici_adini_ayarla(self) -> None:
        """
        Oturumdan kullanıcının gerçek adını alır ve name_label'ı günceller.
        
        Giriş ekranında belirlenen kullanıcı adı (mapping sonrası) 
        ana penceredeki name_label widget'ına yazılır.
        """
        try:
            # Oturumdan gerçek adı al
            gercek_ad = getattr(self.oturum, 'gercek_ad', None)
            
            if gercek_ad is None:
                # Fallback: kullanici_adi varsa onu kullan
                gercek_ad = getattr(self.oturum, 'kullanici_adi', 'Kullanıcı')
            
            # name_label widget'ını bul ve güncelle
            name_label = getattr(self, 'name_label', None)
            
            if name_label is not None:
                name_label.setText(gercek_ad)
                gunluk.info(f"name_label güncellendi: {gercek_ad}")
            else:
                gunluk.warning("name_label widget'ı bulunamadı")
        
        except Exception as e:
            gunluk.error(f"Kullanıcı adı ayarlama hatası: {e}")
            # Hata olsa bile devam et, uygulama çalışmaya devam etsin
    
    def _sinyalleri_bagla(self) -> None:
        """Tüm UI sinyallerini bağlar."""
        projeadi_line = getattr(self, "projeadi_line", None)
        if projeadi_line is not None:
            projeadi_line.textChanged.connect(self._string_buyut)
        # Ülke değişikliği -> İlleri güncelle
        country_box = getattr(self, "country_box", None)
        if country_box is not None:
            country_box.currentIndexChanged.connect(self._illeri_yukle)
        
        # Keşif özeti oluştur butonu
        kesif_butonu = getattr(self, "kesifols_but", None)
        if kesif_butonu is not None:
            kesif_butonu.clicked.connect(self._kesif_ozeti_olustur)
        
        # Fiyat teklifi oluştur butonu
        fiyat_butonu = getattr(self, "fiyatols_but", None)
        if fiyat_butonu is not None:
            fiyat_butonu.clicked.connect(self._fiyat_teklifi_olustur)
        
        # Ürün detay butonları (döngü ile)
        for i in range(1, URUN_COMBOBOX_SAYISI + 1):
            buton = getattr(self, f"cbpushButton_{i}", None)
            combo = getattr(self, f"comboBox_{i}", None)
            
            if buton is not None and combo is not None:
                # Lambda'da varsayılan argüman kullanarak closure sorununu çöz
                buton.clicked.connect(
                    lambda checked=False, c=combo: self._urun_detay_ac(c)
                )
        
        # Dosya menüsü action'ları
        # Dosyayı Aç -> Kayıttan Yükle
        action_dosyay_ac = getattr(self, "actionDosyay_Ac", None)
        if action_dosyay_ac is not None:
            action_dosyay_ac.triggered.connect(self.kayittan_yukle)
            gunluk.info("'Dosyayı Aç' action'ı bağlandı (kayıttan yükle)")
    
    def _turkce_upper(self, text: str) -> str:
        tr_map = {
            "i": "İ",
            "ı": "I",
            "ğ": "Ğ",
            "ü": "Ü",
            "ş": "Ş",
            "ö": "Ö",
            "ç": "Ç",
        }

        result = []
        for ch in text:
            if ch in tr_map:
                result.append(tr_map[ch])
            else:
                result.append(ch.upper())

        return "".join(result)

    def _string_buyut(self, text: str):
        cursor = self.projeadi_line.cursorPosition()
        upper = self._turkce_upper(text)
        if text != upper:
            self.projeadi_line.blockSignals(True)
            self.projeadi_line.setText(self._turkce_upper(text))
            self.projeadi_line.setCursorPosition(cursor)
            self.projeadi_line.blockSignals(False)


    def _urun_detay_ac(self, combo: QtWidgets.QComboBox) -> None:
        """Seçili ürün için detay penceresini açar."""
        if combo is None:
            return
        
        secili = combo.currentText().strip()
        
        if not secili or secili == "-":
            QMessageBox.warning(self, "Uyarı", "Lütfen ürün seçin.")
            return
        
        ui_yolu = UI_DIZINI / f"{secili}.ui"
        
        if not ui_yolu.exists():
            QMessageBox.warning(
                self,
                "Dosya Bulunamadı",
                f"'{secili}' için form dosyası bulunamadı.\n"
                f"Geliştirici ile iletişime geçin."
            )
            return
        
        # Payload hazırla
        yukler = self._payload_olustur()
        
        # Pencereyi aç
        self.urun_penceresi = UrunPenceresi(
            str(ui_yolu),
            secili,
            yukler,
            self.oturum
        )
        self.urun_penceresi.show()
        self.urun_penceresi.raise_()
        self.urun_penceresi.activateWindow()
    
    def _payload_olustur(self) -> dict[str, Any]:
        """Alt pencereler için payload oluşturur."""
        yukler = {}
        
        # Tarih
        gun_widget = getattr(self, "gun_line", None)
        ay_widget = getattr(self, "ay_line", None)
        yil_widget = getattr(self, "yil_line", None)
        
        yukler["gun"] = gun_widget.text() if gun_widget is not None else ""
        yukler["ay"] = ay_widget.text() if ay_widget is not None else ""
        yukler["yil"] = yil_widget.text() if yil_widget is not None else ""
        
        # Ülke ve il
        country_box = getattr(self, "country_box", None)
        province_box = getattr(self, "province_box", None)
        
        yukler["country"] = country_box.currentData() if country_box is not None else ""
        yukler["province"] = province_box.currentText() if province_box is not None else ""
        
        # Proje adı
        proje_adi = getattr(self, "projeadi_line", None)
        yukler["projeadi"] = proje_adi.text() if proje_adi is not None else ""
        
        return yukler
    
    def _standart_girdileri_topla(self) -> bool:
        """
        Ana formdan standart girdileri toplar ve doğrular.
        
        Returns:
            Başarılı ise True
        """
        # Tarih doğrulama
        yil_widget = getattr(self, "yil_line", None)
        ay_widget = getattr(self, "ay_line", None)
        gun_widget = getattr(self, "gun_line", None)
        
        if not all([yil_widget, ay_widget, gun_widget]):
            QMessageBox.warning(self, "Uyarı", "Tarih alanları bulunamadı.")
            return False
        
        yil = guvenli_int_donustur(yil_widget.text())
        ay = guvenli_int_donustur(ay_widget.text())
        gun = guvenli_int_donustur(gun_widget.text())
        
        basarili, tarih, hata = tarih_dogrula(yil, ay, gun)
        if not basarili:
            QMessageBox.warning(self, "Geçersiz Tarih", hata)
            return False
        
        # Geçerlilik süresi (gün sayısı olarak kaydet)
        sontrh_widget = getattr(self, "sontrh_line", None)
        if sontrh_widget is not None:
            gun_sayisi = sontrh_widget.text().strip()
            # Gün sayısını olduğu gibi kaydet (tarih hesaplama belge oluştururken yapılacak)
            self.oturum.standart_girdi_guncelle("SONTRH", gun_sayisi)
        
        # Diğer girdiler
        girdi_esleme = {
            "TERMIN": "termin_line",
            "MONTAJ": "montaj_line",
            "GIRDI1": "girdi1_line",
            "GIRDI3": "girdi3_line",
            "GIRDI4": "girdi4_line",
            "GIRDI5": "girdi5_line",
            "GIRDI6": "girdi6_line",
            "GIRDI7": "girdi7_line",
            "GIRDI8": "girdi8_line",
            "PROJEADI": "projeadi_line",
        }
        
        for anahtar, widget_adi in girdi_esleme.items():
            widget = getattr(self, widget_adi, None)
            if widget is not None:
                if hasattr(widget, "text"):
                    self.oturum.standart_girdi_guncelle(anahtar, widget.text())
                elif hasattr(widget, "toPlainText"):
                    self.oturum.standart_girdi_guncelle(anahtar, widget.toPlainText())
        
        # GIRDI2 özel (QTextEdit olabilir)
        girdi2 = getattr(self, "girdi2_line", None)
        if girdi2 is not None:
            if hasattr(girdi2, "toPlainText"):
                self.oturum.standart_girdi_guncelle("GIRDI2", girdi2.toPlainText())
            else:
                self.oturum.standart_girdi_guncelle("GIRDI2", girdi2.text())
        
        # Konum (ULKE ve IL ayrı ayrı + birleşik PROJEKONUM)
        country_box = getattr(self, "country_box", None)
        province_box = getattr(self, "province_box", None)
        
        if country_box is not None and province_box is not None:
            ulke_metni = country_box.currentText()
            if "-" in ulke_metni:
                ulke = ulke_metni.split("-", 1)[1].strip()
            else:
                ulke = ulke_metni
            
            il = province_box.currentText()
            
            # Ayrı ayrı kaydet
            self.oturum.standart_girdi_guncelle("ULKE", ulke)
            self.oturum.standart_girdi_guncelle("IL", il)
            
            # Geriye dönük uyumluluk için birleşik format
            konum = f"{il} / {ulke}"
            self.oturum.standart_girdi_guncelle("PROJEKONUM", konum)
        
        # Düzenleyen
        name_label = getattr(self, "name_label", None)
        if name_label is not None:
            self.oturum.standart_girdi_guncelle("DUZENLEYEN", name_label.text())
        
        # Tarih
        self.oturum.standart_girdi_guncelle("CURDATE", str(tarih))
        
        # Revize yönetimi
        # NOT: Bu fonksiyon hem okuma hem yazma sırasında revize numarasını yönetir.
        # rvz_checkbox işaretli ise: Düzenleme modu (revize artmaz)
        # rvz_checkbox işaretsiz ise: Yeni revizyon (revize +1 artar)
        self._revize_yonet()
        
        gunluk.info("Standart girdiler toplandı")
        return True
    
    def _revize_yonet(self) -> None:
        """
        Revize numarasını yönetir.
        
        Mantık:
        - rvz_checkbox işaretli (Revize): Revize +1 artırılır
        - rvz_checkbox işaretsiz (Düzenle): Mevcut revize korunur
        - İlk belge: R00 atanır
        """
        rvz_line = getattr(self, "rvz_line", None)
        rvz_checkbox = getattr(self, "rvz_checkbox", None)
        
        if rvz_line is None:
            gunluk.warning("rvz_line widget'ı bulunamadı")
            return
        
        mevcut_revize = rvz_line.text().strip()
        
        # İlk belge kontrolü (boş veya geçersiz)
        if not mevcut_revize or not mevcut_revize.startswith('R'):
            yeni_revize = "R00"
            gunluk.info("İlk belge, revize: R00")
        else:
            # Checkbox kontrolü (TERSİNE ÇEVRİLDİ!)
            revize_yap = rvz_checkbox.isChecked() if rvz_checkbox else False
            
            if revize_yap:
                # Yeni revizyon: Revize +1
                try:
                    # "R03" -> 3 -> 4 -> "R04"
                    revize_no = int(mevcut_revize[1:])
                    yeni_revize = f"R{revize_no + 1:02d}"
                    gunluk.info(f"Yeni revizyon: {mevcut_revize} → {yeni_revize}")
                except (ValueError, IndexError) as e:
                    gunluk.warning(f"Revize parse hatası: {mevcut_revize} - {e}")
                    yeni_revize = "R00"
            else:
                # Düzenleme modu: Revize değişmez
                yeni_revize = mevcut_revize
                gunluk.info(f"Düzenleme modu: Revize korundu ({mevcut_revize})")
        
        # Güncelle
        rvz_line.setText(yeni_revize)
        self.oturum.standart_girdi_guncelle("REVIZYON", yeni_revize)
    
    def _secili_urunleri_al(self) -> list[str]:
        """Seçili ürün listesini döndürür."""
        urunler = []
        
        for i in range(1, URUN_COMBOBOX_SAYISI + 1):
            combo = getattr(self, f"comboBox_{i}", None)
            if combo is not None:
                metin = combo.currentText().strip()
                if metin and metin != "-":
                    urunler.append(metin)
        
        return urunler
    
    def _fiyat_teklifi_olustur(self) -> None:
        """Fiyat teklifi belgesi oluşturur."""
        # Standart girdileri topla
        if not self._standart_girdileri_topla():
            return
        
        # Seçili ürünleri al
        urunler = self._secili_urunleri_al()
        
        if not urunler:
            QMessageBox.warning(
                self,
                "Uyarı",
                "Lütfen en az bir ürün seçin."
            )
            return
        
        # Ebatları çıkar
        ebatlar = [self.oturum.urun_ebat_cikar(u) for u in urunler]
        
        # Kod oluştur
        try:
            from uygulama.kodlama import kod_uret
            kod_yukleri = {
                "konum": self.oturum.standart_girdi_al("PROJEKONUM", ""),
                "firma": self.oturum.standart_girdi_al("DUZENLEYEN", ""),
                "rev": "R00",  # TODO: UI'dan al
                "urunler": urunler,
                "ebatlar": ebatlar,
            }
            kod = kod_uret(kod_yukleri)
            gunluk.info(f"Kod oluşturuldu: {kod}")
        except ImportError:
            gunluk.warning("Kodlama modülü bulunamadı")
            kod = "EMPTY"
        
        # Belge oluştur
        try:
            from uygulama.belge import teklif_formu_olustur
            print(self.oturum.form_onbellegi)
            cikti_yolu = teklif_formu_olustur(
                veri_dizini="./kaynaklar",
                cikti_dizini="./ciktilar",
                urun_kodlari=urunler,
                oturum_onbellegi=self.oturum.form_onbellegi,
                standart_girdiler=self.oturum.standart_girdiler,
                kod_degeri=kod,
                config_yolu="./config.txt"
            )
            
            QMessageBox.information(
                self,
                "Başarılı ✓",
                f"Fiyat teklifi oluşturuldu!\n\n"
                f"Dosya: {cikti_yolu.name}\n\n"
                f"Konum: {cikti_yolu.parent}"
            )
            gunluk.info(f"Belge oluşturuldu: {cikti_yolu}")
        
        except FileNotFoundError as e:
            gunluk.error(f"Şablon bulunamadı: {e}")
            QMessageBox.critical(
                self,
                "Dosya Bulunamadı",
                f"Gerekli şablon dosyası bulunamadı:\n\n{e}\n\n"
                f"Lütfen şablon dosyalarını kontrol edin."
            )
        
        except ValueError as e:
            gunluk.warning(f"Geçersiz girdi: {e}")
            QMessageBox.warning(
                self,
                "Geçersiz Giriş",
                f"Geçersiz veri girişi:\n\n{e}"
            )
        
        except ImportError:
            gunluk.error("DocumentGenerator modülü bulunamadı")
            QMessageBox.critical(
                self,
                "Hata",
                "DocumentGenerator modülü bulunamadı.\n"
                "Lütfen modülün mevcut olduğundan emin olun."
            )
        
        except Exception as e:
            gunluk.exception(f"Beklenmeyen hata: {e}")
            QMessageBox.critical(
                self,
                "Hata",
                f"Dosya oluşturulurken beklenmeyen bir hata oluştu:\n\n{e}\n\n"
                f"Detaylar için ./loglar/ klasöründeki log dosyasını kontrol edin."
            )
    
    def _kesif_ozeti_olustur(self) -> None:
        """Keşif özeti belgesi oluşturur (opsiyon işaretleme ve numaralandırma ile)."""
        # Standart girdileri topla
        if not self._standart_girdileri_topla():
            return
        
        # Seçili ürünleri al
        urunler = self._secili_urunleri_al()
        
        if not urunler:
            QMessageBox.warning(
                self,
                "Uyarı",
                "Lütfen en az bir ürün seçin."
            )
            return
        
        # Ebatları çıkar
        ebatlar = [self.oturum.urun_ebat_cikar(u) for u in urunler]
        
        # Kod oluştur
        try:
            from uygulama.kodlama import kod_uret
            kod_yukleri = {
                "konum": self.oturum.standart_girdi_al("PROJEKONUM", ""),
                "firma": self.oturum.standart_girdi_al("DUZENLEYEN", ""),
                "rev": "R01",  # TODO: UI'dan al
                "urunler": urunler,
                "ebatlar": ebatlar,
            }
            kod = kod_uret(kod_yukleri)
            gunluk.info(f"Kod oluşturuldu: {kod}")
        except ImportError:
            gunluk.warning("Kodlama modülü bulunamadı")
            kod = "EMPTY"
        
        # Keşif özeti oluştur
        try:
            from uygulama.belge import kesif_ozeti_olustur
            
            cikti_yolu = kesif_ozeti_olustur(
                veri_dizini="./kaynaklar",
                cikti_dizini="./ciktilar",
                urun_kodlari=urunler,
                oturum_onbellegi=self.oturum.form_onbellegi,
                standart_girdiler=self.oturum.standart_girdiler,
                kod_degeri=kod,
                config_yolu="./config.txt",
                gecici_temizle=True,
                metadata_yaz=True,
                csv_kayit=True,
            )
            
            QMessageBox.information(
                self,
                "Başarılı ✓",
                f"Keşif özeti oluşturuldu!\n\n"
                f"Dosya: {cikti_yolu.name}\n\n"
                f"Konum: {cikti_yolu.parent}"
            )
            gunluk.info(f"Keşif özeti oluşturuldu: {cikti_yolu}")
        
        except FileNotFoundError as e:
            gunluk.error(f"Şablon bulunamadı: {e}")
            QMessageBox.critical(
                self,
                "Dosya Bulunamadı",
                f"Gerekli şablon dosyası bulunamadı:\n\n{e}\n\n"
                f"Lütfen şablon dosyalarını kontrol edin."
            )
        
        except ValueError as e:
            gunluk.warning(f"Geçersiz girdi: {e}")
            QMessageBox.warning(
                self,
                "Geçersiz Giriş",
                f"Geçersiz veri girişi:\n\n{e}"
            )
        
        except ImportError as e:
            gunluk.error(f"İçe aktarma hatası: {e}")
            QMessageBox.critical(
                self,
                "Hata",
                f"Gerekli modül bulunamadı:\n\n{e}\n\n"
                "Lütfen modülün mevcut olduğundan emin olun."
            )
        
        except Exception as e:
            gunluk.exception(f"Beklenmeyen hata: {e}")
            QMessageBox.critical(
                self,
                "Hata",
                f"Keşif özeti oluşturulurken beklenmeyen bir hata oluştu:\n\n{e}\n\n"
                f"Detaylar için ./loglar/ klasöründeki log dosyasını kontrol edin."
            )
    
    def kayittan_yukle(self):
        """
        ZTF dosyasından belge verilerini okuyarak formu doldurur.
        
        İşlem Akışı:
        ------------
        1. Dosya seçme dialogu aç (.docx veya .ztf)
        2. ZTF dosyasından veri oku
        3. Standart girdileri doldur
        4. Ürün kodlarını seç
        5. Oturum önbelleğini yükle
        6. Başarı mesajı göster
        """
        try:
            # Dosya seçme dialogu - hem .docx hem .ztf kabul et
            dosya_yolu, _ = QFileDialog.getOpenFileName(
                self,
                "Kayıttan Yükle - Belge Seç",
                str(Path.home() / "Desktop"),
                "Word Belgeleri (*.docx);;ZTF Dosyaları (*.ztf);;Tüm Dosyalar (*.*)"
            )
            
            if not dosya_yolu:
                # Kullanıcı iptal etti
                return
            
            gunluk.info(f"Kayıttan yükleme başlatıldı: {dosya_yolu}")
            
            # SQLite veritabanından veri okuma
            yonetici = BelgeVeriYoneticisi()
            veriler = yonetici.veri_yukle(dosya_yolu, logger=gunluk)
            
            if not veriler:
                QMessageBox.warning(
                    self,
                    "Veri Bulunamadı",
                    "Seçtiğiniz belge için kayıtlı veri bulunamadı.\n\n"
                    "Bu belge eski sürümle mi oluşturuldu?\n"
                    "Veya veritabanında kayıt olmayabilir."
                )
                return
            
            # Formu doldur
            self._formu_veriler_ile_doldur(veriler)
            
            # Başarı mesajı
            proje_adi = veriler.get('standart_girdiler', {}).get('PROJEADI', 'Bilinmiyor')
            seri_no = veriler.get('seri_numarasi', 'Bilinmiyor')
            urun_sayisi = len(veriler.get('urun_kodlari', []))
            
            QMessageBox.information(
                self,
                "Kayıt Yüklendi ✓",
                f"Form verileri başarıyla yüklendi!\n\n"
                f"📋 Proje: {proje_adi}\n"
                f"🔢 Seri No: {seri_no}\n"
                f"📦 Ürün Sayısı: {urun_sayisi}\n\n"
                f"Şimdi değişiklik yapıp yeni belge oluşturabilirsiniz."
            )
            
            gunluk.info(f"✓ Kayıt yüklendi: {Path(dosya_yolu).name}")
            
        except Exception as e:
            gunluk.error(f"Kayıttan yükleme hatası: {e}")
            import traceback
            gunluk.error(traceback.format_exc())
            
            QMessageBox.critical(
                self,
                "Hata",
                f"Kayıt yüklenirken hata oluştu:\n\n{str(e)}"
            )
    
    def _formu_veriler_ile_doldur(self, veriler: dict):
        """
        ZTF dosyasından okunan verilerle formu doldurur.
        
        Parametreler:
        -------------
        veriler : dict
            ZTF dosyasından okunan veri sözlüğü
        """
        try:
            # 1. STANDART GİRDİLERİ DOLDUR
            standart_girdiler = veriler.get('standart_girdiler', {})
            
            # Proje adı
            if 'PROJEADI' in standart_girdiler:
                projeadi_line = getattr(self, 'projeadi_line', None)
                if projeadi_line is not None:
                    projeadi_line.setText(standart_girdiler['PROJEADI'])
            
            # Ülke ve il (ULKE/IL varsa direkt, yoksa PROJEKONUM'dan parse et)
            ulke_bulundu = False
            il_bulundu = False
            
            if 'ULKE' in standart_girdiler:
                country_box = getattr(self, 'country_box', None)
                if country_box is not None:
                    ulke = standart_girdiler['ULKE']
                    # ComboBox'ta ara
                    index = country_box.findText(ulke, Qt.MatchFlag.MatchContains)
                    if index >= 0:
                        country_box.setCurrentIndex(index)
                        ulke_bulundu = True
            
            if 'IL' in standart_girdiler:
                province_box = getattr(self, 'province_box', None)
                if province_box is not None:
                    il = standart_girdiler['IL']
                    # ComboBox'ta ara
                    index = province_box.findText(il, Qt.MatchFlag.MatchContains)
                    if index >= 0:
                        province_box.setCurrentIndex(index)
                        il_bulundu = True
            
            # Eski format için geriye dönük uyumluluk: PROJEKONUM'dan parse et
            if (not ulke_bulundu or not il_bulundu) and 'PROJEKONUM' in standart_girdiler:
                projekonum = standart_girdiler['PROJEKONUM']
                # "Çankırı / Türkiye" -> ["Çankırı", "Türkiye"]
                if ' / ' in projekonum:
                    parcalar = projekonum.split(' / ')
                    if len(parcalar) == 2:
                        il_eski, ulke_eski = parcalar
                        
                        if not ulke_bulundu:
                            country_box = getattr(self, 'country_box', None)
                            if country_box is not None:
                                index = country_box.findText(ulke_eski, Qt.MatchFlag.MatchContains)
                                if index >= 0:
                                    country_box.setCurrentIndex(index)
                                    gunluk.debug(f"PROJEKONUM'dan parse: Ülke = {ulke_eski}")
                        
                        if not il_bulundu:
                            province_box = getattr(self, 'province_box', None)
                            if province_box is not None:
                                index = province_box.findText(il_eski, Qt.MatchFlag.MatchContains)
                                if index >= 0:
                                    province_box.setCurrentIndex(index)
                                    gunluk.debug(f"PROJEKONUM'dan parse: İl = {il_eski}")
            
            # Tarih (gün, ay, yıl)
            if 'CURDATE' in standart_girdiler:
                tarih_str = standart_girdiler['CURDATE']
                try:
                    # "2025-12-31" veya "31.12.2025" formatını parse et
                    if '-' in tarih_str:
                        # ISO format: 2025-12-31
                        yil, ay, gun = map(int, tarih_str.split('-'))
                    elif '.' in tarih_str:
                        # Türk format: 31.12.2025
                        gun, ay, yil = map(int, tarih_str.split('.'))
                    else:
                        raise ValueError("Geçersiz tarih formatı")
                    
                    gun_line = getattr(self, 'gun_line', None)
                    ay_line = getattr(self, 'ay_line', None)
                    yil_line = getattr(self, 'yil_line', None)
                    
                    if gun_line is not None:
                        gun_line.setText(f"{gun:02d}")
                    if ay_line is not None:
                        ay_line.setText(f"{ay:02d}")
                    if yil_line is not None:
                        yil_line.setText(str(yil))
                        
                except Exception as e:
                    gunluk.warning(f"Tarih parse edilemedi: {tarih_str} - {e}")
            
            # Son tarih, termin, montaj
            if 'SONTRH' in standart_girdiler:
                sontrh_line = getattr(self, 'sontrh_line', None)
                if sontrh_line is not None:
                    sontrh_line.setText(standart_girdiler['SONTRH'])
            
            if 'TERMIN' in standart_girdiler:
                termin_line = getattr(self, 'termin_line', None)
                if termin_line is not None:
                    termin_line.setText(standart_girdiler['TERMIN'])
            
            if 'MONTAJ' in standart_girdiler:
                montaj_line = getattr(self, 'montaj_line', None)
                if montaj_line is not None:
                    montaj_line.setText(standart_girdiler['MONTAJ'])
            
            # Revizyon
            if 'REVIZYON' in standart_girdiler:
                rvz_line = getattr(self, 'rvz_line', None)
                if rvz_line is not None:
                    rvz_line.setText(standart_girdiler['REVIZYON'])
                
                # Checkbox'ı işaretsiz yap (varsayılan: düzenleme modu)
                rvz_checkbox = getattr(self, 'rvz_checkbox', None)
                if rvz_checkbox is not None:
                    rvz_checkbox.setChecked(False)
                    gunluk.debug("Revize checkbox işaretsiz (düzenleme modu)")
            
            gunluk.info(f"Standart girdiler dolduruldu: {len(standart_girdiler)} alan")
            
            # 2. ÜRÜN KODLARINI SEÇ (ComboBox'ları doldur)
            urun_kodlari = veriler.get('urun_kodlari', [])
            
            # ComboBox'ları temizle
            for i in range(1, URUN_COMBOBOX_SAYISI + 1):
                combo = getattr(self, f'comboBox_{i}', None)
                if combo is not None:
                    combo.setCurrentIndex(0)  # Boş seçim
            
            # Seçili ürünleri doldur
            for idx, urun_kodu in enumerate(urun_kodlari):
                if idx < URUN_COMBOBOX_SAYISI:
                    combo = getattr(self, f'comboBox_{idx + 1}', None)
                    if combo is not None:
                        # ComboBox'ta ürün kodunu ara
                        index = combo.findText(urun_kodu)
                        if index >= 0:
                            combo.setCurrentIndex(index)
            
            gunluk.info(f"Ürün seçimleri yapıldı: {', '.join(urun_kodlari)}")
            
            # 3. OTURUM ÖNBELLEĞİNİ YÜKLE
            oturum_onbellegi = veriler.get('oturum_onbellegi', {})
            
            if hasattr(self, 'oturum'):
                self.oturum.form_onbellegi = oturum_onbellegi
                gunluk.info(f"Oturum önbelleği yüklendi: {len(oturum_onbellegi)} ürün")
            
            # 4. STANDART GİRDİLERİ GÜNCELLE
            if hasattr(self, 'oturum'):
                self.oturum.standart_girdiler = standart_girdiler
            
            gunluk.info("✓ Form verilerle tamamen dolduruldu")
            
        except Exception as e:
            gunluk.error(f"Form doldurma hatası: {e}")
            import traceback
            gunluk.error(traceback.format_exc())
            raise
