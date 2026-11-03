"""Uyandırma sözcüğü (wake word) kapısı.

Emre'nin adı cümlenin **herhangi bir yerinde** geçebilir: "yarın hava nasıl
olacak Emre" ya da "Emre, yarın hava nasıl". Bu modül metni inceler,
uyandırma sözcüğünü temizler ve kalan komutu döndürür.

Neden metin düzeyinde?
- Eldeki ses hattı zaten yerel Whisper ile metne çeviriyor; ayrı bir ses modeli
  indirmek gerekmiyor.
- Yanlış tetiklenme riski yok: mikrofon açıkken konuşulan her şey kaydedilmiyor,
  yalnızca uyandırma sözcüğü geçen cümleler komut sayılıyor.

İsteğe bağlı olarak `openwakeword` kuruluysa (ses düzeyinde tespit) o da
kullanılabilir; bkz. `ses_ile_var()`.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
AYAR = ROOT / 'uyandirma_ayar.json'

# Varsayılan uyandırma ifadeleri (küçük harf, Türkçe).
VARSAYILAN = ('emre', 'hey emre')
AZAMI_KELIME = 60


def _sadelestir(metin):
    return ' '.join(str(metin or '').lower().replace('’', "'").split())


def _sinir(ifade):
    """İfadeyi kelime sınırlarıyla eşleşen bir regex'e çevirir."""
    parcalar = [re.escape(p) for p in ifade.split()]
    return r'(?<![a-zçğıöşü0-9])' + r'\s+'.join(parcalar) + r'(?![a-zçğıöşü0-9])'


def ayikla(metin, kelimeler=VARSAYILAN):
    """Metinde uyandırma sözcüğü var mı? Varsa temizlenmiş komutu döndürür.

    Dönüş: (uyandirildi: bool, komut: str)
    """
    sade = _sadelestir(metin)
    if not sade:
        return False, ''
    kalan = sade
    bulundu = False
    # Uzun ifadeler önce denenir ("hey emre" > "emre").
    for ifade in sorted({_sadelestir(k) for k in kelimeler if str(k).strip()}, key=len, reverse=True):
        yeni, sayi = re.subn(_sinir(ifade), ' ', kalan)
        if sayi:
            bulundu = True
            kalan = yeni
    if not bulundu:
        return False, ''
    komut = ' '.join(kalan.split()).strip(' ,.;:!?…')
    return True, komut[:2000]


def ayar_yolu(yol=None):
    return Path(yol) if yol else AYAR


def ayar_oku(yol=None):
    """Ayar dosyasını okur; bozuksa varsayılana döner."""
    try:
        veri = json.loads(ayar_yolu(yol).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        veri = {}
    if not isinstance(veri, dict):
        veri = {}
    kelimeler = veri.get('kelimeler')
    if not isinstance(kelimeler, list) or not kelimeler:
        kelimeler = list(VARSAYILAN)
    kelimeler = [str(k).strip().lower() for k in kelimeler if str(k).strip()][:6]
    # Varsayılan olarak KAPALI: mikrofon açıkken her cümlenin komut sayılmaması için
    # kullanıcı bilinçli olarak açar (Ayarlar › Ses).
    return {'aktif': bool(veri.get('aktif', False)), 'kelimeler': kelimeler or list(VARSAYILAN)}


def ayar_yaz(aktif=None, kelimeler=None, yol=None):
    """Ayarları kaydeder (atomik yazma)."""
    mevcut = ayar_oku(yol)
    if aktif is not None:
        mevcut['aktif'] = bool(aktif)
    if kelimeler is not None:
        temiz = [str(k).strip().lower() for k in kelimeler if str(k).strip()]
        if not temiz:
            raise ValueError('En az bir uyandırma sözcüğü gerekli.')
        if len(temiz) > 6:
            raise ValueError('En fazla 6 uyandırma sözcüğü tanımlanabilir.')
        if any(len(k) > 40 for k in temiz):
            raise ValueError('Uyandırma sözcüğü çok uzun.')
        mevcut['kelimeler'] = temiz
    hedef = ayar_yolu(yol)
    gecici = hedef.with_suffix('.tmp')
    gecici.write_text(json.dumps(mevcut, ensure_ascii=False, indent=2), encoding='utf-8')
    gecici.replace(hedef)
    return mevcut


def ses_ile_var():
    """`openwakeword` ses düzeyinde tespit için kurulu mu? (isteğe bağlı)"""
    try:
        import openwakeword  # noqa: F401
        return True
    except Exception:
        return False
