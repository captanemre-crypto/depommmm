"""EMRE Windows desktop prototype: loopback server + WebView2 + tray."""
import os
import sys
import threading
from pathlib import Path

if sys.platform != 'win32':
    raise SystemExit('Bu masaüstü sürümü Windows için hazırlanmıştır.')

import pystray
import webview
from PIL import Image, ImageDraw

import server
from openjarvis_yonet import OpenJarvisManager

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
quitting = threading.Event()
tray_ready = threading.Event()

try:
    httpd = server.EmreServer(('127.0.0.1', 8765), server.Handler)
except OSError as exc:
    raise SystemExit('8765 portu kullanılıyor. Önce açık Emre sunucusunu kapatıp tekrar deneyin.\n'+str(exc))

threading.Thread(target=httpd.serve_forever, daemon=True).start()
openjarvis = OpenJarvisManager()
with server.db():
    pass

window = webview.create_window('EMRE', 'http://127.0.0.1:8765/', width=1250, height=850, min_size=(760, 520))

def make_icon():
    image=Image.new('RGBA',(64,64),(5,14,18,255))
    d=ImageDraw.Draw(image)
    d.ellipse((5,5,59,59),outline=(81,224,207,255),width=3)
    d.ellipse((15,15,49,49),outline=(255,139,79,255),width=2)
    d.ellipse((25,25,39,39),fill=(255,174,111,255))
    return image

def show_window(icon=None, item=None):
    window.show()
    window.restore()

def exit_app(icon=None, item=None):
    quitting.set()
    try: icon.stop()
    except Exception: pass
    window.destroy()

tray=pystray.Icon('emre',make_icon(),'EMRE',menu=pystray.Menu(
    pystray.MenuItem('Emre’yi aç',show_window,default=True),
    pystray.MenuItem('Tamamen çık',exit_app),
))

def on_close():
    # Do not hide a window without an accessible tray icon.
    if not quitting.is_set() and tray_ready.is_set() and tray.visible:
        window.hide()
        return False
    return True

window.events.closing += on_close

def tray_setup(icon):
    icon.visible=True
    tray_ready.set()

try:
    threading.Thread(target=openjarvis.start, daemon=True).start()
    tray.run_detached(setup=tray_setup)
    profile=Path(os.environ.get('LOCALAPPDATA',str(ROOT)))/'Emre'/'WebView'
    profile.mkdir(parents=True,exist_ok=True)
    print('EMRE masaüstü çalışıyor. Pencere kapanınca sistem tepsisine gider.',flush=True)
    print('Tamamen kapatmak için tepsi simgesinden Tamamen çık seçin.',flush=True)
    webview.start(private_mode=False,storage_path=str(profile))
finally:
    quitting.set()
    try:tray.stop()
    except Exception:pass
    openjarvis.stop()
    httpd.shutdown()
    httpd.server_close()
