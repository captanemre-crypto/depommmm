# Emre - GitHub'daki yeni surumu cek (PowerShell)
# Kullanim:  powershell -ExecutionPolicy Bypass -File .\guncelle.ps1
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

$dal = 'arena/58f60478-depommmm'

function Baslik($m) { Write-Host ""; Write-Host "== $m" -ForegroundColor Cyan }

Baslik "Depo kontrolu"
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Git bulunamadi. Kur: https://git-scm.com/download/win" -ForegroundColor Red; exit 1
}
if (-not (Test-Path (Join-Path $PSScriptRoot '.git'))) {
    Write-Host "Bu klasor git deposu degil: $PSScriptRoot" -ForegroundColor Red
    Write-Host "Emre deposunun kopyasinda misin? (git rev-parse --show-toplevel ile bul)"
    exit 1
}

Write-Host "Klasor : $PSScriptRoot"
git status -sb
Write-Host ("Son commit: " + (git log --oneline -1))

Baslik "Yerel degisiklik kontrolu"
$kirli = git status --porcelain
if ($kirli) {
    Write-Host "Commit edilmemis degisiklikler var:" -ForegroundColor Yellow
    $kirli | ForEach-Object { Write-Host "  $_" }
    $cevap = Read-Host "Yine de devam edilsin mi? (e/h)"
    if ($cevap -notmatch '^[eE]') {
        Write-Host "Iptal. Once: git stash   ya da   git commit -am `"notlarim`""
        exit 1
    }
}

Baslik "GitHub'dan indiriliyor"
git fetch origin
if ($LASTEXITCODE -ne 0) { Write-Host "Indirme basarisiz; interneti ve depo erisimini kontrol et." -ForegroundColor Red; exit 1 }

$suan = (git rev-parse --abbrev-ref HEAD).Trim()
Write-Host "Su anki dal : $suan"
Write-Host "Guncel dal  : $dal"

if ($suan -ne $dal) {
    Write-Host ""
    Write-Host "Bu dalda yeni ozellik yok; 'git pull' bir sey degistirmez (normal)." -ForegroundColor Yellow
    $cevap = Read-Host "$dal dalina gecilsin mi? (e/h)"
    if ($cevap -notmatch '^[eE]') {
        Write-Host "Alternatif: GitHub'da PR #1'i birlestir, sonra main dalinde git pull yap."
        Write-Host "https://github.com/captanemre-crypto/depommmm/pull/1"
        exit 1
    }
    git rev-parse --verify --quiet "refs/heads/$dal" | Out-Null
    if ($LASTEXITCODE -ne 0) { git checkout -b $dal "origin/$dal" } else { git checkout $dal }
    if ($LASTEXITCODE -ne 0) { Write-Host "Dal degistirilemedi (yerel degisiklik olabilir): git stash dene." -ForegroundColor Red; exit 1 }
}

Baslik "Guncelleniyor"
git pull --ff-only origin $dal
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Cekme basarisiz. Yerel dal ile GitHub dali ayrismis olabilir." -ForegroundColor Yellow
    Write-Host "Sifirlamak icin (yerel farklari siler):  git reset --hard origin/$dal"
}

Baslik "Surum bilgisi"
$surum = Select-String -Path (Join-Path $PSScriptRoot 'server.py') -Pattern '^VERSION' | Select-Object -First 1
Write-Host $surum.Line
if (Select-String -Path (Join-Path $PSScriptRoot 'index.html') -Pattern 'Ücretsiz API' -Quiet) {
    Write-Host "Arayuzde 'Ücretsiz API' sekmesi var: guncel surum." -ForegroundColor Green
} else {
    Write-Host "UYARI: index.html icinde 'Ücretsiz API' yok; dosyalar guncellenmemis." -ForegroundColor Red
}

Write-Host ""
Write-Host "SIMDI YAPILACAKLAR:" -ForegroundColor Cyan
Write-Host "  1) Acik Emre sunucusunu kapat (pencerede Ctrl+C veya pencereyi kapat)"
Write-Host "  2) .\baslat.bat  (ya da  py -3 server.py ) ile yeniden baslat"
Write-Host "  3) Tarayicida Ctrl+F5 ile sayfayi zorla yenile"
Write-Host "  Kontrol: Ayarlar > 'Ücretsiz API' sekmesi gorunuyorsa tamam."
Write-Host ""
