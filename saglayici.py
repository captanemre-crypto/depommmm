"""OpenAI uyumlu sağlayıcı istemcisi (OmniRoute, OpenRouter, Groq, Gemini…).

Emre'nin yerel model zorunluluğunu kaldırır: `/v1/chat/completions` sunan her
servis (kendi bilgisayarında çalışan OmniRoute gateway'i, OpenRouter'ın `:free`
modelleri, Groq, Cerebras vb.) tek bir yapılandırmayla kullanılabilir.

Güvenlik notları
- API anahtarı **yalnızca sunucuda** tutulur (`saglayici_ayar.json`, izin 0600)
  ve arayüze asla tam olarak dönmez; yalnızca son 4 karakteri gösterilir.
- Anahtar düz metin gitmesin diye `http://` yalnızca loopback adreslerinde
  (127.0.0.1 / localhost / ::1) kabul edilir; uzak adresler `https://` olmalıdır.
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

# Hazır seçenekler: arayüzde açılır liste olarak gösterilir.
HAZIR = (
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
        istek = urllib.request.Request(url, data=data, headers=basliklar, method='POST' if data else 'GET')
        try:
            with urllib.request.urlopen(istek, timeout=timeout) as yanit:
                metin = yanit.read().decode('utf-8', 'replace')
        except urllib.error.HTTPError as hata:
            raise ValueError(self._http_mesaji(hata))
        except urllib.error.URLError:
            if ayar['base_url'].startswith('http://127.0.0.1') or 'localhost' in ayar['base_url']:
                raise ValueError('Yerel API sunucusuna ulaşılamadı. OmniRoute çalışıyor mu? '
                                 '(npm i -g omniroute, ardından varsayılan adres http://127.0.0.1:20128/v1)')
            raise ValueError('Sağlayıcıya ulaşılamadı. Adresi ve internet bağlantısını kontrol et.')
        except TimeoutError:
            raise ValueError('Sağlayıcı zamanında yanıt vermedi; tekrar dene.')
        try:
            return json.loads(metin)
        except ValueError:
            raise ValueError('Sağlayıcı JSON olmayan bir yanıt döndürdü. Adres /v1 ile bitiyor mu?')

    @staticmethod
    def _http_mesaji(hata):
        try:
            govde = json.loads(hata.read().decode('utf-8', 'replace'))
            ayrinti = ''
            if isinstance(govde, dict):
                hata_alani = govde.get('error')
                if isinstance(hata_alani, dict):
                    ayrinti = str(hata_alani.get('message') or '')
                elif isinstance(hata_alani, str):
                    ayrinti = hata_alani
            ayrinti = ayrinti[:160]
        except Exception:
            ayrinti = ''
        temel = {401: 'API anahtarı kabul edilmedi (401).',
                 402: 'Kota veya kredi yetersiz (402).',
                 403: 'Bu anahtarın bu modele erişimi yok (403).',
                 404: 'Adres veya model bulunamadı (404). Adresin /v1 ile bittiğini kontrol et.',
                 408: 'Sağlayıcı zaman aşımına uğradı (408).',
                 422: 'İstek biçimi sağlayıcı tarafından reddedildi (422).',
                 429: 'Ücretsiz kota veya hız sınırı doldu (429). Biraz bekleyip tekrar dene ya da başka bir model seç.',
                 500: 'Sağlayıcı iç hatası (500).',
                 502: 'Sağlayıcı geçit hatası (502).',
                 503: 'Sağlayıcı şu anda hizmet vermiyor (503).'}.get(hata.code, f'Sağlayıcı isteği başarısız (HTTP {hata.code}).')
        return temel + ((' Ayrıntı: ' + ayrinti) if ayrinti else '')

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
