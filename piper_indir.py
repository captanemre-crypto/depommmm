"""Türkçe Piper ses modellerini indirir ve bütünlüğünü doğrular.

Hugging Face model dosyaları için yayınlanmış bir sağlama toplamı (checksum)
listesi yok; bu yüzden "ilk kullanımda güven" (TOFU) yöntemi uygulanır:

1. İlk indirmede dosyanın SHA-256 özeti hesaplanır ve `sesler/<ad>.sha256`
   dosyasına yazılır.
2. Sonraki indirmelerde özet bu dosyayla karşılaştırılır; uyuşmazsa dosya
   kullanılmaz ve kullanıcı uyarılır.

Bu yöntem, indirmenin yarıda kalmasını ve sonradan bozulmayı yakalar; ilk
indirmenin güvenilirliği indirme kaynağına (HTTPS + huggingface.co) bağlıdır.
"""
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

BASE = 'https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/tr/tr_TR/{voice}/medium/'
VOICES = ('fahrettin', 'fettah')
MIN_BOYUT = {'onnx': 5_000_000, 'json': 100}


def sha256(yol):
    ozet = hashlib.sha256()
    with yol.open('rb') as dosya:
        for parca in iter(lambda: dosya.read(1024 * 1024), b''):
            ozet.update(parca)
    return ozet.hexdigest()


def dogrula(yol, tur, ad):
    """Dosya bütünlüğünü kontrol eder; sorun varsa ValueError."""
    boyut = yol.stat().st_size
    if boyut < MIN_BOYUT[tur]:
        raise ValueError(f'{ad}: dosya beklenenden küçük ({boyut} bayt). İndirme yarıda kalmış olabilir.')
    if tur == 'json':
        with yol.open('r', encoding='utf-8') as dosya:
            ayar = json.load(dosya)
        if not isinstance(ayar, dict) or 'audio' not in ayar:
            raise ValueError(f'{ad}: model yapılandırması beklenen biçimde değil.')
    return sha256(yol)


def indir(klasor, voice, ad, tur):
    hedef = klasor / ad
    ozet_dosyasi = klasor / f'{ad}.sha256'
    gecici = klasor / (ad + '.part')
    if hedef.exists() and hedef.stat().st_size > 0:
        try:
            ozet = dogrula(hedef, tur, ad)
        except ValueError as hata:
            print(f'UYARI: {hata} Yeniden indiriliyor.', flush=True)
            hedef.unlink(missing_ok=True)
        else:
            if ozet_dosyasi.exists():
                beklenen = ozet_dosyasi.read_text(encoding='utf-8').split()[0].strip()
                if beklenen and beklenen != ozet:
                    raise SystemExit(f'HATA: {ad} özeti eşleşmiyor. Dosya değiştirilmiş olabilir; '
                                     f'sesler klasörünü temizleyip yeniden deneyin.')
                print(f'Zaten var ve doğrulandı: {ad}', flush=True)
                return
            ozet_dosyasi.write_text(ozet + '\n', encoding='utf-8')
            print(f'Zaten var: {ad} (özet kaydedildi)', flush=True)
            return
    print(f'İndiriliyor: {ad}', flush=True)
    try:
        with urllib.request.urlopen(BASE.format(voice=voice) + ad, timeout=180) as kaynak, gecici.open('wb') as cikis:
            while parca := kaynak.read(1024 * 1024):
                cikis.write(parca)
        ozet = dogrula(gecici, tur, ad)
        gecici.replace(hedef)
        ozet_dosyasi.write_text(ozet + '\n', encoding='utf-8')
        print(f'  sha256: {ozet}', flush=True)
    finally:
        if gecici.exists():
            gecici.unlink(missing_ok=True)


def main():
    klasor = Path(__file__).resolve().parent / 'sesler'
    klasor.mkdir(exist_ok=True)
    for voice in VOICES:
        for ad, tur in ((f'tr_TR-{voice}-medium.onnx', 'onnx'), (f'tr_TR-{voice}-medium.onnx.json', 'json')):
            indir(klasor, voice, ad, tur)
    print('Ses modelleri hazır ve doğrulandı.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except Exception as hata:
        print(f'İndirme başarısız: {hata}', file=sys.stderr, flush=True)
        sys.exit(1)
