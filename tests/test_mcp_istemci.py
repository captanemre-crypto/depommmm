"""MCP istemcisi testleri (gerçek stdio alt süreç, sahte sunucu ile)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import mcp_istemci  # noqa: E402

SAHTE = ROOT / 'tests' / 'yardimci' / 'sahte_mcp.py'


class AyarTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.yol = Path(self.tmp.name) / 'mcp.json'

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_file_gives_empty(self):
        self.assertEqual(mcp_istemci.ayar_oku(self.yol)['sunucular'], [])

    def test_broken_file_gives_empty(self):
        self.yol.write_text('{bozuk', encoding='utf-8')
        self.assertEqual(mcp_istemci.ayar_oku(self.yol)['sunucular'], [])

    def test_valid_entry_is_parsed(self):
        self.yol.write_text(json.dumps({'sunucular': [
            {'ad': 'test', 'komut': sys.executable, 'argumanlar': [str(SAHTE)]}]}), encoding='utf-8')
        sunucular = mcp_istemci.ayar_oku(self.yol)['sunucular']
        self.assertEqual(len(sunucular), 1)
        self.assertEqual(sunucular[0]['ad'], 'test')

    def test_incomplete_entry_skipped(self):
        self.yol.write_text(json.dumps({'sunucular': [
            {'ad': '', 'komut': 'x'}, {'ad': 'y'}, {'komut': 'z'}]}), encoding='utf-8')
        self.assertEqual(mcp_istemci.ayar_oku(self.yol)['sunucular'], [])

    def test_bad_argument_type_skipped(self):
        self.yol.write_text(json.dumps({'sunucular': [
            {'ad': 'x', 'komut': sys.executable, 'argumanlar': 'tek-dize'}]}), encoding='utf-8')
        self.assertEqual(mcp_istemci.ayar_oku(self.yol)['sunucular'], [])


class SunucuTest(unittest.TestCase):
    def setUp(self):
        self.sunucu = mcp_istemci.McpSunucu('sahte', sys.executable, [str(SAHTE)])

    def tearDown(self):
        self.sunucu.kapat()

    def test_lists_tools(self):
        araclar = self.sunucu.araclar()
        adlar = [a['ad'] for a in araclar]
        self.assertIn('echo', adlar)
        self.assertIn('topla', adlar)

    def test_calls_tool(self):
        self.sunucu.araclar()
        sonuc = self.sunucu.cagir('echo', {'metin': 'merhaba'})
        self.assertEqual(sonuc['metin'], 'yankı: merhaba')
        self.assertFalse(sonuc['hata'])

    def test_tool_arguments_are_used(self):
        self.sunucu.araclar()
        self.assertEqual(self.sunucu.cagir('topla', {'a': 2, 'b': 40})['metin'], '42')

    def test_tool_error_is_reported(self):
        self.sunucu.araclar()
        with self.assertRaises(ValueError):
            self.sunucu.cagir('patlat', {})

    def test_unknown_binary_fails_clearly(self):
        bozuk = mcp_istemci.McpSunucu('yok', '/olmayan/komut', [])
        with self.assertRaises(ValueError) as ctx:
            bozuk.araclar()
        self.assertIn('başlatılamadı', str(ctx.exception))

    def test_close_is_idempotent(self):
        self.sunucu.araclar()
        self.sunucu.kapat()
        self.sunucu.kapat()


class YoneticiTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.yol = Path(self.tmp.name) / 'mcp.json'
        self.yol.write_text(json.dumps({'sunucular': [
            {'ad': 'sahte', 'komut': sys.executable, 'argumanlar': [str(SAHTE)]}]}), encoding='utf-8')
        self.yonetici = mcp_istemci.Yonetici(self.yol)

    def tearDown(self):
        for sunucu in self.yonetici.sunucular.values():
            sunucu.kapat()
        self.tmp.cleanup()

    def test_refresh_and_tools(self):
        self.yonetici.yenile()
        araclar = self.yonetici.araclar()
        self.assertTrue(any(a.get('ad') == 'echo' for a in araclar))

    def test_call_through_manager(self):
        self.yonetici.yenile()
        sonuc = self.yonetici.cagir('sahte', 'topla', {'a': 1, 'b': 1})
        self.assertEqual(sonuc['metin'], '2')

    def test_unknown_server_rejected(self):
        self.yonetici.yenile()
        with self.assertRaises(ValueError):
            self.yonetici.cagir('yok', 'echo', {})

    def test_status_shape(self):
        self.yonetici.yenile()
        durum = self.yonetici.durum()
        self.assertEqual(durum[0]['ad'], 'sahte')


if __name__ == '__main__':
    unittest.main()
