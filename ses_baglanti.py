"""Local speech worker bridge with bounded audio, serialized requests and timeouts."""
import os, json, threading, tempfile, base64
from pathlib import Path
from yerel_isci import YerelIsci

ROOT = Path(__file__).resolve().parent
lock = threading.Lock()
worker = None


def transcribe(encoded):
    global worker
    if not isinstance(encoded, str) or len(encoded) > 8_000_000:
        raise ValueError('Ses verisi çok büyük.')
    try:
        raw = base64.b64decode(encoded, validate=True)
    except Exception:
        raise ValueError('Ses verisi geçersiz.')
    if not 100 < len(raw) <= 5_000_000:
        raise ValueError('Ses verisi boş veya çok büyük.')
    executable = ROOT / '.venv-ses' / 'Scripts' / 'python.exe'
    if not executable.is_file():
        raise ValueError('Yerel ses kurulu değil. ses_kur.bat dosyasını çalıştır.')
    with lock:
        if worker is None:
            # İlk yükleme modeli diske alır; bu yüzden açılış süresi uzun tutulur.
            worker = YerelIsci(executable, ROOT / 'ses_servisi.py', baslatma_saniye=240, istek_saniye=240)
        name = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as f:
                name = f.name
                f.write(raw)
            result = worker.istek({'path': name})
            if result.get('error'):
                raise ValueError(result['error'])
            return str(result.get('text', '')).strip()
        finally:
            if name:
                try:
                    os.unlink(name)
                except OSError:
                    pass
