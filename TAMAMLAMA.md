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
