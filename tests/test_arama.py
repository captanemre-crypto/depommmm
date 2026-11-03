"""Web araması testleri: ağa çıkılmaz, HTML/JSON yanıtları sahtelenir."""
import io
import json
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import arama  # noqa: E402

LITE_HTML = """
<table>
<tr><td><a rel="nofollow" class="result-link" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fornek.test%2Fa">İlk Sonuç</a></td></tr>
<tr><td class="result-snippet">Birinci sonucun özeti.</td></tr>
<tr><td><a rel="nofollow" class="result-link" href="https://ornek.test/b">İkinci <b>Sonuç</b></a></td></tr>
<tr><td class="result-snippet">İkinci özet.</td></tr>
<tr><td><a class="result-link" href="http://guvensiz.test/c">Güvensiz</a></td></tr>
</table>
"""


def sahte_yanit(metin):
    class Yanit(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False
    return Yanit(metin.encode('utf-8'))


class YardimciTest(unittest.TestCase):
    def test_clean_strips_tags_and_entities(self):
        self.assertEqual(arama.temizle('<b>a</b> &amp; b&nbsp;c'), 'a & b c')

    def test_clean_limits_length(self):
        self.assertLessEqual(len(arama.temizle('x' * 900, 50)), 50)

    def test_redirect_url_unwrapped(self):
        url = arama._temiz_url('//duckduckgo.com/l/?uddg=https%3A%2F%2Fornek.test%2Fa')
        self.assertEqual(url, 'https://ornek.test/a')

    def test_insecure_url_dropped(self):
        self.assertEqual(arama._temiz_url('http://guvensiz.test/a'), '')

    def test_dedup_and_limit(self):
        sonuclar = arama._tekillestir([
            {'baslik': 'a', 'url': 'https://x.test/1', 'ozet': ''},
            {'baslik': 'b', 'url': 'https://x.test/1', 'ozet': ''},
            {'baslik': 'c', 'url': 'https://x.test/2', 'ozet': ''},
        ])
        self.assertEqual([s['url'] for s in sonuclar], ['https://x.test/1', 'https://x.test/2'])

    def test_context_mentions_sources(self):
        metin = arama.baglam([{'baslik': 'A', 'url': 'https://a.test', 'ozet': 'özet'}])
        self.assertIn('https://a.test', metin)
        self.assertIn('kaynak', metin.lower())

    def test_empty_context(self):
        self.assertEqual(arama.baglam([]), '')


class GerekiyorTest(unittest.TestCase):
    def test_current_info_needs_search(self):
        for soru in ('bugün hava nasıl', 'dolar kaç TL', 'son dakika haberleri var mı'):
            self.assertTrue(arama.gerekiyor_mu(soru), soru)

    def test_explicit_command(self):
        for soru in ('internetten bak: python nedir', 'ara: yapay zekâ haberleri', 'bunu araştır'):
            self.assertTrue(arama.gerekiyor_mu(soru), soru)

    def test_person_question(self):
        self.assertTrue(arama.gerekiyor_mu('Mustafa Kemal Atatürk kimdir'))

    def test_plain_chat_does_not_search(self):
        for soru in ('merhaba', 'Ahmet 500 TL borç aldı', 'yarın 09:00 toplantı diye hatırlat', 'teşekkürler'):
            self.assertFalse(arama.gerekiyor_mu(soru), soru)

    def test_empty_input(self):
        self.assertFalse(arama.gerekiyor_mu(''))


class AramaTest(unittest.TestCase):
    def test_lite_results_parsed(self):
        with mock.patch.object(arama, '_istek', return_value=LITE_HTML):
            sonuclar = arama._ddg_lite('test')
        self.assertEqual(sonuclar[0]['baslik'], 'İlk Sonuç')
        self.assertEqual(sonuclar[0]['url'], 'https://ornek.test/a')
        self.assertEqual(sonuclar[0]['ozet'], 'Birinci sonucun özeti.')
        self.assertEqual(len(sonuclar), 2)  # http:// adresi ayrıştırmada elenir
        self.assertFalse(any(s['url'].startswith('http://') for s in sonuclar))

    def test_instant_answer(self):
        govde = json.dumps({'Heading': 'Başlık', 'AbstractText': '<b>Özet</b> metni',
                            'AbstractURL': 'https://ornek.test/ozet',
                            'RelatedTopics': [{'Text': 'İlgili konu', 'FirstURL': 'https://ornek.test/ilgili'}]})
        with mock.patch.object(arama, '_istek', return_value=govde):
            sonuclar = arama._ddg_anlik('test')
        self.assertEqual(sonuclar[0]['ozet'], 'Özet metni')
        self.assertEqual(sonuclar[1]['url'], 'https://ornek.test/ilgili')

    def test_wikipedia_results(self):
        govde = json.dumps({'query': {'search': [
            {'title': 'Ankara', 'snippet': '<span>başkent</span>'}]}})
        with mock.patch.object(arama, '_istek', return_value=govde):
            sonuclar = arama._vikipedi('ankara')
        self.assertEqual(sonuclar[0]['baslik'], 'Ankara')
        self.assertIn('tr.wikipedia.org/wiki/Ankara', sonuclar[0]['url'])
        self.assertEqual(sonuclar[0]['ozet'], 'başkent')

    def test_fallback_to_wikipedia_when_ddg_fails(self):
        wiki = json.dumps({'query': {'search': [{'title': 'Python', 'snippet': 'dil'}]}})

        def istek(url):
            if 'wikipedia' in url:
                return wiki
            raise urllib.error.URLError('engellendi')

        with mock.patch.object(arama, '_istek', side_effect=istek):
            sonuclar = arama.ara('python')
        self.assertEqual(sonuclar[0]['baslik'], 'Python')

    def test_all_sources_failing_returns_empty(self):
        with mock.patch.object(arama, '_istek', side_effect=urllib.error.URLError('yok')):
            self.assertEqual(arama.ara('bir şey'), [])

    def test_empty_query_no_network(self):
        with mock.patch.object(arama, '_istek') as istek:
            self.assertEqual(arama.ara('   '), [])
        istek.assert_not_called()

    def test_limit_is_capped(self):
        cok = [{'baslik': str(i), 'url': f'https://x.test/{i}', 'ozet': ''} for i in range(20)]
        with mock.patch.object(arama, '_ddg_lite', return_value=cok), \
                mock.patch.object(arama, '_ddg_anlik', return_value=[]), \
                mock.patch.object(arama, '_vikipedi', return_value=[]):
            self.assertEqual(len(arama.ara('x', adet=99)), arama.AZAMI_SONUC)

    def test_insecure_url_rejected(self):
        with self.assertRaises(ValueError):
            arama._istek('http://guvensiz.test/')

    def test_oversized_response_rejected(self):
        class Buyuk(io.BytesIO):
            def read(self, n=-1):
                return b'x' * (arama.AZAMI_BAYT + 10)

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        with mock.patch.object(arama.urllib.request, 'urlopen', return_value=Buyuk()):
            with self.assertRaises(ValueError):
                arama._istek('https://ornek.test')


if __name__ == '__main__':
    unittest.main()
