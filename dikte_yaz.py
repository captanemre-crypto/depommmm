"""Dikte metnini etkin pencereye yazan Windows yardımcısı.

Tasarım kuralları
- **Yalnızca Windows.** Diğer platformlarda açık hata verir (sessizce başarısız olmaz).
- **Yalnızca metin yazar.** Komut çalıştırmaz, dosya açmaz, tuş kombinasyonu göndermez
  (Enter isteğe bağlı ve tek başına).
- **Hedef pencere doğrulanır:** `hedef` verilirse yazma yalnızca etkin pencerenin
  başlığı bu metni içeriyorsa yapılır. Böylece metin yanlış uygulamaya gitmez.
- Türkçe karakterler `SendInput` + `KEYEVENTF_UNICODE` ile gönderilir; panoya dokunulmaz.
"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_KEYUP = 0x0002
VK_RETURN = 0x0D
VK_CONTROL, VK_V = 0x11, 0x56
INPUT_KEYBOARD = 1
EN_UZUN = 4000  # tek seferde yazılacak en fazla karakter


class _BIRLESIK(ctypes.Structure):
    _fields_ = [('wVk', wt.WORD), ('wScan', wt.WORD), ('dwFlags', wt.DWORD),
                ('time', wt.DWORD), ('dwExtraInfo', ctypes.c_size_t)]


class _GIRDI(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [('ki', _BIRLESIK)]
    _anonymous_ = ('u',)
    _fields_ = [('type', wt.DWORD), ('u', _U)]


def _gonder(*girdiler):
    """SendInput çağrısı; testlerde bu fonksiyon değiştirilir."""
    user32 = ctypes.windll.user32
    dizi = (_GIRDI * len(girdiler))(*girdiler)
    gonderilen = user32.SendInput(len(girdiler), dizi, ctypes.sizeof(_GIRDI))
    if gonderilen != len(girdiler):
        raise OSError('Tuş gönderilemedi (SendInput).')


def _tus(vk=0, tarama=0, bayrak=0):
    return _GIRDI(type=INPUT_KEYBOARD,
                  ki=_BIRLESIK(wVk=vk, wScan=tarama, dwFlags=bayrak, time=0, dwExtraInfo=0))


def _unicode_kodlari(metin):
    for karakter in metin:
        kod = ord(karakter)
        if kod > 0xFFFF:
            kod -= 0x10000
            yield 0xD800 + (kod >> 10)
            yield 0xDC00 + (kod & 0x3FF)
        else:
            yield kod


def etkin_baslik():
    """Etkin pencerenin başlığı (Windows dışında boş)."""
    if sys.platform != 'win32':
        return ''
    try:
        user32 = ctypes.windll.user32
        pencere = user32.GetForegroundWindow()
        uzunluk = user32.GetWindowTextLengthW(pencere)
        tampon = ctypes.create_unicode_buffer(uzunluk + 1)
        user32.GetWindowTextW(pencere, tampon, uzunluk + 1)
        return tampon.value
    except Exception:
        return ''


def yaz(metin, hedef='', enter=False, bekleme=0.02):
    """Metni etkin pencereye yazar. Hata durumunda `ValueError` yükseltir."""
    if sys.platform != 'win32':
        raise ValueError('Canlı yazma yalnızca Windows üzerinde çalışır.')
    metin = str(metin or '')
    if not metin.strip():
        raise ValueError('Yazılacak metin boş.')
    if len(metin) > EN_UZUN:
        raise ValueError(f'Tek seferde en fazla {EN_UZUN} karakter yazılabilir.')
    if any(k in metin for k in ('\x00', '\r')):
        raise ValueError('Metin satır sonu veya geçersiz karakter içermemeli.')
    hedef = str(hedef or '').strip()
    if hedef:
        baslik = etkin_baslik()
        if hedef.lower() not in baslik.lower():
            raise ValueError(f'Etkin pencere “{baslik or "bilinmiyor"}” hedefle eşleşmiyor. '
                             f'Yazmak istediğin pencereyi öne getir ({hedef}).')
    try:
        for kod in _unicode_kodlari(metin):
            _gonder(_tus(tarama=kod, bayrak=KEYEVENTF_UNICODE),
                    _tus(tarama=kod, bayrak=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP))
            if bekleme:
                time.sleep(bekleme)
        if enter:
            _gonder(_tus(vk=VK_RETURN), _tus(vk=VK_RETURN, bayrak=KEYEVENTF_KEYUP))
    except OSError as hata:
        raise ValueError(str(hata))
    return {'ok': True, 'yazilan': len(metin), 'enter': bool(enter), 'pencere': etkin_baslik()}
