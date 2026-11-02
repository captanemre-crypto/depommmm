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

    def do_POST(self):
        uzunluk = int(self.headers.get('Content-Length', '0'))
        govde = json.loads(self.rfile.read(uzunluk) or b'{}')
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

    def test_missing_model_reports_clearly(self):
        self.sag.kaydet(self.base, 'test-anahtar', '')
        with self.assertRaises(ValueError) as ctx:
            self.sag.sohbet([{'role': 'user', 'content': 'x'}])
        self.assertIn('Model seçilmemiş', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
