"""OpenAI uyumlu sağlayıcı istemcisi (9Router, OmniRoute, OpenRouter, Groq, Gemini…).

Emre'nin yerel model zorunluluğunu kaldırır: `/v1/chat/completions` sunan her
servis (kendi bilgisayarında çalışan OmniRoute gateway'i, OpenRouter'ın `:free`
modelleri, Groq, Cerebras vb.) tek bir yapılandırmayla kullanılabilir.

Güvenlik notları
- API anahtarı **yalnızca sunucuda** tutulur (`saglayici_ayar.json`, izin 0600)
  ve arayüze asla tam olarak dönmez; yalnızca son 4 karakteri gösterilir.
- Anahtar düz metin gitmesin diye `http://` yalnızca loopback adreslerinde
  (127.0.0.1 / localhost / ::1) kabul edilir; uzak adresler `https://` olmalıdır.
- `tara()` yalnızca **kendi bilgisayarındaki** bilinen geçit portlarını yoklar
  (adres kullanıcıdan alınmaz, hep 127.0.0.1 kullanılır).
"""
import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
AYAR_DOSYASI = ROOT / 'saglayici_ayar.json'
LOOPBACK = {'127.0.0.1', 'localhost', '::1', '0.0.0.0'}

# `tara()` yalnızca bu portları ve yalnızca 127.0.0.1 adresini dener.
YEREL_GECITLER = (
    {'port': 20128, 'ad': '9Router / OmniRoute / FlagshipRouter', 'yol': '/v1',
     'not': 'Bu portu üç geçit de varsayılan olarak kullanır; aynı anda yalnızca biri çalışabilir.'},
    {'port': 20130, 'ad': '9Router Go', 'yol': '/v1', 'not': 'Go ile yazılmış tek dosyalık sürüm.'},
    {'port': 11434, 'ad': 'Ollama (OpenAI uyumlu)', 'yol': '/v1', 'not': 'Yerel modeller; anahtar gerekmez.'},
    {'port': 1234, 'ad': 'LM Studio', 'yol': '/v1', 'not': 'LM Studio sunucusu açıksa kullanılabilir.'},
    {'port': 8080, 'ad': 'llama.cpp / vLLM', 'yol': '/v1', 'not': 'Yerel çıkarım sunucusu.'},
    {'port': 8787, 'ad': 'Yerel yardımcı geçit', 'yol': '/v1', 'not': 'Sidecar/yardımcı sağlayıcı adaptörleri.'},
)

# Hazır seçenekler: arayüzde açılır liste olarak gösterilir.
HAZIR = (
    {'ad': '9Router (yerel gateway)', 'base_url': 'http://127.0.0.1:20128/v1',
     'not': '9router.com — kendi bilgisayarında OpenAI uyumlu /v1 açar. Panelden '
            '(http://localhost:20128/dashboard) bir API anahtarı oluşturup buraya yapıştır; '
            'model adı kr/claude-sonnet-4.5 ya da kendi oluşturduğun combo (ör. free-combo) olabilir.'},
    {'ad': '9Router Go (tek dosya sürüm)', 'base_url': 'http://127.0.0.1:20130/v1',
     'not': '9router-go portu 20130; panelden aldığın anahtarı gir. 9Router ile aynı model adlarını kullanır.'},
    {'ad': 'OmniRoute (yerel gateway)', 'base_url': 'http://127.0.0.1:20128/v1',
     'not': 'npm i -g omniroute ile kurulur; kendi bilgisayarında /v1 açar. Anahtar gerekmez.'},
    {'ad': 'OpenRouter', 'base_url': 'https://openrouter.ai/api/v1',
     'not': 'openrouter.ai/keys adresinden ücretsiz anahtar; kimliği ":free" ile biten modeller ücretsizdir.'},
    {'ad': 'Groq', 'base_url': 'https://api.groq.com/openai/v1',
     'not': 'console.groq.com — ücretsiz katman, çok hızlı Llama/Gemma modelleri.'},
    {'ad': 'Cerebras', 'base_url': 'https://api.cerebras.ai/v1',
     'not': 'inference.cerebras.ai — ücretsiz günlük kota.'},
    {'ad': 'Google Gemini (OpenAI uyumlu)', 'base_url': 'https://generativelanguage.googleapis.com/v1beta/openai',
     'not': 'aistudio.google.com — ücretsiz katman; model adı gemini-2.5-flash gibi yazılır.'},
)


