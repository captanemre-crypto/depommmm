"""Örnek beceri: metin istatistikleri (yalnızca standart kütüphane)."""
import json
import re
import sys


def main():
    try:
        veri = json.loads(sys.stdin.read() or '{}')
    except ValueError:
        veri = {}
    metin = str(veri.get('metin') or '').strip()
    if not metin:
        print(json.dumps({'reply': 'Analiz için metin gerekli. Örnek: !metin-analiz bugün hava çok güzel.'},
                         ensure_ascii=False))
        return 0
    kelimeler = [k for k in re.split(r'\s+', metin) if k]
    cumleler = [c for c in re.split(r'[.!?]+', metin) if c.strip()]
    yanit = (f'{len(metin)} karakter, {len(kelimeler)} kelime, {len(cumleler)} cümle. '
             f'Ortalama kelime uzunluğu {sum(len(k) for k in kelimeler) / len(kelimeler):.1f} harf.')
    print(json.dumps({'reply': yanit}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
