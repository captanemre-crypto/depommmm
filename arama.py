"""Web araması (ücretsiz, API anahtarı gerekmez).

Üç kaynak sırayla denenir; biri çalışmazsa diğerine geçilir:

1. **DuckDuckGo Lite** HTML sonuç sayfası (`lite.duckduckgo.com`) — başlık, adres, özet.
2. **DuckDuckGo Instant Answer API** — özet/ilgili konular.
3. **Türkçe Vikipedi** arama API'si — başlık + kısa özet.

Sınırlar (bilinçli):
- Yalnızca **https** adresler; yanıt boyutu ve süre sınırlı.
- Sonuçlar **yalnızca okunur**; sayfalar açılmaz, form gönderilmez, giriş yapılmaz.
- Kişisel veri gönderilmez; yalnızca kullanıcının yazdığı arama cümlesi gider (istemiyorsan
  `web_arama` ayarını kapat).
"""
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

AZAMI_SORGU = 200
AZAMI_SONUC = 5
AZAMI_BAYT = 600_000
ZAMAN_ASIMI = 8
TARAYICI = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')
DDG_LITE = 'https://lite.duckduckgo.com/lite/'
DDG_ANLIK = 'https://api.duckduckgo.com/'
VIKIPEDI = 'https://tr.wikipedia.org/w/api.php'

# Arama gerektiren kalıplar (dikkatli: her sohbeti web'e göndermemek için dar tutuldu).
_KOMUTLAR = re.compile(
    r'(?i)\b(araştır|internetten\s+(?:bak|ara|bul)|web.?de\s+(?:ara|bak)|'
    r'google.?da\s+ara|arama\s+yap|ara:\s*\S)')
_GUNCEL = re.compile(
    r'(?i)\b(güncel|son\s+dakika|bugün|şu\s+an|bu\s+hafta|bu\s+yıl|'
    r'hava\s+durumu|hava\s+nasıl|dolar\s+kaç|euro\s+kaç|kur\s+ne|fiyatı\s+ne|'
    r'kaç\s+tl|haber(?:ler)?|seçim|maç\s+sonucu|çıktı\s+mı|piyasaya\s+sürüldü)')
_KISI_KURUM = re.compile(
    r'(?i)\b(kimdir|kim\s+bu|nereli|hangi\s+(?:ülke|şehir|yıl)|'
    r'ne\s+zaman\s+(?:kurul|çık|başla|öl)|kaç\s+yaşında)')


def _istek(url: str) -> str:
    """https adresten sınırlı boyutta metin indirir."""
    if not str(url).lower().startswith('https://'):
        raise ValueError('Yalnızca https adreslerden arama yapılabilir.')
    istek = urllib.request.Request(url, headers={
        'User-Agent': TARAYICI,
        'Accept': 'text/html,application/json;q=0.9,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.5',
    })
    with urllib.request.urlopen(istek, timeout=ZAMAN_ASIMI) as yanit:
        ham = yanit.read(AZAMI_BAYT + 1)
    if len(ham) > AZAMI_BAYT:
        raise ValueError('Arama yanıtı çok büyük.')
    return ham.decode('utf-8', 'replace')


def temizle(metin: str, azami: int = 300) -> str:
    """HTML etiketlerini ve fazla boşlukları kaldırır."""
    metin = re.sub(r'<[^>]{0,200}>', ' ', str(metin or ''))
    metin = (metin.replace('&nbsp;', ' ').replace('&amp;', '&')
             .replace('&quot;', '"').replace('&#39;', "'").replace('&lt;', '<').replace('&gt;', '>'))
    return ' '.join(metin.split())[:azami]


class _LiteParser(HTMLParser):
    """DuckDuckGo Lite sonuç sayfasından başlık/adres/özet toplar."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.sonuclar = []
        self._aktif = None       # ('baslik'|'ozet', veri)
        self._son_baslik = None

    def handle_starttag(self, tag, attrs):
        if tag != 'a':
            return
        nitelik = dict(attrs)
        sinif = str(nitelik.get('class') or '')
        href = str(nitelik.get('href') or '')
        if 'result-link' in sinif and href:
            self._aktif = 'baslik'
            self._son_baslik = {'baslik': '', 'url': _temiz_url(href), 'ozet': ''}

    def handle_endtag(self, tag):
        if tag == 'a' and self._aktif == 'baslik':
            self._aktif = None
            if self._son_baslik and self._son_baslik['url']:
                self.sonuclar.append(self._son_baslik)

    def handle_data(self, veri):
        if self._aktif == 'baslik' and self._son_baslik is not None:
            self._son_baslik['baslik'] += veri

    def kapat(self):
        for sonuc in self.sonuclar:
            sonuc['baslik'] = temizle(sonuc['baslik'], 160) or sonuc['url']
        return self.sonuclar


class _OzetParser(HTMLParser):
    """`result-snippet` hücrelerindeki özetleri sırayla toplar."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ozetler = []
        self._icinde = False

    def handle_starttag(self, tag, attrs):
        if tag == 'td' and 'result-snippet' in str(dict(attrs).get('class') or ''):
            self._icinde = True
            self.ozetler.append('')

    def handle_endtag(self, tag):
        if tag == 'td' and self._icinde:
            self._icinde = False

    def handle_data(self, veri):
        if self._icinde and self.ozetler:
            self.ozetler[-1] += veri


