# EMRE — Uçtan Uca (E2E) Tarama Raporu

Tarih: 2026-11-02 · Önceki rapor: `DENETIM.md` (statik tarama)
Bu rapor, uygulamayı **çalıştırarak** yapılan ikinci tur taramanın sonuçlarını ve kalan eksikleri içerir.

## 1. Yöntem

| Katman | Araç | Kapsam |
|---|---|---|
| Statik analiz | `pyflakes` | 14 Python dosyası, tests dahil |
| JS sözdizimi | `node --check` | `index.html` içindeki 2 script bloğu |
| Birim/HTTP testleri | `unittest` (46 test) | Defter mantığı, yetkilendirme, CRUD, doğrulama, işçi zaman aşımı |
| **Arayüz E2E** | jsdom + gerçek sunucu (`tools/e2e`) | 23 kontrol: menü, defter, hatırlatıcı, ayarlar, geliştirici, mikrofon, 403, XSS/storage |
| API dayanıklılık | 40+ elle istek | Path traversal, mükerrer kayıt, sınır değerler, OPTIONS, chunked gövde |
| Eşzamanlılık | 20 paralel yazma | SQLite kilitlenme davranışı |
| Türkçe NLU | 17 cümle | Tutar/kişi/tür çıkarımı, hatırlatıcı niyeti |

Komutlar:

```bash
python3 -m unittest discover -s tests -t .      # 46 test
python3 tools/e2e/baslat.py &                    # E2E sunucusu
cd tools/e2e && npm install && npm test          # 23 kontrol
```

## 2. Bu turda bulunup düzeltilen hatalar

### Kritik / yüksek

| # | Bulgu | Kanıt (önce) | Durum |
|---|---|---|---|
| 1 | **`tahsil` kelimesi "sil" içerdiği için silme sanılıyordu.** Tahsilat cümleleri hiç kaydedilmiyor, kullanıcıya hiçbir şey söylenmiyordu (sessiz veri kaybı). | `'Ahmetten 250 TL tahsil ettim' → None`, `'Ahmete 250 TL tahsilat ekle' → None` | `(?<!\w)sil(?!\w)` sınır kontrolü. Artık `received` kaydı oluşuyor. |
| 2 | **Binlik ayırıcılı büyük tutarlar reddediliyordu.** `1.000.000 TL` "Tutar anlaşılamadı" hatası veriyordu. | `parse: '1.000.000' → ValueError` | Ortak `parse_amount()` yardımcısı: `1.250,50`, `1.000.000`, `1.500`, `1,500.75` destekli. |
| 3 | **Tek cümlede iki işlem sessizce yarısı kaydediliyordu.** | `'...100 TL alacak ekle ve 200 TL verecek ekle' → yalnızca 100 TL yazıldı` | Birden fazla tutar varsa kayıt yapılmıyor, "tek tek söyle" uyarısı veriliyor. |
| 4 | **DNS rebinding açığı.** Sunucu `Host` başlığını doğrulamıyordu; saldırgan alan adını `127.0.0.1`'e çözerek tarayıcıda aynı kaynak sayılabilir, `/` sayfasındaki token'ı okuyup yerel API'yi ele geçirebilirdi. | `Host: kotu-site.example` ile istek → 200 | `valid_host()` eklendi: yalnızca `127.0.0.1`, `localhost`, `::1`. Test: `test_foreign_host_header_rejected`. |
| 5 | **Chunked istek gövdesi sessizce yok sayılıyordu.** `Content-Length` göndermeyen istemcilerde gövde boş sanılıp "alan gerekli" hatası dönüyordu. | chunked POST → `{"error":"name alanı gerekli."}` | `read_chunked()` + boyut sınırı; test: `test_chunked_body_accepted`. |
| 6 | **Mükerrer hesapta İngilizce SQL hatası sızıyordu.** | `{"error":"UNIQUE constraint failed: accounts.name"}` | Türkçe "Bu isimde bir hesap zaten var." + `IntegrityError` çevirisi. |
| 7 | **Türkçe büyük/küçük harf:** `İlker` ve `ilker` iki ayrı hesap olarak eklenebiliyordu (SQLite `NOCASE` sadece ASCII). | ikinci kayıt → 200 | `tr_key()` ile Türkçe uyumlu karşılaştırma; ekleme ve silme aynı anahtarı kullanıyor. |

### Orta

