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
import time
import urllib.error
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import arena_bridge
import hatirlatici
import ledger_tools
import saglayici
import ses_baglanti
import telegram_bot
import tts_piper_bridge

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'emre.sqlite3'
OLLAMA = 'http://127.0.0.1:11434'
OPENJARVIS = 'http://127.0.0.1:8766'
MODEL = os.getenv('EMRE_MODEL', 'qwen2.5-coder:7b')
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
KEY = secrets.token_urlsafe(32)
VERSION = '2026-11-02.6'
SYSTEM = 'Adın Emre. Türkçe konuşan yardımcı bir asistansın. Kısa, doğal ve samimi Türkçe konuş; kullanıcıya sen diye hitap et. Yalnızca sorulan sorunun cevabını ver. Cevaptan sonra ek açıklama, öneri, teklif veya takip sorusu ekleme. Her mesajın sonunda soru sorma; özellikle size nasıl yardımcı olabilirim, nasıl yardımcı olabilirim veya başka bir şey var mı gibi kalıpları tekrar etme. Kullanıcının adı bilinmiyor; ona Emre diye seslenme, Emre senin adın. Mikrofonu doğrudan duyduğunu iddia etme; yalnızca sana iletilen metni okuyorsun. Başka dilde gereksiz sözcük kullanma. Doğrudan istenen yanıtı ver. Yapmadığın işlemleri yapmış gibi söyleme. Kullanıcının izni olmadan mesaj gönderme, program çalıştırma veya dosya değiştirme.'

_INITIALIZED = set()


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
        CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session, id);
        CREATE INDEX IF NOT EXISTS idx_ledger_person ON ledger(person);
    """)
    # Eski veritabanları için denetim izi kolonları (A6)
    columns = {row[1] for row in conn.execute('PRAGMA table_info(ledger)')}
    if 'source' not in columns:
        conn.execute('ALTER TABLE ledger ADD COLUMN source TEXT')
    if 'raw_text' not in columns:
        conn.execute('ALTER TABLE ledger ADD COLUMN raw_text TEXT')
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
                return self.out({'ok':True,'status':SAG.durum()})
            if path=='/api/provider/disconnect':
                if data.get('confirmed') is not True: raise ValueError('Bağlantıyı kesmek için onay gerekli.')
                SAG.sil()
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
                def yanitla(text):
                    if session: store_message(session,'assistant',text)
                    return self.out({'reply':text})
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
                system=SYSTEM+' Yerel tarih ve saat: '+datetime.now().strftime('%Y-%m-%d %H:%M')+'. Kullanıcı defter kaydı veya bakiyesi isterse uygun aracı kullan. Kayıt belirsizse soru sor. Gerçek ödeme yapma. Hatırlatıcı için açık tarih ve saat gerekli. Deftere kayıt, tahsilat ve ödeme ekleme için ayrıca onay sorma.'
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
                        raise ValueError('Ücretsiz API ('+SAG.yukle()['base_url']+' · '+str(api_model or SAG.yukle()['model'])+'): '+str(hata))
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
                    return yanitla(reply)
                raw_content=msg.get('content','') or ''
                # Never read a model-generated tool JSON aloud or mistake it for a successful action.
                try: raw_json=json.loads(raw_content.strip())
                except (ValueError,TypeError): raw_json=None
                if (isinstance(raw_json,dict) and ('arguments' in raw_json or 'tool_calls' in raw_json)) or re.search(r'["\'](?:arguments|tool_calls)["\']\s*:', raw_content):
                    return yanitla('İşlemi anlayamadım; kayıt oluşturulmadı. Hesap adını ve yapmak istediğin işlemi tekrar söyle.')
                reply=clean_reply(raw_content)
                if re.search(r'(?i)kay[ıi]t (?:edildi|oluşturuldu)|kaydetti[mn]|deftere (?:ekledim|işledim)|hatırlatıcı (?:oluşturdum|ayarladım)|(?:alacak|verecek|hesap|defter|ödeme|tahsilat).{0,120}(?:gerçekleştirdim|ekledim|oluşturdum|sildim|kaydedildi|yaptım)',reply):
                    reply='Bu işlem için deftere kayıt yapılmadı. Kişiyi, tutarı ve işlem türünü açıkça belirt.'
                return yanitla(reply)
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
                return self.out({'ok':True})
            if path=='/api/reminders':
                text=text_field(data,'text',300,required=True,label='Hatırlatıcı metni'); due=text_field(data,'due',40,required=True,label='Tarih')
                try: datetime.fromisoformat(due)
                except ValueError: raise ValueError('Tarih biçimi geçersiz; YYYY-AA-GG SS:DD kullan.')
                with db() as c: c.execute('INSERT INTO reminders(text,due) VALUES (?,?)',(text,due))
                return self.out({'ok':True})
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
    print('EMRE: http://127.0.0.1:8765 | Model:',MODEL,flush=True)
    print('Yalnızca bu bilgisayardan erişim. Durdurmak için Ctrl+C.',flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\nEMRE durduruldu.',flush=True)
    finally:
        httpd.server_close()
