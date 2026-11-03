"""Ekran görüntüsü modülü testleri (gerçek ekran yakalanmaz, sahtelenir)."""
import base64
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import ekran  # noqa: E402

PNG = b'\x89PNG\r\n\x1a\n' + b'0' * 100


class YakalaTest(unittest.TestCase):
    def test_windows_path_used_on_windows(self):
        with mock.patch.object(ekran.sys, 'platform', 'win32'), \
                mock.patch.object(ekran, '_windows_png', return_value=PNG) as win:
            self.assertEqual(ekran.yakala(), PNG)
            win.assert_called_once()

    def test_pillow_path_elsewhere(self):
        with mock.patch.object(ekran.sys, 'platform', 'linux'), \
                mock.patch.object(ekran, '_pillow_png', return_value=PNG) as pil:
            self.assertEqual(ekran.yakala(), PNG)
            pil.assert_called_once()

    def test_size_limit_enforced(self):
        with mock.patch.object(ekran.sys, 'platform', 'linux'), \
                mock.patch.object(ekran, '_pillow_png', return_value=b'x' * (ekran.AZAMI_BAYT + 1)):
            with self.assertRaises(ValueError) as ctx:
                ekran.yakala()
            self.assertIn('büyük', str(ctx.exception))

    def test_base64_roundtrip(self):
        with mock.patch.object(ekran, 'yakala', return_value=PNG):
            kod = ekran.base64_png()
        self.assertEqual(base64.b64decode(kod), PNG)
        self.assertTrue(kod.isascii())

    def test_powershell_script_saves_png(self):
        """PowerShell yolu doğru betiği kuruyor ve dosyayı okuyor (komut çalıştırılmaz)."""
        with mock.patch.object(ekran.subprocess, 'run') as kos:
            kos.return_value = mock.Mock(returncode=0)
            with self.assertRaises(ValueError):
                ekran._windows_png()  # sahte çalıştırmada dosya oluşmaz
        komut = kos.call_args[0][0]
        self.assertEqual(komut[0], str(ekran._powershell()))
        self.assertIn('-NoProfile', komut)
        self.assertIn('System.Drawing', ' '.join(komut))
        self.assertIn('Bypass', komut)

    def test_pillow_missing_gives_clear_error(self):
        with mock.patch.dict(sys.modules, {'PIL': None, 'PIL.ImageGrab': None}):
            with self.assertRaises(ValueError) as ctx:
                ekran._pillow_png()
        self.assertIn('Pillow', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
