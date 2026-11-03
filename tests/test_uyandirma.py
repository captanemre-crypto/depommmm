"""Uyandırma sözcüğü testleri."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import uyandirma  # noqa: E402


class AyiklaTest(unittest.TestCase):
    def test_wake_word_at_start(self):
        uyandi, komut = uyandirma.ayikla('Emre, yarın toplantı var mı')
        self.assertTrue(uyandi)
        self.assertEqual(komut, 'yarın toplantı var mı')

    def test_wake_word_in_middle(self):
        uyandi, komut = uyandirma.ayikla('yarın hava nasıl olacak Emre')
        self.assertTrue(uyandi)
        self.assertEqual(komut, 'yarın hava nasıl olacak')

    def test_hey_wake_word(self):
        uyandi, komut = uyandirma.ayikla('hey Emre saat kaç')
        self.assertTrue(uyandi)
        self.assertEqual(komut, 'saat kaç')

    def test_no_wake_word(self):
        self.assertEqual(uyandirma.ayikla('yarın toplantı var mı'), (False, ''))

    def test_suffix_is_not_wake_word(self):
        # "emreye", "emreler" gibi ekli kelimeler tetiklememeli.
        self.assertEqual(uyandirma.ayikla('emreye söyle'), (False, ''))
        self.assertEqual(uyandirma.ayikla('emreler geldi'), (False, ''))

    def test_uppercase_and_punctuation(self):
        uyandi, komut = uyandirma.ayikla('EMRE!!! bugün ne var?')
        self.assertTrue(uyandi)
        self.assertEqual(komut, 'bugün ne var')

    def test_only_wake_word_gives_empty_command(self):
        self.assertEqual(uyandirma.ayikla('Emre'), (True, ''))

    def test_custom_words(self):
        uyandi, komut = uyandirma.ayikla('bilge ışık yarını planla', ['bilge ışık'])
        self.assertTrue(uyandi)
        self.assertEqual(komut, 'yarını planla')

    def test_empty_input(self):
        self.assertEqual(uyandirma.ayikla(''), (False, ''))
        self.assertEqual(uyandirma.ayikla(None), (False, ''))

    def test_long_text_is_truncated(self):
        uyandi, komut = uyandirma.ayikla('Emre ' + 'a' * 5000)
        self.assertTrue(uyandi)
        self.assertLessEqual(len(komut), 2000)


class AyarTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.yol = Path(self.tmp.name) / 'wake.json'

    def tearDown(self):
        self.tmp.cleanup()

    def test_defaults_are_off(self):
        ayar = uyandirma.ayar_oku(self.yol)
        self.assertFalse(ayar['aktif'])
        self.assertIn('emre', ayar['kelimeler'])
        self.assertIn('hey emre', ayar['kelimeler'])

    def test_write_and_read(self):
        uyandirma.ayar_yaz(aktif=True, kelimeler=['emre', 'asistan'], yol=self.yol)
        ayar = uyandirma.ayar_oku(self.yol)
        self.assertTrue(ayar['aktif'])
        self.assertEqual(ayar['kelimeler'], ['emre', 'asistan'])

    def test_empty_words_rejected(self):
        with self.assertRaises(ValueError):
            uyandirma.ayar_yaz(kelimeler=['  '], yol=self.yol)

    def test_too_many_words_rejected(self):
        with self.assertRaises(ValueError):
            uyandirma.ayar_yaz(kelimeler=['a', 'b', 'c', 'd', 'e', 'f', 'g'], yol=self.yol)

    def test_broken_file_falls_back(self):
        self.yol.write_text('bozuk', encoding='utf-8')
        self.assertFalse(uyandirma.ayar_oku(self.yol)['aktif'])

    def test_file_is_json(self):
        uyandirma.ayar_yaz(aktif=True, yol=self.yol)
        self.assertTrue(json.loads(self.yol.read_text(encoding='utf-8'))['aktif'])


if __name__ == '__main__':
    unittest.main()
