"""Narrow Ollama tools for the local ledger; never move actual money."""
import re, json
from datetime import datetime

TOOLS=[{'type':'function','function':{'name':'ledger_record','description':'Kullanıcı açıkça deftere alacak, verecek, alınmış tahsilat veya yapılmış ödeme kaydetmek isterse kayıt oluştur. Para transferi yapmaz. Bilgi eksik veya belirsizse çağırma. Sadece son kullanıcı mesajındaki rakamla yazılmış tutarı kullan. Hatırlatma istenirse tam tarih ve saat olmalı; yoksa kullanıcıya sor.', 'parameters':{'type':'object','properties':{'person':{'type':'string','description':'Kullanıcının yazdığı kişi adı'},'kind':{'type':'string','enum':['receivable','payable','received','paid'],'description':'receivable=benim alacağım; payable=benim borcum; received=aldığım tahsilat; paid=yaptığım ödeme'},'amount_kurus':{'type':'integer','description':'TL tutarı kuruş cinsinden; 1000 TL = 100000 kuruş'},'note':{'type':'string'},'remind_at':{'type':'string','description':'İstenmişse YYYY-MM-DDTHH:MM yerel tarih saat, yoksa boş'}},'required':['person','kind','amount_kurus']}}},{'type':'function','function':{'name':'ledger_list','description':'Kullanıcının alacak verecek defteri hesaplarını ve hareketlerini görüntüler.', 'parameters':{'type':'object','properties':{'person':{'type':'string','description':'Kişi adı, tüm kayıtlar için boş bırak'}},'required':[]}}}]
LABELS={'receivable':'Alacak','payable':'Verecek','received':'Tahsilat','paid':'Ödeme'}


def parse_amount(raw):
    """'1.250,50', '1.000.000', '1500', '1,500.75' gibi Türkçe/İngilizce yazımları kuruşa çevir.

    Tek bir yardımcı fonksiyon kullanmak, farklı kod yollarında farklı sonuç
    üretilmesini (örn. '1.000.000 TL'nin reddedilmesini) engeller.
    """
    from decimal import Decimal, InvalidOperation
    raw = (raw or '').strip().rstrip('.,')
    if not raw:
        raise ValueError('Tutar boş.')
    if ',' in raw:
        # Virgül ondalık ayırıcıdır; noktalar binlik ayırıcıdır.
        raw = raw.replace('.', '').replace(',', '.')
    elif raw.count('.') > 1:
        raw = raw.replace('.', '')
    elif raw.count('.') == 1:
        integer, _, fraction = raw.partition('.')
        # '1.500' binlik ayırıcı, '1.50' ondalık.
        if len(fraction) == 3 and integer and integer.isdigit():
            raw = integer + fraction
    try:
        amount = Decimal(raw) * 100
    except (InvalidOperation, ValueError):
        raise ValueError('Tutar anlaşılamadı.')
    if amount != amount.to_integral_value():
        raise ValueError('Tutar en fazla iki ondalık basamak içerebilir.')
    amount = int(amount)
    if not 0 < amount <= 100000000000:
        raise ValueError('Tutar geçersiz.')
    return amount


def amount_matches(text):
    """Metindeki 'TL/lira/₺' ile yazılmış tutarların kuruş karşılıklarını döndürür."""
    results = []
    for match in re.finditer(r'(?<!\w)(\d[\d.,]*)\s*(?:tl|₺|lira)(?!\w)', text.casefold()):
        try:
            results.append(parse_amount(match.group(1)))
        except ValueError:
            results.append(None)
    return results
