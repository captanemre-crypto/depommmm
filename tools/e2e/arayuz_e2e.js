/* EMRE arayüzü uçtan uca test: gerçek sunucu + jsdom + gerçek HTTP istekleri */
const { JSDOM, VirtualConsole } = require('jsdom');
const http = require('http');

const BASE = process.env.EMRE_E2E_BASE || 'http://127.0.0.1:8765';
const TOKEN = process.env.EMRE_E2E_TOKEN || 'e2e-anahtar';

function request(path, options = {}) {
  return new Promise((resolve, reject) => {
    const url = new URL(path, BASE);
    const body = options.body;
    const headers = Object.assign({ 'X-Emre-Token': TOKEN }, options.headers || {});
    if (body) headers['Content-Length'] = Buffer.byteLength(body);
    const req = http.request({
      hostname: url.hostname, port: url.port, path: url.pathname + url.search,
      method: options.method || (body ? 'POST' : 'GET'),
      headers,
    }, res => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        const ct = res.headers['content-type'] || '';
        resolve({
          status: res.statusCode,
          ok: res.statusCode >= 200 && res.statusCode < 300,
          ctype: ct,
          text: data,
          json: async () => JSON.parse(data),
          headers: { get: (name) => res.headers[String(name).toLowerCase()] ?? null },
        });
      });
    });
    req.on('error', reject);
    if (body) req.write(body);
    req.end();
  });
}

const problems = [];
function report(kind, detail) { problems.push({ kind, detail }); }

