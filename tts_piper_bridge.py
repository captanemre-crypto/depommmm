import json,subprocess,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parent
lock=threading.Lock();worker=None

def installed(name):
    return name in ('dfki','fahrettin','fettah') and (ROOT/'.venv-ses'/'Scripts'/'python.exe').is_file() and (ROOT/'sesler'/f'tr_TR-{name}-medium.onnx').is_file() and (ROOT/'sesler'/f'tr_TR-{name}-medium.onnx.json').is_file()

def speak(text,path,name):
    global worker
    exe=ROOT/'.venv-ses'/'Scripts'/'python.exe'
    if not installed(name):raise ValueError('Ses modeli kurulu değil; ses_model_kur.bat dosyasını çalıştır.')
    with lock:
        if worker is None or worker.poll() is not None:
            worker=subprocess.Popen([str(exe),'-X','utf8','-u',str(ROOT/'tts_piper.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            try:ready=json.loads(worker.stdout.readline() or '{}')
            except ValueError:ready={}
            if not ready.get('ready'):raise ValueError(ready.get('error','Piper sesi başlatılamadı.'))
        worker.stdin.write(json.dumps({'path':path,'text':text,'voice':name},ensure_ascii=True)+'\n');worker.stdin.flush()
        try:r=json.loads(worker.stdout.readline() or '{}')
        except ValueError:raise ValueError('Piper geçersiz yanıt döndürdü.')
        if not r.get('ok'):raise ValueError(r.get('error','Piper sesi oluşturamadı.'))
