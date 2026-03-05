@echo off
title Oyun Arsiv - Kurulum
echo ==========================================
echo    Oyun Arsiv - Windows Kurulumu
echo ==========================================
echo.

REM Python kontrolu
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [HATA] Python bulunamadi!
    echo Python 3.10+ yukleyin: https://www.python.org/downloads/
    echo Kurulumda "Add Python to PATH" secenegini isaretleyin.
    pause
    exit /b 1
)

echo [1/3] Sanal ortam olusturuluyor...
python -m venv .venv
if %errorlevel% neq 0 (
    echo [HATA] Sanal ortam olusturulamadi!
    pause
    exit /b 1
)

echo [2/3] Bagimliliklar yukleniyor...
.venv\Scripts\pip install --upgrade pip >nul 2>&1
.venv\Scripts\pip install customtkinter "python-barcode[images]" Pillow reportlab
if %errorlevel% neq 0 (
    echo [HATA] Paketler yuklenemedi!
    pause
    exit /b 1
)

echo [3/3] Masaustu kisayolu olusturuluyor...
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%USERPROFILE%\Desktop\Oyun Arsiv.lnk'); $s.TargetPath = '%CD%\.venv\Scripts\pythonw.exe'; $s.Arguments = 'main.py'; $s.WorkingDirectory = '%CD%'; $s.IconLocation = '%CD%\icon.ico'; $s.Description = 'Oyun Arsiv - Video Oyun Yonetimi'; $s.Save()"

echo.
echo ==========================================
echo    Kurulum tamamlandi!
echo    Masaustundeki "Oyun Arsiv" simgesine
echo    tiklayarak uygulamayi baslatabilirsiniz.
echo ==========================================
echo.
pause
