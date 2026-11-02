"""Local speech worker bridge with bounded audio and serialized requests."""
import os,json,subprocess,threading,tempfile,base64
from pathlib import Path
ROOT=Path(__file__).resolve().parent
lock=threading.Lock()
worker=None

def transcribe(encoded):
    global worker
    if not isinstance(encoded,str) or len(encoded)>8_000_000: raise ValueError('Ses verisi çok büyük.')
    try: raw=base64.b64decode(encoded,validate=True)
    except Exception: raise ValueError('Ses verisi geçersiz.')
    if not 100< len(raw)<=5_000_000: raise ValueError('Ses verisi boş veya çok büyük.')
    executable=ROOT/'.venv-ses'/'Scripts'/'python.exe'
    if not executable.is_file(): raise ValueError('Yerel ses kurulu değil. ses_kur.bat dosyasını çalıştır.')
    with lock:
        if worker is None or worker.poll() is not None:
            worker=subprocess.Popen([str(executable),'-X','utf8','-u',str(ROOT/'ses_servisi.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            ready=json.loads(worker.stdout.readline() or '{}')
            if not ready.get('ready'): raise ValueError(ready.get('error','Yerel ses başlatılamadı.'))
        name=None
        try:
            with tempfile.NamedTemporaryFile(suffix='.webm',delete=False) as f:
                name=f.name; f.write(raw)
            worker.stdin.write(json.dumps({'path':name})+'\n');worker.stdin.flush()
            result=json.loads(worker.stdout.readline() or '{}')
            if result.get('error'): raise ValueError(result['error'])
            return str(result.get('text','')).strip()
        finally:
            if name:
                try: os.unlink(name)
                except OSError: pass
