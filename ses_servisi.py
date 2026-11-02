"""Long-lived local Whisper worker. One JSON request/response per line."""
import json
import sys
import traceback
from pathlib import Path


def log_error():
    try:
        with (Path(__file__).resolve().parent / "ses_hata.log").open("a", encoding="utf-8") as f:
            traceback.print_exc(file=f)
    except OSError:
        pass
try:
    from faster_whisper import WhisperModel
    config_path = Path(__file__).resolve().parent / 'whisper_ayar.json'
    model_name = 'base'
    if config_path.exists():
        settings = json.loads(config_path.read_text(encoding='utf-8'))
        if settings.get('model') in ('base', 'small'):
            model_name = settings['model']
    model=WhisperModel(model_name,device='cpu',compute_type='int8',local_files_only=True,cpu_threads=4)
except Exception:
    log_error()
    print(json.dumps({'ready':False,'error':'Yerel ses modeli yüklenemedi. ses_kur.bat ile kurulumu tamamla.'}),flush=True)
    sys.exit(1)
print(json.dumps({'ready':True}),flush=True)
for line in sys.stdin:
    try:
        req=json.loads(line)
        segments,_=model.transcribe(req['path'],language='tr',beam_size=3,vad_filter=True,condition_on_previous_text=False)
        text=' '.join(s.text.strip() for s in segments).strip()
        print(json.dumps({'text':text},ensure_ascii=True),flush=True)
    except Exception:
        log_error()
        print(json.dumps({'error':'Ses çözümlenemedi.'},ensure_ascii=True),flush=True)