def execute(name,args,db,last_user):
    if isinstance(args,str): args=json.loads(args)
    if not isinstance(args,dict): raise ValueError('İşlem bilgileri geçersiz.')
    if name=='ledger_list':
        person=str(args.get('person','')).strip()
        with db() as c:
            rows=c.execute('SELECT person,kind,amount,note,due FROM ledger ORDER BY id DESC LIMIT 500').fetchall()
        if person: rows=[r for r in rows if person.casefold() in r[0].casefold()]
        totals={}
        for p,k,a,n,d in rows:
            v=totals.setdefault(p,{'alacak':0,'verecek':0})
            if k=='receivable':v['alacak']+=a
            elif k=='received':v['alacak']-=a
            elif k=='payable':v['verecek']+=a
            elif k=='paid':v['verecek']-=a
        if not totals:return 'Defterde kayıt bulunamadı.'
        def tr(n):return f'{n/100:,.2f}'.replace(',','X').replace('.',',').replace('X','.')
        return '\n'.join(f"{p}: alacak {tr(v['alacak'])} TL, verecek {tr(v['verecek'])} TL" for p,v in totals.items())
    if name!='ledger_record': raise ValueError('Bu işlem desteklenmiyor.')
    person=str(args.get('person','')).strip();kind=args.get('kind');amount=args.get('amount_kurus');note=str(args.get('note','')).strip()[:300];due=str(args.get('remind_at','')).strip()
    lower=last_user.lower()
    if not re.search(r'alacağ|alacak|borç|borcum|verecek|ödedim|ödeme|tahsil|aldım|kaydet|deftere',lower) or re.search(r'var\s+m[ıi]|ne kadar|kaç lira|\?',lower): raise ValueError('Kayıt isteği net değil; kişiyi, tutarı ve işlem türünü belirt.')
    if due and not re.search(r'hatırla|hatırlat|uyar|bildir',lower): raise ValueError('Hatırlatıcı isteği açık değil.')
    if not due and re.search(r'hatırla|hatırlat|uyar|bildir',lower): raise ValueError('Hatırlatıcı için tarih ve saati belirt.')
    if not person or len(person)>100 or person.casefold() not in last_user.casefold(): raise ValueError('Kişi adı son mesajda açıkça bulunmalı; tekrar söyle.')
    if kind not in LABELS or type(amount) is not int or not 0<amount<=100000000000: raise ValueError('İşlem türü veya tutar belirsiz.')
    # Models can misinterpret quantities: accept only a numeric amount that matches the utterance.
    nums=[]
    for m in re.finditer(r'(?<!\w)\d[\d.,]*(?!\w)',last_user):
        try: nums.append(parse_amount(m.group()))
        except ValueError: pass
    if amount not in nums: raise ValueError('Hataları önlemek için tutarı rakamla ve açıkça söyle.')
    if due:
        dt=datetime.fromisoformat(due)
        if dt.tzinfo is not None: raise ValueError('Tarih yerel saat olmalı.')
        due=dt.isoformat(timespec='minutes')
    with db() as c:
        cur=c.execute('INSERT INTO ledger(person,kind,amount,note,due,created) VALUES (?,?,?,?,?,?)',(person,kind,amount,note,due or None,datetime.now().isoformat(timespec='seconds')))
        if due: c.execute('INSERT INTO reminders(text,due) VALUES (?,?)',(f"{LABELS[kind]}: {person} — {amount/100:.2f} TL",due))
        record_id=cur.lastrowid
    val=f'{amount/100:,.2f}'.replace(',','X').replace('.',',').replace('X','.')
    return f"Kaydedildi: {person} — {LABELS[kind]} {val} TL."+(f' Hatırlatıcı: {due.replace("T"," ")}.' if due else '')+f' (Kayıt no: {record_id})'

def create_account_from_text(text, db):
    """Explicit account-creation requests; reject ambiguous amounts before writing."""
    lower=text.casefold()
    if re.search(r'hesap\s+makine', lower): return None
    if not re.search(r'hesap',lower) or not re.search(r'oluştur|oluşturalım|aç|ekle',lower):
        return None
    match=re.search(r"(?:^|[,;])\s*(?:emre[, ]+|dostum[, ]+)?([\wÇĞİÖŞÜçğıöşü .'-]{1,100}?)\s+(?:adında|isminde|adlı)\s+(?:(?:yeni|cari)\s+)*hesap",text,re.I)
    if not match:
        match=re.search(r'(?:(?:yeni|cari)\s+)*hesap\s+(?:oluştur|aç|ekle)\s*[:\-]?\s+(?:adı\s+)?([\wÇĞİÖŞÜçğıöşü .\'-]+)',text,re.I)
    if not match: return 'Hesap oluşturmak için kişi veya firma adını söyle.'
    name=match.group(1).strip(' .,-\'\"')
    if not name or len(name)>100:return 'Hesap adı geçersiz; lütfen tekrar söyle.'
    wants_entry=bool(re.search(r'alacak|alacağ|verecek|borç|tahsilat|ödeme',lower))
    kind=None;amount=None
    if wants_entry:
        if re.search(r'alacak|alacağ',lower):kind='receivable'
        elif re.search(r'verecek|borç',lower):kind='payable'
        elif re.search(r'tahsilat',lower):kind='received'
        elif re.search(r'ödeme',lower):kind='paid'
        amounts=amount_matches(lower)
        if not amounts:return 'İşlemi kaydetmek için tutarı rakamla ve TL olarak söyle.'
        if len(amounts)>1:return 'Birden fazla tutar gördüm; işlemleri tek tek söyle.'
        if amounts[0] is None:return 'Tutarı anlayamadım; örneğin 2000 TL diye söyle.'
        amount=amounts[0]
    if re.search(r'hatırla|hatırlat|uyar|bildir',lower):return 'Hatırlatıcı eklemek için tarih ve saati ayrı bir cümlede açıkça söyle.'
    with db() as c:
        existing=[r[0] for r in c.execute('SELECT name FROM accounts UNION SELECT person FROM ledger')]
        existing_name=next((x for x in existing if x.casefold()==name.casefold()),None)
        if not existing_name:c.execute('INSERT INTO accounts(name,note) VALUES (?,?)',(name,''))
        if wants_entry:
            actual=existing_name or name
            c.execute('INSERT INTO ledger(person,kind,amount,note,due,created) VALUES (?,?,?,?,?,?)',(actual,kind,amount,'',None,datetime.now().isoformat(timespec='seconds')))
    msg=(name+' hesabı zaten vardı.' if existing_name else name+' hesabını oluşturdum.')
    if wants_entry:
        val=f'{amount/100:,.2f}'.replace(',','X').replace('.',',').replace('X','.')
        msg+=f' {val} TL {LABELS[kind].lower()} kaydettim.'
    return msg

