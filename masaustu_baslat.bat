@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv-desktop\Scripts\python.exe (
 echo Masaustu ortami kurulu degil. Once masaustu_kur.bat dosyasini calistirin.
 pause
 exit /b 1
)
.venv-desktop\Scripts\python.exe masaustu.py
if errorlevel 1 (
 echo.
 echo Emre acilamadi. Yukaridaki hata mesajini kontrol edin.
 pause
)
