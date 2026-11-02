# EMRE — Proje Taraması ve Eksik Tamamlama Raporu

Tarih: 2026-11-02 · Kapsam: depodaki 29 dosyanın tamamı + çalışan sunucu üzerinde canlı HTTP testleri.

## 1. Mimari özeti

| Katman | Dosyalar | Görev |
|---|---|---|
| Arayüz | `index.html` | Tek dosya SPA: sohbet, defter, hatırlatıcı, Telegram, geliştirici, ayarlar, canvas animasyonu |
| Sunucu | `server.py` | Yalnızca standart kütüphane; `ThreadingHTTPServer` + `127.0.0.1:8765`, token (`X-Emre-Token`) + Origin kontrolü |
| Defter mantığı | `ledger_tools.py` | Ollama tool şemaları + Türkçe metinden tutar/kişi çıkarma, defter yazma |
| Ses | `ses_baglanti.py`, `ses_servisi.py`, `tts_piper_bridge.py`, `tts_piper.py`, `tts_windows.ps1`, `yerel_isci.py` | Whisper (faster-whisper) ve Piper/SAPI konuşma işçileri |
| Tarayıcı otomasyonu | `arena_bridge.py` | Playwright + Edge ile onaylı Arena soru gönderimi |
| Masaüstü | `masaustu*.py`, `openjarvis_yonet.py` | pywebview + sistem tepsisi + OpenJarvis süreç yönetimi |
| Kurulum | `*.bat`, `piper_indir.py` | Windows kurulum/başlatma betikleri |

Genel değerlendirme: mimari tutarlı ve güvenlik bilinci yüksek (token, Origin kontrolü, onay zorunluluğu, modelin "kaydettim" demesini engelleyen filtre). Eksikler daha çok **dayanıklılık, girdi doğrulama, depo hijyeni, gözlemlenebilirlik ve test** tarafındaydı.

## 2. Düzeltilen bulgular

### Kritik — depo ve gizlilik

| # | Bulgu | Dosya | Durum |
|---|---|---|---|
| 1 | `.gitignore` içinde satır birleşmesi (`*.env` + `.venv-ses/` → `*.env.venv-ses/`). Bu yüzden `.venv-ses/` **hiç yok sayılmıyordu**; yüzlerce MB sanal ortam depoya girebilirdi. | `.gitignore` | Düzeltildi |
| 2 | `arena_profile/` (Arena oturum çerezleri) yok sayılmıyordu. README "bu klasörü başkalarıyla paylaşmayın" diyor ama depoya commit edilmesini engelleyen kural yoktu. | `.gitignore` | Düzeltildi |
| 3 | `.venv-desktop/`, `kodlar/` (kullanıcı kodları), `*.sqlite3-wal`, `*.sqlite3-shm` yok sayılmıyordu. | `.gitignore` | Düzeltildi |
| 4 | `openjarvis_yol.json` kişisel makine yolunu (`C:/Users/SERVER/Desktop/OpenJarvis`) depoda tutuyordu. | `openjarvis_yol.json` | Takipten çıkarıldı + `openjarvis_yol.ornek.json` şablonu eklendi. Dosya `masaustu_ayar.py` tarafından yeniden üretilir. |

### Yüksek — hatalar

| # | Bulgu | Dosya | Durum |
|---|---|---|---|
| 5 | **SQLite bağlantı sızıntısı.** `with db() as c:` Python'da yalnızca commit eder, bağlantıyı **kapatmaz**. Canlı testte 40 istek sonunda 6 dosya tanıtıcısı açık kaldı; uzun süre çalışan sunucuda tanıtıcı tükenmesi ve kilitlenme riski. Artık `db()` bir `contextmanager`: commit → rollback → `close()`. Regresyon testi eklendi. | `server.py` | Düzeltildi |
| 6 | **Ses işçilerinde süresiz bekleme.** `worker.stdout.readline()` zaman aşımı olmadan çağrılıyordu; Whisper/Piper takıldığında kilit hiç bırakılmıyor, ses özellikleri uygulama yeniden başlatılana kadar ölü kalıyordu. Yeni `yerel_isci.py`: arka plan okuyucu + kesin zaman aşımı + takılan işçiyi öldürüp yeniden başlatma + boru uçlarını kapatma. | `yerel_isci.py`, `ses_baglanti.py`, `tts_piper_bridge.py` | Düzeltildi |
| 7 | **Ham teknik hata mesajları arayüze sızıyordu:** `{"error": "<urlopen error [Errno 111] Connection refused>"}`, `{"error": "'str' object has no attribute 'get'"}`. Artık `friendly_error()` ile Türkçe, eyleme dönük mesajlar üretiliyor. | `server.py` | Düzeltildi |
| 8 | **Girdi doğrulaması yoktu.** JSON gövdesinde dizi/nesne gelen alanlar `str()`/`int()` çağrılarında Python istisnasına yol açıyordu (`person: ["A"]`, `chat_id: {}` vb.). `text_field()` / `int_field()` yardımcıları + gövdenin JSON nesnesi olma zorunluluğu eklendi; model adı da desenle doğrulanıyor. | `server.py` | Düzeltildi |

### Orta — eksikler

