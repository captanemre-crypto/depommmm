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
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import server  # noqa: E402


class ServerTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.original_db = server.DB
        cls.original_key = server.KEY
        server.DB = Path(cls.tmp.name) / 'test.sqlite3'
        server.KEY = 'test-anahtar'
        cls.httpd = server.EmreServer(('127.0.0.1', 0), server.Handler)
        cls.port = cls.httpd.server_address[1]
        cls.base = f'http://127.0.0.1:{cls.port}'
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.tmp.cleanup()
        server.DB = cls.original_db
        server.KEY = cls.original_key

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
