"""
Tarih Yardımcıları Modülü
========================

Tarih formatlarını standartlaştırır: GÜN-AY-YIL (DD-MM-YYYY)
"""

from datetime import datetime
from typing import Optional, Tuple
import re


# STANDART FORMAT: GÜN-AY-YIL
STANDART_TARIH_FORMATI = "%d-%m-%Y"  # 28-01-2026
VERITABANI_TARIH_FORMATI = "%Y-%m-%d"  # 2026-01-28 (SQL için)
SERI_TARIH_FORMATI = "%d%m%y"  # 280126 (Seri numarası için)


def tarih_parse_et(tarih_str: str) -> Optional[datetime]:
    """
    Çeşitli formatlardaki tarihi parse eder.
    
    Desteklenen formatlar:
    - 28-01-2026, 28.01.2026, 28/01/2026, 28 01 2026, 28,01,2026
    - 2026-01-28, 2026.01.28, 2026/01/28 (ISO formatı)
    - 28012026 (8 haneli)
    - 280126 (6 haneli, yıl 2 haneli)
    
    Parametreler:
    -------------
    tarih_str : str
        Parse edilecek tarih metni
    
    Döndürür:
    ---------
    datetime | None
        Parse edilmiş tarih veya None (başarısızsa)
    
    Örnek:
    ------
    >>> tarih_parse_et("28-01-2026")
    datetime(2026, 1, 28)
    >>> tarih_parse_et("28.01.2026")
    datetime(2026, 1, 28)
    >>> tarih_parse_et("28/01/2026")
    datetime(2026, 1, 28)
    """
    if not tarih_str:
        return None
    
    tarih_str = str(tarih_str).strip()
    
    # Ayırıcıları temizle, sadece rakamları al
    tarih_temiz = re.sub(r'[^\d]', '', tarih_str)
    
    # 8 haneli: DDMMYYYY veya YYYYMMDD
    if len(tarih_temiz) == 8:
        # YYYYMMDD mi kontrol et (yıl 2000-2100)
        if tarih_temiz[:4].isdigit():
            yil = int(tarih_temiz[:4])
            if 2000 <= yil <= 2100:
                # ISO format: YYYYMMDD
                ay = int(tarih_temiz[4:6])
                gun = int(tarih_temiz[6:8])
            else:
                # GÜN formatı: DDMMYYYY
                gun = int(tarih_temiz[:2])
                ay = int(tarih_temiz[2:4])
                yil = int(tarih_temiz[4:8])
        else:
            # GÜN formatı: DDMMYYYY
            gun = int(tarih_temiz[:2])
            ay = int(tarih_temiz[2:4])
            yil = int(tarih_temiz[4:8])
    
    # 6 haneli: DDMMYY
    elif len(tarih_temiz) == 6:
        gun = int(tarih_temiz[:2])
        ay = int(tarih_temiz[2:4])
        yil_kismi = int(tarih_temiz[4:6])
        
        # 2000'li yıllar için +2000, 1900'lü yıllar için +1900
        if yil_kismi >= 0 and yil_kismi <= 50:
            yil = 2000 + yil_kismi
        else:
            yil = 1900 + yil_kismi
    
    # 4 haneli: DDMM (bugünün yılını kullan)
    elif len(tarih_temiz) == 4:
        gun = int(tarih_temiz[:2])
        ay = int(tarih_temiz[2:4])
        yil = datetime.now().year
    
    else:
        # Desteklenmeyen format
        return None
    
    # Tarih oluştur
    try:
        return datetime(yil, ay, gun)
    except ValueError:
        # Geçersiz tarih (örn: 32-13-2026)
        return None


def tarih_formatla(
    tarih_obj: datetime,
    format_tipi: str = "standart"
) -> str:
    """
    Datetime nesnesini belirtilen formata çevirir.
    
    Parametreler:
    -------------
    tarih_obj : datetime
        Formatlanacak tarih
    format_tipi : str
        'standart': DD-MM-YYYY (28-01-2026)
        'veritabani': YYYY-MM-DD (2026-01-28)
        'seri': DDMMYY (280126)
        'nokta': DD.MM.YYYY (28.01.2026)
        'slash': DD/MM/YYYY (28/01/2026)
    
    Döndürür:
    ---------
    str
        Formatlanmış tarih
    
    Örnek:
    ------
    >>> dt = datetime(2026, 1, 28)
    >>> tarih_formatla(dt, 'standart')
    '28-01-2026'
    >>> tarih_formatla(dt, 'veritabani')
    '2026-01-28'
    >>> tarih_formatla(dt, 'seri')
    '280126'
    """
    if format_tipi == "standart":
        return tarih_obj.strftime("%d-%m-%Y")
    elif format_tipi == "veritabani":
        return tarih_obj.strftime("%Y-%m-%d")
    elif format_tipi == "seri":
        return tarih_obj.strftime("%d%m%y")
    elif format_tipi == "nokta":
        return tarih_obj.strftime("%d.%m.%Y")
    elif format_tipi == "slash":
        return tarih_obj.strftime("%d/%m/%Y")
    else:
        # Varsayılan: standart
        return tarih_obj.strftime("%d-%m-%Y")