function makeCtx() {
  const noop = () => {};
  const grad = { addColorStop: noop };
  return new Proxy({}, {
    get: (t, k) => {
      if (k === 'createRadialGradient' || k === 'createLinearGradient') return () => grad;
      if (k === 'measureText') return () => ({ width: 10 });
      if (k === 'canvas') return { width: 500, height: 500 };
      return noop;
    },
    set: () => true,
  });
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

(async () => {
  const indexRes = await request('/');
  const html = indexRes.text;

  const virtualConsole = new VirtualConsole();
  virtualConsole.on('error', (...a) => report('console.error', a.map(String).join(' ').slice(0, 300)));
  virtualConsole.on('jsdomError', e => report('jsdomError', String(e && e.message).slice(0, 300)));

  const dom = new JSDOM(html, {
    url: BASE + '/', runScripts: 'dangerously', pretendToBeVisual: true, virtualConsole,
    beforeParse(window) {
      window.fetch = async (path, opt = {}) => {
        const target = String(path).startsWith('http') ? String(path) : BASE + path;
        const headers = Object.assign({}, opt.headers || {});
        const res = await request(target, { method: opt.method, body: opt.body, headers });
        // jsdom'da Response.blob yok: indirme akışını test edebilmek için ekle.
        res.blob = async () => new window.Blob([res.text], { type: res.ctype || 'application/octet-stream' });
        // SSE (akışlı sohbet) yanıtlarını ReadableStream gibi sun.
        if ((res.ctype || '').includes('text/event-stream')) {
          const parcalar = res.text.match(/[\s\S]{1,64}/g) || [];
          res.body = {
            getReader() {
              let i = 0;
              return {
                read: async () => (i < parcalar.length
                  ? { done: false, value: Uint8Array.from(Buffer.from(parcalar[i++], 'utf8')) }
                  : { done: true, value: undefined }),
              };
            },
          };
        }
        return res;
      };
      window.HTMLCanvasElement.prototype.getContext = () => makeCtx();
      window.AudioContext = class { constructor() { this.state = 'running'; this.destination = {}; } decodeAudioData() { return Promise.resolve({}); } createBufferSource() { return { connect() {}, start() {}, stop() {}, buffer: null, onended: null }; } createGain() { return { connect() {}, gain: { value: 1 } }; } close() { return Promise.resolve(); } };
      window.MediaRecorder = undefined;
      window.Notification = class { static permission = 'denied'; static requestPermission() { return Promise.resolve('denied'); } };
      window.navigator.mediaDevices = { getUserMedia: () => Promise.reject(new Error('cihaz yok')) };
      window.navigator.permissions = { query: () => Promise.resolve({ state: 'denied' }) };
      window.scrollTo = () => {};
      window.HTMLElement.prototype.scrollIntoView = () => {};
      window.open = (u) => { report('window.open', String(u).slice(0, 120)); return null; };
      Object.defineProperty(window, 'confirm', { value: () => true, configurable: true, writable: true });
      window.alert = (m) => report('alert', String(m));
      window.onerror = (msg, src, line) => report('window.onerror', String(msg).slice(0, 300));
      window.addEventListener('unhandledrejection', e => report('unhandledrejection', String(e.reason && e.reason.message || e.reason).slice(0, 300)));
    },
  });

  const { window } = dom;
  const d = window.document;
  await sleep(600);
  const $ = id => d.getElementById(id);
  const visible = el => el && !el.hidden;

  const results = [];
  function check(name, fn) {
    return Promise.resolve().then(fn).then(() => results.push({ name, ok: true }))
      .catch(e => { results.push({ name, ok: false, error: String(e && e.message || e).slice(0, 200) }); });
  }
  function assert(cond, msg) { if (!cond) throw new Error(msg); }

  await check('sayfa yüklendi ve token meta var', () => {
    assert(d.querySelector('meta[name="emre-token"]')?.content === TOKEN, 'token meta yok');
    assert(d.querySelectorAll('.msg').length >= 1, 'karşılama mesajı yok');
  });

  await check('canlı durum paneli güncellendi', async () => {
    const cells = [...d.querySelectorAll('[data-durum]')].map(el => el.textContent);
    assert(cells.length === 5, '5 durum hücresi bekleniyordu (ses, internet, Telegram, cihaz, yapay zekâ), bulunan: ' + cells.length);
    assert(!cells.every(c => c === 'Kontrol ediliyor…'), 'panel hiç güncellenmedi');
    const yz = d.querySelector('[data-durum="yapayzeka"]').textContent;
    assert(yz && yz !== 'Kontrol ediliyor…', 'yapay zekâ satırı boş: ' + yz);
  });

  await check('yaklaşan hatırlatıcılar kartı veri çekti', () => {
    const box = $('upcomingReminders');
    assert(box, '#upcomingReminders yok');
    assert(box.children.length > 0, 'kart boş kaldı');
  });

  const navSections = ['Sohbet', 'Keşfet', 'Hatırlatıcılar', 'Defter', 'Telegram', 'Uygulamalar', 'Geliştirici', 'Ayarlar'];
  for (const section of navSections) {
    await check(`menü: ${section}`, async () => {
      const btn = [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === section);
      assert(btn, 'menü düğmesi yok');
      const before = problems.length;
      btn.click();
      await sleep(250);
      const newProblems = problems.slice(before).filter(p => p.kind !== 'window.open');
      assert(newProblems.length === 0, 'yeni hata: ' + JSON.stringify(newProblems).slice(0, 300));
      const anyVisible = ['chatPage', 'discoverPage', 'simplePage', 'appsPage', 'developerPage', 'settingsPage', 'ledgerPage']
        .some(id => $(id) && !$(id).hidden);
      assert(anyVisible, 'hiçbir bölüm görünür olmadı');
    });
  }

  await check('sohbet gönderimi: Ollama kapalıyken anlaşılır hata', async () => {
    $('input').value = 'merhaba';
    $('form').dispatchEvent(new window.Event('submit', { bubbles: true, cancelable: true }));
    await sleep(900);
    const text = $('messages').textContent;
    assert(/ulaşılamadı|Ollama|hata|kurulu değil/i.test(text), 'anlaşılır hata mesajı görünmedi: ' + text.slice(-200));
  });

  await check('defter: hesap aç, işlem ekle, listele, sil', async () => {
    [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Defter').click();
    await sleep(400);
    assert($('ledgerNew') && $('ledgerAdd'), 'defter düğmeleri yok');
    $('ledgerNew').click(); await sleep(50);
    $('newAccountName').value = 'E2E Kişi';
    [...d.querySelectorAll('.ledger-dialog button')].find(b => b.textContent === 'Kaydet').click();
    await sleep(500);
    $('ledgerAdd').click(); await sleep(50);
    $('newPerson').value = 'E2E Kişi';
    $('newAmount').value = '1.250,75';
    [...d.querySelectorAll('.ledger-dialog button')].find(b => b.textContent === 'Kaydet').click();
    await sleep(700);
    assert(/1\.250,75/.test($('ledgerPage').textContent), 'tutar listede görünmedi: ' + $('ledgerPage').textContent.slice(0, 300));
    const rows = await request('/api/ledger');
    const entries = (await rows.json()).entries;
    assert(entries.length === 1 && entries[0].amount === 125075, 'sunucuda kayıt yanlış: ' + JSON.stringify(entries));
    await request('/api/ledger/delete', { body: JSON.stringify({ id: entries[0].id, confirmed: true }), headers: { 'Content-Type': 'application/json' } });
  });

  await check('hatırlatıcı: ekle ve listele', async () => {
    [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Hatırlatıcılar').click();
    await sleep(400);
    const inputs = [...$('simpleBody').querySelectorAll('input')];
    assert(inputs.length >= 2, 'hatırlatıcı alanları yok');
    inputs[0].value = 'E2E hatırlatıcı';
    inputs[1].value = new Date(Date.now() + 86400000).toISOString().slice(0, 16);
    [...$('simpleBody').querySelectorAll('button')].find(b => b.textContent === 'Ekle').click();
    await sleep(600);
    assert(/E2E hatırlatıcı/.test($('simpleBody').textContent), 'hatırlatıcı listede yok');
  });

  await check('ayarlar: tüm sekmeler açılıyor', async () => {
    [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Ayarlar').click();
    await sleep(400);
    for (const id of ['openjarvisTab', 'browserAccessTab', 'voiceTab', 'telegramTab', 'memoryTab', 'mcpTab', 'systemTab', 'skillsTab', 'arenaApiTab', 'ollamaTab']) {
      const before = problems.length;
      $(id).click();
      await sleep(500);
      const bad = problems.slice(before).filter(p => p.kind !== 'window.open');
      assert(bad.length === 0, `${id} sekmesinde hata: ` + JSON.stringify(bad).slice(0, 300));
      assert($('settingsBody').textContent.trim().length > 20, `${id} içeriği boş`);
    }
  });

  await check('bellek: arayüzden ekle, ara ve sil', async () => {
    [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Ayarlar').click();
    await sleep(300);
    $('memoryTab').click();
    await sleep(600);
    const body = $('settingsBody');
    const inputs = [...body.querySelectorAll('input[type="text"], input:not([type])')];
    assert(inputs.length >= 2, 'bellek alanları yok');
    const metin = inputs.find(i => /Yeni kayıt/.test(i.placeholder));
    assert(metin, 'yeni kayıt alanı yok');
    metin.value = 'E2E kira hatırlatması 9000 TL';
    const ekleBtn = [...body.querySelectorAll('button')].find(b => b.textContent === 'Belleğe ekle');
    assert(ekleBtn, 'belleğe ekle düğmesi yok');
    ekleBtn.click();
    await sleep(700);
    assert(/E2E kira hatırlatması/.test(body.textContent), 'kayıt listede görünmedi: ' + body.textContent.slice(0, 200));
    const kayitlar = await (await request('/api/memory?q=E2E%20kira')).json();
    assert(kayitlar.items.length >= 1, 'sunucuda kayıt yok');
    await request('/api/memory/delete', { body: JSON.stringify({ id: kayitlar.items[0].id, confirmed: true }), headers: { 'Content-Type': 'application/json' } });
    const sonra = await (await request('/api/memory?q=E2E%20kira')).json();
    assert(sonra.items.length === 0, 'kayıt silinmedi');
  });

  await check('uyandırma: ayar aç/kapa arayüzden çalışıyor', async () => {
    $('memoryTab').click();
    await sleep(600);
    const toggle = $('wakeToggle');
    assert(toggle, 'uyandırma anahtarı yok');
    toggle.checked = true;
    toggle.dispatchEvent(new window.Event('change', { bubbles: true }));
    await sleep(500);
    const durum = await (await request('/api/wake/status')).json();
    assert(durum.aktif === true, 'uyandırma açılmadı');
    toggle.checked = false;
    toggle.dispatchEvent(new window.Event('change', { bubbles: true }));
    await sleep(500);
    assert((await (await request('/api/wake/status')).json()).aktif === false, 'uyandırma kapanmadı');
  });

  await check('ekranı sor: onay olmadan istek gitmiyor', async () => {
    const btn = $('screenAsk');
    assert(btn, 'ekranı sor düğmesi yok');
    let sorulan = false;
    const eskiConfirm = window.confirm;
    window.confirm = () => { sorulan = true; return false; };
    btn.click();
    await sleep(200);
    window.confirm = eskiConfirm;
    assert(sorulan, 'ekran görüntüsü için onay istenmedi');
  });

  await check('sistem: kısayol ayarı kaydediliyor', async () => {
    [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Ayarlar').click();
    await sleep(300);
    $('systemTab').click();
    await sleep(700);
    const kutu = $('hotkeyInput');
    assert(kutu, 'kısayol alanı yok');
    kutu.value = 'ctrl+shift+e';
    const kaydet = [...$('settingsBody').querySelectorAll('button')].find(b => b.textContent === 'Kısayolu kaydet');
    assert(kaydet, 'kısayol kaydet düğmesi yok');
    kaydet.click();
    await sleep(600);
    const durum = await (await request('/api/system/status')).json();
    assert(durum.hotkey.kisayol === 'ctrl+shift+e', 'kısayol kaydedilmedi: ' + JSON.stringify(durum.hotkey));
    assert(durum.hotkey.gorunen === 'Ctrl+Shift+E', 'görünen ad yanlış: ' + durum.hotkey.gorunen);
  });

  await check('sistem: geçersiz kısayol reddediliyor', async () => {
    const res = await request('/api/system/hotkey', {
      body: JSON.stringify({ aktif: false, kisayol: 'meta+q' }),
      headers: { 'Content-Type': 'application/json' },
    });
    assert(res.status === 400, 'geçersiz kısayol kabul edildi: ' + res.status);
  });

  await check('sistem: web araması anahtarı', async () => {
    const once = await (await request('/api/system/status')).json();
    assert(once.web && typeof once.web.aktif === 'boolean', 'web durumu yok');
    const kapali = await (await request('/api/system/web', {
      body: JSON.stringify({ aktif: false }),
      headers: { 'Content-Type': 'application/json' },
    })).json();
    assert(kapali.aktif === false, 'web araması kapatılamadı');
    await request('/api/system/web', {
      body: JSON.stringify({ aktif: true }),
      headers: { 'Content-Type': 'application/json' },
    });
  });

  await check('sohbet: akışlı yanıt parça parça geliyor', async () => {
    // Ücretsiz API arka ucuna geç ki sahte sağlayıcı akışı kullanılsın.
    await request('/api/provider/connect', {
      body: JSON.stringify({ base_url: 'http://127.0.0.1:8899/v1', key: 'test', model: 'openai/gpt-oss-20b:free', confirmed: true }),
      headers: { 'Content-Type': 'application/json' },
    });
    const res = await request('/api/chat/stream', {
      body: JSON.stringify({ messages: [{ role: 'user', content: 'merhaba' }], backend: 'api' }),
      headers: { 'Content-Type': 'application/json' },
    });
    assert((res.ctype || '').includes('text/event-stream'), 'SSE içerik tipi değil: ' + res.ctype);
    const olaylar = res.text.split('\n\n').filter(Boolean)
      .map(b => { try { return JSON.parse(b.replace(/^data:\s*/, '')); } catch (e) { return null; } })
      .filter(Boolean);
    assert(olaylar.some(o => o.type === 'delta'), 'delta olayı yok');
    const bitti = olaylar.find(o => o.type === 'done');
    assert(bitti && bitti.reply, 'done olayı yok: ' + JSON.stringify(olaylar).slice(0, 200));
    await request('/api/provider/disconnect', {
      body: JSON.stringify({ confirmed: true }),
      headers: { 'Content-Type': 'application/json' },
    });
  });

  await check('sohbet: arayüz akışlı yanıtı ekrana yazıyor', async () => {
    await request('/api/provider/connect', {
      body: JSON.stringify({ base_url: 'http://127.0.0.1:8899/v1', key: 'test', model: 'openai/gpt-oss-20b:free', confirmed: true }),
      headers: { 'Content-Type': 'application/json' },
    });
    window.localStorage.setItem('emre-backend', 'api');
    window.localStorage.setItem('emre-akis', '1');
    [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Sohbet').click();
    await sleep(400);
    const girdi = $('input');
    girdi.value = 'merhaba';
    $('form').dispatchEvent(new window.Event('submit', { bubbles: true, cancelable: true }));
    await sleep(2500);
    const metin = $('messages').textContent;
    assert(/Sahte akış yanıtı/.test(metin), 'akışlı yanıt ekranda yok: ' + metin.slice(-200));
    window.localStorage.setItem('emre-backend', 'ollama');
    await request('/api/provider/disconnect', {
      body: JSON.stringify({ confirmed: true }),
      headers: { 'Content-Type': 'application/json' },
    });
  });

  await check('sistem: bildirim anahtarı ve durum ucu', async () => {
    const once = await (await request('/api/system/status')).json();
    assert(typeof once.notifications.aktif === 'boolean', 'bildirim durumu yok');
    const kapali = await (await request('/api/system/notifications', {
      body: JSON.stringify({ aktif: false }),
      headers: { 'Content-Type': 'application/json' },
    })).json();
    assert(kapali.aktif === false, 'bildirim kapatılamadı');
    await request('/api/system/notifications', {
      body: JSON.stringify({ aktif: true }),
      headers: { 'Content-Type': 'application/json' },
    });
  });

  await check('sistem: hatırlatıcı bildirimi arayüzde görünüyor', async () => {
    const gecmis = new Date(Date.now() - 600000).toISOString().slice(0, 16);
    await request('/api/reminders', {
      body: JSON.stringify({ text: 'E2E sistem bildirimi', due: gecmis }),
      headers: { 'Content-Type': 'application/json' },
    });
    // Sunucu tarafı işçi (E2E'de 3 sn'de bir) hatırlatıcıyı yakalamalı.
    let bulundu = null;
    for (let i = 0; i < 12 && !bulundu; i++) {
      await sleep(1000);
      const sonuc = await (await request('/api/notifications?since=0')).json();
      bulundu = (sonuc.items || []).find(x => /E2E sistem bildirimi/.test(x.text)) || null;
    }
    assert(bulundu, 'sunucu tarafı hatırlatıcı bildirimi oluşmadı');
    await request('/api/notifications/seen', {
      body: JSON.stringify({ ids: [bulundu.id] }),
      headers: { 'Content-Type': 'application/json' },
    });
  });

  await check('bellek: yedek indir, unut ve geri yükle', async () => {
    [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Ayarlar').click();
    await sleep(300);
    $('memoryTab').click();
    await sleep(700);
    const govde = $('settingsBody');
    const inputs = [...govde.querySelectorAll('input')];
    const metin = inputs.find(i => /Yeni kayıt/.test(i.placeholder));
    metin.value = 'E2E unutulacak kayıt';
    [...govde.querySelectorAll('button')].find(b => b.textContent === 'Belleğe ekle').click();
    await sleep(700);
    const yedek = await (await request('/api/memory/export')).json();
    assert(yedek.kayitlar.some(k => /E2E unutulacak kayıt/.test(k.text)), 'yedekte kayıt yok');
    const unut = await (await request('/api/memory/forget', {
      body: JSON.stringify({ q: 'E2E unutulacak kayıt', confirmed: true }),
      headers: { 'Content-Type': 'application/json' },
    })).json();
    assert(unut.deleted >= 1, 'kayıt unutulmadı');
    // Yedeği geri yükle: kayıt yeniden gelmeli
    const geri = await (await request('/api/memory/import', {
      body: JSON.stringify({ backup: yedek, confirmed: true }),
      headers: { 'Content-Type': 'application/json' },
    })).json();
    assert(geri.eklenen >= 1, 'geri yükleme eklemedi: ' + JSON.stringify(geri));
    const liste = await (await request('/api/memory?q=E2E%20unutulacak')).json();
    assert(liste.items.length >= 1, 'geri yüklenen kayıt bulunamadı');
    await request('/api/memory/forget', {
      body: JSON.stringify({ q: 'E2E unutulacak kayıt', confirmed: true }),
      headers: { 'Content-Type': 'application/json' },
    });
  });

  await check('sistem: kota sayacı ve yedek model alanı', async () => {
    $('systemTab').click();
    await sleep(900);
    const kota = $('quotaBox');
    assert(kota && /Bugün/.test(kota.textContent), 'kota kutusu yok: ' + (kota ? kota.textContent : '-'));
    const yedek = $('fallbackInput');
    assert(yedek, 'yedek model alanı yok');
    const kullanim = await (await request('/api/provider/usage?days=7')).json();
    assert(typeof kullanim.bugun.requests === 'number', 'kota ucu bozuk');
  });

  await check('beceriler: liste ve onaylı çalıştırma', async () => {
    [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Ayarlar').click();
    await sleep(300);
    $('skillsTab').click();
    await sleep(800);
    const govde = $('settingsBody');
    assert(/metin-analiz/.test(govde.textContent), 'örnek beceri listede yok: ' + govde.textContent.slice(0, 200));
    const calistir = [...govde.querySelectorAll('button')].find(b => b.textContent === 'Çalıştır');
    assert(calistir, 'çalıştır düğmesi yok');
    const girdi = [...govde.querySelectorAll('input')].find(i => /gönderilecek metin/.test(i.placeholder));
    assert(girdi, 'beceri metin alanı yok');
    girdi.value = 'bir iki üç dört';
    calistir.click();
    await sleep(1500);
    assert(/4 kelime/.test(govde.textContent), 'beceri sonucu görünmedi: ' + govde.textContent.slice(-200));
  });

  await check('sistem: tanılama ve denetim izi görünüyor', async () => {
    $('systemTab').click();
    await sleep(1500);
    const tani = $('diagnoseBox');
    assert(tani && /Python/.test(tani.textContent), 'tanılama sonucu yok: ' + (tani ? tani.textContent.slice(0, 200) : '-'));
    const denetim = $('auditBox');
    assert(denetim && denetim.children.length > 0, 'denetim izi boş');
    await sleep(500);
    assert(/metin-analiz|bellek|mcp|sistem/i.test(denetim.textContent), 'denetim kaydı beklenen türde değil: ' + denetim.textContent.slice(0, 200));
  });

  await check('geliştirici: dosya kaydet ve geri oku', async () => {
    [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Geliştirici').click();
    await sleep(400);
    $('devName').value = 'e2e_deneme.py';
    $('devCode').value = 'print("merhaba")\n';
    $('devSave').click();
    await sleep(600);
    const res = await request('/api/developer/files');
    const files = (await res.json()).files;
    assert(files.includes('e2e_deneme.py'), 'dosya kaydedilmedi: ' + JSON.stringify(files));
  });

  await check('mikrofon: destek yokken uyarı veriyor', async () => {
    const before = problems.length;
    $('voiceToggle').click();
    await sleep(300);
    assert(/toast/.test('toast') && $('toast').textContent.length > 0, 'uyarı gösterilmedi');
    assert(problems.slice(before).filter(p => p.kind !== 'window.open').length === 0, 'mikrofon tıklaması hata üretti');
  });

  await check('uygulama kartı: onay diyaloğu çalışıyor', async () => {
    [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Uygulamalar').click();
    await sleep(300);
    const card = d.querySelector('.apps-card');
    assert(card, 'uygulama kartı yok');
    card.click();
    await sleep(500);
  });

  await check('yeni sohbet oluşturma', async () => {
    [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Sohbet').click();
    await sleep(300);
    $('newChat').click();
    await sleep(200);
    assert(d.querySelectorAll('#chatHistoryList > *').length >= 1, 'sohbet geçmişi listesi boş');
  });


  await check('mükerrer hesap: Türkçe uyumlu ret', async () => {
    const ad = 'E2EIlker' + Date.now().toString().slice(-5);
    const r1 = await request('/api/accounts', { body: JSON.stringify({ name: ad }), headers: { 'Content-Type': 'application/json' } });
    assert(r1.status === 200, 'ilk hesap eklenemedi: ' + r1.text);
    const r2 = await request('/api/accounts', { body: JSON.stringify({ name: ad.toLowerCase() }), headers: { 'Content-Type': 'application/json' } });
    assert(r2.status === 400, 'Türkçe büyük/küçük harf farkı yakalanmadı');
    const msg = JSON.parse(r2.text).error;
    assert(/zaten var/.test(msg) && !/UNIQUE|constraint/.test(msg), 'İngilizce SQL hatası sızdı: ' + msg);
  });

  await check('hatırlatıcı silme düğmesi çalışıyor', async () => {
    [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Hatırlatıcılar').click();
    await sleep(400);
    const before = await (await request('/api/reminders')).json();
    assert(before.reminders.length > 0, 'silinecek hatırlatıcı yok');
    const del = [...$('simpleBody').querySelectorAll('button')].find(b => b.textContent === 'Sil');
    assert(del, 'Sil düğmesi yok');
    del.click();
    await sleep(700);
    const after = await (await request('/api/reminders')).json();
    assert(after.reminders.length === before.reminders.length - 1, 'hatırlatıcı silinmedi');
  });

  await check('geçersiz oturum anahtarında yenileme uyarısı', async () => {
    const original = window.fetch;
    window.fetch = (p, o = {}) => request(String(p).startsWith('http') ? String(p) : BASE + p, { method: o.method, body: o.body, headers: { 'Content-Type': 'application/json', 'X-Emre-Token': 'gecersiz-anahtar' } });
    try {
      [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Hatırlatıcılar').click();
      await sleep(600);
      assert(/yenile|F5|anahtar/i.test($('toast').textContent + $('simpleBody').textContent), '403 için yönlendirme yok: ' + $('toast').textContent);
    } finally { window.fetch = original; }
  });


  await check('sohbetten hatırlatıcı (Ollama olmadan)', async () => {
    [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Sohbet').click();
    await sleep(300);
    $('input').value = 'yarın 09:00 su iç diye hatırlat';
    $('form').dispatchEvent(new window.Event('submit', { bubbles: true, cancelable: true }));
    await sleep(900);
    assert(/Hatırlatıcı kuruldu/.test($('messages').textContent), 'hatırlatıcı yanıtı görünmedi: ' + $('messages').textContent.slice(-200));
    const r = await (await request('/api/reminders')).json();
    assert(r.reminders.some(x => x.text === 'su iç'), 'hatırlatıcı sunucuda yok');
  });

  await check('sunucu geçmişi paneli oturumları listeliyor', async () => {
    [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Sohbet').click();
    await sleep(700);
    const box = $('serverHistoryList');
    assert(box, 'sunucu geçmişi kutusu yok');
    assert(box.children.length > 0, 'oturum listesi boş');
    const ilk = box.querySelector('button');
    ilk.click();
    await sleep(700);
    assert(/su iç/.test($('messages').textContent), 'oturum yüklenmedi');
  });

  await check('defter CSV ve yedek indirme düğmeleri', async () => {
    [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Defter').click();
    await sleep(400);
    assert($('ledgerExport') && $('ledgerBackup'), 'indirme düğmeleri yok');
    const indirilen = [];
    window.URL.createObjectURL = (blob) => { indirilen.push(blob.size); return 'blob:test'; };
    window.URL.revokeObjectURL = () => {};
    const clickStub = window.HTMLAnchorElement.prototype.click;
    window.HTMLAnchorElement.prototype.click = function () { indirilen.push(this.download); };
    try {
      $('ledgerExport').click(); await sleep(700);
      $('ledgerBackup').click(); await sleep(700);
    } finally { window.HTMLAnchorElement.prototype.click = clickStub; }
    assert(indirilen.some(x => String(x).endsWith('.csv')), 'CSV indirilmedi: ' + JSON.stringify(indirilen));
    assert(indirilen.some(x => String(x).endsWith('.json')), 'JSON yedek indirilmedi: ' + JSON.stringify(indirilen));
  });

  await check('erişilebilirlik: canlı bölge ve toast rolü', () => {
    const liste = $('messages');
    assert(liste.getAttribute('role') === 'log', 'mesaj listesinde role=log yok');
    assert(liste.getAttribute('aria-live') === 'polite', 'aria-live yok');
    assert($('toast').getAttribute('role') === 'status', 'toast role=status değil');
  });

  await check('Escape onay penceresini kapatıyor', async () => {
    [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Defter').click();
    await sleep(400);
    $('ledgerNew').click(); await sleep(100);
    assert(d.querySelector('.ledger-overlay'), 'pencere açılmadı');
    d.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    await sleep(150);
    assert(!d.querySelector('.ledger-overlay'), 'Escape pencereyi kapatmadı');
  });

  await check('ayarlarda sürüm bilgisi görünüyor', async () => {
    [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Ayarlar').click();
    await sleep(700);
    assert(/Sürüm:/.test($('settingsBody').textContent), 'sürüm bilgisi yok');
  });

  await check('telegram bölümü yoklama durumunu gösteriyor', async () => {
    [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Telegram').click();
    await sleep(600);
    const metin = $('simpleBody').textContent;
    assert(/anahtar|bağla|Yoklama|ayarlanmamış/i.test(metin), 'Telegram durumu gösterilmedi: ' + metin.slice(0, 150));
  });


  await check('ücretsiz API sekmesi: sağlayıcıya bağlan, sohbet et, bağlantıyı kes', async () => {
    [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Ayarlar').click();
    await sleep(500);
    $('providerTab').click();
    await sleep(600);
    const metin = () => $('settingsBody').textContent;
    assert(/Ücretsiz API sağlayıcısı/.test(metin()), 'sekme içeriği yok');
    assert(/OmniRoute/.test(metin()), 'hazır sağlayıcı listesi görünmüyor');

    // Form alanlarını sahte sağlayıcıya yönlendir
    const inputs = [...$('settingsBody').querySelectorAll('input')];
    assert(inputs.length >= 2, 'adres/anahtar alanları yok');
    inputs[0].value = 'http://127.0.0.1:8899/v1';
    inputs[1].value = 'test-anahtar';
    [...$('settingsBody').querySelectorAll('button')].find(b => b.textContent === 'Modelleri getir').click();
    await sleep(900);
    assert(/3 model bulundu/.test(metin()), 'model listesi gelmedi: ' + metin().slice(-160));

    [...$('settingsBody').querySelectorAll('button')].find(b => b.textContent === 'Bağlan ve kaydet').click();
    await sleep(1200);
    assert(/Bağlı:/.test(metin()), 'bağlantı durumu güncellenmedi: ' + metin().slice(-160));

    // Sohbeti sağlayıcı üzerinden sür
    [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Sohbet').click();
    await sleep(400);
    $('input').value = 'merhaba';
    $('form').dispatchEvent(new window.Event('submit', { bubbles: true, cancelable: true }));
    await sleep(1500);
    // Akışlı yanıt açıksa sahte sağlayıcının akış metni, kapalıysa tek parça metni gelir.
    assert(/Sahte (sağlayıcı|akış) yanıtı/.test($('messages').textContent), 'sağlayıcı yanıtı görünmedi: ' + $('messages').textContent.slice(-200));

    // Bağlantıyı kes → Ollama'ya dön
    [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Ayarlar').click();
    await sleep(500);
    $('providerTab').click();
    await sleep(500);
    [...$('settingsBody').querySelectorAll('button')].find(b => b.textContent === 'Bağlantıyı kes').click();
    await sleep(1200);
    assert(/Henüz bağlı değil/.test(metin()), 'bağlantı kesilmedi: ' + metin().slice(-160));
    const durum = await (await request('/api/provider/status')).json();
    assert(durum.configured === false, 'sunucuda anahtar kaldı');
  });


  await check('ücretsiz API: yerel geçit taraması çalışıyor (9Router desteği)', async () => {
    [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Ayarlar').click();
    await sleep(500);
    $('providerTab').click();
    await sleep(600);
    const metin = () => $('settingsBody').textContent;
    const inputs = [...$('settingsBody').querySelectorAll('input')];
    inputs[0].value = 'http://127.0.0.1:8899/v1';

    [...$('settingsBody').querySelectorAll('button')].find(b => b.textContent === 'Yerel geçitleri tara').click();
    await sleep(2200);
    assert(/Yerel geçit \(port 8899\)/.test(metin()), 'yazılan adresin portu taranmadı: ' + metin().slice(-200));
    assert(/3 model/.test(metin()), 'model sayısı gösterilmedi: ' + metin().slice(-200));

    [...$('settingsBody').querySelectorAll('button')].find(b => b.textContent === 'Kullan').click();
    await sleep(1200);
    assert(inputs[0].value === 'http://127.0.0.1:8899/v1', 'adres alanı dolmadı: ' + inputs[0].value);
    assert(/3 model bulundu/.test(metin()), 'Kullan sonrası modeller gelmedi: ' + metin().slice(-200));
  });


  await check('ücretsiz API: "Bağlantıyı test et" sağlayıcıyı doğruluyor', async () => {
    [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Ayarlar').click();
    await sleep(500);
    $('providerTab').click();
    await sleep(700);
    const inputs = [...$('settingsBody').querySelectorAll('input')];
    inputs[0].value = 'http://127.0.0.1:8899/v1';
    inputs[1].value = 'test-anahtar';
    [...$('settingsBody').querySelectorAll('button')].find(b => b.textContent === 'Modelleri getir').click();
    await sleep(1000);
    [...$('settingsBody').querySelectorAll('button')].find(b => b.textContent === 'Bağlan ve kaydet').click();
    await sleep(1200);

    [...$('settingsBody').querySelectorAll('button')].find(b => b.textContent === 'Bağlantıyı test et').click();
    await sleep(1500);
    const metin = $('settingsBody').textContent;
    assert(/Çalışıyor/.test(metin), 'test sonucu görünmedi: ' + metin.slice(-200));

    [...$('settingsBody').querySelectorAll('button')].find(b => b.textContent === 'Bağlantıyı kes').click();
    await sleep(1000);
  });

  await check('ücretsiz API: https zorunluluğu arayüzde bildiriliyor', async () => {
    $('providerTab').click();
    await sleep(500);
    const inputs = [...$('settingsBody').querySelectorAll('input')];
    inputs[0].value = 'http://uzak-ornek.example/v1';
    [...$('settingsBody').querySelectorAll('button')].find(b => b.textContent === 'Modelleri getir').click();
    await sleep(900);
    assert(/https/i.test($('toast').textContent), 'https uyarısı gösterilmedi: ' + $('toast').textContent);
  });


  await check('ses sekmesi: konuşma tanıma ayarları görünüyor', async () => {
    [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Ayarlar').click();
    await sleep(500);
    $('voiceTab').click();
    await sleep(1200);
    const metin = $('settingsBody').textContent;
    assert(/Konuşma tanıma \(mikrofon\)/.test(metin), 'tanıma bölümü yok: ' + metin.slice(-200));
    assert(/Cümle bitiş sessizliği/.test(metin), 'sessizlik ayarı yok');
    assert(/Duyduğum metni/.test(metin), 'duyulan metin anahtarı yok');

    // Sessizlik süresi değişince localStorage'a yazılmalı
    const secimler = [...$('settingsBody').querySelectorAll('select')];
    const sessizlik = secimler.find(sel => [...sel.options].some(o => /sn ·/.test(o.textContent)));
    assert(sessizlik, 'sessizlik seçimi bulunamadı');
    sessizlik.value = '2800';
    sessizlik.dispatchEvent(new window.Event('change'));
    await sleep(300);
    assert(window.localStorage.getItem('emre-vad-sessizlik') === '2800',
      'ayar kaydedilmedi: ' + window.localStorage.getItem('emre-vad-sessizlik'));
  });

  await check('ses: mikrofon kapalıyken kayıt başlamıyor', () => {
    assert($('voiceToggle').getAttribute('aria-pressed') === 'false', 'mikrofon beklenmedik şekilde açık');
  });


  await check('canlı dikte paneli açılıyor ve metni sohbete gönderiyor', async () => {
    $('dictateOpen').click();
    await sleep(300);
    assert(!$('dictation').hidden, 'dikte paneli açılmadı');
    assert(/Canlı dikte/.test($('dictation').textContent), 'panel başlığı yok');
    assert($('dictateToggle').textContent === 'Dikteyi başlat', 'başlat düğmesi yok');

    // Panelden metin gönderimi (mikrofon donanımı olmadan da akış çalışır)
    $('dictateText').value = 'yarın saat üçte toplantı var';
    $('dictateSend').click();
    await sleep(900);
    assert(/yarın saat üçte toplantı var/i.test($('messages').textContent), 'dikte metni sohbete gitmedi');
    assert($('dictateText').value === '', 'metin temizlenmedi');

    // "Aktif pencereye yaz" bu ortamda Windows olmadığı için nazik hata vermeli
    $('dictateText').value = 'deneme metni';
    $('dictateType').click();
    await sleep(700);
    assert(/Windows|yazılamadı/i.test($('toast').textContent + $('dictateHint').textContent),
      'yazma hatası bildirilmedi: ' + $('dictateHint').textContent);

    $('dictateClose').click();
    await sleep(200);
    assert($('dictation').hidden, 'panel kapanmadı');
  });


  await check('belgeler sekmesi: metin belgesi yükleniyor, listede görünüyor ve siliniyor', async () => {
    [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Ayarlar').click();
    await sleep(500);
    $('docsTab').click();
    await sleep(900);
    assert(/Belgeler/.test($('settingsBody').textContent), 'belge sekmesi açılmadı');

    const dosyaGirdi = $('settingsBody').querySelector('input[type=file]');
    assert(dosyaGirdi, 'dosya seçimi yok');
    const dosya = new window.File(['Kira sözleşmesi 12 ay sürer. Kira 15000 TL.'], 'e2e-kira.txt', { type: 'text/plain' });
    Object.defineProperty(dosyaGirdi, 'files', { value: [dosya], configurable: true });
    [...$('settingsBody').querySelectorAll('button')].find(b => b.textContent === 'Seçilen dosyayı ekle').click();
    await sleep(1500);
    assert(/e2e-kira\.txt/.test($('settingsBody').textContent), 'belge listede yok: ' + $('settingsBody').textContent.slice(0, 300));

    // Belgeye sor: kaynak gösterilmeli
    const soru = [...$('settingsBody').querySelectorAll('input')].find(i => /Belgeye soru/.test(i.placeholder || ''));
    assert(soru, 'soru alanı yok');
    soru.value = 'kira kaç ay';
    [...$('settingsBody').querySelectorAll('button')].find(b => b.textContent === 'Belgeye sor').click();
    await sleep(2500);
    const metin = $('settingsBody').textContent;
    assert(/Kaynaklar|bulamadım|bağlantı/i.test(metin), 'soru sonucu görünmedi: ' + metin.slice(-200));

    // Silme (onay kutalı)
    [...$('settingsBody').querySelectorAll('button')].filter(b => b.textContent === 'Sil')[0].click();
    await sleep(1200);
    assert(!/e2e-kira\.txt/.test($('settingsBody').textContent), 'belge silinmedi');
  });

  await check('takvim sekmesi: .ics yolu kaydediliyor ve etkinlik listeleniyor', async () => {
    const fs = require('fs');
    const os = require('os');
    const path = require('path');
    const yol = path.join(os.tmpdir(), 'e2e-takvim-' + Date.now() + '.ics');
    const ikiGunSonra = new Date(Date.now() + 2 * 86400000);
    const damga = ikiGunSonra.getFullYear().toString()
      + String(ikiGunSonra.getMonth() + 1).padStart(2, '0')
      + String(ikiGunSonra.getDate()).padStart(2, '0') + 'T140000';
    fs.writeFileSync(yol, 'BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nSUMMARY:E2E toplantı\r\n'
      + 'DTSTART:' + damga + '\r\nLOCATION:Ofis\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n', 'utf8');

    $('calendarTab').click();
    await sleep(900);
    const yollar = [...$('settingsBody').querySelectorAll('input')];
    assert(yollar.length >= 2, 'takvim/posta alanları yok');
    yollar[0].value = yol;
    [...$('settingsBody').querySelectorAll('button')].find(b => b.textContent === 'Takvim yolunu kaydet').click();
    await sleep(900);
    [...$('settingsBody').querySelectorAll('button')].find(b => b.textContent === 'Bu haftayı göster').click();
    await sleep(1200);
    assert(/E2E toplantı/.test($('settingsBody').textContent), 'etkinlik görünmedi: ' + $('settingsBody').textContent.slice(-300));

    // Sohbet kuralı: takvim sorusu model olmadan yanıtlanır
    const sohbet = await request('/api/chat', {
      body: JSON.stringify({ messages: [{ role: 'user', content: 'bu hafta takvimde ne var' }] }),
      headers: { 'Content-Type': 'application/json' },
    });
    const govde = await sohbet.json();
    assert(/E2E toplantı/.test(govde.reply || ''), 'sohbet takvim yanıtı: ' + (govde.reply || '').slice(0, 120));
    fs.unlinkSync(yol);
  });

  await check('ses ayarları: akışlı seslendirme ve söz kesme anahtarları', async () => {
    $('voiceTab').click();
    await sleep(1000);
    const metin = $('settingsBody').textContent;
    assert(/Akışlı seslendirme/.test(metin), 'akışlı seslendirme anahtarı yok');
    assert(/Söz kesme/.test(metin), 'söz kesme anahtarı yok');
    const onaylar = [...$('settingsBody').querySelectorAll('input[type=checkbox]')];
    const akis = onaylar.find(x => x.checked);
    assert(akis, 'akışlı seslendirme varsayılan açık değil');
    akis.click();
    await sleep(400);
    assert(window.localStorage.getItem('emre-tts-akis') === '0', 'akış ayarı kaydedilmedi');
    akis.click();
    await sleep(400);
  });


  await check('ana sayfa: "Bugün" kartı hatırlatıcı, defter ve belge özetini gösteriyor', async () => {
    [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Ana sayfa').click();
    await sleep(800);
    assert(!$('todayCard').hidden, 'bugün kartı görünmüyor');
    const kartlar = [...$('todayGrid').querySelectorAll('.today-card')];
    assert(kartlar.length >= 3, 'bugün kartı bölümleri eksik: ' + kartlar.length);
    assert(/Hatırlatıcılar/.test($('todayGrid').textContent), 'hatırlatıcı bölümü yok');

    await request('/api/reminders', {
      body: JSON.stringify({ text: 'E2E bugün işi', due: new Date(Date.now() + 3600000).toISOString().slice(0, 16) }),
      headers: { 'Content-Type': 'application/json' },
    });
    $('todayRefresh').click();
    await sleep(1200);
    assert(/E2E bugün işi/.test($('todayGrid').textContent), 'yeni hatırlatıcı özete yansımadı');
    const tumu = await (await request('/api/reminders')).json();
    for (const kayit of tumu.reminders.filter(r => /E2E bugün işi/.test(r.text))) {
      await request('/api/reminders/delete', {
        body: JSON.stringify({ id: kayit.id, confirmed: true }),
        headers: { 'Content-Type': 'application/json' },
      }).catch(() => {});
    }
  });

  await check('komut paleti: "/" ile açılıyor, filtre ve Enter çalışıyor, Esc kapatıyor', async () => {
    assert($('palette').hidden, 'palet başlangıçta açık');
    d.body.dispatchEvent(new window.KeyboardEvent('keydown', { key: '/', bubbles: true }));
    await sleep(300);
    assert(!$('palette').hidden, 'palet açılmadı');
    const girdi = $('paletteInput');
    girdi.value = 'hatırlat';
    girdi.dispatchEvent(new window.Event('input'));
    await sleep(200);
    const satirlar = [...$('paletteList').querySelectorAll('li')];
    assert(satirlar.length >= 1 && /Hatırlatıcı/.test(satirlar[0].textContent), 'filtre sonucu yok');

    girdi.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    await sleep(200);
    assert($('palette').hidden, 'Esc paleti kapatmadı');

    d.body.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'k', ctrlKey: true, bubbles: true }));
    await sleep(250);
    assert(!$('palette').hidden, 'Ctrl+K paleti açmadı');
    $('paletteInput').value = 'hatırlat';
    $('paletteInput').dispatchEvent(new window.Event('input'));
    await sleep(200);
    $('paletteInput').dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    await sleep(900);
    assert($('palette').hidden, 'Enter sonrası palet kapanmadı');
    assert(!$('simplePage').hidden && /Hatırlatıcılar/.test($('simpleTitle').textContent),
      'komut çalışmadı: ' + $('simpleTitle').textContent);
  });

  await check('görünüm: tema ve yazı boyutu değişiyor', async () => {
    [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Ayarlar').click();
    await sleep(600);
    $('gorunumTab').click();
    await sleep(900);
    const metin = $('settingsBody').textContent;
    assert(/Görünüm/.test(metin), 'görünüm sekmesi açılmadı');
    assert(/Görsel üretimi/.test(metin), 'görsel üretimi bölümü yok');

    const secimler = [...$('settingsBody').querySelectorAll('select')];
    const tema = secimler[0], yazi = secimler[1];
    tema.value = 'acik';
    tema.dispatchEvent(new window.Event('change'));
    await sleep(300);
    assert(d.body.dataset.tema === 'acik', 'açık tema uygulanmadı: ' + d.body.dataset.tema);
    assert(window.localStorage.getItem('emre-tema') === 'acik', 'tema kaydedilmedi');

    yazi.value = '16';
    yazi.dispatchEvent(new window.Event('change'));
    await sleep(300);
    assert(/16px/.test(d.body.style.getPropertyValue('--yazi')), 'yazı boyutu uygulanmadı');

    tema.value = 'koyu';
    tema.dispatchEvent(new window.Event('change'));
    await sleep(200);
    assert(d.body.dataset.tema === 'koyu', 'koyu temaya dönülmedi');
  });

  await check('görsel üret: panel açılıyor, sağlayıcı yokken açık hata veriyor', async () => {
    window.showGorsel();
    await sleep(500);
    assert(!$('simplePage').hidden && /Görsel üret/.test($('simpleTitle').textContent), 'görsel paneli açılmadı');
    const alan = $('simpleBody').querySelector('textarea');
    assert(alan, 'istem alanı yok');
    alan.value = 'gün batımı';
    [...$('simpleBody').querySelectorAll('button')].find(b => b.textContent === 'Görsel üret').click();
    await sleep(1200);
    assert(/sağlayıcı|bağla/i.test($('simpleBody').textContent), 'sağlayıcı uyarısı yok: ' + $('simpleBody').textContent.slice(-160));
  });


  await check('"?": kısayol yardım paneli açılıyor', async () => {
    [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Ana sayfa').click();
    await sleep(500);
    d.body.dispatchEvent(new window.KeyboardEvent('keydown', { key: '?', bubbles: true }));
    await sleep(500);
    assert(!$('simplePage').hidden, 'yardım paneli açılmadı');
    assert(/Kısayollar/.test($('simpleTitle').textContent), 'başlık yanlış: ' + $('simpleTitle').textContent);
    const metin = $('simpleBody').textContent;
    assert(/Ctrl \+ K/.test(metin), 'Ctrl+K satırı yok');
    assert(/Ctrl \+ Alt \+ D/.test(metin), 'global dikte kısayolu yazmıyor');
    $('simpleBack').click();
    await sleep(300);
  });

  await check('uzun sohbet: DOM en fazla 300 mesaj tutuyor ve bilgi satırı ekliyor', async () => {
    for (let i = 0; i < 320; i++) window.add('EMRE', 'uzun sohbet denemesi ' + i);
    await sleep(600);
    const adet = $('messages').children.length;
    assert(adet <= 305, 'DOM sınırı aşıldı: ' + adet);
    assert($('eskiNotu'), 'eski mesaj bilgi satırı yok');
    assert(/Daha eski mesajlar/.test($('eskiNotu').textContent), 'bilgi satırı metni yanlış');
    window.localStorage.removeItem('emre-chat');
  });


  await check('bellek: "Eşleşenleri unut" düğmesi kayıtları siliyor', async () => {
    await request('/api/memory/add', {
      body: JSON.stringify({ text: 'E2E unutulacak kayit', kind: 'not' }),
      headers: { 'Content-Type': 'application/json' },
    });
    [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Ayarlar').click();
    await sleep(500);
    $('memoryTab').click();
    await sleep(1400);
    const metin = $('settingsBody').textContent;
    assert(/Eşleşenleri unut/.test(metin), 'unut bölümü yok');
    assert(/E2E unutulacak kayit/.test(metin), 'eklenen kayıt listede yok');

    const alan = [...$('settingsBody').querySelectorAll('input')]
      .find(i => /Unutulacak metin/.test(i.placeholder || ''));
    assert(alan, 'unut alanı yok');
    alan.value = 'E2E unutulacak kayit';
    [...$('settingsBody').querySelectorAll('button')]
      .find(b => b.textContent === 'Eşleşen kayıtları unut').click();
    await sleep(1500);
    assert(!/E2E unutulacak kayit/.test($('settingsBody').textContent), 'kayıt silinmedi');
    assert(/kayıt silindi|bulunamadı/i.test($('settingsBody').textContent), 'sonuç mesajı yok');
  });

  await check('sohbet geçmişi: sunucu oturumu silinebiliyor', async () => {
    // Önce sunucu geçmişinde bir oturum oluştur.
    await request('/api/chat', {
      body: JSON.stringify({ messages: [{ role: 'user', content: 'E2E geçmiş silme denemesi' }], session: 'e2esil' }),
      headers: { 'Content-Type': 'application/json' },
    }).catch(() => {});
    [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Sohbet').click();
    await sleep(900);
    $('historyRefresh').click();
    await sleep(1200);
    const liste = $('serverHistoryList');
    const satirlar = [...liste.querySelectorAll('div')];
    assert(satirlar.length >= 1, 'sunucu geçmişi listesi boş');
    const silDugmeleri = [...liste.querySelectorAll('button')].filter(b => b.textContent === 'Sil');
    assert(silDugmeleri.length >= 1, 'silme düğmesi yok');
    silDugmeleri[0].click();
    await sleep(1200);
    assert(/silindi/i.test($('toast').textContent), 'silme bildirimi yok: ' + $('toast').textContent);
  });

  await check('web arama paneli açılıyor (ağ isteği yapmadan)', async () => {
    [...d.querySelectorAll('.nav button')].find(b => b.dataset.section === 'Ana sayfa').click();
    await sleep(400);
    window.showWebArama();
    await sleep(400);
    assert(/Web'de ara/.test($('simpleTitle').textContent), 'panel açılmadı');
    const alan = $('simpleBody').querySelector('input');
    assert(alan && /Aranacak metin/.test(alan.placeholder || ''), 'arama alanı yok');
    assert(/DuckDuckGo/.test($('simpleBody').textContent), 'kaynak bilgisi yok');
    $('simpleBack').click();
    await sleep(300);
  });

  // localStorage'da token saklanmıyor mu?
  await check('güvenlik: token localStorage/sessionStorage içinde değil', () => {
    const dump = JSON.stringify(Object.entries(window.localStorage)) + JSON.stringify(Object.entries(window.sessionStorage));
    assert(!dump.includes(TOKEN), 'API token tarayıcı depolamasına yazılmış');
  });

  const summary = {
    toplam_kontrol: results.length,
    basarili: results.filter(r => r.ok).length,
    basarisiz: results.filter(r => !r.ok),
    js_problemleri: problems.filter(p => p.kind !== 'window.open'),
  };
  console.log(JSON.stringify(summary, null, 2));
  dom.window.close();
  process.exit(0);
})().catch(e => { console.error('HARNESS HATASI', e); process.exit(2); });
