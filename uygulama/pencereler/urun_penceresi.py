"""
Ürün Penceresi Modülü
=====================

Ürün detay formu penceresi.

Bu modül, dinamik olarak .ui dosyasından yüklenen
ve ürüne özel form alanlarını yöneten pencere sınıfını içerir.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from PyQt5 import QtWidgets, uic
from PyQt5.QtGui import QIntValidator

from uygulama.sabitler import MAKSIMUM_FIYAT_SATIRI
from uygulama.yardimcilar.hesaplamalar import (
    satir_toplami_hesapla,
    kdvli_toplam_hesapla,
    ebat_metni_olustur,
    ic_ebat_hesapla,
)
from uygulama.yardimcilar.widget_islemleri import (
    tum_widget_verilerini_topla,
    widget_verilerini_geri_yukle,
)
from uygulama.yardimcilar.fiyat_formatlayici import FiyatFormatlayici
from uygulama.yardimcilar.turk_para_validator import line_edit_otomatik_formatla

# Modül günlükleyicisi
gunluk = logging.getLogger(__name__)


class UrunPenceresi(QtWidgets.QMainWindow):
    """
    Ürün detay formu penceresi.

    Dinamik olarak .ui dosyasından yüklenir ve ürüne özel
    form alanlarını yönetir.

    Özellikler:
    -----------
    - Oturum verilerinden geri yükleme
    - Otomatik hesaplamalar (toplam, KDV, ebat)
    - ComboBox -> LineEdit senkronizasyonu
    - Otomatik Türk para formatı (xxx.xxx.xxx,xx)

    Parametreler:
    -------------
    ui_yolu : str
        .ui dosyasının yolu
    ui_adi : str
        Form tanımlayıcısı (önbellek anahtarı)
    yukler : dict
        Ana pencereden gelen başlangıç verileri
    oturum_ref : OturumYoneticisi
        Oturum yöneticisi referansı
    """

    def __init__(
        self,
        ui_yolu: str,
        ui_adi: str,
        yukler: dict[str, Any],
        oturum_ref: Any  # OturumYoneticisi - döngüsel import'u önlemek için Any
    ):
        super().__init__()

        self.ui_adi = ui_adi
        self.oturum = oturum_ref

        # UI yükle
        uic.loadUi(ui_yolu, self)
        gunluk.info(f"Ürün penceresi yüklendi: {ui_adi}")

        # Fiyat alanlarına validator ekle
        self._fiyat_validatorlerini_ekle()

        # Önceki oturum verilerini geri yükle
        self._oturumdan_geri_yukle()

        # Buton bağlantıları
        self._butonlari_bagla()

        # Sinyal bağlantıları
        self._sinyalleri_bagla()

        # Başlangıç verilerini doldur
        self._baslangic_verilerini_doldur(yukler)

    def _fiyat_validatorlerini_ekle(self) -> None:
        """
        Fiyat alanlarına Türk para formatı validator'ı ekler.

        Bu fonksiyon tüm fiyat ile ilgili QLineEdit'lere:
        - Otomatik formatlama (odak kaybında)
        - Girdi doğrulama (sadece rakam, virgül, nokta)
        - Türk formatına çevirme (xxx.xxx.xxx,xx)
        ekler.
        
        ÖNEMLİ: Maksimum 8 satır desteklenir.
        """
        # Birim fiyat ve toplam alanları (8 satır)
        fiyat_alanlari = []
        for i in range(1, 9):  # 1'den 8'e kadar (dahil)
            fiyat_alanlari.extend([
                f"brmfiyat_line_{i}",  # Birim fiyat
                f"top_line_{i}",       # Satır toplamı
            ])

        # KDV alanları
        fiyat_alanlari.extend(["kdv_line", "topkdv_line"])

        # Her alana validator ekle
        for alan_adi in fiyat_alanlari:
            widget = getattr(self, alan_adi, None)
            if widget is not None and isinstance(widget, QtWidgets.QLineEdit):
                # KDV oranı için özel işlem (% olabilir)
                if alan_adi == "kdv_line":
                    # KDV oranı 0-100 arası olmalı
                    line_edit_otomatik_formatla(
                        widget,
                        negatif_izin=False,
                        maksimum_deger=100.0
                    )
                else:
                    # Normal fiyat alanları
                    line_edit_otomatik_formatla(
                        widget,
                        negatif_izin=False,
                        maksimum_deger=999999999.99
                    )

                gunluk.debug(f"Fiyat validator'ı eklendi: {alan_adi}")

    def _butonlari_bagla(self) -> None:
        """Kaydet ve İptal butonlarını bağlar."""
        kaydet_butonu = getattr(self, "kaydet_but", None)
        if kaydet_butonu is not None:
            kaydet_butonu.clicked.connect(self._oturuma_kaydet)

        iptal_butonu = getattr(self, "iptal_but", None)
        if iptal_butonu is not None:
            iptal_butonu.clicked.connect(self.close)

    def _sinyalleri_bagla(self) -> None:
        """Form alanları arasındaki sinyalleri bağlar."""
        # Kasa ölçü senkronizasyonu
        for alan_adi in ("kapaken_line", "kapakboy_line"):
            widget = getattr(self, alan_adi, None)
            if widget is not None:
                widget.textChanged.connect(self._kasa_olcusunu_guncelle)

        # Satır toplam hesaplamaları (8 satır)
        fiyat_alanlari = []
        for i in range(1, 9):  # 1'den 8'e kadar (dahil)
            fiyat_alanlari.extend([f"adet_line_{i}", f"brmfiyat_line_{i}"])
        fiyat_alanlari.append("kdv_line")

        for alan_adi in fiyat_alanlari:
            widget = getattr(self, alan_adi, None)
            if widget is not None:
                widget.textChanged.connect(self._satirlari_hesapla)

        # Opsiyonel checkbox'lar (8 satır)
        # Checkbox değiştiğinde de toplam yeniden hesaplanmalı
        for i in range(1, 9):  # 1'den 8'e kadar (dahil)
            checkbox = getattr(self, f"urun_ops_{i}", None)
            if checkbox is not None:
                checkbox.stateChanged.connect(self._satirlari_hesapla)

        # ComboBox -> LineEdit senkronizasyonu
        combo_esleme = {
            "kasa_yuks_box": "kasayks_line",
            "motor_cins_box": "motorcns_line",
            "motor_boy_box": "motoryks_line",
        }

        for combo_adi, line_adi in combo_esleme.items():
            combo = getattr(self, combo_adi, None)
            line = getattr(self, line_adi, None)
            if combo is not None and line is not None:
                # Lambda'da varsayılan argüman kullanarak closure sorununu çöz
                combo.currentTextChanged.connect(
                    lambda metin, hedef=line: hedef.setText(metin)
                )

    def _baslangic_verilerini_doldur(self, yukler: dict[str, Any]) -> None:
        """Ana pencereden gelen başlangıç verilerini doldurur."""
        # Tarih alanları
        tarih_alanlari = [
            ("gun_line", "gun", QIntValidator(1, 31, self)),
            ("ay_line", "ay", QIntValidator(1, 12, self)),
            ("yil_line", "yil", QIntValidator(1900, 2100, self)),
        ]

        for alan_adi, yuk_anahtari, dogrulayici in tarih_alanlari:
            widget = getattr(self, alan_adi, None)
            if widget is not None:
                widget.setValidator(dogrulayici)
                widget.setText(str(yukler.get(yuk_anahtari, "")))

        # Proje adı
        proje_adi = getattr(self, "projeadi_line", None)
        if proje_adi is not None:
            proje_adi.setText(str(yukler.get("projeadi", "")))

        # Proje yeri
        proje_yeri = getattr(self, "projeyeri_line", None)
        if proje_yeri is not None:
            ulke = yukler.get("country", "")
            il = yukler.get("province", "")
            proje_yeri.setText(f"{ulke} - {il}")

    def _kasa_olcusunu_guncelle(self, _metin: str = "") -> None:
        """Kapak en/boy değiştiğinde kasa ölçülerini günceller."""
        kapak_en = getattr(self, "kapaken_line", None)
        kapak_boy = getattr(self, "kapakboy_line", None)

        if kapak_en is None or kapak_boy is None:
            return

        en_metin = kapak_en.text()
        boy_metin = kapak_boy.text()

        # Dış ölçü
        kasa_olcu = getattr(self, "kasaolc_line", None)
        if kasa_olcu is not None:
            ebat = ebat_metni_olustur(en_metin, boy_metin)
            kasa_olcu.setText(ebat)

        # İç ölçü
        kasa_ic_olcu = getattr(self, "kasaicolc_line", None)
        if kasa_ic_olcu is not None:
            ic_ebat = ic_ebat_hesapla(en_metin, boy_metin)
            kasa_ic_olcu.setText(ic_ebat)

    def _satirlari_hesapla(self, _metin: str = "") -> None:
        """
        Tüm satır toplamlarını ve KDV'li genel toplamı hesaplar.
        
        ÖNEMLİ: 
        - Maksimum 8 satır desteklenir
        - urun_ops_X checkbox'ı işaretliyse satır genel toplama dahil edilmez
        - Bu fonksiyon FiyatFormatlayici kullanarak tüm fiyatları standart formatta işler.
        """
        ara_toplam = 0.0

        # Her satır için toplam hesapla (8 satıra kadar)
        for i in range(1, 9):  # 1'den 8'e kadar (dahil)
            adet_widget = getattr(self, f"adet_line_{i}", None)
            fiyat_widget = getattr(self, f"brmfiyat_line_{i}", None)
            toplam_widget = getattr(self, f"top_line_{i}", None)
            opsiyonel_checkbox = getattr(self, f"urun_ops_{i}", None)

            if adet_widget is None or fiyat_widget is None:
                continue

            # Adet ve fiyatı float'a çevir
            adet_str = adet_widget.text().strip()
            fiyat_str = fiyat_widget.text().strip()

            if not adet_str or not fiyat_str:
                if toplam_widget is not None:
                    toplam_widget.setText("")
                continue

            # Türk formatından float'a çevir
            try:
                adet = FiyatFormatlayici.turk_format_to_float(adet_str)
                fiyat = FiyatFormatlayici.turk_format_to_float(fiyat_str)
                satir_toplam = adet * fiyat

                # Satır toplamını Türk formatında göster
                if toplam_widget is not None:
                    toplam_formatli = FiyatFormatlayici.float_to_turk_format(satir_toplam)
                    toplam_widget.setText(toplam_formatli)

                # Opsiyonel checkbox kontrolü
                # Eğer checkbox işaretli DEĞİLSE genel toplama ekle
                if opsiyonel_checkbox is not None:
                    if not opsiyonel_checkbox.isChecked():
                        ara_toplam += satir_toplam
                    else:
                        gunluk.debug(f"Satır {i} opsiyonel, genel toplama dahil edilmedi")
                else:
                    # Checkbox yoksa (eski formlar için), toplama ekle
                    ara_toplam += satir_toplam

            except Exception as e:
                gunluk.warning(f"Satır {i} hesaplama hatası: {e}")
                if toplam_widget is not None:
                    toplam_widget.setText("")

        # KDV'li toplam hesapla
        kdv_widget = getattr(self, "kdv_line", None)
        toplam_kdv_widget = getattr(self, "topkdv_line", None)

        if kdv_widget is not None and toplam_kdv_widget is not None and ara_toplam > 0:
            kdv_str = kdv_widget.text().strip()

            if kdv_str:
                try:
                    # KDV oranını al (% işareti varsa kaldır)
                    kdv_orani = FiyatFormatlayici.turk_format_to_float(
                        kdv_str.replace('%', '')
                    )

                    # KDV tutarını hesapla
                    kdv_tutari = ara_toplam * (kdv_orani / 100.0)
                    genel_toplam = ara_toplam + kdv_tutari

                    # Türk formatında göster
                    genel_toplam_formatli = FiyatFormatlayici.float_to_turk_format(
                        genel_toplam
                    )
                    toplam_kdv_widget.setText(genel_toplam_formatli)

                except Exception as e:
                    gunluk.warning(f"KDV hesaplama hatası: {e}")
                    toplam_kdv_widget.setText("")
            else:
                # KDV oranı girilmemişse sadece ara toplamı göster
                ara_toplam_formatli = FiyatFormatlayici.float_to_turk_format(ara_toplam)
                toplam_kdv_widget.setText(ara_toplam_formatli)
        elif toplam_kdv_widget is not None and ara_toplam > 0:
            # KDV widget'ı yoksa sadece ara toplamı göster
            ara_toplam_formatli = FiyatFormatlayici.float_to_turk_format(ara_toplam)
            toplam_kdv_widget.setText(ara_toplam_formatli)

    def _oturuma_kaydet(self) -> None:
        """
        Form verilerini oturuma kaydeder ve pencereyi kapatır.

        ÖNEMLİ: Kaydedilmeden önce tüm fiyat alanları normalize edilir.
        """
        # Tüm widget verilerini topla
        veri = tum_widget_verilerini_topla(self)

        # Fiyat alanlarını normalize et (8 satır)
        fiyat_alanlari = []
        for i in range(1, 9):  # 1'den 8'e kadar (dahil)
            fiyat_alanlari.extend([
                f"brmfiyat_line_{i}",
                f"top_line_{i}",
            ])
        fiyat_alanlari.extend(["kdv_line", "topkdv_line"])

        for alan_adi in fiyat_alanlari:
            if alan_adi in veri and veri[alan_adi]:
                try:
                    # String'i float'a, sonra tekrar Türk formatına çevir
                    deger_float = FiyatFormatlayici.turk_format_to_float(
                        str(veri[alan_adi])
                    )
                    veri[alan_adi] = FiyatFormatlayici.float_to_turk_format(
                        deger_float
                    )
                except Exception as e:
                    gunluk.warning(
                        f"Alan normalize edilemedi {alan_adi}: {e}"
                    )

        # Oturuma kaydet
        self.oturum.form_verisini_kaydet(self.ui_adi, veri)
        gunluk.info(f"Form kaydedildi: {self.ui_adi}")
        self.close()

    def _oturumdan_geri_yukle(self) -> None:
        """Önceki oturum verilerini geri yükler."""
        veri = self.oturum.form_verisini_al(self.ui_adi)
        if veri:
            widget_verilerini_geri_yukle(self, veri)
            gunluk.debug(f"Oturum verileri geri yüklendi: {self.ui_adi}")
