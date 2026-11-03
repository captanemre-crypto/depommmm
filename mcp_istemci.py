"""Minimal MCP (Model Context Protocol) istemcisi.

- stdio taşıması: alt süreç + satır başına bir JSON-RPC 2.0 iletisi.
- Yalnızca `mcp_ayar.json` içinde **kullanıcı tarafından** tanımlanmış sunucular
  çalıştırılır; kabuk (shell) kullanılmaz, argümanlar liste olarak verilir.
- Her araç çağrısı sunucu katmanında onaya (`confirmed:true`) tabidir.
- Süreçler tembel başlar ve boşta kalınca kapatılır.
"""
import json
import os
import subprocess
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
AYAR = ROOT / 'mcp_ayar.json'
AZAMI_SUNUCU = 8
AZAMI_ARAC = 200
BASLATMA_SANIYE = 20
ISTEK_SANIYE = 60


def ayar_oku(yol=None):
    """`mcp_ayar.json` → {'sunucular': [{ad, komut, argumanlar, env}]}"""
    hedef = Path(yol) if yol else AYAR
    try:
        veri = json.loads(hedef.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {'sunucular': []}
    if not isinstance(veri, dict):
        return {'sunucular': []}
    sunucular = []
    for ham in (veri.get('sunucular') or [])[:AZAMI_SUNUCU]:
        if not isinstance(ham, dict):
            continue
        ad = str(ham.get('ad') or '').strip()
        komut = str(ham.get('komut') or '').strip()
        if not ad or not komut:
            continue
        argumanlar = ham.get('argumanlar') or []
        if not isinstance(argumanlar, list) or any(not isinstance(a, str) for a in argumanlar):
            continue
        env = ham.get('env') or {}
        if not isinstance(env, dict):
            env = {}
        sunucular.append({'ad': ad[:40], 'komut': komut[:200],
                          'argumanlar': [a[:300] for a in argumanlar][:20],
                          'env': {str(k)[:60]: str(v)[:300] for k, v in list(env.items())[:20]}})
    return {'sunucular': sunucular}


class McpSunucu:
    """Tek bir stdio MCP sunucusu."""

    def __init__(self, ad, komut, argumanlar=(), env=None):
        self.ad = ad
        self.komut = komut
        self.argumanlar = list(argumanlar)
        self.env = dict(env or {})
        self.proc = None
        self.kilit = threading.Lock()
        self.son_kullanim = 0.0
        self._kimlik = 0
        self.arac_listesi = []

    # --- süreç ------------------------------------------------------------
    def _baslat(self):
        if self.proc and self.proc.poll() is None:
            return
        ortam = dict(os.environ)
        ortam.update(self.env)
        try:
            self.proc = subprocess.Popen(
                [self.komut] + self.argumanlar, cwd=str(ROOT), env=ortam,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, encoding='utf-8', errors='replace', bufsize=1)
        except OSError as hata:
            raise ValueError(f'MCP sunucusu başlatılamadı ({self.ad}): {hata}')
        self._iste('initialize', {
            'protocolVersion': '2024-11-05', 'capabilities': {},
            'clientInfo': {'name': 'Emre', 'version': '1.0'}}, sure=BASLATMA_SANIYE)
        self._bildir('notifications/initialized', {})

    def _bildir(self, yontem, params):
        if not self.proc or self.proc.poll() is not None:
            raise ValueError('MCP sunucusu çalışmıyor.')
        self.proc.stdin.write(json.dumps({'jsonrpc': '2.0', 'method': yontem, 'params': params}) + '\n')
        self.proc.stdin.flush()

    def _iste(self, yontem, params, sure=ISTEK_SANIYE):
        if not self.proc or self.proc.poll() is not None:
            if yontem != 'initialize':
                raise ValueError('MCP sunucusu çalışmıyor.')
            # initialize çağrısı süreci başlatır
        self._kimlik += 1
        kimlik = self._kimlik
        self.proc.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': kimlik, 'method': yontem,
                                          'params': params}) + '\n')
        self.proc.stdin.flush()
        bitis = time.time() + sure
        while time.time() < bitis:
            satir = self.proc.stdout.readline()
            if not satir:
                raise ValueError(f'MCP sunucusu kapandı ({self.ad}).')
            satir = satir.strip()
            if not satir:
                continue
            try:
                veri = json.loads(satir)
            except ValueError:
                continue
            if veri.get('id') != kimlik:
                continue  # bildirim veya başka istek
            if 'error' in veri:
                hata = veri['error']
                mesaj = hata.get('message') if isinstance(hata, dict) else str(hata)
                raise ValueError(f'MCP hatası: {str(mesaj)[:200]}')
            return veri.get('result') or {}
        self.kapat()
        raise ValueError('MCP sunucusu zamanında yanıt vermedi.')

    def araclar(self):
        with self.kilit:
            self._baslat()
            sonuc = self._iste('tools/list', {})
            ham = sonuc.get('tools') or []
            self.arac_listesi = [{'ad': str(t.get('name') or '')[:80],
                                  'aciklama': str(t.get('description') or '')[:300],
                                  'girdi': t.get('inputSchema') or {}}
                                 for t in ham[:AZAMI_ARAC] if isinstance(t, dict) and t.get('name')]
            self.son_kullanim = time.time()
            return self.arac_listesi

    def cagir(self, arac, argumanlar=None):
        with self.kilit:
            self._baslat()
            sonuc = self._iste('tools/call', {'name': arac, 'arguments': argumanlar or {}})
            self.son_kullanim = time.time()
            parcalar = []
            for icerik in (sonuc.get('content') or []):
                if isinstance(icerik, dict) and icerik.get('type') == 'text':
                    parcalar.append(str(icerik.get('text') or ''))
            metin = '\n'.join(p for p in parcalar if p).strip()
            return {'metin': metin[:8000], 'hata': bool(sonuc.get('isError')), 'ham': sonuc if not metin else None}

    def kapat(self):
        proc, self.proc = self.proc, None
        if proc is None:
            return
        try:
            proc.stdin.close()
        except Exception:
            pass
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