def normalize_base(url):
    """Taban adresi doğrular ve normalleştirir."""
    url = (url or '').strip()
    if not url:
        raise ValueError('Sunucu adresi gerekli.')
    if len(url) > 300:
        raise ValueError('Sunucu adresi çok uzun.')
    if '@' in url.split('://', 1)[-1].split('/', 1)[0]:
        raise ValueError('Adresin içine anahtar yazmayın; anahtarı ayrı alana girin.')
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        raise ValueError('Adres http:// veya https:// ile başlamalı.')
    if parsed.scheme == 'http' and parsed.hostname not in LOOPBACK:
        raise ValueError('Uzak adreslerde https:// gerekir; anahtar şifresiz gönderilmez.')
    temiz = url.rstrip('/')
    if not temiz.endswith('/v1') and '/v1/' not in temiz:
        temiz += '/v1'
    return temiz


def _json_deneme(metin):
    """Metni JSON'a çevirmeyi dener; olmazsa None döner."""
    try:
        return json.loads(metin)
    except (ValueError, TypeError):
        return None


def _anahtar_eksik(govde, metin=''):
    """Yanıt “anahtar yok/geçersiz” diyor mu? (geçit sürüm farkları için)"""
    parca = ''
    if isinstance(govde, dict):
        hata = govde.get('error')
        if isinstance(hata, dict):
            parca = ' '.join(str(hata.get(k) or '') for k in ('message', 'code', 'type'))
        elif isinstance(hata, str):
            parca = hata
    parca = (parca + ' ' + (metin or '')).lower()
    return 'missing api key' in parca or 'no api key' in parca or 'invalid_api_key' in parca


