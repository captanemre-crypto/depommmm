"""EMRE local server: standard-library only. Run on Windows: py server.py"""
import json, os, sqlite3, urllib.request, urllib.error, threading, time, webbrowser, secrets, re, subprocess, sys, tempfile, base64
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, quote
from datetime import datetime
from pathlib import Path
import arena_bridge
import ledger_tools
import ses_baglanti
import tts_piper_bridge

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'emre.sqlite3'
OLLAMA = 'http://127.0.0.1:11434'
OPENJARVIS = 'http://127.0.0.1:8766'
MODEL = os.getenv('EMRE_MODEL', 'qwen2.5-coder:7b')
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
KEY = secrets.token_urlsafe(32)
SYSTEM = 'Adın Emre. Türkçe konuşan yardımcı bir asistansın. Kısa, doğal ve samimi Türkçe konuş; kullanıcıya sen diye hitap et. Yalnızca sorulan sorunun cevabını ver. Cevaptan sonra ek açıklama, öneri, teklif veya takip sorusu ekleme. Her mesajın sonunda soru sorma; özellikle size nasıl yardımcı olabilirim, nasıl yardımcı olabilirim veya başka bir şey var mı gibi kalıpları tekrar etme. Kullanıcının adı bilinmiyor; ona Emre diye seslenme, Emre senin adın. Mikrofonu doğrudan duyduğunu iddia etme; yalnızca sana iletilen metni okuyorsun. Başka dilde gereksiz sözcük kullanma. Doğrudan istenen yanıtı ver. Yapmadığın işlemleri yapmış gibi söyleme. Kullanıcının izni olmadan mesaj gönderme, program çalıştırma veya dosya değiştirme.'

