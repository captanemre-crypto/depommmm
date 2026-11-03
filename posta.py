"""Posta: yerel `.eml` ve `.mbox` dosyalarını **salt okunur** okur.

Bilinçli tasarım kararı: **IMAP/SMTP yok**. E-posta hesabına bağlanmak parola
saklamayı ve dış ağa çıkmayı gerektirir; Emre'nin sınırları (yalnızca 127.0.0.1,
onaysız dış işlem yok, sır saklama) gereği posta yalnızca **bilgisayarındaki
dosyalardan** okunur:

- `.eml` dosyaları veya tek dosyalık `.mbox` arşivleri,
- ya da bir klasördeki `.eml` dosyaları.

Gönderim, silme, "okundu" işaretleme yoktur. Yalnızca başlık/gönderen/tarih ve
kısa önizleme okunur. Ekler **açılmaz**.
"""
import email
import email.policy
import re
from datetime import datetime
from pathlib import Path

AZAMI_BAYT = 25 * 1024 * 1024
AZAMI_MESAJ = 200
ONIZLEME = 400


def _temiz(metin, azami=ONIZLEME):
    return ' '.join(str(metin or '').split())[:azami]


def _onar(deger):
    """Başlık değerini metne çevirir; 8 bit Türkçe başlıkları onarır.

    `mailbox` (compat32) 8 bit başlıkları `email.header.Header` olarak döndürür ve
    `str()` bunları bozar (`İ` → `??`). Header'ın iç parçaları doğrudan çözülür.
    """
    parcalar = getattr(deger, '_chunks', None)
    if parcalar:
        metin = ''
        for icerik, kodlama in parcalar:
            if isinstance(icerik, bytes):
                for kod in (kodlama or 'utf-8', 'utf-8', 'cp1254', 'latin-1'):
                    try:
                        metin += icerik.decode(kod)
                        break
                    except (UnicodeDecodeError, LookupError):
                        continue
            else:
                metin += _surrogate_onar(str(icerik))
        return metin
    metin = str(deger or '')
    try:
        ham = metin.encode('ascii', 'surrogateescape')
    except UnicodeEncodeError:
        return metin
    if all(bayt < 128 for bayt in ham):
        return metin
    for kodlama in ('utf-8', 'cp1254'):
        try:
            return ham.decode(kodlama)
        except UnicodeDecodeError:
            continue
    return metin


def _surrogate_onar(metin):
    """`surrogateescape` ile taşınan 8 bit baytları gerçek metne çevirir."""
    try:
        ham = metin.encode('ascii', 'surrogateescape')
    except UnicodeEncodeError:
        return metin
    if all(bayt < 128 for bayt in ham):
        return metin
    for kodlama in ('utf-8', 'cp1254'):
        try:
            return ham.decode(kodlama)
        except UnicodeDecodeError:
            continue
    return metin


def _govde(mesaj):
    """Metin gövdesini çıkarır; HTML varsa etiketleri temizler."""
    parca = None
    if mesaj.is_multipart():
        for alt in mesaj.walk():
            if alt.get_content_maintype() != 'text':
                continue
            if alt.get_content_subtype() == 'plain':
                parca = alt
                break
            if parca is None and alt.get_content_subtype() == 'html':
                parca = alt
    else:
        parca = mesaj
    if parca is None:
        return ''
    try:
        ham = parca.get_content()
    except (LookupError, ValueError, AttributeError):
        # mailbox.mbox ileti nesneleri (compat32) get_content() sunmaz.
        ham = parca.get_payload(decode=True)
        if ham is None:
            ham = parca.get_payload() or ''
        if isinstance(ham, bytes):
            try:
                ham = ham.decode('utf-8')
            except UnicodeDecodeError:
                ham = ham.decode('cp1254', 'replace')
    return re.sub(r'<[^>]{0,200}>', ' ', str(ham))


def _tarih(mesaj):
    try:
        return email.utils.parsedate_to_datetime(mesaj.get('Date', ''))
    except (TypeError, ValueError):
        return None


