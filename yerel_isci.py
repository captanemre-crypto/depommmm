"""Yerel işçi süreci yardımcısı: kalıcı stdin/stdout hattı + kesin zaman aşımı.

Whisper ve Piper işçileri tek bir satır JSON istek/yanıt protokolü kullanır.
Eski sürümde yanıt okuması süresiz bekliyordu; işçi kilitlendiğinde kilit hiç
bırakılmıyor ve ses özellikleri uygulama yeniden başlatılana kadar ölü kalıyordu.
Bu sınıf her isteğe zaman aşımı koyar, takılan işçiyi öldürüp yeniden başlatır.
"""
import json
import queue
import subprocess
import threading


class _Okuyucu(threading.Thread):
    """stdout'u arka planda kuyruğa aktarır; ana iş parçacığı süresiz beklemez."""

    def __init__(self, stream, kuyruk):
        super().__init__(daemon=True)
        self.stream = stream
        self.kuyruk = kuyruk

    def run(self):
        try:
            for satir in self.stream:
                self.kuyruk.put(satir)
        except Exception:
            pass
        finally:
            self.kuyruk.put(None)


class YerelIsci:
    def __init__(self, executable, script, baslatma_saniye=180, istek_saniye=180):
        self.executable = str(executable)
        self.script = str(script)
        self.baslatma_saniye = baslatma_saniye
        self.istek_saniye = istek_saniye
        self.proc = None
        self.kuyruk = None

    def _canli(self):
        return self.proc is not None and self.proc.poll() is None

    def kapat(self):
        proc, self.proc = self.proc, None
        self.kuyruk = None
        if proc is None:
            return
        try:
            proc.kill()
        except OSError:
            pass
        try:
            proc.wait(timeout=5)
        except Exception:
            pass
        # Boru uçlarını kapatmak Windows'ta dosya tanıtıcısı sızıntısını önler.
        for stream in (proc.stdin, proc.stdout):
            try:
                stream.close()
            except Exception:
                pass

    def _satir(self, timeout):
        try:
            satir = self.kuyruk.get(timeout=timeout)
        except queue.Empty:
            self.kapat()
            raise ValueError('Yerel ses işçisi zamanında yanıt vermedi; yeniden başlatıldı.')
        if satir is None:
            self.kapat()
            raise ValueError('Yerel ses işçisi beklenmedik şekilde kapandı.')
        try:
            veri = json.loads(satir)
        except ValueError:
            raise ValueError('Yerel ses işçisi geçersiz yanıt döndürdü.')
        if not isinstance(veri, dict):
            raise ValueError('Yerel ses işçisi geçersiz yanıt döndürdü.')
        return veri

    def _baslat(self):
        self.kapat()
        try:
            self.proc = subprocess.Popen(
                [self.executable, '-X', 'utf8', '-u', self.script],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, encoding='utf-8', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except OSError:
            raise ValueError('Yerel ses ortamı başlatılamadı; kurulumu kontrol et.')
        self.kuyruk = queue.Queue()
        _Okuyucu(self.proc.stdout, self.kuyruk).start()
        hazir = self._satir(self.baslatma_saniye)
        if not hazir.get('ready'):
            self.kapat()
            raise ValueError(hazir.get('error') or 'Yerel ses işçisi başlatılamadı.')

    def istek(self, payload):
        if not self._canli():
            self._baslat()
        satir = json.dumps(payload, ensure_ascii=True) + '\n'
        try:
            self.proc.stdin.write(satir)
            self.proc.stdin.flush()
        except (OSError, ValueError):
            self._baslat()
            try:
                self.proc.stdin.write(satir)
                self.proc.stdin.flush()
            except (OSError, ValueError):
                self.kapat()
                raise ValueError('Yerel ses işçisine istek gönderilemedi.')
        return self._satir(self.istek_saniye)
