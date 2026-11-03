"""Masaüstü bildirimi testleri (gerçek bildirim göstermez)."""
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import bildirim  # noqa: E402


class TemizleTest(unittest.TestCase):
    def test_whitespace_collapsed(self):
        self.assertEqual(bildirim._temizle('  a\n\t b  '), 'a b')

    def test_length_limited(self):
        self.assertEqual(len(bildirim._temizle('x' * 500)), bildirim.AZAMI_KARAKTER)

    def test_none_becomes_empty(self):
        self.assertEqual(bildirim._temizle(None), '')


class GosterTest(unittest.TestCase):
    def test_empty_text_does_nothing(self):
        with mock.patch.object(bildirim.subprocess, 'Popen') as popen:
            self.assertFalse(bildirim.goster('başlık', '   '))
        popen.assert_not_called()

    def test_windows_uses_powershell_balloon(self):
        with mock.patch.object(bildirim.sys, 'platform', 'win32'), \
                mock.patch.object(bildirim.subprocess, 'Popen') as popen:
            self.assertTrue(bildirim.goster('Hatırlatıcı', 'Kira ödemesi'))
        komut = popen.call_args[0][0]
        self.assertIn('-NoProfile', komut)
        self.assertIn('NotifyIcon', ' '.join(komut))
        self.assertIn('Kira ödemesi', ' '.join(komut))

    def test_quotes_escaped(self):
        with mock.patch.object(bildirim.sys, 'platform', 'win32'), \
                mock.patch.object(bildirim.subprocess, 'Popen') as popen:
            bildirim.goster("a'b", "O'Brien aradı")
        betik = popen.call_args[0][0][-1]
        self.assertIn("O''Brien", betik)

    def test_missing_notify_send_returns_false(self):
        with mock.patch.object(bildirim.sys, 'platform', 'linux'), \
                mock.patch.object(bildirim.shutil, 'which', return_value=None):
            self.assertFalse(bildirim.goster('b', 'metin'))

    def test_linux_uses_notify_send(self):
        with mock.patch.object(bildirim.sys, 'platform', 'linux'), \
                mock.patch.object(bildirim.shutil, 'which', return_value='/usr/bin/notify-send'), \
                mock.patch.object(bildirim.subprocess, 'Popen') as popen:
            self.assertTrue(bildirim.goster('b', 'metin'))
        self.assertEqual(popen.call_args[0][0][0], '/usr/bin/notify-send')

    def test_launch_failure_is_swallowed(self):
        with mock.patch.object(bildirim.sys, 'platform', 'win32'), \
                mock.patch.object(bildirim.subprocess, 'Popen', side_effect=OSError('yok')):
            self.assertFalse(bildirim.goster('b', 'metin'))

    def test_beep_outside_windows_is_false(self):
        with mock.patch.object(bildirim.sys, 'platform', 'linux'):
            self.assertFalse(bildirim.cal())

    def test_popen_flags_avoid_console(self):
        with mock.patch.object(bildirim.sys, 'platform', 'win32'), \
                mock.patch.object(bildirim.subprocess, 'Popen') as popen:
            bildirim.goster('b', 'm')
        self.assertIs(popen.call_args[1]['stdout'], subprocess.DEVNULL)


if __name__ == '__main__':
    unittest.main()