| # | Bulgu | Durum |
|---|---|---|
| 9 | Telegram `getUpdates` **offset kullanmıyordu**; aynı mesaj her açılışta yeniden gösteriliyordu. Artık `update_id` imleci tutuluyor, `next_offset` dönüyor ve bot değiştirilince imleç sıfırlanıyor. | Düzeltildi |
| 10 | Arayüzdeki **"Sistem durumu → Bağlantılar" paneli tamamen statikti**; hiçbir zaman gerçek durumu göstermiyordu (her zaman "Bağlı değil"). Artık `/api/status` 15 saniyede bir yoklanıyor ve dört satır gerçek veriyle güncelleniyor. | Düzeltildi |
| 11 | Yan paneldeki **"Yaklaşan hatırlatıcılar" kartı statikti**. Artık en yakın 3 bekleyen hatırlatıcı tarih/saatiyle listeleniyor (30 sn'de bir tazelenir). | Düzeltildi |
| 12 | `/api/status` yalnızca Ollama ve Telegram'ı biliyordu. Ses kurulumu, Piper, OpenJarvis, Arena ve uygulama desteği eklendi; `version` sabiti tek yerde toplandı (`VERSION`). | Düzeltildi |
| 13 | `/favicon.ico` 404 dönüyordu. Artık `emre.ico` sunuluyor. | Düzeltildi |
| 14 | HTML/JSON yanıtlarında güvenlik başlıkları yoktu. `X-Content-Type-Options: nosniff` ve `Referrer-Policy: no-referrer` eklendi. | Düzeltildi |
| 15 | SQLite WAL/busy_timeout ayarı yoktu; eşzamanlı isteklerde `database is locked` olasılığı. `journal_mode=WAL`, `synchronous=NORMAL`, `busy_timeout=10000` eklendi. | Düzeltildi |
| 16 | Projede **hiç test ve CI yoktu.** 36 testlik `unittest` paketi + GitHub Actions iş akışı eklendi. | Eklendi |
| 17 | Bağımlılıklar yalnızca `.bat` dosyalarının içinde dağınık biçimde geçiyordu. `requirements-optional.txt` ile tek yerde belgelendi. | Eklendi |

## 3. Doğrulama

```powershell
# Windows
py -m unittest discover -s tests -t .
# Linux/macOS
python3 -m unittest discover -s tests -t .
```

Sonuç: `Ran 36 tests ... OK`

Kapsam:
- `tests/test_ledger_tools.py` — tutarın son mesajdaki rakamla eşleşmesi, kişi adının mesajda bulunması, belirsiz istekte kayıt yapılmaması, bakiye toplamı, hesap oluşturma akışı.
- `tests/test_server.py` — token/Origin yetkilendirmesi, defter ve hatırlatıcı CRUD, silme onayı, tarih/tutar doğrulaması, JSON gövde doğrulaması, `/favicon.ico`, ve **bağlantı sızıntısı regresyon testi** (açılan = kapatılan bağlantı sayısı).
- `tests/test_yerel_isci.py` — işçi ile istek/yanıt, süreç yeniden kullanımı, zaman aşımında öldürme, zaman aşımından sonra otomatik yeniden başlatma.

Ayrıca canlı sunucuda elle doğrulandı: `/`, `/api/status`, `/api/ledger`, `/api/reminders`, `/api/telegram/updates`, `/favicon.ico`, yetkisiz istek → 403, bozuk gövde → 400, Ollama kapalıyken anlaşılır hata mesajı. `index.html` içindeki iki `<script>` bloğu `node --check` ile sözdizimi denetiminden geçirildi.

## 4. Bilinçli olarak açık bırakılanlar (yol haritası)

Bunlar hata değil; kapsamı büyüteceği için bu turda yapılmadı ve README'de sınır olarak yazılı:

1. **Uyandırma sözcüğü** yok; mikrofon düğmeyle açılıyor.
2. **Arka plan hatırlatma servisi** yok: bildirim yalnızca sayfa/WebView açıkken ve bildirim izni verilmişse çalışır. Kalıcı bir Windows hizmeti/planlı görev entegrasyonu tasarım gerektirir.
3. **Kalıcı sohbet hafızası** tarayıcıda (localStorage) tutuluyor; sunucu tarafında SQLite geçmişi ve `webview` ile Chrome arasında paylaşım yok.
4. **Gerçek internet araması/özetleme** yok; "ara" komutu Google'ı yeni sekmede açar. Sunucu taraflı bir arama + özet hattı eklenebilir.
5. **Şifreleme ve çok kullanıcılı erişim** yok; `emre.sqlite3` düz metindir, yedeklerken dikkat gerekir.
6. **Telefondan erişim** yok: sunucu yalnızca `127.0.0.1` dinler (güvenlik tercihi). Uzak erişim için TLS + kimlik doğrulama + ters vekil gerekir.
7. **Arena otomasyonu** site DOM'una bağlı ve kırılgandır; `data-message-role` benzeri seçiciler değişirse yanıt bulunamaz. CAPTCHA/lisans ihlali yapılmaz.
8. **Windows üzerinde uçtan uca test edilmedi** (bu tarama Linux ortamında yapıldı): SAPI sesleri, WebView2, tepsi simgesi, `.bat` betikleri ve OpenJarvis süreç yönetimi gerçek makinede doğrulanmalı.
9. **Lisans dosyası yok**; proje kamuya açık paylaşılacaksa lisans seçilmelidir.
10. **Model tabanlı defter yazımı** kural tabanlı filtrelerle korunuyor; yine de kritik kayıtlar arayüzden doğrulanmalı (tasarım gereği defter tool'ları tek işlemle sınırlı ve tutar son mesajdaki rakamla eşleşmek zorunda).
