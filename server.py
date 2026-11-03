"""EMRE local server: standard-library only. Run on Windows: py server.py"""
import base64
import contextlib
import json
import os
import re
import secrets
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote_plus, urlparse

import arama
import arena_bridge
import beceriler
import belge
import bellek
import bildirim
import denetim
import dikte
import dikte_yaz
import ekran
import hatirlatici
import kisayol
import ledger_tools
import mcp_istemci
import otomatik_baslat
import posta
import saglayici
import ses_baglanti
import sesli_yanit
import takvim
import tanilama
import telegram_bot
import tts_piper_bridge
import uyandirma

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'emre.sqlite3'
OLLAMA = 'http://127.0.0.1:11434'
OPENJARVIS = 'http://127.0.0.1:8766'
MODEL = os.getenv('EMRE_MODEL', 'qwen2.5-coder:7b')
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
KEY = secrets.token_urlsafe(32)
VERSION = '2026-11-03.7'
SYSTEM = 'Adın Emre. Türkçe konuşan yardımcı bir asistansın. Kısa, doğal ve samimi Türkçe konuş; kullanıcıya sen diye hitap et. Yalnızca sorulan sorunun cevabını ver. Cevaptan sonra ek açıklama, öneri, teklif veya takip sorusu ekleme. Her mesajın sonunda soru sorma; özellikle size nasıl yardımcı olabilirim, nasıl yardımcı olabilirim veya başka bir şey var mı gibi kalıpları tekrar etme. Kullanıcının adı bilinmiyor; ona Emre diye seslenme, Emre senin adın. Mikrofonu doğrudan duyduğunu iddia etme; yalnızca sana iletilen metni okuyorsun. Başka dilde gereksiz sözcük kullanma. Doğrudan istenen yanıtı ver. Yapmadığın işlemleri yapmış gibi söyleme. Kullanıcının izni olmadan mesaj gönderme, program çalıştırma veya dosya değiştirme.'

_INITIALIZED = set()

VARSAYILAN_AYARLAR = {
    'kisayol_aktif': '0',
    'kisayol_tus': kisayol.VARSAYILAN,
    'kisayol_tarayici': '1',
    'bildirim_aktif': '1',
    'tts_akis': '1',
    'barge_in': '1',
    'takvim_yolu': '',
    'posta_yolu': '',
}


def ayar_al(conn, ad, varsayilan=''):
    """settings tablosundan tek bir ayar okur; yoksa varsayılanı döndürür."""
    try:
        satir = conn.execute('SELECT value FROM settings WHERE key=?', (ad,)).fetchone()
    except sqlite3.Error:
        return varsayilan
    return satir[0] if satir else varsayilan


def kota_artir(basarili=True, yedek=False):
    """Günlük sağlayıcı kullanım sayacı (yerel, yalnızca istatistik)."""
    gun = datetime.now().strftime('%Y-%m-%d')
    try:
        with db() as c:
            c.execute('INSERT INTO provider_usage(day,requests,errors,fallback) VALUES (?,1,0,?) '
                      'ON CONFLICT(day) DO UPDATE SET requests=requests+1, '
                      'errors=errors+excluded.errors, fallback=fallback+excluded.fallback',
                      (gun, 1 if yedek else 0))
            if not basarili:
                c.execute('UPDATE provider_usage SET errors=errors+1 WHERE day=?', (gun,))
    except Exception:
        pass


def kota_ozet(gun=7):
    """Son `gun` günün kullanım özeti."""
    gun = max(1, min(int(gun or 7), 90))
    with db() as c:
        satirlar = c.execute('SELECT day,requests,errors,fallback FROM provider_usage '
                             'ORDER BY day DESC LIMIT ?', (gun,)).fetchall()
        bugun = c.execute('SELECT requests,errors,fallback FROM provider_usage WHERE day=?',
                          (datetime.now().strftime('%Y-%m-%d'),)).fetchone() or (0, 0, 0)
    return {'bugun': {'requests': bugun[0], 'errors': bugun[1], 'fallback': bugun[2]},
            'gunler': [{'gun': r[0], 'requests': r[1], 'errors': r[2], 'fallback': r[3]} for r in satirlar]}


def _denetle(kind, action, detail='', status='ok'):
    """Denetim izine kayıt düşer; hata olursa işlemi bozmaz."""
    try:
        with db() as c:
            denetim.kaydet(c, kind, action, detail, status)
    except Exception:
        pass


def ayar_yaz(conn, ad, deger):
    conn.execute('INSERT INTO settings(key,value) VALUES(?,?) '
                 'ON CONFLICT(key) DO UPDATE SET value=excluded.value', (ad, str(deger)))


