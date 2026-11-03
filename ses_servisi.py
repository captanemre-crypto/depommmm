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
print(json.dumps({'ready':True,'model':model_name}),flush=True)
for line in sys.stdin:
    try:
        req=json.loads(line)
        ipucu=str(req.get('ipucu') or '')[:300]
        kwargs=dict(language='tr',beam_size=5,temperature=0.0,condition_on_previous_text=False,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=700,speech_pad_ms=600),
                    no_speech_threshold=0.6,log_prob_threshold=-1.0,compression_ratio_threshold=2.4,
                    initial_prompt=('Türkçe konuşma. Kişisel asistan: defter, alacak, verecek, tahsilat, ödeme, '
                                    'hatırlatıcı, tutar, TL, tarih, saat. '+ipucu).strip())
        try:
            segments,_=model.transcribe(req['path'],**kwargs)
        except TypeError:
            # Eski faster-whisper sürümleri vad_parameters/initial_prompt almayabilir.
            segments,_=model.transcribe(req['path'],language='tr',beam_size=5,condition_on_previous_text=False)
        # Yineleyen segmentleri at (halüsinasyon) ve uzun cümleyi bölmeden birleştir.
        parcalar=[]; onceki=''
        for s in segments:
            t=' '.join(str(s.text or '').split())
            if not t or t.lower()==onceki.lower(): continue
            onceki=t; parcalar.append(t)
        text=' '.join(parcalar).strip()
        print(json.dumps({'text':text},ensure_ascii=True),flush=True)
    except Exception:
        log_error()
        print(json.dumps({'error':'Ses çözümlenemedi.'},ensure_ascii=True),flush=True)
