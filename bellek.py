"""Kalıcı kişisel bellek (kişi, proje, tercih) + basit bilgi grafiği.

Tasarım
- Hepsi **yerelde** SQLite'ta: `memories` (kayıtlar) ve `baglantilar` (ilişkiler).
- Arama Türkçe karakterlere duyarlı değil: `ahmet` ↔ `Ahmet` ↔ `AHMET`.
- Model çağrısı öncesi en ilgili birkaç kayıt sistem istemine eklenir; bu sayede
  "geçen hafta Ahmet'le ne konuştuk?" gibi sorular bağlam kazanır.
- Otomatik kayıt yalnızca **açık** kalıplarda yapılır ("hatırla", "not al",
  "benim adım", "X'in telefonu ...") — modelin tahminleri değil.
"""
import json
import re
import unicodedata
from datetime import datetime, timedelta

AZAMI_KAYIT = 5000
AZAMI_UZUNLUK = 500
YEDEK_SURUM = 1
AZAMI_ICEAKTARMA = 5000
VARSAYILAN_ARSIV_GUN = 180


def _sade(metin):
    """Türkçe küçük harf + aksan sadeleştirme (arama için)."""
    metin = str(metin or '').replace('İ', 'i').replace('I', 'ı').lower()
    metin = unicodedata.normalize('NFKD', metin)
    metin = ''.join(c for c in metin if not unicodedata.combining(c))
    return metin.replace('ı', 'i').replace('ş', 's').replace('ğ', 'g').replace('ç', 'c').replace('ö', 'o').replace('ü', 'u')


def kelimeler(metin):
    return [k for k in re.split(r'[^0-9a-z]+', _sade(metin)) if len(k) > 1]


def kur(c):
    c.executescript("""
    CREATE TABLE IF NOT EXISTS memories(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kind TEXT NOT NULL DEFAULT 'not',
        subject TEXT NOT NULL DEFAULT '',
        text TEXT NOT NULL,
        arama TEXT NOT NULL DEFAULT '',
        source TEXT NOT NULL DEFAULT '',
        created TEXT NOT NULL,
        hits INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS baglantilar(
        kaynak INTEGER NOT NULL,
        hedef INTEGER NOT NULL,
        iliski TEXT NOT NULL DEFAULT 'ilgili'
    );
    CREATE INDEX IF NOT EXISTS memories_subject ON memories(subject);
    """)
    # Eski veritabanları için: arama sütunu yoksa ekle ve doldur.
    kolonlar = {r[1] for r in c.execute('PRAGMA table_info(memories)')}
    if 'arama' not in kolonlar:
        c.execute("ALTER TABLE memories ADD COLUMN arama TEXT NOT NULL DEFAULT ''")
        for kid, konu, metin in c.execute('SELECT id,subject,text FROM memories').fetchall():
            c.execute('UPDATE memories SET arama=? WHERE id=?', (_sade(f'{konu} {metin}'), kid))


def ekle(c, text, kind='not', subject='', source=''):
    text = ' '.join(str(text or '').split())[:AZAMI_UZUNLUK]
    if not text:
        raise ValueError('Bellek kaydı boş olamaz.')
    kind = str(kind or 'not').strip().lower()[:20] or 'not'
    subject = ' '.join(str(subject or '').split())[:80]
    sayi = c.execute('SELECT COUNT(*) FROM memories').fetchone()[0]
    if sayi >= AZAMI_KAYIT:
        raise ValueError('Bellek dolu; önce eski kayıtları sil.')
    cur = c.execute('INSERT INTO memories(kind,subject,text,arama,source,created) VALUES (?,?,?,?,?,?)',
                    (kind, subject, text, _sade(f'{subject} {text}'), str(source or '')[:40],
                     datetime.now().isoformat(timespec='seconds')))
    return cur.lastrowid


