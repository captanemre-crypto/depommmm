"""Windows'a yazma yardımcısının güvenlik kuralları (gerçek tuş gönderilmez)."""
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import dikte_yaz  # noqa: E402


class DikteYazTest(unittest.TestCase):
    def setUp(self):
        self.gonderilen = []
        self.yama = mock.patch.object(dikte_yaz, '_gonder', side_effect=lambda *g: self.gonderilen.append(g))
        self.yama.start()
        self.platform = mock.patch.object(dikte_yaz.sys, 'platform', 'win32')
        self.platform.start()
        self.baslik = mock.patch.object(dikte_yaz, 'etkin_baslik', return_value='Antigravity — chat')
        self.baslik.start()

    def tearDown(self):
        self.baslik.stop()
        self.platform.stop()
        self.yama.stop()

    def test_writes_every_character_as_unicode(self):
        sonuc = dikte_yaz.yaz('Merhaba çğış', bekleme=0)
        self.assertTrue(sonuc['ok'])
        self.assertEqual(sonuc['yazilan'], len('Merhaba çğış'))
        # Her karakter için tek çağrı: bas + bırak (iki girdi).
        self.assertEqual(len(self.gonderilen), len('Merhaba çğış'))
        self.assertTrue(all(len(g) == 2 for g in self.gonderilen))

    def test_turkish_characters_use_unicode_scan_code(self):
        dikte_yaz.yaz('ç', bekleme=0)
        bas = self.gonderilen[0][0].ki
        self.assertEqual(bas.wScan, ord('ç'))
        self.assertEqual(bas.dwFlags & dikte_yaz.KEYEVENTF_UNICODE, dikte_yaz.KEYEVENTF_UNICODE)

    def test_enter_sends_return_key(self):
        dikte_yaz.yaz('tamam', enter=True, bekleme=0)
        son = self.gonderilen[-1]
        self.assertEqual(son[0].ki.wVk, dikte_yaz.VK_RETURN)

    def test_target_mismatch_is_refused(self):
        with self.assertRaises(ValueError) as ctx:
            dikte_yaz.yaz('gizli', hedef='Visual Studio Code', bekleme=0)
        self.assertIn('eşleşmiyor', str(ctx.exception))
        self.assertEqual(self.gonderilen, [])

    def test_target_match_is_allowed(self):
        sonuc = dikte_yaz.yaz('selam', hedef='antigravity', bekleme=0)
        self.assertTrue(sonuc['ok'])

    def test_empty_text_rejected(self):
        with self.assertRaises(ValueError):
            dikte_yaz.yaz('   ', bekleme=0)

    def test_newline_rejected(self):
        with self.assertRaises(ValueError):
            dikte_yaz.yaz('bir\r\niki', bekleme=0)

    def test_too_long_rejected(self):
        with self.assertRaises(ValueError):
            dikte_yaz.yaz('a' * (dikte_yaz.EN_UZUN + 1), bekleme=0)

    def test_non_windows_refused(self):
        with mock.patch.object(dikte_yaz.sys, 'platform', 'linux'):
            with self.assertRaises(ValueError) as ctx:
                dikte_yaz.yaz('selam', bekleme=0)
        self.assertIn('Windows', str(ctx.exception))

    def test_send_failure_becomes_value_error(self):
        with mock.patch.object(dikte_yaz, '_gonder', side_effect=OSError('SendInput başarısız')):
            with self.assertRaises(ValueError):
                dikte_yaz.yaz('selam', bekleme=0)

    def test_surrogate_pair_handled(self):
        # Emoji gibi BMP dışı karakterler iki kod birimine ayrılır.
        dikte_yaz.yaz('a😀', bekleme=0)
        # 'a' tek kod birimi, emoji iki kod birimi → 3 çağrı.
        self.assertEqual(len(self.gonderilen), 3)
        self.assertEqual(self.gonderilen[1][0].ki.wScan, 0xD83D)


if __name__ == '__main__':
    unittest.main()
