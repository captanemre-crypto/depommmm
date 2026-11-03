"""Local speech worker bridge with bounded audio, serialized requests and timeouts.

Konuşma tanıma (Whisper) tek bir kalıcı işçide çalışır. Model seçimi
`saglayici_ayar.json` benzeri `whisper_ayar.json` dosyasında tutulur; `base` hızlı
ama Türkçede daha çok kelime kaçırır, `small` belirgin şekilde daha doğrudur.
"""
import base64
import json
import os
import tempfile
import threading
from pathlib import Path

from yerel_isci import YerelIsci

ROOT = Path(__file__).resolve().parent
AYAR = ROOT / 'whisper_ayar.json'
MODELLER = ('base', 'small')
lock = threading.Lock()
worker = None


def _yol():
    return ROOT / '.venv-ses' / 'Scripts' / 'python.exe'


def model():
    """Etkin Whisper modeli (whisper_ayar.json; varsayılan base)."""
    try:
        veri = json.loads(AYAR.read_text(encoding='utf-8'))
        ad = veri.get('model') if isinstance(veri, dict) else None
    except (OSError, ValueError):
        ad = None
    return ad if ad in MODELLER else 'base'


def ayarla(ad):
    """Modeli değiştirir; dosya yoksa yazılır, işçi bir sonraki istekte yeniden açılır."""
    if ad not in MODELLER:
        raise ValueError('Model yalnızca base veya small olabilir.')
    global worker
    with lock:
        AYAR.write_text(json.dumps({'model': ad}), encoding='utf-8')
        if worker is not None:
            worker.kapat()
            worker = None
    return durum()


def durum():
    return {'installed': _yol().is_file(), 'model': model(),
            'models': list(MODELLER),
            'hint': ('small modeli Türkçeyi belirgin şekilde daha iyi anlar; kurmak için '
                     'ses_small_kur.bat çalıştır (internet gerekir).')}


def transcribe(encoded, ipucu=''):
    global worker
    if not isinstance(encoded, str) or len(encoded) > 8_000_000:
        raise ValueError('Ses verisi çok büyük.')
    try:
        raw = base64.b64decode(encoded, validate=True)
    except Exception:
        raise ValueError('Ses verisi geçersiz.')
    if not 100 < len(raw) <= 5_000_000:
        raise ValueError('Ses verisi boş veya çok büyük.')
    executable = _yol()
    if not executable.is_file():
        raise ValueError('Yerel ses kurulu değil. ses_kur.bat dosyasını çalıştır.')
    ipucu = str(ipucu or '')[:300]
    with lock:
        if worker is None:
            # İlk yükleme modeli diske alır; bu yüzden açılış süresi uzun tutulur.
            worker = YerelIsci(executable, ROOT / 'ses_servisi.py', baslatma_saniye=240, istek_saniye=240)
        name = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as f:
                name = f.name
                f.write(raw)
            try:
                result = worker.istek({'path': name, 'ipucu': ipucu})
            except ValueError:
                # İşçi öldüyse bir sonraki istek yeniden başlatabilsin.
                worker = None
                raise
            if result.get('error'):
                raise ValueError(result['error'])
            return str(result.get('text', '')).strip()
        finally:
            if name:
                try:
                    os.unlink(name)
                except OSError:
                    pass
