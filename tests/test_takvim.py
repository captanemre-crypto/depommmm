"""Yerel `.ics` takvim okuma testleri (salt okunur, ağsız)."""
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import takvim  # noqa: E402


def _ics(*etkinlikler):
    govde = '\r\n'.join(etkinlikler)
    return f'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//test//TR\r\n{govde}\r\nEND:VCALENDAR\r\n'


class OkumaTest(unittest.TestCase):
    def test_single_event(self):
        metin = _ics('BEGIN:VEVENT', 'SUMMARY:Diş randevusu', 'DTSTART:20261105T140000',
                     'DTEND:20261105T150000', 'LOCATION:Klinik', 'END:VEVENT')
        kayitlar = takvim.oku(metin)
        self.assertEqual(len(kayitlar), 1)
        self.assertEqual(kayitlar[0]['baslik'], 'Diş randevusu')
        self.assertEqual(kayitlar[0]['basla'], '2026-11-05T14:00')
        self.assertEqual(kayitlar[0]['yer'], 'Klinik')

    def test_multiple_events_sorted(self):
        metin = _ics('BEGIN:VEVENT', 'SUMMARY:Sonra', 'DTSTART:20261110T090000', 'END:VEVENT',
                     'BEGIN:VEVENT', 'SUMMARY:Önce', 'DTSTART:20261105T090000', 'END:VEVENT')
        kayitlar = takvim.oku(metin)
        self.assertEqual([k['baslik'] for k in kayitlar], ['Önce', 'Sonra'])

    def test_utc_suffix_and_dash_format(self):
        metin = _ics('BEGIN:VEVENT', 'SUMMARY:Toplantı', 'DTSTART:2026-11-06T09:30:00Z', 'END:VEVENT')
        kayitlar = takvim.oku(metin)
        self.assertEqual(kayitlar[0]['basla'], '2026-11-06T09:30')

    def test_date_only_event(self):
        metin = _ics('BEGIN:VEVENT', 'SUMMARY:Tatil', 'DTSTART;VALUE=DATE:20261107', 'END:VEVENT')
        kayitlar = takvim.oku(metin)
        self.assertEqual(kayitlar[0]['basla'], '2026-11-07T00:00')

    def test_tzid_parameter(self):
        metin = _ics('BEGIN:VEVENT', 'SUMMARY:Uçuş', 'DTSTART;TZID=Europe/Istanbul:20261108T070000', 'END:VEVENT')
        kayitlar = takvim.oku(metin)
        self.assertEqual(kayitlar[0]['basla'], '2026-11-08T07:00')

    def test_recurring_flag(self):
        metin = _ics('BEGIN:VEVENT', 'SUMMARY:Haftalık', 'DTSTART:20261105T100000',
                     'RRULE:FREQ=WEEKLY;COUNT=10', 'END:VEVENT')
        self.assertTrue(takvim.oku(metin)[0]['tekrarli'])

    def test_folded_lines_are_joined(self):
        metin = _ics('BEGIN:VEVENT', 'SUMMARY:Çok uzun başlık', ' devamı', 'DTSTART:20261105T100000', 'END:VEVENT')
        self.assertIn('devamı', takvim.oku(metin)[0]['baslik'])

    def test_escaped_chars(self):
        metin = _ics('BEGIN:VEVENT', r'SUMMARY:Ara toplantı\, katılım zorunlu',
                     r'DESCRIPTION:Birinci satır\nİkinci satır', 'DTSTART:20261105T100000', 'END:VEVENT')
        kayit = takvim.oku(metin)[0]
        self.assertIn('Ara toplantı, katılım', kayit['baslik'])
        self.assertIn('Birinci satır İkinci satır', kayit['not'])

    def test_missing_summary_placeholder(self):
        metin = _ics('BEGIN:VEVENT', 'DTSTART:20261105T100000', 'END:VEVENT')
        self.assertEqual(takvim.oku(metin)[0]['baslik'], '(başlıksız)')

    def test_event_without_start_is_skipped(self):
        metin = _ics('BEGIN:VEVENT', 'SUMMARY:Tarihsiz', 'END:VEVENT')
        self.assertEqual(takvim.oku(metin), [])

    def test_default_end_is_one_hour(self):
        metin = _ics('BEGIN:VEVENT', 'SUMMARY:Tek', 'DTSTART:20261105T100000', 'END:VEVENT')
        kayit = takvim.oku(metin)[0]
        fark = datetime.fromisoformat(kayit['bitis']) - datetime.fromisoformat(kayit['basla'])
        self.assertEqual(fark, timedelta(hours=1))

    def test_not_a_calendar(self):
        with self.assertRaises(ValueError):
            takvim.oku('bu bir metin dosyası')

    def test_event_limit(self):
        satirlar = []
        for i in range(takvim.AZAMI_ETKINLIK + 20):
            satirlar += ['BEGIN:VEVENT', f'SUMMARY:E{i}', 'DTSTART:20261105T100000', 'END:VEVENT']
        self.assertLessEqual(len(takvim.oku(_ics(*satirlar))), takvim.AZAMI_ETKINLIK)


class DosyaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.yol = Path(self.tmp.name)

    def test_dosya_oku(self):
        dosya = self.yol / 'a.ics'
        dosya.write_text(_ics('BEGIN:VEVENT', 'SUMMARY:Test', 'DTSTART:20261105T100000', 'END:VEVENT'), encoding='utf-8')
        self.assertEqual(len(takvim.dosya_oku(dosya)), 1)
        self.assertEqual(takvim.dosya_oku(dosya)[0]['kaynak'], 'a.ics')

    def test_missing_file(self):
        with self.assertRaises(ValueError):
            takvim.dosya_oku(self.yol / 'yok.ics')

    def test_klasor_oku_merges_and_skips_broken(self):
        (self.yol / 'a.ics').write_text(_ics('BEGIN:VEVENT', 'SUMMARY:A', 'DTSTART:20261105T100000', 'END:VEVENT'), encoding='utf-8')
        (self.yol / 'b.ics').write_text(_ics('BEGIN:VEVENT', 'SUMMARY:B', 'DTSTART:20261106T100000', 'END:VEVENT'), encoding='utf-8')
        (self.yol / 'bozuk.ics').write_text('bu takvim değil', encoding='utf-8')
        kayitlar = takvim.klasor_oku(self.yol)
        self.assertEqual([k['baslik'] for k in kayitlar], ['A', 'B'])

    def test_klasor_missing(self):
        with self.assertRaises(ValueError):
            takvim.klasor_oku(self.yol / 'olmayan')

    def test_yolu_oku_accepts_file_and_folder(self):
        dosya = self.yol / 'tek.ics'
        dosya.write_text(_ics('BEGIN:VEVENT', 'SUMMARY:Tek', 'DTSTART:20261105T100000', 'END:VEVENT'), encoding='utf-8')
        self.assertEqual(len(takvim.yolu_oku(dosya)), 1)
        self.assertEqual(len(takvim.yolu_oku(self.yol)), 1)


class OzetTest(unittest.TestCase):
    def _etkinlik(self, gun, baslik='Etkinlik', yer=''):
        basla = datetime(2026, 11, 5, 10, 0) + timedelta(days=gun)
        return {'baslik': baslik, 'basla': basla.isoformat(timespec='minutes'),
                'bitis': (basla + timedelta(hours=1)).isoformat(timespec='minutes'),
                'yer': yer, 'not': '', 'tekrarli': False, 'kaynak': 'a.ics'}

    def test_yaklasan_window(self):
        simdi = datetime(2026, 11, 5, 8, 0)
        hepsi = [self._etkinlik(0), self._etkinlik(30), self._etkinlik(-10)]
        secili = takvim.yaklasan(hepsi, gun=7, simdi=simdi)
        self.assertEqual(len(secili), 1)

    def test_yaklasan_keeps_ongoing_event(self):
        simdi = datetime(2026, 11, 5, 10, 30)
        self.assertEqual(len(takvim.yaklasan([self._etkinlik(0)], gun=1, simdi=simdi)), 1)

    def test_metin_ozet_lists_events(self):
        simdi = datetime(2026, 11, 5, 8, 0)
        ozet = takvim.metin_ozet([self._etkinlik(0, 'Diş', 'Klinik')], gun=7, simdi=simdi)
        self.assertIn('Diş', ozet)
        self.assertIn('Klinik', ozet)

    def test_metin_ozet_empty(self):
        simdi = datetime(2026, 11, 5, 8, 0)
        self.assertIn('etkinlik yok', takvim.metin_ozet([], gun=7, simdi=simdi))

    def test_gun_parameter_clamped(self):
        self.assertEqual(takvim.yaklasan([], gun=9999), [])
        self.assertEqual(takvim.yaklasan([], gun=0), [])


class GerekiyorTest(unittest.TestCase):
    def test_calendar_questions(self):
        for metin in ('bu hafta takvimde ne var', 'bugün ajandamda ne var göster', 'yarın randevu var mı'):
            self.assertTrue(takvim.gerekiyor_mu(metin), metin)

    def test_plain_statements(self):
        for metin in ('merhaba', 'takvim', 'fatura öde'):
            self.assertFalse(takvim.gerekiyor_mu(metin), metin)

    def test_empty(self):
        self.assertFalse(takvim.gerekiyor_mu('   '))


if __name__ == '__main__':
    unittest.main()