def direct_ledger_action(text, db):
    """Process explicit, unambiguous ledger requests; never perform bank transactions."""
    lower=text.casefold()
    if not re.search(r'alacak|alacağ|verecek|borç|tahsil|ödeme|ödedim',lower): return None
    # These are questions, not requests to mutate the ledger.
    is_query=bool(re.search(r'ne kadar|bakiye|hesabında ne var|borcu var mı|alacağım var mı',lower))
    action=bool(re.search(r'ekle|kaydet|yaz|işle|ödedim|tahsil ettim|ödeme yaptım|tahsilat yaptım',lower))
    if not is_query and not action:return None
    with db() as c:
        names=[r[0] for r in c.execute('SELECT name FROM accounts UNION SELECT person FROM ledger')]
    def trnorm(x):return x.translate(str.maketrans({'I':'ı','İ':'i'})).casefold()
    normalized=trnorm(text)
    matches=[]
    for name in names:
        n=trnorm(name.strip())
        # Permit common Turkish case suffixes with or without an apostrophe.
        pattern=r'(?<!\w)'+re.escape(n)+r"(?:['’]?(?:a|e|ya|ye|ı|i|u|ü|dan|den|tan|ten|nın|nin|nun|nün))?(?!\w)"
        if re.search(pattern,normalized):matches.append(name)
    if len(matches)>1:
        matches=sorted(matches,key=len,reverse=True)
        if trnorm(matches[1]) not in trnorm(matches[0]):return 'Hangi hesabı kastettiğin net değil; hesap adını tam söyle.'
        matches=matches[:1]
    if not matches:return 'Hesabı bulamadım. Önce hesap oluştur veya kayıtlı hesap adını tam söyle.'
    person=matches[0]
    if is_query:return execute('ledger_list',{'person':person},db,text)
    if re.search(r'(?<!\w)(?:sil|silelim|kaldır|kaldıralım|iptal)(?!\w)',lower): return None
    if re.search(r'alacak|alacağ',lower):kind='receivable'
    elif re.search(r'verecek|borç',lower):kind='payable'
    elif re.search(r'tahsil',lower):kind='received'
    else:kind='paid'
    amounts=amount_matches(lower)
    if not amounts:return 'Kayıt yapılmadı. Tutarı rakamla ve TL olarak söyle.'
    if len(amounts)>1:return 'Birden fazla tutar gördüm; yanlış kayıt olmaması için işlemleri tek tek söyle.'
    if amounts[0] is None:return 'Tutar anlaşılamadı; kayıt yapılmadı.'
    amount=amounts[0]
    if re.search(r'hatırla|hatırlat|uyar|bildir',lower):return 'Hatırlatıcı isteniyorsa tarih ve saat bilgisiyle ayrı bir kayıt oluştur; bu işlem henüz yapılmadı.'
    with db() as c:
        cur=c.execute('INSERT INTO ledger(person,kind,amount,note,due,created) VALUES (?,?,?,?,?,?)',(person,kind,amount,'',None,datetime.now().isoformat(timespec='seconds')))
        entry_id=cur.lastrowid
    formatted=f'{amount/100:,.2f}'.replace(',','X').replace('.',',').replace('X','.')
    return f'{person} hesabına {formatted} TL {LABELS[kind].lower()} kaydedildi. Kayıt no: {entry_id}.'
