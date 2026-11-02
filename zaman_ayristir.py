"""Türkçe doğal dilde tarih/saat ayrıştırma (yerel saat).

Sohbetten hatırlatıcı oluşturmak için kullanılır: "yarın 09:00'da hatırlat",
"3 gün sonra", "15 Kasım 14:30", "pazartesi sabah 9" gibi ifadeleri
`datetime` nesnesine çevirir. Belirsiz veya geçmiş bir zaman için None döner;
böylece kayıt sessizce yanlış tarihe yazılmaz.
"""
import re
from datetime import datetime, timedelta

AYLAR = {
    'ocak': 1, 'şubat': 2, 'subat': 2, 'mart': 3, 'nisan': 4, 'mayıs': 5, 'mayis': 5,
    'haziran': 6, 'temmuz': 7, 'ağustos': 8, 'agustos': 8, 'eylül': 9, 'eylul': 9,
    'ekim': 10, 'kasım': 11, 'kasim': 11, 'aralık': 12, 'aralik': 12,
}
GUNLER = {
    'pazartesi': 0, 'salı': 1, 'sali': 1, 'çarşamba': 2, 'carsamba': 2,
    'perşembe': 3, 'persembe': 3, 'cuma': 4, 'cumartesi': 5, 'pazar': 6,
}
# "sabah 9" gibi ifadelerde saat belirtilmemişse kullanılan varsayılanlar.
GUN_BOLUMLERI = {'sabah': 9, 'öğle': 13, 'ogle': 13, 'öğleden sonra': 15,
                 'ogleden sonra': 15, 'akşam': 19, 'aksam': 19, 'gece': 22}

# Ayrıştırmada kullanılan ve hatırlatıcı metninden çıkarılacak kalıplar.
SAAT_KALIBI = r'(?:saat\s*)?(?:[01]?\d|2[0-3])(?:[:.][0-5]\d)?\s*(?:[\'’]?(?:da|de|ta|te))?'
TARIH_KALIPLARI = (
    r'\bbugün\b', r'\byarın\b', r'\böbür\s*gün\b', r'\bobur\s*gun\b', r'\bhaftaya\b',
    r'\b\d{1,3}\s*(?:dakika|saat|gün|gun|hafta)\s*(?:sonra|içinde|icinde)\b',
    r'\byarım\s*saat\s*(?:sonra)?\b',
    r'\b\d{1,2}[./]\d{1,2}(?:[./]\d{2,4})?\b',
    r'\b\d{1,2}\s+' + r'(?:' + '|'.join(AYLAR) + r')(?:\s+\d{2,4})?\b',
    r'\b(?:' + '|'.join(GUNLER) + r')\b',
)
KOMUT_KALIPLARI = (
    r'\bhatırlat(?:ır|ir)?\s*(?:mısın|misin|ır\s*mısın)?\b',
    r'\bhatırla(?:t|talım)?\b', r'\bbana\s+hatırlat\b', r'\bnot\s+al\b',
    r'\balarm\s+kur\b', r'\b(?:beni\s+)?uyar\b', r'\bbildir\b',
)


def tr_lower(text):
    """Türkçe kurallarına uygun küçük harfe çevir (I→ı, İ→i)."""
    return str(text).translate(str.maketrans({'I': 'ı', 'İ': 'i'})).casefold()


