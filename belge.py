"""Belge okuma: yerel dosyalardan metin çıkarır ve belgeye soru sorar.

Desteklenen biçimler (hepsi **standart kütüphane** ile, ek paket gerekmez):

| Biçim | Yöntem |
| --- | --- |
| `.txt`, `.md`, `.csv`, `.json`, `.log` | düz metin (UTF-8, gerekirse cp1254/latin-1) |
| `.html`, `.htm` | etiketler temizlenir |
| `.docx` | ZIP + `word/document.xml` (paragraflar) |
| `.pdf` | metin akışları (`BT…ET`, `Tj`/`TJ`) + `FlateDecode` |

Güvenlik ve sınırlar:

- Dosya yalnızca kullanıcının verdiği **yerel yol**tan veya base64 içerikten okunur; ağdan indirme yok.
- En fazla 20 MB dosya, 2000 sayfa/parça, parça başına 900 karakter.
- Metin `docs` / `doc_chunks` tablolarında saklanır; arama Türkçe aksan duyarsızdır.
- PDF çıkarma **basittir**: taranmış (görüntü) PDF'lerde metin bulunmaz; bu durumda açık uyarı döner.
"""
import base64
import io
import json
import re
import unicodedata
import zipfile
import zlib
from html.parser import HTMLParser
from pathlib import Path

AZAMI_BAYT = 20 * 1024 * 1024
AZAMI_SAYFA = 2000
Parca_BOY = 900
Parca_BINIS = 150
DESTEKLENEN = ('.txt', '.md', '.markdown', '.csv', '.json', '.log', '.html', '.htm', '.docx', '.pdf')


def _sade(metin):
    metin = str(metin or '').replace('İ', 'i').replace('I', 'ı').lower()
    metin = unicodedata.normalize('NFKD', metin)
    metin = ''.join(c for c in metin if not unicodedata.combining(c))
    return (metin.replace('ı', 'i').replace('ş', 's').replace('ğ', 'g')
            .replace('ç', 'c').replace('ö', 'o').replace('ü', 'u'))


def kur(c):
    c.executescript("""
    CREATE TABLE IF NOT EXISTS docs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        kind TEXT NOT NULL DEFAULT '',
        pages INTEGER NOT NULL DEFAULT 0,
        chars INTEGER NOT NULL DEFAULT 0,
        created TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS doc_chunks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_id INTEGER NOT NULL,
        sayfa INTEGER NOT NULL DEFAULT 0,
        metin TEXT NOT NULL,
        arama TEXT NOT NULL DEFAULT ''
    );
    CREATE INDEX IF NOT EXISTS doc_chunks_doc ON doc_chunks(doc_id);
    """)


