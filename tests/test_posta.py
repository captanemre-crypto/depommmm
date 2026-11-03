"""Yerel `.eml` / `.mbox` posta okuma testleri (salt okunur, ağsız)."""
import base64
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import posta  # noqa: E402


def _eml(konu='Merhaba', kimden='Ahmet <ahmet@ornek.com>', kime='emre@ornek.com',
         tarih='Fri, 06 Nov 2026 09:30:00 +0300', govde='Bu bir test iletisi.', ek=None):
    satirlar = [f'From: {kimden}', f'To: {kime}', f'Subject: {konu}', f'Date: {tarih}', 'MIME-Version: 1.0']
    if ek:
        sinir = 'sinir123'
        satirlar += [f'Content-Type: multipart/mixed; boundary="{sinir}"', '',
                     f'--{sinir}', 'Content-Type: text/plain; charset=utf-8', '', govde,
                     f'--{sinir}', f'Content-Type: application/octet-stream; name="{ek}"',
                     f'Content-Disposition: attachment; filename="{ek}"',
                     'Content-Transfer-Encoding: base64', '', base64.b64encode(b'ek icerik').decode(),
                     f'--{sinir}--']
    else:
        satirlar += ['Content-Type: text/plain; charset=utf-8', '', govde]
    return '\n'.join(satirlar) + '\n'


class EmlTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.yol = Path(self.tmp.name)

    def _yaz(self, ad, icerik):
        dosya = self.yol / ad
        dosya.write_text(icerik, encoding='utf-8')
        return dosya

    def test_headers_and_preview(self):
        dosya = self._yaz('a.eml', _eml())
        mesaj = posta.eml_oku(dosya)[0]
        self.assertEqual(mesaj['konu'], 'Merhaba')
        self.assertIn('ahmet@ornek.com', mesaj['kimden'])
        self.assertIn('test iletisi', mesaj['onizleme'])
        self.assertTrue(mesaj['tarih'].startswith('2026-11-06T09:30'), mesaj['tarih'])
        self.assertFalse(mesaj['ek_var'])
        self.assertEqual(mesaj['kaynak'], 'a.eml')

    def test_attachment_flagged(self):
        dosya = self._yaz('a.eml', _eml(ek='rapor.pdf'))
        self.assertTrue(posta.eml_oku(dosya)[0]['ek_var'])

    def test_base64_subject_decoded(self):
        icerik = ('From: a@b.com\nTo: c@d.com\nSubject: =?utf-8?b?'
                  + base64.b64encode('Türkçe konu'.encode('utf-8')).decode() + '?=\n\nGovde\n')
        dosya = self._yaz('b.eml', icerik)
        self.assertEqual(posta.eml_oku(dosya)[0]['konu'], 'Türkçe konu')

    def test_html_only_body_is_stripped(self):
        icerik = ('From: a@b.com\nTo: c@d.com\nSubject: HTML\n'
                  'Content-Type: text/html; charset=utf-8\n\n<p>Merhaba <b>dunya</b></p>\n')
        dosya = self._yaz('c.eml', icerik)
        onizleme = posta.eml_oku(dosya)[0]['onizleme']
        self.assertIn('Merhaba', onizleme)
        self.assertNotIn('<b>', onizleme)

    def test_missing_file(self):
        with self.assertRaises(ValueError):
            posta.eml_oku(self.yol / 'yok.eml')

    def test_subjectless_message(self):
        icerik = 'From: a@b.com\nTo: c@d.com\n\nGovde\n'
        self.assertEqual(posta.eml_oku(self._yaz('d.eml', icerik))[0]['konu'], '(konusuz)')

    def test_klasor_oku(self):
        self._yaz('a.eml', _eml(konu='Bir'))
        self._yaz('b.eml', _eml(konu='İki'))
        self.assertEqual(len(posta.klasor_oku(self.yol)), 2)

    def test_klasor_missing(self):
        with self.assertRaises(ValueError):
            posta.klasor_oku(self.yol / 'yok')


class MboxTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.yol = Path(self.tmp.name)

    def test_mbox_two_messages(self):
        icerik = ('From a@b.com Fri Nov  6 09:30:00 2026\n' + _eml(konu='Birinci') + '\n'
                  'From a@b.com Fri Nov 06 10:30:00 2026\n' + _eml(konu='İkinci') + '\n')
        dosya = self.yol / 'arsiv.mbox'
        dosya.write_text(icerik, encoding='utf-8')
        mesajlar = posta.mbox_oku(dosya)
        self.assertEqual(len(mesajlar), 2)
        self.assertIn('İkinci', [m['konu'] for m in mesajlar])

    def test_mbox_missing(self):
        with self.assertRaises(ValueError):
            posta.mbox_oku(self.yol / 'yok.mbox')

    def test_yolu_oku_dispatch(self):
        eml = self.yol / 'tek.eml'
        eml.write_text(_eml(konu='Tek'), encoding='utf-8')
        self.assertEqual(posta.yolu_oku(eml)[0]['konu'], 'Tek')
        self.assertEqual(len(posta.yolu_oku(self.yol)), 1)

    def test_yolu_oku_missing(self):
        with self.assertRaises(ValueError):
            posta.yolu_oku(self.yol / 'olmayan')


class OzetTest(unittest.TestCase):
    def _mesaj(self, konu, tarih):
        return {'kimden': 'a@b.com', 'kime': 'c@d.com', 'konu': konu, 'tarih': tarih,
                'onizleme': 'onizleme metni', 'ek_var': False, 'kaynak': 'a.eml'}

    def test_sirala_newest_first(self):
        mesajlar = [self._mesaj('Eski', '2026-11-01T09:00'), self._mesaj('Yeni', '2026-11-06T09:00')]
        self.assertEqual([m['konu'] for m in posta.sirala(mesajlar)], ['Yeni', 'Eski'])

    def test_sirala_without_date(self):
        mesajlar = [self._mesaj('Tarihsiz', ''), self._mesaj('Tarihli', '2026-11-06T09:00')]
        self.assertEqual([m['konu'] for m in posta.sirala(mesajlar)], ['Tarihli', 'Tarihsiz'])

    def test_metin_ozet(self):
        ozet = posta.metin_ozet([self._mesaj('Fatura', '2026-11-06T09:00')], adet=5)
        self.assertIn('Fatura', ozet)
        self.assertIn('2026-11-06', ozet)

    def test_metin_ozet_limit(self):
        mesajlar = [self._mesaj(f'M{i}', f'2026-11-0{i + 1}T09:00') for i in range(10)]
        ozet = posta.metin_ozet(mesajlar, adet=3)
        self.assertIn('Son 3 ileti', ozet)
        self.assertNotIn('M0 ', ozet)  # en eski ileti listeye girmez

    def test_metin_ozet_empty(self):
        self.assertIn('ileti bulunamadı', posta.metin_ozet([]))


class GerekiyorTest(unittest.TestCase):
    def test_mail_questions(self):
        for metin in ('son mailleri özetle', 'e-posta var mı', 'gelen kutusu göster'):
            self.assertTrue(posta.gerekiyor_mu(metin), metin)

    def test_plain_statements(self):
        for metin in ('merhaba', 'mail', 'fatura öde'):
            self.assertFalse(posta.gerekiyor_mu(metin), metin)

    def test_empty(self):
        self.assertFalse(posta.gerekiyor_mu(''))


if __name__ == '__main__':
    unittest.main()