def mesaj_ozeti(mesaj, kaynak=''):
    tarih = _tarih(mesaj)
    return {
        'kimden': _temiz(_onar(mesaj.get('From', '')), 160),
        'kime': _temiz(_onar(mesaj.get('To', '')), 160),
        'konu': _temiz(_onar(mesaj.get('Subject', '')), 200) or '(konusuz)',
        'tarih': tarih.isoformat(timespec='minutes') if tarih else '',
        'onizleme': _temiz(_govde(mesaj)),
        'ek_var': any(p.get_filename() for p in mesaj.walk()),
        'kaynak': str(kaynak or '')[:120],
    }


def eml_oku(yol):
    yol = Path(str(yol or '')).expanduser()
    if not yol.is_file():
        raise ValueError('Posta dosyası bulunamadı: ' + str(yol))
    if yol.stat().st_size > AZAMI_BAYT:
        raise ValueError('Posta dosyası çok büyük.')
    with yol.open('rb') as dosya:
        mesaj = email.message_from_binary_file(dosya, policy=email.policy.default)
    return [mesaj_ozeti(mesaj, kaynak=yol.name)]


def mbox_oku(yol):
    """Tek dosyalık mbox arşivini okur (en yeni `AZAMI_MESAJ` ileti)."""
    yol = Path(str(yol or '')).expanduser()
    if not yol.is_file():
        raise ValueError('Posta arşivi bulunamadı: ' + str(yol))
    if yol.stat().st_size > AZAMI_BAYT:
        raise ValueError('Posta arşivi çok büyük.')
    import mailbox
    sonuc = []
    try:
        kutu = mailbox.mbox(str(yol), create=False)
        try:
            for mesaj in kutu:
                sonuc.append(mesaj_ozeti(mesaj, kaynak=yol.name))
        finally:
            kutu.close()
    except (OSError, ValueError) as hata:
        raise ValueError(f'Posta arşivi okunamadı: {hata}')
    return sonuc[-AZAMI_MESAJ:]


def klasor_oku(klasor):
    """Klasördeki tüm `.eml` dosyalarını okur."""
    kok = Path(str(klasor or '')).expanduser()
    if not kok.is_dir():
        raise ValueError('Posta klasörü bulunamadı: ' + str(kok))
    hepsi = []
    for dosya in sorted(kok.glob('*.eml'))[:AZAMI_MESAJ]:
        try:
            hepsi.extend(eml_oku(dosya))
        except ValueError:
            continue
    return hepsi


def yolu_oku(yol):
    """Tek bir yol: .eml, .mbox veya klasör. Biçime göre okur."""
    hedef = Path(str(yol or '')).expanduser()
    if hedef.is_dir():
        return klasor_oku(hedef)
    if not hedef.is_file():
        raise ValueError('Posta kaynağı bulunamadı: ' + str(hedef))
    if hedef.suffix.lower() == '.eml':
        return eml_oku(hedef)
    return mbox_oku(hedef)


def sirala(mesajlar):
    """Yeniden eskiye sıralar (tarihi olmayanlar sona)."""
    def anahtar(mesaj):
        try:
            return datetime.fromisoformat(mesaj['tarih'])
        except (ValueError, KeyError):
            return datetime.min
    return sorted(mesajlar, key=anahtar, reverse=True)


def metin_ozet(mesajlar, adet=5):
    """Son iletileri modele/seslendirmeye uygun kısa metne çevirir."""
    secili = sirala(mesajlar)[:max(1, min(int(adet or 5), 20))]
    if not secili:
        return 'Posta kaynağında ileti bulunamadı.'
    satirlar = [f'Son {len(secili)} ileti:']
    for mesaj in secili:
        tarih = mesaj['tarih'][:16].replace('T', ' ') if mesaj['tarih'] else '—'
        satirlar.append(f"- {tarih} · {mesaj['konu']} · {mesaj['kimden'][:60]}")
        if mesaj['onizleme']:
            satirlar.append(f"  {mesaj['onizleme'][:140]}")
    return '\n'.join(satirlar)


def gerekiyor_mu(metin):
    """Metin posta sorusu mu?"""
    kucuk = ' '.join(str(metin or '').lower().split())
    if not kucuk:
        return False
    return any(a in kucuk for a in ('mail', 'e-posta', 'eposta', 'gelen kutusu')) and any(
        s in kucuk for s in ('son', 'özetle', 'göster', 'var mı', 'kimden', 'oku'))
