"""Persistent local Piper TTS worker; loads requested voice on CPU."""
import json
import sys
import wave
from pathlib import Path

try:
    from piper import PiperVoice
except Exception:
    print(json.dumps({'ready':False,'error':'Piper kurulu degil; ses_model_kur.bat dosyasini calistir.'}),flush=True)
    sys.exit(1)
print(json.dumps({'ready':True}),flush=True)
voices={};folder=Path(__file__).resolve().parent/'sesler'
for line in sys.stdin:
    try:
        req=json.loads(line);name=req.get('voice')
        if name not in ('dfki','fahrettin','fettah'):raise ValueError('Ses desteklenmiyor.')
        if name not in voices:voices[name]=PiperVoice.load(str(folder/f'tr_TR-{name}-medium.onnx'),use_cuda=False)
        with wave.open(req['path'],'wb') as output:voices[name].synthesize_wav(req['text'],output)
        print(json.dumps({'ok':True}),flush=True)
    except Exception:
        print(json.dumps({'error':'Piper sesi olusturulamadi; model dosyalarini ve kurulumu kontrol et.'}),flush=True)
