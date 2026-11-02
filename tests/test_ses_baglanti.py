"""Konuşma tanıma köprüsü testleri (Whisper çalıştırmadan)."""
import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import ses_baglanti  # noqa: E402


class SesBaglantiTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.eski_ayar = ses_baglanti.AYAR
        ses_baglanti.AYAR = Path(self.tmp.name) / 'whisper_ayar.json'
        ses_baglanti.worker = None

    def tearDown(self):
        ses_baglanti.AYAR = self.eski_ayar
        ses_baglanti.worker = None
        self.tmp.cleanup()

    def test_default_model_is_base(self):
        self.assertEqual(ses_baglanti.model(), 'base')

    def test_set_model_persists(self):
        durum = ses_baglanti.ayarla('small')
        self.assertEqual(durum['model'], 'small')
        self.assertEqual(json.loads(ses_baglanti.AYAR.read_text(encoding='utf-8'))['model'], 'small')

    def test_invalid_model_rejected(self):
        with self.assertRaises(ValueError):
            ses_baglanti.ayarla('large-v3')

    def test_broken_settings_file_falls_back(self):
        ses_baglanti.AYAR.write_text('bozuk json', encoding='utf-8')
        self.assertEqual(ses_baglanti.model(), 'base')

    def test_status_shape(self):
        durum = ses_baglanti.durum()
        self.assertIn('installed', durum)
        self.assertIn('model', durum)
        self.assertIn('hint', durum)

    def test_empty_audio_rejected(self):
        with self.assertRaises(ValueError):
            ses_baglanti.transcribe('')

    def test_invalid_base64_rejected(self):
        with self.assertRaises(ValueError):
            ses_baglanti.transcribe('%%%gecersiz%%%')

    def test_oversized_audio_rejected(self):
        buyuk = base64.b64encode(b'x' * 5_100_000).decode()
        with self.assertRaises(ValueError):
            ses_baglanti.transcribe(buyuk)

    def test_missing_install_reports_clearly(self):
        eski_yol = ses_baglanti._yol
        ses_baglanti._yol = lambda: Path(self.tmp.name) / 'yok.exe'
        try:
            ses = base64.b64encode(b'x' * 2000).decode()
            with self.assertRaises(ValueError) as ctx:
                ses_baglanti.transcribe(ses)
            self.assertIn('ses_kur.bat', str(ctx.exception))
        finally:
            ses_baglanti._yol = eski_yol


if __name__ == '__main__':
    unittest.main()
