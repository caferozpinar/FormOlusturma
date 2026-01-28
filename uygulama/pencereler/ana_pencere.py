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

from PyQt5 import QtWidgets, uic, QtCore
from PyQt5.QtWidgets import QMessageBox, QFileDialog, QTableWidgetItem
from PyQt5.QtCore import QDate, Qt

try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_MEVCUT = True
except ImportError:
    RAPIDFUZZ_MEVCUT = False
    logging.warning("rapidfuzz bulunamadı. Fuzzy arama devre dışı. Kurmak için: pip install rapidfuzz")

from uygulama.sabitler import (
    URUN_COMBOBOX_SAYISI,
    UI_DIZINI,
    VERILER_DIZINI,
)
from uygulama.yardimcilar.donusturucular import guvenli_int_donustur
from uygulama.yardimcilar.dogrulayicilar import tarih_dogrula
# from uygulama.yardimcilar.fuzzy_arama import fuzzy_ara, self._tab3_fuzzy_eslesme
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
        
        # Tab_3 arama sistemi sinyalleri
        self._tab3_sinyalleri_bagla()
    
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
        
        # Tab_2 Kaydet butonu
        kaydet_butonu = getattr(self, "pushButton_kaydet", None)
        if kaydet_butonu is not None:
            kaydet_butonu.clicked.connect(self._tab2_kaydet)
            gunluk.info("Tab_2 'Kaydet' butonu bağlandı")
        
        # Dosya menüsü action'ları
        # Dosyayı Aç -> Kayıttan Yükle
        action_dosyay_ac = getattr(self, "actionDosyay_Ac", None)
        if action_dosyay_ac is not None:
            action_dosyay_ac.triggered.connect(self.kayittan_yukle)
            gunluk.info("'Dosyayı Aç' action'ı bağlandı (kayıttan yükle)")
        
        # Format Düzenle -> Format Ayarları Dialog
        action_format_duzenle = getattr(self, "actionFormat_Duzenle", None)
        if action_format_duzenle is not None:
            action_format_duzenle.triggered.connect(self._format_ayarlari_ac)
            gunluk.info("'Format Düzenle' action'ı bağlandı")
        
        # === OTOMATIK UPPERCASE ===
        uppercase_alanlar = [
            'urun1_kod_line', 'urun2_kod_line', 'urun3_kod_line',
            'urun4_kod_line', 'urun5_kod_line', 'urun6_kod_line',
            'belge_tarih_line', 'belge_projeadi_line', 'belge_projeyeri_line'
        ]
        
        for alan_adi in uppercase_alanlar:
            line_edit = getattr(self, alan_adi, None)
            if line_edit is not None:
                # Lambda ile closure problemini çöz
                line_edit.textChanged.connect(
                    lambda text, widget=line_edit: self._otomatik_buyut(widget, text)
                )
        
        # === OTOMATIK FİYAT FORMATLAMASI (Tab_2) ===
        toplamteklif_line = getattr(self, "toplamteklif_line", None)
        if toplamteklif_line is not None:
            # Validator ekle (sadece rakam, nokta, virgül)
            from uygulama.yardimcilar.turk_para_validator import line_edit_fiyat_validatoru_ekle, line_edit_otomatik_formatla
            
            # Otomatik formatlama ekle
            line_edit_otomatik_formatla(toplamteklif_line, negatif_izin=False)
            gunluk.info("toplamteklif_line'a otomatik fiyat formatlaması eklendi")
    
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
    
    def _otomatik_buyut(self, widget, text: str) -> None:
        """QLineEdit'te metni otomatik Türkçe büyük harfe çevirir."""
        upper_text = self._turkce_upper(text)
        if text != upper_text:
            cursor_pos = widget.cursorPosition()
            widget.blockSignals(True)  # Sonsuz döngüyü önle
            widget.setText(upper_text)
            widget.setCursorPosition(cursor_pos)
            widget.blockSignals(False)


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
    
    def _format_ayarlari_ac(self) -> None:
        """
        Format Ayarları dialogunu açar.
        
        Bu dialog, belge üretiminde kullanılan hardcode formatların
        ayarlarını yönetir.
        """
        try:
            gunluk.info("Format Ayarları dialogu açılıyor...")
            
            # FormatAyarlariDialog'u import et
            from uygulama.pencereler.format_ayarlari_dialog import FormatAyarlariDialog
            
            # Dialog'u oluştur ve göster
            dialog = FormatAyarlariDialog(self)
            dialog.show()
            
            gunluk.info("✓ Format Ayarları dialogu açıldı")
        
        except ImportError as e:
            gunluk.error(f"Format Ayarları modülü import hatası: {e}")
            QMessageBox.critical(
                self,
                "Hata",
                "Format Ayarları penceresi yüklenemedi!\n\n"
                "Lütfen format_ayarlari_dialog.py dosyasının\n"
                "./uygulama/pencereler/ klasöründe olduğundan emin olun.",
                QMessageBox.Ok
            )
        
        except Exception as e:
            gunluk.error(f"Format Ayarları açma hatası: {e}")
            import traceback
            gunluk.error(traceback.format_exc())
            QMessageBox.critical(
                self,
                "Hata",
                f"Format Ayarları penceresi açılamadı:\n{str(e)}",
                QMessageBox.Ok
            )
    
    def _tab2_kaydet(self) -> None:
        """
        Tab_2'deki tüm verileri CSV'ye kaydeder.
        
        Bu metod:
        - Tab_2'deki tüm girdileri toplar
        - Radio button seçimini belirler
        - CSV'ye kaydeder
        - Kullanıcıya başarı/hata mesajı gösterir
        """
        try:
            gunluk.info("Tab_2 kayıt işlemi başlatıldı")
            
            # Tab_2 verilerini topla
            tab2_verileri = {}
            
            # Temel bilgiler
            # Tarih bilgisi (otomatik formatla)
            belge_tarih = getattr(self, "belge_tarih_line", None)
            if belge_tarih is not None:
                from uygulama.yardimcilar.tarih_yardimcilari import tarih_widget_formatla
                
                tarih_ham = belge_tarih.text().strip()
                if tarih_ham:
                    # Otomatik formatla: her format → DD-MM-YYYY
                    tarih_formatli = tarih_widget_formatla(tarih_ham)
                    if tarih_formatli:
                        tab2_verileri["belge_tarih_line"] = tarih_formatli
                        gunluk.info(f"Tarih formatlandı: {tarih_ham} → {tarih_formatli}")
                    else:
                        # Formatlanamadı, orijinali kullan
                        tab2_verileri["belge_tarih_line"] = tarih_ham
                        gunluk.warning(f"Tarih formatlanamadı: {tarih_ham}")
                else:
                    tab2_verileri["belge_tarih_line"] = ""
            
            belge_projeadi = getattr(self, "belge_projeadi_line", None)
            if belge_projeadi is not None:
                tab2_verileri["belge_projeadi_line"] = belge_projeadi.text()
            
            belge_projeyeri = getattr(self, "belge_projeyeri_line", None)
            if belge_projeyeri is not None:
                tab2_verileri["belge_projeyeri_line"] = belge_projeyeri.text()
            
            # Ürün bilgileri (6 ürün)
            for i in range(1, 7):
                # Ürün kodu
                urun_kod = getattr(self, f"urun{i}_kod_line", None)
                if urun_kod is not None:
                    tab2_verileri[f"urun{i}_kod_line"] = urun_kod.text()
                
                # Ürün adet
                urun_adet = getattr(self, f"urun{i}_adet_line", None)
                if urun_adet is not None:
                    tab2_verileri[f"urun{i}_adet_line"] = urun_adet.text()
                
                # Ürün özellik
                urun_ozl = getattr(self, f"urun{i}_ozl_line", None)
                if urun_ozl is not None:
                    tab2_verileri[f"urun{i}_ozl_line"] = urun_ozl.text()
            
            # Toplam teklif
            toplam_teklif = getattr(self, "toplamteklif_line", None)
            if toplam_teklif is not None:
                tab2_verileri["toplamteklif_line"] = toplam_teklif.text()
            
            # Radio button'ları kontrol et
            teklif_radio = getattr(self, "teklif_radio", None)
            kesif_radio = getattr(self, "kesif_radio", None)
            tanim_radio = getattr(self, "tanim_radio", None)
            
            tab2_verileri["teklif_radio"] = teklif_radio.isChecked() if teklif_radio is not None else False
            tab2_verileri["kesif_radio"] = kesif_radio.isChecked() if kesif_radio is not None else False
            tab2_verileri["tanim_radio"] = tanim_radio.isChecked() if tanim_radio is not None else False
            
            # Notlar (textEdit)
            notlar = getattr(self, "notlar_textEdit", None)
            if notlar is not None:
                tab2_verileri["notlar_textEdit"] = notlar.toPlainText()
            
            # === SERİ NUMARASI OLUŞTUR ===
            from uygulama.belge.yardimcilar import seri_numarasi_olustur
            from uygulama.yardimcilar.tarih_yardimcilari import tarih_donustur, bugun
            
            # Tarih formatını dönüştür (herhangi bir format → DDMMYY)
            tarih_text = tab2_verileri.get("belge_tarih_line", "")
            if tarih_text:
                # Yeni yardımcı ile dönüştür
                basarili, tarih_ddmmyy, _ = tarih_donustur(tarih_text, "seri")
                if not basarili:
                    # Formatlanamadıysa bugünü kullan
                    tarih_ddmmyy = bugun("seri")
                    gunluk.warning(f"Tarih dönüştürülemedi, bugün kullanıldı: {tarih_text}")
            else:
                # Tarih yoksa bugünü kullan
                tarih_ddmmyy = bugun("seri")
            
            # Firma ve konum
            firma = tab2_verileri.get("belge_projeadi_line", "PROJE")
            konum = tab2_verileri.get("belge_projeyeri_line", "KONUM")
            
            # Ürün kodlarını topla
            urun_kodlari = []
            for i in range(1, 7):
                urun_kod = tab2_verileri.get(f"urun{i}_kod_line", "").strip()
                if urun_kod:
                    urun_kodlari.append(urun_kod)
            
            # Revizyon (şimdilik R00)
            revizyon = "R00"
            
            # Seri numarasını oluştur
            seri_no = seri_numarasi_olustur(
                tarih=tarih_ddmmyy,
                firma=firma,
                konum=konum,
                urunler=urun_kodlari,
                revizyon=revizyon
            )
            
            # Serial_label'a yaz
            serial_label = getattr(self, "Serial_label", None)
            if serial_label is not None:
                serial_label.setText(seri_no)
                gunluk.info(f"Seri numarası oluşturuldu: {seri_no}")
            
            # Seri numarasını verilere ekle
            tab2_verileri["seri_numarasi"] = seri_no
            # === SERİ NUMARASI BİTİŞ ===
            
            # Veritabanı Kaydedici'yi oluştur
            from uygulama.belge.veritabani_kaydedici import VeritabaniKaydedici
            
            kaydedici = VeritabaniKaydedici()
            
            # Kaydet
            basarili = kaydedici.tab2_kaydi_ekle(tab2_verileri, gunluk)
            
            if basarili:
                QMessageBox.information(
                    self,
                    "Başarılı",
                    "Tab_2 verileri başarıyla veritabanına kaydedildi!",
                    QMessageBox.Ok
                )
                gunluk.info("✓ Tab_2 verileri veritabanına kaydedildi")
            else:
                QMessageBox.warning(
                    self,
                    "Hata",
                    "Tab_2 verileri kaydedilirken bir hata oluştu. Lütfen log dosyasını kontrol edin.",
                    QMessageBox.Ok
                )
                gunluk.error("Tab_2 verileri kaydedilemedi")
        
        except Exception as e:
            gunluk.error(f"Tab_2 kayıt hatası: {e}")
            import traceback
            gunluk.error(f"Detay: {traceback.format_exc()}")
            
            QMessageBox.critical(
                self,
                "Kritik Hata",
                f"Tab_2 kayıt işlemi sırasında beklenmeyen bir hata oluştu:\n{str(e)}",
                QMessageBox.Ok
            )

    # =========================================================================
    # TAB_3 ARAMA VE GÖRÜNTÜLEME SİSTEMİ
    # =========================================================================
    

    # =========================================================================
    # TAB_3 ARAMA VE GÖRÜNTÜLEME - BASİT VERSİYON (HATASIZ)
    # =========================================================================
    
    def _tab3_sinyalleri_bagla(self) -> None:
        """Tab_3 sinyallerini bağlar."""
        try:
            # ARA butonu
            ara_butonu = getattr(self, "pushButton_2", None)
            if ara_butonu is not None:
                ara_butonu.clicked.connect(self._tab3_ara)
                gunluk.info("Tab_3 'ARA' butonu bağlandı")
            
            # Proje Detaylarını Göster butonu
            detay_butonu = getattr(self, "pushButton_3", None)
            if detay_butonu is not None:
                detay_butonu.clicked.connect(self._tab3_detay_goster)
                gunluk.info("Tab_3 'Detay Göster' butonu bağlandı")
            
            # Proje Detay Göster butonu (yeni)
            proje_detay_button = getattr(self, "proje_detay_goster_button", None)
            if proje_detay_button is not None:
                proje_detay_button.clicked.connect(self._tab3_detay_goster)
                gunluk.info("proje_detay_goster_button bağlandı")
            
            # Tablo satır seçimi - OTOMATİK GÖSTERME KAPALI
            # (Sadece seçili satırı işaretle, detay gösterme)
            sonuc_tablosu = getattr(self, "tableWidget", None)
            if sonuc_tablosu is not None:
                # itemSelectionChanged sinyalini BAĞLAMA
                # Artık otomatik gösterme yok
                gunluk.info("Tab_3 tablo seçimi hazır (otomatik gösterme kapalı)")
            
            # === ONAY VE HATIRLATMA BUTONLARI ===
            onaylandi_button = getattr(self, "onaylandi_button", None)
            if onaylandi_button is not None:
                # Tıklandığında sadece renk değiştir
                onaylandi_button.clicked.connect(lambda: self._buton_renk_guncelle(onaylandi_button))
                # Başlangıç rengini ayarla
                self._buton_renk_guncelle(onaylandi_button)
                gunluk.info("onaylandi_button bağlandı")
            
            hatirlat_button = getattr(self, "hatirlat_button", None)
            if hatirlat_button is not None:
                # Tıklandığında sadece renk değiştir
                hatirlat_button.clicked.connect(lambda: self._buton_renk_guncelle(hatirlat_button))
                # Başlangıç rengini ayarla
                self._buton_renk_guncelle(hatirlat_button)
                gunluk.info("hatirlat_button bağlandı")
            
            # === VERİTABANI KAYDET BUTONU ===
            veritabani_kaydet_button = getattr(self, "veritabani_kaydet_button", None)
            if veritabani_kaydet_button is not None:
                veritabani_kaydet_button.clicked.connect(self._tab3_veritabani_kaydet)
                gunluk.info("veritabani_kaydet_button bağlandı")
                gunluk.info("hatirlat_button bağlandı")
        except Exception as e:
            gunluk.error(f"Tab_3 sinyal bağlama hatası: {e}")
    
    def _buton_renk_guncelle(self, buton) -> None:
        """Butonun checked durumuna göre arka plan rengini günceller."""
        try:
            if buton.isChecked():
                # Yeşil arka plan (checked)
                buton.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
            else:
                # Kırmızı arka plan (unchecked)
                buton.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
        except Exception as e:
            gunluk.error(f"Buton renk güncelleme hatası: {e}")
    
    def _tab3_veritabani_kaydet(self) -> None:
        """
        Tab_3'te değiştirilen onay ve hatırlatma durumlarını veritabanına kaydeder.
        """
        try:
            # Seçili belge ID'sini al
            belge_id = self._secili_belge_id_al()
            if not belge_id:
                QMessageBox.warning(
                    self,
                    "Uyarı",
                    "Lütfen önce bir belge seçin!",
                    QMessageBox.Ok
                )
                return
            
            # Buton durumlarını al
            onaylandi_button = getattr(self, "onaylandi_button", None)
            hatirlat_button = getattr(self, "hatirlat_button", None)
            
            # Güncellemeleri hazırla
            guncellemeler = {}
            
            if onaylandi_button is not None:
                yeni_onay = 'Evet' if onaylandi_button.isChecked() else 'Hayır'
                guncellemeler['form_onaylandi'] = yeni_onay
            
            if hatirlat_button is not None:
                yeni_hatirlat = 'Aktif' if hatirlat_button.isChecked() else 'Pasif'
                guncellemeler['hatirlatma_durumu'] = yeni_hatirlat
            
            if not guncellemeler:
                QMessageBox.information(
                    self,
                    "Bilgi",
                    "Kaydedilecek değişiklik yok.",
                    QMessageBox.Ok
                )
                return
            
            # Veritabanını güncelle
            from uygulama.veri.belge_onbellegi import BelgeOnbellegi
            onbellek = BelgeOnbellegi()
            
            basarili = onbellek.belge_guncelle(belge_id, guncellemeler, gunluk)
            
            if basarili:
                QMessageBox.information(
                    self,
                    "Başarılı",
                    f"Değişiklikler kaydedildi!\n\nGüncellenen alanlar:\n" + 
                    "\n".join([f"- {alan}: {deger}" for alan, deger in guncellemeler.items()]),
                    QMessageBox.Ok
                )
                gunluk.info(f"✓ Tab_3 değişiklikler kaydedildi: Belge ID={belge_id}, {guncellemeler}")
            else:
                QMessageBox.critical(
                    self,
                    "Hata",
                    "Değişiklikler kaydedilemedi!\nLütfen log dosyasını kontrol edin.",
                    QMessageBox.Ok
                )
                gunluk.error(f"Tab_3 değişiklikler kaydedilemedi: Belge ID={belge_id}")
        
        except Exception as e:
            gunluk.error(f"Tab_3 veritabanı kaydetme hatası: {e}")
            import traceback
            gunluk.error(traceback.format_exc())
            QMessageBox.critical(
                self,
                "Kritik Hata",
                f"Beklenmeyen bir hata oluştu:\n{str(e)}",
                QMessageBox.Ok
            )
    
    def _secili_belge_id_al(self) -> Optional[int]:
        """Şu anda seçili olan belgenin ID'sini döner."""
        try:
            tablo = getattr(self, "tableWidget", None)
            if tablo is None:
                return None
            
            secili_satirlar = tablo.selectedItems()
            if not secili_satirlar:
                return None
            
            satir = secili_satirlar[0].row()
            
            # İlk kolondaki veriyi al (kayit_id, tablo_adi, kayit)
            item = tablo.item(satir, 0)
            if item is None:
                return None
            
            kayit_data = item.data(QtCore.Qt.UserRole)
            if not kayit_data:
                return None
            
            kayit_id, _, _ = kayit_data
            return kayit_id
        
        except Exception as e:
            gunluk.error(f"Seçili belge ID alma hatası: {e}")
            return None
    
    def _tab3_ara(self) -> None:
        """Veritabanında BASİT arama yapar - HATASIZ."""
        try:
            gunluk.info("Tab_3 arama başlatıldı")
            
            # Arama kutusundan metni al
            arama_kutusu = getattr(self, "lineEdit", None)
            if arama_kutusu is None:
                return
            
            arama_metni = arama_kutusu.text().strip().lower()
            
            # Takvimden tarihi al
            takvim = getattr(self, "calendarWidget", None)
            secili_tarih = None
            if takvim is not None:
                qdate = takvim.selectedDate()
                secili_tarih = qdate.toString("yyyy-MM-dd")
            
            # Veritabanı kaydedici
            from uygulama.belge.veritabani_kaydedici import VeritabaniKaydedici
            kaydedici = VeritabaniKaydedici()
            
            # === YENİ YAPI: Tek tablo, filtreli arama ===
            # Tüm belgeler (UYGULAMA + MANUEL)
            tum_kayitlar = []
            
            try:
                # Tarih filtresi ile ara
                filtreler = {}
                if secili_tarih:
                    filtreler['tarih_baslangic'] = secili_tarih
                filtreler['limit'] = 1000
                
                belgeler = kaydedici.kayit_ara(**filtreler)
                
                # Her belgeyi kaydet (tablo_adi olarak 'belgeler' kullan)
                for belge in belgeler:
                    tum_kayitlar.append((belge, 'belgeler'))
                
                gunluk.debug(f"{len(belgeler)} belge bulundu")
                
            except Exception as e:
                gunluk.error(f"Belge arama hatası: {e}")
                import traceback
                gunluk.error(traceback.format_exc())
            
            # Arama metni varsa filtrele (AKILLI ARAMA)
            if arama_metni:
                # Ayraçlarla kelime ayır: boşluk, nokta, virgül, tire
                import re
                arama_kelimeleri = re.split(r'[\s\.,\-]+', arama_metni.strip())
                arama_kelimeleri = [k.lower() for k in arama_kelimeleri if k]  # Boş olanları çıkar
                
                if arama_kelimeleri:
                    gunluk.info(f"Arama kelimeleri: {arama_kelimeleri}")
                    
                    filtrelenmis = []
                    for kayit, tablo_adi in tum_kayitlar:
                        # TÜM kelimeleri içermeli (AND mantığı)
                        tum_kelimeler_bulundu = True
                        
                        for kelime in arama_kelimeleri:
                            # Bu kelime kaydın herhangi bir alanında var mı?
                            kelime_bulundu = False
                            
                            for alan, deger in kayit.items():
                                if deger and kelime in str(deger).lower():
                                    kelime_bulundu = True
                                    break
                            
                            if not kelime_bulundu:
                                # Bu kelime bulunamadı, kayıt eşleşmiyor
                                tum_kelimeler_bulundu = False
                                break
                        
                        if tum_kelimeler_bulundu:
                            filtrelenmis.append((kayit, tablo_adi))
                    
                    tum_kayitlar = filtrelenmis
                    gunluk.info(f"Filtreleme sonrası: {len(tum_kayitlar)} sonuç")
            
            # Tabloya doldur
            self._tab3_sonuclari_tabloya_doldur(tum_kayitlar)
            
            gunluk.info(f"✓ Tab_3 arama tamamlandı: {len(tum_kayitlar)} sonuç")
            
        except Exception as e:
            gunluk.error(f"Tab_3 arama hatası: {e}")
            import traceback
            gunluk.error(f"Detay: {traceback.format_exc()}")
    
    def _tab3_sonuclari_tabloya_doldur(self, sonuclar: list) -> None:
        """Arama sonuçlarını tabloya doldurur."""
        try:
            tablo = getattr(self, "tableWidget", None)
            if tablo is None:
                return
            
            # Tabloyu temizle
            tablo.setRowCount(0)
            
            # Satırları ekle
            for idx, (kayit, tablo_adi) in enumerate(sonuclar):
                tablo.insertRow(idx)
                
                # Tarih
                tarih = kayit.get('tarih', '') or kayit.get('belge_tarih', '')
                tablo.setItem(idx, 0, QTableWidgetItem(str(tarih)))
                
                # Proje Yeri
                proje_yeri = kayit.get('proje_konum', '') or kayit.get('proje_yeri', '')
                tablo.setItem(idx, 1, QTableWidgetItem(str(proje_yeri)))
                
                # Proje Adı
                proje_adi = kayit.get('proje_adi', '')
                tablo.setItem(idx, 2, QTableWidgetItem(str(proje_adi)))
                
                # Gizli veri sakla
                tablo.item(idx, 0).setData(Qt.UserRole, (kayit.get('id'), tablo_adi, kayit))
            
            tablo.resizeColumnsToContents()
            
        except Exception as e:
            gunluk.error(f"Tablo doldurma hatası: {e}")
    
    # _tab3_satir_secildi metodu kaldırıldı - artık otomatik gösterme yok
    # Detay göstermek için proje_detay_goster_button kullanılıyor
    
    def _tab3_detay_goster(self) -> None:
        """
        Detay göster butonu - Seçili belgeyi veritabanından çeker ve gösterir.
        """
        try:
            # Seçili belge ID'sini al
            belge_id = self._secili_belge_id_al()
            
            if not belge_id:
                QMessageBox.warning(
                    self,
                    "Uyarı",
                    "Lütfen önce tabloda bir belge seçin!",
                    QMessageBox.Ok
                )
                return
            
            # Veritabanından belgeyi çek (FRESH DATA)
            from uygulama.veri.belge_onbellegi import BelgeOnbellegi
            onbellek = BelgeOnbellegi()
            
            # Belgeyi ID ile ara
            belgeler = onbellek.belge_ara(limit=1)
            
            # SQL'de ID ile direkt arama yapalım
            import sqlite3
            with sqlite3.connect(str(onbellek.veritabani_yolu)) as baglanti:
                baglanti.row_factory = sqlite3.Row
                imlec = baglanti.cursor()
                imlec.execute("SELECT * FROM belgeler WHERE id = ?", (belge_id,))
                satir = imlec.fetchone()
                
                if satir:
                    kayit = dict(satir)
                    self._tab3_detaylari_goster(kayit, 'belgeler')
                    gunluk.info(f"✓ Belge detayı veritabanından yüklendi: ID={belge_id}")
                else:
                    QMessageBox.warning(
                        self,
                        "Hata",
                        f"Belge bulunamadı! (ID: {belge_id})",
                        QMessageBox.Ok
                    )
                    gunluk.error(f"Belge bulunamadı: ID={belge_id}")
        
        except Exception as e:
            gunluk.error(f"Detay göster hatası: {e}")
            import traceback
            gunluk.error(traceback.format_exc())
            QMessageBox.critical(
                self,
                "Hata",
                f"Detay gösterilirken hata oluştu:\n{str(e)}",
                QMessageBox.Ok
            )
    
    
    def _tab3_detaylari_goster(self, kayit: dict, tablo_adi: str) -> None:
        """Detayları sağ panelde gösterir."""
        try:
            # Temel bilgiler
            self._tab3_label_ayarla("proje_adi_label", kayit.get('proje_adi', ''))
            self._tab3_label_ayarla("proje_yeri_label", kayit.get('proje_konum', ''))
            self._tab3_label_ayarla("revizyon_label", kayit.get('revizyon_numarasi', ''))
            self._tab3_label_ayarla("tarih_label", kayit.get('tarih', ''))
            self._tab3_label_ayarla("serinumara_label", kayit.get('seri_numarasi', ''))
            self._tab3_label_ayarla("dosyayolu_label", kayit.get('dosya_yolu', ''))
            self._tab3_label_ayarla("duzenleyen_isim_label", kayit.get('olusturan_kisi', ''))
            self._tab3_label_ayarla("notes_label", kayit.get('notlar', ''))
            self._tab3_label_ayarla("label_102", kayit.get('kdvli_toplam_fiyat', ''))
            
            # Toplam fiyat label'ı (yeni)
            kdvli_toplam = kayit.get('kdvli_toplam_fiyat', '').strip()
            if kdvli_toplam and kdvli_toplam != '0,00' and kdvli_toplam != '0':
                self._tab3_label_ayarla("toplam_fiyat_label", kdvli_toplam)
            else:
                self._tab3_label_ayarla("toplam_fiyat_label", "Fiyat bilgisi yok")
            
            # Onay durumu butonları
            onay_butonu = getattr(self, "onaylandi_button", None)
            if onay_butonu is not None:
                onay_butonu.setChecked(kayit.get('form_onaylandi', 'Hayır') == 'Evet')
                self._buton_renk_guncelle(onay_butonu)
            
            hatirlat_butonu = getattr(self, "hatirlat_button", None)
            if hatirlat_butonu is not None:
                hatirlat_butonu.setChecked(kayit.get('hatirlatma_durumu', 'Pasif') == 'Aktif')
                self._buton_renk_guncelle(hatirlat_butonu)
            
            # === ÜRÜN BİLGİLERİNİ GÖSTER ===
            # Yeni yapı: belge_urunler tablosundan çek
            belge_id = kayit.get('id')
            if belge_id:
                try:
                    from uygulama.belge.veritabani_kaydedici import VeritabaniKaydedici
                    kaydedici = VeritabaniKaydedici()
                    
                    # Ürünleri getir
                    urunler = kaydedici.onbellek.belge_urunlerini_getir(belge_id)
                    
                    # İlk 6 ürünü göster (UI'da 6 ürün alanı var)
                    for i in range(6):
                        if i < len(urunler):
                            urun = urunler[i]
                            self._tab3_label_ayarla(f"urun_kod_label_{i}", urun.get('urun_kodu', ''))
                            self._tab3_label_ayarla(f"urun_adet_label_{i}", urun.get('urun_adet', ''))
                            self._tab3_label_ayarla(f"urun_ozl_label_{i}", urun.get('urun_ozellik', ''))
                        else:
                            # Boş göster
                            self._tab3_label_ayarla(f"urun_kod_label_{i}", "")
                            self._tab3_label_ayarla(f"urun_adet_label_{i}", "")
                            self._tab3_label_ayarla(f"urun_ozl_label_{i}", "")
                    
                    gunluk.debug(f"✓ {len(urunler)} ürün gösterildi")
                    
                except Exception as e:
                    gunluk.error(f"Ürün getirme hatası: {e}")
            
            # === ÜRÜN ALT BİLGİLERİNİ DOLDUR (5x6 tablo) ===
            # Şimdilik boş bırak - gelecekte kullanılabilir
            for satir in range(1, 6):
                for sutun in range(0, 6):
                    self._tab3_label_ayarla(f"urun_alt_isim_{satir}_{sutun}", "")
                    self._tab3_label_ayarla(f"urun_alt_adet_{satir}_{sutun}", "")
                    self._tab3_label_ayarla(f"urun_alt_fiyat_{satir}_{sutun}", "")
            
        except Exception as e:
            gunluk.error(f"Detay gösterme hatası: {e}")
            import traceback
            gunluk.error(traceback.format_exc())
    
    def _tab3_label_ayarla(self, label_adi: str, metin: str) -> None:
        """Label metnini güvenli ayarlar."""
        try:
            label = getattr(self, label_adi, None)
            if label is not None:
                label.setText(str(metin) if metin else "")
        except:
            pass
    
    def _tab3_detaylari_temizle(self) -> None:
        """Detay panelini temizler."""
        try:
            self._tab3_label_ayarla("proje_adi_label", "Proje Adı")
            self._tab3_label_ayarla("proje_yeri_label", "Proje konumu")
            self._tab3_label_ayarla("revizyon_label", "Revizyon")
            self._tab3_label_ayarla("tarih_label", "Tarih")
            self._tab3_label_ayarla("serinumara_label", "Seri Numarası")
            self._tab3_label_ayarla("dosyayolu_label", "Dosya yolu")
            self._tab3_label_ayarla("duzenleyen_isim_label", "Düzenleyen")
            self._tab3_label_ayarla("notes_label", "")
            self._tab3_label_ayarla("label_102", "Fiyat Teklif Miktarı")
            
            for i in range(6):
                self._tab3_label_ayarla(f"urun_kod_label_{i}", "")
                self._tab3_label_ayarla(f"urun_adet_label_{i}", "")
                self._tab3_label_ayarla(f"urun_ozl_label_{i}", "")
        except:
            pass
