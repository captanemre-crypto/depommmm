"""Beceriler: kullanıcının kendi eklediği küçük yetenekler.

Her beceri `beceriler/<ad>/` klasörüdür ve en az bir `SKILL.md` içerir:

```
---
ad: metin-analiz
aciklama: Metnin kelime ve karakter sayısını verir
tetik: kelime say, karakter say, metni analiz et
komut: python calistir.py
---
Bu beceri yalnızca yerel olarak çalışır.
```

- `komut` verilmişse beceri bir **alt süreç** olarak çalıştırılır: JSON
  (`{"metin": "...", "beceri": "...", "klasor": "..."}`) stdin'e yazılır, stdout'tan
  JSON (`{"reply": "..."}`) veya düz metin okunur. Kabuk (shell) kullanılmaz.
- `komut` yoksa beceri yalnızca **açıklama**dır; modelin sistem isteminde listelenir,
  çalıştırılmaz.
- Güvenlik: ad `[a-z0-9_-]{1,40}`, en fazla 40 beceri, komut metni 300 karakter,
  alt süreç zaman aşımı 20 sn, çıktı 4000 karakterle sınırlı. Tehlikeli işlem yok:
  beceriler yalnızca senin yazdığın komutları çalıştırır ve her çalıştırma **onay** ister
  (arayüzde) — sohbet içinde yalnızca `!<ad>` ile açıkça istendiğinde çalışır.
"""
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KOK = ROOT / 'beceriler'
AZAMI_BECERI = 40
AZAMI_KOMUT = 300
AZAMI_KARAKTER = 4000
AZAMI_CIKTI = 200_000
ZAMAN_ASIMI = 20
AD_DESENI = re.compile(r'^[a-z0-9][a-z0-9_-]{0,39}$')


def _kok(kok=None) -> Path:
    return Path(kok) if kok else KOK


def _ayikla(yol: Path) -> dict:
    """SKILL.md dosyasını ayrıştırır: `---` arası anahtar: değer, kalanı açıklama."""
    ham = yol.read_text(encoding='utf-8', errors='replace')[:20_000]
    satirlar = ham.splitlines()
    veri = {}
    govde_baslangic = 0
    if satirlar and satirlar[0].strip() == '---':
        for i, satir in enumerate(satirlar[1:], 1):
            if satir.strip() == '---':
                govde_baslangic = i + 1
                break
            if ':' in satir:
                anahtar, _, deger = satir.partition(':')
                veri[anahtar.strip().lower()] = deger.strip()
    veri['govde'] = '\n'.join(satirlar[govde_baslangic:]).strip()
    return veri


def listele(kok=None) -> list:
    """Becerileri listeler; bozuk klasörler `hata` alanıyla döner."""
    kok = _kok(kok)
    if not kok.is_dir():
        return []
    beceriler = []
    for klasor in sorted(kok.iterdir())[:AZAMI_BECERI * 2]:
        if not klasor.is_dir() or klasor.name.startswith('.'):
            continue
        if not AD_DESENI.match(klasor.name):
            beceriler.append({'ad': klasor.name, 'hata': 'Klasör adı geçersiz (a-z, 0-9, -, _).'})
            continue
        dosya = klasor / 'SKILL.md'
        if not dosya.is_file():
            continue
        try:
            veri = _ayikla(dosya)
        except OSError as hata:
            beceriler.append({'ad': klasor.name, 'hata': f'SKILL.md okunamadı: {hata}'})
            continue
        komut = str(veri.get('komut') or '').strip()
        beceri = {
            'ad': str(veri.get('ad') or klasor.name).strip()[:60] or klasor.name,
            'klasor': klasor.name,
            'aciklama': str(veri.get('aciklama') or '').strip()[:300],
            'tetik': [t.strip() for t in re.split(r'[,;]', str(veri.get('tetik') or '')) if t.strip()][:20],
            'komut': komut[:AZAMI_KOMUT],
            'calistirilabilir': bool(komut),
            'ayrinti': str(veri.get('govde') or '')[:600],
        }
        if len(komut) > AZAMI_KOMUT:
            beceri['hata'] = 'Komut çok uzun.'
            beceri['calistirilabilir'] = False
        beceriler.append(beceri)
        if len(beceriler) >= AZAMI_BECERI:
            break
    return beceriler


def bul(ad, kok=None):
    """Ada göre tek bir beceri döndürür (yoksa None)."""
    ad = str(ad or '').strip().lower()
    if not AD_DESENI.match(ad):
        return None
    for beceri in listele(kok):
        if beceri.get('klasor') == ad or str(beceri.get('ad', '')).lower() == ad:
            return beceri
    return None


