@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Yerel Turkce Piper Fahrettin ve Fettah sesleri kurulacak. Yaklasik 130 MB indirilir.
echo Fahrettin ve Fettah model kartlarinda egitim verisi CC0 olarak belirtilir.
echo Piper yaziliminin ve kullanilan modellerin lisanslarini inceleyin.
choice /C EH /N /M "Kosullari inceleyip kurulumu kabul ediyor musun? [E/H]: "
if errorlevel 2 exit /b
py -m uv --version >nul 2>&1
if errorlevel 1 (
 echo uv bulunamadi. Once: py -m pip install --user uv
 pause
 exit /b 1
)
if not exist .venv-ses\Scripts\python.exe py -m uv venv --python 3.12 .venv-ses
if not exist .venv-ses\Scripts\python.exe py -m uv venv .venv-ses
if not exist .venv-ses\Scripts\python.exe goto error
py -m uv pip install --python .venv-ses\Scripts\python.exe piper-tts
if errorlevel 1 goto error
.venv-ses\Scripts\python.exe piper_indir.py
if errorlevel 1 goto error
echo Hazir. Emre sunucusunu yeniden baslatip Ayarlar - Ses bolumune girin.
pause
exit /b 0
:error
echo Kurulum tamamlanamadi. Yukaridaki hata mesajini kontrol edin.
pause
exit /b 1