def _temiz_url(url: str) -> str:
    """DuckDuckGo yönlendirme adresini gerçek adrese çevirir; https olmayanı atar."""
    url = str(url or '').strip()
    if url.startswith('//'):
        url = 'https:' + url
    if 'duckduckgo.com/l/' in url:
        sorgu = urllib.parse.urlparse(url).query
        hedef = urllib.parse.parse_qs(sorgu).get('uddg', [''])[0]
        if hedef:
            url = hedef
    return url if url.lower().startswith('https://') else ''


def _ddg_lite(sorgu: str):
    sayfa = _istek(DDG_LITE + '?' + urllib.parse.urlencode({'q': sorgu, 'kl': 'tr-tr'}))
    parser = _LiteParser()
    parser.feed(sayfa)
    sonuclar = parser.kapat()
    ozet = _OzetParser()
    ozet.feed(sayfa)
    temiz_ozetler = [temizle(o) for o in ozet.ozetler if temizle(o)]
    for i, sonuc in enumerate(sonuclar[:AZAMI_SONUC]):
        if i < len(temiz_ozetler):
            sonuc['ozet'] = temiz_ozetler[i]
    return sonuclar[:AZAMI_SONUC]


def _ddg_anlik(sorgu: str):
    veri = _istek(DDG_ANLIK + '?' + urllib.parse.urlencode(
        {'q': sorgu, 'format': 'json', 'no_html': '1', 'skip_disambig': '1'}))
    govde = json.loads(veri)
    sonuclar = []
    if govde.get('AbstractText'):
        sonuclar.append({'baslik': govde.get('Heading') or sorgu,
                         'url': govde.get('AbstractURL') or '',
                         'ozet': temizle(govde['AbstractText'])})
    for konu in (govde.get('RelatedTopics') or [])[:AZAMI_SONUC]:
        if not isinstance(konu, dict):
            continue
        metin = konu.get('Text')
        adres = konu.get('FirstURL')
        if metin and str(adres or '').lower().startswith('https://'):
            sonuclar.append({'baslik': temizle(metin, 90), 'url': adres, 'ozet': temizle(metin)})
    return sonuclar[:AZAMI_SONUC]


def _vikipedi(sorgu: str):
    veri = _istek(VIKIPEDI + '?' + urllib.parse.urlencode({
        'action': 'query', 'list': 'search', 'srsearch': sorgu, 'srlimit': AZAMI_SONUC,
        'format': 'json', 'utf8': '1'}))
    govde = json.loads(veri)
    sonuclar = []
    for madde in ((govde.get('query') or {}).get('search') or [])[:AZAMI_SONUC]:
        baslik = str(madde.get('title') or '').strip()
        if not baslik:
            continue
        sonuclar.append({'baslik': baslik,
                         'url': 'https://tr.wikipedia.org/wiki/' + urllib.parse.quote(baslik.replace(' ', '_')),
                         'ozet': temizle(madde.get('snippet') or '')})
    return sonuclar


def _tekillestir(sonuclar):
    gorulen = set()
    temiz = []
    for sonuc in sonuclar:
        adres = str(sonuc.get('url') or '')
        if not adres.lower().startswith('https://') or adres in gorulen:
            continue
        gorulen.add(adres)
        temiz.append({'baslik': temizle(sonuc.get('baslik'), 160) or adres,
                      'url': adres, 'ozet': temizle(sonuc.get('ozet'), 400)})
        if len(temiz) >= AZAMI_SONUC:
            break
    return temiz


def ara(sorgu: str, adet: int = AZAMI_SONUC):
    """Web'de arar; sonuç yoksa boş liste döner (hata fırlatmaz)."""
    sorgu = ' '.join(str(sorgu or '').split())[:AZAMI_SORGU]
    if not sorgu:
        return []
    adet = max(1, min(int(adet or AZAMI_SONUC), AZAMI_SONUC))
    sonuclar = []
    for kaynak in (_ddg_lite, _ddg_anlik, _vikipedi):
        try:
            sonuclar = _tekillestir(sonuclar + list(kaynak(sorgu) or []))
        except (urllib.error.URLError, TimeoutError, ValueError, OSError, json.JSONDecodeError):
            continue
        if len(sonuclar) >= adet:
            break
    return sonuclar[:adet]


def gerekiyor_mu(metin: str) -> bool:
    """Bu cümle için web araması yapılmalı mı? (dar ve öngörülebilir)"""
    metin = ' '.join(str(metin or '').split())[:500]
    if len(metin) < 3:
        return False
    if _KOMUTLAR.search(metin):
        return True
    if _KISI_KURUM.search(metin):
        return True
    return bool(_GUNCEL.search(metin))


def baglam(sonuclar) -> str:
    """Sonuçları modelin sistem istemine eklenecek kısa metne çevirir."""
    if not sonuclar:
        return ''
    satirlar = ['Web arama sonuçları (yalnızca aşağıdaki bilgilere dayan; emin değilsen belirt):']
    for i, sonuc in enumerate(sonuclar, 1):
        ozet = sonuc.get('ozet') or ''
        satirlar.append(f'{i}. {sonuc.get("baslik","")} — {sonuc.get("url","")}' + (f' — {ozet}' if ozet else ''))
    satirlar.append('Yanıtta kullandığın bilgilerin sonuna [1], [2] gibi kaynak numarası ekle. '
                    'Bu sonuçlarda olmayan güncel bilgi uydurma.')
    return '\n'.join(satirlar)
