"""Yerel işçi süreci testleri: normal yanıt, hata yanıtı, zaman aşımı ve yeniden başlatma."""
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from yerel_isci import YerelIsci  # noqa: E402

WORKER = textwrap.dedent('''
    import json, sys, time
    print(json.dumps({'ready': True}), flush=True)
    for line in sys.stdin:
        req = json.loads(line)
        if req.get('sleep'):
            time.sleep(req['sleep'])
        if req.get('error'):
            print(json.dumps({'error': 'istenen hata'}), flush=True)
            continue
        print(json.dumps({'ok': True, 'echo': req.get('value')}), flush=True)
''')

BROKEN = textwrap.dedent('''
    import json
    print(json.dumps({'ready': False, 'error': 'model yok'}), flush=True)
''')


class YerelIsciTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.worker_path = Path(self.tmp.name) / 'isci.py'
        self.worker_path.write_text(WORKER, encoding='utf-8')
        self.broken_path = Path(self.tmp.name) / 'bozuk.py'
        self.broken_path.write_text(BROKEN, encoding='utf-8')
        self.isci = YerelIsci(sys.executable, self.worker_path, baslatma_saniye=20, istek_saniye=20)

    def tearDown(self):
        self.isci.kapat()
        self.tmp.cleanup()

    def test_request_roundtrip(self):
        self.assertEqual(self.isci.istek({'value': 42})['echo'], 42)

    def test_multiple_requests_reuse_process(self):
        self.isci.istek({'value': 'a'})
        pid = self.isci.proc.pid
        self.isci.istek({'value': 'b'})
        self.assertEqual(self.isci.proc.pid, pid)

    def test_error_response_is_passed_through(self):
        self.assertEqual(self.isci.istek({'error': True})['error'], 'istenen hata')
        self.assertTrue(self.isci._canli())

    def test_timeout_kills_worker_and_raises(self):
        self.isci.istek_saniye = 1
        started = time.monotonic()
        with self.assertRaises(ValueError) as ctx:
            self.isci.istek({'sleep': 5})
        self.assertLess(time.monotonic() - started, 8)
        self.assertIn('zamanında', str(ctx.exception))
        self.assertFalse(self.isci._canli())

    def test_worker_restarts_after_timeout(self):
        self.isci.istek_saniye = 1
        with self.assertRaises(ValueError):
            self.isci.istek({'sleep': 5})
        self.isci.istek_saniye = 20
        self.assertEqual(self.isci.istek({'value': 'tekrar'})['echo'], 'tekrar')

    def test_missing_model_reports_startup_error(self):
        with self.assertRaises(ValueError) as ctx:
            YerelIsci(sys.executable, self.broken_path, baslatma_saniye=20).istek({'value': 1})
        self.assertIn('model yok', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
