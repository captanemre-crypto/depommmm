# EMRE — Kalan Eksiklerin Tamamlanması (3. tur)

Tarih: 2026-11-02 · Önceki raporlar: `DENETIM.md` (statik), `E2E_DENETIM.md` (uçtan uca)
Bu turda `E2E_DENETIM.md` §3'te listelenen eksiklerin uygulanabilir olanları kapatıldı.

## 1. Tamamlanan maddeler

| Kod | Eksik | Yapılan | Doğrulama |
|---|---|---|---|
| **A1** | Sohbetten hatırlatıcı oluşturulamıyordu ("bu işlem henüz yapılmadı" ölü ucu) | Yeni `zaman_ayristir.py` (Türkçe tarih/saat ayrıştırma) + `hatirlatici.py` (kural tabanlı akış) + `reminder_create` model aracı. Desteklenen biçimler: `yarın 09:00`, `bugün 18:30`, `3 gün sonra saat 18:00`, `5 dk sonra`, `yarım saat sonra`, `15 Kasım 14:30`, `15.11.2026 14:30`, `pazartesi sabah 9`, `akşam 8`, `gece 11`. Belirsiz/geçmiş zaman → kayıt yok + örnekli uyarı. Aynı cümlede defter işlemi varsa ikisi birlikte yapılır. **Ollama kapalıyken de çalışır.** | `tests/test_zaman_ayristir.py` (11), `tests/test_hatirlatici.py` (7), `test_server.test_chat_creates_reminder_without_ollama`, E2E "sohbetten hatırlatıcı" |
| **A4** | Sunucu taraflı sohbet geçmişi yok | `messages` tablosu; `/api/chat` mesajları oturum kimliğiyle saklar; `GET /api/history` (oturum listesi), `GET /api/history?session=…`, `POST /api/history/delete`. Arayüzde "Sunucu geçmişi" paneli; oturuma tıklayınca mesajlar yüklenir. | `test_chat_history_is_stored`, E2E "sunucu geçmişi paneli" |
| **A5** | Defter dışa aktarma/yedekleme yok | `GET /api/ledger/export?format=csv\|json` (`;` ayırıcı + UTF-8 BOM, `1.250,75` biçimi) ve `GET /api/backup` (hesaplar + defter + hatırlatıcılar + geçmiş). Defter sayfasında **⤓ CSV** ve **⤓ Yedek** düğmeleri. | `test_csv_export`, `test_backup_contains_all_tables`, E2E "CSV ve yedek indirme" |
| **A6** | Defter kayıtlarında denetim izi yok | `ledger.source` ve `ledger.raw_text` kolonları; açılışta otomatik `ALTER TABLE` migrasyonu (eski veritabanları bozulmaz). | Yeni kolonlar `test_backup_contains_all_tables` çıktısında |
| **A8** | Telegram mesajları yalnızca sayfa açıkken çekiliyordu; offset bellekte | Yeni `telegram_bot.py`: uzun yoklama yapan arka plan iş parçacığı, mesajlar ve offset **veritabanında**, okunmamış sayacı, `mark-read` ve `poll` uçları. Yeniden başlatmada mesaj tekrarı yok. | `test_telegram_inbox_requires_token`, `/api/status` → `telegram` alt nesnesi, E2E "telegram bölümü" |
| **C1–C3** | Erişilebilirlik | Mesaj listesine `role="log" aria-live="polite"`, toast'a `role="status"`, bölüm değişiminde başlığa odak (`tabindex="-1"`), `Esc` ile onay penceresini kapatma. | E2E "erişilebilirlik" ve "Escape" kontrolleri |
| **C7** | Sürüm bilgisi görünmüyordu | Ayarlar > Ollama sekmesinde `Sürüm: …` ve okunmamış Telegram sayısı. `/api/status` sürümü tek sabitten (`VERSION`). | E2E "ayarlarda sürüm bilgisi" |
| **B3** | CSP yok | `Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; …; frame-ancestors 'none'; base-uri 'none'` | `test_csp_header_present` |
| **D2** | Arena köprüsü test edilmiyordu | Sahte Playwright katmanı ile durum makinesi testleri: hazır olmadan gönderim reddi, uzunluk doğrulaması, Playwright yok → anlaşılır hata, yanıtın yakalanması, yanıt bulunamazsa uyarı. Testler için `ANSWER_TIMEOUT_SECONDS`/`STABLE_SECONDS` sabitleri dışa açıldı. | `tests/test_arena_bridge.py` (5) |
| **D3** | Lint/format yapılandırması yok | `pyproject.toml` + ruff kuralları; CI'da `ruff check .` zorunlu adım. Kod tabanı temiz. | `ruff check .` → *All checks passed* |
| **D4** | Model indiriminde doğrulama yok | `piper_indir.py` yeniden yazıldı: boyut + JSON yapısı kontrolü, SHA-256 (TOFU) kaydı ve karşılaştırması, atomik `.part` indirme. | `tests/test_piper_indir.py` (5) |
| **D6** | `/api/ledger` sayfalanmıyordu | `limit`/`offset` (varsayılan 500, üst sınır 2000) + `total` alanı; geçersiz parametre → 400. | `test_ledger_pagination` |
| **D7** | Her istekte `CREATE TABLE` | Şema ve migrasyon süreç başına bir kez (`_init_schema` + `_INITIALIZED`). | Tüm sunucu testleri |
| **C6** | Canvas animasyonu CPU tüketimi | İncelendi: 33 ms kare sınırı (≈30 FPS) ve `prefers-reduced-motion` zaten vardı; ek değişiklik gerekmedi. | Kod incelemesi |

