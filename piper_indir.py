"""Download two Turkish Piper voice models into this project."""
from pathlib import Path
import urllib.request
folder=Path(__file__).resolve().parent/'sesler';folder.mkdir(exist_ok=True)
for voice in ('fahrettin','fettah'):
    base=f'https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/tr/tr_TR/{voice}/medium/'
    for name in (f'tr_TR-{voice}-medium.onnx',f'tr_TR-{voice}-medium.onnx.json'):
        target=folder/name; tmp=folder/(name+'.part')
        if target.exists() and target.stat().st_size>0:
            print(f'Zaten var: {name}',flush=True);continue
        print(f'Indiriliyor: {name}',flush=True)
        try:
            with urllib.request.urlopen(base+name,timeout=120) as src,tmp.open('wb') as out:
                while chunk:=src.read(1024*1024):out.write(chunk)
            tmp.replace(target)
        finally:
            if tmp.exists():tmp.unlink()
print('Ses modelleri indirildi.',flush=True)