def _saat(metin):
    """Metinden (saat, dakika) çıkar. Tutar sayılarıyla karışmamak için dikkatli."""
    eslesme = re.search(r'(?<!\d)([01]?\d|2[0-3])[:.]([0-5]\d)(?!\d)', metin)
    if eslesme:
        return int(eslesme.group(1)), int(eslesme.group(2))
    eslesme = re.search(r'\bsaat\s*([01]?\d|2[0-3])(?:[:.]?([0-5]\d))?(?!\d)', metin)
    if eslesme:
        return int(eslesme.group(1)), int(eslesme.group(2) or 0)
    eslesme = re.search(r"(?<!\d)([01]?\d|2[0-3])\s*['’](?:da|de|ta|te)\b", metin)
    if eslesme:
        return int(eslesme.group(1)), 0
    for kelime, varsayilan in GUN_BOLUMLERI.items():
        konum = metin.find(kelime)
        if konum >= 0:
            sonrasi = metin[konum + len(kelime):konum + len(kelime) + 12]
            eslesme = re.search(r'(?<!\d)([01]?\d|2[0-3])(?!\d)', sonrasi)
            if not eslesme:
                return varsayilan, 0
            saat = int(eslesme.group(1))
            # "akşam 8" = 20:00, "gece 11" = 23:00
            if varsayilan >= 15 and saat < 12:
                saat += 12
            return saat, 0
    return None


def _tarih(metin, simdi):
    """(datetime, göreli_mi, aralık) döndürür; bulunamazsa (None, False, None)."""
    bugun = simdi.date()

    # Göreli ifadeler: "3 gün sonra", "yarım saat sonra"
    eslesme = re.search(r'\b(\d{1,3})\s*(dakika|dak|dk|saat|sa|gün|gun|hafta)\s*(?:sonra|içinde|icinde)\b', metin)
    if eslesme:
        aralik = eslesme.span()
        miktar = int(eslesme.group(1))
        birim = eslesme.group(2)
        delta = {'dakika': timedelta(minutes=miktar), 'dak': timedelta(minutes=miktar),
                 'dk': timedelta(minutes=miktar), 'saat': timedelta(hours=miktar),
                 'sa': timedelta(hours=miktar), 'gün': timedelta(days=miktar),
                 'gun': timedelta(days=miktar), 'hafta': timedelta(weeks=miktar)}[birim]
        return simdi + delta, True, aralik
    if re.search(r'\byarım\s*saat\b', metin):
        return simdi + timedelta(minutes=30), True, re.search(r'\byarım\s*saat\b', metin).span()

    # Açık tarih: 15.11.2026 / 15/11 / 15 Kasım 2026
    eslesme = re.search(r'\b(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?\b', metin)
    if eslesme:
        aralik = eslesme.span()
        gun, ay = int(eslesme.group(1)), int(eslesme.group(2))
        yil = int(eslesme.group(3) or bugun.year)
        if yil < 100:
            yil += 2000
        try:
            return datetime(yil, ay, gun), False, aralik
        except ValueError:
            return None, False, None
    eslesme = re.search(r'\b(\d{1,2})\s+(?:' + '|'.join(AYLAR) + r')(?:\s+(\d{4}))?\b', metin)
    if eslesme:
        aralik = eslesme.span()
        gun = int(eslesme.group(1))
        ay_adi = re.search(r'(?:' + '|'.join(AYLAR) + r')', metin).group(0)
        yil = int(eslesme.group(2) or bugun.year)
        try:
            return datetime(yil, AYLAR[ay_adi], gun), False, aralik
        except ValueError:
            return None, False, None

    # Adlandırılmış günler
    for kalip, gun_farki in ((r'\bbugün\b', 0), (r'\byarın\b', 1), (r'\böbür\s*gün\b|\bobur\s*gun\b', 2), (r'\bhaftaya\b', 7)):
        eslesme = re.search(kalip, metin)
        if eslesme:
            return (datetime.combine(bugun + timedelta(days=gun_farki), datetime.min.time()),
                    False, eslesme.span())

    # Haftanın günü: en yakın gelecek gün
    for ad, hedef in GUNLER.items():
        if re.search(r'\b' + ad + r'\b', metin):
            fark = (hedef - bugun.weekday()) % 7
            fark = fark or 7
            return (datetime.combine(bugun + timedelta(days=fark), datetime.min.time()),
                    False, re.search(r'\b' + ad + r'\b', metin).span())
    return None, False, None


