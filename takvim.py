"""Takvim: yerel `.ics` dosyalarını **salt okunur** okur.

- Dosya açılmaz/çoğaltılmaz; yalnızca okunur. Etkinlik oluşturma veya silme yoktur.
- `VEVENT` blokları ayrıştırılır: `SUMMARY`, `DTSTART`, `DTEND`, `LOCATION`,
  `DESCRIPTION` (kısa). Tarih-saat biçimleri: `2026-11-05T14:00:00Z`,
  `20261105T140000`, tarih-only `20261105` ve `VALUE=DATE` desteklenir.
- Tekrarlayan etkinliklerde (`RRULE`) yalnızca **ilk** oluşum listelenir; arayüzde
  "tekrarlayan" olarak işaretlenir (basit ve öngörülebilir davranış).
- Ağdan abone olma (webcal) yoktur; yalnızca bilgisayarındaki dosyalar.
"""
import re
from datetime import datetime, timedelta
from pathlib import Path

AZAMI_BAYT = 8 * 1024 * 1024
AZAMI_ETKINLIK = 500


def _ac(satir):
    """ICS satır katlamasını çözer (satır başındaki boşluk devam demektir)."""
    return re.sub(r'\r?\n[ \t]', '', satir)


def _kacis(metin):
    return (str(metin or '')
            .replace('\\n', ' ').replace('\\N', ' ')
            .replace('\\,', ',').replace('\\;', ';').replace('\\\\', '\\').strip())


def _tarih(deger):
    """ICS tarih değerini datetime'a çevirir; anlaşılamazsa None."""
    deger = str(deger or '').strip()
    if not deger:
        return None
    # Parametreleri at: 20261105T140000Z, 2026-11-05T14:00:00Z, 20261105
    deger = deger.split(':')[-1] if deger.upper().startswith('TZID') else deger
    deger = deger.strip().rstrip('Z')
    for kalip in ('%Y%m%dT%H%M%S', '%Y-%m-%dT%H:%M:%S', '%Y%m%dT%H%M', '%Y-%m-%dT%H:%M', '%Y%m%d', '%Y-%m-%d'):
        try:
            return datetime.strptime(deger, kalip)
        except ValueError:
            continue
    return None


def _alanlar(blok):
    """VEVENT bloğundaki alanları toplar; DTSTART'ın TZID parametresini korur."""
    veri = {}
    for satir in blok.splitlines():
        if ':' not in satir:
            continue
        anahtar, _, deger = satir.partition(':')
        ad = anahtar.split(';')[0].strip().upper()
        if not ad or ad in veri:
            continue
        veri[ad] = deger.strip()
    return veri


def oku(ham_metin, kaynak=''):
    """ICS metninden etkinlik listesi çıkarır."""
    metin = _ac(str(ham_metin or ''))
    if 'BEGIN:VCALENDAR' not in metin.upper() and 'BEGIN:VEVENT' not in metin.upper():
        raise ValueError('Bu dosya bir takvim (.ics) dosyası değil.')
    etkinlikler = []
    for parca in re.split(r'(?i)BEGIN:VEVENT', metin)[1:]:
        blok = re.split(r'(?i)END:VEVENT', parca)[0]
        alan = _alanlar(blok)
        basla = _tarih(alan.get('DTSTART', ''))
        if basla is None:
            continue
        bitis = _tarih(alan.get('DTEND', ''))
        etkinlikler.append({
            'baslik': _kacis(alan.get('SUMMARY', ''))[:200] or '(başlıksız)',
            'basla': basla.isoformat(timespec='minutes'),
            'bitis': (bitis or (basla + timedelta(hours=1))).isoformat(timespec='minutes'),
            'yer': _kacis(alan.get('LOCATION', ''))[:120],
            'not': _kacis(alan.get('DESCRIPTION', ''))[:300],
            'tekrarli': bool(alan.get('RRULE')),
            'kaynak': str(kaynak or '')[:120],
        })
        if len(etkinlikler) >= AZAMI_ETKINLIK:
            break
    etkinlikler.sort(key=lambda e: e['basla'])
    return etkinlikler


def dosya_oku(yol):
    yol = Path(str(yol or '')).expanduser()
    if not yol.is_file():
        raise ValueError('Takvim dosyası bulunamadı: ' + str(yol))
    if yol.stat().st_size > AZAMI_BAYT:
        raise ValueError('Takvim dosyası çok büyük.')
    return oku(yol.read_text(encoding='utf-8', errors='replace'), kaynak=yol.name)


def klasor_oku(klasor):
    """Bir klasördeki tüm `.ics` dosyalarını okur (alt klasörlere inmez)."""
    kok = Path(str(klasor or '')).expanduser()
    if not kok.is_dir():
        raise ValueError('Takvim klasörü bulunamadı: ' + str(kok))
    hepsi = []
    for dosya in sorted(kok.glob('*.ics'))[:50]:
        try:
            hepsi.extend(dosya_oku(dosya))
        except ValueError:
            continue
    hepsi.sort(key=lambda e: e['basla'])
    return hepsi


def yolu_oku(yol):
    """Tek bir `.ics` dosyası veya bir klasörü okur."""
    hedef = Path(str(yol or '')).expanduser()
    if hedef.is_dir():
        return klasor_oku(hedef)
    return dosya_oku(hedef)


def yaklasan(etkinlikler, gun=7, simdi=None):
    """Önümüzdeki `gun` gün içindeki etkinlikler (bitenler hariç)."""
    simdi = simdi or datetime.now()
    bitis = simdi + timedelta(days=max(1, min(int(gun or 7), 365)))
    secili = []
    for etkinlik in etkinlikler:
        try:
            basla = datetime.fromisoformat(etkinlik['basla'])
            son = datetime.fromisoformat(etkinlik.get('bitis') or etkinlik['basla'])
        except ValueError:
            continue
        if son >= simdi and basla <= bitis:
            secili.append(etkinlik)
    return secili


def metin_ozet(etkinlikler, gun=7, simdi=None):
    """Etkinlikleri modele/seslendirmeye uygun kısa metne çevirir."""
    secili = yaklasan(etkinlikler, gun=gun, simdi=simdi)
    if not secili:
        return f'Önümüzdeki {gun} günde takvimde etkinlik yok.'
    satirlar = [f'Önümüzdeki {gun} günde {len(secili)} etkinlik var:']
    for etkinlik in secili[:20]:
        try:
            basla = datetime.fromisoformat(etkinlik['basla'])
            zaman = basla.strftime('%d.%m %H:%M')
        except ValueError:
            zaman = etkinlik['basla']
        ek = f" ({etkinlik['yer']})" if etkinlik.get('yer') else ''
        satirlar.append(f"- {zaman} · {etkinlik['baslik']}{ek}")
    return '\n'.join(satirlar)


def gerekiyor_mu(metin):
    """Metin takvim sorusu mu? (sohbette kural tabanlı yanıt için)"""
    kucuk = ' '.join(str(metin or '').lower().split())
    if not kucuk:
        return False
    anahtarlar = ('takvim', 'ajanda', 'toplantı var mı', 'randevu', 'etkinlik', 'programım')
    return any(a in kucuk for a in anahtarlar) and any(
        s in kucuk for s in ('ne var', 'neler var', 'göster', 'listele', 'bugün', 'yarın', 'bu hafta', 'var mı'))