class Saglayici:
    def __init__(self, ayar_dosyasi=AYAR_DOSYASI):
        self.yol = Path(ayar_dosyasi)

    # --- yapılandırma ------------------------------------------------------
    def yukle(self):
        try:
            veri = json.loads(self.yol.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return {'base_url': '', 'key': '', 'model': ''}
        if not isinstance(veri, dict):
            return {'base_url': '', 'key': '', 'model': ''}
        return {'base_url': str(veri.get('base_url') or ''), 'key': str(veri.get('key') or ''),
                'model': str(veri.get('model') or '')}

    def kaydet(self, base_url, key, model):
        base_url = normalize_base(base_url)
        key = (key or '').strip()
        if len(key) > 400 or '\n' in key or '\r' in key:
            raise ValueError('API anahtarı geçersiz.')
        model = (model or '').strip()
        if len(model) > 200 or (model and not all(k not in model for k in '\n\r\t')):
            raise ValueError('Model adı geçersiz.')
        veri = {'base_url': base_url, 'key': key, 'model': model,
                'guncelleme': datetime.now().isoformat(timespec='seconds')}
        gecici = self.yol.with_suffix('.tmp')
        gecici.write_text(json.dumps(veri, ensure_ascii=False, indent=2), encoding='utf-8')
        try:
            os.chmod(gecici, 0o600)  # yalnızca kullanıcı okuyabilsin
        except OSError:
            pass
        gecici.replace(self.yol)
        return veri

    def sil(self):
        try:
            self.yol.unlink()
        except FileNotFoundError:
            pass

    def tara(self, ek_portlar=None, zaman=0.8):
        """Kendi bilgisayarındaki bilinen OpenAI uyumlu geçitleri yoklar.

        Adres hiçbir zaman kullanıcıdan gelmez: her deneme
        `http://127.0.0.1:<port>/v1/models` biçimindedir. `ek_portlar` yalnızca
        ek port numarası ekler (testler ve özel kurulumlar için).
        """
        from concurrent.futures import ThreadPoolExecutor

        hedefler = [dict(g) for g in YEREL_GECITLER]
        for ham in (ek_portlar or []):
            try:
                port = int(ham)
            except (TypeError, ValueError):
                continue
            if not 1 <= port <= 65535 or any(g['port'] == port for g in hedefler):
                continue
            hedefler.append({'port': port, 'ad': f'Yerel geçit (port {port})', 'yol': '/v1',
                             'not': 'Elle eklenen yerel adres.'})

        def _dene(hedef):
            adres = f"http://127.0.0.1:{hedef['port']}{hedef['yol']}"
            sonuc = {'ad': hedef['ad'], 'base_url': adres, 'port': hedef['port'],
                     'alive': False, 'needs_key': False, 'models': [], 'note': hedef['not']}
            istek = urllib.request.Request(adres + '/models',
                                           headers={'Accept': 'application/json'})
            try:
                with urllib.request.urlopen(istek, timeout=zaman) as yanit:
                    govde = json.loads(yanit.read().decode('utf-8', 'replace') or '{}')
            except urllib.error.HTTPError as hata:
                # 401/403: sunucu ayakta ama anahtar istiyor (9Router böyle davranır).
                sonuc['alive'] = hata.code in (401, 403)
                sonuc['needs_key'] = sonuc['alive']
                if not sonuc['alive']:
                    sonuc['error'] = f'HTTP {hata.code}'
                return sonuc
            except (urllib.error.URLError, TimeoutError, OSError):
                return sonuc
            except ValueError:
                sonuc['alive'] = True
                sonuc['error'] = '/models JSON döndürmedi'
                return sonuc
            sonuc['alive'] = True
            ham = govde.get('data') if isinstance(govde, dict) else None
            adlar = []
            for item in (ham or []):
                if isinstance(item, dict) and item.get('id'):
                    adlar.append(str(item['id']))
                elif isinstance(item, str):
                    adlar.append(item)
            sonuc['models'] = sorted(set(adlar), key=str.lower)[:40]
            return sonuc

        with ThreadPoolExecutor(max_workers=min(8, len(hedefler))) as havuz:
            sonuclar = list(havuz.map(_dene, hedefler))
        sonuclar.sort(key=lambda s: (not s['alive'], s['port']))
        return sonuclar

    def durum(self):
        """Arayüze dönen özet: anahtar asla tam gönderilmez."""
        veri = self.yukle()
        key = veri['key']
        return {
            'configured': bool(veri['base_url']),
            'base_url': veri['base_url'],
            'model': veri['model'],
            'key_hint': ('…' + key[-4:]) if len(key) >= 4 else ('ayarlı' if key else ''),
            'presets': [dict(p) for p in HAZIR],
        }

    # --- HTTP --------------------------------------------------------------
    def _istek(self, yol, payload=None, timeout=60, ayar=None):
        ayar = ayar or self.yukle()
        if not ayar['base_url']:
            raise ValueError('Ücretsiz API sağlayıcısı ayarlanmamış. Ayarlar > Ücretsiz API bölümünden bağlan.')
        url = ayar['base_url'].rstrip('/') + yol
        data = json.dumps(payload).encode('utf-8') if payload is not None else None
        basliklar = {'Accept': 'application/json'}
        if data is not None:
            basliklar['Content-Type'] = 'application/json'
        if ayar['key']:
            basliklar['Authorization'] = 'Bearer ' + ayar['key']
        try:
            return self._gonder(url, data, basliklar, timeout)
        except urllib.error.HTTPError as hata:
            metin = hata.read().decode('utf-8', 'replace')
            govde = _json_deneme(metin)
            # Bilinen geçit hatası: bazı 9Router/OmniRoute sürümleri
            # `/v1/chat/completions` çağrısında anahtarı yalnızca `x-api-key`
            # başlığından okuyor ("401: Missing API key"); `/v1/models` ise
            # `Authorization: Bearer` ile çalışıyor. Bir kez yedek başlıkla dene.
            if ayar['key'] and 'x-api-key' not in basliklar and _anahtar_eksik(govde, metin):
                yedek = dict(basliklar)
                yedek['x-api-key'] = ayar['key']
                try:
                    return self._gonder(url, data, yedek, timeout)
                except urllib.error.HTTPError as hata2:
                    metin2 = hata2.read().decode('utf-8', 'replace')
                    raise ValueError(self._http_mesaji(hata2.code, _json_deneme(metin2), metin2))
                except urllib.error.URLError:
                    raise ValueError(self._ulasilamadi(ayar))
                except TimeoutError:
                    raise ValueError('Sağlayıcı zamanında yanıt vermedi; tekrar dene.')
            raise ValueError(self._http_mesaji(hata.code, govde, metin))
        except urllib.error.URLError:
            raise ValueError(self._ulasilamadi(ayar))
        except TimeoutError:
            raise ValueError('Sağlayıcı zamanında yanıt vermedi; tekrar dene.')

    def _gonder(self, url, data, basliklar, timeout):
        """Tek HTTP denemesi; JSON döndürür (hatalar çağırana HTTPError olarak gider)."""
        istek = urllib.request.Request(url, data=data, headers=basliklar, method='POST' if data else 'GET')
        with urllib.request.urlopen(istek, timeout=timeout) as yanit:
            metin = yanit.read().decode('utf-8', 'replace')
        try:
            return json.loads(metin)
        except ValueError:
            raise ValueError('Sağlayıcı JSON olmayan bir yanıt döndürdü. Adres /v1 ile bitiyor mu?')

    @staticmethod
    def _ulasilamadi(ayar):
        if ayar['base_url'].startswith('http://127.0.0.1') or 'localhost' in ayar['base_url']:
            return ('Yerel API sunucusuna ulaşılamadı. 9Router/OmniRoute çalışıyor mu? '
                    '(9Router varsayılan: http://127.0.0.1:20128/v1, 9Router Go: '
                    'http://127.0.0.1:20130/v1). Ayarlar > Ücretsiz API > '
                    '“Yerel geçitleri tara” ile açık olanı bulabilirsin.')
        return 'Sağlayıcıya ulaşılamadı. Adresi ve internet bağlantısını kontrol et.'

    @staticmethod
    def _http_mesaji(kod, govde=None, metin=''):
        ayrinti = ''
        if isinstance(govde, dict):
            hata_alani = govde.get('error')
            if isinstance(hata_alani, dict):
                ayrinti = str(hata_alani.get('message') or hata_alani.get('msg') or '')
            elif isinstance(hata_alani, str):
                ayrinti = hata_alani
            elif govde.get('message'):
                ayrinti = str(govde['message'])
        elif isinstance(govde, list):
            ayrinti = ''
        if not ayrinti:
            ayrinti = (metin or '').strip()[:160]
        ayrinti = ayrinti[:160]
        kod = int(kod)
        temel = {401: 'API anahtarı kabul edilmedi (401).',
                 402: 'Kota veya kredi yetersiz (402).',
                 403: 'Bu anahtarın bu modele erişimi yok (403).',
                 404: 'Adres veya model bulunamadı (404). Adresin /v1 ile bittiğini kontrol et.',
                 408: 'Sağlayıcı zaman aşımına uğradı (408).',
                 422: 'İstek biçimi sağlayıcı tarafından reddedildi (422).',
                 429: 'Ücretsiz kota veya hız sınırı doldu (429). Biraz bekleyip tekrar dene ya da başka bir model seç.',
                 500: 'Sağlayıcı iç hatası (500).',
                 502: 'Sağlayıcı geçit hatası (502).',
                 503: 'Sağlayıcı şu anda hizmet vermiyor (503).'}.get(kod, f'Sağlayıcı isteği başarısız (HTTP {kod}).')
        ipucu = ''
        if kod == 401:
            ipucu = (' İpucu: anahtarı 9Router panelinden (API Keys) yeniden kopyala; anahtarın '
                     '“tüm modeller” izni olduğundan emin ol. 9Router/OmniRoute’un bilinen bir hatasında '
                     '“Missing API key” yalnızca sohbet ucunda çıkar: geçidi yeniden başlatmak, başka bir '
                     'model seçmek veya OpenRouter/Groq gibi doğrudan bir sağlayıcı kullanmak çözer. '
                     'Ayarlar > Ücretsiz API > “Bağlantıyı test et” düğmesi ayrıntıyı gösterir.')
        return temel + ipucu + ((' Ayrıntı: ' + ayrinti) if ayrinti else '')

    # --- işlemler ----------------------------------------------------------
    def modeller(self, base_url=None, key=None, timeout=25):
        """`/v1/models` listesini döndürür; ücretsiz modeller önce gelir."""
        ayar = self.yukle()
        if base_url: ayar['base_url'] = normalize_base(base_url)
        if key is not None: ayar['key'] = key.strip()
        yanit = self._istek('/models', timeout=timeout, ayar=ayar)
        ham = yanit.get('data') if isinstance(yanit, dict) else None
        adlar = []
        for item in (ham or []):
            if isinstance(item, dict) and item.get('id'):
                adlar.append(str(item['id']))
            elif isinstance(item, str):
                adlar.append(item)
        adlar = sorted(set(adlar), key=lambda a: (0 if 'free' in a.lower() else 1, a.lower()))
        return adlar

    def sohbet(self, messages, model=None, tools=None, max_tokens=500, timeout=120):
        ayar = self.yukle()
        model = (model or ayar['model'] or '').strip()
        if not model:
            raise ValueError('Model seçilmemiş. Ayarlar > Ücretsiz API bölümünden bir model seç.')
        payload = {'model': model, 'messages': messages, 'max_tokens': max_tokens, 'stream': False}
        if tools:
            payload['tools'] = tools
            payload['tool_choice'] = 'auto'
        yanit = self._istek('/chat/completions', payload, timeout=timeout, ayar=ayar)
        secenekler = yanit.get('choices') if isinstance(yanit, dict) else None
        if not secenekler:
            # Bazı sağlayıcılar hata durumunu 200 ile gövdede bildirir.
            hata = yanit.get('error') if isinstance(yanit, dict) else None
            if hata:
                raise ValueError('Sağlayıcı hata döndürdü: ' + str(hata)[:200])
            raise ValueError('Sağlayıcı yanıtında mesaj bulunamadı.')
        mesaj = (secenekler[0] or {}).get('message') or {}
        if not isinstance(mesaj, dict):
            raise ValueError('Sağlayıcı beklenmeyen bir yanıt biçimi döndürdü.')
        return mesaj