def tarih_donustur(
    tarih_str: str,
    hedef_format: str = "standart"
) -> Tuple[bool, str, str]:
    """
    Çeşitli formatlardaki tarihi hedef formata dönüştürür.
    
    Parametreler:
    -------------
    tarih_str : str
        Kaynak tarih metni (herhangi bir format)
    hedef_format : str
        Hedef format ('standart', 'veritabani', 'seri', vb.)
    
    Döndürür:
    ---------
    tuple[bool, str, str]
        (başarılı, dönüştürülmüş_tarih, hata_mesajı)
    
    Örnek:
    ------
    >>> tarih_donustur("28.01.2026", "standart")
    (True, "28-01-2026", "")
    >>> tarih_donustur("2026-01-28", "seri")
    (True, "280126", "")
    >>> tarih_donustur("hatalı", "standart")
    (False, "", "Geçersiz tarih formatı")
    """
    # Parse et
    tarih_obj = tarih_parse_et(tarih_str)
    
    if tarih_obj is None:
        return False, "", f"Geçersiz tarih formatı: {tarih_str}"
    
    # Formatla
    try:
        formatli_tarih = tarih_formatla(tarih_obj, hedef_format)
        return True, formatli_tarih, ""
    except Exception as e:
        return False, "", f"Tarih formatlama hatası: {e}"


def bugun(format_tipi: str = "standart") -> str:
    """
    Bugünün tarihini belirtilen formatta döner.
    
    Parametreler:
    -------------
    format_tipi : str
        Hedef format
    
    Döndürür:
    ---------
    str
        Bugünün tarihi
    
    Örnek:
    ------
    >>> bugun("standart")
    '28-01-2026'
    >>> bugun("veritabani")
    '2026-01-28'
    """
    return tarih_formatla(datetime.now(), format_tipi)


def tarih_widget_formatla(tarih_str: str) -> str:
    """
    UI widget'larından gelen tarihi standart formata çevirir.
    
    Özel kullanım: QLineEdit, QDateEdit'ten gelen değerler
    
    Parametreler:
    -------------
    tarih_str : str
        Widget'tan gelen tarih
    
    Döndürür:
    ---------
    str
        Standart format (DD-MM-YYYY) veya boş (hata durumunda)
    
    Örnek:
    ------
    >>> tarih_widget_formatla("28.01.2026")
    '28-01-2026'
    >>> tarih_widget_formatla("28/01/2026")
    '28-01-2026'
    >>> tarih_widget_formatla("hatalı")
    ''
    """
    basarili, formatli, _ = tarih_donustur(tarih_str, "standart")
    return formatli if basarili else ""


# Test
if __name__ == "__main__":
    print("=" * 60)
    print("TARİH YARDIMCILARI - TEST")
    print("=" * 60)
    
    test_tarihleri = [
        "28-01-2026",
        "28.01.2026",
        "28/01/2026",
        "28 01 2026",
        "28,01,2026",
        "2026-01-28",
        "28012026",
        "280126",
        "hatalı",
    ]
    
    print("\n1. Parse Testi:")
    for tarih in test_tarihleri:
        sonuc = tarih_parse_et(tarih)
        print(f"  {tarih:20s} → {sonuc}")
    
    print("\n2. Dönüştürme Testi (Standart Format):")
    for tarih in test_tarihleri:
        basarili, formatli, hata = tarih_donustur(tarih, "standart")
        if basarili:
            print(f"  {tarih:20s} → {formatli}")
        else:
            print(f"  {tarih:20s} → HATA: {hata}")
    
    print("\n3. Dönüştürme Testi (Veritabanı Format):")
    for tarih in ["28-01-2026", "28.01.2026", "280126"]:
        basarili, formatli, _ = tarih_donustur(tarih, "veritabani")
        if basarili:
            print(f"  {tarih:20s} → {formatli}")
    
    print("\n4. Dönüştürme Testi (Seri Format):")
    for tarih in ["28-01-2026", "2026-01-28"]:
        basarili, formatli, _ = tarih_donustur(tarih, "seri")
        if basarili:
            print(f"  {tarih:20s} → {formatli}")
    
    print("\n5. Bugün:")
    print(f"  Standart    : {bugun('standart')}")
    print(f"  Veritabanı  : {bugun('veritabani')}")
    print(f"  Seri        : {bugun('seri')}")
    
    print("\n✅ TEST TAMAMLANDI!")
