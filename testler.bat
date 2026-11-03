@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Emre - Testler

py -3 --version >nul 2>&1
if errorlevel 1 (
    echo Python bulunamadi. Python 3 kurup yeniden deneyin: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ==========================================
echo              EMRE TESTLER
echo ==========================================
echo.
py -3 -m unittest discover -s tests -t . -v
if errorlevel 1 (
    echo.
    echo Testler basarisiz. Yukaridaki hata mesajini kontrol edin.
    pause
    exit /b 1
)
echo.
echo Tum testler gecti.
pause
exit /b 0
