"""Download and verify a better multilingual Whisper model; activate only on success."""
import json
from pathlib import Path
from faster_whisper import WhisperModel
root = Path(__file__).resolve().parent
print('Whisper small indiriliyor ve CPU üzerinde yükleniyor. Bu işlem biraz sürebilir.', flush=True)
WhisperModel('small', device='cpu', compute_type='int8', cpu_threads=4)
(root / 'whisper_ayar.json').write_text(json.dumps({'model': 'small'}), encoding='utf-8')
print('Whisper small hazır. Emre uygulamasını tamamen kapatıp yeniden başlatın.', flush=True)
