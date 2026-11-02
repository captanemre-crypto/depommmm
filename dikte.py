"""Canlı dikte için metin işleme yardımcıları.

Amaç: Whisper'ın kısa pencereler hâlinde ürettiği ham metni, kesintisiz ve
okunabilir bir dikte metnine dönüştürmek:

- `kaydir()`: üst üste binen pencerelerin tekrarını atar (kelime düzeyinde),
  yalnızca gerçekten yeni kelimeleri döndürür.
- `temizle()`: dolgu seslerini (ıı, eee, hmm, öhö) ve tekrarları atar.
- `bicimlendir()`: Türkçe büyük harf kuralları, noktalama ve boşluk düzeltmesi.
- `birlesik()`: kaydırılan metni önceki metinle birleştirip biçimlendirir.

Modül bilinçli olarak ağ erişimi yapmaz ve motor çalıştırmaz; bu yüzden
Windows olmayan ortamlarda da test edilebilir.
"""
import re

# Yalnızca anlam taşımayan sesler atılır. "yani", "işte", "şey" gibi sözcükler
# cümlenin anlamını değiştirebildiği için KORUNUR.
DOLGU = {
    'ıı', 'ııı', 'ıııı', 'ii', 'iii', 'eee', 'eeee', 'aaa', 'aaaa', 'hmm', 'hmmm', 'hm',
    'öhö', 'öhöm', 'ıh', 'ıhh', 'uh', 'uhh', 'efendim',
}
# Bunlar tek başına gelirse cümle başı sayılmaz; metne dokunulmaz.
KORUNAN = {'evet', 'hayır', 'tamam', 'peki', 'neden', 'nasıl', 'ne', 'kim', 'hangi'}

_SESLI = 'aeıioöuü'
_SESSIZ = 'bcçdfgğhjklmnprsştvyz'


def kelimeler(metin):
    return re.findall(r'\S+', str(metin or ''))


def kaydir(onceki, yeni):
    """`onceki` metninin sonu ile `yeni` metninin başı çakışıyorsa tekrarı atar.

    Dönen değer yalnızca eklenmesi gereken yeni kısımdır. Büyük/küçük harf ve
    noktalama karşılaştırmada yok sayılır; dönen metin `yeni` içindeki hâliyle
    kalır (Whisper'ın noktalaması korunur).
    """
    a = kelimeler(onceki)
    b = kelimeler(yeni)
    if not b:
        return ''
    if not a:
        return ' '.join(b)
    norm = lambda w: re.sub(r'[^\wçğıöşüÇĞİÖŞÜ]', '', w).lower()  # noqa: E731
    a_n = [norm(w) for w in a]
    b_n = [norm(w) for w in b]
    # En uzun çakışmayı ara (en fazla 12 kelime).
    for uzunluk in range(min(len(a_n), len(b_n), 12), 0, -1):
        if a_n[-uzunluk:] == b_n[:uzunluk]:
            return ' '.join(b[uzunluk:])
    # Tam çakışma yoksa: son kelime yarım kalmış olabilir; yeni metnin ilk kelimesi
    # öncekinin son kelimesinin uzantısıysa onu da at.
    if b_n and a_n and b_n[0] and a_n[-1].startswith(b_n[0][:max(3, len(b_n[0]) - 1)]) and b[0].lower() == a[-1].lower():
        return ' '.join(b[1:])
    return ' '.join(b)


def temizle(metin):
    """Dolgu seslerini, tekrarlanan kelimeleri ve fazla boşlukları atar."""
    parcalar = []
    for kelime in kelimeler(metin):
        sade = kelime.strip('.,;:!?…"\'()[]').lower()
        if sade in DOLGU:
            continue
        # Ardışık aynı kelimeyi tekilleştir (kekeleme): "ben ben ben" → "ben".
        if parcalar and parcalar[-1].lower() == kelime.lower():
            continue
        parcalar.append(kelime)
    return ' '.join(parcalar).strip()


def _buyuk_harf(kelime):
    """Türkçe kurallarına uygun ilk harf büyütme (i→İ, ı→I)."""
    if not kelime:
        return kelime
    ilk = kelime[0]
    if ilk == 'i':
        return 'İ' + kelime[1:]
    if ilk == 'ı':
        return 'I' + kelime[1:]
    return ilk.upper() + kelime[1:]


