"""
Widget İşlemleri Modülü
=======================

PyQt5 widget veri toplama ve yükleme fonksiyonları.

Bu modül, form widget'larından veri toplamak ve
widget'lara veri yüklemek için fonksiyonlar sağlar.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from PyQt5 import QtWidgets

# Modül günlükleyicisi
gunluk = logging.getLogger(__name__)


def widget_degerini_al(widget: QtWidgets.QWidget) -> Any:
    """
    Tek bir widget'tan değeri alır.
    
    Widget tipine göre uygun metodu çağırır.
    
    Parametreler:
    -------------
    widget : QWidget
        Değeri alınacak widget
    
    Döndürür:
    ---------
    Any
        Widget değeri (tip widget'a göre değişir)
    
    Örnekler:
    ---------
    >>> widget_degerini_al(line_edit)  # QLineEdit
    'metin değeri'
    
    >>> widget_degerini_al(spin_box)  # QSpinBox
    42
    
    >>> widget_degerini_al(check_box)  # QCheckBox
    True
    """
    if isinstance(widget, QtWidgets.QLineEdit):
        return widget.text()
    
    elif isinstance(widget, QtWidgets.QComboBox):
        return widget.currentText()
    
    elif isinstance(widget, QtWidgets.QSpinBox):
        return widget.value()
    
    elif isinstance(widget, QtWidgets.QDoubleSpinBox):
        return widget.value()
    
    elif isinstance(widget, QtWidgets.QCheckBox):
        return widget.isChecked()
    
    elif isinstance(widget, QtWidgets.QRadioButton):
        return widget.isChecked()
    
    elif isinstance(widget, QtWidgets.QTextEdit):
        return widget.toPlainText()
    
    elif isinstance(widget, QtWidgets.QPlainTextEdit):
        return widget.toPlainText()
    
    elif isinstance(widget, QtWidgets.QDateEdit):
        return widget.date().toString("yyyy-MM-dd")
    
    elif isinstance(widget, QtWidgets.QTimeEdit):
        return widget.time().toString("HH:mm:ss")
    
    elif isinstance(widget, QtWidgets.QDateTimeEdit):
        return widget.dateTime().toString("yyyy-MM-dd HH:mm:ss")
    
    elif isinstance(widget, QtWidgets.QSlider):
        return widget.value()
    
    elif isinstance(widget, QtWidgets.QDial):
        return widget.value()

    elif isinstance(widget, QtWidgets.QLabel):
        return widget.text()
    
    # Bilinmeyen widget tipi
    gunluk.debug(f"Bilinmeyen widget tipi: {type(widget).__name__}")
    return None


def widget_degerini_ayarla(widget: QtWidgets.QWidget, deger: Any) -> bool:
    """
    Tek bir widget'a değer ayarlar.
    
    Widget tipine göre uygun metodu çağırır.
    
    Parametreler:
    -------------
    widget : QWidget
        Değer ayarlanacak widget
    deger : Any
        Ayarlanacak değer
    
    Döndürür:
    ---------
    bool
        Başarılı ise True
    """
    try:
        if isinstance(widget, QtWidgets.QLineEdit):
            widget.setText(str(deger) if deger is not None else "")
            return True
        
        elif isinstance(widget, QtWidgets.QComboBox):
            metin = str(deger) if deger is not None else ""
            idx = widget.findText(metin)
            if idx >= 0:
                widget.setCurrentIndex(idx)
            else:
                # Listede yoksa ekle
                widget.addItem(metin)
                widget.setCurrentText(metin)
            return True
        
        elif isinstance(widget, QtWidgets.QSpinBox):
            widget.setValue(int(deger) if deger is not None else 0)
            return True
        
        elif isinstance(widget, QtWidgets.QDoubleSpinBox):
            widget.setValue(float(deger) if deger is not None else 0.0)
            return True
        
        elif isinstance(widget, QtWidgets.QCheckBox):
            widget.setChecked(bool(deger) if deger is not None else False)
            return True
        
        elif isinstance(widget, QtWidgets.QRadioButton):
            widget.setChecked(bool(deger) if deger is not None else False)
            return True
        
        elif isinstance(widget, QtWidgets.QTextEdit):
            widget.setPlainText(str(deger) if deger is not None else "")
            return True
        
        elif isinstance(widget, QtWidgets.QPlainTextEdit):
            widget.setPlainText(str(deger) if deger is not None else "")
            return True
        
        elif isinstance(widget, QtWidgets.QSlider):
            widget.setValue(int(deger) if deger is not None else 0)
            return True
        
        elif isinstance(widget, QtWidgets.QDial):
            widget.setValue(int(deger) if deger is not None else 0)
            return True
        
        # Bilinmeyen widget tipi
        gunluk.debug(f"Bilinmeyen widget tipi: {type(widget).__name__}")
        return False
    
    except (ValueError, TypeError) as e:
        gunluk.warning(f"Widget değer ayarlama hatası ({widget.objectName()}): {e}")
        return False


def tum_widget_verilerini_topla(
    parent: QtWidgets.QWidget,
    bos_isimleri_atla: bool = True
) -> dict[str, Any]:
    """
    Bir parent widget altındaki tüm form verilerini toplar.
    
    Desteklenen widget tipleri:
    - QLineEdit
    - QComboBox
    - QSpinBox
    - QDoubleSpinBox
    - QCheckBox
    - QRadioButton
    - QTextEdit
    - QPlainTextEdit
    - QDateEdit
    - QTimeEdit
    - QDateTimeEdit
    - QSlider
    - QDial
    
    Parametreler:
    -------------
    parent : QWidget
        Üst widget
    bos_isimleri_atla : bool, optional
        Boş objectName'li widget'ları atlayıp atlamama (varsayılan: True)
    
    Döndürür:
    ---------
    dict[str, Any]
        Widget objectName -> değer eşlemesi
    
    Örnekler:
    ---------
    >>> veri = tum_widget_verilerini_topla(form)
    >>> veri
    {'isim_line': 'Ahmet', 'yas_spin': 25, 'aktif_check': True}
    """
    veri: dict[str, Any] = {}
    
    # Desteklenen widget tipleri
    desteklenen_tipler = (
        QtWidgets.QLineEdit,
        QtWidgets.QComboBox,
        QtWidgets.QSpinBox,
        QtWidgets.QDoubleSpinBox,
        QtWidgets.QCheckBox,
        QtWidgets.QRadioButton,
        QtWidgets.QTextEdit,
        QtWidgets.QPlainTextEdit,
        QtWidgets.QDateEdit,
        QtWidgets.QTimeEdit,
        QtWidgets.QDateTimeEdit,
        QtWidgets.QSlider,
        QtWidgets.QDial,
        QtWidgets.QLabel,
    )
    
    for widget in parent.findChildren(QtWidgets.QWidget):
        # Sadece desteklenen tipleri işle
        if not isinstance(widget, desteklenen_tipler):
            continue
        
        ad = widget.objectName()
        
        # Boş isimleri atla
        if bos_isimleri_atla and not ad:
            continue
        
        deger = widget_degerini_al(widget)
        if deger is not None:
            veri[ad] = deger
    
    gunluk.debug(f"Toplanan widget sayısı: {len(veri)}")
    return veri


def widget_verilerini_geri_yukle(
    parent: QtWidgets.QWidget,
    veri: dict[str, Any],
    eksik_widgetleri_logla: bool = False
) -> int:
    """
    Kaydedilmiş verileri widget'lara geri yükler.
    
    Parametreler:
    -------------
    parent : QWidget
        Üst widget
    veri : dict[str, Any]
        Widget objectName -> değer eşlemesi
    eksik_widgetleri_logla : bool, optional
        Bulunamayan widget'ları loglayıp loglamama (varsayılan: False)
    
    Döndürür:
    ---------
    int
        Başarıyla yüklenen widget sayısı
    
    Örnekler:
    ---------
    >>> veri = {'isim_line': 'Ahmet', 'yas_spin': 25}
    >>> yuklenen = widget_verilerini_geri_yukle(form, veri)
    >>> yuklenen
    2
    """
    if not veri:
        return 0
    
    yuklenen_sayisi = 0
    bulunan_widgetler = set()
    
    # Tüm widget'ları tara
    for widget in parent.findChildren(QtWidgets.QWidget):
        ad = widget.objectName()
        
        if ad in veri:
            bulunan_widgetler.add(ad)
            if widget_degerini_ayarla(widget, veri[ad]):
                yuklenen_sayisi += 1
    
    # Eksik widget'ları logla
    if eksik_widgetleri_logla:
        eksik = set(veri.keys()) - bulunan_widgetler
        if eksik:
            gunluk.warning(f"Bulunamayan widget'lar: {eksik}")
    
    gunluk.debug(f"Yüklenen widget sayısı: {yuklenen_sayisi}/{len(veri)}")
    return yuklenen_sayisi


def belirli_widgetlari_topla(
    parent: QtWidgets.QWidget,
    widget_adlari: list[str]
) -> dict[str, Any]:
    """
    Sadece belirtilen widget'lardan veri toplar.
    
    Parametreler:
    -------------
    parent : QWidget
        Üst widget
    widget_adlari : list[str]
        Toplanacak widget objectName'leri
    
    Döndürür:
    ---------
    dict[str, Any]
        Widget objectName -> değer eşlemesi
    """
    veri: dict[str, Any] = {}
    
    for ad in widget_adlari:
        widget = parent.findChild(QtWidgets.QWidget, ad)
        if widget is not None:
            deger = widget_degerini_al(widget)
            if deger is not None:
                veri[ad] = deger
        else:
            gunluk.debug(f"Widget bulunamadı: {ad}")
    
    return veri


def widget_varmi(parent: QtWidgets.QWidget, ad: str) -> bool:
    """
    Belirtilen isimde widget var mı kontrol eder.
    
    Parametreler:
    -------------
    parent : QWidget
        Üst widget
    ad : str
        Aranacak widget objectName'i
    
    Döndürür:
    ---------
    bool
        Widget bulundu ise True
    """
    widget = parent.findChild(QtWidgets.QWidget, ad)
    return widget is not None


def guvenli_widget_al(
    parent: QtWidgets.QWidget,
    ad: str,
    widget_tipi: type = QtWidgets.QWidget
) -> Optional[QtWidgets.QWidget]:
    """
    Widget'ı güvenli şekilde alır (None kontrolü ile).
    
    Parametreler:
    -------------
    parent : QWidget
        Üst widget
    ad : str
        Widget objectName'i
    widget_tipi : type, optional
        Beklenen widget tipi (varsayılan: QWidget)
    
    Döndürür:
    ---------
    Optional[QWidget]
        Widget nesnesi veya None
    """
    widget = parent.findChild(widget_tipi, ad)
    return widget
