"""
Türk Para Birimi Validator'ı
==============================

PyQt5 QLineEdit için Türk para formatı doğrulayıcısı.

Bu modül, kullanıcının fiyat girerken canlı olarak formatlanmasını
ve yanlış girişlerin engellenmesini sağlar.

Özellikler:
-----------
- Canlı format düzeltme
- Sadece rakam, virgül ve nokta girişi
- Otomatik binlik ayırıcı ekleme
- Negatif değer desteği (opsiyonel)
"""

from __future__ import annotations

from PyQt5.QtCore import QLocale
from PyQt5.QtGui import QValidator
from PyQt5.QtWidgets import QLineEdit

from uygulama.yardimcilar.fiyat_formatlayici import FiyatFormatlayici


class TurkParaValidator(QValidator):
    """
    Türk para formatı için özel validator.
    
    Kullanım:
    ---------
    >>> line_edit = QLineEdit()
    >>> validator = TurkParaValidator(line_edit)
    >>> line_edit.setValidator(validator)
    
    Kabul Edilen Girdiler:
    ----------------------
    - "1256" → Kabul (sonradan formatlanacak)
    - "1256,8" → Kabul
    - "1.256,80" → Kabul
    - "abc" → Reddedilir
    - "12.34.56" → Reddedilir (çoklu nokta)
    """
    
    def __init__(
        self,
        parent: QLineEdit = None,
        negatif_izin: bool = False,
        maksimum_deger: float = None
    ):
        """
        Validator başlatıcı.
        
        Parametreler:
        -------------
        parent : QLineEdit, optional
            Ana widget
        negatif_izin : bool, optional
            Negatif değerlere izin ver (varsayılan: False)
        maksimum_deger : float, optional
            Maksimum izin verilen değer (varsayılan: None - sınırsız)
        """
        super().__init__(parent)
        self.negatif_izin = negatif_izin
        self.maksimum_deger = maksimum_deger
    
    def validate(self, metin: str, konum: int) -> tuple[QValidator.State, str, int]:
        """
        Girdiyi doğrular.
        
        Parametreler:
        -------------
        metin : str
            Doğrulanacak metin
        konum : int
            İmleç konumu
        
        Döndürür:
        ---------
        tuple[QValidator.State, str, int]
            (Durum, Düzeltilmiş metin, Yeni imleç konumu)
        """
        # Boş girdi kabul edilir (kullanıcı silebilir)
        if not metin:
            return (QValidator.Acceptable, metin, konum)
        
        # Sadece boşluk varsa kabul edilmez
        if metin.strip() == '':
            return (QValidator.Invalid, metin, konum)
        
        # Negatif kontrolü
        if metin.startswith('-'):
            if not self.negatif_izin:
                return (QValidator.Invalid, metin, konum)
            # Negatif işaretinden sonraki kısmı kontrol et
            metin_temiz = metin[1:]
            if not metin_temiz:
                return (QValidator.Intermediate, metin, konum)
        else:
            metin_temiz = metin
        
        # Sadece izin verilen karakterler: rakam, nokta, virgül
        izinli_karakterler = set('0123456789.,')
        if not all(c in izinli_karakterler for c in metin_temiz):
            return (QValidator.Invalid, metin, konum)
        
        # Çoklu virgül kontrolü
        if metin_temiz.count(',') > 1:
            return (QValidator.Invalid, metin, konum)
        
        # Virgülden sonra en fazla 2 basamak
        if ',' in metin_temiz:
            parcalar = metin_temiz.split(',')
            if len(parcalar[1]) > 2:
                return (QValidator.Invalid, metin, konum)
        
        # Maksimum değer kontrolü
        if self.maksimum_deger is not None:
            try:
                deger = FiyatFormatlayici.turk_format_to_float(metin)
                if abs(deger) > self.maksimum_deger:
                    return (QValidator.Invalid, metin, konum)
            except:
                pass  # Henüz tam sayı değilse kontrol etme
        
        # Geçerli bir sayı formatı mı kontrol et
        try:
            FiyatFormatlayici.turk_format_to_float(metin)
            return (QValidator.Acceptable, metin, konum)
        except:
            # Henüz tamamlanmamış olabilir (örn: "1," veya "1.2")
            return (QValidator.Intermediate, metin, konum)
    
    def fixup(self, metin: str) -> str:
        """
        Geçersiz girdiyi düzeltir.
        
        Not: Bu fonksiyon kullanıcı odaktan çıktığında çağrılır.
        
        Parametreler:
        -------------
        metin : str
            Düzeltilecek metin
        
        Döndürür:
        ---------
        str
            Düzeltilmiş metin
        """
        if not metin or not metin.strip():
            return "0,00"
        
        try:
            # Float'a çevir ve tekrar Türk formatına çevir
            deger = FiyatFormatlayici.turk_format_to_float(metin)
            return FiyatFormatlayici.float_to_turk_format(deger)
        except:
            return "0,00"


