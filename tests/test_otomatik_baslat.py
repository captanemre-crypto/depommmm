"""Windows açılışında otomatik başlatma testleri (kısayol gerçekten oluşturulmaz)."""
import os
import pathlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import otomatik_baslat  # noqa: E402


class BaslangicTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ortam = mock.patch.dict(os.environ, {'APPDATA': self.tmp.name})
        self.ortam.start()
        self.platform = mock.patch.object(otomatik_baslat.sys, 'platform', 'win32')
        self.platform.start()

    def tearDown(self):
        self.platform.stop()
        self.ortam.stop()
        self.tmp.cleanup()

    def test_folder_under_appdata(self):
        yol = otomatik_baslat.baslangic_klasoru()
        self.assertTrue(str(yol).startswith(self.tmp.name))
        self.assertEqual(yol.name, 'Startup')

    def test_missing_appdata_raises(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                otomatik_baslat.baslangic_klasoru()

    def test_unsupported_platform(self):
        with mock.patch.object(otomatik_baslat.sys, 'platform', 'linux'):
            self.assertFalse(otomatik_baslat.destekli())
            with self.assertRaises(ValueError):
                otomatik_baslat.kur(ROOT)

    def test_status_reports_not_installed(self):
        durum = otomatik_baslat.durum(ROOT)
        self.assertTrue(durum['destekli'])
        self.assertFalse(durum['kurulu'])
        self.assertIn('EMRE.lnk', durum['yol'])

    def test_background_script_written_once(self):
        kok = Path(self.tmp.name) / 'proje'
        kok.mkdir()
        # Dosya zaman damgası (mtime) bazı dosya sistemlerinde kaba ya da geriye
        # atlayabildiği için CI'da güvenilir değildi. Bunun yerine gerçekten
        # yazma çağrısı yapılıp yapılmadığını sayıyoruz: içerik değişmediyse
        # ikinci çağrı dosyaya dokunmamalı.
        gercek_yaz = pathlib.Path.write_bytes
        yazilanlar = []

        def sayan(yol_, *a, **k):
            yazilanlar.append(str(yol_))
            return gercek_yaz(yol_, *a, **k)

        with mock.patch.object(pathlib.Path, 'write_bytes', sayan):
            yol = otomatik_baslat.arka_plan_betigi(kok)
            otomatik_baslat.arka_plan_betigi(kok)

        self.assertEqual(yazilanlar, [str(yol)], 'değişmemişse yeniden yazmamalı')
        self.assertTrue(yol.is_file())
        icerik = yol.read_bytes().decode('utf-8')
        self.assertIn('server.py', icerik)
        self.assertIn('kabuk.Run', icerik)
        self.assertIn(', 0, False', icerik)  # gizli pencere
        # Metin kipinde yazılsaydı Windows'ta satır sonları '\\r\\r\\n' olurdu.
        self.assertNotIn('\r\r\n', icerik)

    def test_pythonw_preferred(self):
        kok = Path(self.tmp.name) / 'py'
        kok.mkdir()
        (kok / 'pythonw.exe').write_text('', encoding='utf-8')
        with mock.patch.object(otomatik_baslat.sys, 'executable', str(kok / 'python.exe')):
            self.assertEqual(otomatik_baslat.pythonw().name, 'pythonw.exe')

    def test_pythonw_fallback(self):
        kok = Path(self.tmp.name) / 'py2'
        kok.mkdir()
        with mock.patch.object(otomatik_baslat.sys, 'executable', str(kok / 'python.exe')):
            self.assertEqual(otomatik_baslat.pythonw().name, 'python.exe')

    def test_install_runs_powershell_and_verifies_shortcut(self):
        kok = Path(self.tmp.name) / 'proje2'
        kok.mkdir()
        hedef = otomatik_baslat.kisayol_yolu()

        def sahte_calistir(betik):
            hedef.parent.mkdir(parents=True, exist_ok=True)
            hedef.write_text('kisayol', encoding='utf-8')
            self.assertIn('CreateShortcut', betik)
            self.assertIn('wscript.exe', betik)
            return mock.Mock(returncode=0, stdout='', stderr='')

        with mock.patch.object(otomatik_baslat, '_calistir', side_effect=sahte_calistir):
            durum = otomatik_baslat.kur(kok)
        self.assertTrue(durum['kurulu'])

    def test_install_failure_reports_error(self):
        kok = Path(self.tmp.name) / 'proje3'
        kok.mkdir()
        with mock.patch.object(otomatik_baslat, '_calistir',
                               return_value=mock.Mock(returncode=1, stdout='', stderr='izin yok')):
            with self.assertRaises(ValueError) as ctx:
                otomatik_baslat.kur(kok)
        self.assertIn('izin yok', str(ctx.exception))

    def test_remove_deletes_shortcut(self):
        hedef = otomatik_baslat.kisayol_yolu()
        hedef.parent.mkdir(parents=True, exist_ok=True)
        hedef.write_text('kisayol', encoding='utf-8')
        sonuc = otomatik_baslat.kaldir(ROOT)
        self.assertTrue(sonuc['silindi'])
        self.assertFalse(hedef.exists())

    def test_remove_when_missing_is_noop(self):
        sonuc = otomatik_baslat.kaldir(ROOT)
        self.assertFalse(sonuc['silindi'])

    def test_powershell_single_quotes_escaped(self):
        self.assertEqual(otomatik_baslat._ps_dize("C:\\a'b"), "'C:\\a''b'")


if __name__ == '__main__':
    unittest.main()
