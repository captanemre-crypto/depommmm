# git-sync.ps1 - Yerel <-> GitHub iki yonlu senkron
$ErrorActionPreference = 'Continue'
Set-Location (git rev-parse --show-toplevel)

Write-Host "`n[1/4] Uzak degisiklikler cekiliyor..." -ForegroundColor Cyan
git pull --rebase --autostash
if ($LASTEXITCODE -ne 0) {
    Write-Host "CARPISMA var! VS Code'da coz, sonra tekrar calistir." -ForegroundColor Red
    exit 1
}

Write-Host "`n[2/4] Degisiklikler ekleniyor..." -ForegroundColor Cyan
git add -A

if (git diff --cached --quiet) {
    Write-Host "Commit edilecek degisiklik yok." -ForegroundColor Yellow
} else {
    $msg = Read-Host "Commit mesaji (Enter = otomatik)"
    if ([string]::IsNullOrWhiteSpace($msg)) {
        $msg = "otomatik kayit $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    }
    git commit -m $msg
}

Write-Host "`n[3/4] GitHub'a gonderiliyor..." -ForegroundColor Cyan
git push
if ($LASTEXITCODE -ne 0) {
    Write-Host "Push basarisiz. 'git pull --rebase' sonrasi tekrar dene." -ForegroundColor Red
    exit 1
}

Write-Host "`n[4/4] Senkron tamam. Durum:" -ForegroundColor Green
git status -sb
git log --oneline -3