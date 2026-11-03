"""Piper model indirme doğrulaması (ağa çıkmadan)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import piper_indir  # noqa: E402


class PiperIndirTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.klasor = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_small_file_rejected(self):
        dosya = self.klasor / 'a.onnx'
        dosya.write_bytes(b'x' * 100)
        with self.assertRaises(ValueError):
            piper_indir.dogrula(dosya, 'onnx', 'a.onnx')

    def test_bad_json_config_rejected(self):
        dosya = self.klasor / 'a.json'
        dosya.write_text('[]', encoding='utf-8')
        with self.assertRaises(ValueError):
            piper_indir.dogrula(dosya, 'json', 'a.json')

    def test_valid_config_hash_stable(self):
        dosya = self.klasor / 'a.json'
        dosya.write_text(json.dumps({'audio': {'sample_rate': 22050, 'quality': 'medium'}, 'espeak': {'voice': 'tr'}, 'pad': 'x' * 80}), encoding='utf-8')
        ozet1 = piper_indir.dogrula(dosya, 'json', 'a.json')
        ozet2 = piper_indir.dogrula(dosya, 'json', 'a.json')
        self.assertEqual(ozet1, ozet2)
        self.assertEqual(len(ozet1), 64)

    def test_existing_file_hash_mismatch_detected(self):
        # Mevcut ve geçerli dosya + yanlış kayıtlı özet -> SystemExit
        dosya = self.klasor / 'a.json'
        dosya.write_text(json.dumps({'audio': {'sample_rate': 22050}, 'note': 'x' * 80}), encoding='utf-8')
        (self.klasor / 'a.json.sha256').write_text('0' * 64 + '\n', encoding='utf-8')
        with self.assertRaises(SystemExit):
            piper_indir.indir(self.klasor, 'fahrettin', 'a.json', 'json')

    def test_existing_valid_file_is_reused(self):
        dosya = self.klasor / 'b.json'
        dosya.write_text(json.dumps({'audio': {'sample_rate': 22050}, 'note': 'x' * 80}), encoding='utf-8')
        piper_indir.indir(self.klasor, 'fahrettin', 'b.json', 'json')  # ilk çağrı özeti kaydeder
        self.assertTrue((self.klasor / 'b.json.sha256').exists())
        piper_indir.indir(self.klasor, 'fahrettin', 'b.json', 'json')  # ikinci çağrı doğrular


if __name__ == '__main__':
    unittest.main()
