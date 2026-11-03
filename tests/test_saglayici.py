"""OpenAI uyumlu sağlayıcı istemcisi testleri (sahte /v1 sunucusu, internet yok)."""
import json
import socket
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import saglayici  # noqa: E402

MODELLER = ['meta-llama/llama-3.3-70b-instruct:free', 'openai/gpt-oss-20b:free', 'some/paid-model']


class SahteSaglayici(BaseHTTPRequestHandler):
    kayitlar = []

    def log_message(self, *args):
        pass

    def _json(self, kod, govde):
        veri = json.dumps(govde).encode()
        self.send_response(kod)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(veri)))
        self.end_headers()
        self.wfile.write(veri)

    def do_GET(self):
        SahteSaglayici.kayitlar.append(('GET', self.path, dict(self.headers)))
        if self.path.endswith('/models'):
            if self.headers.get('Authorization') not in ('Bearer test-anahtar', None, ''):
                return self._json(401, {'error': {'message': 'invalid api key'}})
            return self._json(200, {'data': [{'id': m} for m in MODELLER]})
        self._json(404, {'error': 'yok'})

    def _akis(self, parcalar):
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
        self.send_header('Connection', 'close')
        self.end_headers()
        for parca in parcalar:
            self.wfile.write(('data: ' + json.dumps({'choices': [{'delta': {'content': parca}}]}) + '\n\n').encode())
            self.wfile.flush()
        self.wfile.write(b'data: [DONE]\n\n')
        self.wfile.flush()

    def do_POST(self):
        uzunluk = int(self.headers.get('Content-Length', '0'))
        govde = json.loads(self.rfile.read(uzunluk) or b'{}')
        if govde.get('model') == 'hata-model':
            return self._json(429, {'error': {'message': 'kota doldu'}})
        if govde.get('stream'):
            SahteSaglayici.kayitlar.append(('STREAM', self.path, dict(self.headers)))
            return self._akis(['Merhaba', ' dünya', '.'])
        SahteSaglayici.kayitlar.append(('POST', self.path, govde))
        if self.headers.get('Authorization') == 'Bearer gecersiz':
            return self._json(401, {'error': {'message': 'invalid api key'}})
        if govde.get('model') == 'kota-dolu':
            return self._json(429, {'error': {'message': 'rate limit exceeded'}})
        if govde.get('model') == 'tool-model':
            return self._json(200, {'choices': [{'message': {
                'role': 'assistant', 'content': None,
                'tool_calls': [{'id': '1', 'type': 'function',
                                'function': {'name': 'ledger_list', 'arguments': '{"person": "Ahmet"}'}}]}}]})
        return self._json(200, {'choices': [{'message': {'role': 'assistant', 'content': 'Merhaba, nasıl yardımcı olabilirim?'}}]})


class AnahtarIsteyenGecit(BaseHTTPRequestHandler):
    """9Router gibi davranır: /models için geçerli anahtar (Bearer sk_test) ister."""

    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.headers.get('Authorization') != 'Bearer sk_test':
            veri = b'{"error":{"message":"unauthorized"}}'
            self.send_response(401)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(veri)))
            self.end_headers()
            self.wfile.write(veri)
            return
        veri = json.dumps({'data': [{'id': 'kr/claude-sonnet-4.5'}, {'id': 'free-combo'}]}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(veri)))
        self.end_headers()
        self.wfile.write(veri)


class YedekBaslikGecidi(BaseHTTPRequestHandler):
    """Bilinen 9Router/OmniRoute hatası: /models Bearer ile çalışır,
    /chat/completions ise anahtarı yalnızca `x-api-key` başlığından okur."""

    def log_message(self, *args):
        pass

    def _json(self, kod, govde):
        veri = json.dumps(govde).encode()
        self.send_response(kod)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(veri)))
        self.end_headers()
        self.wfile.write(veri)

    def do_GET(self):
        if self.headers.get('Authorization') != 'Bearer sk_test':
            return self._json(401, {'error': {'message': 'unauthorized'}})
        self._json(200, {'data': [{'id': 'kr/claude-sonnet-4.5'}]})

    def do_POST(self):
        if self.headers.get('x-api-key') != 'sk_test':
            return self._json(401, {'error': {'message': '[401]: Missing API key.',
                                              'code': 'invalid_api_key'}})
        self._json(200, {'choices': [{'message': {'role': 'assistant', 'content': 'hazır'}}]})


class SaglayiciTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(('127.0.0.1', 0), SahteSaglayici)
        cls.port = cls.httpd.server_address[1]
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.base = f'http://127.0.0.1:{cls.port}/v1'

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sag = saglayici.Saglayici(Path(self.tmp.name) / 'ayar.json')
        SahteSaglayici.kayitlar.clear()

    def tearDown(self):
        self.tmp.cleanup()

    # --- adres doğrulama ---------------------------------------------------
    def test_local_http_allowed(self):
        self.assertEqual(saglayici.normalize_base('http://127.0.0.1:20128/v1'), 'http://127.0.0.1:20128/v1')
        self.assertEqual(saglayici.normalize_base('http://localhost:20128'), 'http://localhost:20128/v1')

    def test_remote_plain_http_rejected(self):
        with self.assertRaises(ValueError):
            saglayici.normalize_base('http://kotu-site.example/v1')

    def test_https_remote_allowed(self):
        self.assertEqual(saglayici.normalize_base('https://openrouter.ai/api/v1/'), 'https://openrouter.ai/api/v1')

    def test_credentials_in_url_rejected(self):
        with self.assertRaises(ValueError):
            saglayici.normalize_base('https://kullanici:anahtar@ornek.example/v1')

    # --- yapılandırma ------------------------------------------------------
    def test_save_and_mask_key(self):
        self.sag.kaydet(self.base, 'test-anahtar-1234', 'openai/gpt-oss-20b:free')
        durum = self.sag.durum()
        self.assertTrue(durum['configured'])
        self.assertEqual(durum['model'], 'openai/gpt-oss-20b:free')
        self.assertEqual(durum['key_hint'], '…1234')
        self.assertNotIn('test-anahtar-1234', json.dumps(durum))

    def test_saved_file_is_user_only(self):
        import os
        import stat
        self.sag.kaydet(self.base, 'abc12345', 'm')
        mod = stat.S_IMODE(os.stat(self.sag.yol).st_mode)
        self.assertEqual(mod, 0o600)

    def test_model_list_prefers_free(self):
        modeller = self.sag.modeller(base_url=self.base, key='test-anahtar')
        self.assertEqual(modeller[:2], ['meta-llama/llama-3.3-70b-instruct:free', 'openai/gpt-oss-20b:free'])
        self.assertIn('some/paid-model', modeller)

    def test_models_require_configuration(self):
        with self.assertRaises(ValueError):
            self.sag.modeller()

    # --- sohbet ------------------------------------------------------------
    def test_chat_returns_message(self):
        self.sag.kaydet(self.base, 'test-anahtar', 'openai/gpt-oss-20b:free')
        mesaj = self.sag.sohbet([{'role': 'user', 'content': 'selam'}])
        self.assertIn('Merhaba', mesaj['content'])

    def test_chat_passes_tools_and_model(self):
        self.sag.kaydet(self.base, 'test-anahtar', 'openai/gpt-oss-20b:free')
        self.sag.sohbet([{'role': 'user', 'content': 'x'}], tools=[{'type': 'function'}])
        gonderilen = [k for k in SahteSaglayici.kayitlar if k[0] == 'POST'][-1][2]
        self.assertEqual(gonderilen['model'], 'openai/gpt-oss-20b:free')
        self.assertEqual(gonderilen['tool_choice'], 'auto')
        self.assertIn('tools', gonderilen)

    def test_tool_call_arguments_readable(self):
        self.sag.kaydet(self.base, 'test-anahtar', 'tool-model')
        mesaj = self.sag.sohbet([{'role': 'user', 'content': 'Ahmet bakiyesi'}])
        cagri = mesaj['tool_calls'][0]['function']
        self.assertEqual(cagri['name'], 'ledger_list')
        self.assertEqual(json.loads(cagri['arguments'])['person'], 'Ahmet')

    def test_auth_error_is_turkish(self):
        self.sag.kaydet(self.base, 'gecersiz', 'm')
        with self.assertRaises(ValueError) as ctx:
            self.sag.sohbet([{'role': 'user', 'content': 'x'}])
        self.assertIn('401', str(ctx.exception))

    def test_missing_api_key_retries_with_x_api_key(self):
        httpd = ThreadingHTTPServer(('127.0.0.1', 0), YedekBaslikGecidi)
        port = httpd.server_address[1]
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            self.sag.kaydet(f'http://127.0.0.1:{port}/v1', 'sk_test', 'kr/claude-sonnet-4.5')
            cevap = self.sag.sohbet([{'role': 'user', 'content': 'selam'}])
            self.assertIn('hazır', cevap.get('content', ''))
        finally:
            httpd.shutdown()
            httpd.server_close()

    def test_auth_error_mentions_gateway_hint(self):
        self.sag.kaydet(self.base, 'gecersiz', 'm')
        with self.assertRaises(ValueError) as ctx:
            self.sag.sohbet([{'role': 'user', 'content': 'x'}])
        mesaj = str(ctx.exception)
        self.assertIn('401', mesaj)
        self.assertIn('9Router', mesaj)
        self.assertIn('Bağlantıyı test et', mesaj)

    def test_quota_error_explains_free_tier(self):
        self.sag.kaydet(self.base, 'test-anahtar', 'kota-dolu')
        with self.assertRaises(ValueError) as ctx:
            self.sag.sohbet([{'role': 'user', 'content': 'x'}])
        mesaj = str(ctx.exception)
        self.assertIn('429', mesaj)
        self.assertIn('kota', mesaj.lower())

    def test_unreachable_local_server_message(self):
        bos_port = 1
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            bos_port = s.getsockname()[1]
        self.sag.kaydet(f'http://127.0.0.1:{bos_port}/v1', '', 'm')
        with self.assertRaises(ValueError) as ctx:
            self.sag.sohbet([{'role': 'user', 'content': 'x'}])
        self.assertIn('OmniRoute', str(ctx.exception))

    # --- 9Router / yerel geçit taraması -----------------------------------
    def test_presets_include_9router(self):
        adlar = [p['ad'] for p in saglayici.HAZIR]
        adresler = [p['base_url'] for p in saglayici.HAZIR]
        self.assertTrue(any('9Router' in a for a in adlar))
        self.assertIn('http://127.0.0.1:20128/v1', adresler)
        self.assertIn('http://127.0.0.1:20130/v1', adresler)

    def test_scan_finds_local_gateway(self):
        sonuc = self.sag.tara(ek_portlar=[self.port], zaman=1)
        bulunan = [g for g in sonuc if g['base_url'].endswith(f':{self.port}/v1')]
        self.assertEqual(len(bulunan), 1)
        self.assertTrue(bulunan[0]['alive'])
        self.assertFalse(bulunan[0]['needs_key'])
        self.assertEqual(len(bulunan[0]['models']), len(MODELLER))

    def test_scan_marks_key_requiring_gateway(self):
        httpd = ThreadingHTTPServer(('127.0.0.1', 0), AnahtarIsteyenGecit)
        port = httpd.server_address[1]
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            sonuc = self.sag.tara(ek_portlar=[port], zaman=1)
            bulunan = [g for g in sonuc if g['port'] == port][0]
            self.assertTrue(bulunan['alive'], 'anahtar isteyen geçit de ayakta sayılmalı')
            self.assertTrue(bulunan['needs_key'])
        finally:
            httpd.shutdown()
            httpd.server_close()

    def test_scan_only_targets_loopback(self):
        sonuc = self.sag.tara(ek_portlar=['abc', 'http://kötü.example', 70000, -1, None], zaman=0.2)
        self.assertTrue(sonuc)
        for g in sonuc:
            self.assertTrue(g['base_url'].startswith('http://127.0.0.1:'), g['base_url'])
        self.assertEqual(len(sonuc), len(saglayici.YEREL_GECITLER))
        self.assertTrue(all(not g['alive'] for g in sonuc if g['port'] not in (self.port,)))

    def test_scan_sorts_alive_first(self):
        sonuc = self.sag.tara(ek_portlar=[self.port], zaman=1)
        self.assertTrue(sonuc[0]['alive'])
        self.assertTrue(all(not g['alive'] for g in sonuc[1:]))

    def test_missing_model_reports_clearly(self):
        self.sag.kaydet(self.base, 'test-anahtar', '')
        with self.assertRaises(ValueError) as ctx:
            self.sag.sohbet([{'role': 'user', 'content': 'x'}])
        self.assertIn('Model seçilmemiş', str(ctx.exception))



