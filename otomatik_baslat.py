"""Windows açılışında Emre'yi arka planda başlatma.

Başlangıç klasörüne bir kısayol (`EMRE.lnk`) kurulur; kısayol, proje kökünde
üretilen `emre_arkaplan.vbs` dosyasını `wscript` ile sessizce çalıştırır. VBS,
`pythonw.exe server.py` komutunu **konsol penceresi olmadan** başlatır.

- Yalnızca Windows'ta desteklenir; diğer platformlarda açık hata verir.
- Kısayol yalnızca kullanıcının kendi Başlangıç klasörüne yazılır (yönetici izni
  gerekmez, kayıt defterine dokunulmaz).
- Kurulum `confirmed:true` olmadan çalıştırılmaz (sunucu tarafında denetlenir).
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KISAYOL_ADI = 'EMRE.lnk'
VBS_ADI = 'emre_arkaplan.vbs'
AZAMI_BEKLEME = 30


def destekli() -> bool:
    """Otomatik başlatma bu bilgisayarda kurulabilir mi?"""
    return sys.platform == 'win32' and bool(os.environ.get('APPDATA'))


def baslangic_klasoru() -> Path:
    appdata = os.environ.get('APPDATA')
    if not appdata:
        raise ValueError('APPDATA bulunamadı; otomatik başlatma kurulamıyor.')
    return Path(appdata) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'Startup'


def kisayol_yolu() -> Path:
    return baslangic_klasoru() / KISAYOL_ADI


def pythonw() -> Path:
    """Konsol açmayan Python yorumlayıcısı (yoksa mevcut yorumlayıcı)."""
    exe = Path(sys.executable)
    if exe.name.lower() == 'pythonw.exe':
        return exe
    aday = exe.with_name('pythonw.exe')
    return aday if aday.is_file() else exe


def _powershell() -> str:
    kok = Path(os.environ.get('SystemRoot', r'C:\Windows'))
    return str(kok / 'System32' / 'WindowsPowerShell' / 'v1.0' / 'powershell.exe')


def arka_plan_betigi(kok=ROOT) -> Path:
    """Sessiz başlatma için VBS betiğini yazar (değişmemişse yeniden yazmaz)."""
    kok = Path(kok)
    yol = kok / VBS_ADI
    q = 'Chr(34)'
    icerik = (
        "' EMRE: konsol penceresi açmadan sunucuyu başlatır.\r\n"
        "' otomatik_baslat.py tarafından üretilir; elle düzenlemeyin.\r\n"
        'Set kabuk = CreateObject("WScript.Shell")\r\n'
        f'kabuk.CurrentDirectory = "{kok}"\r\n'
        f'kabuk.Run {q} & "{pythonw()}" & {q} & " server.py", 0, False\r\n'
    )
    if not yol.is_file() or yol.read_text(encoding='utf-8', errors='replace') != icerik:
        yol.write_text(icerik, encoding='utf-8')
    return yol


def _calistir(betik: str):
    return subprocess.run([_powershell(), '-NoProfile', '-NonInteractive',
                           '-ExecutionPolicy', 'Bypass', '-Command', betik],
                          capture_output=True, text=True, timeout=AZAMI_BEKLEME)


def _ps_dize(metin: str) -> str:
    """PowerShell tek tırnaklı dize (tek tırnak ikiye katlanır)."""
    return "'" + str(metin).replace("'", "''") + "'"


def kur(kok=ROOT) -> dict:
    """Otomatik başlatmayı kurar ve sonucu döndürür."""
    if not destekli():
        raise ValueError('Otomatik başlatma yalnızca Windows\'ta kurulabilir.')
    kok = Path(kok)
    betik = arka_plan_betigi(kok)
    hedef = kisayol_yolu()
    hedef.parent.mkdir(parents=True, exist_ok=True)
    wscript = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32' / 'wscript.exe'
    simge = kok / 'emre.ico'
    ps = (
        '$s=(New-Object -ComObject WScript.Shell).CreateShortcut(' + _ps_dize(hedef) + ');'
        '$s.TargetPath=' + _ps_dize(wscript) + ';'
        '$s.Arguments=' + _ps_dize('"' + str(betik) + '"') + ';'
        '$s.WorkingDirectory=' + _ps_dize(kok) + ';'
        '$s.WindowStyle=7;'
        '$s.Description=' + _ps_dize('EMRE yerel asistan') + ';'
        + ('$s.IconLocation=' + _ps_dize(str(simge)) + ';' if simge.is_file() else '')
        + '$s.Save()'
    )
    sonuc = _calistir(ps)
    if sonuc.returncode != 0 or not hedef.is_file():
        ayrinti = (sonuc.stderr or sonuc.stdout or '').strip()[:200]
        raise ValueError('Kısayol oluşturulamadı. ' + (ayrinti or 'PowerShell hatası.'))
    return durum(kok)


def kaldir(kok=ROOT) -> dict:
    """Otomatik başlatmayı kaldırır (kısayolu siler, VBS dosyası kalır)."""
    if not destekli():
        raise ValueError('Otomatik başlatma yalnızca Windows\'ta yönetilebilir.')
    hedef = kisayol_yolu()
    silindi = False
    if hedef.exists():
        try:
            hedef.unlink()
            silindi = True
        except OSError as hata:
            raise ValueError(f'Kısayol silinemedi: {hata}')
    return {'silindi': silindi, **durum(kok)}


def durum(kok=ROOT) -> dict:
    """Kurulu mu? (dosya sistemi okunur, komut çalıştırılmaz)"""
    kok = Path(kok)
    destek = destekli()
    yol = None
    kurulu = False
    if destek:
        try:
            yol = str(kisayol_yolu())
            kurulu = Path(yol).is_file()
        except ValueError:
            destek = False
    return {'destekli': destek, 'kurulu': kurulu, 'yol': yol,
            'betik': str(kok / VBS_ADI), 'python': str(pythonw())}
