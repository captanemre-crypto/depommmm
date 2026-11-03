"""Türkçe zaman ayrıştırma testleri (sabit 'şimdi' ile deterministik)."""
import sys
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import zaman_ayristir as z  # noqa: E402

NOW = datetime(2026, 11, 2, 10, 0)  # Pazartesi


class ZamanAyristirTest(unittest.TestCase):
    def test_named_days(self):
        self.assertEqual(z.parse_when('yarın 09:00 hatırlat', NOW), datetime(2026, 11, 3, 9, 0))
        self.assertEqual(z.parse_when('bugün 18:30 ara', NOW), datetime(2026, 11, 2, 18, 30))
        self.assertEqual(z.parse_when('öbür gün 08:00', NOW), datetime(2026, 11, 4, 8, 0))

    def test_relative(self):
        self.assertEqual(z.parse_when('3 gün sonra saat 18:00', NOW), datetime(2026, 11, 5, 18, 0))
        self.assertEqual(z.parse_when('5 dk sonra', NOW), datetime(2026, 11, 2, 10, 5))
        self.assertEqual(z.parse_when('yarım saat sonra çay', NOW), datetime(2026, 11, 2, 10, 30))
        self.assertEqual(z.parse_when('2 saat sonra kontrol', NOW), datetime(2026, 11, 2, 12, 0))

    def test_explicit_dates(self):
        self.assertEqual(z.parse_when('15 Kasım 14:30 fatura', NOW), datetime(2026, 11, 15, 14, 30))
        self.assertEqual(z.parse_when('15.11.2026 14:30 sunum', NOW), datetime(2026, 11, 15, 14, 30))
        self.assertEqual(z.parse_when('20 Aralık 2027 09:15', NOW), datetime(2027, 12, 20, 9, 15))
        # Yıl verilmemiş ve tarih geçmişte: gelecek yıla taşınır
        self.assertEqual(z.parse_when('1 Ocak 10:00', NOW), datetime(2027, 1, 1, 10, 0))

    def test_weekday(self):
        self.assertEqual(z.parse_when('pazartesi sabah 9 kontrol', NOW), datetime(2026, 11, 9, 9, 0))
        self.assertEqual(z.parse_when('cuma 16:00 toplantı', NOW), datetime(2026, 11, 6, 16, 0))

    def test_part_of_day(self):
        self.assertEqual(z.parse_when('akşam 8 fatura öde', NOW), datetime(2026, 11, 2, 20, 0))
        self.assertEqual(z.parse_when('gece 11 ilaç', NOW), datetime(2026, 11, 2, 23, 0))

    def test_time_only_rolls_to_tomorrow(self):
        self.assertEqual(z.parse_when('09:00 spor', NOW), datetime(2026, 11, 3, 9, 0))
        self.assertEqual(z.parse_when('18:00 spor', NOW), datetime(2026, 11, 2, 18, 0))

    def test_amounts_are_not_times(self):
        # "1.500 TL" gibi tutarlar saat sanılmamalı
        self.assertIsNone(z.parse_when('Ahmete 1.500 TL alacak ekle', NOW))
        self.assertIsNone(z.parse_when('1250,50 TL ödeme', NOW))

    def test_ambiguous_returns_none(self):
        self.assertIsNone(z.parse_when('toplantı var diye hatırlat', NOW))
        self.assertIsNone(z.parse_when('bir ara kontrol et', NOW))

    def test_strip_keeps_ledger_text(self):
        metin = "Ahmete 1.500 TL alacak ekle yarın 09:00'da hatırlat"
        self.assertEqual(z.strip_time_and_command(metin), 'Ahmete 1.500 TL alacak ekle')
        self.assertEqual(z.strip_time_and_command('15.11.2026 14:30 sunum'), 'sunum')
        self.assertEqual(z.strip_time_and_command('akşam 8 fatura öde diye hatırlat'), 'fatura öde')

    def test_intent_detection(self):
        for metin in ('yarın hatırlat', 'bana hatırlatır mısın', 'beni uyar', 'not al'):
            self.assertTrue(z.has_reminder_intent(metin), metin)
        for metin in ('saat kaç', 'hava nasıl', 'defteri göster'):
            self.assertFalse(z.has_reminder_intent(metin), metin)


if __name__ == '__main__':
    unittest.main()
