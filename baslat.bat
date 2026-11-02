@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Emre - Baslat

echo ==========================================
echo              EMRE BASLAT
 echo ==========================================
echo.

py -3 --version >nul 2>&1
if errorlevel 1 (
    echo Python bulunamadi. Python 3 kurup yeniden deneyin: https://www.python.org/downloads/
    pause
    exit /b 1
)

py -3 -c "import playwright" >nul 2>&1
if errorlevel 1 (
    echo Arena tarayici baglantisi icin Playwright yuklu degil.
    echo Yukleme internet baglantisi ve ek disk alani gerektirir.
    choice /C EH /N /M "Playwright ve Chromium simdi yuklensin mi? [E/H]: "
    if errorlevel 2 goto runserver
    py -3 -m pip install playwright
    if errorlevel 1 goto installerror
    echo Not: Otomasyon yüklü Microsoft Edge ile açilir; ayrica tarayici indirilmez.
)

:runserver
echo.
echo Emre baslatiliyor. Tarayicida http://127.0.0.1:8765 adresini acin.
echo Kapatmak icin bu pencerede Ctrl+C tuslarina basin.
echo.
py -3 server.py
if errorlevel 1 (
    echo.
    echo Sunucu baslatilamadi. Yukaridaki hatayi kontrol edin.
)
pause
exit /b

:installerror
echo.
echo Kurulum tamamlanamadi. Internet baglantisini ve yukaridaki hatayi kontrol edin.
echo Dilerseniz baslat.bat dosyasini yeniden calistirabilirsiniz.
pause
exit /b 1