class AkisTest(unittest.TestCase):
    """SSE akışı: gerçek akış isteği, sahte /v1 sunucusuna karşı."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.httpd = ThreadingHTTPServer(('127.0.0.1', 0), SahteSaglayici)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.base = f'http://127.0.0.1:{cls.httpd.server_address[1]}/v1'

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.tmp.cleanup()

    def setUp(self):
        self.sag = saglayici.Saglayici(Path(self.tmp.name) / 'akis_ayar.json')
        self.sag.kaydet(self.base, 'test-anahtar', 'openai/gpt-oss-20b:free')

    def test_chunks_are_streamed_in_order(self):
        parcalar = list(self.sag.sohbet_akis([{'role': 'user', 'content': 'selam'}]))
        self.assertEqual(''.join(parcalar), 'Merhaba dünya.')

    def test_stream_requests_sse(self):
        list(self.sag.sohbet_akis([{'role': 'user', 'content': 'selam'}]))
        tur, yol, basliklar = [k for k in SahteSaglayici.kayitlar if k[0] == 'STREAM'][-1]
        self.assertEqual(basliklar.get('Accept'), 'text/event-stream')
        self.assertEqual(basliklar.get('Authorization'), 'Bearer test-anahtar')

    def test_http_error_is_translated(self):
        with self.assertRaises(ValueError) as ctx:
            list(self.sag.sohbet_akis([{'role': 'user', 'content': 'selam'}], model='hata-model'))
        self.assertIn('kota', str(ctx.exception).lower())

    def test_missing_model_rejected(self):
        bos = saglayici.Saglayici(Path(self.tmp.name) / 'bos_ayar.json')
        bos.kaydet(self.base, 'k', '')
        with self.assertRaises(ValueError):
            list(bos.sohbet_akis([{'role': 'user', 'content': 'x'}]))

    def test_unreachable_gateway_message(self):
        kapali = saglayici.Saglayici(Path(self.tmp.name) / 'kapali_ayar.json')
        kapali.kaydet('http://127.0.0.1:9/v1', 'k', 'model')
        with self.assertRaises(ValueError) as ctx:
            list(kapali.sohbet_akis([{'role': 'user', 'content': 'x'}]))
        self.assertIn('ulaşılamadı', str(ctx.exception))


class YedekModelTest(unittest.TestCase):
    """Kota/hız sınırında yedek modele geçiş."""

    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(('127.0.0.1', 0), SahteSaglayici)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.base = f'http://127.0.0.1:{cls.httpd.server_address[1]}/v1'

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.yol = Path(self.tmp.name) / 'ayar.json'
        self.sag = saglayici.Saglayici(self.yol)

    def tearDown(self):
        self.tmp.cleanup()

    def test_fallback_saved_and_read(self):
        self.sag.kaydet(self.base, 'k', 'openai/gpt-oss-20b:free', yedek='meta-llama/llama-3.3-70b-instruct:free')
        self.assertEqual(self.sag.yukle()['yedek'], 'meta-llama/llama-3.3-70b-instruct:free')
        self.assertEqual(self.sag.durum()['yedek'], 'meta-llama/llama-3.3-70b-instruct:free')

    def test_saving_without_fallback_preserves_existing(self):
        self.sag.kaydet(self.base, 'k', 'openai/gpt-oss-20b:free', yedek='X')
        self.sag.kaydet(self.base, 'k', 'openai/gpt-oss-20b:free')
        self.assertEqual(self.sag.yukle()['yedek'], 'X')

    def test_fallback_requires_provider(self):
        with self.assertRaises(ValueError):
            saglayici.Saglayici(Path(self.tmp.name) / 'bos.json').yedek_ayarla('X')

    def test_invalid_fallback_rejected(self):
        self.sag.kaydet(self.base, 'k', 'openai/gpt-oss-20b:free')
        with self.assertRaises(ValueError):
            self.sag.yedek_ayarla('kötü\nmodel')

    def test_quota_error_switches_to_fallback(self):
        self.sag.kaydet(self.base, 'k', 'hata-model', yedek='openai/gpt-oss-20b:free')
        # hata-model 429 döner, yedek model ise normal yanıt verir (akışsız yol).
        mesaj = self.sag.sohbet([{'role': 'user', 'content': 'selam'}])
        self.assertTrue(mesaj.get('content'))
        self.assertEqual(mesaj.get('_yedek_model'), 'openai/gpt-oss-20b:free')
        self.assertEqual(mesaj.get('_asil_model'), 'hata-model')

    def test_quota_error_without_fallback_raises(self):
        self.sag.kaydet(self.base, 'k', 'hata-model')
        with self.assertRaises(ValueError) as ctx:
            self.sag.sohbet([{'role': 'user', 'content': 'selam'}])
        self.assertIn('kota', str(ctx.exception).lower())

    def test_fallback_not_used_for_non_transient_errors(self):
        self.sag.kaydet('http://127.0.0.1:9/v1', 'k', 'model', yedek='başka-model')
        with self.assertRaises(ValueError) as ctx:
            self.sag.sohbet([{'role': 'user', 'content': 'selam'}])
        self.assertIn('ulaşılamadı', str(ctx.exception))

    def test_stream_switches_to_fallback_before_first_chunk(self):
        self.sag.kaydet(self.base, 'k', 'hata-model', yedek='openai/gpt-oss-20b:free')
        self.assertEqual(''.join(self.sag.sohbet_akis([{'role': 'user', 'content': 'x'}])), 'Merhaba dünya.')

    def test_gecici_hata_classification(self):
        self.assertTrue(saglayici.gecici_hata('Ücretsiz kota veya hız sınırı doldu (429).'))
        self.assertTrue(saglayici.gecici_hata('Sağlayıcı şu anda hizmet vermiyor (503).'))
        self.assertFalse(saglayici.gecici_hata('API anahtarı kabul edilmedi (401).'))
        self.assertFalse(saglayici.gecici_hata('Sağlayıcıya ulaşılamadı.'))

    def test_fallback_same_as_primary_not_retried(self):
        self.sag.kaydet(self.base, 'k', 'hata-model', yedek='hata-model')
        with self.assertRaises(ValueError):
            self.sag.sohbet([{'role': 'user', 'content': 'selam'}])

if __name__ == '__main__':
    unittest.main()
