@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Emre - GitHub'dan Guncelle
setlocal enabledelayedexpansion

echo ==========================================
echo        EMRE - GITHUB'DAN GUNCELLE
echo ==========================================
echo.

git --version >nul 2>&1
if errorlevel 1 (
    echo Git bulunamadi. Kur: https://git-scm.com/download/win
    pause
    exit /b 1
)

if not exist ".git" (
    echo Bu klasor bir git deposu degil: %CD%
    echo Dogru klasorde misin? Depo genelde: c:\Users\SERVER\Desktop\jarvis
    pause
    exit /b 1
)

echo [1/5] Mevcut durum:
git status -sb
echo.
echo Yerel commit:
git log --oneline -1
echo.

git status --porcelain | findstr /r "." >nul
if not errorlevel 1 (
    echo UYARI: Commit edilmemis degisiklikler var. Bunlarin uzerine yazilmaz,
    echo        ama birlestirme sirasinda cakisma cikabilir.
    choice /C EH /N /M "Yine de devam edilsin mi? [E/H]: "
    if errorlevel 2 (
        echo Islem iptal edildi. Once: git stash  ya da  git commit -am "notlarim"
        pause
        exit /b 1
    )
)

echo [2/5] GitHub'daki dallar indiriliyor...
git fetch origin
if errorlevel 1 (
    echo.
    echo Indirme basarisiz. Internet baglantisini ve depo erisimini kontrol et.
    pause
    exit /b 1
)
echo.

set "DAL=arena/58f60478-depommmm"
set "SUAN="
for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD') do set "SUAN=%%b"
echo Su anki dal: !SUAN!
echo Guncel calisma dali: !DAL!
echo.

if "!SUAN!"=="!DAL!" (
    echo [3/5] Bu daldasin; son degisiklikler cekiliyor...
    git pull --ff-only origin "!DAL!"
    if errorlevel 1 (
        echo.
        echo Cekme basarisiz. Muhtemel sebep: yerel dal ile GitHub dali ayrismis.
        echo Duzeltmek icin:  git reset --hard origin/!DAL!
        echo DIKKAT: bu komut yereldeki commit edilmemis/edilmis farklari siler.
    )
) else (
    echo [3/5] Su an "!SUAN!" dalindasin. Yeni ozellikler "!DAL!" dalinda.
    echo       Bu yuzden "git pull" bir sey degistirmez — normal.
    choice /C EH /N /M "Bu dala gecilsin mi? [E/H]: "
    if errorlevel 2 (
        echo.
        echo Alternatif: once GitHub'da Pull Request #1'i birlestir, sonra main dalinde git pull yap.
        echo Adres: https://github.com/captanemre-crypto/depommmm/pull/1
        pause
        exit /b 1
    )
    git rev-parse --verify --quiet "refs/heads/!DAL!" >nul
    if errorlevel 1 (
        git checkout -b "!DAL!" "origin/!DAL!"
    ) else (
        git checkout "!DAL!"
        git pull --ff-only origin "!DAL!"
    )
)

echo.
echo [4/5] Dosyalar guncellendi. Surum bilgisi:
findstr /b /c:"VERSION" server.py
echo.

echo [5/5] ONEMLI: Degisikliklerin gorunmesi icin
echo       1. Acik olan Emre sunucusunu kapat  (pencerede Ctrl+C)
echo       2. baslat.bat ile yeniden baslat
echo       3. Tarayicida Ctrl+F5 ile sayfayi zorla yenile
echo.
echo Kontrol: Ayarlar > "Ücretsiz API" sekmesi gorunuyorsa guncel surumdesin.
echo.
pause
endlocal
