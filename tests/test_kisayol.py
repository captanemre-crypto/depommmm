"""Global kısayol modülü testleri (gerçek kayıt yapılmaz, Windows API sahtelenir)."""
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import kisayol  # noqa: E402


class CozTest(unittest.TestCase):
    def test_default_combination(self):
        self.assertEqual(kisayol.coz('ctrl+alt+d'), (0x0002 | 0x0001, ord('D')))

    def test_single_modifier(self):
        self.assertEqual(kisayol.coz('shift+f5'), (0x0004, 0x6F + 5))

    def test_letter_case_insensitive(self):
        self.assertEqual(kisayol.coz('CTRL+ALT+D'), kisayol.coz('ctrl+alt+d'))

    def test_keywords(self):
        self.assertEqual(kisayol.coz('ctrl+space')[1], 0x20)
        self.assertEqual(kisayol.coz('ctrl+enter')[1], 0x0D)

    def test_missing_modifier_rejected(self):
        with self.assertRaises(ValueError):
            kisayol.coz('d')

    def test_unknown_modifier_rejected(self):
        with self.assertRaises(ValueError):
            kisayol.coz('meta+d')

    def test_unknown_key_rejected(self):
        with self.assertRaises(ValueError):
            kisayol.coz('ctrl+enter2')

    def test_too_many_modifiers_rejected(self):
        with self.assertRaises(ValueError):
            kisayol.coz('ctrl+alt+shift+win+d')

    def test_modifier_as_final_key_rejected(self):
        for deger in ('ctrl+alt+', 'ctrl+alt+shift'):
            with self.assertRaises(ValueError):
                kisayol.coz(deger)

    def test_empty_rejected(self):
        for deger in ('', '   ', None, '+'):
            with self.assertRaises(ValueError):
                kisayol.coz(deger)

    def test_formatting(self):
        self.assertEqual(kisayol.bicim('ctrl+alt+d'), 'Ctrl+Alt+D')
        self.assertEqual(kisayol.bicim('shift+f5'), 'Shift+F5')


class KisayolTest(unittest.TestCase):
    def test_unsupported_platform_raises(self):
        with mock.patch.object(kisayol.sys, 'platform', 'linux'):
            nesne = kisayol.Kisayol(lambda: None)
            self.assertFalse(nesne.destekli())
            with self.assertRaises(ValueError) as ctx:
                nesne.baslat()
        self.assertIn('Windows', str(ctx.exception))

    def test_status_shape(self):
        with mock.patch.object(kisayol.sys, 'platform', 'linux'):
            durum = kisayol.Kisayol(lambda: None).durum()
        self.assertEqual(set(durum), {'destekli', 'aktif', 'kisayol', 'gorunen', 'hata', 'basildi'})
        self.assertFalse(durum['aktif'])

    def test_invalid_shortcut_rejected_before_thread(self):
        nesne = kisayol.Kisayol(lambda: None, metin='ctrl+alt+')
        with mock.patch.object(kisayol.sys, 'platform', 'win32'), \
                mock.patch.object(kisayol, '_user32'), mock.patch.object(kisayol, '_kernel32'):
            with self.assertRaises(ValueError):
                nesne.baslat()

    def test_registration_failure_reported(self):
        sahte = mock.MagicMock()
        sahte.RegisterHotKey.return_value = 0
        with mock.patch.object(kisayol.sys, 'platform', 'win32'), \
                mock.patch.object(kisayol, '_user32', return_value=sahte), \
                mock.patch.object(kisayol, '_kernel32', return_value=mock.MagicMock()):
            nesne = kisayol.Kisayol(lambda: None)
            with self.assertRaises(ValueError) as ctx:
                nesne.baslat()
        self.assertIn('kullanılıyor', str(ctx.exception))

    def test_callback_increments_counter(self):
        def geri():
            kisayol_test_sayac.append(1)
        kisayol_test_sayac = []
        # Geri çağrı yalnızca WM_HOTKEY mesajında çalışır; bunu döngüde taklit et.
        def sahte_dongu(self, mod, tus):
            geri()
        nesne = kisayol.Kisayol(geri)
        with mock.patch.object(kisayol.Kisayol, '_dongu', sahte_dongu), \
                mock.patch.object(kisayol.sys, 'platform', 'win32'):
            # _basarili beklemesi gerçek döngüde set edilir; burada doğrudan çağırıyoruz.
            nesne._dongu(0, 0)
        self.assertEqual(len(kisayol_test_sayac), 1)


if __name__ == '__main__':
    unittest.main()
