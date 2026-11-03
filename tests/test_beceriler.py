"""Beceri sistemi testleri: gerçek alt süreçler, geçici beceri klasörleri."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import beceriler  # noqa: E402

SKILL = """---
ad: deneme
aciklama: Deneme becerisi
tetik: deneme, test et
komut: {komut}
---
Açıklama gövdesi.
"""


class BeceriTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kok = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def beceri_ekle(self, ad='deneme', komut=None, icerik=None, betik=None):
        klasor = self.kok / ad
        klasor.mkdir(parents=True, exist_ok=True)
        if icerik is None:
            icerik = SKILL.format(komut=komut or 'python calistir.py')
        (klasor / 'SKILL.md').write_text(icerik, encoding='utf-8')
        if betik is not None:
            (klasor / 'calistir.py').write_text(betik, encoding='utf-8')
        return klasor

    # --- ayrıştırma ------------------------------------------------------
    def test_empty_folder_lists_nothing(self):
        self.assertEqual(beceriler.listele(self.kok), [])

    def test_missing_root_lists_nothing(self):
        self.assertEqual(beceriler.listele(self.kok / 'yok'), [])

    def test_metadata_is_parsed(self):
        self.beceri_ekle()
        beceri = beceriler.listele(self.kok)[0]
        self.assertEqual(beceri['ad'], 'deneme')
        self.assertEqual(beceri['aciklama'], 'Deneme becerisi')
        self.assertEqual(beceri['tetik'], ['deneme', 'test et'])
        self.assertTrue(beceri['calistirilabilir'])
        self.assertIn('gövdesi', beceri['ayrinti'])

    def test_folder_without_skill_md_skipped(self):
        (self.kok / 'bos').mkdir()
        self.assertEqual(beceriler.listele(self.kok), [])

    def test_invalid_folder_name_reported(self):
        (self.kok / 'Kötü Ad').mkdir()
        (self.kok / 'Kötü Ad' / 'SKILL.md').write_text('---\nad: x\n---\n', encoding='utf-8')
        kayit = beceriler.listele(self.kok)[0]
        self.assertIn('geçersiz', kayit['hata'])

    def test_skill_without_command_is_description_only(self):
        self.beceri_ekle(komut='', icerik='---\nad: deneme\naciklama: sadece açıklama\n---\n')
        beceri = beceriler.listele(self.kok)[0]
        self.assertFalse(beceriler.listele(self.kok)[0]['calistirilabilir'])
        with self.assertRaises(ValueError) as ctx:
            beceriler.calistir('deneme', 'x', kok=self.kok)
        self.assertIn('komutu yok', str(ctx.exception))
        self.assertTrue(beceri['aciklama'])

    def test_bul_by_folder_and_name(self):
        self.beceri_ekle()
        self.assertIsNotNone(beceriler.bul('deneme', self.kok))
        self.assertIsNone(beceriler.bul('yok', self.kok))
        self.assertIsNone(beceriler.bul('../../etc', self.kok))

    # --- eşleştirme ------------------------------------------------------
    def test_keyword_match(self):
        self.beceri_ekle()
        eslesen = beceriler.esles('bunu test et lütfen', self.kok)
        self.assertEqual(eslesen[0]['klasor'], 'deneme')

    def test_no_match(self):
        self.beceri_ekle()
        self.assertEqual(beceriler.esles('merhaba', self.kok), [])

    def test_explicit_command_parsing(self):
        self.assertEqual(beceriler.acik_komut('!deneme abc def'), ('deneme', 'abc def'))
        self.assertEqual(beceriler.acik_komut('!deneme'), ('deneme', ''))
        self.assertEqual(beceriler.acik_komut('merhaba'), (None, 'merhaba'))
        self.assertEqual(beceriler.acik_komut('!BÜYÜK x'), (None, '!BÜYÜK x'))

    def test_context_lists_skills(self):
        self.beceri_ekle()
        metin = beceriler.baglam(self.kok)
        self.assertIn('!deneme', metin)
        self.assertIn('Deneme becerisi', metin)

    def test_context_empty_without_skills(self):
        self.assertEqual(beceriler.baglam(self.kok), '')

    # --- çalıştırma ------------------------------------------------------
    def test_runs_and_reads_json_reply(self):
        self.beceri_ekle(betik='import json,sys\nd=json.load(sys.stdin)\n'
                               'print(json.dumps({"reply":"aldım: "+d["metin"]}, ensure_ascii=False))\n')
        sonuc = beceriler.calistir('deneme', 'selam', kok=self.kok)
        self.assertEqual(sonuc['reply'], 'aldım: selam')
        self.assertEqual(sonuc['klasor'], 'deneme')
        self.assertGreaterEqual(sonuc['sure'], 0)

    def test_plain_text_output_is_used(self):
        self.beceri_ekle(betik='print("düz metin yanıt")\n')
        self.assertEqual(beceriler.calistir('deneme', '', kok=self.kok)['reply'], 'düz metin yanıt')

    def test_python_alias_uses_current_interpreter(self):
        self.beceri_ekle(betik='import sys\nprint(sys.executable)\n')
        sonuc = beceriler.calistir('deneme', '', kok=self.kok)
        self.assertEqual(Path(sonuc['reply']).name, Path(sys.executable).name)

    def test_error_exit_reports_stderr(self):
        self.beceri_ekle(betik='import sys\nsys.stderr.write("bozuk")\nsys.exit(2)\n')
        with self.assertRaises(ValueError) as ctx:
            beceriler.calistir('deneme', '', kok=self.kok)
        self.assertIn('bozuk', str(ctx.exception))

    def test_empty_output_rejected(self):
        self.beceri_ekle(betik='pass\n')
        with self.assertRaises(ValueError) as ctx:
            beceriler.calistir('deneme', '', kok=self.kok)
        self.assertIn('boş', str(ctx.exception))

    def test_timeout_is_reported(self):
        self.beceri_ekle(betik='import time\ntime.sleep(5)\n')
        with self.assertRaises(ValueError) as ctx:
            beceriler.calistir('deneme', '', kok=self.kok, zaman=0.3)
        self.assertIn('bitmedi', str(ctx.exception))

    def test_missing_binary(self):
        self.beceri_ekle(komut='olmayan-komut-xyz --yardim')
        with self.assertRaises(ValueError) as ctx:
            beceriler.calistir('deneme', '', kok=self.kok)
        self.assertIn('bulunamadı', str(ctx.exception))

    def test_unknown_skill(self):
        with self.assertRaises(ValueError):
            beceriler.calistir('yok', '', kok=self.kok)

    def test_long_input_truncated(self):
        self.beceri_ekle(betik='import json,sys\nd=json.load(sys.stdin)\nprint(len(d["metin"]))\n')
        self.assertEqual(beceriler.calistir('deneme', 'x' * 5000, kok=self.kok)['reply'], '2000')

    def test_output_truncated(self):
        self.beceri_ekle(betik=f'print("y"*{beceriler.AZAMI_KARAKTER + 500})\n')
        self.assertEqual(len(beceriler.calistir('deneme', '', kok=self.kok)['reply']), beceriler.AZAMI_KARAKTER)

    def test_shell_metacharacters_are_not_executed(self):
        self.beceri_ekle(komut='olmayan-komut ; echo tehlikeli')
        with self.assertRaises(ValueError):
            beceriler.calistir('deneme', '', kok=self.kok)

    def test_skill_limit(self):
        for i in range(beceriler.AZAMI_BECERI + 3):
            self.beceri_ekle(ad=f'b{i}')
        self.assertLessEqual(len(beceriler.listele(self.kok)), beceriler.AZAMI_BECERI)

    def test_project_sample_skill_runs(self):
        """Depodaki örnek beceri gerçekten çalışıyor."""
        sonuc = beceriler.calistir('metin-analiz', 'bir iki üç')
        self.assertIn('3 kelime', sonuc['reply'])

    def test_run_with_patched_root(self):
        self.beceri_ekle(betik='print("kok testi")\n')
        with mock.patch.object(beceriler, 'KOK', self.kok):
            self.assertEqual(beceriler.calistir('deneme', '')['reply'], 'kok testi')


class KomutAyristirmaTest(unittest.TestCase):
    def test_shlex_quotes(self):
        # Tırnaklı argümanlar tek parça kalmalı; kabuk yorumu yapılmaz.
        parcalar = beceriler.shlex.split('python -c "print(1)"')
        self.assertEqual(parcalar, ['python', '-c', 'print(1)'])

    def test_json_reply_shape_documented(self):
        self.assertEqual(json.loads('{"reply": "a"}')['reply'], 'a')


if __name__ == '__main__':
    unittest.main()
