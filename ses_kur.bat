@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Turkce yerel ses tanima kurulumu: Python paketleri ve Whisper base modeli indirilecek.
echo Internet ve disk alani gereklidir. Ilk indirmeden sonra internet gerekmez.
choice /C EH /N /M "Kuruluma baslansin mi? [E/H]: "
if errorlevel 2 exit /b
py -m uv --version >nul 2>&1
if errorlevel 1 (
 echo uv bulunamadi. Once: py -m pip install --user uv
 pause
 exit /b 1
)
if not exist .venv-ses\Scripts\python.exe py -m uv venv --python 3.12 .venv-ses
if not exist .venv-ses\Scripts\python.exe py -m uv venv .venv-ses
if errorlevel 1 goto error
py -m uv pip install --python .venv-ses\Scripts\python.exe faster-whisper "av>=15,<19"
if errorlevel 1 goto error
.venv-ses\Scripts\python.exe -c "from faster_whisper import WhisperModel; WhisperModel('base',device='cpu',compute_type='int8'); print('Model indirildi.')"
if errorlevel 1 goto error
echo Kurulum bitti. Emre sunucusunu yeniden baslatin.
pause
exit /b 0
:error
echo Kurulum tamamlanamadi; yukaridaki hata mesajini kontrol edin.
pause
exit /b 1
