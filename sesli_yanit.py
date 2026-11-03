"""Akışlı seslendirme ve söz kesme (barge-in) yardımcıları.

Yanıt metni akarken cümle cümle seslendirilir: ilk cümle hazır olur olmaz
konuşma başlar, kalan cümleler arka planda hazırlanır. Böylece 10 saniyelik bir
yanıtın tamamı beklenmez.

Söz kesme (barge-in): konuşma sürerken mikrofon ses düzeyi eşiği belirli sayıda
ardışık ölçümde aşarsa seslendirme durdurulur. Yanlış tetiklemeyi azaltmak için
hiserezis (kısa süreli yükselmeleri yok sayma) uygulanır.

Bu modül **ses üretmez**; yalnızca metni parçalara ayırır ve karar verir. Ses
üretimi tarayıcıda (`/api/tts/speak` çağrılarıyla) yapılır.
"""
import re

AZAMI_CUMLE = 220          # tek seslendirme isteğinin üst sınırı (karakter)
AZAMI_PARCALAR = 40        # tek yanıt için en fazla cümle
KISA_KUYRUK = 12           # akış bittiğinde kalan kırıntı eşiği

# Kısaltmalar: bunlardan sonra cümle bitmiş sayılmaz.
_KISALTMA = ('dr', 'prof', 'sn', 'mr', 'mrs', 'vs', 'vb', 'ör', 'örn', 'yy', 'mm', 'no', 'tel', 'tl')

_BITIS = re.compile(r'(?<=[.!?…])\s+')


def _kisaltma_mi(parca: str) -> bool:
    kelime = parca.strip().split()[-1].lower().rstrip('.') if parca.strip() else ''
    return kelime in _KISALTMA or (len(kelime) == 1 and kelime.isalpha())


def cumlelere_ayir(metin):
    """Metni seslendirilebilir cümlelere böler (kısaltmaları korur)."""
    metin = ' '.join(str(metin or '').split())
    if not metin:
        return []
    parcalar = []
    for ham in _BITIS.split(metin):
        ham = ham.strip()
        if not ham:
            continue
        if parcalar and _kisaltma_mi(parcalar[-1]):
            parcalar[-1] = parcalar[-1] + ' ' + ham  # kısaltmadan sonra bölmeyi geri al
        else:
            parcalar.append(ham)
    sonuc = []
    for parca in parcalar:
        sonuc.extend(_uzun_bol(parca))
    return sonuc[:AZAMI_PARCALAR]


def _uzun_bol(parca: str):
    """Çok uzun cümleyi kelime sınırından parçalara böler."""
    if len(parca) <= AZAMI_CUMLE:
        return [parca]
    kelimeler, parcalar, tampon = parca.split(), [], ''
    for kelime in kelimeler:
        aday = (tampon + ' ' + kelime).strip()
        if len(aday) > AZAMI_CUMLE and tampon:
            parcalar.append(tampon)
            tampon = kelime
        else:
            tampon = aday
    if tampon:
        parcalar.append(tampon)
    return parcalar


class AkisParcalayici:
    """Akan metni cümle cümle dışarı verir.

    Kullanım:
        p = AkisParcalayici()
        for parca in p.besle('Merhaba dünya. Nasıl') : ...
        for parca in p.besle('sın?'): ...
        for parca in p.kapat(): ...   # kalan kırıntı

    İlk cümle 2 karakterden kısaysa bekletilir (yarım kelime seslendirilmesin).
    """

    def __init__(self):
        self._tampon = ''
        self._verilen = 0

    def besle(self, metin):
        """Yeni metin parçası ekler; seslendirilmeye hazır cümleleri döndürür."""
        self._tampon += str(metin or '')
        hazir = []
        while True:
            eslesme = _BITIS.search(self._tampon)
            if not eslesme:
                break
            aday = self._tampon[:eslesme.start()].strip()
            if len(aday) < 2 or _kisaltma_mi(aday):
                # Kısaltmadan sonraki boşlukta bölme: daha fazla metin bekle.
                if len(self._tampon) > AZAMI_CUMLE:
                    aday = self._tampon[:eslesme.end()].strip()
                else:
                    break
            self._tampon = self._tampon[eslesme.end():]
            hazir.extend(_uzun_bol(aday))
        # Çok uzun tek parça birikirse (noktalama yok) yine de böl.
        while len(self._tampon) > AZAMI_CUMLE:
            kesme = self._tampon.rfind(' ', 0, AZAMI_CUMLE)
            if kesme < 40:
                kesme = AZAMI_CUMLE
            hazir.append(self._tampon[:kesme].strip())
            self._tampon = self._tampon[kesme:].lstrip()
        return hazir[:AZAMI_PARCALAR]

    def kapat(self):
        """Akış bittiğinde kalan metni döndürür."""
        kalan = self._tampon.strip()
        self._tampon = ''
        if not kalan:
            return []
        return _uzun_bol(kalan) if len(kalan) > KISA_KUYRUK else [kalan]


class BargeIn:
    """Konuşma sürerken kullanıcı sesini algılayıp seslendirmeyi keser.

    `besle(seviye)` her ses ölçümünde çağrılır; `True` dönerse seslendirme
    durdurulmalıdır. `esik` üstünde `ardisik` ölçüm gerekir; ardından `soguma`
    saniye boyunca yeniden tetiklenmez (çınlama/kendi sesimiz tetiklemesin).
    """

    def __init__(self, esik=0.06, ardisik=3, soguma=1.5):
        self.esik = float(esik)
        self.ardisik = max(1, int(ardisik))
        self.soguma = float(soguma)
        self.sayac = 0
        self._son_tetik = None
        self.tetiklenme = 0

    def besle(self, seviye, simdi=None):
        """Ses düzeyini işler; kesme kararı verilirse True döner."""
        simdi = 0.0 if simdi is None else float(simdi)
        if simdi - (self._son_tetik if self._son_tetik is not None else -1e9) < self.soguma:
            return False
        if float(seviye or 0) < self.esik:
            self.sayac = 0
            return False
        self.sayac += 1
        if self.sayac < self.ardisik:
            return False
        self.sayac = 0
        self._son_tetik = simdi
        self.tetiklenme += 1
        return True

    def sifirla(self):
        """Yeni seslendirme başlarken durumu temizler (soğuma da sıfırlanır)."""
        self.sayac = 0
        self._son_tetik = None
