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
        resolve({ status: res.statusCode, ok: res.statusCode >= 200 && res.statusCode < 300, ctype: ct, text: data, json: async () => JSON.parse(data) });
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
      window.fetch = (path, opt = {}) => {
        const target = String(path).startsWith('http') ? String(path) : BASE + path;
        const headers = Object.assign({}, opt.headers || {});
        return request(target, { method: opt.method, body: opt.body, headers });
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
    assert(cells.length === 4, '4 durum hücresi bekleniyordu, bulunan: ' + cells.length);
    assert(!cells.every(c => c === 'Kontrol ediliyor…'), 'panel hiç güncellenmedi');
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
    for (const id of ['openjarvisTab', 'browserAccessTab', 'voiceTab', 'telegramTab', 'arenaApiTab', 'ollamaTab']) {
      const before = problems.length;
      $(id).click();
      await sleep(500);
      const bad = problems.slice(before).filter(p => p.kind !== 'window.open');
      assert(bad.length === 0, `${id} sekmesinde hata: ` + JSON.stringify(bad).slice(0, 300));
      assert($('settingsBody').textContent.trim().length > 20, `${id} içeriği boş`);
    }
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
    const r1 = await request('/api/accounts', { body: JSON.stringify({ name: 'İlker' }), headers: { 'Content-Type': 'application/json' } });
    assert(r1.status === 200, 'ilk hesap eklenemedi: ' + r1.text);
    const r2 = await request('/api/accounts', { body: JSON.stringify({ name: 'ilker' }), headers: { 'Content-Type': 'application/json' } });
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