| # | Bulgu | Durum |
|---|---|---|
| 8 | Hata mesajları iç alan adlarını sızdırıyordu: `"name alanı gerekli."` | `text_field(..., label='Hesap adı')` → "Hesap adı gerekli." |
| 9 | Hatırlatıcı **silinemiyordu** (yalnızca "tamamlandı"). | `/api/reminders/delete` + arayüzde onaylı "Sil" düğmesi |
| 10 | Sunucu yeniden başlayınca (token değişir) arayüz yalnızca "Yetkisiz istek." gösteriyordu. | 403 → "Oturum anahtarı geçersiz… sayfayı yenile (F5)." |
| 11 | 8765 portu doluysa çıplak Python traceback'i. | Anlaşılır Türkçe mesaj + `KeyboardInterrupt` ile temiz kapanış |
| 12 | `OPTIONS` isteğine HTML 501 yanıtı. | JSON 405 |
| 13 | Clickjacking koruması yoktu. | `X-Frame-Options: DENY` |
| 14 | Kullanılmayan importlar (6 adet). | Temizlendi (`pyflakes` temiz) |
| 15 | `baslat.bat` Edge kanalı kullanıldığı hâlde **Chromium indiriyordu** (~150 MB gereksiz). README de aynı yanlış yönlendirmeyi yapıyordu. | Kaldırıldı, README düzeltildi |
| 16 | `.venv-*` oluşturma `--python 3.12` ile sabitti; 3.12 kurulu değilse kurulum başarısız oluyordu. | Kurulu sürüme düşen yedek adım eklendi |
| 17 | Arayüz için otomatik test yoktu. | `tools/e2e` (jsdom, 23 kontrol) + CI işi |

## 3. Açık kalan eksikler

### A. İşlevsel boşluklar

| # | Eksik | Etki | Öneri / tahmini efor |
|---|---|---|---|
| A1 | **Sohbetten hatırlatıcı oluşturma çalışmıyor.** Doğrudan kural yolu hatırlatma niyeti görünce "bu işlem henüz yapılmadı" deyip duruyor; modelin `remind_at` alanlı tool'u hiç devreye girmiyor. | Kullanıcı sohbette "yarın 09:00'da hatırlat" dediğinde ölü uca düşüyor | Niyet tespitinde `None` dönüp model yoluna bırakmak (küçük) veya Türkçe tarih/saat ayrıştırıcı (orta, ~1 gün) |
| A2 | **Web'den bilgi alma yok.** "Ara" komutu Google'ı yeni sekmede açar; asistan içeriği okuyup özetlemez. | README'de sınır olarak yazılı | Sunucu taraflı arama + özet (orta, 2-3 gün; gizlilik/rate-limit tasarımı gerekir) |
| A3 | **Arka plan hatırlatma yok.** Sayfa/WebView kapalıyken bildirim üretilmez. | Zamanlanmış hatırlatmalar kaçabilir | Windows Zamanlanmış Görev + küçük bildirim yardımcısı (orta) |
| A4 | **Sunucu taraflı sohbet geçmişi yok.** Konuşmalar `localStorage`'da; masaüstü (WebView2) ve tarayıcı geçmişi ayrı. | Cihaz/oturum değişince kaybolur | SQLite `messages` tablosu + `/api/chat/history` (orta) |
| A5 | **Defter dışa aktarma/yedekleme yok.** Yalnızca `emre.sqlite3` dosyasını elle kopyalamak mümkün. | Yedekleme hatası = veri kaybı | CSV/JSON dışa aktarma uç noktası (küçük) |
| A6 | **Yapay zekâ kaynaklı defter kayıtlarında denetim izi zayıf.** Kayıtta yalnızca `created` var; kaydı kimin/neyin tetiklediği tutulmuyor. | Sonradan inceleme zor | `source` ve `raw_text` kolonları (küçük) |
| A7 | **Uyandırma sözcüğü yok**; mikrofon düğmeyle açılıyor. | README'de sınır | Yerel VAD + anahtar sözcük (büyük) |
| A8 | **Telegram art arda sorgulanmıyor.** Mesajlar yalnızca bölüm açıkken çekiliyor; offset yalnızca bellekte (yeniden başlatınca sıfırlanır). | Gecikmeli mesaj, yeniden başlatmada eski mesaj tekrarı | Zamanlayıcı iş parçacığı + offset'i SQLite'ta tutmak (küçük-orta) |

### B. Güvenlik ve gizlilik

| # | Eksik | Not |
|---|---|---|
| B1 | `emre.sqlite3` **şifresiz**; yerel kullanıcı/zararlı yazılım okuyabilir. | README'de yazılı; SQLCipher veya işletim sistemi disk şifrelemesi önerilir |
| B2 | Token her açılışta üretiliyor ve HTML'e gömülüyor (meta etiketi); sunucu yeniden başlarsa açık sekmeler kırılır. | Kabul edilebilir; "yenile" mesajı eklendi. Kalıcı token dosyası seçenek olarak düşünülebilir |
| B3 | **CSP yok.** Tüm JS/CSS satır içi; `script-src 'unsafe-inline'` gerektirdiği için gerçek koruma sağlamaz. | Uzun vadede inline kodun ayrı dosyalara taşınması gerekir |
| B4 | Hız sınırı (rate limit) yok. | Yalnızca loopback dinlendiği için risk düşük |
| B5 | `arena_profile` çerezleri şifresiz saklanıyor. | Artık `.gitignore`'da; disk şifreleme önerilir |
| B6 | Model çağrılarında istem enjeksiyonu (prompt injection) koruması sınırlı: defter tool'ları kural tabanlı filtrelerle korunuyor ama "kaydettim" yalanını engelleyen regex listesi zamanla aşınabilir. | Ek testlerle genişletilmeli |

