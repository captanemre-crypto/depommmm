"""Sohbetten hatırlatıcı oluşturma (kural tabanlı, modelden bağımsız).

Model çağrısı başarısız olsa veya niyeti kaçırsa bile "yarın 09:00'da hatırlat"
gibi açık komutlar kaydedilir. Tarih belirsizse kayıt yapılmaz; kullanıcıya
desteklenen biçimler örneklerle söylenir.
"""
from datetime import datetime

import ledger_tools
import zaman_ayristir

ORNEKLER = ('Örnek: "yarın 09:00 Ahmet\'i ara diye hatırlat", "3 gün sonra saat 18:00 '
            'toplantı", "15 Kasım 14:30 fatura ödemesi", "pazartesi sabah 9 kontrol et".')


def _kaydet(db, text, when):
    with db() as c:
        cur = c.execute('INSERT INTO reminders(text,due) VALUES (?,?)',
                        (text[:300], when.isoformat(timespec='minutes')))
        return cur.lastrowid


def direct_reminder_action(text, db, now=None):
    """Açık hatırlatıcı isteklerini işler; niyet yoksa None döner."""
    if not zaman_ayristir.has_reminder_intent(text):
        return None
    when = zaman_ayristir.parse_when(text, now=now)
    if when is None:
        return ('Hatırlatıcı için tarih ve saati anlayamadım; kayıt yapılmadı. ' + ORNEKLER)
    if when <= (now or datetime.now()):
        return ('Hatırlatıcı zamanı geçmişte kalıyor; kayıt yapılmadı. ' + ORNEKLER)

    temiz = zaman_ayristir.strip_time_and_command(text)
    mesaj = _kaydet(db, temiz or 'Hatırlatıcı', when)

    # Aynı cümlede defter işlemi varsa (örn. "Ahmete 100 TL alacak ekle yarın hatırlat")
    # tutarı ve kişiyi kaybetmemek için defter kaydını da oluştur.
    defter_mesaji = ledger_tools.direct_ledger_action(temiz, db) if temiz else None
    zaman = when.strftime('%d.%m.%Y %H:%M')
    if defter_mesaji and 'kaydedildi' in defter_mesaji.casefold():
        return f'{defter_mesaji} Hatırlatıcı kuruldu: {zaman}.'
    return f'Hatırlatıcı kuruldu: {zaman} — {temiz or "Hatırlatıcı"} (Kayıt no: {mesaj}).'