class OtomatikFormatliLineEdit(QLineEdit):
    """
    Otomatik Türk para formatı uygulayan QLineEdit.
    
    Bu widget, kullanıcı odaktan çıktığında otomatik olarak
    girdiyi Türk para formatına çevirir.
    
    Kullanım:
    ---------
    >>> line_edit = OtomatikFormatliLineEdit()
    >>> line_edit.setText("1256.8")
    >>> # Kullanıcı odaktan çıktığında: "1.256,80"
    """
    
    def __init__(
        self,
        parent=None,
        negatif_izin: bool = False,
        maksimum_deger: float = None
    ):
        """
        Widget başlatıcı.
        
        Parametreler:
        -------------
        parent : QWidget, optional
            Ana widget
        negatif_izin : bool, optional
            Negatif değerlere izin ver
        maksimum_deger : float, optional
            Maksimum izin verilen değer
        """
        super().__init__(parent)
        
        # Validator ekle
        validator = TurkParaValidator(
            self,
            negatif_izin=negatif_izin,
            maksimum_deger=maksimum_deger
        )
        self.setValidator(validator)
        
        # Odak kaybı sinyalini bağla
        self.editingFinished.connect(self._otomatik_formatla)
    
    def _otomatik_formatla(self):
        """Kullanıcı odaktan çıktığında metni formatlar."""
        metin = self.text()
        
        if not metin or not metin.strip():
            self.setText("0,00")
            return
        
        try:
            # Float'a çevir ve Türk formatına çevir
            deger = FiyatFormatlayici.turk_format_to_float(metin)
            formatli = FiyatFormatlayici.float_to_turk_format(deger)
            self.setText(formatli)
        except:
            self.setText("0,00")
    
    def deger(self) -> float:
        """
        Widget'taki değeri float olarak döndürür.
        
        Döndürür:
        ---------
        float
            Widget değeri
        """
        return FiyatFormatlayici.turk_format_to_float(self.text())
    
    def deger_ata(self, deger: float):
        """
        Widget'a float değer atar (otomatik formatlanır).
        
        Parametreler:
        -------------
        deger : float
            Atanacak değer
        """
        formatli = FiyatFormatlayici.float_to_turk_format(deger)
        self.setText(formatli)


def line_edit_fiyat_validatoru_ekle(
    line_edit: QLineEdit,
    negatif_izin: bool = False,
    maksimum_deger: float = None
) -> TurkParaValidator:
    """
    Mevcut bir QLineEdit'e Türk para validator'ı ekler.
    
    Kullanım:
    ---------
    >>> line_edit = QLineEdit()
    >>> validator = line_edit_fiyat_validatoru_ekle(line_edit)
    
    Parametreler:
    -------------
    line_edit : QLineEdit
        Validator eklenecek widget
    negatif_izin : bool, optional
        Negatif değerlere izin ver
    maksimum_deger : float, optional
        Maksimum izin verilen değer
    
    Döndürür:
    ---------
    TurkParaValidator
        Oluşturulan validator
    """
    validator = TurkParaValidator(
        line_edit,
        negatif_izin=negatif_izin,
        maksimum_deger=maksimum_deger
    )
    line_edit.setValidator(validator)
    return validator


def line_edit_otomatik_formatla(
    line_edit: QLineEdit,
    negatif_izin: bool = False,
    maksimum_deger: float = None
):
    """
    Mevcut bir QLineEdit'e otomatik formatlama ekler.
    
    Kullanım:
    ---------
    >>> line_edit = QLineEdit()
    >>> line_edit_otomatik_formatla(line_edit)
    
    Parametreler:
    -------------
    line_edit : QLineEdit
        Otomatik formatlama eklenecek widget
    negatif_izin : bool, optional
        Negatif değerlere izin ver
    maksimum_deger : float, optional
        Maksimum izin verilen değer
    """
    # Validator ekle
    validator = line_edit_fiyat_validatoru_ekle(
        line_edit,
        negatif_izin=negatif_izin,
        maksimum_deger=maksimum_deger
    )
    
    # Otomatik formatlama fonksiyonu
    def formatla():
        metin = line_edit.text()
        if not metin or not metin.strip():
            line_edit.setText("0,00")
            return
        
        try:
            deger = FiyatFormatlayici.turk_format_to_float(metin)
            formatli = FiyatFormatlayici.float_to_turk_format(deger)
            line_edit.setText(formatli)
        except:
            line_edit.setText("0,00")
    
    # Odak kaybında formatla
    line_edit.editingFinished.connect(formatla)
