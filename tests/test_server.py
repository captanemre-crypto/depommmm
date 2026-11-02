"""HTTP arayüzü testleri: yetkilendirme, doğrulama, defter/hatırlatıcı akışı.

Sunucu rastgele bir portta, geçici bir veritabanıyla ayağa kaldırılır; testler
gerçek Emre veritabanına (emre.sqlite3) dokunmaz.
"""
import json
import sqlite3
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import saglayici  # noqa: E402
import server  # noqa: E402


class SahteSaglayici(BaseHTTPRequestHandler):
    """Testler için OpenAI uyumlu küçük sunucu."""

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
        if self.path.endswith('/models'):
            return self._json(200, {'data': [{'id': 'openai/gpt-oss-20b:free'}, {'id': 'tool-model'}]})
        self._json(404, {'error': 'yok'})

    def do_POST(self):
        n = int(self.headers.get('Content-Length', '0'))
        govde = json.loads(self.rfile.read(n) or b'{}')
        if govde.get('model') == 'tool-model':
            return self._json(200, {'choices': [{'message': {
                'role': 'assistant', 'content': None,
                'tool_calls': [{'id': '1', 'type': 'function',
                                'function': {'name': 'ledger_list', 'arguments': '{"person": "Araç Kişi"}'}}]}}]})
        return self._json(200, {'choices': [{'message': {'role': 'assistant', 'content': 'Sağlayıcı yanıtı: merhaba!'}}]})


class ServerTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_key = server.KEY
        server.KEY = 'test-anahtar'
        cls.httpd = server.EmreServer(('127.0.0.1', 0), server.Handler)
        cls.port = cls.httpd.server_address[1]
        cls.base = f'http://127.0.0.1:{cls.port}'
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        # Sahte OpenAI uyumlu sağlayıcı
        cls.sag_httpd = ThreadingHTTPServer(('127.0.0.1', 0), SahteSaglayici)
        cls.provider_base = f'http://127.0.0.1:{cls.sag_httpd.server_address[1]}/v1'
        threading.Thread(target=cls.sag_httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.sag_httpd.shutdown()
        cls.sag_httpd.server_close()
        server.KEY = cls.original_key

    def setUp(self):
        # Her test kendi geçici veritabanıyla çalışır: testler birbirinin
        # kayıtlarını görmez (mükerrer hesap kontrolü yüzünden önemli).
        self.tmp = tempfile.TemporaryDirectory()
        self.original_db = server.DB
        self.original_sag = server.SAG
        server.DB = Path(self.tmp.name) / 'test.sqlite3'
        server.SAG = saglayici.Saglayici(Path(self.tmp.name) / 'saglayici_ayar.json')

    def tearDown(self):
        server.DB = self.original_db
        server.SAG = self.original_sag
        self.tmp.cleanup()

    def raw(self, path, data=None, token='test-anahtar', origin=None, method=None):
        body = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(self.base + path, data=body, method=method or ('POST' if body else 'GET'))
        req.add_header('Content-Type', 'application/json')
        if token is not None:
            req.add_header('X-Emre-Token', token)
        if origin:
            req.add_header('Origin', origin)
        try:
            with urllib.request.urlopen(req, timeout=15) as res:
                payload = res.read()
                ctype = res.headers.get('Content-Type', '')
                return res.status, (json.loads(payload) if 'json' in ctype else payload), ctype
        except urllib.error.HTTPError as exc:
            payload = exc.read()
            try:
                return exc.code, json.loads(payload), exc.headers.get('Content-Type', '')
            except ValueError:
                return exc.code, payload, exc.headers.get('Content-Type', '')

    def api(self, path, data=None, expect=200, **kwargs):
        status, payload, _ = self.raw(path, data, **kwargs)
        self.assertEqual(status, expect, msg=f'{path} -> {status}: {payload}')
        return payload

    # --- yetkilendirme -----------------------------------------------------
    def test_token_required(self):
        self.api('/api/ledger', token=None, expect=403)

    def test_wrong_token_rejected(self):
        self.api('/api/ledger', token='yanlis', expect=403)

    def test_foreign_host_header_rejected(self):
        """DNS rebinding: saldırgan alan adıyla gelen istek reddedilmeli."""
        import socket
        raw = (b'GET /api/ledger HTTP/1.1\r\nHost: kotu-site.example\r\n'
               b'X-Emre-Token: test-anahtar\r\nConnection: close\r\n\r\n')
        with socket.create_connection(('127.0.0.1', self.port), timeout=10) as sock:
            sock.sendall(raw)
            data = sock.recv(4096)
        self.assertIn(b' 403 ', data.split(b'\r\n')[0] + b' ')

    def test_security_headers_present(self):
        req = urllib.request.Request(self.base + '/api/ledger')
        req.add_header('X-Emre-Token', 'test-anahtar')
        with urllib.request.urlopen(req, timeout=10) as res:
            self.assertEqual(res.headers.get('X-Frame-Options'), 'DENY')
            self.assertEqual(res.headers.get('X-Content-Type-Options'), 'nosniff')

    def test_foreign_origin_rejected(self):
        self.api('/api/ledger', origin='http://kotu-site.example', expect=403)

    def test_local_origin_allowed(self):
        self.api('/api/ledger', origin='http://127.0.0.1:8765')

    def test_index_page_injects_token(self):
        status, body, ctype = self.raw('/', token=None)
        self.assertEqual(status, 200)
        self.assertIn('text/html', ctype)
        self.assertIn(b'meta name="emre-token" content="test-anahtar"', body)

    def test_favicon_served(self):
        status, body, ctype = self.raw('/favicon.ico', token=None)
        self.assertEqual(status, 200)
        self.assertIn('image/x-icon', ctype)
        self.assertTrue(len(body) > 100)

    def test_unknown_route_404(self):
        self.api('/api/bilinmeyen', expect=404)

    # --- durum -------------------------------------------------------------
    def test_status_payload_fields(self):
        data = self.api('/api/status')
        for key in ('ollama', 'model', 'models', 'telegram_configured', 'version', 'speech_installed',
                    'piper_installed', 'openjarvis_online', 'arena_status', 'apps_supported', 'internet_access'):
            self.assertIn(key, data)

    # --- defter ------------------------------------------------------------
    def test_ledger_flow(self):
        self.api('/api/accounts', {'name': 'Test Kişi', 'note': 'deneme'})
        self.api('/api/ledger', {'person': 'Test Kişi', 'kind': 'receivable', 'amount': 12345,
                                 'note': 'borç', 'due': '', 'remind': False})
        entries = self.api('/api/ledger')['entries']
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['amount'], 12345)
        self.api('/api/ledger/delete', {'id': entries[0]['id'], 'confirmed': True})
        self.assertEqual(self.api('/api/ledger')['entries'], [])

    def test_ledger_delete_requires_confirmation(self):
        self.api('/api/ledger', {'person': 'Test Kişi', 'kind': 'payable', 'amount': 500})
        entry_id = self.api('/api/ledger')['entries'][0]['id']
        self.api('/api/ledger/delete', {'id': entry_id}, expect=400)
        self.assertEqual(len(self.api('/api/ledger')['entries']), 1)
        self.api('/api/ledger/delete', {'id': entry_id, 'confirmed': True})

    def test_ledger_rejects_string_amount(self):
        error = self.api('/api/ledger', {'person': 'A', 'kind': 'receivable', 'amount': '100'}, expect=400)
        self.assertIn('tutar', error['error'].lower())

    def test_ledger_rejects_non_text_person(self):
        error = self.api('/api/ledger', {'person': ['A'], 'kind': 'receivable', 'amount': 100}, expect=400)
        self.assertIn('metin', error['error'].lower())

    def test_ledger_rejects_unknown_kind(self):
        self.api('/api/ledger', {'person': 'A', 'kind': 'hediye', 'amount': 100}, expect=400)

    def test_account_delete_cascades_entries(self):
        self.api('/api/accounts', {'name': 'Silinecek'})
        self.api('/api/ledger', {'person': 'Silinecek', 'kind': 'payable', 'amount': 800})
        result = self.api('/api/accounts/delete', {'name': 'Silinecek', 'confirmed': True})
        self.assertEqual(result['deleted_entries'], 1)
        self.assertEqual(self.api('/api/ledger')['entries'], [])

    # --- hatırlatıcılar ----------------------------------------------------
    def test_reminder_flow(self):
        self.api('/api/reminders', {'text': 'Su iç', 'due': '2030-01-01T09:00'})
        reminders = self.api('/api/reminders')['reminders']
        self.assertTrue(any(r['text'] == 'Su iç' for r in reminders))
        target = next(r for r in reminders if r['text'] == 'Su iç')
        self.api('/api/reminders/done', {'id': target['id']})
        updated = next(r for r in self.api('/api/reminders')['reminders'] if r['id'] == target['id'])
        self.assertTrue(updated['done'])

    def test_reminder_rejects_bad_date(self):
        error = self.api('/api/reminders', {'text': 'x', 'due': 'yarın sabah'}, expect=400)
        self.assertIn('Tarih', error['error'])

    def test_duplicate_account_rejected_with_turkish_message(self):
        self.api('/api/accounts', {'name': 'İlker'})
        error = self.api('/api/accounts', {'name': 'ilker'}, expect=400)['error']
        self.assertIn('zaten var', error)
        self.assertNotIn('UNIQUE', error)

    def test_reminder_delete(self):
        self.api('/api/reminders', {'text': 'Silinecek', 'due': '2030-02-02T10:00'})
        reminder = next(r for r in self.api('/api/reminders')['reminders'] if r['text'] == 'Silinecek')
        self.api('/api/reminders/delete', {'id': reminder['id']}, expect=400)
        self.api('/api/reminders/delete', {'id': reminder['id'], 'confirmed': True})
        self.assertFalse(any(r['id'] == reminder['id'] for r in self.api('/api/reminders')['reminders']))

    # --- hatırlatıcı (sohbetten, Ollama olmadan) ----------------------------
    def test_chat_creates_reminder_without_ollama(self):
        cevap = self.api('/api/chat', {'messages': [{'role': 'user', 'content': 'yarın 09:00 su iç diye hatırlat'}],
                                       'session': 'test-oturum'})
        self.assertIn('Hatırlatıcı kuruldu', cevap['reply'])
        kayitlar = self.api('/api/reminders')['reminders']
        self.assertTrue(any(r['text'] == 'su iç' for r in kayitlar))

    def test_chat_history_is_stored(self):
        self.api('/api/chat', {'messages': [{'role': 'user', 'content': 'yarın 10:00 test diye hatırlat'}],
                               'session': 'gecmis-1'})
        oturumlar = self.api('/api/history')['sessions']
        self.assertTrue(any(o['session'] == 'gecmis-1' for o in oturumlar))
        detay = self.api('/api/history?session=gecmis-1')
        self.assertEqual(detay['messages'][0]['role'], 'user')
        self.assertGreaterEqual(len(detay['messages']), 2)
        silinen = self.api('/api/history/delete', {'session': 'gecmis-1', 'confirmed': True})
        self.assertGreaterEqual(silinen['deleted'], 2)

    # --- dışa aktarma ------------------------------------------------------
    def test_csv_export(self):
        self.api('/api/ledger', {'person': 'Dışa Kişi', 'kind': 'receivable', 'amount': 125075})
        status, body, ctype = self.raw('/api/ledger/export?format=csv')
        self.assertEqual(status, 200)
        self.assertIn('text/csv', ctype)
        self.assertTrue(body.startswith(b'\xef\xbb\xbf'), 'CSV BOM ile başlamalı (Excel/Türkçe)')
        metin = body.decode('utf-8-sig')
        self.assertIn('Dışa Kişi', metin)
        self.assertIn('1.250,75', metin)

    def test_backup_contains_all_tables(self):
        status, veri, ctype = self.raw('/api/backup')
        self.assertEqual(status, 200)
        if isinstance(veri, (bytes, str)):
            veri = json.loads(veri)
        for anahtar in ('accounts', 'ledger', 'reminders', 'messages', 'surum'):
            self.assertIn(anahtar, veri)

    def test_ledger_pagination(self):
        for i in range(3):
            self.api('/api/ledger', {'person': 'Sayfa', 'kind': 'payable', 'amount': 100 + i})
        veri = self.api('/api/ledger?limit=1&offset=0')
        self.assertEqual(len(veri['entries']), 1)
        self.assertGreaterEqual(veri['total'], 3)
        self.api('/api/ledger?limit=abc', expect=400)

    # --- telegram arka planı ----------------------------------------------
    def test_telegram_inbox_requires_token(self):
        self.api('/api/telegram/updates', expect=400)
        self.api('/api/telegram/poll', {}, expect=400)
        durum = self.api('/api/status')['telegram']
        self.assertFalse(durum['configured'])

    # --- güvenlik başlıkları ----------------------------------------------
    def test_csp_header_present(self):
        req = urllib.request.Request(self.base + '/')
        with urllib.request.urlopen(req, timeout=10) as res:
            csp = res.headers.get('Content-Security-Policy', '')
            self.assertIn("default-src 'self'", csp)
            self.assertIn("frame-ancestors 'none'", csp)

    # --- ücretsiz API sağlayıcısı -----------------------------------------
    def test_provider_status_hides_key(self):
        server.SAG.kaydet(self.provider_base, 'gizli-anahtar-9876', 'openai/gpt-oss-20b:free')
        durum = self.api('/api/provider/status')
        self.assertTrue(durum['configured'])
        self.assertEqual(durum['key_hint'], '…9876')
        self.assertNotIn('gizli-anahtar-9876', json.dumps(durum))
        self.assertIn('presets', durum)

    def test_provider_models_listing(self):
        veri = self.api('/api/provider/models', {'base_url': self.provider_base, 'key': 'test'})
        self.assertIn('openai/gpt-oss-20b:free', veri['models'])
        self.assertTrue(all('free' in m for m in veri['free']))

    def test_provider_connect_requires_confirmation(self):
        self.api('/api/provider/connect', {'base_url': self.provider_base, 'model': 'openai/gpt-oss-20b:free'}, expect=400)
        self.assertFalse(self.api('/api/provider/status')['configured'])

    def test_provider_connect_rejects_unknown_model(self):
        self.api('/api/provider/connect', {'base_url': self.provider_base, 'model': 'yok/boyle-model',
                                           'confirmed': True}, expect=400)
        self.assertFalse(self.api('/api/provider/status')['configured'])

    def test_provider_connect_and_disconnect(self):
        veri = self.api('/api/provider/connect', {'base_url': self.provider_base, 'key': 'test',
                                                  'model': 'openai/gpt-oss-20b:free', 'confirmed': True})
        self.assertTrue(veri['status']['configured'])
        self.assertTrue(self.api('/api/provider/status')['configured'])
        self.api('/api/provider/disconnect', {'confirmed': True})
        self.assertFalse(self.api('/api/provider/status')['configured'])

    # --- canlı dikte -------------------------------------------------------
    def test_dictate_window_merges_overlapping_windows(self):
        import ses_baglanti
        metinler = ['yarın saat üçte toplantı', 'saat üçte toplantı var', 'toplantı var ve fatura']
        with mock.patch.object(ses_baglanti, 'transcribe', side_effect=lambda *a, **k: metinler.pop(0)):
            ilk = self.api('/api/dictate/window', {'audio': 'x' * 10, 'session': 'test1'})
            ikinci = self.api('/api/dictate/window', {'audio': 'x' * 10, 'session': 'test1'})
            ucuncu = self.api('/api/dictate/window', {'audio': 'x' * 10, 'session': 'test1'})
        self.assertEqual(ilk['added'], 'yarın saat üçte toplantı')
        self.assertEqual(ikinci['added'], 'var')
        self.assertEqual(ucuncu['added'], 've fatura')
        self.assertIn('fatura', ucuncu['full'])
        self.assertEqual(ucuncu['full'].count('toplantı'), 1)

    def test_dictate_finish_formats_sentence(self):
        import ses_baglanti
        with mock.patch.object(ses_baglanti, 'transcribe', return_value='yarın toplantı var'):
            self.api('/api/dictate/window', {'audio': 'x' * 10, 'session': 'test2'})
        veri = self.api('/api/dictate/finish', {'session': 'test2'})
        self.assertEqual(veri['text'], 'Yarın toplantı var.')

    def test_dictate_reset_clears_session(self):
        import ses_baglanti
        with mock.patch.object(ses_baglanti, 'transcribe', return_value='bir cümle'):
            self.api('/api/dictate/window', {'audio': 'x' * 10, 'session': 'test3'})
        self.api('/api/dictate/reset', {'session': 'test3'})
        self.assertEqual(self.api('/api/dictate/finish', {'session': 'test3'})['text'], '')

    def test_dictate_window_needs_audio(self):
        self.api('/api/dictate/window', {'session': 'x'}, expect=400)

    def test_dictate_type_requires_confirmation(self):
        hata = self.api('/api/dictate/type', {'text': 'selam'}, expect=400)
        self.assertIn('onay', hata['error'])

    def test_dictate_type_writes_into_active_window(self):
        import dikte_yaz
        with mock.patch.object(dikte_yaz, 'yaz', return_value={'ok': True, 'yazilan': 5,
                                                               'pencere': 'Antigravity', 'enter': False}) as sahte:
            veri = self.api('/api/dictate/type', {'text': 'selam', 'confirmed': True, 'target': 'Antigravity'})
        self.assertTrue(veri['ok'])
        self.assertEqual(sahte.call_args.kwargs.get('hedef'), 'Antigravity')

    def test_dictate_type_rejects_empty(self):
        self.api('/api/dictate/type', {'text': '   ', 'confirmed': True}, expect=400)

    def test_dictate_type_rejects_long_target(self):
        self.api('/api/dictate/type', {'text': 'a', 'confirmed': True, 'target': 'x' * 200}, expect=400)

    def test_dictate_finish_polish_uses_provider(self):
        import ses_baglanti
        with mock.patch.object(ses_baglanti, 'transcribe', return_value='yarın toplantı var mı'):
            self.api('/api/dictate/window', {'audio': 'x' * 10, 'session': 'test4'})
        server.SAG.kaydet(self.provider_base, 'test', 'openai/gpt-oss-20b:free')
        veri = self.api('/api/dictate/finish', {'session': 'test4', 'polish': True})
        self.assertTrue(veri['polished'])
        self.assertTrue(veri['text'])

    def test_dictate_finish_without_provider_falls_back(self):
        import ses_baglanti
        with mock.patch.object(ses_baglanti, 'transcribe', return_value='bir cümle'):
            self.api('/api/dictate/window', {'audio': 'x' * 10, 'session': 'test5'})
        veri = self.api('/api/dictate/finish', {'session': 'test5', 'polish': True})
        self.assertFalse(veri['polished'])
        self.assertEqual(veri['text'], 'Bir cümle.')

    def test_dictate_status_shape(self):
        veri = self.api('/api/dictate/status', {})
        self.assertIn('sessions', veri)
        self.assertIn('typing_supported', veri)

    def test_speech_status_includes_model(self):
        veri = self.api('/api/speech/status')
        self.assertIn('installed', veri)
        self.assertIn(veri['model'], ('base', 'small'))
        self.assertIn('hint', veri)

    def test_speech_model_switch(self):
        import ses_baglanti
        eski = ses_baglanti.AYAR
        tmp = tempfile.TemporaryDirectory()
        ses_baglanti.AYAR = Path(tmp.name) / 'whisper_ayar.json'
        try:
            veri = self.api('/api/speech/model', {'model': 'small'})
            self.assertEqual(veri['status']['model'], 'small')
            self.api('/api/speech/model', {'model': 'large'}, expect=400)
        finally:
            ses_baglanti.AYAR = eski
            tmp.cleanup()

    def test_provider_test_endpoint_reports_success(self):
        server.SAG.kaydet(self.provider_base, 'test', 'openai/gpt-oss-20b:free')
        veri = self.api('/api/provider/test', {'model': 'openai/gpt-oss-20b:free'})
        self.assertTrue(veri['ok'])
        self.assertIn('Sağlayıcı yanıtı', veri['reply'])

    def test_provider_test_endpoint_requires_configuration(self):
        hata = self.api('/api/provider/test', {}, expect=400)
        self.assertIn('ayarlanmamış', hata['error'])

    def test_provider_scan_finds_fake_gateway(self):
        port = int(self.provider_base.rsplit(':', 1)[1].split('/')[0])
        veri = self.api('/api/provider/scan', {'ports': [port]})
        self.assertEqual(veri['total_alive'], 1)
        bulunan = [g for g in veri['gateways'] if g['port'] == port][0]
        self.assertTrue(bulunan['alive'])
        self.assertTrue(bulunan['models'])
        self.assertTrue(all(g['base_url'].startswith('http://127.0.0.1') for g in veri['gateways']))

    def test_provider_scan_rejects_bad_port_list(self):
        self.api('/api/provider/scan', {'ports': 'hepsi'}, expect=400)
        self.api('/api/provider/scan', {'ports': list(range(1, 20))}, expect=400)

    def test_provider_rejects_plain_http_remote(self):
        error = self.api('/api/provider/models', {'base_url': 'http://kotu-site.example/v1'}, expect=400)['error']
        self.assertIn('https', error)

    def test_chat_with_api_backend(self):
        server.SAG.kaydet(self.provider_base, 'test', 'openai/gpt-oss-20b:free')
        cevap = self.api('/api/chat', {'messages': [{'role': 'user', 'content': 'merhaba'}],
                                       'backend': 'api', 'session': 'api-oturum'})
        self.assertIn('sağlayıcı yanıtı', cevap['reply'].lower())
        # Mesaj sunucu geçmişine de yazılmalı
        oturumlar = self.api('/api/history')['sessions']
        self.assertTrue(any(o['session'] == 'api-oturum' for o in oturumlar))

    def test_chat_with_api_backend_runs_ledger_tool(self):
        server.SAG.kaydet(self.provider_base, 'test', 'tool-model')
        self.api('/api/accounts', {'name': 'Araç Kişi'})
        self.api('/api/ledger', {'person': 'Araç Kişi', 'kind': 'receivable', 'amount': 10000})
        cevap = self.api('/api/chat', {'messages': [{'role': 'user', 'content': 'Araç Kişi bakiyesi ne?'}],
                                       'backend': 'api'})
        self.assertIn('alacak', cevap['reply'].lower())
        self.assertIn('100,00', cevap['reply'])

    def test_chat_with_api_backend_not_configured(self):
        error = self.api('/api/chat', {'messages': [{'role': 'user', 'content': 'selam'}], 'backend': 'api'},
                         expect=400)['error']
        self.assertIn('Ücretsiz API', error)

    # --- istek gövdesi -----------------------------------------------------
    def test_chunked_body_accepted(self):
        import socket
        body = json.dumps({'name': 'Chunk Kişi', 'note': ''}).encode()
        request = (b'POST /api/accounts HTTP/1.1\r\nHost: 127.0.0.1\r\nX-Emre-Token: test-anahtar\r\n'
                   b'Content-Type: application/json\r\nTransfer-Encoding: chunked\r\nConnection: close\r\n\r\n')
        request += f'{len(body):x}'.encode() + b'\r\n' + body + b'\r\n0\r\n\r\n'
        with socket.create_connection(('127.0.0.1', self.port), timeout=10) as sock:
            sock.sendall(request)
            data = b''
            while True:
                part = sock.recv(4096)
                if not part:
                    break
                data += part
        self.assertIn(b' 200 ', data.split(b'\r\n')[0] + b' ', data[:120])
        names = [a['name'] for a in self.api('/api/accounts')['accounts']]
        self.assertIn('Chunk Kişi', names)

    def test_error_messages_are_turkish_not_field_names(self):
        error = self.api('/api/accounts', {'name': '   '}, expect=400)['error']
        self.assertIn('Hesap adı gerekli', error)
        self.assertNotIn('name', error)
        error = self.api('/api/reminders', {'text': '', 'due': '2030-01-01T09:00'}, expect=400)['error']
        self.assertIn('Hatırlatıcı metni gerekli', error)

    def test_non_object_body_rejected(self):
        status, payload, _ = self.raw('/api/accounts', data=[1, 2, 3])
        self.assertEqual(status, 400)
        self.assertIn('JSON', payload['error'])

    def test_chat_rejects_string_messages(self):
        error = self.api('/api/chat', {'messages': 'merhaba'}, expect=400)
        self.assertIn('Mesaj', error['error'])

    # --- bağlantı sızıntısı ------------------------------------------------
    def test_connections_are_closed(self):
        counts = {'open': 0, 'close': 0}
        original_connect = server.sqlite3.connect

        class Tracking(sqlite3.Connection):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.kapandi = False
                counts['open'] += 1

            def close(self):
                if not getattr(self, 'kapandi', False):
                    self.kapandi = True
                    counts['close'] += 1
                super().close()

        def connect(*args, **kwargs):
            kwargs['factory'] = Tracking
            return original_connect(*args, **kwargs)

        server.sqlite3.connect = connect
        try:
            for _ in range(10):
                self.api('/api/ledger')
        finally:
            server.sqlite3.connect = original_connect
        self.assertGreater(counts['open'], 0)
        self.assertEqual(counts['open'], counts['close'], 'SQLite bağlantıları kapatılmıyor (fd sızıntısı)')


if __name__ == '__main__':
    unittest.main()
