@echo off
title Oyun Arsiv - EXE Olusturucu
echo ==========================================
echo    Oyun Arsiv - EXE Derleme
echo ==========================================
echo.

REM PyInstaller kontrolu
.venv\Scripts\pyinstaller --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] PyInstaller yukleniyor...
    .venv\Scripts\pip install pyinstaller
)

echo [*] EXE dosyasi derleniyor...
echo    Bu islem birkaç dakika surebilir.
echo.

.venv\Scripts\pyinstaller ^
    --onefile ^
    --windowed ^
    --name "OyunArsiv" ^
    --icon "icon.ico" ^
    --add-data "icon.png;." ^
    --add-data "icon.ico;." ^
    --hidden-import customtkinter ^
    --hidden-import PIL ^
    --hidden-import barcode ^
    --hidden-import barcode.codex ^
    --hidden-import barcode.code128 ^
    --collect-data customtkinter ^
    main.py

if %errorlevel% neq 0 (
    echo.
    echo [HATA] EXE olusturulamadi!
    pause
    exit /b 1
)

echo.
echo ==========================================
echo    EXE basariyla olusturuldu!
echo    Dosya: dist\OyunArsiv.exe
echo ==========================================
echo.

REM dist klasörüne ek dosyaları kopyala
copy /y icon.png dist\ >nul 2>&1
copy /y icon.ico dist\ >nul 2>&1

echo "dist" klasorunun icindeki OyunArsiv.exe
echo dosyasini istediginiz yere kopyalayabilirsiniz.
echo.
pause
