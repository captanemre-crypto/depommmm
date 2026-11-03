"""Kendi kendini kontrol: açılışta ve istenince çalışan tanılama.

Her kontrol `{'ad', 'durum', 'mesaj'}` döndürür; `durum` değeri `ok`, `uyari` veya `hata`.
Amaç "neden çalışmıyor?" sorusunu Emre'nin kendisinin yanıtlayabilmesi: port, veritabanı,
yazma izni, model, sağlayıcı, ses, beceriler, MCP, disk alanı.
"""
import os
import shutil
import socket
import sys
from pathlib import Path

GEREKLI_PYTHON = (3, 10)
AZAMI_DISK_UYARI = 500 * 1024 * 1024  # 500 MB


def _sonuc(ad, durum, mesaj):
    return {'ad': ad, 'durum': durum, 'mesaj': str(mesaj)[:300]}


def python_kontrol():
    surum = sys.version_info
    metin = f'Python {surum.major}.{surum.minor}.{surum.micro}'
    if (surum.major, surum.minor) < GEREKLI_PYTHON:
        return _sonuc('Python', 'hata', metin + ' — en az 3.10 gerekli.')
    return _sonuc('Python', 'ok', metin)


def disk_kontrol(kok=None):
    kok = Path(kok or Path(__file__).resolve().parent)
    try:
        kullanim = shutil.disk_usage(kok)
    except OSError as hata:
        return _sonuc('Disk', 'uyari', f'Disk bilgisi okunamadı: {hata}')
    bos_gb = kullanim.free / (1024 ** 3)
    if kullanim.free < AZAMI_DISK_UYARI:
        return _sonuc('Disk', 'uyari', f'Yalnızca {bos_gb:.1f} GB boş; model indirmeleri başarısız olabilir.')
    return _sonuc('Disk', 'ok', f'{bos_gb:.1f} GB boş alan.')


def yazma_kontrol(kok=None):
    """Proje klasörüne yazılabiliyor mu? (geçici dosya ile denenir, silinir)"""
    kok = Path(kok or Path(__file__).resolve().parent)
    hedef = kok / '.emre_yazma_testi'
    try:
        hedef.write_text('ok', encoding='utf-8')
        hedef.unlink()
    except OSError as hata:
        try:
            hedef.unlink()
        except OSError:
            pass
        return _sonuc('Yazma izni', 'hata', f'Klasöre yazılamıyor: {hata}')
    return _sonuc('Yazma izni', 'ok', f'{kok.name} klasörüne yazılabiliyor.')


