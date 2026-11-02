"""Telegram botu için arka plan yoklayıcı.

Telegram `getUpdates` yalnızca tek bir istemci tarafından okunabilir; bu yüzden
mesajlar sunucu tarafında **uzun yoklama** ile toplanır, SQLite'a yazılır ve
arayüz yalnızca yerel API'den okur. Offset veritabanında tutulduğu için sunucu
yeniden başladığında eski mesajlar yeniden gösterilmez.
"""
import json
import threading
import time
import urllib.error
import urllib.request

API = 'https://api.telegram.org/bot'


class TelegramBot:
    def __init__(self, db_factory):
        self.db = db_factory
        self.token = ''
        self.started_at = None
        self.last_error = ''
        self._thread = None
        self._stop = threading.Event()
        self._lock = threading.Lock()

    # --- durum -------------------------------------------------------------
    def configured(self):
        return bool(self.token)

    def status(self):
        with self._lock:
            return {'configured': self.configured(), 'running': bool(self._thread and self._thread.is_alive()),
                    'started_at': self.started_at, 'last_error': self.last_error}

    # --- yoklama -----------------------------------------------------------
    def start(self, token):
        with self._lock:
            if self.token == token and self._thread and self._thread.is_alive():
                return
            self.token = token
            self._stop.set()
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=3)
            self._stop = threading.Event()
            self._thread = threading.Thread(target=self._loop, name='telegram-poller', daemon=True)
            self.started_at = time.strftime('%Y-%m-%dT%H:%M:%S')
            self.last_error = ''
            self._thread.start()

    def stop(self):
        with self._lock:
            self._stop.set()
            thread, self._thread = self._thread, None
            self.token = ''
        if thread and thread.is_alive():
            thread.join(timeout=3)

    def _loop(self):
        while not self._stop.is_set():
            try:
                self._poll_once()
            except urllib.error.HTTPError as exc:
                # 401/404: anahtar geçersiz; döngüyü yormamak için bekle.
                with self._lock:
                    self.last_error = f'Telegram isteği başarısız (HTTP {exc.code}).'
                if exc.code in (401, 404):
                    break
                self._stop.wait(10)
            except Exception:
                with self._lock:
                    self.last_error = 'Telegram bağlantısı kurulamadı.'
                self._stop.wait(15)

    def _poll_once(self):
        token = self.token
        if not token:
            return
        offset = self._offset()
        params = {'timeout': 25, 'limit': 30, 'allowed_updates': ['message']}
        if offset is not None:
            params['offset'] = offset
        url = API + token + '/getUpdates'
        data = json.dumps(params).encode()
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=40) as res:
            payload = json.load(res)
        if not payload.get('ok'):
            raise ValueError('Telegram isteği başarısız.')
        for update in payload.get('result', []):
            self._store_update(update)
        if not payload.get('result'):
            self._stop.wait(1)

    # --- depolama ----------------------------------------------------------
    def _offset(self):
        with self.db() as conn:
            row = conn.execute("SELECT value FROM telegram_state WHERE key='offset'").fetchone()
        return int(row[0]) if row and str(row[0]).isdigit() else None

    def _store_update(self, update):
        uid = update.get('update_id')
        message = update.get('message') or {}
        text = message.get('text')
        with self.db() as conn:
            if isinstance(uid, int):
                conn.execute("INSERT INTO telegram_state(key,value) VALUES('offset',?) "
                             "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(uid + 1),))
            if not text:
                return
            chat = message.get('chat') or {}
            try:
                conn.execute('INSERT OR IGNORE INTO telegram_messages(update_id,chat_id,sender,text,date,read) '
                             'VALUES (?,?,?,?,?,0)',
                             (uid, chat.get('id'), chat.get('first_name') or chat.get('title') or 'Kullanıcı',
                              text[:4000], message.get('date')))
            except Exception:
                pass

    # --- okuma / gönderme --------------------------------------------------
    def messages(self, limit=50):
        with self.db() as conn:
            rows = conn.execute('SELECT id,chat_id,sender,text,date,read FROM telegram_messages '
                                'ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
            unread = conn.execute('SELECT COUNT(*) FROM telegram_messages WHERE read=0').fetchone()[0]
        items = [{'id': r[0], 'chat_id': r[1], 'from': r[2], 'text': r[3], 'date': r[4], 'read': bool(r[5])}
                 for r in rows]
        return {'messages': items, 'unread': unread}

    def mark_read(self):
        with self.db() as conn:
            conn.execute('UPDATE telegram_messages SET read=1 WHERE read=0')

    def send(self, chat_id, text):
        token = self.token
        if not token:
            raise ValueError('Telegram bot anahtarı ayarlanmamış.')
        payload = json.dumps({'chat_id': chat_id, 'text': text}).encode()
        req = urllib.request.Request(API + token + '/sendMessage', data=payload,
                                     headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=20) as res:
            result = json.load(res)
        if not result.get('ok'):
            raise ValueError('Telegram mesajı gönderemedi.')
        return True
