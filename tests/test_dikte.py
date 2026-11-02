"""Canlı dikte metin işleme testleri."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import dikte  # noqa: E402


class KaydirTest(unittest.TestCase):
    def test_no_overlap_appends_everything(self):
        self.assertEqual(dikte.kaydir('yarın toplantı', 'faturayı öde'), 'faturayı öde')

    def test_overlapping_words_are_dropped(self):
        self.assertEqual(dikte.kaydir('yarın saat üçte toplantı', 'saat üçte toplantı var'), 'var')

    def test_overlap_ignores_punctuation_and_case(self):
        self.assertEqual(dikte.kaydir('Yarın toplantı var.', 'toplantı var ve fatura'), 've fatura')

    def test_empty_new_text(self):
        self.assertEqual(dikte.kaydir('abc', ''), '')

    def test_empty_previous_text(self):
        self.assertEqual(dikte.kaydir('', 'yeni cümle'), 'yeni cümle')

    def test_full_repeat_returns_nothing(self):
        self.assertEqual(dikte.kaydir('bugün hava güzel', 'bugün hava güzel'), '')

    def test_max_overlap_is_bounded(self):
        uzun = ' '.join(['kelime'] * 30)
        self.assertEqual(dikte.kaydir(uzun, 'kelime yeni'), 'yeni')


class TemizleTest(unittest.TestCase):
    def test_fillers_removed(self):
        self.assertEqual(dikte.temizle('ıı bugün hmm toplantı var eee'), 'bugün toplantı var')

    def test_meaningful_words_kept(self):
        # "yani" anlam taşıyan bağlaçtır; dolgu sesi gibi atılmamalı.
        self.assertEqual(dikte.temizle('yani bu iş bitti'), 'yani bu iş bitti')
        self.assertEqual(dikte.temizle('bir şey söyle'), 'bir şey söyle')

    def test_stutter_collapsed(self):
        self.assertEqual(dikte.temizle('ben ben ben geliyorum'), 'ben geliyorum')

    def test_empty(self):
        self.assertEqual(dikte.temizle(''), '')


class BicimlendirTest(unittest.TestCase):
    def test_capitalizes_first_letter(self):
        self.assertEqual(dikte.bicimlendir('bugün hava güzel'), 'Bugün hava güzel.')

    def test_turkish_i(self):
        self.assertTrue(dikte.bicimlendir('istanbul güzel').startswith('İstanbul'))

    def test_question_detected(self):
        self.assertEqual(dikte.bicimlendir('toplantı bitti mi'), 'Toplantı bitti mi?')

    def test_question_word_detected(self):
        self.assertEqual(dikte.bicimlendir('bu nasıl oldu'), 'Bu nasıl oldu?')

    def test_existing_punctuation_preserved(self):
        self.assertEqual(dikte.bicimlendir('Tamam. Yarın görüşürüz'), 'Tamam. Yarın görüşürüz.')

    def test_space_before_punctuation_removed(self):
        self.assertEqual(dikte.bicimlendir('merhaba , nasılsın .'), 'Merhaba, nasılsın.')

    def test_proper_noun_suffix_apostrophe(self):
        self.assertEqual(dikte.bicimlendir('ankara da hava güzel'), "Ankara'da hava güzel.")

    def test_no_double_punctuation(self):
        self.assertEqual(dikte.bicimlendir('harika!!'), 'Harika!')

    def test_empty_returns_empty(self):
        self.assertEqual(dikte.bicimlendir(''), '')

    def test_bitir_false_leaves_sentence_open(self):
        self.assertEqual(dikte.bicimlendir('yarın görüşürüz', bitir=False), 'Yarın görüşürüz')

    def test_sentence_start_after_period(self):
        self.assertEqual(dikte.bicimlendir('bitti. yarın devam ederiz'), 'Bitti. Yarın devam ederiz.')


class BirlestikTest(unittest.TestCase):
    def test_appends_new_part(self):
        tam, eklenen = dikte.birlesik('Yarın toplantı var', 'toplantı var ve fatura')
        self.assertEqual(eklenen, 've fatura')
        self.assertEqual(tam, 'Yarın toplantı var ve fatura')

    def test_no_duplicate_when_window_repeats(self):
        tam, eklenen = dikte.birlesik('Merhaba dünya', 'merhaba dünya')
        self.assertEqual(eklenen, '')
        self.assertEqual(tam, 'Merhaba dünya')


class YardimciTest(unittest.TestCase):
    def test_ipucu_takes_tail(self):
        metin = ' '.join(f'kelime{i}' for i in range(30))
        self.assertLessEqual(len(dikte.ipucu(metin)), 120)
        self.assertIn('kelime29', dikte.ipucu(metin))

    def test_temiz_mi(self):
        self.assertFalse(dikte.temiz_mi('...'))
        self.assertFalse(dikte.temiz_mi(''))
        self.assertTrue(dikte.temiz_mi('tamam'))


if __name__ == '__main__':
    unittest.main()
