@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Daha iyi Turkce anlama icin Whisper small modeli internetten indirilecek.
echo Indirme tamamlaninca ses tanima internetsiz ve CPU uzerinde calisir.
choice /C EH /N /M "Indirme ve kuruluma baslansin mi? [E/H]: "
if errorlevel 2 exit /b
if not exist .venv-ses\Scripts\python.exe (
 echo Ses ortami bulunamadi. Once ses_kur.bat ile kurulum yapin.
 pause
 exit /b 1
)
.venv-ses\Scripts\python.exe -X utf8 ses_small_kur.py
if errorlevel 1 echo Kurulum tamamlanamadi. Yukaridaki hata mesajini kontrol edin.
pause
