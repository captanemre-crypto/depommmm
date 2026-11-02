"""Arena köprüsü durum makinesi testleri (sahte Playwright katmanı, ağ yok)."""
import sys
import time
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import arena_bridge  # noqa: E402


class SahteLocator:
    def __init__(self, sayfa, tur):
        self.sayfa = sayfa
        self.tur = tur

    def count(self):
        if self.tur == 'kutu':
            return 1
        return self.sayfa.cevap_sayisi

    @property
    def first(self):
        return self

    @property
    def last(self):
        return self

    def fill(self, metin):
        self.sayfa.soru = metin

    def press(self, tus):
        self.sayfa.gonderildi = True
        self.sayfa.gonderim_zamani = time.monotonic()

    def inner_text(self, timeout=None):
        return self.sayfa.cevap


class SahteSayfa:
    def __init__(self, cevap='Sahte yanıt', kapan=True, cevapla=True, kapanma_gecikmesi=1.5):
        self.cevap = cevap
        self.cevapla = cevapla
        self.kapan = kapan
        self.url = 'https://arena.ai/agent'
        self.cevap_sayisi = 0
        self.soru = ''
        self.gonderildi = False
        self.poll = 0
        self.kapanma_gecikmesi = kapanma_gecikmesi
        self.gonderim_zamani = None
        self._kapali = False

    def is_closed(self):
        return self._kapali

    def wait_for_timeout(self, ms):
        time.sleep(0.005)  # gerçek zamanlı bekleme: kararlılık ölçümü ilerlesin
        if self.gonderildi:
            if self.cevapla:
                self.cevap_sayisi = 1
            self.poll += 1
            # Yanıt okunduktan bir süre sonra sekmeyi kapat (gerçek kullanıcı davranışı).
            if self.kapan and self.gonderim_zamani and time.monotonic() - self.gonderim_zamani > self.kapanma_gecikmesi:
                self._kapali = True

    def locator(self, secici):
        if 'textarea' in secici:
            return SahteLocator(self, 'kutu')
        return SahteLocator(self, 'cevap')

    def goto(self, url, **kwargs):
        self.url = url


class SahteContext:
    def __init__(self, sayfa):
        self.pages = [sayfa]
        self.kapandi = False

    def close(self):
        self.kapandi = True


class SahtePlaywright:
    def __init__(self, sayfa):
        self.sayfa = sayfa
        self.chromium = types.SimpleNamespace(launch_persistent_context=self._baslat)

    def _baslat(self, *args, **kwargs):
        return SahteContext(self.sayfa)


class Yonetici:
    """`with sync_playwright() as p:` bağlam yöneticisi."""

    def __init__(self, sahte):
        self.sahte = sahte

    def __enter__(self):
        return self.sahte

    def __exit__(self, *args):
        return False


class ArenaBridgeTest(unittest.TestCase):
    def setUp(self):
        self.orijinal_modul = sys.modules.get('playwright.sync_api')
        self.eski_timeout = arena_bridge.ANSWER_TIMEOUT_SECONDS
        self.eski_stabil = arena_bridge.STABLE_SECONDS
        arena_bridge.ANSWER_TIMEOUT_SECONDS = 2
        arena_bridge.STABLE_SECONDS = 0.2
        arena_bridge.update(status='stopped', message='', answer='', answer_verified=False)
        arena_bridge.started = False

    def tearDown(self):
        self.bekle(lambda: arena_bridge.snapshot()['status'] in ('stopped', 'error'), 6)
        if self.orijinal_modul is None:
            sys.modules.pop('playwright.sync_api', None)
            sys.modules.pop('playwright', None)
        else:
            sys.modules['playwright.sync_api'] = self.orijinal_modul
        arena_bridge.update(status='stopped', message='', answer='', answer_verified=False)
        arena_bridge.started = False
        arena_bridge.ANSWER_TIMEOUT_SECONDS = self.eski_timeout
        arena_bridge.STABLE_SECONDS = self.eski_stabil

    def modul_kur(self, sayfa):
        sahte = SahtePlaywright(sayfa)
        modul = types.ModuleType('playwright.sync_api')
        modul.sync_playwright = lambda: Yonetici(sahte)
        sys.modules['playwright.sync_api'] = modul
        return sahte

    def bekle(self, kosul, saniye=10):
        import time
        bitis = time.monotonic() + saniye
        while time.monotonic() < bitis:
            if kosul():
                return True
            time.sleep(0.02)
        return False

    def test_send_before_ready_is_rejected(self):
        with self.assertRaises(ValueError):
            arena_bridge.send('merhaba')

    def test_question_length_is_validated(self):
        arena_bridge.update(status='ready')
        with self.assertRaises(ValueError):
            arena_bridge.send('')
        with self.assertRaises(ValueError):
            arena_bridge.send('a' * 6001)

    def test_missing_playwright_reports_error(self):
        sys.modules['playwright.sync_api'] = None  # import hatası üretir
        arena_bridge.start()
        self.assertTrue(self.bekle(lambda: arena_bridge.snapshot()['status'] == 'error'))
        self.assertIn('Playwright kurulu değil', arena_bridge.snapshot()['message'])

    def test_answer_is_captured(self):
        sayfa = SahteSayfa(cevap='Toplantı yarın 10:00.')
        self.modul_kur(sayfa)
        arena_bridge.start()
        self.assertTrue(self.bekle(lambda: arena_bridge.snapshot()['status'] == 'ready'))
        arena_bridge.send('Yarın toplantı var mı?')
        self.assertTrue(self.bekle(lambda: arena_bridge.snapshot()['answer'] == 'Toplantı yarın 10:00.'))
        self.assertFalse(arena_bridge.snapshot()['answer_verified'])
        self.assertEqual(sayfa.soru, 'Yarın toplantı var mı?')
        self.assertTrue(sayfa.gonderildi)

    def test_no_answer_reports_friendly_error(self):
        sayfa = SahteSayfa(cevap='', cevapla=False, kapan=False)
        self.modul_kur(sayfa)
        arena_bridge.started = False
        arena_bridge.update(status='stopped', message='')
        arena_bridge.start()
        # Yanıt alanı hiç dolmuyor: 120 saniyelik bekleme yerine hızlı hata beklenir.
        self.assertTrue(self.bekle(lambda: arena_bridge.snapshot()['status'] == 'ready', 6))
        arena_bridge.update(status='ready')
        arena_bridge.send('Soru')
        self.assertTrue(self.bekle(lambda: 'Yanıt güvenilir biçimde bulunamadı' in arena_bridge.snapshot()['message'], 15))


if __name__ == '__main__':
    unittest.main()
