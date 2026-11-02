@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo EMRE masaustu prototipi icin pywebview, pystray ve Pillow indirilecek.
echo Windows icin Microsoft Edge WebView2 Runtime gerekebilir.
choice /C EH /N /M "Masaustu bilesenleri kurulsun mu? [E/H]: "
if errorlevel 2 exit /b
py -m uv --version >nul 2>&1
if errorlevel 1 (
 echo uv bulunamadi. Once: py -m pip install --user uv
 pause
 exit /b 1
)
if not exist .venv-desktop\Scripts\python.exe py -m uv venv --python 3.12 .venv-desktop
if not exist .venv-desktop\Scripts\python.exe goto error
py -m uv pip install --python .venv-desktop\Scripts\python.exe "pywebview>=6,<7" "pystray>=0.19,<1" "Pillow>=10,<13"
if errorlevel 1 goto error
.venv-desktop\Scripts\python.exe masaustu_ayar.py
if errorlevel 1 goto error
echo Kurulum tamamlandi. Masaustundeki EMRE kisayolunu kullanin.
pause
exit /b 0
:error
echo Kurulum tamamlanamadi. Yukaridaki hatayi kontrol edin.
pause
exit /b 1
