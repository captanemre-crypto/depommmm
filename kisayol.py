"""Windows global kısayolu (RegisterHotKey) — dikteyi her uygulamadan açar.

Kısayol basıldığında Emre'ye bir "dikte isteği" düşer. Tarayıcı sayfası açıksa
bu isteği ~1 saniye içinde görüp dikteyi başlatır/durdurur. Sayfa açık değilse
sunucu isteğe bağlı olarak tarayıcıyı dikte sayfasıyla açar (bkz. server.py).

Windows dışında desteklenmez; `baslat()` açık hata verir (sessiz başarısızlık yok).
Kayıt defterine veya sistem ayarlarına dokunulmaz.
"""
import ctypes
import ctypes.wintypes
import sys
import threading

VARSAYILAN = 'ctrl+alt+d'
MODLAR = {'alt': 0x0001, 'ctrl': 0x0002, 'control': 0x0002, 'shift': 0x0004, 'win': 0x0008}
# Kayıt sırasında kullanılan "tekrar basmayı engelle" bayrağı
MOD_NOREPEAT = 0x4000
AZAMI_TUS = 3


def _win32() -> bool:
    return sys.platform == 'win32'


def _user32():
    """user32 modülü (testlerde sahtelenebilmesi için ayrı fonksiyon)."""
    return ctypes.windll.user32


def _kernel32():
    return ctypes.windll.kernel32


def coz(metin):
    """'ctrl+alt+d' → (mod bayrağı, sanal tuş kodu). Geçersizse ValueError."""
    if not isinstance(metin, str) or not metin.strip():
        raise ValueError('Kısayol metni boş olamaz.')
    parcalar = [p.strip().lower() for p in metin.split('+') if p.strip()]
    if not parcalar:
        raise ValueError('Kısayol metni boş olamaz.')
    tus = parcalar[-1]
    modlar = parcalar[:-1]
    if not modlar:
        raise ValueError('Kısayolda en az bir değiştirici tuş olmalı (ctrl, alt, shift, win).')
    if len(modlar) > AZAMI_TUS:
        raise ValueError('En fazla üç değiştirici tuş kullanılabilir.')
    bayrak = 0
    for ad in modlar:
        if ad not in MODLAR:
            raise ValueError(f'Bilinmeyen değiştirici tuş: {ad}')
        bayrak |= MODLAR[ad]
    if len(tus) == 1 and ('a' <= tus <= 'z' or '0' <= tus <= '9'):
        kod = ord(tus.upper())
    elif len(tus) == 1 and tus in '[];,./\\-=`':
        kod = ord(tus.upper())
    elif tus.startswith('f') and tus[1:].isdigit() and 1 <= int(tus[1:]) <= 24:
        kod = 0x6F + int(tus[1:])
    elif tus in MODLAR:
        raise ValueError(f'{tus} bir değiştirici tuş; kısayolun sonunda gerçek bir tuş olmalı.')
    elif tus in ('space', 'boşluk'):
        kod = 0x20
    elif tus in ('enter', 'return'):
        kod = 0x0D
    else:
        raise ValueError(f'Bilinmeyen tuş: {tus}')
    return bayrak, kod


def bicim(metin) -> str:
    """Kısayolu görüntülemek için düzenler: 'ctrl+alt+d' → 'Ctrl+Alt+D'."""
    parcalar = [p.strip() for p in str(metin).split('+') if p.strip()]
    adlar = {'ctrl': 'Ctrl', 'control': 'Ctrl', 'alt': 'Alt', 'shift': 'Shift', 'win': 'Win',
             'space': 'Space', 'enter': 'Enter'}

    def _ad(parca):
        kucuk = parca.lower()
        if kucuk in adlar:
            return adlar[kucuk]
        if len(kucuk) == 1 or (kucuk.startswith('f') and kucuk[1:].isdigit()):
            return kucuk.upper()
        return parca

    return '+'.join(_ad(p) for p in parcalar)


class Kisayol:
    """Global kısayol dinleyicisi. `baslat()` / `durdur()` / `durum()`."""

    def __init__(self, geri_cagri, metin=VARSAYILAN, kimlik=0xE33E):
        self.geri_cagri = geri_cagri
        self.metin = metin
        self.kimlik = kimlik
        self._is_thread = None
        self._calisiyor = threading.Event()
        self._hata = ''
        self._basarili = threading.Event()
        self._kayit_ok = False
        self._thread_id = None
        self.basildi = 0

    # --- durum -----------------------------------------------------------
    def destekli(self) -> bool:
        return _win32()

    def durum(self) -> dict:
        return {'destekli': self.destekli(), 'aktif': bool(self._is_thread and self._is_thread.is_alive()),
                'kisayol': self.metin, 'gorunen': bicim(self.metin),
                'hata': self._hata, 'basildi': self.basildi}

    # --- yaşam döngüsü ---------------------------------------------------
    def baslat(self) -> bool:
        if not self.destekli():
            raise ValueError('Global kısayol yalnızca Windows\'ta çalışır.')
        if self._is_thread and self._is_thread.is_alive():
            return True
        mod, tus = coz(self.metin)  # geçersiz kısayol burada hata verir
        self._calisiyor.set()
        self._basarili.clear()
        self._kayit_ok = False
        self._hata = ''
        self._is_thread = threading.Thread(target=self._dongu, args=(mod, tus), daemon=True)
        self._is_thread.start()
        self._basarili.wait(timeout=5)
        if not self._kayit_ok:
            self.durdur()
            raise ValueError(self._hata or 'Kısayol kaydedilemedi.')
        return True

    def durdur(self) -> bool:
        if not self._is_thread:
            return False
        self._calisiyor.clear()
        if _win32() and self._thread_id:
            try:
                _user32().PostThreadMessageW(self._thread_id, 0x0012, 0, 0)  # WM_QUIT
            except Exception:
                pass
        self._is_thread.join(timeout=3)
        self._is_thread = None
        return True

    def yeniden_basla(self, metin) -> bool:
        """Yeni kısayolla yeniden kaydolur."""
        coz(metin)
        self.durdur()
        self.metin = metin
        return self.baslat()

    # --- iç işleyiş ------------------------------------------------------
    def _dongu(self, mod, tus):
        u32 = _user32()
        k32 = _kernel32()
        try:
            self._thread_id = k32.GetCurrentThreadId()
        except Exception:
            self._thread_id = None
        basarili = False
        try:
            basarili = bool(u32.RegisterHotKey(None, self.kimlik, mod | MOD_NOREPEAT, tus))
        except Exception as hata:
            self._hata = f'Kısayol kaydedilemedi: {hata}'
        if not basarili:
            self._hata = self._hata or (f'{bicim(self.metin)} başka bir program tarafından kullanılıyor olabilir.')
            self._calisiyor.clear()
            self._basarili.set()
            return
        self._kayit_ok = True
        self._basarili.set()
        try:
            msg = ctypes.wintypes.MSG()
            while self._calisiyor.is_set():
                if not u32.GetMessageW(ctypes.byref(msg), None, 0, 0):
                    break
                if msg.message == 0x0312:  # WM_HOTKEY
                    self.basildi += 1
                    try:
                        self.geri_cagri()
                    except Exception:
                        pass
        finally:
            try:
                u32.UnregisterHotKey(None, self.kimlik)
            except Exception:
                pass
            self._calisiyor.clear()
