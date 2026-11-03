"""Kalıcı bellek ve bilgi grafiği testleri."""
import sqlite3
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import bellek  # noqa: E402


class BellekTest(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        bellek.kur(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_add_and_list(self):
        bellek.ekle(self.conn, 'Ahmet 5000 TL borçlu', kind='borc', subject='Ahmet')
        kayitlar = bellek.hepsi(self.conn)
        self.assertEqual(len(kayitlar), 1)
        self.assertEqual(kayitlar[0]['subject'], 'Ahmet')

    def test_empty_text_rejected(self):
        with self.assertRaises(ValueError):
            bellek.ekle(self.conn, '   ')

    def test_search_is_accent_and_case_insensitive(self):
        bellek.ekle(self.conn, 'Şükrü ile toplantı yapıldı')
        self.assertTrue(bellek.ara(self.conn, 'sukru'))
        self.assertTrue(bellek.ara(self.conn, 'ŞÜKRÜ'))
        self.assertFalse(bellek.ara(self.conn, 'mehmet'))

    def test_search_ranks_multiple_matches_higher(self):
        bellek.ekle(self.conn, 'delta projesi başladı', subject='delta')
        bellek.ekle(self.conn, 'delta toplantısı cuma günü', subject='delta')
        bellek.ekle(self.conn, 'delta', subject='başka')
        sonuc = bellek.ara(self.conn, 'delta projesi toplantı')
        self.assertTrue(sonuc)

    def test_context_block_contains_records(self):
        bellek.ekle(self.conn, 'kullanıcı sabah 7’de kalkıyor', kind='alışkanlık')
        metin = bellek.baglam(self.conn, 'sabah kaçta kalkıyorum')
        self.assertIn('sabah 7', metin)
        self.assertEqual(bellek.baglam(self.conn, 'alakasız konu'), '')

    def test_delete_removes_record(self):
        kid = bellek.ekle(self.conn, 'silinecek kayıt')
        self.assertEqual(bellek.sil(self.conn, kid), 1)
        self.assertEqual(bellek.hepsi(self.conn), [])


class CikarimTest(unittest.TestCase):
    def test_hatirla_prefix(self):
        self.assertEqual(bellek.cikar('hatırla: Ahmet 5000 TL borçlu'),
                         [('not', '', 'Ahmet 5000 TL borçlu')])

    def test_not_al_prefix(self):
        self.assertEqual(bellek.cikar('not al: yarın doktor randevusu'),
                         [('not', '', 'yarın doktor randevusu')])

    def test_identity(self):
        self.assertEqual(bellek.cikar('benim adım Mehmet'), [('kimlik', 'kullanıcı', 'adı Mehmet')])

    def test_phone(self):
        cikti = bellek.cikar("Ahmet'in telefonu 0532 111 22 33")
        self.assertEqual(cikti[0][0], 'kişi')
        self.assertEqual(cikti[0][1], 'Ahmet')
        self.assertIn('0532', cikti[0][2])

    def test_preference(self):
        self.assertIn('tercih', [c[0] for c in bellek.cikar('ben kahve seviyorum')])

    def test_plain_sentence_is_not_stored(self):
        self.assertEqual(bellek.cikar('bugün hava güzel'), [])

    def test_no_duplicates_on_repeat(self):
        c = sqlite3.connect(':memory:')
        bellek.kur(c)
        ilk = bellek.kaydet_cikarimlar(c, 'hatırla: kira 15.000 TL')
        ikinci = bellek.kaydet_cikarimlar(c, 'hatırla: kira 15.000 TL')
        self.assertEqual(len(ilk), 1)
        self.assertEqual(ikinci, [])
        self.assertEqual(len(bellek.hepsi(c)), 1)
        c.close()

    def test_empty_and_long_input(self):
        self.assertEqual(bellek.cikar(''), [])
        self.assertEqual(bellek.cikar('hatırla: ' + 'a' * 3000), [])


if __name__ == '__main__':
    unittest.main()
