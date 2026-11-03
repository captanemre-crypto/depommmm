"""Akışlı seslendirme (cümle bölme) ve söz kesme (barge-in) testleri."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import sesli_yanit  # noqa: E402


class CumleTest(unittest.TestCase):
    def test_splits_on_sentence_end(self):
        parcalar = sesli_yanit.cumlelere_ayir('Merhaba Emre. Bugün hava güzel! Yarın yağmur var mı?')
        self.assertEqual(parcalar, ['Merhaba Emre.', 'Bugün hava güzel!', 'Yarın yağmur var mı?'])

    def test_keeps_abbreviation_together(self):
        parcalar = sesli_yanit.cumlelere_ayir('Toplantı 14.30 da başlıyor. Sonra görüşürüz.')
        self.assertEqual(len(parcalar), 2)
        self.assertIn('14.30', parcalar[0])

    def test_empty_text_returns_empty_list(self):
        self.assertEqual(sesli_yanit.cumlelere_ayir(''), [])
        self.assertEqual(sesli_yanit.cumlelere_ayir('   '), [])

    def test_long_sentence_is_split(self):
        metin = ('kelime ' * 200).strip() + '.'
        parcalar = sesli_yanit.cumlelere_ayir(metin)
        self.assertGreater(len(parcalar), 1)  # çok uzun cümle bölünür
        for parca in parcalar:
            self.assertLessEqual(len(parca), sesli_yanit.AZAMI_CUMLE + 20)

    def test_limit_truncates(self):
        metin = ' '.join(f'Cümle {i} burada.' for i in range(80))
        parcalar = sesli_yanit.cumlelere_ayir(metin)
        self.assertLessEqual(len(parcalar), sesli_yanit.AZAMI_PARCALAR)

    def test_text_without_punctuation(self):
        parcalar = sesli_yanit.cumlelere_ayir('noktalama yok ama metin var')
        self.assertEqual(parcalar, ['noktalama yok ama metin var'])


class AkisParcalayiciTest(unittest.TestCase):
    def test_emits_only_complete_sentences(self):
        akis = sesli_yanit.AkisParcalayici()
        self.assertEqual(akis.besle('Merhaba'), [])
        self.assertEqual(akis.besle(' Emre. Bugün'), ['Merhaba Emre.'])
        # Cümle sonu boşlukla gelmedikçe seslendirilmez (yarım cümle okunmasın).
        self.assertEqual(akis.besle(' hava güzel.'), [])
        self.assertEqual(akis.besle(' Sonra'), ['Bugün hava güzel.'])
        self.assertEqual(akis.kapat(), ['Sonra'])

    def test_flush_returns_remainder(self):
        akis = sesli_yanit.AkisParcalayici()
        akis.besle('Yarım kalan cümle')
        self.assertEqual(akis.kapat(), ['Yarım kalan cümle'])
        self.assertEqual(akis.kapat(), [])

    def test_short_buffer_waits_for_more_text(self):
        akis = sesli_yanit.AkisParcalayici()
        self.assertEqual(akis.besle('a.'), [])

    def test_stream_reassembles_to_original(self):
        akis = sesli_yanit.AkisParcalayici()
        metin = 'Birinci cümle. İkinci cümle daha uzun. Üçüncü!'
        parcalar = []
        for i in range(0, len(metin), 7):
            parcalar.extend(akis.besle(metin[i:i + 7]))
        parcalar.extend(akis.kapat())
        self.assertEqual(' '.join(parcalar), metin)


class BargeInTest(unittest.TestCase):
    def test_needs_consecutive_measurements(self):
        barge = sesli_yanit.BargeIn(esik=0.1, ardisik=3)
        self.assertFalse(barge.besle(0.5, simdi=0.0))
        self.assertFalse(barge.besle(0.5, simdi=0.1))
        self.assertTrue(barge.besle(0.5, simdi=0.2))

    def test_noise_below_threshold_does_not_trigger(self):
        barge = sesli_yanit.BargeIn(esik=0.1, ardisik=2)
        self.assertFalse(barge.besle(0.02, simdi=0.0))
        self.assertFalse(barge.besle(0.02, simdi=0.1))

    def test_quiet_sample_resets_counter(self):
        barge = sesli_yanit.BargeIn(esik=0.1, ardisik=2)
        barge.besle(0.5, simdi=0.0)
        barge.besle(0.0, simdi=0.1)
        self.assertFalse(barge.besle(0.5, simdi=0.2))

    def test_cooldown_prevents_retrigger(self):
        barge = sesli_yanit.BargeIn(esik=0.1, ardisik=1, soguma=2.0)
        self.assertTrue(barge.besle(0.5, simdi=0.0))
        self.assertFalse(barge.besle(0.5, simdi=1.0))
        self.assertTrue(barge.besle(0.5, simdi=2.5))

    def test_sifirla_resets_state(self):
        barge = sesli_yanit.BargeIn(esik=0.1, ardisik=1, soguma=5.0)
        self.assertTrue(barge.besle(0.5, simdi=0.0))
        barge.sifirla()
        self.assertTrue(barge.besle(0.5, simdi=0.1))


if __name__ == '__main__':
    unittest.main()
