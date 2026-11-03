"""Masaüstü bildirimi ve uyarı sesi (ek bağımlılık yok).

Windows'ta PowerShell `NotifyIcon` balonu kullanılır (pythonw ile çalışırken de
görünür). Linux/macOS'ta `notify-send` varsa o kullanılır. Bildirim gösterilemezse
sessizce False döner; hiçbir zaman istisna fırlatıp hatırlatıcı akışını bozmaz.
"""
import os
import shutil
import subprocess
import sys

AZAMI_KARAKTER = 300


def _temizle(metin, azami=AZAMI_KARAKTER) -> str:
    return ' '.join(str(metin or '').split())[:azami]


def _powershell() -> str:
    kok = os.environ.get('SystemRoot', r'C:\Windows')
    return os.path.join(kok, 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe')


def _windows(baslik: str, metin: str) -> bool:
    baslik = _temizle(baslik, 80).replace("'", "''")
    metin = _temizle(metin).replace("'", "''")
    betik = (
        'Add-Type -AssemblyName System.Windows.Forms;'
        'Add-Type -AssemblyName System.Drawing;'
        '$n=New-Object System.Windows.Forms.NotifyIcon;'
        '$n.Icon=[System.Drawing.SystemIcons]::Information;'
        '$n.Visible=$true;'
        f"$n.ShowBalloonTip(8000,'{baslik}','{metin}',"
        '[System.Windows.Forms.ToolTipIcon]::Info);'
        'Start-Sleep -Seconds 9;$n.Visible=$false;$n.Dispose()'
    )
    try:
        subprocess.Popen([_powershell(), '-NoProfile', '-NonInteractive',
                          '-ExecutionPolicy', 'Bypass', '-Command', betik],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        return True
    except Exception:
        return False


def _diger(baslik: str, metin: str) -> bool:
    arac = shutil.which('notify-send')
    if not arac:
        return False
    try:
        subprocess.Popen([arac, _temizle(baslik, 80), _temizle(metin)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def goster(baslik, metin) -> bool:
    """Masaüstü bildirimi gösterir; mümkün değilse False döner."""
    baslik, metin = _temizle(baslik, 80), _temizle(metin)
    if not metin:
        return False
    if sys.platform == 'win32':
        return _windows(baslik, metin)
    return _diger(baslik, metin)


def cal(sure_ms=200) -> bool:
    """Kısa uyarı sesi (Windows'ta sistem bip sesi)."""
    if sys.platform == 'win32':
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
            return True
        except Exception:
            return False
    return False