def ara(c, sorgu='', limit=8):
    """Anahtar kelime eşleşmesi + güncellik sırası."""
    limit = max(1, min(int(limit or 8), 50))
    if not str(sorgu or '').strip():
        return [dict(zip(('id', 'kind', 'subject', 'text', 'created'), r))
                for r in c.execute('SELECT id,kind,subject,text,created FROM memories ORDER BY id DESC LIMIT ?', (limit,))]
    anahtarlar = kelimeler(sorgu)[:8]
    if not anahtarlar:
        return []
    kosul = ' OR '.join(['arama LIKE ?' for _ in anahtarlar])
    params = [f'%{k}%' for k in anahtarlar]
    satirlar = c.execute(f'SELECT id,kind,subject,text,created FROM memories WHERE {kosul} ORDER BY id DESC LIMIT 200', params).fetchall()
    puanli = []
    for satir in satirlar:
        metin = _sade(f'{satir[2]} {satir[3]}')
        puan = sum(1 for k in anahtarlar if k in metin)
        if puan:
            puanli.append((puan, satir[0], satir))
    puanli.sort(key=lambda x: (-x[0], -x[1]))
    return [dict(zip(('id', 'kind', 'subject', 'text', 'created'), s)) for _, _, s in puanli[:limit]]


def baglam(c, sorgu, limit=5):
    """Sistem istemine eklenecek kısa bellek bloğu (yoksa boş metin)."""
    kayitlar = ara(c, sorgu, limit=limit)
    if not kayitlar:
        return ''
    satirlar = []
    for k in kayitlar:
        konu = f'{k["subject"]}: ' if k['subject'] else ''
        satirlar.append(f'- {konu}{k["text"]}')
    return 'Bilinen kişisel bilgiler (kullanıcı daha önce söyledi):\n' + '\n'.join(satirlar)


def sil(c, kayit_id):
    cur = c.execute('DELETE FROM memories WHERE id=?', (int(kayit_id),))
    c.execute('DELETE FROM baglantilar WHERE kaynak=? OR hedef=?', (int(kayit_id), int(kayit_id)))
    return cur.rowcount


def hepsi(c, limit=100):
    return [dict(zip(('id', 'kind', 'subject', 'text', 'created'), r)) for r in
            c.execute('SELECT id,kind,subject,text,created FROM memories ORDER BY id DESC LIMIT ?', (min(int(limit), 500),))]


# --- otomatik çıkarım -------------------------------------------------------
_ONEK = re.compile(r'^(?:lütfen\s+)?(?:hatırla|unutma|not al|not düş|kaydet|aklında tut)\s*[:,]?\s*(?P<metin>.+)$', re.I)
_ADIM = re.compile(r'\bbenim adım\s+(?P<ad>[A-ZÇĞİÖŞÜ][\wçğıöşü]{1,20})\b')
_TELEFON = re.compile(r'\b(?P<kisi>[A-ZÇĞİÖŞÜ][\wçğıöşü]{1,20})(?:[\'’]?[ıiuü]n)?\s+telefonu\s+(?P<no>0?\d{3}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2})\b')
_SEV = re.compile(r'\bben\s+(?P<nesne>[\wçğıöşü ]{2,40})\s+sev(?:iyorum|erim)\b', re.I)


def cikar(metin):
    """Metinden kaydedilmeye değer açık bilgiler çıkarır: [(kind, subject, text)]"""
    metin = ' '.join(str(metin or '').split())
    if not metin or len(metin) > 2000:
        return []
    sonuc = []
    m = _ONEK.match(metin)
    if m:
        govde = m.group('metin').strip(' .!')
        if govde:
            sonuc.append(('not', '', govde[:AZAMI_UZUNLUK]))
    m = _ADIM.search(metin)
    if m:
        sonuc.append(('kimlik', 'kullanıcı', f'adı {m.group("ad")}'))
    m = _TELEFON.search(metin)
    if m:
        sonuc.append(('kişi', m.group('kisi'), f'telefonu {m.group("no")}'))
    m = _SEV.search(metin)
    if m:
        nesne = m.group('nesne').strip()
        if 2 < len(nesne) < 40:
            sonuc.append(('tercih', '', f'{nesne} seviyor'))
    # Aynı kayıt birden çok kez üretilmesin.
    tekil = []
    for s in sonuc:
        if s not in tekil:
            tekil.append(s)
    return tekil


def kaydet_cikarimlar(c, metin, source='sohbet'):
    yazilan = []
    for kind, subject, text in cikar(metin):
        ayni = c.execute('SELECT id FROM memories WHERE lower(text)=lower(?)', (text,)).fetchone()
        if ayni:
            c.execute('UPDATE memories SET hits=hits+1 WHERE id=?', (ayni[0],))
            continue
        ekle(c, text, kind=kind, subject=subject, source=source)
        yazilan.append(text)
    return yazilan


