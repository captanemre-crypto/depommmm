"""Local, opt-in Arena browser bridge. No CAPTCHA or login bypass."""
import queue
import threading
import time
from pathlib import Path

# Testlerde kısaltılabilmesi için modül düzeyinde sabitler.
ANSWER_TIMEOUT_SECONDS = 120
STABLE_SECONDS = 4

jobs=queue.Queue()
state={'status':'stopped','message':'Tarayıcı başlatılmadı.','answer':'','answer_verified':False}
lock=threading.Lock()
started=False

def update(**values):
    with lock: state.update(values)

def snapshot():
    with lock: return dict(state)

def start():
    global started
    if started and snapshot()['status'] not in ('error','stopped'): return
    started=True
    update(status='starting',message='Tarayıcı başlatılıyor…',answer='',answer_verified=False)
    threading.Thread(target=worker,daemon=True).start()

def send(question):
    st=snapshot()['status']
    if st!='ready': raise ValueError('Önce Arena tarayıcısını aç ve giriş yap.')
    if not question or len(question)>6000: raise ValueError('Soru 1–6000 karakter arasında olmalı.')
    update(status='busy',message='Soru gönderiliyor…',answer='',answer_verified=False)
    jobs.put(question)

def worker():
    global started
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            profile=Path(__file__).resolve().parent/'arena_profile'
            ctx=p.chromium.launch_persistent_context(str(profile),channel='msedge',headless=False,chromium_sandbox=True,viewport={'width':1200,'height':850})
            page=ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto('https://arena.ai/agent',wait_until='domcontentloaded',timeout=45000)
            update(status='ready',message='Tarayıcı açık. Arena’ya giriş yap ve gerekiyorsa doğrulamayı kendin tamamla.')
            # Read only explicit assistant role nodes. Never scrape arbitrary page text or guess.
            answer_selector='[data-message-role="assistant"], [data-role="assistant"], [data-testid="assistant-message"]'
            while True:
                if page.is_closed(): break
                try: text=jobs.get(timeout=.5)
                except queue.Empty:
                    page.wait_for_timeout(50)
                    continue
                try:
                    if not page.url.startswith('https://arena.ai/'):
                        raise ValueError('Arena sayfası açık değil. Tarayıcıda arena.ai/agent sayfasına dön.')
                    boxes=page.locator('textarea:visible, [contenteditable="true"][role="textbox"]:visible')
                    if boxes.count()!=1: raise ValueError('Soru alanı güvenle belirlenemedi. Giriş/doğrulama durumunu kontrol et.')
                    answers=page.locator(answer_selector)
                    old=answers.count()
                    box=boxes.first
                    box.fill(text)
                    box.press('Enter')
                    update(message='Yanıt bekleniyor…')
                    deadline=time.monotonic()+ANSWER_TIMEOUT_SECONDS
                    previous=''; stable_since=None
                    while time.monotonic()<deadline:
                        if page.is_closed() or not page.url.startswith('https://arena.ai/'): raise ValueError('Arena sayfası kapandı veya farklı bir adrese geçildi.')
                        count=answers.count()
                        value=answers.last.inner_text(timeout=2000).strip() if count>old else ''
                        if value and value==previous:
                            if stable_since is None: stable_since=time.monotonic()
                            if time.monotonic()-stable_since>=STABLE_SECONDS: break
                        else: previous=value;stable_since=None
                        page.wait_for_timeout(500)
                    if not previous: raise ValueError('Yanıt güvenilir biçimde bulunamadı. Arena arayüzü bu sürümle uyumsuz olabilir; yanıtı tarayıcıdan kontrol et.')
                    update(status='ready',message='Yanıt bulundu; Arena ekranıyla karşılaştırarak doğrula.',answer=previous,answer_verified=False)
                except Exception as exc:
                    msg=str(exc)
                    if len(msg)>280: msg=msg[:280]
                    update(status='ready',message='İşlem tamamlanamadı: '+msg,answer='',answer_verified=False)
            ctx.close()
    except ImportError:
        update(status='error',message='Playwright kurulu değil. Kurulum adımları README dosyasında.',answer='')
    except Exception:
        update(status='error',message='Microsoft Edge başlatılamadı. Edge ve Playwright kurulumunu, açık Arena profili olup olmadığını kontrol et.',answer='')
    finally:
        started=False
        # Son bulunan yanıt korunur: kullanıcı pencere kapandıktan sonra da okuyabilir.
        if snapshot()['status'] not in ('error',): update(status='stopped',message='Arena tarayıcısı kapatıldı.')
