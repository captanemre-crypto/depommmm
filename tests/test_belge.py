"""Belge okuma, parçalama, arama ve bağlam testleri (hepsi yerel, ağsız)."""
import base64
import io
import json
import sqlite3
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import belge  # noqa: E402


def _docx_olustur(metin):
    """En küçük geçerli .docx üretir (metin paragraflarıyla)."""
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, 'w') as z:
        paragraflar = ''.join(f'<w:p><w:r><w:t>{satır}</w:t></w:r></w:p>' for satır in metin.split('\n'))
        z.writestr('word/document.xml',
                   '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                   f'<w:body>{paragraflar}</w:body></w:document>')
    return tampon.getvalue()


def _pdf_olustur(metin):
    """Sıkıştırılmamış, tek sayfalık basit PDF üretir."""
    icerik = f'BT /F1 12 Tf 72 720 Td ({metin}) Tj ET'.encode('latin-1')
    pdf = (b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n'
           b'2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n'
           b'3 0 obj<</Type/Page/Parent 2 0 R/Contents 4 0 R>>endobj\n'
           b'4 0 obj<</Length ' + str(len(icerik)).encode() +
           b'>>stream\n' + icerik + b'\nendstream endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n')
    return pdf


class MetinCikarmaTest(unittest.TestCase):
    def conn_dummy(self):
        conn = sqlite3.connect(':memory:')
        belge.kur(conn)
        self.addCleanup(conn.close)
        return conn

    def test_plain_text(self):
        self.assertEqual(belge.metin_cikar(b'Merhaba dunya', '.txt'), 'Merhaba dunya')

    def test_utf8_turkish(self):
        self.assertIn('Değerli müşteri', belge.metin_cikar('Değerli müşteri'.encode('utf-8'), '.txt'))

    def test_cp1254_fallback(self):
        ham = 'Zeytin yağı'.encode('cp1254')
        self.assertIn('Zeytin', belge.metin_cikar(ham, '.txt'))

    def test_html_tags_removed(self):
        cikti = belge.metin_cikar(b'<html><body><h1>Baslik</h1><p>Govde</p></body></html>', '.html')
        self.assertIn('Baslik', cikti)
        self.assertIn('Govde', cikti)
        self.assertNotIn('<h1>', cikti)

    def test_html_hidden_parts_skipped(self):
        cikti = belge.metin_cikar(b'<html><head><style>a{color:red}</style></head><body>Gorunur</body></html>', '.html')
        self.assertIn('Gorunur', cikti)
        self.assertNotIn('color:red', cikti)

    def test_docx_paragraphs(self):
        metin = belge.metin_cikar(_docx_olustur('Birinci paragraf\nIkinci paragraf'), '.docx')
        self.assertIn('Birinci paragraf', metin)
        self.assertIn('Ikinci paragraf', metin)

    def test_docx_broken_archive_raises(self):
        with self.assertRaises(ValueError):
            belge.metin_cikar(b'bu bir zip degil', '.docx')

    def test_pdf_text_stream(self):
        metin = belge.metin_cikar(_pdf_olustur('Fatura tutari 1500 TL'), '.pdf')
        self.assertIn('Fatura', metin)

    def test_pdf_without_text_returns_empty(self):
        # Taranmış (OCR gerektiren) PDF'lerde metin bulunmaz; açık hata dosya_ekle'de verilir.
        bos_pdf = b'%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF'
        self.assertEqual(belge.metin_cikar(bos_pdf, '.pdf'), '')
        with tempfile.TemporaryDirectory() as tmp:
            dosya = Path(tmp) / 'tarama.pdf'
            dosya.write_bytes(bos_pdf)
            with self.assertRaises(ValueError):
                belge.dosya_ekle(self.conn_dummy(), dosya)

    def test_unknown_extension_is_read_as_text(self):
        self.assertEqual(belge.metin_cikar(b'x', '.exe'), 'x')


class SayfalamaTest(unittest.TestCase):
    def test_small_text_single_page(self):
        self.assertEqual(len(belge.sayfalara_ayir('kisa metin')), 1)

    def test_form_feed_splits_pages(self):
        self.assertEqual(len(belge.sayfalara_ayir('sayfa bir\x0csayfa iki')), 2)

    def test_empty_text_no_pages(self):
        self.assertEqual(belge.sayfalara_ayir('   '), [])

    def test_page_limit(self):
        metin = '\x0c'.join('x' for _ in range(belge.AZAMI_SAYFA + 50))
        self.assertLessEqual(len(belge.sayfalara_ayir(metin)), belge.AZAMI_SAYFA)

    def test_chunks_cover_text(self):
        metin = ' '.join(f'kelime{i}' for i in range(2000))
        parcalar = belge.parcalara_ayir(metin)
        self.assertGreater(len(parcalar), 1)
        for parca in parcalar:
            self.assertLessEqual(len(parca), belge.Parca_BOY + 50)

    def test_no_infinite_loop_on_short_text(self):
        parcalar = belge.parcalara_ayir('kisa', boy=100, binis=50)
        self.assertEqual(parcalar, ['kisa'])


class VeritabaniTest(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        belge.kur(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_kur_is_idempotent(self):
        belge.kur(self.conn)
        self.assertEqual(belge.listele(self.conn), [])

    def test_add_and_list(self):
        sonuc = belge.ekle(self.conn, 'sozlesme.txt', 'Kira sözleşmesi 12 ay sürer.')
        self.assertEqual(sonuc['pages'], 1)
        kayitlar = belge.listele(self.conn)
        self.assertEqual(len(kayitlar), 1)
        self.assertEqual(kayitlar[0]['name'], 'sozlesme.txt')

    def test_add_empty_rejected(self):
        with self.assertRaises(ValueError):
            belge.ekle(self.conn, 'bos.txt', '   ')

    def test_file_ekle_from_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            dosya = Path(tmp) / 'notlar.md'
            dosya.write_text('# Başlık\nÖdeme planı hazır.', encoding='utf-8')
            sonuc = belge.dosya_ekle(self.conn, dosya)
            self.assertEqual(sonuc['name'], 'notlar.md')
            kayit = belge.listele(self.conn)[0]
            self.assertEqual(kayit['kind'], 'md')

    def test_file_ekle_missing_file(self):
        with self.assertRaises(ValueError):
            belge.dosya_ekle(self.conn, '/olmayan/dosya.txt')

    def test_file_ekle_unsupported(self):
        with tempfile.TemporaryDirectory() as tmp:
            dosya = Path(tmp) / 'program.exe'
            dosya.write_bytes(b'MZ')
            with self.assertRaises(ValueError):
                belge.dosya_ekle(self.conn, dosya)

    def test_icerik_ekle_base64(self):
        ham = base64.b64encode('Base64 içerik.'.encode('utf-8')).decode()
        sonuc = belge.icerik_ekle(self.conn, 'b64.txt', ham)
        self.assertEqual(sonuc['name'], 'b64.txt')

    def test_icerik_ekle_invalid_base64_name(self):
        with self.assertRaises(ValueError):
            belge.icerik_ekle(self.conn, 'dosya.exe', base64.b64encode(b'x').decode())

    def test_icerik_ekle_empty(self):
        with self.assertRaises(ValueError):
            belge.icerik_ekle(self.conn, 'bos.txt', '')

    def test_delete(self):
        sonuc = belge.ekle(self.conn, 'sil.txt', 'Silinecek belge.')
        self.assertEqual(belge.sil(self.conn, sonuc['id']), 1)
        self.assertEqual(belge.listele(self.conn), [])
        self.assertEqual(belge.ara(self.conn, 'silinecek'), [])

    def test_search_accent_insensitive(self):
        belge.ekle(self.conn, 'a.txt', 'Şükrü Bey ödemeyi Çarşamba yapacak.')
        self.assertTrue(belge.ara(self.conn, 'sukru'))
        self.assertTrue(belge.ara(self.conn, 'CARSAMBA'))
        self.assertFalse(belge.ara(self.conn, 'mehmet'))

    def test_search_returns_page_numbers(self):
        metin = 'giriş bölümü\x0c' + 'fatura detayları burada'
        belge.ekle(self.conn, 'cok.txt', metin)
        sonuclar = belge.ara(self.conn, 'fatura')
        self.assertEqual(len(sonuclar), 1)
        self.assertEqual(sonuclar[0]['sayfa'], 2)

    def test_search_scoped_to_document(self):
        a = belge.ekle(self.conn, 'a.txt', 'ortak kelime burada')
        belge.ekle(self.conn, 'b.txt', 'ortak kelime orada')
        sonuclar = belge.ara(self.conn, 'ortak', doc_id=a['id'])
        self.assertTrue(sonuclar)
        self.assertTrue(all(x['doc_id'] == a['id'] for x in sonuclar))

    def test_search_limit(self):
        for i in range(10):
            belge.ekle(self.conn, f'{i}.txt', 'aynı kelime ' + str(i))
        self.assertLessEqual(len(belge.ara(self.conn, 'ayni', limit=3)), 3)

    def test_search_empty_query(self):
        belge.ekle(self.conn, 'a.txt', 'metin')
        self.assertEqual(belge.ara(self.conn, '   '), [])

    def test_baglam_has_numbered_sources(self):
        belge.ekle(self.conn, 'rapor.txt', 'Satışlar arttı.')
        parcalar = belge.ara(self.conn, 'satislar')
        metin = belge.baglam(parcalar)
        self.assertIn('[1]', metin)
        self.assertIn('rapor.txt', metin)
        self.assertIn('uydurma', metin.lower())

    def test_baglam_empty(self):
        self.assertEqual(belge.baglam([]), '')

    def test_ozet_metni(self):
        kayit = {'name': 'a.pdf', 'sayfa': 3, 'metin': 'kisa metin'}
        ozet = belge.ozet_metni(kayit)
        self.assertIn('a.pdf', ozet)
        self.assertIn('sayfa 3', ozet)

    def test_json_yukle(self):
        self.assertEqual(belge.json_yukle('{"a": 1}'), {'a': 1})
        self.assertIsNone(belge.json_yukle('bozuk'))
        self.assertEqual(json.dumps(belge.json_yukle('[1,2]')), '[1, 2]')


if __name__ == '__main__':
    unittest.main()