# --- metin çıkarma ----------------------------------------------------------
class _MetinToplayici(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parcalar = []
        self._atla = False

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self._atla = True
        elif tag in ('p', 'br', 'div', 'li', 'tr', 'h1', 'h2', 'h3', 'h4'):
            self.parcalar.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self._atla = False

    def handle_data(self, veri):
        if not self._atla:
            self.parcalar.append(veri)


def _html_metin(ham: bytes) -> str:
    toplayici = _MetinToplayici()
    toplayici.feed(ham.decode('utf-8', 'replace'))
    return ' '.join(toplayici.parcalar)


def _docx_metin(ham: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(ham)) as z:
            xml = z.read('word/document.xml').decode('utf-8', 'replace')
    except (KeyError, zipfile.BadZipFile) as hata:
        raise ValueError(f'DOCX açılamadı: {hata}')
    # Paragrafları koru, etiketleri boşluğa çevir.
    xml = re.sub(r'</w:p>', '\n', xml)
    xml = re.sub(r'<w:tab[^>]*/>', ' ', xml)
    return re.sub(r'<[^>]+>', '', xml)


def _pdf_akis_metni(veri: bytes) -> str:
    """PDF içerik akışındaki Tj/TJ metinlerini kabaca toplar."""
    parcalar = []
    # (…) Tj  ve  [(…)(…)] TJ
    for eslesme in re.finditer(rb'\((?:\\.|[^\\()])*\)\s*Tj|\[(?:[^\]]*)\]\s*TJ', veri):
        blok = eslesme.group(0)
        for metin in re.finditer(rb'\((?:\\.|[^\\()])*\)', blok):
            ham = metin.group(0)[1:-1]
            ham = re.sub(rb'\\([()\\])', rb'\1', ham)
            ham = ham.replace(b'\\n', b' ').replace(b'\\r', b' ').replace(b'\\t', b' ')
            parcalar.append(ham.decode('latin-1', 'replace'))
        parcalar.append(' ')
    return ''.join(parcalar)


def _pdf_metin(ham: bytes) -> str:
    if not ham.lstrip().startswith(b'%PDF'):
        raise ValueError('Dosya geçerli bir PDF değil.')
    parcalar = []
    # Sıkıştırılmış akışları çöz (FlateDecode); çözülemeyenler atlanır.
    for eslesme in re.finditer(rb'stream\r?\n(.*?)endstream', ham, re.S):
        veri = eslesme.group(1)
        try:
            veri = zlib.decompress(veri)
        except zlib.error:
            try:
                veri = zlib.decompressobj().decompress(veri)
            except zlib.error:
                pass  # sıkıştırılmamış ya da görüntü akışı
        if b'Tj' in veri or b'TJ' in veri:
            parcalar.append(_pdf_akis_metni(veri))
    metin = ' '.join(parcalar)
    metin = metin.replace('\\(', '(').replace('\\)', ')')
    return metin


def metin_cikar(ham: bytes, uzanti: str) -> str:
    """Baytlardan düz metin çıkarır (biçime göre)."""
    uzanti = str(uzanti or '').lower()
    if len(ham) > AZAMI_BAYT:
        raise ValueError('Dosya çok büyük (en fazla 20 MB).')
    if uzanti == '.pdf':
        metin = _pdf_metin(ham)
    elif uzanti == '.docx':
        metin = _docx_metin(ham)
    elif uzanti in ('.html', '.htm'):
        metin = _html_metin(ham)
    else:
        for kodlama in ('utf-8', 'cp1254', 'latin-1'):
            try:
                metin = ham.decode(kodlama)
                break
            except UnicodeDecodeError:
                continue
        else:
            metin = ham.decode('utf-8', 'replace')
    metin = metin.replace('\x00', ' ')
    metin = re.sub(r'[ \t]+', ' ', metin)
    metin = re.sub(r'\n{3,}', '\n\n', metin)
    return metin.strip()


def sayfalara_ayir(metin: str):
    """Metni sayfalara böler: form feed varsa onu, yoksa ~3000 karakterlik blokları kullanır."""
    metin = str(metin or '').strip()
    if not metin:
        return []
    if '\f' in metin:
        sayfalar = [s.strip() for s in metin.split('\f') if s.strip()]
    elif len(metin) <= 3000:
        sayfalar = [metin]
    else:
        sayfalar, tampon = [], ''
        for paragraf in metin.split('\n'):
            if len(tampon) + len(paragraf) > 3000 and tampon:
                sayfalar.append(tampon)
                tampon = paragraf
            else:
                tampon = (tampon + '\n' + paragraf).strip()
        if tampon:
            sayfalar.append(tampon)
    return sayfalar[:AZAMI_SAYFA]


def parcalara_ayir(metin: str, boy=Parca_BOY, binis=Parca_BINIS):
    """Uzun sayfa metnini üst üste binen parçalara böler (arama için)."""
    metin = ' '.join(str(metin or '').split())
    if not metin:
        return []
    if len(metin) <= boy:
        return [metin]
    parcalar, basla = [], 0
    while basla < len(metin):
        parca = metin[basla:basla + boy]
        # Kelime ortasında kesmemeye çalış.
        if basla + boy < len(metin):
            kesme = parca.rfind(' ')
            if kesme > boy * 0.6:
                parca = parca[:kesme]
        parca = parca.strip()
        if parca and (not parcalar or parca != parcalar[-1]):
            parcalar.append(parca)
        # Her adımda anlamlı ilerleme olsun (kısa kuyrukta sonsuz döngü olmasın).
        basla += max(len(parca) - binis, boy // 2)
        if len(parcalar) >= AZAMI_SAYFA * 4:
            break
    return [p for p in parcalar if p]


# --- veritabanı -------------------------------------------------------------
def ekle(c, ad, metin, kind=''):
    """Belgeyi parçalara ayırıp kaydeder; {'id', 'pages', 'chunks', 'chars'} döner."""
    from datetime import datetime
    sayfalar = sayfalara_ayir(metin)
    if not sayfalar:
        raise ValueError('Belgede okunabilir metin bulunamadı.')
    ad = ' '.join(str(ad or 'belge').split())[:120]
    simdi = datetime.now().isoformat(timespec='seconds')
    cur = c.execute('INSERT INTO docs(name,kind,pages,chars,created) VALUES (?,?,?,?,?)',
                    (ad, str(kind or '')[:20], len(sayfalar), len(metin), simdi))
    doc_id = int(cur.lastrowid or 0)
    adet = 0
    for i, sayfa in enumerate(sayfalar, 1):
        for parca in parcalara_ayir(sayfa):
            c.execute('INSERT INTO doc_chunks(doc_id,sayfa,metin,arama) VALUES (?,?,?,?)',
                      (doc_id, i, parca, _sade(parca)))
            adet += 1
    return {'id': doc_id, 'name': ad, 'pages': len(sayfalar), 'chunks': adet, 'chars': len(metin)}


def dosya_ekle(c, yol):
    """Yerel dosyayı okuyup belge olarak ekler."""
    yol = Path(str(yol or '')).expanduser()
    if not yol.is_file():
        raise ValueError('Dosya bulunamadı: ' + str(yol))
    uzanti = yol.suffix.lower()
    if uzanti not in DESTEKLENEN:
        raise ValueError('Desteklenmeyen biçim: ' + uzanti + ' (' + ', '.join(DESTEKLENEN) + ')')
    ham = yol.read_bytes()
    metin = metin_cikar(ham, uzanti)
    if not metin.strip():
        raise ValueError('Belgede metin bulunamadı (taranmış PDF olabilir; OCR desteklenmiyor).')
    return ekle(c, yol.name, metin, kind=uzanti.lstrip('.'))


def icerik_ekle(c, ad, b64, kind=''):
    """Base64 ile gelen dosya içeriğini ekler (tarayıcıdan yükleme)."""
    try:
        ham = base64.b64decode(str(b64 or ''), validate=False)
    except (ValueError, TypeError):
        raise ValueError('Dosya içeriği çözülemedi.')
    if not ham:
        raise ValueError('Dosya boş.')
    uzanti = Path(str(ad or '')).suffix.lower()
    if uzanti not in DESTEKLENEN:
        raise ValueError('Desteklenmeyen biçim: ' + (uzanti or '(yok)'))
    metin = metin_cikar(ham, uzanti)
    if not metin.strip():
        raise ValueError('Belgede metin bulunamadı.')
    return ekle(c, ad, metin, kind=kind or uzanti.lstrip('.'))


def listele(c):
    return [dict(zip(('id', 'name', 'kind', 'pages', 'chars', 'created'), r)) for r in
            c.execute('SELECT id,name,kind,pages,chars,created FROM docs ORDER BY id DESC LIMIT 200')]


def sil(c, doc_id):
    cur = c.execute('DELETE FROM docs WHERE id=?', (int(doc_id),))
    c.execute('DELETE FROM doc_chunks WHERE doc_id=?', (int(doc_id),))
    return cur.rowcount


def _kelimeler(sorgu):
    return [k for k in re.split(r'[^0-9a-z]+', _sade(sorgu)) if len(k) > 2]


def ara(c, sorgu, doc_id=None, limit=5):
    """Belge parçalarında kelime araması: en çok eşleşen parçalar."""
    kelimeler = _kelimeler(sorgu)[:8]
    if not kelimeler:
        return []
    # Soru cümlelerinde tüm kelimeler belgede geçmez ("kaç", "ne" gibi);
    # bu yüzden kelimeler OR ile aranır, sonra en az yarısını içeren parçalar seçilir.
    kosul = ' OR '.join(['arama LIKE ?'] * len(kelimeler))
    degerler = [f'%{k}%' for k in kelimeler]
    sql = ('SELECT ch.doc_id, d.name, ch.sayfa, ch.metin FROM doc_chunks ch '
           'JOIN docs d ON d.id=ch.doc_id WHERE ' + kosul)
    if doc_id:
        sql += ' AND ch.doc_id=?'
        degerler.append(int(doc_id))
    satirlar = c.execute(sql + ' LIMIT 400', degerler).fetchall()
    if not satirlar:
        return []
    gerekli = max(1, (len(kelimeler) + 1) // 2)
    puanli = []
    for doc, ad, sayfa, metin in satirlar:
        kucuk = _sade(metin)
        eslesen = sum(1 for k in kelimeler if k in kucuk)
        if eslesen < gerekli:
            continue
        puan = sum(kucuk.count(k) for k in kelimeler)
        puanli.append((puan, {'doc_id': doc, 'name': ad, 'sayfa': sayfa, 'metin': metin}))
    puanli.sort(key=lambda x: -x[0])
    secili, gorulen = [], set()
    for _, kayit in puanli:
        anahtar = (kayit['doc_id'], kayit['sayfa'], kayit['metin'][:60])
        if anahtar in gorulen:
            continue
        gorulen.add(anahtar)
        secili.append(kayit)
        if len(secili) >= max(1, min(int(limit or 5), 10)):
            break
    return secili


def baglam(parcalar):
    """Bulunan parçaları modele verilecek metne çevirir (kaynak numaralı)."""
    if not parcalar:
        return ''
    satirlar = ['Belgeden alınan bölümler (yalnızca bunlara dayan; emin değilsen belirt):']
    for i, parca in enumerate(parcalar, 1):
        satirlar.append(f'[{i}] {parca["name"]} · sayfa {parca["sayfa"]}: {parca["metin"]}')
    satirlar.append('Yanıtta [1], [2] gibi kaynak numarası kullan ve belge adını/sayfayı belirt. '
                    'Bu bölümlerde olmayan bilgiyi uydurma.')
    return '\n'.join(satirlar)


def ozet_metni(kayit):
    return f'{kayit["name"]} (sayfa {kayit["sayfa"]}, {len(kayit["metin"])} karakter)'


def json_yukle(metin):
    try:
        return json.loads(metin)
    except ValueError:
        return None
