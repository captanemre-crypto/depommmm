"""Arayüz erişilebilirlik testleri (WCAG AA kontrast + yapısal kontroller).

Tarayıcı çalıştırmadan `index.html` içindeki renk çiftlerini ve temel erişilebilirlik
işaretlerini denetler. Amaç: koyu temada küçük yardımcı metinlerin okunmaz hâle
gelmesini ve yeni panellerin klavye/aria desteğini kaybetmesini yakalamak.
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = (ROOT / 'index.html').read_text(encoding='utf-8')
sys.path.insert(0, str(ROOT))

# (açıklama, ön plan, arka plan) — koyu tema
KOYU = [
    ('gövde metni', '#e7f4f5', '#000000'),
    ('ikincil metin (--muted)', '#78919e', '#071014'),
    ('ayar kartı paragrafı', '#9bb3ba', '#071014'),
    ('sekme yazısı', '#829ba4', '#090f13'),
    ('palet satırı', '#cfe3e6', '#071319'),
    ('palet yardım satırı', '#7b95a1', '#071319'),
    ('palet küçük yazı', '#8fa7b0', '#0e2b33'),
    ('bugün kartı başlığı', '#6fd7d2', '#081217'),
    ('bugün kartı listesi', '#c6dde0', '#081217'),
    ('bugün kartı boş durumu', '#7e97a3', '#081217'),
    ('bugün kartı saati', '#7294a0', '#08131a'),
    ('bugün sayı vurgusu', '#eafcfb', '#081217'),
    ('vurgu rengi', '#58e4e5', '#000000'),
]

# Açık tema çiftleri (beyaz zemin)
ACIK = [
    ('gövde metni', '#0d1b21', '#ffffff'),
    ('ikincil metin', '#4e6a76', '#ffffff'),
    ('vurgu başlığı', '#0a6a6d', '#ffffff'),
    ('bugün kartı metni', '#173842', '#f7fafb'),
    ('palet satırı', '#24404a', '#ffffff'),
]


def parlaklik(renk):
    renk = renk.lstrip('#')
    kanallar = [int(renk[i:i + 2], 16) / 255 for i in (0, 2, 4)]

    def dogrusal(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return (0.2126 * dogrusal(kanallar[0]) + 0.7152 * dogrusal(kanallar[1])
            + 0.0722 * dogrusal(kanallar[2]))


def kontrast(on, arka):
    a, b = parlaklik(on), parlaklik(arka)
    acik, koyu = max(a, b), min(a, b)
    return (acik + 0.05) / (koyu + 0.05)


class KontrastTest(unittest.TestCase):
    def _denetle(self, ciftler, tema):
        for ad, on, arka in ciftler:
            with self.subTest(tema=tema, ad=ad):
                oran = kontrast(on, arka)
                self.assertGreaterEqual(round(oran, 2), 4.5,
                                        f'{ad}: {on} / {arka} kontrast {oran:.2f} (en az 4.5 gerekli)')

    def test_koyu_tema_aa(self):
        self._denetle(KOYU, 'koyu')

    def test_acik_tema_aa(self):
        self._denetle(ACIK, 'acik')

    def test_renkler_hala_kullaniliyor(self):
        """Test edilen renkler CSS içinde gerçekten tanımlı olmalı (bayat test olmasın)."""
        for _, on, _arka in KOYU + ACIK:
            if on in ('#ffffff', '#000000'):
                continue
            self.assertIn(on, HTML, f'{on} artık kullanılmıyor; testi güncelle')


class YapiTest(unittest.TestCase):
    def test_palet_dialog_rolu(self):
        self.assertRegex(HTML, r'id="palette"[^>]*role="dialog"[^>]*aria-modal="true"')
        self.assertIn('aria-label="Komut paleti"', HTML)

    def test_palet_klavye_ipucu_var(self):
        self.assertIn('↑ ↓ gez · Enter çalıştır · Esc kapat', HTML)

    def test_bugun_karti_bolgesi(self):
        self.assertIn('id="todayCard"', HTML)
        self.assertIn('aria-labelledby="todayTitle"', HTML)
        self.assertIn('id="todayTitle"', HTML)

    def test_tum_ayar_sekmeleri_aria(self):
        sekmeler = re.findall(r'<button class="settings-tab[^"]*" id="(\w+)" role="tab" '
                              r'aria-selected="(?:true|false)" aria-controls="settingsBody">', HTML)
        self.assertGreaterEqual(len(sekmeler), 12, sekmeler)
        self.assertIn('gorunumTab', sekmeler)
        self.assertIn('docsTab', sekmeler)
        self.assertIn('calendarTab', sekmeler)

    def test_sohbet_uzunluk_siniri(self):
        self.assertIn('messages.children.length>300', HTML.replace(' ', ''))

    def test_kisayol_yardimi_var(self):
        self.assertIn("e.key==='?'", HTML.replace(' ', ''))
        self.assertIn("ad:'Kısayollar'", HTML.replace(' ', ''))

    def test_hicbir_bolum_henuz_hazir_degil_demiyor(self):
        # Navigasyon ve eylem düğmeleri bağlı olmalı; kullanıcıya "hazırlanmadı" denmemeli.
        self.assertNotIn('bölümü henüz hazırlanmadı', HTML)
        self.assertNotIn('özelliği henüz bağlı değil', HTML)

    def test_her_uc_noktasinin_arayuz_karsiligi_var(self):
        """Sunucudaki her `/api/...` ucu arayüzde ya kullanılmalı ya da bilinçli istisna olmalı.

        Kullanılmayan uçlar ölü kod birikmesini gösterir; bu test yeni bir uç eklenip
        arayüze bağlanmadığında uyarır. İstisnalar gerekçesiyle listelenir.
        """
        import server

        bilincli = {
            # Ekran görüntüsü: /api/screen/ask zaten görüntüyü alıp soruyu yanıtlar;
            # /api/screen/capture yalnızca tanılama/elle deneme için açık bırakıldı.
            '/api/screen/capture',
            # Akışlı seslendirme cümleleri tarayıcıda bölünür (gecikme yok); uç,
            # sunucu tarafında bölmek isteyen istemciler için yardımcı API olarak duruyor.
            '/api/tts/split',
        }
        kaynak = (ROOT / 'server.py').read_text(encoding='utf-8')
        uclar = sorted(set(re.findall(r"path=='(/api/[^']+)'", kaynak)))
        self.assertGreater(len(uclar), 80)
        kullanilmayan = [u for u in uclar if u not in HTML and u not in bilincli]
        self.assertEqual(kullanilmayan, [], f'Arayüze bağlanmamış uçlar: {kullanilmayan}')
        # İstisnalar gerçekten sunucuda tanımlı olmalı (bayat istisna olmasın).
        for uc in bilincli:
            self.assertIn(uc, uclar, f'{uc} artık sunucuda yok; istisnayı kaldır')
        del server

    def test_ozellikler_yukleniyor(self):
        # Yeni sekmeler gerçek bir işlev tanımlıyor mu?
        for kimlik in ('docsTab', 'calendarTab', 'gorunumTab'):
            self.assertIn(f"getElementById('{kimlik}').onclick", HTML)


if __name__ == '__main__':
    unittest.main()