# --- yedekleme, geri yükleme, unutma, yaşlandırma ---------------------------
def disa_aktar(c):
    """Belleği JSON'a uygun bir sözlüğe çevirir (yedek dosyası)."""
    kayitlar = [dict(zip(('id', 'kind', 'subject', 'text', 'source', 'created', 'hits'), r)) for r in
                c.execute('SELECT id,kind,subject,text,source,created,hits FROM memories ORDER BY id')]
    baglantilar = [dict(zip(('kaynak', 'hedef', 'iliski'), r)) for r in
                   c.execute('SELECT kaynak,hedef,iliski FROM baglantilar')]
    return {'surum': YEDEK_SURUM, 'tarih': datetime.now().isoformat(timespec='seconds'),
            'kayitlar': kayitlar, 'baglantilar': baglantilar}


def ice_aktar(c, veri, mod='birlestir'):
    """Yedekten geri yükler. mod='birlestir' (varsayılan) veya 'degistir'."""
    if not isinstance(veri, dict):
        raise ValueError('Yedek biçimi geçersiz.')
    if int(veri.get('surum') or 0) > YEDEK_SURUM:
        raise ValueError('Bu yedek daha yeni bir Emre sürümünden; güncelleme gerekli.')
    kayitlar = veri.get('kayitlar')
    if not isinstance(kayitlar, list):
        raise ValueError('Yedekte “kayitlar” listesi yok.')
    if len(kayitlar) > AZAMI_ICEAKTARMA:
        raise ValueError(f'Yedek çok büyük (en fazla {AZAMI_ICEAKTARMA} kayıt).')
    if mod not in ('birlestir', 'degistir'):
        raise ValueError('Mod “birlestir” veya “degistir” olmalı.')
    if mod == 'degistir':
        c.execute('DELETE FROM memories')
        c.execute('DELETE FROM baglantilar')
    eklenen, atlanan = 0, 0
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            atlanan += 1
            continue
        metin = ' '.join(str(kayit.get('text') or '').split())[:AZAMI_UZUNLUK]
        if not metin:
            atlanan += 1
            continue
        ayni = c.execute('SELECT id FROM memories WHERE lower(text)=lower(?)', (metin,)).fetchone()
        if ayni:
            atlanan += 1
            continue
        tur = str(kayit.get('kind') or 'not')[:20]
        konu = str(kayit.get('subject') or '')[:60]
        c.execute('INSERT INTO memories(kind,subject,text,arama,source,created,hits) '
                  'VALUES (?,?,?,?,?,?,?)',
                  (tur, konu, metin, _sade(f'{konu} {metin}'), 'yedek',
                   str(kayit.get('created') or datetime.now().isoformat(timespec='seconds'))[:19],
                   int(kayit.get('hits') or 0)))
        eklenen += 1
    return {'eklenen': eklenen, 'atlanan': atlanan}


def unut(c, sorgu):
    """Eşleşen kayıtları siler: {'silinen': n, 'kayitlar': [...]} (geri bildirim için)."""
    sorgu = ' '.join(str(sorgu or '').split())[:200]
    if len(sorgu) < 2:
        raise ValueError('Unutulacak bilgi en az iki karakter olmalı.')
    kayitlar = ara(c, sorgu, limit=AZAMI_ICEAKTARMA)
    if not kayitlar:
        return {'silinen': 0, 'kayitlar': []}
    for kayit in kayitlar:
        sil(c, kayit['id'])
    return {'silinen': len(kayitlar), 'kayitlar': kayitlar}


def arsivle(c, gun=VARSAYILAN_ARSIV_GUN):
    """Hiç kullanılmamış ve `gun` günden eski kayıtları siler (yaşlandırma)."""
    gun = max(7, min(int(gun or VARSAYILAN_ARSIV_GUN), 3650))
    esik = (datetime.now() - timedelta(days=gun)).isoformat(timespec='seconds')
    cur = c.execute('DELETE FROM memories WHERE hits=0 AND created < ?', (esik,))
    return {'silinen': max(cur.rowcount, 0), 'gun': gun}


def yedek_json(c):
    """Yedeği okunabilir JSON metni olarak döndürür."""
    return json.dumps(disa_aktar(c), ensure_ascii=False, indent=2)