def _init_schema(conn, path):
    """Tabloları ve kolonları oluşturur; süreç başına yalnızca bir kez çalışır."""
    if path in _INITIALIZED:
        return
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY, text TEXT NOT NULL, due TEXT NOT NULL, done INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS ledger (id INTEGER PRIMARY KEY, person TEXT NOT NULL, kind TEXT NOT NULL, amount INTEGER NOT NULL, note TEXT NOT NULL DEFAULT "", due TEXT, created TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY, name TEXT NOT NULL COLLATE NOCASE UNIQUE, note TEXT NOT NULL DEFAULT "");
        CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, session TEXT NOT NULL, role TEXT NOT NULL, text TEXT NOT NULL, created TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS telegram_messages (id INTEGER PRIMARY KEY, update_id INTEGER UNIQUE, chat_id INTEGER, sender TEXT, text TEXT, date INTEGER, read INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS telegram_state (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, kind TEXT NOT NULL, action TEXT NOT NULL,
            detail TEXT NOT NULL DEFAULT "", status TEXT NOT NULL DEFAULT "ok", created TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS docs (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            kind TEXT NOT NULL DEFAULT "", pages INTEGER NOT NULL DEFAULT 0, chars INTEGER NOT NULL DEFAULT 0,
            created TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS doc_chunks (id INTEGER PRIMARY KEY AUTOINCREMENT, doc_id INTEGER NOT NULL,
            sayfa INTEGER NOT NULL DEFAULT 0, metin TEXT NOT NULL, arama TEXT NOT NULL DEFAULT "");
        CREATE TABLE IF NOT EXISTS provider_usage (day TEXT PRIMARY KEY, requests INTEGER NOT NULL DEFAULT 0,
            errors INTEGER NOT NULL DEFAULT 0, fallback INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY, kind TEXT NOT NULL, title TEXT NOT NULL, text TEXT NOT NULL, created TEXT NOT NULL, seen INTEGER DEFAULT 0);
        CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session, id);
        CREATE INDEX IF NOT EXISTS idx_ledger_person ON ledger(person);
    """)
    # Eski veritabanları için denetim izi kolonları (A6)
    columns = {row[1] for row in conn.execute('PRAGMA table_info(ledger)')}
    if 'source' not in columns:
        conn.execute('ALTER TABLE ledger ADD COLUMN source TEXT')
    if 'raw_text' not in columns:
        conn.execute('ALTER TABLE ledger ADD COLUMN raw_text TEXT')
    # Hatırlatıcının bir kez bildirildiğini işaretleyen kolon (A3)
    belge.kur(conn)
    rcolumns = {row[1] for row in conn.execute('PRAGMA table_info(reminders)')}
    if 'notified' not in rcolumns:
        conn.execute('ALTER TABLE reminders ADD COLUMN notified INTEGER DEFAULT 0')
    _INITIALIZED.add(path)


@contextlib.contextmanager
def db():
    """Open a short-lived connection that commits on success and always closes.

    Yuvalanmis (nested) baglanti acmak dosya tanimlayicisi sizdirir; bu nedenle
    her istek kendi baglantisini acip kapatiyor. WAL modu es zamanli okumalarda
    'database is locked' hatasini azaltir.
    """
    conn = sqlite3.connect(DB, timeout=10)
    try:
        bellek.kur(conn)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
        conn.execute('PRAGMA busy_timeout=10000')
        _init_schema(conn, str(DB))
        yield conn
        conn.commit()
    except BaseException:
        try: conn.rollback()
        except sqlite3.Error: pass
        raise
    finally:
        conn.close()


BOT = telegram_bot.TelegramBot(lambda: db())
SAG = saglayici.Saglayici()
MCP = mcp_istemci.Yonetici()

# --- Canlı dikte oturumları -------------------------------------------------
# Her oturum: kullanıcının o ana kadar dikte ettiği metin (sunucuda tutulur ki
# üst üste binen ses pencerelerinin tekrarı ayıklanabilsin). Bellek sınırlıdır.
DIKTE = {}
DIKTE_KILIT = threading.RLock()  # dikte_oturum() aynı kilidi içeriden kullanır
DIKTE_AZAMI_OTURUM = 32
DIKTE_AZAMI_KARAKTER = 8000


# --- Global kısayol (dikteyi her uygulamadan başlatma) ----------------------
# Kısayol basıldığında sıra numarası artar; açık sayfa bunu görüp dikteyi açar.
KISAYOL_DURUM = {'seq': 0, 'son': 0.0, 'son_yoklama': 0.0}
KISAYOL_KILIT = threading.Lock()
KISAYOL_ESKI_PENCERE = 15.0  # sayfa bu süredir yoklamıyorsa tarayıcı açılır


def _kisayol_geri_cagri():
    """Kısayol basıldı: sıra numarasını artır, gerekirse tarayıcıyı aç."""
    simdi = time.time()
    with KISAYOL_KILIT:
        KISAYOL_DURUM['seq'] += 1
        KISAYOL_DURUM['son'] = simdi
        sayfa_yok = (simdi - KISAYOL_DURUM['son_yoklama']) > KISAYOL_ESKI_PENCERE
    if sayfa_yok:
        try:
            with db() as c:
                ac = ayar_al(c, 'kisayol_tarayici', '1') == '1'
            if ac:
                import webbrowser
                webbrowser.open('http://127.0.0.1:8765/?dikte=1')
        except Exception:
            pass


KISAYOL = kisayol.Kisayol(_kisayol_geri_cagri)


# --- Hatırlatıcı arka plan işçisi -------------------------------------------
# Tarayıcı kapalı olsa da süresi gelen hatırlatıcılar burada yakalanır: veritabanına
# bildirim yazılır, istenirse masaüstü balonu ve bip sesi gösterilir. Her hatırlatıcı
# yalnızca bir kez bildirilir (`reminders.notified`).
try:
    BILDIRIM_ARALIK = max(int(os.getenv('EMRE_BILDIRIM_ARALIK', '20')), 1)
except ValueError:
    BILDIRIM_ARALIK = 20
BILDIRIM_DURDUR = threading.Event()
_BILDIRIM_ISCI = None


def bildirim_tara(simdi=None):
    """Süresi gelmiş ve henüz bildirilmemiş hatırlatıcıları işler."""
    simdi = simdi or datetime.now()
    esik = simdi.strftime('%Y-%m-%dT%H:%M:59')
    with db() as c:
        satirlar = c.execute('SELECT id,text,due FROM reminders '
                             'WHERE done=0 AND notified=0 AND due<=?', (esik,)).fetchall()
        for rid, metin, due in satirlar:
            c.execute('UPDATE reminders SET notified=1 WHERE id=?', (rid,))
            c.execute('INSERT INTO notifications(kind,title,text,created) VALUES (?,?,?,?)',
                      ('reminder', 'Hatırlatıcı', metin, datetime.now().isoformat(timespec='seconds')))
        masaustu = ayar_al(c, 'bildirim_aktif', '1') == '1'
    if satirlar and masaustu:
        try:
            bildirim.cal()
            bildirim.goster('Emre hatırlatıyor', ' · '.join(m for _, m, _ in satirlar))
        except Exception:
            pass
    return [{'id': r[0], 'text': r[1], 'due': r[2]} for r in satirlar]


def _bildirim_dongusu():
    while not BILDIRIM_DURDUR.wait(BILDIRIM_ARALIK):
        try:
            bildirim_tara()
        except Exception:
            pass  # arka plan işçisi hatası sunucuyu düşürmemeli


def arka_planlari_baslat():
    """Hatırlatıcı işçisini ve (açıksa) global kısayolu başlatır."""
    global _BILDIRIM_ISCI
    with db() as c:
        kisayol_acik = ayar_al(c, 'kisayol_aktif', '0') == '1'
        tus = ayar_al(c, 'kisayol_tus', kisayol.VARSAYILAN)
    if _BILDIRIM_ISCI is None or not _BILDIRIM_ISCI.is_alive():
        BILDIRIM_DURDUR.clear()
        _BILDIRIM_ISCI = threading.Thread(target=_bildirim_dongusu, daemon=True,
                                          name='emre-hatirlatici')
        _BILDIRIM_ISCI.start()
    if kisayol_acik:
        try:
            KISAYOL.metin = tus
            KISAYOL.baslat()
        except ValueError as hata:
            print('Global kısayol açılamadı:', hata, flush=True)
    return {'kisayol': KISAYOL.durum(), 'bildirim': True}


class DikteOturum:
    def __init__(self):
        self.metin = ''
        self.guncelleme = time.time()
        self.uyandi = 0.0  # uyandırma sözcüğünün duyulduğu an (son 12 sn geçerli)

    def ekle(self, yeni):
        """Yeni pencere metnini ekler; eklenen kısmı ve tam metni döndürür."""
        tam, eklenen = dikte.birlesik(self.metin, yeni, bitir=False)
        self.metin = tam[:DIKTE_AZAMI_KARAKTER]
        self.guncelleme = time.time()
        return eklenen, self.metin


def dikte_oturum(ad):
    with DIKTE_KILIT:
        simdi = time.time()
        # Eski oturumları temizle (30 dakika).
        for anahtar in [k for k, v in DIKTE.items() if simdi - v.guncelleme > 1800]:
            DIKTE.pop(anahtar, None)
        if len(DIKTE) >= DIKTE_AZAMI_OTURUM and ad not in DIKTE:
            en_eski = min(DIKTE, key=lambda k: DIKTE[k].guncelleme)
            DIKTE.pop(en_eski, None)
        return DIKTE.setdefault(ad, DikteOturum())


def store_message(session, role, text):
    """Sohbet mesajını sunucuda sakla (A4: kalıcı geçmiş, cihazdan bağımsız)."""
    if not session or not text:
        return
    with db() as conn:
        conn.execute('INSERT INTO messages(session,role,text,created) VALUES (?,?,?,?)',
                     (session[:80], role, str(text)[:6000], datetime.now().isoformat(timespec='seconds')))


def text_field(data, name, limit, required=False, default='', label=None):
    """Return a trimmed string field; never let a list/dict reach str operations.

    `label` kullanıcıya gösterilecek Türkçe alan adıdır; hata mesajı hiçbir zaman
    iç alan adını (name/person/text) sızdırmaz.
    """
    etiket = label or 'Alan'
    value = data.get(name, default)
    if value is None: value = default
    if not isinstance(value, str):
        raise ValueError(f'{etiket} metin olmalı.')
    value = value.strip()
    if len(value) > limit:
        raise ValueError(f'{etiket} en fazla {limit} karakter olabilir.')
    if required and not value:
        raise ValueError(f'{etiket} gerekli.')
    return value


def int_field(data, name, minimum, maximum, label=None):
    etiket = label or 'Alan'
    value = data.get(name)
    if type(value) is not int:
        raise ValueError(f'{etiket} tam sayı olmalı.')
    if not minimum <= value <= maximum:
        raise ValueError(f'{etiket} geçerli aralıkta olmalı.')
    return value


def friendly_error(exc):
    """Translate technical exceptions into short Turkish messages for the UI."""
    message = str(exc)
    if isinstance(exc, urllib.error.HTTPError):
        return f'Servis isteği başarısız (HTTP {exc.code}).'
    if isinstance(exc, urllib.error.URLError) or 'urlopen error' in message or 'Connection refused' in message:
        return 'Yerel servise ulaşılamadı. Ollama/OpenJarvis çalışıyor mu? Bağlantıyı ve internet erişimini kontrol et.'
    if isinstance(exc, (TimeoutError,)) or 'timed out' in message:
        return 'İşlem zaman aşımına uğradı; lütfen tekrar dene.'
    if isinstance(exc, sqlite3.OperationalError) and 'locked' in message:
        return 'Veritabanı şu anda meşgul; birkaç saniye sonra tekrar dene.'
    if isinstance(exc, sqlite3.IntegrityError):
        return 'Bu isimde bir kayıt zaten var.'
    if isinstance(exc, json.JSONDecodeError):
        return 'İstek gövdesi geçerli JSON değil.'
    if isinstance(exc, AttributeError) or "object has no attribute" in message:
        return 'İstek biçimi beklenenden farklı; alanları kontrol et.'
    return message or 'Beklenmeyen bir hata oluştu.'


def tr_key(text):
    """İsimleri Türkçe kurallarına göre karşılaştırmak için anahtar üret.

    SQLite'ın NOCASE collation'ı yalnızca ASCII'de çalışır; bu yüzden 'İlker' ve
    'ilker' farklı kayıtlar olarak eklenebiliyordu.
    """
    return str(text).strip().translate(str.maketrans({'I': 'ı', 'İ': 'i'})).casefold()


NET_CACHE = {'ok': False, 'at': 0.0}


def internet_available():
    """Cheap internet probe, cached for a minute so /api/status stays fast."""
    now = time.monotonic()
    if now - NET_CACHE['at'] < 60:
        return NET_CACHE['ok']
    ok = False
    try:
        with socket.create_connection(('1.1.1.1', 443), timeout=1.2):
            ok = True
    except OSError:
        ok = False
    NET_CACHE.update(ok=ok, at=now)
    return ok


def request_json(url, payload=None, timeout=20):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.load(res)

def ollama_akis(model, messages, timeout=300):
    """Ollama'nın NDJSON akışını metin parçalarına çevirir."""
    govde = json.dumps({'model': model, 'messages': messages, 'stream': True, 'think': False,
                        'options': {'num_ctx': 4096, 'num_predict': 400, 'num_gpu': 0}}).encode()
    istek = urllib.request.Request(OLLAMA + '/api/chat', data=govde,
                                   headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(istek, timeout=timeout) as yanit:
        for ham in yanit:
            satir = ham.decode('utf-8', 'replace').strip()
            if not satir:
                continue
            try:
                olay = json.loads(satir)
            except ValueError:
                continue
            parca = (olay.get('message') or {}).get('content')
            if isinstance(parca, str) and parca:
                yield parca
            if olay.get('done'):
                break


def sohbet_istegi(data):
    """Sohbet isteğini doğrular; (clean, last_user, session, backend, selected, api_model) döndürür."""
    messages = data.get('messages', [])
    if not isinstance(messages, list):
        raise ValueError('Mesaj listesi geçersiz.')
    messages = messages[-12:]
    clean = [{'role': m['role'], 'content': str(m['content'])[:6000]} for m in messages
             if isinstance(m, dict) and m.get('role') in ('user', 'assistant')
             and isinstance(m.get('content'), str)]
    if not clean:
        raise ValueError('Mesaj boş.')
    selected = str(data.get('model') or MODEL).strip()
    if len(selected) > 200:
        raise ValueError('Model adı çok uzun.')
    if not re.fullmatch(r'[\w.\-:/]{1,200}', selected):
        raise ValueError('Model adı geçersiz.')
    last_user = next((m['content'] for m in reversed(clean) if m['role'] == 'user'), '')
    session = str(data.get('session') or '').strip()[:80]
    if session and not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', session):
        session = ''
    backend = str(data.get('backend') or 'ollama').strip().lower()
    if backend in ('api', 'openai', 'omnirouter', 'openrouter', 'saglayici'):
        backend = 'api'
    api_model = str(data.get('model') or '').strip() or None if backend == 'api' else None
    return clean, last_user, session, backend, selected, api_model


def gun_ozeti(simdi=None):
    """Ana sayfadaki “Bugün” kartı için tek istekte özet üretir.

    Dönen alanlar: hatırlatıcılar (geciken/bugün/yaklaşan), defter bakiyesi,
    son bellek kayıtları, belge sayısı ve varsa bugünün takvim etkinlikleri.
    Hiçbir dış istek yapılmaz; yalnızca yerel veritabanı ve yerel dosyalar okunur.
    """
    simdi = simdi or datetime.now()
    bugun = simdi.strftime('%Y-%m-%d')
    with db() as c:
        satirlar = c.execute('SELECT id,text,due FROM reminders WHERE done=0 ORDER BY due LIMIT 200').fetchall()
        defter_satir = c.execute('SELECT kind,amount FROM ledger').fetchall()
        bellek_satir = c.execute('SELECT text,created FROM memories ORDER BY id DESC LIMIT 3').fetchall()
        belge_sayisi = c.execute('SELECT COUNT(*) FROM docs').fetchone()[0]
        takvim_yolu = ayar_al(c, 'takvim_yolu', '')
    geciken, bugun_kayit, yaklasan = [], [], []
    bitis = (simdi + timedelta(days=7)).strftime('%Y-%m-%dT%H:%M')
    for rid, metin, due in satirlar:
        kayit = {'id': rid, 'text': metin, 'due': due}
        if due < simdi.strftime('%Y-%m-%dT%H:%M'):
            geciken.append(kayit)
        elif due[:10] == bugun:
            bugun_kayit.append(kayit)
        elif due <= bitis:
            yaklasan.append(kayit)
    bakiye = {'alacak': 0, 'verecek': 0}
    for kind, amount in defter_satir:
        if kind == 'receivable':
            bakiye['alacak'] += amount
        elif kind == 'received':
            bakiye['alacak'] -= amount
        elif kind == 'payable':
            bakiye['verecek'] += amount
        elif kind == 'paid':
            bakiye['verecek'] -= amount
    etkinlikler, takvim_hatasi = [], ''
    if takvim_yolu:
        try:
            etkinlikler = takvim.yaklasan(takvim.yolu_oku(takvim_yolu), gun=1, simdi=simdi)[:5]
        except ValueError as hata:
            takvim_hatasi = str(hata)
    return {
        'tarih': simdi.strftime('%Y-%m-%d %H:%M'),
        'hatirlaticilar': {'geciken': geciken[:5], 'bugun': bugun_kayit[:5], 'yaklasan': yaklasan[:5],
                           'toplam': len(satirlar)},
        'defter': {'alacak_tl': bakiye['alacak'] / 100, 'verecek_tl': bakiye['verecek'] / 100,
                   'kayit': len(defter_satir)},
        'bellek': [{'text': metin, 'created': tarih} for metin, tarih in bellek_satir],
        'belgeler': belge_sayisi,
        'takvim': {'path': takvim_yolu, 'etkinlikler': etkinlikler, 'error': takvim_hatasi},
    }


def belge_baglami(metin, doc_id=None, limit=4):
    """Belgeye soru sorulduysa ilgili parçaları kaynak numaralı metne çevirir."""
    metin = str(metin or '')
    soru = metin.split(':', 1)[1] if ':' in metin and metin.lower().startswith(('belgeye sor', 'belge:')) else metin
    if doc_id in (None, '', 0, '0', 'all'):
        doc_id = None
    else:
        try:
            doc_id = int(doc_id)
        except (TypeError, ValueError):
            doc_id = None
    with db() as c:
        parcalar = belge.ara(c, soru, doc_id=doc_id, limit=limit)
    if not parcalar:
        return '', []
    return belge.baglam(parcalar), parcalar


def takvim_yaniti(metin, gun=7):
    """Takvim sorusuysa kural tabanlı yanıt üretir; değilse (None, None)."""
    if not takvim.gerekiyor_mu(metin):
        return None, None
    with db() as c:
        yol = ayar_al(c, 'takvim_yolu', '')
    if not yol:
        return ('Takvim dosyası tanımlı değil. Ayarlar › Takvim ve posta bölümünden bir .ics dosyası '
                'veya klasör seç.'), None
    try:
        hepsi = takvim.yolu_oku(yol)
    except ValueError as hata:
        return f'Takvim okunamadı: {hata}', None
    if 'yarın' in metin.lower():
        gun = 2
    elif 'hafta' in metin.lower():
        gun = 7
    elif 'bugün' in metin.lower():
        gun = 1
    _denetle('takvim', 'takvim okundu', f'{len(hepsi)} etkinlik')
    return takvim.metin_ozet(hepsi, gun=gun), hepsi


def posta_yaniti(metin, adet=5):
    """Posta sorusuysa son iletileri özetler; değilse (None, None)."""
    if not posta.gerekiyor_mu(metin):
        return None, None
    with db() as c:
        yol = ayar_al(c, 'posta_yolu', '')
    if not yol:
        return ('Posta kaynağı tanımlı değil. Ayarlar › Takvim ve posta bölümünden bir .eml/.mbox '
                'dosyası veya klasör seç. (Emre e-posta hesabına bağlanmaz; yalnızca yerel dosyaları okur.)'), None
    try:
        mesajlar = posta.yolu_oku(yol)
    except ValueError as hata:
        return f'Posta okunamadı: {hata}', None
    _denetle('posta', 'posta okundu', f'{len(mesajlar)} ileti')
    return posta.metin_ozet(mesajlar, adet=adet), None


def beceri_cagrisi(metin):
    """`!beceri-adı ...` yazılmışsa beceriyi çalıştırır; (yanıt, beceri) döndürür."""
    ad, kalan = beceriler.acik_komut(metin)
    if not ad:
        return None, None
    try:
        sonuc = beceriler.calistir(ad, kalan)
    except ValueError as hata:
        _denetle('beceri', f'{ad} çalıştırılamadı', str(hata), 'hata')
        return f'“{ad}” çalıştırılamadı: {hata}', ad
    _denetle('beceri', f'{ad} sohbetten çalıştırıldı', f'{len(sonuc["reply"])} karakter')
    return sonuc['reply'], ad


_UNUT = re.compile(r'^(?:bunu\s+)?unut\s*[:,]?\s*(?P<konu>.{2,200})$', re.I)


def unutma_cagrisi(metin):
    """“unut: X” / “bunu unut: X” yazılmışsa kaydı siler; (yanıt, silinen) döndürür."""
    eslesme = _UNUT.match(' '.join(str(metin or '').split()))
    if not eslesme:
        return None, 0
    try:
        sonuc = None
        with db() as c:
            sonuc = bellek.unut(c, eslesme.group('konu'))
    except ValueError as hata:
        return f'Unutulamadı: {hata}', 0
    if not sonuc['silinen']:
        return f'“{eslesme.group("konu")}” ile eşleşen bir bellek kaydı bulunamadı.', 0
    _denetle('bellek', 'bellek kaydı unutuldu', f'{sonuc["silinen"]} kayıt')
    ilk = sonuc['kayitlar'][0]['text'][:80]
    return f'{sonuc["silinen"]} kayıt silindi: {ilk}', sonuc['silinen']


def web_baglami(last_user, istenen=None):
    """Gerekiyorsa web araması yapar: (sistem_metni, kaynaklar)."""
    with db() as c:
        acik = ayar_al(c, 'web_arama', '1') == '1'
    karar = istenen if istenen is not None else arama.gerekiyor_mu(last_user)
    if not (acik and karar):
        return '', []
    try:
        sonuclar = arama.ara(last_user)
    except Exception:
        sonuclar = []
    if not sonuclar:
        return '', []
    return arama.baglam(sonuclar), [{'baslik': x['baslik'], 'url': x['url']} for x in sonuclar]


def telegram(method, payload=None):
    if not TOKEN: raise ValueError('Telegram bot anahtarı ayarlanmamış.')
    return request_json('https://api.telegram.org/bot'+TOKEN+'/'+method, payload, timeout=15)

def clean_reply(text):
    """Suppress explicit thought blocks and prevent obvious leaked reasoning from reaching the UI."""
    text = re.sub(r'<think>.*?</think>', '', text or '', flags=re.I | re.S).strip()
    if re.search(r'<think>', text, flags=re.I):
        text = re.split(r'<think>', text, flags=re.I)[0].strip()
    # Some model/version combinations output untagged reasoning despite think=False.
    patterns = (r"let me (?:think|check)", r"the user (?:said|wants|wrote)", r"i (?:need|should) to respond", r"the instructions (?:say|are)")
    if any(re.search(p, text, re.I) for p in patterns):
        return 'Bir yanıt oluştururken sorun yaşadım. Lütfen tekrar dener misin?'
    # Remove repetitive unsolicited assistance prompts without altering other content.
    text = re.sub(r'(?i)(?:size|sana)?\s*(?:nasıl|ne şekilde) yardımcı olabilirim\s*[?!.]*', '', text)
    text = re.sub(r'(?i)(?:size|sana)?\s*hangi konuda yardıma ihtiyacınız var\s*[?!.]*', '', text)
    text = re.sub(r'(?i)başka bir (?:şey|konu)(?: var mı|de yardımcı olabilir miyim)\s*[?!.]*', '', text)
    return text.strip() or 'Anladım.'

def windows_tts(request):
    if os.name != 'nt': raise ValueError('Yerel Windows sesi yalnızca Windows üzerinde kullanılabilir.')
    exe=Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32'/'WindowsPowerShell'/'v1.0'/'powershell.exe'
    try:
        result=subprocess.run([str(exe),'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(ROOT/'tts_windows.ps1')],input=json.dumps(request,ensure_ascii=False),capture_output=True,text=True,encoding='utf-8',timeout=90,check=False)
        parsed=json.loads(result.stdout.strip().lstrip('\ufeff'))
        if not parsed.get('ok'): raise ValueError(parsed.get('error','Yerel ses başlatılamadı.'))
        return parsed
    except (OSError,subprocess.TimeoutExpired,json.JSONDecodeError): raise ValueError('Yerel ses servisi başlatılamadı.')

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass
    def sse_basla(self):
        """Sunucudan tarayıcıya olay akışı (SSE) başlatır."""
        self.send_response(200)
        self.send_header('Content-Type','text/event-stream; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Connection','close')
        self.end_headers()
        self.close_connection=True

    def sse(self, olay):
        self.wfile.write(('data: '+json.dumps(olay, ensure_ascii=False)+'\n\n').encode('utf-8'))
        self.wfile.flush()

    def chat_akis(self, data):
        """Sohbet yanıtını parça parça gönderir (SSE). Kurallı yanıtlar tek parça gelir."""
        clean, last_user, session, backend, selected, api_model = sohbet_istegi(data)
        if session: store_message(session,'user',last_user)
        with db() as c:
            bellek.kaydet_cikarimlar(c,last_user,source='sohbet')
            kisisel=bellek.baglam(c,last_user,limit=5)
        web_metin, kaynaklar = web_baglami(last_user, data.get('web'))
        belge_metin, belge_kaynaklar = belge_baglami(last_user, data.get('doc_id'))
        if belge_metin:
            kaynaklar = list(kaynaklar or []) + [{'title': x['name'] + ' · sayfa ' + str(x['sayfa']),
                                                 'url': ''} for x in belge_kaynaklar]

        def tek_parca(metin):
            self.sse_basla()
            self.sse({'type':'delta','text':metin})
            if session: store_message(session,'assistant',metin)
            self.sse({'type':'done','reply':metin,'sources':kaynaklar})

        # Açık beceri çağrısı (!beceri ...) ve kural tabanlı işlemler modelden önce çözülür.
        unut_yanit, _ = unutma_cagrisi(last_user)
        if unut_yanit is not None:
            return tek_parca(unut_yanit)
        for kural in (takvim_yaniti, posta_yaniti):
            yanit, _veri = kural(last_user)
            if yanit is not None:
                return tek_parca(yanit)
        beceri_yanit, _ = beceri_cagrisi(last_user)
        if beceri_yanit is not None:
            return tek_parca(beceri_yanit)
        for cozum in (ledger_tools.create_account_from_text(last_user,db),
                      hatirlatici.direct_reminder_action(last_user,db),
                      ledger_tools.direct_ledger_action(last_user,db)):
            if cozum is not None:
                return tek_parca(cozum)

        if backend=='api':
            if not SAG.yukle()['base_url']:
                raise ValueError('Ücretsiz API sağlayıcısı ayarlanmamış. Ayarlar > Ücretsiz API bölümünden bağlan.')
        elif backend=='ollama':
            installed={m.get('name') for m in request_json(OLLAMA+'/api/tags',timeout=5).get('models',[])}
            if selected not in installed and selected+':latest' not in installed:
                raise ValueError('Seçilen model Ollama üzerinde kurulu değil.')
            if selected.lower().startswith('qwen3'):
                clean[-1]['content'] += '\n/no_think'
        elif backend=='openjarvis':
            raise ValueError('OpenJarvis akışlı yanıtı desteklemiyor; normal sohbeti kullan.')
        else:
            raise ValueError('Bilinmeyen yapay zekâ bağlantısı.')

        beceri_metin=beceriler.baglam()
        system=SYSTEM+(' '+kisisel if kisisel else '')+(' '+beceri_metin if beceri_metin else '')+(' '+web_metin if web_metin else '')+(' '+belge_metin if belge_metin else '')+' Yerel tarih ve saat: '+datetime.now().strftime('%Y-%m-%d %H:%M')+'. Kısa ve doğrudan yanıt ver.'
        mesajlar=[{'role':'system','content':system}]+clean
        self.sse_basla()
        self.sse({'type':'start','sources':kaynaklar})
        parcalar=[]
        try:
            if backend=='api':
                try:
                    for parca in SAG.sohbet_akis(mesajlar, model=api_model, max_tokens=500, timeout=120):
                        parcalar.append(parca); self.sse({'type':'delta','text':parca})
                except ValueError as hata:
                    kota_artir(basarili=False)
                    if saglayici.gecici_hata(hata):
                        _denetle('saglayici','kota/hız sınırı (akış)',str(hata)[:120],'hata')
                    raise
                kota_artir(basarili=True)
            else:
                for parca in ollama_akis(selected, mesajlar):
                    parcalar.append(parca); self.sse({'type':'delta','text':parca})
        except (BrokenPipeError, ConnectionResetError):
            return  # sekme kapatıldı; yazmayı sürdürmenin anlamı yok
        reply=clean_reply(''.join(parcalar))
        if not reply:
            reply='Model boş yanıt verdi. Lütfen tekrar dene.'
        if session: store_message(session,'assistant',reply)
        try:
            self.sse({'type':'done','reply':reply,'sources':kaynaklar})
        except (BrokenPipeError, ConnectionResetError):
            pass

    def out(self, obj, status=200):
        data=json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(data)))
        self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Referrer-Policy','no-referrer'); self.send_header('X-Frame-Options','DENY'); self.end_headers(); self.wfile.write(data)
    def raw(self, payload, ctype, filename=None, status=200):
        self.send_response(status)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Frame-Options', 'DENY')
        if filename:
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(payload)
    # --- dışa aktarma yardımcıları (A5) ---------------------------------
    def export_ledger(self, query):
        import csv
        import io
        params = dict(pair.split('=', 1) for pair in query.split('&') if '=' in pair)
        bicim = (params.get('format') or 'csv').lower()
        if bicim not in ('csv', 'json'):
            raise ValueError('Desteklenen biçimler: csv, json.')
        with db() as c:
            rows = c.execute('SELECT id,person,kind,amount,note,due,created,source FROM ledger ORDER BY id').fetchall()
        turkce = {'receivable': 'Alacak', 'payable': 'Verecek', 'received': 'Tahsilat', 'paid': 'Ödeme'}
        kayitlar = [{'id': r[0], 'kisi': r[1], 'tur': turkce.get(r[2], r[2]), 'tutar_tl': r[3] / 100,
                      'not': r[4], 'vade': r[5], 'olusturma': r[6], 'kaynak': r[7] or 'manual'} for r in rows]
        stamp = datetime.now().strftime('%Y%m%d-%H%M')
        if bicim == 'json':
            data = json.dumps({'defter': kayitlar}, ensure_ascii=False, indent=2).encode('utf-8')
            return self.raw(data, 'application/json; charset=utf-8', f'emre-defter-{stamp}.json')
        out = io.StringIO()
        writer = csv.writer(out, delimiter=';', lineterminator='\r\n')
        writer.writerow(['Kayıt No', 'Kişi', 'İşlem', 'Tutar (TL)', 'Açıklama', 'Vade', 'Oluşturma', 'Kaynak'])
        for k in kayitlar:
            tutar = f"{k['tutar_tl']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            writer.writerow([k['id'], k['kisi'], k['tur'], tutar,
                             k['not'], k['vade'] or '', k['olusturma'], k['kaynak']])
        # BOM: Excel'in UTF-8'i Türkçe karakterlerle doğru açması için.
        return self.raw(b'\xef\xbb\xbf' + out.getvalue().encode('utf-8'),
                        'text/csv; charset=utf-8', f'emre-defter-{stamp}.csv')

    def export_backup(self):
        with db() as c:
            veri = {
                'surum': VERSION,
                'olusturma': datetime.now().isoformat(timespec='seconds'),
                'accounts': [dict(zip(('id', 'name', 'note'), r)) for r in
                             c.execute('SELECT id,name,note FROM accounts ORDER BY id')],
                'ledger': [dict(zip(('id', 'person', 'kind', 'amount', 'note', 'due', 'created', 'source', 'raw_text'), r))
                           for r in c.execute('SELECT id,person,kind,amount,note,due,created,source,raw_text FROM ledger ORDER BY id')],
                'reminders': [dict(zip(('id', 'text', 'due', 'done'), r)) for r in
                              c.execute('SELECT id,text,due,done FROM reminders ORDER BY id')],
                'messages': [dict(zip(('id', 'session', 'role', 'text', 'created'), r)) for r in
                             c.execute('SELECT id,session,role,text,created FROM messages ORDER BY id')],
            }
        stamp = datetime.now().strftime('%Y%m%d-%H%M')
        return self.raw(json.dumps(veri, ensure_ascii=False, indent=2).encode('utf-8'),
                        'application/json; charset=utf-8', f'emre-yedek-{stamp}.json')

    def valid_host(self):
        """Yalnızca loopback adlarına yanıt ver.

        Host başlığı doğrulanmazsa DNS rebinding ile saldırganın alan adı
        127.0.0.1'e çözülebilir ve tarayıcı aynı kaynak sayıp token'ı okuyabilir.
        """
        host=self.headers.get('Host','')
        if not host: return False
        name=host.rsplit(':',1)[0].strip('[]').lower() if not host.startswith('[') else host[1:host.find(']')].lower()
        return name in ('127.0.0.1','localhost','::1','0.0.0.0')
    def valid(self):
        origin=self.headers.get('Origin','')
        return self.valid_host() and self.headers.get('X-Emre-Token') == KEY and (not origin or origin in ('http://127.0.0.1:8765','http://localhost:8765'))
    def body(self):
        limit=8_500_000 if urlparse(self.path).path=='/api/speech/transcribe' else 100000
        if 'chunked' in self.headers.get('Transfer-Encoding','').lower():
            raw=self.read_chunked(limit)
        else:
            n=int(self.headers.get('Content-Length','0') or 0)
            if n>limit: raise ValueError('İstek çok büyük.')
            raw=self.rfile.read(n) if n>0 else b''
        if not raw: return {}
        parsed=json.loads(raw)
        if not isinstance(parsed,dict): raise ValueError('İstek gövdesi bir JSON nesnesi olmalı.')
        return parsed
    def read_chunked(self, limit):
        """Chunked gövdeyi sınırla oku; aksi halde gövde sessizce boş kalıyordu."""
        chunks=[]; total=0
        while True:
            line=self.rfile.readline(1024).strip()
            if not line: break
            try: size=int(line.split(b';')[0],16)
            except ValueError: raise ValueError('Chunked istek gövdesi geçersiz.')
            if size==0:
                while True:
                    trailer=self.rfile.readline(1024)
                    if trailer in (b'\r\n', b'\n', b''): break
                break
            total+=size
            if total>limit: raise ValueError('İstek çok büyük.')
            chunks.append(self.rfile.read(size))
            self.rfile.read(2)
        return b''.join(chunks)
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/':
            html=(ROOT/'index.html').read_text(encoding='utf-8').replace('</head>', '<meta name="emre-token" content="'+KEY+'"></head>', 1).encode()
            self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(html))); self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Referrer-Policy','no-referrer'); self.send_header('X-Frame-Options','DENY')
            # Yalnızca kendi kaynağımıza bağlanılabilir; dış script/çerçeve engellenir.
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers(); self.wfile.write(html); return
        if path=='/favicon.ico':
            icon=ROOT/'emre.ico'
            if not icon.is_file(): return self.out({'error':'Bulunamadı'},404)
            data=icon.read_bytes(); self.send_response(200); self.send_header('Content-Type','image/x-icon'); self.send_header('Content-Length',str(len(data))); self.send_header('Cache-Control','max-age=86400'); self.end_headers(); self.wfile.write(data); return
        if not self.valid(): return self.out({'error':'Yetkisiz istek.'},403)
        try:
            if path=='/api/developer/files':
                folder=ROOT/'kodlar'
                folder.mkdir(exist_ok=True)
                files=[p.name for p in folder.iterdir() if p.is_file() and not p.is_symlink() and len(p.name)<=100]
                return self.out({'files':sorted(files)})
            if path=='/api/tts/voices':
                voices=[]
                for voice in ('fahrettin','fettah','dfki'):
                    if tts_piper_bridge.installed(voice): voices.append({'name':'piper-tr-'+voice,'culture':'tr-TR','gender':'Belirtilmemiş','label':'Piper Türkçe · '+voice+' (yerel)'})
                try: voices.extend(windows_tts({'action':'voices'}).get('voices',[]))
                except ValueError: pass
                return self.out({'voices':voices,'piper_installed':any(tts_piper_bridge.installed(v) for v in ('dfki','fahrettin','fettah'))})
            if path=='/api/speech/status': return self.out(ses_baglanti.durum())
            if path=='/api/provider/status':
                return self.out(SAG.durum())
            if path=='/api/memory':
                query=dict(pair.split('=',1) for pair in urlparse(self.path).query.split('&') if '=' in pair)
                sorgu=unquote_plus(query.get('q',''))[:200].strip()
                try: limit=min(max(int(query.get('limit',50)),1),200)
                except ValueError: raise ValueError('Limit sayı olmalı.')
                with db() as c:
                    kayitlar=bellek.ara(c,sorgu,limit=limit) if sorgu else bellek.hepsi(c,limit=limit)
                return self.out({'items':kayitlar,'total':len(kayitlar)})
            if path=='/api/memory/export':
                with db() as c: yedek=bellek.disa_aktar(c)
                return self.out(yedek)
            if path=='/api/provider/usage':
                query=dict(pair.split('=',1) for pair in urlparse(self.path).query.split('&') if '=' in pair)
                try: gun=max(int(query.get('days',7)),1)
                except ValueError: gun=7
                return self.out(kota_ozet(gun))
            if path=='/api/wake/status':
                return self.out({**uyandirma.ayar_oku(),'ses_modeli':uyandirma.ses_ile_var()})
            if path=='/api/today':
                return self.out(gun_ozeti())
            if path=='/api/docs':
                with db() as c: belgeler=belge.listele(c)
                return self.out({'docs':belgeler})
            if path=='/api/calendar':
                query=dict(pair.split('=',1) for pair in urlparse(self.path).query.split('&') if '=' in pair)
                try: gun=max(int(query.get('days',7)),1)
                except ValueError: gun=7
                with db() as c: yol=ayar_al(c,'takvim_yolu','')
                if not yol: return self.out({'path':'','events':[],'message':'Takvim yolu tanımlı değil.'})
                try: hepsi=takvim.yolu_oku(yol)
                except ValueError as hata: return self.out({'path':yol,'events':[],'error':str(hata)})
                return self.out({'path':yol,'events':takvim.yaklasan(hepsi,gun=gun),'total':len(hepsi)})
            if path=='/api/mail':
                query=dict(pair.split('=',1) for pair in urlparse(self.path).query.split('&') if '=' in pair)
                try: adet=max(int(query.get('limit',10)),1)
                except ValueError: adet=10
                with db() as c: yol=ayar_al(c,'posta_yolu','')
                if not yol: return self.out({'path':'','messages':[],'message':'Posta yolu tanımlı değil.'})
                try: mesajlar=posta.yolu_oku(yol)
                except ValueError as hata: return self.out({'path':yol,'messages':[],'error':str(hata)})
                return self.out({'path':yol,'messages':posta.sirala(mesajlar)[:min(adet,50)],'total':len(mesajlar)})
            if path=='/api/skills':
                with db() as c: web_acik=ayar_al(c,'web_arama','1')=='1'
                return self.out({'skills':beceriler.listele(),'folder':str(beceriler.KOK),
                                 'web':web_acik})
            if path=='/api/audit':
                query=dict(pair.split('=',1) for pair in urlparse(self.path).query.split('&') if '=' in pair)
                try: limit=min(max(int(query.get('limit',50)),1),300)
                except ValueError: limit=50
                tur=query.get('kind')
                with db() as c: kayitlar=denetim.son(c,limit=limit,kind=tur)
                return self.out({'items':kayitlar})
            if path=='/api/diagnose':
                sonuc=tanilama.calistir(db_yolu=DB,kok=ROOT,port=self.server.server_address[1])
                return self.out(sonuc)
            if path=='/api/system/status':
                with db() as c:
                    bildirim_acik=ayar_al(c,'bildirim_aktif','1')=='1'
                    kisayol_acik=ayar_al(c,'kisayol_aktif','0')=='1'
                    tarayici=ayar_al(c,'kisayol_tarayici','1')=='1'
                    tus=ayar_al(c,'kisayol_tus',kisayol.VARSAYILAN)
                    web_acik=ayar_al(c,'web_arama','1')=='1'
                    tts_akis=ayar_al(c,'tts_akis','1')=='1'
                    barge_in=ayar_al(c,'barge_in','1')=='1'
                    takvim_yolu=ayar_al(c,'takvim_yolu','')
                    posta_yolu=ayar_al(c,'posta_yolu','')
                    bekleyen=c.execute('SELECT COUNT(*) FROM notifications WHERE seen=0').fetchone()[0]
                durum=dict(KISAYOL.durum())
                durum['acik']=kisayol_acik
                if not durum['aktif']:
                    durum['kisayol']=tus
                    durum['gorunen']=kisayol.bicim(tus)
                return self.out({'autostart':otomatik_baslat.durum(ROOT),
                                 'hotkey':durum,'hotkey_tarayici':tarayici,
                                 'notifications':{'aktif':bildirim_acik,'bekleyen':bekleyen},
                                 'web':{'aktif':web_acik},
                                 'tts':{'akis':tts_akis,'barge_in':barge_in},
                                 'calendar':{'path':takvim_yolu},
                                 'mail':{'path':posta_yolu},
                                 'version':VERSION})
            if path=='/api/hotkey/poll':
                query=dict(pair.split('=',1) for pair in urlparse(self.path).query.split('&') if '=' in pair)
                try: since=max(int(query.get('since',0)),0)
                except ValueError: since=0
                with KISAYOL_KILIT:
                    KISAYOL_DURUM['son_yoklama']=time.time()
                    seq=KISAYOL_DURUM['seq']
                return self.out({'seq':seq,'basildi':seq>since,'aktif':KISAYOL.durum()['aktif']})
            if path=='/api/notifications':
                query=dict(pair.split('=',1) for pair in urlparse(self.path).query.split('&') if '=' in pair)
                try: since=max(int(query.get('since',0)),0)
                except ValueError: since=0
                with db() as c:
                    rows=c.execute('SELECT id,kind,title,text,created FROM notifications '
                                   'WHERE seen=0 AND id>? ORDER BY id DESC LIMIT 20',(since,)).fetchall()
                    son=c.execute('SELECT COALESCE(MAX(id),0) FROM notifications').fetchone()[0]
                return self.out({'items':[{'id':r[0],'kind':r[1],'title':r[2],'text':r[3],'created':r[4]}
                                          for r in rows],'last':son})
            if path=='/api/web/search':
                query=dict(pair.split('=',1) for pair in urlparse(self.path).query.split('&') if '=' in pair)
                sorgu=unquote_plus(query.get('q',''))[:200].strip()
                if not sorgu: raise ValueError('Arama metni gerekli.')
                return self.out({'query':sorgu,'results':arama.ara(sorgu)})
            if path=='/api/mcp/status':
                ayar=MCP.yenile()
                return self.out({'servers':MCP.durum(),'configured':len(ayar['sunucular'])})
            if path=='/api/mcp/tools':
                MCP.yenile()
                return self.out({'tools':MCP.araclar()})
            if path=='/api/openjarvis/status':
                try:
                    health=request_json(OPENJARVIS+'/health',timeout=3)
                    return self.out({'online':True,'health':health})
                except Exception: return self.out({'online':False})
            if path=='/api/arena/status': return self.out(arena_bridge.snapshot())
            if path=='/api/status':
                try: models=request_json(OLLAMA+'/api/tags',timeout=2); ollama=True
                except Exception: models={'models':[]}; ollama=False
                try: openjarvis_online=bool(request_json(OPENJARVIS+'/health',timeout=2))
                except Exception: openjarvis_online=False
                return self.out({'ollama':ollama,'model':MODEL,'models':[m['name'] for m in models.get('models',[])],
                                 'telegram_configured':bool(TOKEN),'version':VERSION,
                                 'speech_installed':(ROOT/'.venv-ses'/'Scripts'/'python.exe').is_file(),'speech_model':ses_baglanti.model(),
                                 'piper_installed':any(tts_piper_bridge.installed(v) for v in ('dfki','fahrettin','fettah')),
                                 'openjarvis_online':openjarvis_online,'arena_status':arena_bridge.snapshot().get('status','stopped'),
                                 'apps_supported':os.name=='nt','internet_access':internet_available(),
                                 'telegram':BOT.status(),'telegram_unread':BOT.messages(1).get('unread',0) if BOT.configured() else 0,
                                 'arena_message':arena_bridge.snapshot().get('message',''),
                                 'provider':SAG.durum()})
            if path=='/api/accounts':
                with db() as c: rows=c.execute('SELECT name,note FROM accounts ORDER BY name').fetchall()
                return self.out({'accounts':[{'name':r[0],'note':r[1]} for r in rows]})
            if path=='/api/ledger':
                query=dict(pair.split('=',1) for pair in urlparse(self.path).query.split('&') if '=' in pair)
                try:
                    limit=min(max(int(query.get('limit',500)),1),2000)
                    offset=max(int(query.get('offset',0)),0)
                except ValueError: raise ValueError('Sayfalama parametreleri geçersiz.')
                with db() as c:
                    total=c.execute('SELECT COUNT(*) FROM ledger').fetchone()[0]
                    rows=c.execute('SELECT id,person,kind,amount,note,due,created,source FROM ledger ORDER BY id DESC LIMIT ? OFFSET ?',(limit,offset)).fetchall()
                return self.out({'entries':[{'id':r[0],'person':r[1],'kind':r[2],'amount':r[3],'note':r[4],'due':r[5],'created':r[6],'source':r[7] or 'manual'} for r in rows],
                                 'total':total,'limit':limit,'offset':offset})
            if path=='/api/ledger/export':
                return self.export_ledger(urlparse(self.path).query)
            if path=='/api/backup':
                return self.export_backup()
            if path=='/api/reminders':
                with db() as c: rows=c.execute('SELECT id,text,due,done FROM reminders ORDER BY due').fetchall()
                return self.out({'reminders':[{'id':r[0],'text':r[1],'due':r[2],'done':bool(r[3])} for r in rows]})
            if path=='/api/history':
                query=dict(pair.split('=',1) for pair in urlparse(self.path).query.split('&') if '=' in pair)
                session=query.get('session','')
                with db() as c:
                    if session:
                        rows=c.execute('SELECT role,text,created FROM messages WHERE session=? ORDER BY id',(session,)).fetchall()
                        if not rows: raise ValueError('Bu oturumda kayıt bulunamadı.')
                        return self.out({'session':session,'messages':[{'role':r[0],'text':r[1],'created':r[2]} for r in rows]})
                    rows=c.execute('SELECT session,COUNT(*),MIN(created),MAX(created) FROM messages GROUP BY session ORDER BY MAX(created) DESC LIMIT 50').fetchall()
                    sessions=[]
                    for sid,count,first,last in rows:
                        preview=c.execute("SELECT text FROM messages WHERE session=? AND role='user' ORDER BY id LIMIT 1",(sid,)).fetchone()
                        sessions.append({'session':sid,'count':count,'first':first,'last':last,
                                         'preview':(preview[0][:80] if preview else '')})
                return self.out({'sessions':sessions})
            if path=='/api/telegram/updates':
                if not BOT.configured(): raise ValueError('Telegram bot anahtarı ayarlanmamış.')
                data=BOT.messages(50)
                data['status']=BOT.status()
                return self.out(data)
            return self.out({'error':'Bulunamadı'},404)
        except ValueError as e: return self.out({'error':str(e)},400)
        except Exception as e: return self.out({'error':friendly_error(e)},400)
    def do_OPTIONS(self):
        self.out({'error':'Bu yöntem desteklenmiyor.'},405)
    def do_POST(self):
        global TOKEN
        if not self.valid(): return self.out({'error':'Yetkisiz istek.'},403)
        try:
            data=self.body(); path=urlparse(self.path).path
            if path in ('/api/developer/read','/api/developer/save'):
                name=str(data.get('name','')).strip()
                if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,95}\.(?:py|js|html|css|json|txt|md)',name,re.I) or '..' in name: raise ValueError('Geçerli bir dosya adı ve desteklenen uzantı kullan.')
                folder=ROOT/'kodlar'; folder.mkdir(exist_ok=True); target=folder/name
                if target.is_symlink(): raise ValueError('Sembolik bağlantıya erişilemez.')
                if path.endswith('/read'):
                    if not target.is_file(): raise ValueError('Dosya bulunamadı.')
                    if target.stat().st_size>200000: raise ValueError('Dosya çok büyük.')
                    return self.out({'content':target.read_text(encoding='utf-8')})
                if data.get('confirmed') is not True: raise ValueError('Kaydetme onayı gerekli.')
                content=data.get('content')
                if not isinstance(content,str) or len(content.encode('utf-8'))>90000: raise ValueError('Dosya içeriği çok büyük veya geçersiz.')
                target.write_text(content,encoding='utf-8')
                return self.out({'ok':True})
            if path=='/api/tts/speak':
                text=text_field(data,'text',1500,required=True,label='Okunacak metin'); voice=text_field(data,'voice',200,required=True,label='Ses adı')
                name=None
                try:
                    with tempfile.NamedTemporaryFile(suffix='.wav',delete=False) as f: name=f.name
                    if voice in ('piper-tr-dfki','piper-tr-fahrettin','piper-tr-fettah'): tts_piper_bridge.speak(text,name,voice.removeprefix('piper-tr-'))
                    else: windows_tts({'action':'speak','voice':voice,'text':text,'path':name})
                    audio=Path(name).read_bytes()
                    if len(audio)>10_000_000: raise ValueError('Oluşan ses çok büyük.')
                    return self.out({'audio':base64.b64encode(audio).decode('ascii')})
                finally:
                    if name:
                        try:os.unlink(name)
                        except OSError:pass
            if path=='/api/speech/transcribe':
                if not isinstance(data.get('audio'),str): raise ValueError('Ses verisi gerekli.')
                ipucu=data.get('ipucu') or ''
                if not isinstance(ipucu,str): raise ValueError('İpucu metin olmalı.')
                text=ses_baglanti.transcribe(data.get('audio'), ipucu=ipucu[:300])
                return self.out({'text':text,'model':ses_baglanti.model()})
            if path=='/api/memory':
                sorgu=str(data.get('q') or '').strip()[:200]
                with db() as c:
                    kayitlar=bellek.ara(c,sorgu,limit=int(data.get('limit') or 50)) if sorgu else bellek.hepsi(c,limit=50)
                return self.out({'items':kayitlar,'total':len(kayitlar)})
            if path=='/api/memory/add':
                metin=data.get('text'); konu=data.get('subject'); tur=data.get('kind')
                if not isinstance(metin,str): raise ValueError('Bellek metni gerekli.')
                if konu is not None and not isinstance(konu,str): raise ValueError('Konu metin olmalı.')
                if tur is not None and not isinstance(tur,str): raise ValueError('Tür metin olmalı.')
                with db() as c:
                    kid=bellek.ekle(c,metin,kind=tur or 'not',subject=konu or '',source='arayuz')
                _denetle('bellek','bellek kaydı eklendi',metin)
                return self.out({'ok':True,'id':kid})
            if path=='/api/memory/delete':
                if data.get('confirmed') is not True: raise ValueError('Silme onayı gerekli.')
                with db() as c:
                    sayi=bellek.sil(c,int(data.get('id') or 0))
                if not sayi: raise ValueError('Kayıt bulunamadı.')
                _denetle('bellek','bellek kaydı silindi',f'id={data.get("id")}')
                return self.out({'ok':True,'deleted':sayi})
            if path=='/api/wake/status':
                ayar=uyandirma.ayar_oku()
                return self.out({**ayar,'ses_modeli':uyandirma.ses_ile_var()})
            if path=='/api/wake/settings':
                kelimeler=data.get('kelimeler')
                if kelimeler is not None and not isinstance(kelimeler,list): raise ValueError('Kelimeler liste olmalı.')
                aktif=data.get('aktif')
                if aktif is not None and not isinstance(aktif,bool): raise ValueError('Aktif alanı doğru/yanlış olmalı.')
                return self.out(uyandirma.ayar_yaz(aktif=aktif,kelimeler=kelimeler))
            if path=='/api/mcp/status':
                ayar=MCP.yenile()
                return self.out({'servers':MCP.durum(),'configured':len(ayar['sunucular'])})
            if path=='/api/mcp/tools':
                MCP.yenile()
                return self.out({'tools':MCP.araclar()})
            if path=='/api/mcp/call':
                if data.get('confirmed') is not True: raise ValueError('Araç çalıştırmak için onay gerekli.')
                sunucu=data.get('server'); arac=data.get('tool')
                if not isinstance(sunucu,str) or not isinstance(arac,str): raise ValueError('Sunucu ve araç adı gerekli.')
                argumanlar=data.get('arguments')
                if argumanlar is None: argumanlar={}
                if not isinstance(argumanlar,dict): raise ValueError('Argümanlar nesne olmalı.')
                try:
                    MCP.yenile()
                    sonuc=MCP.cagir(sunucu,arac,argumanlar)
                except Exception as hata:
                    _denetle('mcp',f'{sunucu}/{arac} çağrısı başarısız',str(hata),'hata')
                    raise
                _denetle('mcp',f'{sunucu}/{arac} çağrıldı',f'{len(sonuc["metin"])} karakter')
                return self.out({'ok':not sonuc['hata'],'result':sonuc['metin']})
            if path=='/api/screen/capture':
                if data.get('confirmed') is not True: raise ValueError('Ekran görüntüsü için onay gerekli.')
                gorsel=ekran.base64_png()
                _denetle('ekran','ekran görüntüsü alındı',f'{len(gorsel)//1024} KB (base64)')
                return self.out({'image':gorsel,'type':'image/png'})
            if path=='/api/screen/ask':
                if data.get('confirmed') is not True: raise ValueError('Ekranı sormak için onay gerekli.')
                soru=str(data.get('question') or 'Ekranda ne var? Kısaca açıkla.').strip()[:600]
                if not SAG.yukle()['base_url']:
                    raise ValueError('Ekranı yorumlamak için görsel destekli bir sağlayıcı bağla (Ayarlar > Ücretsiz API).')
                try:
                    gorsel=ekran.base64_png()
                except ValueError as hata:
                    raise ValueError(str(hata))
                mesajlar=[{'role':'system','content':'Ekran görüntüsünü inceleyip Türkçe, kısa ve net yanıt ver.'},
                          {'role':'user','content':[{'type':'text','text':soru},
                                                    {'type':'image_url','image_url':{'url':'data:image/png;base64,'+gorsel}}]}]
                msg=SAG.sohbet(mesajlar, max_tokens=500, timeout=90)
                _denetle('ekran','ekran sorusu yanıtlandı',soru)
                return self.out({'reply':(msg.get('content') or '').strip()})
            if path=='/api/dictate/window':
                # Canlı dikte: istemci her ~1 sn'de son birkaç saniyeyi gönderir.
                if not isinstance(data.get('audio'),str): raise ValueError('Ses verisi gerekli.')
                oturum=str(data.get('session') or 'varsayilan')[:64]
                if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',oturum): oturum='varsayilan'
                with DIKTE_KILIT:
                    durum=dikte_oturum(oturum)
                    ipucu=dikte.ipucu(durum.metin)
                ham=ses_baglanti.transcribe(data.get('audio'), ipucu=ipucu)
                ayar=uyandirma.ayar_oku()
                uyandi=False; komut=''
                if ayar['aktif']:
                    uyandi,komut=uyandirma.ayikla(ham,ayar['kelimeler'])
                with DIKTE_KILIT:
                    durum=dikte_oturum(oturum)
                    simdi=time.time()
                    if uyandi: durum.uyandi=simdi
                    # Uyandırma sözcüğü son 12 saniye içinde duyulduysa devam eden komut sayılır.
                    devam=bool(durum.uyandi) and (simdi-durum.uyandi)<12
                    if ayar['aktif'] and not (uyandi or devam):
                        return self.out({'text':'','added':'','full':durum.metin,'triggered':False,
                                         'model':ses_baglanti.model(),'final':False})
                    eklenen,tam=durum.ekle(komut if uyandi else ham)
                return self.out({'text':dikte.temizle(ham),'added':eklenen,'full':tam,'triggered':True,
                                 'model':ses_baglanti.model(),'final':False})
            if path=='/api/dictate/finish':
                oturum=str(data.get('session') or 'varsayilan')[:64]
                with DIKTE_KILIT:
                    durum=DIKTE.get(oturum)
                    metin=dikte.bicimlendir(durum.metin, bitir=True) if durum else ''
                # İsteğe bağlı: yapay zekâ ile noktalama/yazım düzeltmesi.
                duzeltilmis=False
                if data.get('polish') is True and metin and SAG.yukle()['base_url']:
                    try:
                        cevap=SAG.sohbet([
                            {'role':'system','content':('Sen bir Türkçe dikte düzelticisisin. Verilen metnin '
                             'yalnızca noktalama, büyük harf ve açık yazım hatalarını düzelt. Kelime ekleme, '
                             'özetleme veya anlam değiştirme. Yanıt olarak SADECE düzeltilmiş metni yaz.')},
                            {'role':'user','content':metin[:2000]}], max_tokens=600, timeout=45)
                        oneri=str(cevap.get('content') or '').strip()
                        if oneri and abs(len(oneri)-len(metin))<=max(40,len(metin)//3):
                            metin=oneri
                            duzeltilmis=True
                    except ValueError:
                        pass  # sağlayıcı yoksa/başarısızsa kural tabanlı metin kalır
                return self.out({'text':metin,'polished':duzeltilmis})
            if path=='/api/dictate/reset':
                oturum=str(data.get('session') or 'varsayilan')[:64]
                with DIKTE_KILIT:
                    DIKTE.pop(oturum, None)
                return self.out({'ok':True})
            if path=='/api/dictate/type':
                # Metni ETKİN pencereye yazar (ör. Antigravity). Onay zorunludur.
                if data.get('confirmed') is not True: raise ValueError('Yazma için onay gerekli.')
                metin=data.get('text')
                if not isinstance(metin,str): raise ValueError('Yazılacak metin gerekiyor.')
                if not metin.strip(): raise ValueError('Yazılacak metin boş.')
                if len(metin)>dikte_yaz.EN_UZUN: raise ValueError('Metin çok uzun; parçalara böl.')
                hedef=data.get('target') or ''
                if not isinstance(hedef,str) or len(hedef)>80: raise ValueError('Hedef pencere adı geçersiz.')
                enter=bool(data.get('enter'))
                sonuc=dikte_yaz.yaz(metin, hedef=hedef, enter=enter)
                _denetle('dikte','etkin pencereye yazıldı',f'{len(metin)} karakter · {hedef or "(serbest)"}')
                return self.out(sonuc)
            if path=='/api/dictate/status':
                return self.out({'sessions':len(DIKTE),'model':ses_baglanti.model(),
                                 'typing_supported':os.name=='nt',
                                 'window':dikte_yaz.etkin_baslik() if os.name=='nt' else ''})
            if path=='/api/speech/model':
                ad=str(data.get('model') or '').strip().lower()
                if ad not in ses_baglanti.MODELLER: raise ValueError('Model base veya small olmalı.')
                return self.out({'ok':True,'status':ses_baglanti.ayarla(ad)})
            if path=='/api/arena/test-api':
                if data.get('confirmed') is not True: raise ValueError('Test isteği için onay gerekli.')
                key=str(data.get('key','')).strip();model=str(data.get('model','')).strip();prompt=str(data.get('prompt','')).strip()
                if not key or len(key)>500 or '\n' in key or '\r' in key: raise ValueError('Geçerli API anahtarını gir.')
                if not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,150}',model): raise ValueError('Geçerli model kimliğini gir.')
                if not prompt or len(prompt)>3000: raise ValueError('Test mesajı 1–3000 karakter olmalı.')
                req=urllib.request.Request('https://api.arena.ai/v1/chat/completions',data=json.dumps({'model':model,'messages':[{'role':'user','content':prompt}],'max_tokens':250,'stream':False}).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json','Accept':'application/json'},method='POST')
                try:
                    with urllib.request.urlopen(req,timeout=90) as res:
                        result=json.load(res)
                except urllib.error.HTTPError as exc:
                    messages={401:'API anahtarı kabul edilmedi (401).',403:'Bu anahtarın veya hesabın bu istemci/model için erişimi yok (403).',404:'Model veya API yolu bulunamadı (404).',429:'Kota veya hız sınırına ulaşıldı (429).'}
                    return self.out({'error':messages.get(exc.code,f'Arena API isteği başarısız (HTTP {exc.code}).')},502)
                except Exception:
                    return self.out({'error':'Arena API bağlantısı kurulamadı veya yanıt çözümlenemedi.'},502)
                choices=result.get('choices') or []
                if not choices: return self.out({'error':'Arena API yanıtında mesaj bulunamadı.'},502)
                content=choices[0].get('message',{}).get('content')
                if not isinstance(content,str) or not content.strip(): return self.out({'error':'Arena API boş veya desteklenmeyen bir yanıt döndürdü.'},502)
                return self.out({'reply':content,'usage':result.get('usage',{})})
            if path=='/api/apps/open':
                if os.name != 'nt': raise ValueError('Uygulama açma şu an yalnızca Windows içindir.')
                if data.get('confirmed') is not True: raise ValueError('Uygulama açma onayı gerekli.')
                allowed={'notepad':'notepad.exe','calculator':'calc.exe','paint':'mspaint.exe','explorer':'explorer.exe'}
                app=allowed.get(data.get('app')) if isinstance(data.get('app'),str) else None
                if not app: raise ValueError('Bu uygulama desteklenmiyor.')
                system=Path(os.environ.get('SystemRoot',r'C:\Windows'))
                exe=system/'explorer.exe' if app=='explorer.exe' else system/'System32'/app
                if not exe.is_file(): raise ValueError('Uygulama bu bilgisayarda bulunamadı.')
                subprocess.Popen([str(exe)],close_fds=True)
                _denetle('uygulama','uygulama açıldı',app)
                return self.out({'ok':True})
            if path=='/api/arena/open-normal':
                if os.name != 'nt': raise ValueError('Bu özellik Windows içindir.')
                candidates = [Path(os.environ.get('PROGRAMFILES(X86)', r'C:\Program Files (x86)')) / 'Microsoft' / 'Edge' / 'Application' / 'msedge.exe', Path(os.environ.get('PROGRAMFILES', r'C:\Program Files')) / 'Microsoft' / 'Edge' / 'Application' / 'msedge.exe']
                edge = next((p for p in candidates if p.is_file()), None)
                if not edge: raise ValueError('Microsoft Edge varsayılan konumda bulunamadı.')
                subprocess.Popen([str(edge), 'https://arena.ai/agent'], close_fds=True)
                return self.out({'ok':True})
            if path=='/api/arena/start':
                arena_bridge.start()
                return self.out({'ok':True})
            if path=='/api/arena/send':
                if data.get('confirmed') is not True: raise ValueError('Soru göndermek için onay gerekli.')
                arena_bridge.send(text_field(data,'question',6000,required=True,label='Soru'))
                return self.out({'ok':True})
            if path=='/api/provider/models':
                taban=data.get('base_url'); anahtar=data.get('key')
                if taban is not None and not isinstance(taban,str): raise ValueError('Sunucu adresi metin olmalı.')
                if anahtar is not None and not isinstance(anahtar,str): raise ValueError('API anahtarı metin olmalı.')
                if taban and taban.strip():
                    saglayici.normalize_base(taban)
                modeller=SAG.modeller(base_url=taban or None, key=anahtar)
                ucretsiz=[m for m in modeller if 'free' in m.lower()]
                return self.out({'models':modeller,'free':ucretsiz,'total':len(modeller)})
            if path=='/api/provider/test':
                # Kayıtlı yapılandırmayla minik bir sohbet denemesi: hata varsa
                # sağlayıcının kendi mesajını olduğu gibi gösterir.
                if not SAG.yukle()['base_url']:
                    raise ValueError('Ücretsiz API sağlayıcısı ayarlanmamış.')
                model=data.get('model')
                if model is not None and not isinstance(model,str): raise ValueError('Model adı metin olmalı.')
                try:
                    msg=SAG.sohbet([{'role':'user','content':'Yalnızca "hazır" yaz.'}],
                                   model=(model or '').strip() or None, max_tokens=16, timeout=60)
                except ValueError as hata:
                    return self.out({'ok':False,'error':str(hata),'base_url':SAG.yukle()['base_url']},400)
                return self.out({'ok':True,'reply':(msg.get('content') or '').strip()[:200],
                                 'model':SAG.yukle()['model']})
            if path=='/api/provider/scan':
                # Yalnızca kendi bilgisayarındaki bilinen portlar denenir; adres
                # istemciden alınmaz (yalnızca ek port numarası verilebilir).
                ek=data.get('ports') or []
                if not isinstance(ek,list) or len(ek)>12: raise ValueError('Port listesi geçersiz.')
                bulunan=SAG.tara(ek_portlar=ek)
                return self.out({'gateways':bulunan,'alive':[g for g in bulunan if g['alive']],
                                 'total_alive':sum(1 for g in bulunan if g['alive'])})
            if path=='/api/provider/connect':
                if data.get('confirmed') is not True: raise ValueError('Bağlantı için onay gerekli.')
                taban=data.get('base_url'); anahtar=data.get('key'); model=data.get('model')
                for alan,deger in (('Sunucu adresi',taban),('API anahtarı',anahtar),('Model',model)):
                    if deger is not None and not isinstance(deger,str): raise ValueError(alan+' metin olmalı.')
                if not isinstance(taban,str) or not taban.strip(): raise ValueError('Sunucu adresi gerekli.')
                if not isinstance(model,str) or not model.strip(): raise ValueError('Model seçilmeli.')
                # Kaydetmeden önce doğrula: yanlış anahtar dosyaya yazılmasın.
                modeller=SAG.modeller(base_url=taban, key=anahtar or '')
                if model.strip() not in modeller:
                    raise ValueError('Seçilen model sağlayıcının listesinde yok. Listeyi yenileyip tekrar seç.')
                SAG.kaydet(taban, anahtar or '', model)
                _denetle('saglayici','sağlayıcı bağlandı',f'{taban} · {model}')
                return self.out({'ok':True,'status':SAG.durum()})
            if path=='/api/provider/disconnect':
                if data.get('confirmed') is not True: raise ValueError('Bağlantıyı kesmek için onay gerekli.')
                SAG.sil()
                _denetle('saglayici','sağlayıcı bağlantısı kesildi','anahtar silindi')
                return self.out({'ok':True})
            if path=='/api/telegram/connect':
                candidate=str(data.get('token','')).strip()
                if not re.fullmatch(r'\d{5,15}:[A-Za-z0-9_-]{20,100}',candidate): raise ValueError('Bot anahtarı biçimi geçersiz.')
                try:
                    info=request_json('https://api.telegram.org/bot'+candidate+'/getMe', timeout=15)
                    if not info.get('ok') or not info.get('result',{}).get('is_bot'): raise ValueError()
                except Exception: raise ValueError('Bot doğrulanamadı. Anahtarı ve internet bağlantısını kontrol et.')
                TOKEN=candidate
                BOT.start(candidate)
                return self.out({'ok':True,'username':info['result'].get('username','')})
            if path=='/api/telegram/disconnect':
                TOKEN=''
                BOT.stop()
                return self.out({'ok':True})
            if path=='/api/telegram/mark-read':
                BOT.mark_read()
                return self.out({'ok':True})
            if path=='/api/telegram/poll':
                if not BOT.configured(): raise ValueError('Telegram bot anahtarı ayarlanmamış.')
                BOT.start(TOKEN)
                return self.out({'ok':True,'status':BOT.status()})
            if path=='/api/chat/stream':
                return self.chat_akis(data)
            if path=='/api/chat':
                messages=data.get('messages',[])
                if not isinstance(messages,list): raise ValueError('Mesaj listesi geçersiz.')
                messages=messages[-12:]
                clean=[{'role':m['role'],'content':str(m['content'])[:6000]} for m in messages if isinstance(m,dict) and m.get('role') in ('user','assistant') and isinstance(m.get('content'),str)]
                if not clean: raise ValueError('Mesaj boş.')
                selected=str(data.get('model') or MODEL).strip()
                if len(selected)>200: raise ValueError('Model adı çok uzun.')
                if not re.fullmatch(r'[\w.\-:/]{1,200}',selected): raise ValueError('Model adı geçersiz.')
                last_user = next((m['content'] for m in reversed(clean) if m['role']=='user'), '')
                session=str(data.get('session') or '').strip()[:80]
                if session and not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',session): session=''
                if session: store_message(session,'user',last_user)
                # Açık bilgiler ("hatırla", "benim adım", telefon…) hemen kaydedilir;
                # ilgili eski kayıtlar bağlama eklenir.
                with db() as c:
                    bellek.kaydet_cikarimlar(c,last_user,source='sohbet')
                    kisisel=bellek.baglam(c,last_user,limit=5)
                web_metin, kaynaklar = web_baglami(last_user, data.get('web'))
                belge_metin, belge_kaynaklar = belge_baglami(last_user, data.get('doc_id'))
                if belge_metin:
                    kaynaklar = list(kaynaklar or []) + [{'title': x['name'] + ' · sayfa ' + str(x['sayfa']),
                                                         'url': ''} for x in belge_kaynaklar]
                def yanitla(text, kaynaklar=None):
                    if session: store_message(session,'assistant',text)
                    return self.out({'reply':text,'sources':kaynaklar or []})
                unut_yanit, _silinen = unutma_cagrisi(last_user)
                if unut_yanit is not None: return yanitla(unut_yanit)
                for kural in (takvim_yaniti, posta_yaniti):
                    yanit, _veri = kural(last_user)
                    if yanit is not None: return yanitla(yanit)
                beceri_yanit, beceri_adi = beceri_cagrisi(last_user)
                if beceri_yanit is not None: return yanitla(beceri_yanit)
                direct=ledger_tools.create_account_from_text(last_user,db)
                if direct is not None: return yanitla(direct)
                # Hatırlatıcı niyeti modelden önce kural tabanlı çözülür (A1).
                direct=hatirlatici.direct_reminder_action(last_user,db)
                if direct is not None: return yanitla(direct)
                direct=ledger_tools.direct_ledger_action(last_user,db)
                if direct is not None: return yanitla(direct)
                backend=str(data.get('backend') or 'ollama').strip().lower()
                # Model kontrolü kural tabanlı işlemlerden SONRA yapılır: Ollama kapalıyken
                # bile hatırlatıcı ve defter komutları çalışmaya devam eder.
                if backend in ('api','openai','omnirouter','openrouter','saglayici'):
                    backend='api'
                    if not SAG.yukle()['base_url']:
                        raise ValueError('Ücretsiz API sağlayıcısı ayarlanmamış. Ayarlar > Ücretsiz API bölümünden bağlan.')
                elif backend=='ollama':
                    installed={m.get('name') for m in request_json(OLLAMA+'/api/tags',timeout=5).get('models',[])}
                    if selected not in installed and selected+':latest' not in installed: raise ValueError('Seçilen model Ollama üzerinde kurulu değil.')
                    # Qwen3 supports both the API flag and an explicit no-thinking directive.
                    if selected.lower().startswith('qwen3'):
                        clean[-1]['content'] += '\n/no_think'
                beceri_metin=beceriler.baglam()
                system=SYSTEM+(' '+kisisel if kisisel else '')+(' '+beceri_metin if beceri_metin else '')+(' '+web_metin if web_metin else '')+(' '+belge_metin if belge_metin else '')+' Yerel tarih ve saat: '+datetime.now().strftime('%Y-%m-%d %H:%M')+'. Kullanıcı defter kaydı veya bakiyesi isterse uygun aracı kullan. Kayıt belirsizse soru sor. Gerçek ödeme yapma. Hatırlatıcı için açık tarih ve saat gerekli. Deftere kayıt, tahsilat ve ödeme ekleme için ayrıca onay sorma.'
                if backend=='openjarvis':
                    if selected not in ('emre-cpu','emre-cpu:latest'): return self.out({'error':'OpenJarvis için önce emre-cpu modelini oluştur ve Ayarlar’dan seç.'},400)
                    # Client-supplied tools keep tool execution under Emre's validation.
                    result=request_json(OPENJARVIS+'/v1/chat/completions',{'model':selected,'messages':[{'role':'system','content':system}]+clean,'tools':ledger_tools.TOOLS,'stream':False,'max_tokens':400},timeout=300)
                    choices=result.get('choices') or []
                    if not choices: raise ValueError('OpenJarvis yanıt döndürmedi.')
                    msg=choices[0].get('message',{})
                elif backend=='api':
                    # OpenAI uyumlu sağlayıcı: OmniRoute, OpenRouter, Groq, Gemini…
                    # Model belirtilmemişse sağlayıcı ayarında kayıtlı model kullanılır.
                    api_model=str(data.get('model') or '').strip() or None
                    try:
                        msg=SAG.sohbet([{'role':'system','content':system}]+clean, model=api_model,
                                       tools=ledger_tools.TOOLS, max_tokens=500, timeout=120)
                    except ValueError as hata:
                        kota_artir(basarili=False)
                        if saglayici.gecici_hata(hata):
                            _denetle('saglayici','kota/hız sınırı',str(hata)[:120],'hata')
                        raise ValueError('Ücretsiz API ('+SAG.yukle()['base_url']+' · '+str(api_model or SAG.yukle()['model'])+'): '+str(hata))
                    kota_artir(basarili=True, yedek=bool(msg.get('_yedek_model')))
                    if msg.get('_yedek_model'):
                        _denetle('saglayici','yedek model kullanıldı',f"{msg.get('_asil_model')} → {msg.get('_yedek_model')}")
                elif backend=='ollama':
                    result=request_json(OLLAMA+'/api/chat',{'model':selected,'messages':[{'role':'system','content':system}]+clean,'tools':ledger_tools.TOOLS,'stream':False,'think':False,'options':{'num_ctx':4096,'num_predict':400,'num_gpu':0}}, timeout=300)
                    msg=result.get('message',{})
                else: raise ValueError('Bilinmeyen yapay zekâ bağlantısı.')
                calls=msg.get('tool_calls') or []
                if calls:
                    if len(calls)!=1: return yanitla('Bir seferde tek işlem yapabiliyorum; lütfen işlemleri ayrı ayrı söyle.')
                    fn=calls[0].get('function',{}) if isinstance(calls[0],dict) else {}
                    if not isinstance(fn,dict): fn={}
                    try: reply=ledger_tools.execute(fn.get('name'),fn.get('arguments',{}),db,last_user)
                    except (ValueError,TypeError,KeyError) as err: reply='Kayıt yapılmadı: '+str(err)
                    return yanitla(reply, kaynaklar)
                raw_content=msg.get('content','') or ''
                # Never read a model-generated tool JSON aloud or mistake it for a successful action.
                try: raw_json=json.loads(raw_content.strip())
                except (ValueError,TypeError): raw_json=None
                if (isinstance(raw_json,dict) and ('arguments' in raw_json or 'tool_calls' in raw_json)) or re.search(r'["\'](?:arguments|tool_calls)["\']\s*:', raw_content):
                    return yanitla('İşlemi anlayamadım; kayıt oluşturulmadı. Hesap adını ve yapmak istediğin işlemi tekrar söyle.', kaynaklar)
                reply=clean_reply(raw_content)
                if re.search(r'(?i)kay[ıi]t (?:edildi|oluşturuldu)|kaydetti[mn]|deftere (?:ekledim|işledim)|hatırlatıcı (?:oluşturdum|ayarladım)|(?:alacak|verecek|hesap|defter|ödeme|tahsilat).{0,120}(?:gerçekleştirdim|ekledim|oluşturdum|sildim|kaydedildi|yaptım)',reply):
                    reply='Bu işlem için deftere kayıt yapılmadı. Kişiyi, tutarı ve işlem türünü açıkça belirt.'
                return yanitla(reply, kaynaklar)
            if path=='/api/history/delete':
                if data.get('confirmed') is not True: raise ValueError('Silme onayı gerekli.')
                session=text_field(data,'session',80,label='Oturum')
                with db() as c:
                    cur=c.execute('DELETE FROM messages WHERE session=?',(session,)) if session else c.execute('DELETE FROM messages')
                return self.out({'ok':True,'deleted':cur.rowcount})
            if path=='/api/accounts/delete':
                if data.get('confirmed') is not True: raise ValueError('Silme onayı gerekli.')
                name=str(data.get('name','')).strip()
                if not name: raise ValueError('Hesap adı gerekli.')
                with db() as c:
                    key=tr_key(name)
                    a_ids=[r[0] for r in c.execute('SELECT id,name FROM accounts').fetchall() if tr_key(r[1])==key]
                    l_ids=[r[0] for r in c.execute('SELECT id,person FROM ledger').fetchall() if tr_key(r[1])==key]
                    if not a_ids and not l_ids: raise ValueError('Hesap bulunamadı.')
                    c.executemany('DELETE FROM accounts WHERE id=?',[(i,) for i in a_ids])
                    c.executemany('DELETE FROM ledger WHERE id=?',[(i,) for i in l_ids])
                return self.out({'ok':True,'deleted_entries':len(l_ids)})
            if path=='/api/accounts':
                name=text_field(data,'name',100,required=True,label='Hesap adı'); note=text_field(data,'note',300,label='Açıklama')
                with db() as c:
                    existing=[r[0] for r in c.execute('SELECT name FROM accounts UNION SELECT DISTINCT person FROM ledger')]
                    if any(tr_key(x)==tr_key(name) for x in existing):
                        raise ValueError('Bu isimde bir hesap zaten var.')
                    c.execute('INSERT INTO accounts(name,note) VALUES (?,?)',(name,note))
                return self.out({'ok':True})
            if path=='/api/ledger':
                person=text_field(data,'person',100,required=True,label='Kişi adı'); kind=data.get('kind'); amount=data.get('amount'); note=text_field(data,'note',300,label='Açıklama'); due=text_field(data,'due',40,label='Tarih')
                if kind not in ('receivable','payable','received','paid') or type(amount) is not int or not 0 < amount <= 100000000000: raise ValueError('Kişi, işlem türü ve geçerli tutar gerekli.')
                if due:
                    try: datetime.fromisoformat(due)
                    except ValueError: raise ValueError('Tarih biçimi geçersiz; YYYY-AA-GG SS:DD kullan.')
                if data.get('remind') and (not due or kind not in ('receivable','payable')): raise ValueError('Hatırlatıcı için alacak/verecek ve tarih gerekli.')
                with db() as c:
                    c.execute('INSERT INTO ledger(person,kind,amount,note,due,created) VALUES (?,?,?,?,?,?)',(person,kind,amount,note,due or None,datetime.now().isoformat(timespec='seconds')))
                    if data.get('remind'):
                        label='Alacak' if kind=='receivable' else 'Verecek'
                        c.execute('INSERT INTO reminders(text,due) VALUES (?,?)',(f'{label}: {person} — {amount/100:.2f} TL',due))
                return self.out({'ok':True})
            if path=='/api/ledger/delete':
                if data.get('confirmed') is not True: raise ValueError('Silme onayı gerekli.')
                with db() as c: c.execute('DELETE FROM ledger WHERE id=?',(int_field(data,'id',1,2**53,label='Kayıt numarası'),))
                _denetle('defter','kayıt silindi',f'id={data.get("id")}')
                return self.out({'ok':True})
            if path=='/api/reminders':
                text=text_field(data,'text',300,required=True,label='Hatırlatıcı metni'); due=text_field(data,'due',40,required=True,label='Tarih')
                try: datetime.fromisoformat(due)
                except ValueError: raise ValueError('Tarih biçimi geçersiz; YYYY-AA-GG SS:DD kullan.')
                with db() as c: c.execute('INSERT INTO reminders(text,due) VALUES (?,?)',(text,due))
                return self.out({'ok':True})
            if path=='/api/notifications/seen':
                ids=data.get('ids')
                if ids is not None and not isinstance(ids,list):
                    raise ValueError('Kimlikler liste olmalı.')
                with db() as c:
                    if ids:
                        temiz=[int(x) for x in ids if isinstance(x,(int,str)) and str(x).isdigit()][:50]
                        c.executemany('UPDATE notifications SET seen=1 WHERE id=?',[(i,) for i in temiz])
                    else: c.execute('UPDATE notifications SET seen=1')
                return self.out({'ok':True})
            if path=='/api/memory/import':
                if data.get('confirmed') is not True: raise ValueError('Bellek geri yükleme için onay gerekli.')
                mod=str(data.get('mode') or 'birlestir').strip().lower()
                yedek=data.get('backup')
                if isinstance(yedek,str):
                    try: yedek=json.loads(yedek)
                    except ValueError: raise ValueError('Yedek JSON biçimi geçersiz.')
                with db() as c:
                    sonuc=bellek.ice_aktar(c,yedek,mod=mod)
                _denetle('bellek','bellek yedeği geri yüklendi',f'{sonuc["eklenen"]} eklendi · {mod}')
                return self.out({'ok':True,**sonuc})
            if path=='/api/memory/forget':
                sorgu=str(data.get('q') or '').strip()
                if data.get('confirmed') is not True: raise ValueError('Unutmak için onay gerekli.')
                with db() as c: sonuc=bellek.unut(c,sorgu)
                if not sonuc['silinen']: raise ValueError('Eşleşen kayıt bulunamadı.')
                _denetle('bellek','bellek kayıtları unutuldu',f'{sonuc["silinen"]} kayıt · {sorgu}')
                return self.out({'ok':True,'deleted':sonuc['silinen']})
            if path=='/api/memory/archive':
                if data.get('confirmed') is not True: raise ValueError('Arşivleme için onay gerekli.')
                with db() as c: sonuc=bellek.arsivle(c,data.get('gun') or bellek.VARSAYILAN_ARSIV_GUN)
                _denetle('bellek','bellek yaşlandırıldı',f'{sonuc["silinen"]} kayıt · {sonuc["gun"]} gün')
                return self.out({'ok':True,**sonuc})
            if path=='/api/provider/fallback':
                model=data.get('model','')
                if not isinstance(model,str): raise ValueError('Model adı metin olmalı.')
                SAG.yedek_ayarla(model)
                _denetle('saglayici','yedek model ayarlandı',model or '(kaldırıldı)')
                return self.out({'ok':True,'status':SAG.durum()})
            if path=='/api/docs/import':
                if data.get('confirmed') is not True: raise ValueError('Belge eklemek için onay gerekli.')
                yol=data.get('path'); ad=data.get('name'); icerik=data.get('content')
                with db() as c:
                    if isinstance(yol,str) and yol.strip():
                        sonuc=belge.dosya_ekle(c,yol.strip())
                    elif isinstance(icerik,str) and icerik.strip():
                        if not isinstance(ad,str) or not ad.strip(): raise ValueError('Dosya adı gerekli.')
                        sonuc=belge.icerik_ekle(c,ad.strip(),icerik,kind=str(data.get('kind') or ''))
                    else: raise ValueError('Dosya yolu veya içerik gerekli.')
                _denetle('belge','belge eklendi',f'{sonuc["name"]} · {sonuc["pages"]} sayfa')
                return self.out({'ok':True,**sonuc})
            if path=='/api/docs/delete':
                if data.get('confirmed') is not True: raise ValueError('Belge silmek için onay gerekli.')
                with db() as c: sayi=belge.sil(c,int(data.get('id') or 0))
                if not sayi: raise ValueError('Belge bulunamadı.')
                _denetle('belge','belge silindi',f'id={data.get("id")}')
                return self.out({'ok':True,'deleted':sayi})
            if path=='/api/docs/ask':
                soru=str(data.get('question') or '').strip()[:600]
                if not soru: raise ValueError('Soru gerekli.')
                doc_id=data.get('id')
                with db() as c:
                    belgeler=belge.listele(c)
                    if not belgeler: raise ValueError('Önce bir belge ekle (Ayarlar › Belgeler).')
                    parcalar=belge.ara(c,soru,doc_id=doc_id,limit=5)
                    adlar={b['id']:b['name'] for b in belgeler}
                if not parcalar:
                    return self.out({'reply':'Bu soruyla ilgili bölüm bulamadım. Farklı kelimelerle sorabilir '
                                             'ya da belgeyi yeniden ekleyebilirsin.','sources':[]})
                kaynaklar=[{'name':x['name'],'sayfa':x['sayfa'],'id':x['doc_id']} for x in parcalar]
                baglam=belge.baglam(parcalar)
                mesajlar=[{'role':'system','content':SYSTEM+' '+baglam},
                          {'role':'user','content':soru}]
                backend=str(data.get('backend') or '').strip().lower()
                if backend in ('api','openai','openrouter','omnirouter','saglayici') or (
                        not backend and SAG.yukle()['base_url']):
                    msg=SAG.sohbet(mesajlar,max_tokens=500,timeout=120)
                    yanit=(msg.get('content') or '').strip()
                else:
                    secili=str(data.get('model') or MODEL).strip()
                    sonuc=request_json(OLLAMA+'/api/chat',{'model':secili,'messages':mesajlar,'stream':False,
                                                          'think':False,'options':{'num_ctx':4096,'num_predict':400,'num_gpu':0}},
                                       timeout=300)
                    yanit=clean_reply((sonuc.get('message') or {}).get('content',''))
                _denetle('belge','belge sorusu yanıtlandı',f'{soru[:80]} · {len(parcalar)} bölüm')
                return self.out({'reply':yanit,'sources':kaynaklar,
                                 'docs':[adlar.get(x['doc_id'],'') for x in parcalar]})
            if path=='/api/image/generate':
                if data.get('confirmed') is not True:
                    raise ValueError('Görsel üretmek için onay gerekli.')
                istem=str(data.get('prompt') or '').strip()
                boyut=str(data.get('size') or '1024x1024')
                with db() as c: model=ayar_al(c,'gorsel_model','')
                sonuc=SAG.gorsel(istem,model=model,boyut=boyut)
                _denetle('gorsel','görsel üretildi',istem[:80])
                return self.out({'ok':True,'image':sonuc['image'],'mime':'image/png',
                                 'model':sonuc['model'],'size':sonuc['size']})
            if path=='/api/image/model':
                model=str(data.get('model') or '').strip()[:120]
                with db() as c: ayar_yaz(c,'gorsel_model',model)
                _denetle('gorsel','görsel modeli ayarlandı',model or '(kaldırıldı)')
                return self.out({'ok':True,'model':model})
            if path=='/api/calendar/path':
                yol=data.get('path','')
                if yol is not None and not isinstance(yol,str): raise ValueError('Yol metin olmalı.')
                yol=str(yol or '').strip()[:400]
                if yol:
                    try: takvim.yolu_oku(yol)
                    except ValueError as hata: raise ValueError(str(hata))
                with db() as c: ayar_yaz(c,'takvim_yolu',yol)
                _denetle('takvim','takvim yolu ayarlandı',yol or '(kaldırıldı)')
                return self.out({'ok':True,'path':yol})
            if path=='/api/mail/path':
                yol=data.get('path','')
                if yol is not None and not isinstance(yol,str): raise ValueError('Yol metin olmalı.')
                yol=str(yol or '').strip()[:400]
                if yol:
                    try: posta.yolu_oku(yol)
                    except ValueError as hata: raise ValueError(str(hata))
                with db() as c: ayar_yaz(c,'posta_yolu',yol)
                _denetle('posta','posta yolu ayarlandı',yol or '(kaldırıldı)')
                return self.out({'ok':True,'path':yol})
            if path=='/api/system/tts':
                with db() as c:
                    akis=data.get('akis'); barge=data.get('barge_in')
                    if akis is not None:
                        if not isinstance(akis,bool): raise ValueError('akis doğru/yanlış olmalı.')
                        ayar_yaz(c,'tts_akis','1' if akis else '0')
                    if barge is not None:
                        if not isinstance(barge,bool): raise ValueError('barge_in doğru/yanlış olmalı.')
                        ayar_yaz(c,'barge_in','1' if barge else '0')
                    sonuc={'akis':ayar_al(c,'tts_akis','1')=='1','barge_in':ayar_al(c,'barge_in','1')=='1'}
                return self.out(sonuc)
            if path=='/api/tts/split':
                # Akışlı seslendirme için metni cümlelere böler (istemci kullanır).
                metin=data.get('text')
                if not isinstance(metin,str): raise ValueError('Metin gerekli.')
                if len(metin)>6000: raise ValueError('Metin çok uzun.')
                return self.out({'sentences':sesli_yanit.cumlelere_ayir(metin)})
            if path=='/api/skills/run':
                if data.get('confirmed') is not True: raise ValueError('Beceri çalıştırmak için onay gerekli.')
                ad=str(data.get('ad') or '').strip().lower()
                metin=str(data.get('metin') or '')[:2000]
                try:
                    sonuc=beceriler.calistir(ad,metin)
                except ValueError as hata:
                    _denetle('beceri',f'{ad} çalıştırılamadı',str(hata),'hata')
                    raise
                _denetle('beceri',f'{ad} çalıştırıldı',f'{len(sonuc["reply"])} karakter, {sonuc["sure"]} sn')
                return self.out({'ok':True,**sonuc})
            if path=='/api/audit/clear':
                if data.get('confirmed') is not True: raise ValueError('Denetim kayıtlarını silmek için onay gerekli.')
                with db() as c: sayi=denetim.temizle(c)
                _denetle('denetim','kayıtlar temizlendi',f'{sayi} kayıt')
                return self.out({'ok':True,'deleted':sayi})
            if path=='/api/system/autostart':
                if data.get('confirmed') is not True: raise ValueError('Açılış ayarı için onay gerekli.')
                aktif=data.get('aktif')
                if not isinstance(aktif,bool): raise ValueError('Aktif alanı doğru/yanlış olmalı.')
                if aktif: sonuc=otomatik_baslat.kur(ROOT)
                else: sonuc=otomatik_baslat.kaldir(ROOT)
                _denetle('sistem','otomatik başlatma ' + ('kuruldu' if aktif else 'kaldırıldı'),sonuc.get('yol') or '')
                return self.out(sonuc)
            if path=='/api/system/hotkey':
                aktif=data.get('aktif')
                if not isinstance(aktif,bool): raise ValueError('Aktif alanı doğru/yanlış olmalı.')
                tus=data.get('kisayol')
                tarayici=data.get('tarayici')
                with db() as c:
                    if tarayici is not None:
                        if not isinstance(tarayici,bool): raise ValueError('Tarayıcı alanı doğru/yanlış olmalı.')
                        ayar_yaz(c,'kisayol_tarayici','1' if tarayici else '0')
                    if isinstance(tus,str) and tus.strip():
                        kisayol.coz(tus.strip())  # geçersizse 400
                        ayar_yaz(c,'kisayol_tus',tus.strip()[:40])
                    guncel=ayar_al(c,'kisayol_tus',kisayol.VARSAYILAN)
                if aktif:
                    if not KISAYOL.destekli(): raise ValueError('Global kısayol yalnızca Windows\'ta çalışır.')
                    if KISAYOL.durum()['aktif'] and guncel!=KISAYOL.metin: KISAYOL.yeniden_basla(guncel)
                    elif not KISAYOL.durum()['aktif']:
                        KISAYOL.metin=guncel
                        KISAYOL.baslat()
                    with db() as c: ayar_yaz(c,'kisayol_aktif','1')
                else:
                    KISAYOL.durdur()
                    with db() as c: ayar_yaz(c,'kisayol_aktif','0')
                durum=dict(KISAYOL.durum()); durum['acik']=bool(aktif)
                _denetle('sistem','global kısayol ' + ('açıldı' if aktif else 'kapatıldı'),durum['gorunen'])
                return self.out(durum)
            if path=='/api/system/web':
                aktif=data.get('aktif')
                if not isinstance(aktif,bool): raise ValueError('Aktif alanı doğru/yanlış olmalı.')
                with db() as c: ayar_yaz(c,'web_arama','1' if aktif else '0')
                return self.out({'aktif':aktif})
            if path=='/api/system/notifications':
                aktif=data.get('aktif')
                if not isinstance(aktif,bool): raise ValueError('Aktif alanı doğru/yanlış olmalı.')
                with db() as c: ayar_yaz(c,'bildirim_aktif','1' if aktif else '0')
                return self.out({'aktif':aktif})
            if path=='/api/reminders/delete':
                if data.get('confirmed') is not True: raise ValueError('Silme onayı gerekli.')
                with db() as c: c.execute('DELETE FROM reminders WHERE id=?',(int_field(data,'id',1,2**53,label='Kayıt numarası'),))
                return self.out({'ok':True})
            if path=='/api/reminders/done':
                with db() as c: c.execute('UPDATE reminders SET done=1 WHERE id=?',(int_field(data,'id',1,2**53,label='Kayıt numarası'),))
                return self.out({'ok':True})
            if path=='/api/telegram/send':
                if data.get('confirmed') is not True: raise ValueError('Gönderme onayı gerekli.')
                chat_id=int_field(data,'chat_id',-2**53,2**53,label='Sohbet kimliği'); text=text_field(data,'text',4096,required=True,label='Mesaj')
                BOT.send(chat_id,text)
                return self.out({'ok':True})
            return self.out({'error':'Bulunamadı'},404)
        except urllib.error.HTTPError as e:
            try: message=json.loads(e.read()).get('error','Servis hatası')
            except Exception: message='Servis hatası'
            return self.out({'error':str(message)},502)
        except ValueError as e: return self.out({'error':str(e)},400)
        except Exception as e: return self.out({'error':friendly_error(e)},400)

class EmreServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        exc = sys.exc_info()[1]
        if isinstance(exc, (ConnectionAbortedError, ConnectionResetError, BrokenPipeError)):
            return
        super().handle_error(request, client_address)

if __name__=='__main__':
    with db(): pass
    try:
        httpd=EmreServer(('127.0.0.1',8765),Handler)
    except OSError as exc:
        print('8765 portu kullanılıyor. Açık Emre penceresini kapatıp tekrar deneyin.',flush=True)
        print('Ayrıntı:',exc,flush=True)
        sys.exit(1)
    if TOKEN:
        BOT.start(TOKEN)
        print('Telegram arka plan yoklaması açık.',flush=True)
    arka_planlari_baslat()
    print('Hatırlatıcı işçisi açık (tarayıcı kapalıyken de bildirir).',flush=True)
    print('EMRE: http://127.0.0.1:8765 | Model:',MODEL,flush=True)
    print('Yalnızca bu bilgisayardan erişim. Durdurmak için Ctrl+C.',flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\nEMRE durduruldu.',flush=True)
    finally:
        httpd.server_close()
