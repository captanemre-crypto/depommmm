"""Tanılama testleri: gerçek sistemde çalışır, ağ çağrıları sahtelenir."""
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tanilama  # noqa: E402


class KontrolTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kok = Path(self.tmp.name)
        (self.kok / 'beceriler').mkdir()
        self.db = self.kok / 'test.sqlite3'

    def tearDown(self):
        self.tmp.cleanup()

    def test_python_ok(self):
        sonuc = tanilama.python_kontrol()
        self.assertEqual(sonuc['durum'], 'ok')
        self.assertIn('Python', sonuc['mesaj'])

    def test_write_permission_ok(self):
        self.assertEqual(tanilama.yazma_kontrol(self.kok)['durum'], 'ok')
        self.assertFalse((self.kok / '.emre_yazma_testi').exists())

    def test_write_permission_error(self):
        with mock.patch.object(Path, 'write_text', side_effect=OSError('izin yok')):
            self.assertEqual(tanilama.yazma_kontrol(self.kok)['durum'], 'hata')

    def test_database_ok(self):
        self.assertEqual(tanilama.veritabani_kontrol(self.db)['durum'], 'ok')

    def test_database_error(self):
        bozuk = self.kok / 'bozuk.sqlite3'
        bozuk.write_text('bu bir veritabanı değil', encoding='utf-8')
        self.assertEqual(tanilama.veritabani_kontrol(bozuk)['durum'], 'hata')

    def test_port_closed_reports_warning(self):
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            port = s.getsockname()[1]
        self.assertEqual(tanilama.port_kontrol(port)['durum'], 'uyari')

    def test_port_open_reports_ok(self):
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            s.listen(1)
            port = s.getsockname()[1]
            self.assertEqual(tanilama.port_kontrol(port)['durum'], 'ok')

    def test_ollama_offline_is_warning_only(self):
        sonuc = tanilama.ollama_kontrol('http://127.0.0.1:9')
        self.assertEqual(sonuc['durum'], 'uyari')
        self.assertIn('zorunlu değil', sonuc['mesaj'])

    def test_skill_folder_reported(self):
        (self.kok / 'beceriler' / 'a').mkdir()
        (self.kok / 'beceriler' / 'a' / 'SKILL.md').write_text('---\nad: a\n---\n', encoding='utf-8')
        self.assertIn('1 beceri', tanilama.beceri_kontrol(self.kok / 'beceriler')['mesaj'])

    def test_missing_skill_folder(self):
        self.assertEqual(tanilama.beceri_kontrol(self.kok / 'yok')['durum'], 'uyari')

    def test_mcp_config_missing_is_warning(self):
        self.assertEqual(tanilama.mcp_kontrol(self.kok)['durum'], 'uyari')

    def test_mcp_config_broken_is_error(self):
        (self.kok / 'mcp_ayar.json').write_text('{bozuk', encoding='utf-8')
        self.assertEqual(tanilama.mcp_kontrol(self.kok)['durum'], 'hata')

    def test_mcp_config_valid(self):
        (self.kok / 'mcp_ayar.json').write_text('{"sunucular": [{"ad": "x"}]}', encoding='utf-8')
        sonuc = tanilama.mcp_kontrol(self.kok)
        self.assertEqual(sonuc['durum'], 'ok')
        self.assertIn('1 MCP', sonuc['mesaj'])

    def test_full_run_shape(self):
        with mock.patch.object(tanilama, 'ollama_kontrol', return_value={'ad': 'Ollama', 'durum': 'uyari', 'mesaj': ''}):
            sonuc = tanilama.calistir(db_yolu=self.db, kok=self.kok, port=9)
        self.assertEqual(len(sonuc['checks']), 10)
        self.assertIn('ok', sonuc['ozet'])
        self.assertIn('mesaj', sonuc['ozet'])
        for kontrol in sonuc['checks']:
            self.assertEqual(set(kontrol), {'ad', 'durum', 'mesaj'})
            self.assertIn(kontrol['durum'], ('ok', 'uyari', 'hata'))

    def test_summary_counts_match(self):
        sonuc = tanilama.calistir(db_yolu=self.db, kok=self.kok, port=9)
        durumlar = [k['durum'] for k in sonuc['checks']]
        self.assertEqual(sonuc['ozet']['ok'], durumlar.count('ok'))
        self.assertEqual(sonuc['ozet']['hata'], durumlar.count('hata'))
        self.assertEqual(sonuc['ozet']['uyari'], durumlar.count('uyari'))

    def test_platform_message(self):
        sonuc = tanilama.platform_kontrol()
        self.assertIn(sonuc['durum'], ('ok', 'uyari'))
        self.assertTrue(sonuc['mesaj'])


if __name__ == '__main__':
    unittest.main()