def esles(metin, kok=None):
    """Metinde geçen tetik sözcüklerine göre beceri önerir (en fazla 3)."""
    kucuk = ' '.join(str(metin or '').lower().split())[:500]
    if not kucuk:
        return []
    puanlar = []
    for beceri in listele(kok):
        if beceri.get('hata'):
            continue
        puan = sum(1 for t in beceri.get('tetik', []) if t.lower() in kucuk)
        if puan:
            puanlar.append((puan, beceri))
    puanlar.sort(key=lambda x: -x[0])
    return [b for _, b in puanlar[:3]]


def acik_komut(metin):
    """`!beceri-adı ...` biçimindeki açık çağrıyı çözer: (ad, kalan_metin) veya (None, metin)."""
    ham = str(metin or '').strip()
    if not ham.startswith('!'):
        return None, ham
    parca = ham[1:].split(None, 1)
    if not parca:
        return None, ham
    ad = parca[0].strip().lower().rstrip(':')
    if not AD_DESENI.match(ad):
        return None, ham
    return ad, (parca[1].strip() if len(parca) > 1 else '')


def baglam(kok=None):
    """Modelin sistem istemine eklenecek beceri listesi (yalnızca ad + açıklama)."""
    beceriler = [b for b in listele(kok) if not b.get('hata') and b.get('aciklama')]
    if not beceriler:
        return ''
    satirlar = ['Kullanıcının tanımladığı beceriler (yalnızca kullanıcı !<ad> yazarak çalıştırır; '
                'sen çalıştıramazsın, sadece önerebilirsin):']
    for beceri in beceriler[:10]:
        satirlar.append(f"- !{beceri['klasor']}: {beceri['aciklama']}")
    return '\n'.join(satirlar)


def _komut_calistir(komut: str, klasor: Path, veri: dict, zaman=ZAMAN_ASIMI) -> str:
    """Beceri komutunu kabuk kullanmadan çalıştırır ve çıktısını döndürür."""
    try:
        parcalar = shlex.split(komut, posix=(os.name != 'nt'))
    except ValueError as hata:
        raise ValueError(f'Beceri komutu ayrıştırılamadı: {hata}')
    if not parcalar:
        raise ValueError('Beceri komutu boş.')
    if parcalar[0].lower() in ('python', 'python3', 'py'):
        parcalar[0] = sys.executable
    try:
        sonuc = subprocess.run(parcalar, cwd=str(klasor), input=json.dumps(veri, ensure_ascii=False),
                               capture_output=True, text=True, timeout=zaman,
                               env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
    except subprocess.TimeoutExpired:
        raise ValueError(f'Beceri {zaman} saniyede bitmedi.')
    except FileNotFoundError:
        raise ValueError(f'Beceri komutu bulunamadı: {parcalar[0]}')
    except OSError as hata:
        raise ValueError(f'Beceri çalıştırılamadı: {hata}')
    cikti = (sonuc.stdout or '')[:AZAMI_CIKTI].strip()
    if sonuc.returncode != 0:
        ayrinti = (sonuc.stderr or cikti or '').strip()[:300]
        raise ValueError('Beceri hata verdi.' + (f' Ayrıntı: {ayrinti}' if ayrinti else ''))
    if not cikti:
        raise ValueError('Beceri boş yanıt döndürdü.')
    try:
        govde = json.loads(cikti)
    except ValueError:
        govde = None
    if isinstance(govde, dict) and 'reply' in govde:
        metin = str(govde.get('reply') or '')
    elif govde is not None and not isinstance(govde, dict):
        metin = str(govde)
    else:
        metin = cikti
    metin = metin.strip()
    if not metin:
        raise ValueError('Beceri boş yanıt döndürdü.')
    return metin[:AZAMI_KARAKTER]


def calistir(ad, metin='', kok=None, zaman=ZAMAN_ASIMI) -> dict:
    """Beceriyi çalıştırır: {'ad', 'reply', 'sure'} döndürür."""
    beceri = bul(ad, kok)
    if beceri is None:
        raise ValueError('Beceri bulunamadı: ' + str(ad)[:60])
    if beceri.get('hata'):
        raise ValueError(beceri['hata'])
    if not beceri.get('komut'):
        raise ValueError(f"“{beceri['ad']}” yalnızca açıklama içeriyor; komutu yok. SKILL.md dosyasına 'komut:' ekle.")
    klasor = _kok(kok) / beceri['klasor']
    veri = {'metin': str(metin or '')[:2000], 'beceri': beceri['klasor'], 'klasor': str(klasor)}
    import time
    basla = time.monotonic()
    reply = _komut_calistir(beceri['komut'], klasor, veri, zaman=zaman)
    return {'ad': beceri['ad'], 'klasor': beceri['klasor'], 'reply': reply,
            'sure': round(time.monotonic() - basla, 2)}