def son_buyuk(metin):
    """Cümle başlarını ve 'ben', 'sen' gibi zamirleri büyütür (yalnızca başta)."""
    metin = str(metin or '')
    if not metin:
        return metin
    # Cümle sonu noktalamasından sonra gelen ilk harf.
    metin = re.sub(r'([.!?…]\s+)([a-zçğıöşü])', lambda m: m.group(1) + _buyuk_harf(m.group(2)), metin)
    return _buyuk_harf(metin)


# Özel ada gelen tek heceli hâl ekleri kesme işaretiyle yazılır: "İstanbul'a".
_EK = ('nın', 'nin', 'nun', 'nün', 'dan', 'den', 'dan', 'tan', 'ten', 'da', 'de', 'ta', 'te',
       'ya', 'ye', 'na', 'ne', 'ın', 'in', 'un', 'ün', 'a', 'e', 'ı', 'i', 'u', 'ü')


def _kesme(metin):
    """Büyük harfle başlayan addan sonra gelen hâl ekine kesme işareti ekler."""
    def degistir(m):
        ad, ek = m.group(1), m.group(2)
        if not ad[:1].isupper() or len(ad) < 2:
            return m.group(0)
        if ek.lower() not in _EK:
            return m.group(0)
        # Ek, adın son harfiyle kaynaşmış olabilir (İstanbul+da); yine de kesme eklenir.
        return f"{ad}'{ek}"
    return re.sub(r'\b([A-ZÇĞİÖŞÜ][\wçğıöşü]{1,})(?:\s+)([a-zçğıöşü]{1,3})(?=\s|$|[.,;:!?])', degistir, metin)


SORU_SONU = {'mi', 'mı', 'mu', 'mü', 'misin', 'mısın', 'musun', 'müsün', 'miyiz', 'mıyız'}
SORU_KELIME = {'nasıl', 'neden', 'niye', 'niçin', 'nerede', 'nereye', 'nereden', 'kim', 'hangi', 'kaç'}


def soru_mu(metin):
    """Cümle soru mu? (son kelime 'mi/mı/mu/mü' ya da soru sözcüğü)"""
    k = [re.sub(r'[^\wçğıöşüÇĞİÖŞÜ]', '', w).lower() for w in kelimeler(metin)]
    if not k:
        return False
    if k[-1] in SORU_SONU or k[-2:-1] and k[-2] in SORU_SONU:
        return True
    return any(w in SORU_KELIME for w in k)


def bicimlendir(metin, bitir=True):
    """Noktalama ve boşluk düzeltmesi; `bitir` ise sonuna nokta/noktalama ekler."""
    metin = ' '.join(str(metin or '').split())
    if not metin:
        return ''
    # Noktalama öncesi boşlukları at, sonrasına tek boşluk koy.
    metin = re.sub(r'\s+([,.;:!?…])', r'\1', metin)
    metin = re.sub(r'([,;:])(?=\S)', r'\1 ', metin)
    metin = re.sub(r'([.!?…])(?=[^\s.!?…])', r'\1 ', metin)
    # Ünlem/soru işareti tekrarını sadeleştir.
    metin = re.sub(r'([!?])\1{1,}', r'\1', metin)
    # Türkçede kesme işareti ve kısaltma çevresi.
    metin = metin.replace(' ?', '?').replace(' !', '!').replace(' .', '.')
    metin = son_buyuk(metin)
    metin = _kesme(metin)
    if bitir and not re.search(r'[.!?…]$', metin):
        metin = metin.rstrip(',;:')
        metin += '?' if soru_mu(metin) else '.'
    return metin


def birlesik(onceki, yeni, bitir=False):
    """Kaydırılmış yeni parçayı önceki metne ekleyip biçimlendirir."""
    parca = kaydir(onceki, yeni)
    parca = temizle(parca)
    metin = (' '.join([str(onceki or '').strip(), parca]).strip()) if parca else str(onceki or '').strip()
    return bicimlendir(metin, bitir=bitir), parca


def ipucu(metin, uzunluk=120):
    """Whisper'a bağlam olarak verilecek kısa kuyruk (özel isimleri korur)."""
    kuyruk = ' '.join(kelimeler(metin)[-14:])
    return kuyruk[-uzunluk:]


def temiz_mi(metin):
    """Metin anlamlı mı? (yalnızca noktalama/dolgu ise False)"""
    harfler = re.sub(r'[^\wçğıöşüÇĞİÖŞÜ]', '', str(metin or ''))
    return len(harfler) >= 2