def port_kontrol(port=8765, host='127.0.0.1'):
    """Port dinleniyor mu, yoksa boş mu? (yalnızca yerel adres denenir)"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.6)
        if s.connect_ex((host, int(port))) == 0:
            return _sonuc('Port', 'ok', f'{host}:{port} dinleniyor (Emre çalışıyor).')
    return _sonuc('Port', 'uyari', f'{host}:{port} şu anda dinlenmiyor; sunucu kapalı olabilir.')


def veritabani_kontrol(db_yolu=None):
    import sqlite3
    yol = Path(db_yolu or (Path(__file__).resolve().parent / 'emre.sqlite3'))
    try:
        conn = sqlite3.connect(yol, timeout=5)
        try:
            # Şemayı gerçekten oku: bozuk dosya burada hata verir.
            conn.execute('SELECT COUNT(*) FROM sqlite_master').fetchone()
        finally:
            conn.close()
    except sqlite3.Error as hata:
        return _sonuc('Veritabanı', 'hata', f'{yol.name} açılamadı: {hata}')
    boyut = yol.stat().st_size / (1024 * 1024) if yol.is_file() else 0
    return _sonuc('Veritabanı', 'ok', f'{yol.name} açılabiliyor ({boyut:.1f} MB).')


def ollama_kontrol(url='http://127.0.0.1:11434'):
    import json
    import urllib.request
    try:
        with urllib.request.urlopen(url + '/api/tags', timeout=2) as yanit:
            veri = json.load(yanit)
    except Exception:
        return _sonuc('Ollama', 'uyari', 'Ollama çalışmıyor (zorunlu değil; ücretsiz API de kullanılabilir).')
    adet = len(veri.get('models') or [])
    if not adet:
        return _sonuc('Ollama', 'uyari', 'Ollama açık ama yüklü model yok.')
    return _sonuc('Ollama', 'ok', f'Ollama açık, {adet} model yüklü.')


def ses_kontrol(kok=None):
    kok = Path(kok or Path(__file__).resolve().parent)
    venv = kok / '.venv-ses'
    if venv.is_dir():
        return _sonuc('Ses motoru', 'ok', 'Yerel ses tanıma ortamı (.venv-ses) kurulu.')
    return _sonuc('Ses motoru', 'uyari', 'Yerel ses ortamı yok; ses_kur.bat ile kurulabilir.')


def beceri_kontrol(kok=None):
    kok = Path(kok or (Path(__file__).resolve().parent / 'beceriler'))
    if not kok.is_dir():
        return _sonuc('Beceriler', 'uyari', 'beceriler/ klasörü yok.')
    adet = sum(1 for p in kok.iterdir() if p.is_dir() and (p / 'SKILL.md').is_file())
    if not adet:
        return _sonuc('Beceriler', 'uyari', 'Henüz beceri yok.')
    return _sonuc('Beceriler', 'ok', f'{adet} beceri bulundu.')


def mcp_kontrol(kok=None):
    kok = Path(kok or Path(__file__).resolve().parent)
    dosya = kok / 'mcp_ayar.json'
    if not dosya.is_file():
        return _sonuc('MCP', 'uyari', 'mcp_ayar.json yok (isteğe bağlı).')
    import json
    try:
        veri = json.loads(dosya.read_text(encoding='utf-8'))
        adet = len(veri.get('sunucular') or [])
    except (OSError, ValueError) as hata:
        return _sonuc('MCP', 'hata', f'mcp_ayar.json okunamadı: {hata}')
    return _sonuc('MCP', 'ok', f'{adet} MCP sunucusu tanımlı.')


def platform_kontrol():
    if sys.platform == 'win32':
        return _sonuc('Platform', 'ok', 'Windows: dikte yazımı, otomatik başlatma ve global kısayol kullanılabilir.')
    return _sonuc('Platform', 'uyari', f'{sys.platform}: Windows’a özel özellikler (dikte yazımı, kısayol) kapalı.')


def calistir(db_yolu=None, kok=None, port=8765):
    """Tüm kontrolleri çalıştırır: {'checks': [...], 'ozet': {...}}"""
    kok = Path(kok or Path(__file__).resolve().parent)
    kontroller = [
        python_kontrol(),
        platform_kontrol(),
        disk_kontrol(kok),
        yazma_kontrol(kok),
        veritabani_kontrol(db_yolu or kok / 'emre.sqlite3'),
        port_kontrol(port),
        ollama_kontrol(),
        ses_kontrol(kok),
        beceri_kontrol(kok / 'beceriler'),
        mcp_kontrol(kok),
    ]
    ozet = {'ok': sum(1 for k in kontroller if k['durum'] == 'ok'),
            'uyari': sum(1 for k in kontroller if k['durum'] == 'uyari'),
            'hata': sum(1 for k in kontroller if k['durum'] == 'hata')}
    ozet['mesaj'] = (f"{ozet['ok']} kontrol iyi, {ozet['uyari']} uyarı, {ozet['hata']} hata."
                     if ozet['hata'] else f"{ozet['ok']} kontrol iyi" +
                     (f", {ozet['uyari']} uyarı." if ozet['uyari'] else '.'))
    return {'checks': kontroller, 'ozet': ozet, 'platform': os.name}
