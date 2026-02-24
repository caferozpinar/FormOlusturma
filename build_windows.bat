@echo off
chcp 65001 >nul
echo ══════════════════════════════════════
echo   FormOlusturma - Windows Build
echo ══════════════════════════════════════
echo.

REM Python kontrol
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [HATA] Python bulunamadi!
    echo Python 3.10+ kurun: https://python.org/downloads
    pause
    exit /b 1
)

echo [1/4] Bagimliliklari kuruluyor...
pip install -r requirements.txt
pip install pyinstaller
echo.

echo [2/4] Klasorler olusturuluyor...
if not exist veri mkdir veri
if not exist loglar mkdir loglar
if not exist sablonlar mkdir sablonlar
echo.

echo [3/4] EXE olusturuluyor (bu 2-5 dakika surebilir)...
pyinstaller build.spec --noconfirm
echo.

if exist dist\FormOlusturma\FormOlusturma.exe (
    echo [4/4] Build basarili!
    echo.
    echo   Cikti: dist\FormOlusturma\
    echo   EXE:   dist\FormOlusturma\FormOlusturma.exe
    echo.
    echo   Bu klasoru ZIP'leyip dagitabilirsiniz.
) else (
    echo [HATA] Build basarisiz!
    echo   Hata loglarini kontrol edin.
)

echo.
pause