### C. Erişilebilirlik ve UX

| # | Eksik | Öneri |
|---|---|---|
| C1 | Sohbet mesajları için `aria-live` yok; ekran okuyucu yeni yanıtı duyurmuyor. | `role="log" aria-live="polite"` |
| C2 | Defter/onay pencerelerinde odak tuzağı ve `Esc` ile kapatma yok. | Dialog bileşenine `keydown` + odak yönetimi |
| C3 | Bölüm değişiminde odak taşınmıyor, `h1`'e atlanmıyor. | `focus()` + başlık bağlantısı |
| C4 | Renk kontrastı ölçülmedi (koyu tema, `#78919e` metin). | WCAG AA için kontrast denetimi |
| C5 | Uzun sohbetlerde mesaj listesi sanallaştırılmıyor; 200+ mesajda kaydırma ağırlaşabilir. | Sanallaştırma veya "daha fazla yükle" |
| C6 | Canvas animasyonu her karede 360 parçacık + 48 iz çiziyor; dizüstünde CPU/pil tüketimi yüksek olabilir. | `prefers-reduced-motion` var (iyi); ayrıca FPS sınırı (30) önerilir |
| C7 | Hiçbir yerde "sürüm" gösterilmiyor (`/api/status` `version` döndürüyor). | Ayarlar altına sürüm + "güncelleme var mı" bilgisi |

### D. Test ve altyapı

| # | Eksik | Öneri |
|---|---|---|
| D1 | Windows'a özgü kod (SAPI, WebView2, tepsi, `.bat`, OpenJarvis, Piper) **otomatik test edilmiyor**; bu tarama Linux'ta yapıldı. | Gerçek makinede aşağıdaki kontrol listesi |
| D2 | `arena_bridge` durum makinesi test edilmiyor (Playwright/Edge gerektirir). | `pytest` ile sahte (mock) Playwright katmanı |
| D3 | Lint/format yapılandırması yok (ruff/flake8, prettier). | `ruff` + CI adımı |
| D4 | `piper_indir.py` indirdiği model dosyalarını **doğrulamıyor** (checksum yok). | SHA-256 sabitleri |
| D5 | Lisans dosyası yok. | Kamuya açık paylaşım öncesi seçilmeli |
| D6 | `/api/ledger` tüm kayıtları döndürüyor (sayfalama yok). | `limit/offset` parametreleri |
| D7 | `db()` her istekte `CREATE TABLE IF NOT EXISTS` çalıştırıyor (~1 ms). | Süreç başına bir kez şema kurulumu |

### E. Windows'ta elle doğrulanması gerekenler

1. `baslat.bat` → sunucu açılıyor mu, tarayıcı adresi çalışıyor mu?
2. `ses_kur.bat` → `.venv-ses` kurulumu, Whisper `base` modeli, mikrofonla Türkçe tanıma.
3. `ses_model_kur.bat` → Piper Fahrettin/Fettah indirme, Ayarlar > Ses'te önizleme.
4. `masaustu_kur.bat` + `masaustu_baslat.bat` → WebView2, tepsi simgesi, X ile gizleme, tepsi menüsünden tamamen çıkış.
5. OpenJarvis: `ollama create emre-cpu -f Modelfile.emre`, `jarvis serve`, `ollama ps` ile CPU doğrulaması.
6. Telegram: gerçek bot anahtarı ile bağlan, mesaj gönder, onaylı yanıt.
7. Arena: Edge ile oturum açma, soru gönderimi, yanıt yakalama (arayüz değişmiş olabilir).
8. `testler.bat` → 46 testin Windows'ta da geçtiğinin doğrulanması.

## 4. Öncelik sıralı öneri

1. **A1 + A8** (sohbetten hatırlatma, Telegram arka planı) — günlük kullanımda en çok hissedilen boşluk.
2. **D1/E** — gerçek Windows makinesinde doğrulama; buradaki tek büyük kör nokta.
3. **A4 + A5** (kalıcı sohbet geçmişi, defter dışa aktarma) — veri güvenliği hissi.
4. **C1-C3** (erişilebilirlik) — düşük efor, yüksek kazanç.
5. **B1 + D4** (disk şifreleme, indirme doğrulama) — güvenlik sertleştirme.
6. **A2, A7** — büyük özellikler; ayrı tasarım gerektirir.
