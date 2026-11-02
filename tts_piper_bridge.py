import threading
from pathlib import Path

from yerel_isci import YerelIsci

ROOT = Path(__file__).resolve().parent
lock = threading.Lock()
worker = None
VOICES = ('dfki', 'fahrettin', 'fettah')


def installed(name):
    return (name in VOICES
            and (ROOT / '.venv-ses' / 'Scripts' / 'python.exe').is_file()
            and (ROOT / 'sesler' / f'tr_TR-{name}-medium.onnx').is_file()
            and (ROOT / 'sesler' / f'tr_TR-{name}-medium.onnx.json').is_file())


def speak(text, path, name):
    global worker
    exe = ROOT / '.venv-ses' / 'Scripts' / 'python.exe'
    if not installed(name):
        raise ValueError('Ses modeli kurulu değil; ses_model_kur.bat dosyasını çalıştır.')
    with lock:
        if worker is None:
            # İlk istekte model CPU'ya yüklenir; soğuk başlangıç yavaş olabilir.
            worker = YerelIsci(exe, ROOT / 'tts_piper.py', baslatma_saniye=180, istek_saniye=180)
        r = worker.istek({'path': path, 'text': text, 'voice': name})
        if not r.get('ok'):
            raise ValueError(r.get('error') or 'Piper sesi oluşturamadı.')