Ek olarak: **`/api/chat` sıralaması düzeltildi** — Ollama model kontrolü kural tabanlı işlemlerden *sonra* yapılıyor; böylece Ollama kapalıyken defter/hatırlatıcı komutları çalışır (öncesinde "Yerel servise ulaşılamadı" hatası veriyordu).

## 2. Test durumu

```bash
ruff check .                                  # All checks passed
python3 -m unittest discover -s tests -t .    # Ran 80 tests ... OK
cd tools/e2e && npm test                      # 30/30 kontrol, JS hatası yok
```

| Paket | Test sayısı |
|---|---|
| `tests/test_server.py` (HTTP) | 30 |
| `tests/test_ledger_tools.py` | 15 |
| `tests/test_zaman_ayristir.py` | 11 |
| `tests/test_hatirlatici.py` | 7 |
| `tests/test_arena_bridge.py` | 5 |
| `tests/test_piper_indir.py` | 5 |
| `tests/test_yerel_isci.py` | 7 |

E2E paketi: 30 kontrol (menü, defter, hatırlatıcı, sohbetten hatırlatıcı, sunucu geçmişi, CSV/yedek indirme, ayarlar sekmeleri, geliştirici, mikrofon, 403, erişilebilirlik, Escape, sürüm, Telegram durumu, token'ın depolanmaması).

## 3. Bilinçli olarak açık bırakılanlar

| Kod | Eksik | Neden yapılmadı | Öneri |
|---|---|---|---|
| **A2** | Web'den bilgi alma/özetleme | Ayrı tasarım gerektirir: sağlayıcı seçimi, gizlilik, hız sınırı, kaynak gösterimi ve istem enjeksiyonu riskleri. Kod tabanının "onay olmadan dış istek yok" ilkesiyle çelişmemesi gerekir. | `/api/web/search` + onay adımı; DuckDuckGo/Brave API gibi bir sağlayıcı (2–3 gün) |
| **A7** | Uyandırma sözcüğü | Yerel VAD + anahtar sözcük modeli gerekir; sürekli mikrofon, pil ve gizlilik etkisi büyük. | openWakeWord/Porcupine ve net bir "sürekli dinleme" onayı |
| **A3** | Arka plan hatırlatma (uygulama kapalıyken) | Windows Zamanlanmış Görev + ayrı bildirim yardımcısı ve kurulum/izin akışı gerekir. | `schtasks` ile kullanıcı düzeyinde görev + tepsi bildirimi |
| **B1** | Veritabanı şifreleme | SQLCipher bağımlılığı ve anahtar yönetimi gerekir; mevcut "yalnızca standart kütüphane" ilkesini bozar. | BitLocker/OS disk şifrelemesi (README'de yazılı) veya SQLCipher'a isteğe bağlı geçiş |
| **C4/C5** | Kontrast denetimi, uzun sohbet sanallaştırma | Görsel doğrulama ve UI yeniden düzenlemesi gerektirir. | WCAG AA kontrast taraması; `IntersectionObserver` ile sanallaştırma |
| **D1** | Windows'ta uçtan uca doğrulama | Bu ortam Linux; SAPI, WebView2, tepsi, `.bat` ve OpenJarvis yalnızca gerçek makinede test edilebilir. | `E2E_DENETIM.md` §3.E kontrol listesi |
| **D5** | Lisans dosyası | Lisans seçimi kullanıcının hukuki kararıdır. | MIT/Apache-2.0 veya kapalı kullanım notu |

## 4. Windows'ta hızlı doğrulama listesi

1. `baslat.bat` → sunucu açılıyor, tarayıcı adresi çalışıyor.
2. Sohbete `yarın 09:00 su iç diye hatırlat` → "Hatırlatıcı kuruldu" ve Hatırlatıcılar bölümünde kayıt.
3. Defter → **⤓ CSV** → Excel'de Türkçe karakterler ve `1.250,75` biçimi doğru.
4. Defter → **⤓ Yedek** → JSON dosyasında `accounts`, `ledger`, `reminders`, `messages`.
5. Sohbet → **Sunucu geçmişi** → oturuma tıkla → mesajlar yükleniyor.
6. Telegram anahtarı ile bağlan → mesaj gönder → okunmamış sayısı artıyor, sunucuyu yeniden başlat → aynı mesaj tekrar görünmüyor.
7. `testler.bat` → 80 test geçiyor.
8. `ses_model_kur.bat` → indirme sonunda `sesler/*.sha256` dosyaları oluşuyor.

## Ek tur: Ollama'sız ücretsiz yapay zekâ (sağlayıcı katmanı)

**Soru:** "Ollama yerine ücretsiz bir yapay zekâya bağlama şansımız nedir, mesela OmniRoute'taki ücretsizleri kullanmak?"
**Yanıt:** Evet. OmniRoute OpenAI uyumlu `http://127.0.0.1:20128/v1` sunduğu için doğrudan bağlanır; OpenRouter/Groq/Cerebras/Gemini gibi servisler de aynı protokolü konuştuğu için tek istemciyle kullanılır.

Eklenenler:

| # | Madde | Durum |
| --- | --- | --- |
| H1 | `saglayici.py`: OpenAI uyumlu istemci (model listesi, sohbet, araç çağrıları) | ✅ |
| H2 | Adres güvenliği: uzakta `https` zorunlu, `http` yalnız loopback, URL'de kimlik reddi, `/v1` otomatik tamamlama | ✅ |
| H3 | Anahtar saklama: `saglayici_ayar.json`, 0600 izin, atomik yazma, arayüze maskeli (`…1234`), `.gitignore` kaydı | ✅ |
| H4 | Türkçe hata mesajları (401/402/403/404/422/429/5xx, bağlantı yok) | ✅ |
| H5 | Hazır servis listesi (OmniRoute, OpenRouter, Groq, Cerebras, Gemini) | ✅ |
| H6 | `/api/chat` içinde `backend:'api'` dalı; defter/hatırlatıcı araçları sağlayıcıda da çalışır | ✅ |
| H7 | Ayarlar → **Ücretsiz API** sekmesi: ön ayar seçimi, model getirme (`:free` ★), onay, bağlantıyı kes | ✅ |
| H8 | Sistem durumu panelinde "Yapay zekâ" satırı (hangi arka uç etkin) | ✅ |
| H9 | Testler: `tests/test_saglayici.py` (15) + `tests/test_server.py` içinde 9 sağlayıcı testi | ✅ (104 test) |
| H10 | E2E: sahte OpenAI uyumlu sağlayıcı ile 2 yeni kontrol (bağlan → sohbet → kes, https uyarısı) | ✅ (32 kontrol) |
| H11 | README bölümü + gizlilik/kota uyarıları | ✅ |

Bilinçli sınırlar:

- Ücretsiz kotalar sağlayıcıya göre değişir; "sınırsız" iddiaları garanti değildir, kod 429'u anlaşılır biçimde bildirir.
- Sağlayıcıya gönderilen mesajlar o servisin gizlilik politikasına tabidir; hassas veri için yerel Ollama/OmniRoute önerilir.
- Otomatik yedekleme (bir sağlayıcı 429 verince diğerine geçme) yapılmaz; kullanıcı modeli elle seçer.

## Ek tur: 9Router entegrasyonu

**İstek:** "9router da entegre et."
**Yaklaşım:** 9Router da OpenAI uyumlu `/v1` sunduğu için ayrı bir istemci yazmak yerine mevcut sağlayıcı katmanına **ön ayar + otomatik keşif** olarak eklendi.

| # | Madde | Durum |
| --- | --- | --- |
| J1 | `HAZIR` listesine **9Router** (`http://127.0.0.1:20128/v1`) ve **9Router Go** (`http://127.0.0.1:20130/v1`) eklendi; panelden alınan `sk_...` anahtarı ve `kr/`, `if/`, combo adları açıklandı | ✅ |
| J2 | `Saglayici.tara()`: yalnızca `127.0.0.1` üzerindeki bilinen portları (20128, 20130, 11434, 1234, 8080, 8787) paralel yoklar; açık / anahtar isteyen / kapalı ayrımı yapar | ✅ |
| J3 | `POST /api/provider/scan` uç noktası; adres istemciden alınmaz, yalnızca ek **port numarası** verilebilir (en fazla 12) → SSRF yüzeyi yok | ✅ |
| J4 | Arayüz: "Yerel geçitleri tara" düğmesi, bulunan geçitleri adres + model sayısı ile listeler, "Kullan" formu doldurup modelleri getirir; anahtar isteyen geçitte panel yönlendirmesi gösterilir | ✅ |
| J5 | Aynı 20128 portunu 9Router / OmniRoute / FlagshipRouter paylaştığı için arayüz ve README'de uyarı | ✅ |
| J6 | Testler: 5 yeni birim testi (`test_saglayici.py` → 20) + 2 uç nokta testi (`test_server.py` → 43) + 1 E2E kontrolü (33) | ✅ |

Bilinçli sınırlar:

- 9Router'ın OAuth ile bağladığı hesaplar (Kiro, Codex, Copilot vb.) Emre'de **yapılandırılmaz**; Emre yalnızca 9Router'ın `/v1` uç noktasını kullanır. Hesap/anahtar yönetimi 9Router panelinde kalır.
- Tarama yalnızca bilinen portları dener; keyfi port taraması (port scanning) yapılmaz.
- 9Router "sınırsız" iddiaları sağlayıcı politikalarına bağlıdır ve değişebilir.

## Ek tur: “401 Missing API key” teşhisi ve yedeği

Belirti (kullanıcı): Ücretsiz API bağlandı, model listesi geldi, ama sohbette `API anahtarı kabul edilmedi (401). Ayrıntı: Missing API key.`

Kök neden: 9Router/OmniRoute ailesinde bilinen geçit hatası — `/v1/models` Bearer anahtarıyla çalışırken `/v1/chat/completions` “Missing API key” dönebiliyor.

| # | Madde | Durum |
| --- | --- | --- |
| K1 | `_istek()`: 401 gövdesi “missing api key” ise istek bir kez `x-api-key` başlığıyla tekrarlanır (`_anahtar_eksik`, `_json_deneme`) | ✅ |
| K2 | 401 mesajına uygulanabilir ipucu: anahtarı yeniden kopyala, izinleri kontrol et, geçidi yeniden başlat, başka model/dogrudan sağlayıcı | ✅ |
| K3 | `POST /api/provider/test`: kayıtlı yapılandırmayla minik sohbet; hata varsa sağlayıcının kendi metni döner | ✅ |
| K4 | Arayüz: **Bağlantıyı test et** düğmesi; sohbet hatası artık “Ollama ile…” yerine gerçek arka ucu yazar | ✅ |
| K5 | `_http_mesaji` gövdeyi bir kez okuyacak şekilde yeniden yazıldı (HTTPError tekrar okunamıyordu), `_gonder`/`_ulasilamadi` yardımcıları | ✅ |
| K6 | Testler: 2 yeni `test_saglayici.py` (x-api-key yedeği, 401 ipucu), 2 yeni `test_server.py` (`/api/provider/test`) → **115 test**; E2E **34/34** | ✅ |

## Ek tur: konuşmayı eksik duyma sorunu

**Belirti:** “Konuşmamı eksik duyuyor ve tam olarak algılamıyor.” (Mikrofon düğmesi, yerel Whisper)

Kök nedenler ve düzeltmeler:

| # | Kök neden | Düzeltme | Durum |
| --- | --- | --- | --- |
| L1 | 1,2 sn sessizlikte kayıt kesiliyordu → cümle ortadan bölünüyordu | Varsayılan 2,2 sn, Ayarlar › Ses'ten 1,2–3,5 sn arası seçilebilir | ✅ |
| L2 | 16 sn üst sınırı uzun cümleyi kesiyordu | 30 sn varsayılan (15–60 sn) | ✅ |
| L3 | Sabit 0,008 eşiği sessiz konuşmayı hiç “duyuldu” saymıyordu | Uyarlanır gürültü tabanı (`zemin*3`, en az 0,005) | ✅ |
| L4 | Kayıtlar arasında boşluk → sonraki cümlenin başı kayboluyordu | `onstop` içinde anında yeni kayıt (`startClip`) | ✅ |
| L5 | Parçalar ayrı komut sayılıyordu | 900 ms birleştirme penceresi (`birlestirGonder`), meşgulse 8 kez erteler | ✅ |
| L6 | Asistan konuşurken söze girince kayıt atılıyordu | Barge-in: yüksek seste TTS durur, dinleme başlar | ✅ |
| L7 | Ne duyulduğu görünmüyordu | “Duyduğum: …” bildirimi + ayarı | ✅ |
| L8 | Whisper `base` Türkçede zayıf | `beam_size=5`, `temperature=0`, VAD dolgusu (700/600 ms), `initial_prompt` (defter/alacak/hatırlatıcı…), yinelenen segment atma, `small` modeli seçilebilir + `sesTanimaAyarlari` arayüzü | ✅ |
| L9 | `whisper_ayar.json` ve `ses_hata.log` git'e girebilirdi | `.gitignore`'a eklendi | ✅ |
| L10 | İşçi çökünce oturum boyunca ses ölü kalıyordu | `ses_baglanti` hata sonrası `worker=None` | ✅ |

Testler: `tests/test_ses_baglanti.py` 9 test, `test_server.py` +2 (`/api/speech/status`, `/api/speech/model`) → **126 test**; E2E **36/36** (Ses sekmesinde tanıma ayarları ve sessizlik seçiminin kaydı).

## Ek tur: canlı dikte (Antigravity'ye anında yazma)

**İstek:** “Konuştuklarımı algılasın, anında yazsın ve cevap vermeye çalışsın. Belli bir süre sonra toplu yazmasını istemiyorum. Yazımı düzelt, noktalamasını yap, anlam ver — dikte olarak kullan.”

| # | Madde | Durum |
| --- | --- | --- |
| M1 | `dikte.py`: `kaydir()` (üst üste binen pencerelerde kelime düzeyinde tekrar ayıklama), `temizle()` (dolgu sesleri, kekeleme), `bicimlendir()` (Türkçe büyük harf, soru algılama, noktalama, kesme işareti), `ipucu()` (Whisper bağlamı) | ✅ |
| M2 | `dikte_yaz.py`: Windows `SendInput` + `KEYEVENTF_UNICODE` ile etkin pencereye yazma; hedef pencere doğrulaması, uzunluk/satır sonu denetimi, Enter seçeneği, Windows dışında açık hata | ✅ |
| M3 | `POST /api/dictate/{window,finish,reset,type,status}`; oturum başına metin (en fazla 32 oturum, 8000 karakter, 30 dk TTL, `RLock`) | ✅ |
| M4 | İstemci: `ScriptProcessor` ile ham PCM → 16 kHz WAV → her 1 sn'de pencere gönderimi; sessizlikte motoru çalıştırmaz; metin panelde anında | ✅ |
| M5 | Panel: canlı yazım / Enter / cevap ver / yapay zekâ düzeltmesi anahtarları, hedef pencere alanı, “Aktif pencereye yaz”, “Sohbete gönder”, “Temizle” | ✅ |
| M6 | Yapay zekâ düzeltmesi: yalnızca noktalama/yazım, anlam korunur; uzunluk ±%33 dışındaysa öneri yok sayılır; sağlayıcı yoksa kural tabanlı metin kalır | ✅ |
| M7 | Testler: `tests/test_dikte.py` (26), `tests/test_dikte_yaz.py` (11), `test_server.py` +11 dikte testi → **172 test**; E2E **37/37** | ✅ |

Bilinçli sınırlar:

- Yazma yalnızca Windows'ta; Linux/macOS'ta açık hata (sessiz başarısızlık yok).
- Dikte metni **pano kullanmaz**, tuş kombinasyonu göndermez; yalnızca harf ve (istenirse) Enter.
- Canlı yazım varsayılan olarak **kapalı**; kullanıcı açmadan başka uygulamaya yazılmaz.
- Whisper `base` modeli 1 sn'lik pencerelerde hızlı ama Türkçede zayıf; `small` önerilir (gecikme ~1–2 sn).

## Ek tur: Jarvis karşılaştırmasındaki ilk dört öneri (2026-11-03)

**İstek:** `JARVIS_INCELEME.md` incelemesindeki önerilerden “ekle” talimatı.

| # | Madde | Durum |
| --- | --- | --- |
| N1 | `uyandirma.py`: “Emre” ile başlayan cümleleri ayıklama (`ayikla`), kelime sınırı (emreye/emreler tetiklemez), en fazla 6 kelime, `uyandirma_ayar.json`, varsayılan **kapalı** | ✅ |
| N2 | Dikte kapısı: `/api/dictate/window` → `triggered`; uyandırmadan sonra **12 sn** devam penceresi; uyandırma sözü metinden çıkarılır | ✅ |
| N3 | `bellek.py`: SQLite `memories` tablosu, kural tabanlı çıkarım (hatırla/not al/adım/telefon/seviyorum), mükerrer engeli, Türkçe aksan duyarsız arama (`arama` sütunu + eski DB göçü), 5000 kayıt sınırı | ✅ |
| N4 | Sohbet entegrasyonu: ilgili bellek kayıtları sistem istemine eklenir, açık bilgiler yanıttan **önce** kaydedilir | ✅ |
| N5 | `mcp_istemci.py`: stdio JSON-RPC (`initialize` → `tools/list` → `tools/call`), kabuk yok, 8 sunucu / 20 sn başlatma / 60 sn istek, `mcp_ayar.json` + `mcp_ayar.ornek.json` | ✅ |
| N6 | `ekran.py`: Windows PowerShell + `System.Drawing`, diğer platformlarda Pillow; 6 MB sınırı, diske yazmaz | ✅ |
| N7 | Uçlar: `GET /api/memory`, `POST /api/memory/{add,delete}`, `GET /api/wake/status`, `POST /api/wake/settings`, `GET /api/mcp/{status,tools}`, `POST /api/mcp/call`, `POST /api/screen/{capture,ask}` | ✅ |
| N8 | Arayüz: **Bellek** sekmesi (arama/ekle/sil + uyandırma anahtarı ve kelimeleri), **MCP araçları** sekmesi (durum + araç listesi + onaylı çağrı), sohbet alanında **▣ Ekranı sor** düğmesi | ✅ |
| N9 | Testler: `test_uyandirma` (15), `test_bellek` (15), `test_mcp_istemci` (15), `test_ekran` (6), `test_server` +14 → **239 test**; arayüz E2E **40/40** | ✅ |

Bilinçli sınırlar:

- Uyandırma sözcüğü **metin** üzerinde çalışır (cihaz içi akustik model yok); Whisper metni gecikmeli geldiği için ~1–2 sn gecikme olabilir.
- Bellek araması anlamsal (vektör) değil, kelime + aksan normalizasyonu; Türkçe ekler için kök eşleşmesi yok.
- MCP sunucuları yerel komutlardır; ağdan gelen bir MCP sunucusuna bağlanma yoktur. Her çağrı onay ister.
- Ekran görüntüsü sağlayıcıya gönderilir; sağlayıcı seçiminde gizlilik maddesine dikkat.
