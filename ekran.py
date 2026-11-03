"""Ekran görüntüsü alma (yerel).

Windows'ta PowerShell + System.Drawing kullanır (ek bağımlılık gerekmez);
diğer platformlarda Pillow varsa onu dener. Görüntü **yalnızca** kullanıcı
isteğiyle (`confirmed:true`) alınır ve diske yazılmaz.
"""
import base64
import os
import subprocess
import sys
import tempfile
from pathlib import Path

AZAMI_BAYT = 6_000_000


def _powershell():
    kok = Path(os.environ.get('SystemRoot', r'C:\Windows'))
    return kok / 'System32' / 'WindowsPowerShell' / 'v1.0' / 'powershell.exe'


def _windows_png():
    hedef = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    hedef.close()
    betik = (
        'Add-Type -AssemblyName System.Windows.Forms,System.Drawing;'
        '$b=[System.Windows.Forms.SystemInformation]::VirtualScreen;'
        '$bmp=New-Object System.Drawing.Bitmap $b.Width,$b.Height;'
        '$g=[System.Drawing.Graphics]::FromImage($bmp);'
        '$g.CopyFromScreen($b.Location,[System.Drawing.Point]::Empty,$b.Size);'
        f'$bmp.Save("{hedef.name}",[System.Drawing.Imaging.ImageFormat]::Png);'
        '$g.Dispose();$bmp.Dispose()'
    )
    try:
        sonuc = subprocess.run([str(_powershell()), '-NoProfile', '-NonInteractive',
                                '-ExecutionPolicy', 'Bypass', '-Command', betik],
                               capture_output=True, text=True, timeout=25)
        yol = Path(hedef.name)
        if sonuc.returncode != 0 or not yol.is_file() or yol.stat().st_size == 0:
            raise ValueError('Ekran görüntüsü alınamadı (PowerShell).')
        return yol.read_bytes()
    finally:
        try:
            os.unlink(hedef.name)
        except OSError:
            pass


def _pillow_png():
    try:
        from PIL import ImageGrab  # type: ignore
    except Exception:
        raise ValueError('Ekran görüntüsü için Pillow gerekli: pip install pillow')
    goruntu = ImageGrab.grab()
    import io
    tampon = io.BytesIO()
    goruntu.save(tampon, format='PNG')
    return tampon.getvalue()


def yakala():
    """Ekran görüntüsünü PNG baytları olarak döndürür."""
    if sys.platform == 'win32':
        veri = _windows_png()
    else:
        veri = _pillow_png()
    if len(veri) > AZAMI_BAYT:
        raise ValueError('Ekran görüntüsü çok büyük.')
    return veri


def base64_png():
    return base64.b64encode(yakala()).decode('ascii')