def db():
    conn = sqlite3.connect(DB, timeout=10)
    conn.execute('CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY, text TEXT NOT NULL, due TEXT NOT NULL, done INTEGER DEFAULT 0)')
    conn.execute('CREATE TABLE IF NOT EXISTS ledger (id INTEGER PRIMARY KEY, person TEXT NOT NULL, kind TEXT NOT NULL, amount INTEGER NOT NULL, note TEXT NOT NULL DEFAULT \"\", due TEXT, created TEXT NOT NULL)')
    conn.execute('CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY, name TEXT NOT NULL COLLATE NOCASE UNIQUE, note TEXT NOT NULL DEFAULT \"\")')
    return conn

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
        self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
    def valid(self):
        origin=self.headers.get('Origin','')
        return self.headers.get('X-Emre-Token') == KEY and (not origin or origin in ('http://127.0.0.1:8765','http://localhost:8765'))
    def body(self):
        n=int(self.headers.get('Content-Length','0'))
        limit=8_500_000 if urlparse(self.path).path=='/api/speech/transcribe' else 100000
        if n>limit: raise ValueError('İstek çok büyük.')
        return json.loads(self.rfile.read(n) or b'{}')
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/':
            html=(ROOT/'index.html').read_text(encoding='utf-8').replace('</head>', '<meta name="emre-token" content="'+KEY+'"></head>', 1).encode()
            self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(html))); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(html); return
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
            if path=='/api/speech/status': return self.out({'installed':(ROOT/'.venv-ses'/'Scripts'/'python.exe').is_file()})
            if path=='/api/openjarvis/status':
                try:
                    health=request_json(OPENJARVIS+'/health',timeout=3)
                    return self.out({'online':True,'health':health})
                except Exception: return self.out({'online':False})
            if path=='/api/arena/status': return self.out(arena_bridge.snapshot())
            if path=='/api/status':
                try: models=request_json(OLLAMA+'/api/tags',timeout=2); ollama=True
                except Exception: models={'models':[]}; ollama=False
                return self.out({'ollama':ollama,'model':MODEL,'models':[m['name'] for m in models.get('models',[])], 'telegram_configured':bool(TOKEN), 'version':'2026-10-29-fix2'})
            if path=='/api/accounts':
                with db() as c: rows=c.execute('SELECT name,note FROM accounts ORDER BY name').fetchall()
                return self.out({'accounts':[{'name':r[0],'note':r[1]} for r in rows]})
            if path=='/api/ledger':
                with db() as c: rows=c.execute('SELECT id,person,kind,amount,note,due,created FROM ledger ORDER BY id DESC').fetchall()
                return self.out({'entries':[{'id':r[0],'person':r[1],'kind':r[2],'amount':r[3],'note':r[4],'due':r[5],'created':r[6]} for r in rows]})
            if path=='/api/reminders':
                with db() as c: rows=c.execute('SELECT id,text,due,done FROM reminders ORDER BY due').fetchall()
                return self.out({'reminders':[{'id':r[0],'text':r[1],'due':r[2],'done':bool(r[3])} for r in rows]})
            if path=='/api/telegram/updates':
                result=telegram('getUpdates',{'timeout':0,'limit':30,'allowed_updates':['message']})
                if not result.get('ok'): raise ValueError('Telegram isteği başarısız.')
                messages=[]
                for u in result.get('result',[]):
                    m=u.get('message',{}); chat=m.get('chat',{})
                    if m.get('text'): messages.append({'chat_id':chat.get('id'),'from':chat.get('first_name','Kullanıcı'),'text':m['text']})
                return self.out({'messages':messages})
            return self.out({'error':'Bulunamadı'},404)
        except Exception as e: return self.out({'error':str(e)},400)
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
                text=str(data.get('text','')).strip();voice=str(data.get('voice','')).strip()
                if not text or len(text)>1500 or not voice or len(voice)>200: raise ValueError('Ses veya metin geçersiz.')
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
                text=ses_baglanti.transcribe(data.get('audio'))
                return self.out({'text':text})
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
                app=allowed.get(data.get('app'))
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
                arena_bridge.send(str(data.get('question','')).strip())
                return self.out({'ok':True})
            if path=='/api/telegram/connect':
                candidate=str(data.get('token','')).strip()
                if not re.fullmatch(r'\d{5,15}:[A-Za-z0-9_-]{20,100}',candidate): raise ValueError('Bot anahtarı biçimi geçersiz.')
                try:
                    info=request_json('https://api.telegram.org/bot'+candidate+'/getMe', timeout=15)
                    if not info.get('ok') or not info.get('result',{}).get('is_bot'): raise ValueError()
                except Exception: raise ValueError('Bot doğrulanamadı. Anahtarı ve internet bağlantısını kontrol et.')
                TOKEN=candidate
                return self.out({'ok':True,'username':info['result'].get('username','')})
            if path=='/api/telegram/disconnect':
                TOKEN=''
                return self.out({'ok':True})
            if path=='/api/chat':
                messages=data.get('messages',[])[-12:]
                clean=[{'role':m['role'],'content':str(m['content'])[:6000]} for m in messages if m.get('role') in ('user','assistant') and isinstance(m.get('content'),str)]
                if not clean: raise ValueError('Mesaj boş.')
                selected=str(data.get('model') or MODEL).strip()
                if len(selected)>200: raise ValueError('Model adı çok uzun.')
                installed={m.get('name') for m in request_json(OLLAMA+'/api/tags',timeout=5).get('models',[])}
                if selected not in installed and selected+':latest' not in installed: raise ValueError('Seçilen model Ollama üzerinde kurulu değil.')
                # Qwen3 supports both the API flag and an explicit no-thinking directive.
                if selected.lower().startswith('qwen3'):
                    clean[-1]['content'] += '\n/no_think'
                last_user = next((m['content'] for m in reversed(clean) if m['role']=='user'), '')
                direct=ledger_tools.create_account_from_text(last_user,db)
                if direct is not None: return self.out({'reply':direct})
                direct=ledger_tools.direct_ledger_action(last_user,db)
                if direct is not None: return self.out({'reply':direct})
                system=SYSTEM+' Yerel tarih ve saat: '+datetime.now().strftime('%Y-%m-%d %H:%M')+'. Kullanıcı defter kaydı veya bakiyesi isterse uygun aracı kullan. Kayıt belirsizse soru sor. Gerçek ödeme yapma. Hatırlatıcı için açık tarih ve saat gerekli. Deftere kayıt, tahsilat ve ödeme ekleme için ayrıca onay sorma.'
                backend=data.get('backend','ollama')
                if backend=='openjarvis':
                    if selected not in ('emre-cpu','emre-cpu:latest'): return self.out({'error':'OpenJarvis için önce emre-cpu modelini oluştur ve Ayarlar’dan seç.'},400)
                    # Client-supplied tools keep tool execution under Emre's validation.
                    result=request_json(OPENJARVIS+'/v1/chat/completions',{'model':selected,'messages':[{'role':'system','content':system}]+clean,'tools':ledger_tools.TOOLS,'stream':False,'max_tokens':400},timeout=300)
                    choices=result.get('choices') or []
                    if not choices: raise ValueError('OpenJarvis yanıt döndürmedi.')
                    msg=choices[0].get('message',{})
                elif backend=='ollama':
                    result=request_json(OLLAMA+'/api/chat',{'model':selected,'messages':[{'role':'system','content':system}]+clean,'tools':ledger_tools.TOOLS,'stream':False,'think':False,'options':{'num_ctx':4096,'num_predict':400,'num_gpu':0}}, timeout=300)
                    msg=result.get('message',{})
                else: raise ValueError('Bilinmeyen yapay zekâ bağlantısı.')
                calls=msg.get('tool_calls') or []
                if calls:
                    if len(calls)!=1: return self.out({'reply':'Bir seferde tek defter işlemi yapabiliyorum; lütfen işlemleri ayrı ayrı söyle.'})
                    fn=calls[0].get('function',{})
                    try: reply=ledger_tools.execute(fn.get('name'),fn.get('arguments',{}),db,last_user)
                    except (ValueError,TypeError,KeyError) as err: reply='Kayıt yapılmadı: '+str(err)
                    return self.out({'reply':reply})
                raw_content=msg.get('content','') or ''
                # Never read a model-generated tool JSON aloud or mistake it for a successful action.
                try: raw_json=json.loads(raw_content.strip())
                except (ValueError,TypeError): raw_json=None
                if (isinstance(raw_json,dict) and ('arguments' in raw_json or 'tool_calls' in raw_json)) or re.search(r'["\'](?:arguments|tool_calls)["\']\s*:', raw_content):
                    return self.out({'reply':'İşlemi anlayamadım; kayıt oluşturulmadı. Hesap adını ve yapmak istediğin işlemi tekrar söyle.'})
                reply=clean_reply(raw_content)
                if re.search(r'(?i)kay[ıi]t (?:edildi|oluşturuldu)|kaydetti[mn]|deftere (?:ekledim|işledim)|hatırlatıcı (?:oluşturdum|ayarladım)|(?:alacak|verecek|hesap|defter|ödeme|tahsilat).{0,120}(?:gerçekleştirdim|ekledim|oluşturdum|sildim|kaydedildi|yaptım)',reply):
                    reply='Bu işlem için deftere kayıt yapılmadı. Kişiyi, tutarı ve işlem türünü açıkça belirt.'
                return self.out({'reply':reply})
            if path=='/api/accounts/delete':
                if data.get('confirmed') is not True: raise ValueError('Silme onayı gerekli.')
                name=str(data.get('name','')).strip()
                if not name: raise ValueError('Hesap adı gerekli.')
                with db() as c:
                    a_ids=[r[0] for r in c.execute('SELECT id,name FROM accounts').fetchall() if r[1].strip().casefold()==name.casefold()]
                    l_ids=[r[0] for r in c.execute('SELECT id,person FROM ledger').fetchall() if r[1].strip().casefold()==name.casefold()]
                    if not a_ids and not l_ids: raise ValueError('Hesap bulunamadı.')
                    c.executemany('DELETE FROM accounts WHERE id=?',[(i,) for i in a_ids])
                    c.executemany('DELETE FROM ledger WHERE id=?',[(i,) for i in l_ids])
                return self.out({'ok':True,'deleted_entries':len(l_ids)})
            if path=='/api/accounts':
                name=str(data.get('name','')).strip()[:100]; note=str(data.get('note','')).strip()[:300]
                if not name: raise ValueError('Hesap adı gerekli.')
                with db() as c: c.execute('INSERT INTO accounts(name,note) VALUES (?,?)',(name,note))
                return self.out({'ok':True})
            if path=='/api/ledger':
                person=str(data.get('person','')).strip()[:100]; kind=data.get('kind'); amount=data.get('amount'); note=str(data.get('note','')).strip()[:300]; due=str(data.get('due','')).strip()
                if not person or kind not in ('receivable','payable','received','paid') or type(amount) is not int or not 0 < amount <= 100000000000: raise ValueError('Kişi, işlem türü ve geçerli tutar gerekli.')
                if due: datetime.fromisoformat(due)
                if data.get('remind') and (not due or kind not in ('receivable','payable')): raise ValueError('Hatırlatıcı için alacak/verecek ve tarih gerekli.')
                with db() as c:
                    c.execute('INSERT INTO ledger(person,kind,amount,note,due,created) VALUES (?,?,?,?,?,?)',(person,kind,amount,note,due or None,datetime.now().isoformat(timespec='seconds')))
                    if data.get('remind'):
                        label='Alacak' if kind=='receivable' else 'Verecek'
                        c.execute('INSERT INTO reminders(text,due) VALUES (?,?)',(f'{label}: {person} — {amount/100:.2f} TL',due))
                return self.out({'ok':True})
            if path=='/api/ledger/delete':
                if data.get('confirmed') is not True: raise ValueError('Silme onayı gerekli.')
                with db() as c: c.execute('DELETE FROM ledger WHERE id=?',(int(data['id']),))
                return self.out({'ok':True})
            if path=='/api/reminders':
                text=str(data.get('text','')).strip()[:300]; due=str(data.get('due',''))
                if not text: raise ValueError('Hatırlatıcı metni gerekli.')
                datetime.fromisoformat(due)
                with db() as c: c.execute('INSERT INTO reminders(text,due) VALUES (?,?)',(text,due))
                return self.out({'ok':True})
            if path=='/api/reminders/done':
                with db() as c: c.execute('UPDATE reminders SET done=1 WHERE id=?',(int(data['id']),))
                return self.out({'ok':True})
            if path=='/api/telegram/send':
                if data.get('confirmed') is not True: raise ValueError('Gönderme onayı gerekli.')
                chat_id=int(data['chat_id']); text=str(data.get('text','')).strip()[:4096]
                if not text: raise ValueError('Mesaj boş.')
                result=telegram('sendMessage',{'chat_id':chat_id,'text':text})
                if not result.get('ok'): raise ValueError('Telegram mesajı gönderemedi.')
                return self.out({'ok':True})
            return self.out({'error':'Bulunamadı'},404)
        except urllib.error.HTTPError as e:
            try: message=json.loads(e.read()).get('error','Servis hatası')
            except Exception: message='Servis hatası'
            return self.out({'error':str(message)},502)
        except Exception as e: return self.out({'error':str(e)},400)

class EmreServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        exc = sys.exc_info()[1]
        if isinstance(exc, (ConnectionAbortedError, ConnectionResetError, BrokenPipeError)):
            return
        super().handle_error(request, client_address)

if __name__=='__main__':
    with db(): pass
    print('EMRE: http://127.0.0.1:8765 | Model:',MODEL,flush=True)
    print('Yalnızca bu bilgisayardan erişim. Durdurmak için Ctrl+C.',flush=True)
    EmreServer(('127.0.0.1',8765),Handler).serve_forever()