class Yonetici:
    """Tanımlı sunucuları yönetir (tek örnek sunucu katmanında tutulur)."""

    def __init__(self, ayar_yolu=None):
        self.ayar_yolu = ayar_yolu
        self.sunucular = {}
        self.kilit = threading.Lock()

    def yenile(self):
        ayar = ayar_oku(self.ayar_yolu)
        with self.kilit:
            for ad in list(self.sunucular):
                if ad not in {s['ad'] for s in ayar['sunucular']}:
                    self.sunucular.pop(ad).kapat()
            for tanim in ayar['sunucular']:
                if tanim['ad'] not in self.sunucular:
                    self.sunucular[tanim['ad']] = McpSunucu(tanim['ad'], tanim['komut'],
                                                            tanim['argumanlar'], tanim['env'])
        return ayar

    def tanimlar(self):
        return ayar_oku(self.ayar_yolu)['sunucular']

    def durum(self):
        return [{'ad': ad, 'calisiyor': bool(s.proc and s.proc.poll() is None),
                 'arac_sayisi': len(s.arac_listesi)} for ad, s in self.sunucular.items()]

    def araclar(self):
        sonuc = []
        for ad, sunucu in list(self.sunucular.items()):
            try:
                for arac in sunucu.araclar():
                    sonuc.append({'sunucu': ad, **arac})
            except ValueError as hata:
                sonuc.append({'sunucu': ad, 'ad': '', 'hata': str(hata)})
        return sonuc

    def cagir(self, sunucu_adi, arac, argumanlar=None):
        sunucu = self.sunucular.get(sunucu_adi)
        if not sunucu:
            raise ValueError('MCP sunucusu tanımlı değil.')
        if not isinstance(argumanlar, dict):
            raise ValueError('Araç argümanları nesne olmalı.')
        return sunucu.cagir(arac, argumanlar)
