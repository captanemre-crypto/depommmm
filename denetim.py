"""Denetim izi: Emre'nin yaptığı önemli işlemlerin yerel kaydı.

Amaç şeffaflık: hangi araç çağrıldı, hangi dosya yazıldı, hangi bildirim gitti,
hangi ayar değişti. Kayıtlar yalnızca `emre.sqlite3` içinde (`audit` tablosu) tutulur
ve dışarıya gönderilmez; en fazla `AZAMI_KAYIT` satır saklanır (eskiler silinir).

Gizlilik: kayıtlara **anahtar, parola veya tam mesaj metni** yazılmaz; yalnızca kısa
bir özet ve varsa hedef (kişi/araç/dosya adı) yazılır. `gizle()` bu temizliği yapar.
"""
import re
from datetime import datetime

AZAMI_KAYIT = 2000
AZAMI_DETAY = 300
_ANAHTAR_DESENI = re.compile(r'(?i)(sk-[A-Za-z0-9]{8,}|bearer\s+\S+|api[_-]?key\s*[:=]\s*\S+|'
                             r'token\s*[:=]\s*\S+|parola\s*[:=]\s*\S+)')


def gizle(metin, azami=AZAMI_DETAY) -> str:
    """Hassas görünen değerleri maskeler ve metni kısaltır."""
    metin = ' '.join(str(metin or '').split())
    metin = _ANAHTAR_DESENI.sub('[gizli]', metin)
    return metin[:azami]


def kur(conn):
    """`audit` tablosunu oluşturur (idempotent)."""
    conn.execute('''CREATE TABLE IF NOT EXISTS audit (
        id INTEGER PRIMARY KEY, kind TEXT NOT NULL, action TEXT NOT NULL,
        detail TEXT NOT NULL DEFAULT "", status TEXT NOT NULL DEFAULT "ok", created TEXT NOT NULL)''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_audit_created ON audit(created)')


def kaydet(conn, kind, action, detail='', status='ok') -> int:
    """Tek bir denetim kaydı yazar ve kimliğini döndürür."""
    kind = gizle(kind, 40) or 'genel'
    action = gizle(action, 80) or 'işlem'
    detail = gizle(detail)
    status = status if status in ('ok', 'hata', 'onay-bekliyor') else 'ok'
    cur = conn.execute('INSERT INTO audit(kind,action,detail,status,created) VALUES (?,?,?,?,?)',
                       (kind, action, detail, status, datetime.now().isoformat(timespec='seconds')))
    # Eski kayıtları buda: tablo sonsuz büyümesin.
    conn.execute('DELETE FROM audit WHERE id <= (SELECT MAX(id) FROM audit) - ?', (AZAMI_KAYIT,))
    return int(cur.lastrowid or 0)


def son(conn, limit=50, kind=None):
    """Son kayıtları yeniden eskiye döndürür."""
    limit = max(1, min(int(limit or 50), 300))
    if kind:
        satirlar = conn.execute('SELECT id,kind,action,detail,status,created FROM audit '
                                'WHERE kind=? ORDER BY id DESC LIMIT ?', (gizle(kind, 40), limit)).fetchall()
    else:
        satirlar = conn.execute('SELECT id,kind,action,detail,status,created FROM audit '
                                'ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
    adlar = ('id', 'kind', 'action', 'detail', 'status', 'created')
    return [dict(zip(adlar, s)) for s in satirlar]


def temizle(conn) -> int:
    """Tüm denetim kayıtlarını siler; silinen satır sayısını döndürür."""
    sayi = conn.execute('SELECT COUNT(*) FROM audit').fetchone()[0]
    conn.execute('DELETE FROM audit')
    return int(sayi)