def parse_when(text, now=None, varsayilan_saat=9):
    """Metinden gelecekteki bir datetime çıkar.

    Dönüş: datetime veya None (belirsiz/geçmiş). Saat verilmemişse `varsayilan_saat`.
    """
    simdi = now or datetime.now()
    metin = tr_lower(text)
    tarih, goreli, aralik = _tarih(metin, simdi)
    # Tarih ifadesini metinden çıkar: "15.11.2026 14:30" ifadesindeki 15.11 saat sanılmasın.
    kalan = (metin[:aralik[0]] + ' ' + metin[aralik[1]:]) if aralik else metin
    saat = _saat(kalan)
    if tarih is None:
        if saat is None:
            return None
        aday = simdi.replace(hour=saat[0], minute=saat[1], second=0, microsecond=0)
        return aday if aday > simdi else aday + timedelta(days=1)
    if goreli:
        if saat is not None:
            tarih = tarih.replace(hour=saat[0], minute=saat[1], second=0, microsecond=0)
        return tarih.replace(second=0, microsecond=0)
    saat = saat or (varsayilan_saat, 0)
    aday = tarih.replace(hour=saat[0], minute=saat[1], second=0, microsecond=0)
    if aday <= simdi:
        # Yıl verilmemiş açık tarihlerde gelecek yıla taşı (örn. 1 Ocak).
        if not re.search(r'[./]\d{2,4}\b', metin) and re.search(r'\b\d{1,2}\s+(?:' + '|'.join(AYLAR) + r')\b', metin):
            aday = aday.replace(year=aday.year + 1)
    return aday


def has_reminder_intent(text):
    """Metin hatırlatıcı istiyor mu?"""
    metin = tr_lower(text)
    return any(re.search(k, metin) for k in KOMUT_KALIPLARI)


TEMIZLE_KALIPLARI = (
    r"\b\d{1,2}[./]\d{1,2}(?:[./]\d{2,4})?\b",
    r"\bsaat\s*[01]?\d(?:[:.][0-5]\d)?\b",
    r"(?<!\d)(?:[01]?\d|2[0-3])[:.][0-5]\d(?!\d)",
    r"(?<!\d)(?:[01]?\d|2[0-3])\s*['’](?:da|de|ta|te)\b",
    r"\b\d{1,2}\s+(?:" + "|".join(AYLAR) + r")(?:\s+\d{4})?\b",
    r"\b\d{1,3}\s*(?:dakika|dak|dk|saat|sa|gün|gun|hafta)\s*(?:sonra|içinde|icinde)\b",
    r"\byarım\s*saat(?:\s*sonra)?\b",
    r"\b(?:bugün|yarın|öbür\s*gün|obur\s*gun|haftaya)\b",
    r"\b(?:" + "|".join(GUNLER) + r")\b",
    r"\b(?:sabah|öğle|öğleden\s+sonra|ogle|ogleden\s+sonra|akşam|aksam|gece)\s*(?:[01]?\d|2[0-3])?\b",
    r"['’]\s*(?:da|de|ta|te)\b",
    r"(?<!\d)\b(?:[01]?\d|2[0-3])\b(?=\s*(?:['’]?(?:da|de|ta|te)))",
) + KOMUT_KALIPLARI


def strip_time_and_command(text):
    """Zaman ifadelerini ve hatırlat komutlarını metinden çıkarır."""
    temiz = text
    for kalip in TEMIZLE_KALIPLARI:
        temiz = re.sub(kalip, ' ', temiz, flags=re.I)
    temiz = re.sub(r"(?i)^\s*(?:emre|bana|lütfen|dostum)[\s,]+", '', temiz)
    temiz = re.sub(r"(?i)\b(?:diye|olarak)\b", ' ', temiz)
    temiz = re.sub(r"\s*['’]\s*", ' ', temiz)
    temiz = re.sub(r'\s{2,}', ' ', temiz)
    return temiz.strip(" \t\n.,;:!?-–—_\'’")
