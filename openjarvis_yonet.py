"""Desktop-only lifecycle manager for an existing local OpenJarvis checkout."""
import json
import os
import socket
import subprocess
import threading
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / 'openjarvis_yol.json'
LOG = ROOT / 'openjarvis_masaustu.log'

class OpenJarvisManager:
    def __init__(self):
        self.process = None
        self.log = None
        self.lock = threading.Lock()
        self.closed = False

    def start(self):
        with self.lock:
            if self.closed:
                return
            try:
                with urllib.request.urlopen('http://127.0.0.1:8766/health', timeout=2) as response:
                    if response.status == 200:
                        print('8766 üzerinde mevcut servis bulundu; kapatılmayacak.', flush=True)
                        return
            except Exception:
                pass
            try:
                with socket.socket() as sock:
                    sock.settimeout(1)
                    if sock.connect_ex(('127.0.0.1', 8766)) == 0:
                        print('8766 portu başka bir servis tarafından kullanılıyor.', flush=True)
                        return
            except OSError:
                return
            try:
                data = json.loads(CONFIG.read_text(encoding='utf-8'))
                folder = Path(data['klasor'])
                if not (folder / 'pyproject.toml').is_file():
                    raise ValueError('OpenJarvis proje klasöründe pyproject.toml bulunamadı.')
                self.log = LOG.open('a', encoding='utf-8')
                self.log.write('\n--- EMRE OpenJarvis başlatma ---\n'); self.log.flush()
                self.process = subprocess.Popen(
                    ['py', '-m', 'uv', 'run', '--extra', 'server', 'jarvis', 'serve',
                     '--host', '127.0.0.1', '--port', '8766', '--engine', 'ollama',
                     '--model', 'emre-cpu', '--agent', 'simple'],
                    cwd=str(folder), stdin=subprocess.DEVNULL, stdout=self.log,
                    stderr=subprocess.STDOUT, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            except Exception as exc:
                print('OpenJarvis otomatik başlatılamadı:', exc, flush=True)
                try:
                    with LOG.open('a', encoding='utf-8') as f: f.write('Başlatma hatası: '+str(exc)+'\n')
                except OSError:
                    pass
                if self.log:
                    self.log.close(); self.log = None

    def stop(self):
        with self.lock:
            self.closed = True
            if self.process and self.process.poll() is None:
                try:
                    # Only the process tree created by this desktop instance.
                    subprocess.run(['taskkill', '/PID', str(self.process.pid), '/T', '/F'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), timeout=10)
                except Exception:
                    self.process.terminate()
            if self.log:
                self.log.close(); self.log = None
