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
python3 -m unittest discover -s tests -t .    # Ran 580 tests ... OK
cd tools/e2e && npm test                      # 63/63 kontrol, JS hatası yok
```

| Paket | Test sayısı |
|---|---|
| `tests/test_server.py` (HTTP) | 152 |
| `tests/test_arayuz_erisim.py` (kontrast + yapı + uç kapsamı) | 12 |
| `tests/test_saglayici.py` (sağlayıcı + görsel) | 44 |
| `tests/test_belge.py` | 35 |
| `tests/test_beceriler.py` | 28 |
| `tests/test_bellek.py` | 27 |
| `tests/test_takvim.py` | 26 |
| `tests/test_dikte.py` | 26 |
| `tests/test_arama.py` | 21 |
| `tests/test_posta.py` | 20 |
| `tests/test_kisayol.py` | 16 |
| `tests/test_tanilama.py` | 16 |
| `tests/test_uyandirma.py` | 16 |
| `tests/test_sesli_yanit.py` | 15 |
| `tests/test_ledger_tools.py` | 15 |
| `tests/test_mcp_istemci.py` | 15 |
| `tests/test_denetim.py` | 14 |
| `tests/test_otomatik_baslat.py` | 12 |
| `tests/test_bildirim.py` | 11 |
| `tests/test_dikte_yaz.py` | 11 |
| `tests/test_zaman_ayristir.py` | 10 |
| `tests/test_ses_baglanti.py` | 9 |
| `tests/test_hatirlatici.py` | 7 |
| `tests/test_ekran.py` | 6 |
| `tests/test_yerel_isci.py` | 6 |
| `tests/test_arena_bridge.py` | 5 |
| `tests/test_piper_indir.py` | 5 |
| **Toplam** | **580** |

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

## Ek tur: sistem entegrasyonu (2026-11-03 · ikinci tur)

**İstek:** “ekleyelim” — `YOL_HARITASI.md` A bloğunun ilk üç maddesi.

| # | Madde | Durum |
| --- | --- | --- |
| S1 | `otomatik_baslat.py`: Başlangıç klasörüne `EMRE.lnk`, sessiz `emre_arkaplan.vbs` (pythonw, konsol yok), kur/kaldır/durum, kayıt defterine dokunmaz | ✅ |
| S2 | `kisayol.py`: `RegisterHotKey` ile global kısayol (varsayılan `ctrl+alt+d`), `coz()` doğrulaması, kayıt hatası Türkçe, Windows dışında açık hata | ✅ |
| S3 | Kısayol → dikte: `/api/hotkey/poll` sıra numarası; açık sayfa 1,5 sn'de bir yoklar ve dikteyi açar/kapatır; sayfa kapalıysa isteğe bağlı `?dikte=1` ile tarayıcı açılır | ✅ |
| S4 | `bildirim.py`: Windows PowerShell `NotifyIcon` balonu, Linux'ta `notify-send`, uyarı sesi; hata akışı bozmaz | ✅ |
| S5 | Sunucu hatırlatıcı işçisi: 20 sn'de bir tarama, `reminders.notified` ile tek bildirim, `notifications` tablosu, `EMRE_BILDIRIM_ARALIK` | ✅ |
| S6 | Uçlar: `/api/system/{status,autostart,hotkey,notifications}`, `/api/hotkey/poll`, `/api/notifications`, `/api/notifications/seen` | ✅ |
| S7 | Arayüz: **Ayarlar › Sistem** sekmesi (otomatik başlatma, kısayol + tuş + tarayıcı seçeneği, bildirim anahtarı), sayfa içi bildirim akışı | ✅ |
| S8 | Testler: `test_kisayol` (15), `test_bildirim` (11), `test_otomatik_baslat` (12), `test_server` +13 → **291 test**; E2E **44/44** | ✅ |

Bilinçli sınırlar:

- Otomatik başlatma ve global kısayol **yalnızca Windows**; diğer platformlarda açık hata (sessiz başarısızlık yok).
- Otomatik başlatma kayıt defteri/Hizmetler kullanmaz; kullanıcı oturumu açıldığında çalışır (oturum açmadan önce değil).
- Kısayol yalnızca dikteyi açar/kapatır; başka işlem yapmaz. Tarayıcı kapalıyken dikte, sayfa açılana kadar başlamaz.
- Masaüstü bildirimi odak çalmayan balondur; Windows bildirim ayarlarında "rahatsız etme" açıksa görünmeyebilir.
- Hatırlatıcı işçisi sunucu çalışırken aktiftir; Emre tamamen kapalıyken bildirim üretilmez (bir sonraki açılışta birikenler gösterilir).

## Ek tur: akışlı yanıt + web araması (2026-11-03 · üçüncü tur)

**İstek:** “devam edelim” — `YOL_HARITASI.md` A5 ve A4.

| # | Madde | Durum |
| --- | --- | --- |
| K1 | `saglayici.sohbet_akis()`: OpenAI uyumlu SSE akışı, `x-api-key` yedeği, Türkçe hata çevirisi | ✅ |
| K2 | `POST /api/chat/stream`: SSE olayları (`start`, `delta`, `done`), kural tabanlı yanıtlarda tek parça, bağlantı kopunca sessiz çıkış | ✅ |
| K3 | Ollama akışı (`ollama_akis`): NDJSON satırları → parça; `qwen3` için `/no_think` | ✅ |
| K4 | Arayüz: akışlı yazım (canlı satır), akış başarısızsa otomatik tek parça yola dönüş, `TextDecoder` olmayan ortamlar için bayt çözücü | ✅ |
| K5 | `arama.py`: DuckDuckGo Lite → Instant Answer → Türkçe Vikipedi; https zorunlu, boyut/süre sınırı, tekilleştirme | ✅ |
| K6 | `gerekiyor_mu()`: güncel bilgi/belirtilen komut kalıpları; defter/hatırlatıcı komutları aramaya gitmez | ✅ |
| K7 | Sohbete kaynak ekleme: sistem isteminde numaralı kaynaklar, yanıtta `sources`, arayüzde tıklanabilir liste | ✅ |
| K8 | Uçlar: `/api/chat/stream`, `/api/web/search`, `/api/system/web`; Sistem sekmesinde web ve akış anahtarları | ✅ |
| K9 | Testler: `test_arama` (21), `test_saglayici` +5, `test_server` +12 → **329 test**; E2E **47/47** | ✅ |

Yol boyunca düzeltilen hata:

- Açık bilgiler bağlama eklenirken `kisisel` değişkeni sonradan `''` ile eziliyordu; **kişisel bellek sohbete hiç girmiyordu**. Düzeltildi.

Bilinçli sınırlar:

- Akışlı yolda modelin **araç çağrısı** (tool_calls) kullanılmaz; defter/hatırlatıcı işlemleri kural tabanlı çözücülerle yapılır.
  Modelin tool JSON’u yazması durumunda yanıt güvenli biçimde “işlem yapılmadı” olarak değiştirilir.
- Web araması bir arama motoruna bağımlı; DuckDuckGo sayfa yapısı değişirse Vikipedi yedeği devreye girer.
- Arama sonuçları özet düzeyinde; tam sayfa okuma (fetch + çıkarma) yok.

## Ek tur: beceriler, denetim izi, tanılama (2026-11-03 · dördüncü tur)

**İstek:** “ekleyelim” — `YOL_HARITASI.md` B1 + C1 + C4.

| # | Madde | Durum |
| --- | --- | --- |
| T1 | `beceriler.py`: `beceriler/<ad>/SKILL.md` ayrıştırma, tetik kelimeleri, listele/bul/eşleştir | ✅ |
| T2 | Beceri çalıştırma: kabuk yok, `shlex` ile argümanlar, stdin JSON, stdout JSON/düz metin, 20 sn zaman aşımı, çıktı sınırı | ✅ |
| T3 | Sohbet entegrasyonu: `!beceri-adı metin` açık komutu (`/api/chat` ve `/api/chat/stream`), bağlamda beceri listesi | ✅ |
| T4 | Örnek beceri: `beceriler/metin-analiz` (SKILL.md + calistir.py), depoda hazır | ✅ |
| T5 | `denetim.py`: `audit` tablosu, sır maskeleme (`Bearer`, `sk-`, `token:`, `parola:`), 2000 kayıt budaması | ✅ |
| T6 | Denetim kancaları: MCP, beceri, ekran, dikte yazımı, defter/bellek, sağlayıcı, uygulama, otomatik başlatma, kısayol | ✅ |
| T7 | `tanilama.py`: 10 kontrol (Python, platform, disk, yazma, veritabanı, port, Ollama, ses, beceri, MCP) + özet | ✅ |
| T8 | Uçlar: `GET /api/skills`, `POST /api/skills/run`, `GET /api/audit`, `POST /api/audit/clear`, `GET /api/diagnose` | ✅ |
| T9 | Arayüz: **Ayarlar › Beceriler** sekmesi (liste + onaylı çalıştırma), Sistem sekmesinde tanılama ve denetim izi bölümleri | ✅ |
| T10 | Testler: `test_beceriler` (28), `test_denetim` (16), `test_tanilama` (16), `test_server` +12 → **399 test**; E2E **49/49** | ✅ |

Bilinçli sınırlar:

- Beceriler Emre'nin kullanıcısıyla aynı yetkilerle çalışır; yalnızca **senin yazdığın** dosyalardan oluşur ve
  her çalıştırma onay ya da açık `!ad` komutu ister. Üçüncü taraftan beceri indirme yoktur.
- Beceri çıktısı 4000 karakterle sınırlı; uzun çıktılar kırpılır.
- Denetim izi yalnızca bu bilgisayarda; dışa aktarma/senkron yok. Silme onay ister.
- Tanılama yalnızca okuma yapar (tek istisna: yazma testi için geçici dosya).

## Ek tur: bellek yedeği + sağlayıcı dayanıklılığı (2026-11-03 · beşinci tur)

**İstek:** “yapalım” — `YOL_HARITASI.md` C2 ve C3.

| # | Madde | Durum |
| --- | --- | --- |
| U1 | `bellek.disa_aktar/ice_aktar/yedek_json`: sürümlü JSON yedeği, `birlestir`/`degistir` modları, mükerrer atlama, 5000 kayıt sınırı | ✅ |
| U2 | `bellek.unut()` + sohbette `unut: …` komutu; `bellek.arsivle()` (hits=0 ve N günden eski) | ✅ |
| U3 | Uçlar: `/api/memory/export`, `/api/memory/import`, `/api/memory/forget`, `/api/memory/archive` | ✅ |
| U4 | `saglayici`: `yedek` alanı, `yedek_ayarla()`, `gecici_hata()` sınıflandırması, sohbet ve akışta tek denemeli yedek geçiş | ✅ |
| U5 | Kota sayacı: `provider_usage` tablosu, `kota_artir()/kota_ozet()`, `/api/provider/usage`, `/api/provider/fallback` | ✅ |
| U6 | Arayüz: Bellek sekmesinde yedek indir / geri yükle / yaşlandır; Sistem sekmesinde kota satırı + yedek model alanı | ✅ |
| U7 | Testler: `test_bellek` +12, `test_saglayici` +10, `test_server` +14 → **436 test**; E2E **51/51** | ✅ |

## Ek tur: akışlı seslendirme, belge okuma, takvim ve posta (2026-11-03 · altıncı tur)

**İstek:** “kalanları bitir” — `YOL_HARITASI.md` B2, B3 ve B4.

| # | Madde | Durum |
| --- | --- | --- |
| V1 | `sesli_yanit.py`: `cumlelere_ayir` (kısaltma koruması, 220 karakter sınırı), `AkisParcalayici` (akan metni cümle cümle verir), `BargeIn` (eşik + 3 ardışık ölçüm + 1,5 sn soğuma) | ✅ |
| V2 | `belge.py`: stdlib ile PDF (`FlateDecode` + `Tj/TJ`), DOCX (ZIP + XML), HTML, txt/md/csv/json/log metin çıkarma; sayfa ve parça bölme; `docs`/`doc_chunks` tabloları; Türkçe aksan duyarsız arama | ✅ |
| V3 | `takvim.py`: `.ics` salt okunur okuma (TZID, RRULE, katlanmış satır), `yaklasan`, `metin_ozet`, `gerekiyor_mu` | ✅ |
| V4 | `posta.py`: `.eml` / `.mbox` / klasör salt okunur okuma; RFC 2047 ve 8 bit Türkçe başlık onarımı; `sirala`, `metin_ozet`, `gerekiyor_mu` | ✅ |
| V5 | `server.py`: `/api/docs/*`, `/api/calendar`, `/api/calendar/path`, `/api/mail`, `/api/mail/path`, `/api/tts/split`, `/api/system/tts`; sohbette belge bağlamı ve takvim/posta kural yanıtları | ✅ |
| V6 | `index.html`: Ayarlar › **Belgeler** (yükleme, listeleme, silme, belgeye sor) ve **Takvim & posta** sekmeleri; Ses sekmesinde akışlı seslendirme ve söz kesme anahtarları; akış sırasında cümle cümle okuma | ✅ |
| V7 | Testler: `test_sesli_yanit` (15), `test_belge` (35), `test_takvim` (26), `test_posta` (20), `test_server` +29 → **553 test**; E2E **54/54** | ✅ |

Bilinçli sınırlar:

- **IMAP/SMTP yok**: hesaba bağlanmak parola saklamayı ve dış ağa çıkmayı gerektirir; posta yalnızca yerel dosyalardan okunur.
- Taranmış PDF'lerde **OCR yok**; metin bulunamazsa açık hata döner.
- Belge yedeği şifrelenmez; içerik `docs`/`doc_chunks` tablolarında düz metindir.
- Belge araması kelime tabanlıdır (gömme/vektör arama yok); çok uzun belgelerde en iyi 5 parça getirilir.
- Takvimde tekrarlayan etkinliklerin yalnızca ilk oluşumu gösterilir; seriyi genişletmek takvim uygulamasının işidir.

## Ek tur: bugün özeti, komut paleti, tema ve görsel üretimi (2026-11-03 · yedinci tur)

**İstek:** “kalanları bitir” — `YOL_HARITASI.md` D1, D2, D3 ve B5.

| # | Madde | Durum |
| --- | --- | --- |
| W1 | `server.gun_ozeti()` + `GET /api/today`: geciken/bugün/hafta hatırlatıcıları, defter bakiyesi, son bellek kayıtları, belge sayısı, bugünün takvim etkinlikleri | ✅ |
| W2 | Arayüz: ana sayfada “Bugün” kartı (4 bölüm), “Yenile” + “⌘ Komutlar” düğmeleri, 2 dakikalık tazeleme | ✅ |
| W3 | Komut paleti: `/` ve `Ctrl+K`, 15 komut, filtre, ↑↓/Enter, `Esc` kapatma, dışına tıklayınca kapanma | ✅ |
| W4 | Ayarlar › **Görünüm**: Koyu/Açık/Sistem teması, 13–18 px yazı boyutu, `localStorage` kalıcılığı, açık tema CSS kapsamı | ✅ |
| W5 | `saglayici.gorsel()`: OpenAI uyumlu `/images/generations`, b64 yanıt zorunlu, URL yanıtı reddedilir, boyut doğrulama, Türkçe hatalar | ✅ |
| W6 | Uçlar `/api/image/generate` (onay zorunlu) ve `/api/image/model`; arayüzde “Görsel üret” paneli + model alanı | ✅ |
| W7 | Testler: `test_server` +8, `test_saglayici` +7 → **568 test**; E2E +4 → **58/58** | ✅ |

Bilinçli sınırlar:

- **C5 (telefondan erişim) yapılmadı**: sunucu yalnızca `127.0.0.1` dinler; dışarı açmak token + TLS + yama yönetimi
  gerektirir ve güvenlik sınırını bozar. Öneri: ayrı tünel (Tailscale/WireGuard), Emre yine yerel adreste.
- Görsel üretimi sağlayıcıya bağlıdır; ücretsiz modellerin çoğu desteklemez. Sağlayıcı görseli URL olarak dönerse indirilmez.
- Üretilen görsel yalnızca tarayıcıda gösterilir; diske yazılmaz, veritabanına girmez (istenirse kullanıcı indirir).
- Tema seçimi sunucuda saklanmaz; tarayıcı değişirse varsayılan koyu temaya döner.

## Ek tur: kapanış — erişilebilirlik, uzun sohbet, kısayol yardımı, erişim rehberi (2026-11-03 · sekizinci tur)

**İstek:** “kalanları bitir”. Bu turda yeni özellik yerine kalan kalite ve güvenlik başlıkları kapatıldı.

| # | Madde | Durum |
| --- | --- | --- |
| X1 | WCAG AA kontrast düzeltmeleri (palet alt yazısı 3.87→5.96, Bugün kartı saati 4.28→5.78, palet küçük yazı 3.93→5.10) | ✅ |
| X2 | `tests/test_arayuz_erisim.py`: 18 renk çifti için kontrast testi + 9 yapısal/aria kontrolü (tarayıcısız) | ✅ |
| X3 | Uzun sohbet: DOM'da en fazla 300 mesaj + “eski mesajlar kaldırıldı” bilgi satırı | ✅ |
| X4 | `?` kısayol yardım paneli + palette “Kısayollar” komutu (16 komut) | ✅ |
| X5 | Ulaşılamayan “henüz hazırlanmadı / henüz bağlı değil” yedek mesajlarının kaldırılması | ✅ |
| X6 | [`UZAK_ERISIM.md`](UZAK_ERISIM.md): telefondan erişimin güvenli yolu (Tailscale + SSH tüneli); sunucu yine `127.0.0.1` | ✅ |
| X7 | Testler: +11 → **579 test**; E2E +2 → **60/60** (`?` yardımı, uzun sohbet sınırı); `ruff` temiz | ✅ |
| X8 | Arayüze bağlanmamış uçlar kapatıldı: sohbet geçmişi silme düğmesi, bellek “Eşleşenleri unut”, dikte durumu (`/api/dictate/status`), paletten **Web'de ara** paneli | ✅ |
| X9 | `test_her_uc_noktasinin_arayuz_karsiligi_var`: sunucudaki tüm `/api/...` uçları arayüzde geçmeli (2 bilinçli istisna gerekçeli) | ✅ |
| X10 | `WINDOWS_DOGRULAMA.md`: Windows'ta elle doğrulama listesi (11 bölüm) | ✅ |
| X11 | CI: sözdizimi kontrolü artık tüm Python dosyalarını kapsıyor (`compileall -q .`) | ✅ |
| X12 | E2E +3 → **63/63**; toplam **580 test** | ✅ |
| X13 | `emre_arkaplan.vbs` her başlatmada yeniden yazılıyordu (metin kipinde okuma `\r\n`→`\n` çevirisi yüzünden karşılaştırma hiç eşleşmiyordu); bayt düzeyinde karşılaştırma + yazma, Windows'ta `\r\r\n` bozulması da giderildi | ✅ |
| X14 | `test_background_script_written_once` mtime yerine yazma sayımına dayanıyor (CI'da kırılgandı) | ✅ |

Bilinçli sınırlar:

- **Tam tarayıcı erişimi** hâlâ yalnızca hazırlık tercihi; Emre tarayıcıyı sürmez (CAPTCHA/giriş atlatma yasak).
- Sunucu `0.0.0.0`'a alınmadı, port yönlendirme/herkese açık tünel önerilmiyor (bkz. `UZAK_ERISIM.md`).
- Veritabanı şifrelemesi yok (SQLCipher standart kütüphane ilkesini bozar); disk şifrelemesi (BitLocker) README'de öneriliyor.
- Lisans dosyası hukuki bir karar olduğu için eklenmedi.

Bilinçli sınırlar:

- Yedek dosyası **şifrelenmez**; kişisel notlar düz metindir. Paylaşmadan önce içeriğini kontrol et.
- Geri yükleme yalnızca `kayitlar` listesini işler; bağlantı grafiği yedeğe yazılır ama geri yüklemede yeniden kurulmaz.
- Yedek model aynı sağlayıcı/anahtar üzerinden çağrılır (ayrı sağlayıcıya otomatik geçiş yok).
- Kota sayacı Emre'nin kendi isteklerini sayar; sağlayıcı panelindeki gerçek kota ile birebir aynı olmayabilir.
