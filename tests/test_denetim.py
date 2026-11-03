"""Denetim izi testleri (geçici SQLite)."""
import sqlite3
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import denetim  # noqa: E402


class DenetimTest(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        denetim.kur(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_kur_is_idempotent(self):
        denetim.kur(self.conn)
        denetim.kaydet(self.conn, 'test', 'işlem')
        self.assertEqual(len(denetim.son(self.conn)), 1)

    def test_record_and_read(self):
        kid = denetim.kaydet(self.conn, 'mcp', 'araç çağrıldı', 'sunucu=x', 'ok')
        kayit = denetim.son(self.conn)[0]
        self.assertEqual(kayit['id'], kid)
        self.assertEqual(kayit['kind'], 'mcp')
        self.assertEqual(kayit['status'], 'ok')
        self.assertTrue(kayit['created'])

    def test_newest_first(self):
        denetim.kaydet(self.conn, 'a', 'bir')
        denetim.kaydet(self.conn, 'b', 'iki')
        self.assertEqual([k['action'] for k in denetim.son(self.conn)], ['iki', 'bir'])

    def test_filter_by_kind(self):
        denetim.kaydet(self.conn, 'mcp', 'bir')
        denetim.kaydet(self.conn, 'defter', 'iki')
        self.assertEqual([k['action'] for k in denetim.son(self.conn, kind='mcp')], ['bir'])

    def test_limit_respected(self):
        for i in range(10):
            denetim.kaydet(self.conn, 'x', str(i))
        self.assertEqual(len(denetim.son(self.conn, limit=3)), 3)

    def test_secrets_masked(self):
        denetim.kaydet(self.conn, 'saglayici', 'anahtar',
                       'Authorization: Bearer sk-abcdefgh12345 token: supersecret123')
        detay = denetim.son(self.conn)[0]['detail']
        self.assertNotIn('sk-abcdefgh12345', detay)
        self.assertNotIn('supersecret123', detay)
        self.assertIn('[gizli]', detay)

    def test_gizle_truncates(self):
        self.assertLessEqual(len(denetim.gizle('x' * 900)), denetim.AZAMI_DETAY)

    def test_gizle_collapses_whitespace(self):
        self.assertEqual(denetim.gizle('a\n\t b'), 'a b')

    def test_long_fields_truncated(self):
        denetim.kaydet(self.conn, 'k' * 200, 'a' * 300, 'd' * 900)
        kayit = denetim.son(self.conn)[0]
        self.assertLessEqual(len(kayit['kind']), 40)
        self.assertLessEqual(len(kayit['action']), 80)
        self.assertLessEqual(len(kayit['detail']), denetim.AZAMI_DETAY)

    def test_invalid_status_falls_back(self):
        denetim.kaydet(self.conn, 'a', 'b', status='bilinmeyen')
        self.assertEqual(denetim.son(self.conn)[0]['status'], 'ok')

    def test_error_status_saved(self):
        denetim.kaydet(self.conn, 'mcp', 'başarısız', status='hata')
        self.assertEqual(denetim.son(self.conn)[0]['status'], 'hata')

    def test_pruning_keeps_limit(self):
        eski = denetim.AZAMI_KAYIT
        try:
            denetim.AZAMI_KAYIT = 5
            for i in range(12):
                denetim.kaydet(self.conn, 'x', str(i))
            adet = self.conn.execute('SELECT COUNT(*) FROM audit').fetchone()[0]
        finally:
            denetim.AZAMI_KAYIT = eski
        self.assertLessEqual(adet, 5)  # budama sınırı korunur
        self.assertGreaterEqual(adet, 4)

    def test_temizle(self):
        denetim.kaydet(self.conn, 'a', 'bir')
        denetim.kaydet(self.conn, 'a', 'iki')
        self.assertEqual(denetim.temizle(self.conn), 2)
        self.assertEqual(denetim.son(self.conn), [])

    def test_broken_table_does_not_crash_kaydet(self):
        # kur() çağrılmamış bağlantıda kaydet hata verir; sunucu tarafı bunu yutar.
        with sqlite3.connect(':memory:') as bos:
            with self.assertRaises(sqlite3.Error):
                denetim.kaydet(bos, 'a', 'b')


if __name__ == '__main__':
    unittest.main()
