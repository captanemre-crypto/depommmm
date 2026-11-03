# EMRE — Windows yerel sürümü

## Başlatma
1. Windows için Python 3 ve Ollama kurun; Python kurulumunda PATH seçeneğini açın.
2. PowerShell'de `ollama run qwen2.5-coder:7b` ile modeli indirin. `/bye` ile çıkın; Ollama arka planda çalışmalı.
3. Bu klasörde `py server.py` çalıştırın. Tarayıcıda http://127.0.0.1:8765 açın. HTML dosyasını doğrudan açarsanız yerel sunucu işlevleri çalışmaz.
4. Farklı model için sunucuyu başlatmadan önce `$env:EMRE_MODEL="qwen3:8b"` yazın.

## Telegram botu (isteğe bağlı)
BotFather ile bot oluşturun. Anahtarı kimseyle paylaşmayın. PowerShell'de `$env:TELEGRAM_BOT_TOKEN="BOT_ANAHTARINIZ"` yazıp aynı pencerede `py server.py` başlatın. Anahtar dosyaya kaydedilmez, ancak ortam değişkenine erişebilen yerel süreçler anahtarı görebilir. Botla Telegram'da önce mesajlaşın; sol menüde Telegram ile gelen mesajları görüntüleyin. Gönderme öncesi onay istenir. Bot kişisel hesabın tüm sohbetlerine erişemez. getUpdates başka bir bot istemcisi/webhook ile çakışabilir; özel/kalıcı mesaj geçmişi sağlamaz.

## Hatırlatıcılar
Yerel SQLite dosyasında saklanır. Bildirimler yalnızca sayfa açıkken ve tarayıcı bildirim izni varsa görünür; arka planda Windows hizmeti kurulmaz.

## Sınırlar ve güvenlik
Sunucu yalnızca 127.0.0.1'e bağlıdır; telefondan erişim henüz yoktur. Sayfayı ve erişim anahtarını yalnızca güvenilir yerel kullanıcılarla paylaşın. Yerel uygulamalara erişimi olan kötü amaçlı yazılımlara karşı koruma sağlamaz. Kamera önizlemesi görüntülü görüşme veya görüntü analizi değildir. Windows uygulama kontrolü, otonom kod değiştirme, gerçek internetten bilgi çıkarma, kalıcı sohbet hafızası, uyandırma sözcüğü ve yerel ses motorları henüz uygulanmadı. Mikrofon ve ses tarayıcıya bağlıdır; erkek Türkçe ses garanti edilmez. AI tarafından önerilen komutlar otomatik çalıştırılmaz. Mikrofon dinlemesi açıkken tarayıcının ses tanıma servisi ses verisini buluta gönderebilir.

## Alacak & verecek defteri
Sol menüde Alacak verecek bölümünden kişi, işlem türü ve TL tutarı girin. Alacak size borçlu olunan, verecek sizin borcunuzdur; tahsilat alacağınızı, ödeme vereceğinizi azaltır. Aynı isimle kaydedilenler gruplanır; fazla tahsilat/ödeme negatif bakiye gösterebilir. İsteğe bağlı hatırlatıcı için tarih ve saat girin. Kayıtlar emre.sqlite3 dosyasında yerel tutulur; bu dosyayı düzenli yedekleyin. Şifreleme ve çok kullanıcılı erişim yoktur. İşlem silinirse bağlı hatırlatıcı otomatik silinmez; Hatırlatıcılar bölümünden tamamlayın. Bildirimler yalnızca açık sayfada kontrol edilir. Bu basit kişisel takip aracıdır, profesyonel muhasebe yazılımı değildir.

## Model seçimi
Ayarlar bölümünden Ollama'da yüklü modelleri listeleyip seçim yapın. Seçim tarayıcıda saklanır ve model değiştirilince sohbet bağlamı sıfırlanır. Yeni modeli önce `ollama pull MODEL_ADI` ile indirin; Ayarlar'da Listeyi yenile düğmesine basın. Ollama çalışmıyorsa liste yüklenmez. Telefonda alt menüyü yana kaydırarak Ayarlar bölümüne ulaşabilirsiniz.

## Arena tarayıcı bağlantısı (deneysel)
PowerShell'de `py -m pip install playwright` çalıştırın (otomasyon yüklü Microsoft Edge kanalını kullanır, ayrıca Chromium indirilmez). Sunucuyu yeniden başlatın. Keşfet > Arena tarayıcısını aç ile açılan tarayıcıda Arena hesabınıza giriş yapın ve güvenlik doğrulamalarını kendiniz tamamlayın. Soruyu yazıp onaylayarak gönderin. Bağlantı yalnızca tanımlanabilen asistan yanıtlarını okur; Arena arayüzü değişirse veya bu tanımlayıcıları kullanmıyorsa yanıtı bulamayabilir. CAPTCHA atlatılmaz. Yanıtın doğru ve tamamlanmış olduğunu Arena ekranında kontrol edin; kısa süreli duraklamalar tamamlanma sanılabilir. Oturum çerezleri `arena_profile` klasöründe saklanır: bu klasörü başkalarıyla paylaşmayın ve yedeklerken kişisel bilgi içerdiğini unutmayın. Profil silinirse tekrar giriş gerekir. Sorular ve cevaplar Arena servisine gönderilir; hizmet şartları ve gizlilik kuralları geçerlidir. Bu özellik otomatik ihtiyaç tespiti yapmaz; her soru kullanıcı tarafından onaylanır.

## başlat.bat
Windows'ta klasördeki `baslat.bat` dosyasına çift tıklayın. Python 3 kurulu olmalıdır. Playwright kurulu değilse Arena için kurmayı teklif eder; onay verirseniz yalnızca Playwright paketi indirilir. Kurulumu reddederseniz Emre yine açılır fakat Arena otomasyonu çalışmaz. Tarayıcıda http://127.0.0.1:8765 adresini açın. Otomasyon Microsoft Edge ile çalışır; Edge kurulu değilse `py -3 -m playwright install chromium` alternatif olarak denenebilir (kod Edge kanalını istediği için önerilmez). Açık eski sunucuyu önce Ctrl+C ile kapatın.

Arena otomasyonu yüklü Microsoft Edge ile açılır. Oturum ayrı arena_profile klasöründe tutulur; kişisel Edge profili otomatik kullanılmaz. Google otomasyonlu Edge girişine de izin vermeyebilir.

## OpenJarvis entegrasyonu ve CPU
Emre OpenJarvis'i kurmaz; masaüstü sürümü mevcut OpenJarvis projesini seçerseniz otomatik başlatabilir. OpenJarvis, Ollama'dan ayrı bir yerel servis olarak çalışır. Doğrudan Ollama seçildiğinde Emre `num_gpu: 0` gönderir; OpenJarvis seçeneğinde aşağıdaki CPU modeli gerekir.

1. Ollama açıkken, bu klasörde `ollama create emre-cpu -f Modelfile.emre` çalıştırın. Dosya taban modeli `qwen2.5-coder:7b` kullanır; gerekirse önce `ollama pull qwen2.5-coder:7b` ile indirin. Zaten `emre-cpu` adında farklı bir model varsa bu komut adı güncelleyebilir: önce `ollama list` ile kontrol edin.
2. OpenJarvis'i resmi dokümantasyona göre ayrı bir klasöre kurun. Windows kurulumunun Python ve derleyici gereksinimleri olabilir; bilgisayarınızda Python 3.15 varsa uyumluluğunu kontrol edin. Dokümantasyon: https://github.com/open-jarvis/OpenJarvis/blob/main/docs/getting-started/windows-native.md . Kurulum üçüncü taraf yazılım indirir; kodu inceleyin ve yalnızca istiyorsanız kurun.
3. OpenJarvis ortamında `uv run jarvis serve --host 127.0.0.1 --port 8766 --engine ollama --model emre-cpu --agent simple` komutunu çalıştırın. LUX FUTURES 8000 portunu kullandığından 8766 kullanılır. Yalnızca loopback arayüzünü kullanın. OpenJarvis araç yetkilerini varsayılan olarak açmadan önce kendi yapılandırmasını inceleyin.
4. Emre'yi ayrı pencerede başlatın. Ayarlar > Ollama modeli bölümünde `emre-cpu` seçin; Ayarlar > OpenJarvis bölümünde OpenJarvis'i seçip kaydedin. Normal sohbet için ayrı, açık bir yerel sunucu gerekir.
5. Yanıt üretilirken başka bir terminalde `ollama ps` çalıştırıp PROCESSOR sütununda CPU kullanımını doğrulayın. Model ayarları diğer süreçlerce değiştirilebilir; CPU kullanımı bu testle kesinleştirilmelidir.

OpenJarvis bağlantısı hazırlık aşamasındadır ve hedef Windows makinede veya gerçek OpenJarvis sunucusuyla uçtan uca test edilmemiştir. Araç çağrıları model ve sürüme bağlıdır; hata halinde deftere kayıt yapılmış gibi kabul etmeyin. Çalıştırılan üçüncü taraf araçlar ve ağ erişimi için OpenJarvis'in kendi izin ve ayarlarını kontrol edin. Bu entegrasyon ticari botta emir verme yetkisi eklemez.

## Türkçe yerel ses tanıma (deneysel)
`ses_kur.bat` dosyasını çalıştırın. Onay verirseniz Python 3.12 ortamına faster-whisper kurar ve çok dilli Whisper `base` modelini indirir. İndirme için internet, sonrasında ses tanıma için CPU ve yerel model dosyaları gerekir. Emre sunucusunu yeniden başlatın, Chrome/Edge üzerinden 127.0.0.1:8765 adresini açın ve mikrofon izni verin. Ses WebM/Opus olarak yalnızca yerel sunucuya gönderilir; geçici dosya olarak işlenip normal işlem sonunda silinir (beklenmedik kapanmada dosya kalabilir). Model doğruluğu ortam gürültüsü, mikrofon ve donanım hızına bağlıdır. Sesli okuma ayrı tarayıcı özelliğidir ve yerel olması garanti değildir. İlk istekte model yüklenmesi zaman alır. Güvenilir olmayan konuşmaları deftere kaydetmeden önce kontrol edin. Model indirmenin ve paketlerin kaynakları ile lisanslarını inceleyin.

## Yerel konuşma sesi
Ayarlar > Ses ekranından Windows System.Speech tarafından sunulan Türkçe sesleri listeleyip birini seçin ve örneğini dinleyin. Üretilen ses bilgisayarda kalır; hafif reverb tarayıcıda uygulanır. Windows'da kullanılabilir Türkçe/erkek SAPI sesi bulunmayabilir; Windows ayarlarındaki seslerin hepsi System.Speech'e görünmeyebilir. Seçilen ses örnek seste duyulan sesin aynısı değildir. Uygulama Windows, izinli yerel sunucu ve destekli AudioContext gerektirir; gerçek Windows üzerinde test edilmelidir.

## Piper yerel Türkçe konuşma modeli
`ses_model_kur.bat` onayla `piper-tts` ve Fahrettin ile Fettah Türkçe modellerini `sesler` klasörüne indirir. Model kartları eğitim verisi için CC0 belirtir; Piper yazılımı ve modellerin kendi lisanslarını ayrıca inceleyin. Önceden indirilmiş dfki modeli ayrı bir seçenektir ve veri lisansı CC BY-NC-SA 4.0 olarak belirtilir. Kurulumdan sonra Emre'yi yeniden başlatıp Ayarlar > Ses'te sesi seçin. Sesler beğenilen servis sesinin aynısı değildir. Konuşma CPU'da yerel üretilir. Windows'ta uçtan uca test edilmemiştir.

## Windows masaüstü prototipi
`masaustu_kur.bat` ile pywebview, pystray ve Pillow'u ayrı `.venv-desktop` ortamına kurun; Edge WebView2 Runtime gerekli olabilir. Önce `baslat.bat` ile çalışan eski Emre sunucusunu kapatın, ardından `masaustu_baslat.bat` çalıştırın. İlk aşamada `.exe` değil, Python tabanlı prototiptir. X düğmesi çalışan sistem tepsisi simgesi varsa pencereyi gizlemeyi dener; simge menüsünden yeniden aç veya tamamen çık seçilir. Tepsi erişilemiyorsa pencerenin kapanmasına izin verilir. Başlangıç dosyaları ve emre.sqlite3 aynı klasörde kalmalıdır. Kurulumda mevcut OpenJarvis proje klasörünü (pyproject.toml içeren klasör) seçin; EMRE kısayolu masaüstüne oluşturulur. Emre, OpenJarvis servisinin 127.0.0.1:8766 üzerinde çalıştığını algılamazsa arka planda başlatmayı dener. İlk açılış zaman alabilir; hata için openjarvis_masaustu.log dosyasını inceleyin. Ollama ve emre-cpu modeli ayrıca hazır olmalıdır. Ayarlar > OpenJarvis bölümünde OpenJarvis seçimini kaydedin. Tamamen çıkıldığında yalnız Emre tarafından başlatılan servis durdurulur; önceden açık servis kapatılmaz. Mikrofon/kamera ve bildirim izinleri WebView2'de yeniden istenebilir. Pencere gizlenince ses tanıma ve hatırlatma zamanlaması sistemin WebView2 davranışına bağlıdır; gerçek Windows üzerinde doğrulanmadı, arka planda sürekli çalışacağı garanti değildir. WebView2'nin sohbet geçmişi normal Chrome/Edge geçmişinden ayrıdır. Geliştirme sürümüdür, güvenli finansal kararlar için denetimsiz kullanmayın.

## Testler ve otomatik denetim
Projede standart kütüphaneyle çalışan bir test paketi vardır; ek paket kurmak gerekmez.

```powershell
py -m unittest discover -s tests -t .     # Windows
testler.bat                                # Windows (çift tıkla)
```
```bash
python3 -m unittest discover -s tests -t .  # Linux/macOS
```

**579 test**; defter araçları, tutar ayrıştırma, Türkçe zaman ayrıştırma, sohbetten hatırlatıcı, HTTP yetkilendirmesi (token + Origin + Host), defter/hatırlatıcı/dışa aktarma akışı, girdi doğrulaması, Arena köprüsü durum makinesi (sahte Playwright), Piper model doğrulaması, yerel ses işçisi zaman aşımı, uyandırma sözcüğü, kişisel bellek, MCP istemcisi (sahte stdio sunucu), ekran görüntüsü, global kısayol, masaüstü bildirimi, otomatik başlatma, web araması, akışlı yanıt, beceri sistemi, denetim izi, tanılama, bellek yedeği, sağlayıcı yedek modeli, günlük özet, görsel üretimi, arayüz erişilebilirliği (kontrast), akışlı seslendirme/söz kesme, belge okuma ve belgeye soru sorma, `.ics` takvim ve `.eml`/`.mbox` posta okumayı kapsar. GitHub Actions (`.github/workflows/ci.yml`) her push ve pull request'te Python 3.11 ve 3.12 üzerinde sözdizimi kontrolü ile testleri çalıştırır. Tarama sonuçlarının tamamı `DENETIM.md` (statik) ve `E2E_DENETIM.md` (uçtan uca) dosyalarındadır.

### Arayüz uçtan uca testi (isteğe bağlı, Node gerekir)
`tools/e2e` gerçek sunucu ve gerçek `index.html` üzerinde arayüzü jsdom ile sürer (51 kontrol).

```bash
python3 tools/e2e/baslat.py      # ayrı terminal, geçici veritabanı
cd tools/e2e && npm install && npm test
```

Node yalnızca bu test aracı için gerekir; uygulamanın kendisi Node kullanmaz.

## Depoda tutulmayan dosyalar
`.gitignore` şu yerel dosyaları dışarıda bırakır: `emre.sqlite3` ve WAL dosyaları, `.venv-ses/`, `.venv-desktop/`, `sesler/`, `kodlar/`, loglar, `openjarvis_yol.json` ve **`arena_profile/`**.

`arena_profile/` Arena oturum çerezlerini içerir; hiçbir zaman commit edilmemeli, yedeklerken kişisel veri sayılmalıdır. OpenJarvis klasör ayarı kişiye özeldir; şablon `openjarvis_yol.ornek.json`, gerçek dosyayı `masaustu_ayar.py` üretir.

## İsteğe bağlı bağımlılıklar
Sunucu yalnızca standart kütüphaneyi kullanır. İsteğe bağlı özelliklerin paketleri ve sürüm aralıkları `requirements-optional.txt` dosyasında listelenir; kurulumları ilgili `.bat` dosyaları ayrı sanal ortamlara yapar.

## Sürüm notları (2026-11-02 · ikinci tur)
- **Tahsilat cümleleri düzeltildi:** "tahsil" kelimesi "sil" içerdiği için silme sanılıyor ve kayıt sessizce yutuluyordu.
- Binlik ayırıcılı tutarlar (`1.000.000 TL`) artık kabul ediliyor; tek cümlede birden fazla tutar varsa kayıt yapılmıyor.
- Mükerrer hesaplarda Türkçe uyarı; `İlker`/`ilker` aynı hesap sayılıyor.
- **Güvenlik:** `Host` başlığı doğrulanıyor (DNS rebinding), `X-Frame-Options: DENY`, chunked gövde desteği.
- Hatırlatıcı silme, 403 sonrası "sayfayı yenile" yönlendirmesi, port dolu mesajı.
- `baslat.bat` gereksiz Chromium indirmiyor; sanal ortam kurulumu Python 3.12 yoksa kurulu sürüme düşüyor.
- Arayüz E2E test paketi (`tools/e2e`) ve CI'da arayüz işi.

## Sürüm notları (2026-11-02 · ilk tur)
- SQLite bağlantıları artık her istekten sonra kapatılıyor (dosya tanıtıcısı sızıntısı giderildi) ve veritabanı WAL modunda.
- Yerel ses işçileri zaman aşımına uğradığında öldürülüp otomatik yeniden başlatılıyor; ses özellikleri kilitlenmiyor.
- Hata mesajları Türkçeleştirildi; bozuk istek gövdeleri ve yanlış alan tipleri 400 ile reddediliyor.
- Telegram mesajları `update_id` imleciyle izleniyor; aynı mesaj tekrar gösterilmiyor.
- Arayüzdeki "Sistem durumu" ve "Yaklaşan hatırlatıcılar" panelleri artık canlı veriyle güncelleniyor.
- `/favicon.ico` sunuluyor, yanıtlara `nosniff` ve `no-referrer` başlıkları eklendi.

## Sohbetten hatırlatıcı
"Sohbet" bölümünde doğal Türkçe ile hatırlatıcı kurabilirsin: `yarın 09:00 Ahmet'i ara diye hatırlat`, `3 gün sonra saat 18:00 sunum`, `15 Kasım 14:30 fatura`, `pazartesi sabah 9 kontrol`, `akşam 8 ilaç`, `5 dk sonra çay`, `15.11.2026 14:30 toplantı`.
Tarih/saat anlaşılamazsa kayıt **yapılmaz** ve desteklenen biçimler örneklenir; geçmiş bir zaman da reddedilir. Bu yol modelden bağımsızdır: Ollama kapalıyken de çalışır. Aynı cümlede defter işlemi varsa (örn. `Ahmete 1.500 TL alacak ekle yarın hatırlat`) hem defter kaydı hem hatırlatıcı oluşturulur.

## Kalıcı sohbet geçmişi
Her sohbet mesajı `emre.sqlite3` içindeki `messages` tablosuna yazılır (oturum kimliğiyle). Sohbet sayfasındaki **Sunucu geçmişi** panelinden oturumlar listelenir, birine tıklayınca mesajlar yüklenir. Bu geçmiş tarayıcı depolamasından bağımsızdır: masaüstü sürümü (WebView2) ile tarayıcı aynı kaydı görür. `POST /api/history/delete` ile oturum veya tüm geçmiş silinebilir.

## Defter ve yedek dışa aktarma
Defter sayfasındaki **⤓ CSV** düğmesi tüm hareketleri `;` ayırıcı ve UTF-8 BOM ile indirir (Excel'de Türkçe karakterler doğru görünür). **⤓ Yedek** düğmesi hesaplar, defter, hatırlatıcılar ve sohbet geçmişini tek JSON dosyasında toplar. Uçlar: `GET /api/ledger/export?format=csv|json`, `GET /api/backup`. Defter okuması `limit`/`offset` ile sayfalanır (varsayılan 500, üst sınır 2000).

## Telegram arka plan yoklaması
Bot anahtarı bağlandığında sunucu, Telegram'ı **uzun yoklama** ile dinleyen bir arka plan iş parçacığı başlatır. Gelen mesajlar veritabanına yazılır, okunmamış sayısı Ayarlar'da ve Telegram bölümünde görünür. `getUpdates` imleci (offset) veritabanında tutulduğu için sunucu yeniden başladığında aynı mesaj tekrar gösterilmez. Arayüz yalnızca yerel API'yi okur; Telegram'a doğrudan bağlanmaz. Uçlar: `GET /api/telegram/updates`, `POST /api/telegram/mark-read`, `POST /api/telegram/poll`.

## Denetim izi
Defter kayıtlarında `source` (`manual` veya `chat`) ve `raw_text` (kaydı tetikleyen cümle) kolonları tutulur; eski veritabanları açılışta otomatik güncellenir (ALTER TABLE). `GET /api/ledger` yanıtı `source` alanını da döndürür.

## Ses modeli indirme doğrulaması
`ses_model_kur.bat` / `piper_indir.py` indirilen dosyaları boyut ve JSON yapısı açısından doğrular, SHA-256 özetini hesaplar ve `sesler/<dosya>.sha256` olarak saklar. Sonraki çalıştırmalarda özet uyuşmazsa dosya kullanılmaz. Hugging Face yayınlanmış bir sağlama listesi vermediği için bu "ilk kullanımda güven" yöntemidir; ilk indirmenin güvenilirliği kaynağa (HTTPS) bağlıdır.

## Geliştirme araçları
`pyproject.toml` içinde ruff yapılandırması vardır: `ruff check .` (CI'da zorunlu adım). Arayüz E2E paketi `tools/e2e` altındadır ve CI'da ayrı iş olarak çalışır.

## Bilinen sınırlar (2026-11-02 itibarıyla)
- **Web'den bilgi alma yok:** "ara" komutu Google'ı yeni sekmede açar; asistan içeriği okumaz/özetlemez.
- **Uyandırma sözcüğü yok:** mikrofon düğmeyle açılır.
- **Arka plan hatırlatma servisi yok:** bildirim yalnızca sayfa/WebView açıkken ve izin verildiğinde görünür; Windows hizmeti kurulmaz.
- **Veritabanı şifrelenmez:** `emre.sqlite3` düz metindir; disk şifrelemesi işletim sistemi düzeyinde yapılmalıdır.
- **Telefon erişimi yok:** sunucu yalnızca `127.0.0.1` dinler.
- **Windows üzerinde uçtan uca doğrulanmadı:** SAPI/Piper sesleri, WebView2, tepsi simgesi, `.bat` akışları ve OpenJarvis süreç yönetimi gerçek makinede denenmelidir.
- **Lisans dosyası yok:** kamuya açık paylaşım öncesi lisans seçilmelidir.

## Ücretsiz yapay zekâ (Ollama zorunlu değil)

Emre artık **OpenAI uyumlu** her sohbet servisine bağlanabilir. Ollama kurulu olmasa da asistan çalışır:

1. Ayarlar → **Ücretsiz API** sekmesini aç.
2. Hazır servislerden birini seç (adres otomatik dolar) veya kendi `/v1` adresini yaz.
3. **Modelleri getir** ile model listesini çek (`:free` olan modeller listede başa alınır ve ★ ile işaretlenir).
   - Emin değilsen **Yerel geçitleri tara** düğmesine bas: Emre kendi bilgisayarındaki bilinen geçit portlarını (20128, 20130, 11434, 1234, 8080, 8787) yoklar ve açık olanı "Kullan" ile forma doldurur. Anahtar isteyen geçitler "anahtar istiyor" diye ayrıca işaretlenir.
4. Bir model seç, **Bağlan ve kaydet**'e bas. Bağlantı kesilene kadar sohbetler bu sağlayıcı üzerinden yürür.

> **Not:** 9Router, OmniRoute ve FlagshipRouter varsayılan olarak aynı **20128** portunu kullanır; aynı anda yalnızca biri çalışabilir. 9Router Go 20130'u kullanır, ikisi birlikte çalışabilir.

| Servis | Adres | Anahtar | Not |
| --- | --- | --- | --- |
| **9Router** (önerilen, yerel) | `http://127.0.0.1:20128/v1` | panelden alınır (`sk_...`) | `npm i -g 9router` → `9router`; panel `http://localhost:20128/dashboard`. Tek uç nokta, sağlayıcı rotasyonu + combo (yedekleme) desteği; model adları `kr/claude-sonnet-4.5`, `if/kimi-k2-thinking` gibi ön ek taşır |
| **9Router Go** | `http://127.0.0.1:20130/v1` | panelden alınır | Tek dosyalık Go sürümü; Node.js gerekmez, portu 20130 |
| **OmniRoute** (yerel, alternatif) | `http://127.0.0.1:20128/v1` | gerekmez (yerelde `auto` modeli) | `npm i -g omniroute` ile kurulur, kendi bilgisayarında çalışır, birden çok ücretsiz sağlayıcıyı sırayla dener |
| OpenRouter | `https://openrouter.ai/api/v1` | gerekli | `:free` ekiyle biten modeller ücretsizdir, günlük istek sınırı vardır |
| Groq | `https://api.groq.com/openai/v1` | gerekli | hızlı çıkarım, günlük ücretsiz kota |
| Cerebras | `https://api.cerebras.ai/v1` | gerekli | günlük token kotası |
| Gemini (OpenAI uyumlu) | `https://generativelanguage.googleapis.com/v1beta/openai` | gerekli | ücretsiz katman, model adı `gemini-2.5-flash` gibi yazılır |

Önerilen ücretsiz modeller: sohbet için `meta-llama/llama-3.3-70b-instruct:free`, araç (defter/hatırlatıcı) çağrıları için `openai/gpt-oss-120b:free` veya `cohere/north-mini-code:free`.

### Güvenlik ve gizlilik

- API anahtarı yalnızca bu bilgisayarda, `saglayici_ayar.json` dosyasında **0600** izinle saklanır; dosya `.gitignore` içindedir ve arayüze yalnızca son dört karakteri (`…1234`) döner.
- Uzak sağlayıcılarda adres **https://** olmak zorundadır; `http://` yalnızca kendi bilgisayarındaki adresler (OmniRoute gibi) için kabul edilir. Böylece anahtar şifresiz ağda taşınmaz.
- Adres içine kullanıcı adı/parola yazılamaz (`https://kullanici:parola@host` reddedilir).
- Mesajlar seçtiğin sağlayıcıya gider; ücretsiz katmanlarda "gönderilen metin eğitimde kullanılabilir" maddesi bulunabilir. Gizli bilgi yazacaksan yerel Ollama veya OmniRoute (yerel ağ geçidi) kullan.
- Kotan dolduğunda sağlayıcı `429` döner; Emre bunu Türkçe açıklar, başka model seçebilir veya Ollama'ya dönebilirsin.
- Ücretsiz kotalar servis sağlayıcıya göre değişir; tablodaki değerler garanti değildir.

### Sunucu uç noktaları

| Uç nokta | Açıklama |
| --- | --- |
| `GET /api/provider/status` | bağlı mı, adres, model, maskeli anahtar ve hazır servis listesi |
| `POST /api/provider/models` | `{base_url, key}` → model listesi ve ücretsiz (`:free`) modeller ayrıca |
| `POST /api/provider/scan` | `{ports:[...]}` → yalnız `127.0.0.1` üzerindeki bilinen geçit portlarını yoklar; açık olanları, model sayısını ve anahtar gerekip gerekmediğini döner |
| `POST /api/provider/connect` | `{base_url, key, model, confirmed:true}` → model listede yoksa reddeder |
| `POST /api/provider/disconnect` | `{confirmed:true}` → anahtarı siler, Ollama'ya döner |
| `POST /api/chat` | `backend:'api'` ile ücretsiz sağlayıcı kullanılır; `ollama` varsayılan kalır |

## Kapanış turu: erişilebilirlik, uzun sohbet ve erişim rehberi (2026-11-03 · sekizinci tur)

Yol haritasındaki son açık başlıklar kapatıldı; bu tur yeni özellik değil, **kalite ve güvenlik** turudur.

### 1. Erişilebilirlik: WCAG AA kontrast + otomatik test

- Koyu temada okunurluğu düşük olan yardımcı metinler düzeltildi:
  palet alt yazısı `3.87 → 5.96`, “Bugün” kartı saat satırı `4.28 → 5.78`, palet küçük yazı `3.93 → 5.10`.
- Yeni `tests/test_arayuz_erisim.py` (11 test) renk çiftlerini **tarayıcı çalıştırmadan** hesaplar:
  13 koyu tema + 5 açık tema çifti ≥ 4.5:1 olmalı. Renk değiştirilirse test uyarır.
- Aynı test dosyası yapısal kontrolleri de yapar: palet `role="dialog"` + `aria-modal`, `Bugün` kartının
  `aria-labelledby` bağlantısı, 12+ ayar sekmesinin `role="tab"` işaretleri, `?` kısayol yardımının varlığı,
  “henüz hazırlanmadı” gibi yarım kalmış metinlerin **bulunmaması**.

### 2. Uzun sohbet: DOM sınırı

- Sohbet görünümünde en fazla **300 mesaj** tutulur; daha eskiler DOM'dan çıkarılır.
  Sunucu geçmişi ve tarayıcı kaydı silinmez; üstte “Daha eski mesajlar bu görünümden kaldırıldı…”
  bilgi satırı görünür.
- Böylece saatlerce açık kalan pencerede bellek/düzen bozulması ve kaydırma yavaşlaması önlenir.

### 3. `?` kısayol yardımı

- Klavyeden `?` (Shift + `/`) kısayol panelini açar: `/`, `Ctrl+K`, `?`, `Esc`, `↑ ↓ · Enter`,
  `Ctrl+Alt+D` (global dikte) ve mikrofon düğmesi.
- Palete **Kısayollar** komutu da eklendi (16 komut).

### 4. Temizlik

- Navigasyonda ulaşılamayan “bölümü henüz hazırlanmadı” ve “özelliği henüz bağlı değil” yedek mesajları kaldırıldı;
  artık her menü öğesi gerçek bir ekrana gider.

### 5. Telefondan erişim (C5) — kod değişikliği yok

- Sunucu **yalnızca `127.0.0.1`** dinlemeye devam ediyor.
- Güvenli yol adım adım yazıldı: **[`UZAK_ERISIM.md`](UZAK_ERISIM.md)** — Tailscale özel ağı + SSH tüneli,
  Emre yine yerel adreste kalır. Port yönlendirme ve herkese açık tüneller açıkça **önerilmiyor**.

### Testler

`tests/test_arayuz_erisim.py` +11 → **579 test**. Arayüz E2E **60/60** (yeni kontroller: `?` yardımı, uzun sohbet sınırı).

## Bugün özeti, komut paleti, tema ve görsel üretimi (2026-11-03 · yedinci tur)

Bu tur `YOL_HARITASI.md` içindeki **D1, D2, D3** ve **B5** maddelerini kapatır. Yol haritasındaki tüm maddeler bitti;
yalnızca “bilinçli olarak yapılmayacaklar” listesi (telefondan erişim, tam tarayıcı erişimi) açık.

### 1. “Bugün” kartı (D1)

Ana sayfanın üstünde tek bakışta günlük durum:

- **Hatırlatıcılar**: gecikenler (⚠ kırmızı), bugün olanlar ve önümüzdeki 7 gün.
- **Defter**: alacak/verecek bakiyesi ve kayıt sayısı.
- **Takvim**: bugünün etkinlikleri (takvim yolu tanımlıysa).
- **Bellek ve belgeler**: son 3 bellek kaydı ve ekli belge sayısı.

Kart açılışta ve sekme görünür olduğunda yüklenir, 2 dakikada bir tazelenir; “Yenile” düğmesiyle elle yenilenir.
Tüm veriler tek istekte gelir ve hiçbir dış bağlantı kurulmaz.

| Uç nokta | Açıklama |
| --- | --- |
| `GET /api/today` | `{tarih, hatirlaticilar:{geciken,bugun,yaklasan,toplam}, defter:{alacak_tl,verecek_tl,kayit}, bellek:[…], belgeler, takvim:{path,etkinlikler,error}}` |

### 2. Komut paleti (D2)

- `/` veya `Ctrl+K` (macOS'ta `⌘K`) ile açılır; yazarken filtrelenir.
- `↑` `↓` ile gez, `Enter` ile çalıştır, `Esc` ile kapat. Palet dışına tıklamak da kapatır.
- 15 komut: sohbet, yeni sohbet, hatırlatıcılar, defter, Telegram, uygulamalar, geliştirici, ayarlar, belgeler,
  takvim ve posta, görünüm, görsel üret, bugünü yenile, mikrofonu aç/kapat, sistemi tanı.
- Ana sayfadaki **⌘ Komutlar** düğmesi de paleti açar (klavye kullanmayanlar için).
- `Esc` ayrıca açık onay pencerelerini kapatır.

### 3. Tema ve yazı boyutu (D3)

- Ayarlar › **Görünüm**: **Koyu** (varsayılan), **Açık**, **Sistemle aynı**.
- Yazı boyutu: 13 / 14 / 16 / 18 px.
- Seçimler yalnızca bu tarayıcıda (`localStorage`) saklanır; sunucuya yazılmaz. Açık tema tüm ana panellerde
  (sohbet, ayarlar, defter, bugün kartı, palet) geçerlidir.

### 4. Görsel üretimi (B5)

- Ayarlar › Görünüm › **Görsel üretimi**: kullanılan görsel modeli adı kaydedilir; “Görsel üret panelini aç” düğmesi paneli açar.
  Paletten de **Görsel üret** komutuyla ulaşılır.
- İstem + boyut seçilir, **onay** verilir; görsel, Ayarlar › Ücretsiz API bölümünde bağlı sağlayıcının
  `/images/generations` ucunda üretilir ve `data:` adresiyle gösterilir. İndirmek istersen “Görseli indir”e basarsın.
- **Görsel diske yazılmaz**, sunucuda saklanmaz. Sağlayıcı görseli bağlantı (URL) olarak döndürürse Emre
  güvenlik gereği indirmez ve açık hata verir.
- Ücretsiz modellerin çoğu görsel üretmez; sağlayıcı desteklemiyorsa “Sağlayıcı görsel üretemedi…” mesajı gelir.

| Uç nokta | Açıklama |
| --- | --- |
| `POST /api/image/generate` | `{prompt, size?, confirmed:true}` → `{ok, image(base64), mime, model, size}` |
| `POST /api/image/model` | `{model}` → görsel modeli ayarını kaydeder (boş gönderim kaldırır) |

### 5. Yapılmayan: telefondan erişim (C5)

Sunucu yalnızca `127.0.0.1` dinler ve bu değişmedi. Telefondan erişim için sunucuyu dışarı açmak token + TLS +
güncelleme yönetimi gerektirir; “yalnızca bu bilgisayar” sınırını bozar. İhtiyaç olursa önerilen yol: ayrı bir tünel
(Tailscale/WireGuard) kurup Emre'yi yine yerel adreste bırakmak. Bu turda **kod değişikliği yapılmadı**.

### Testler

`test_server.py` +8 (bugün özeti, görsel üretimi uçları), `test_saglayici.py` +7 (`gorsel` yolu, sahte görsel ucu)
→ **568 test**. Arayüz E2E **58/58** (“Bugün” kartı, komut paleti, tema/yazı boyutu, görsel paneli kontrolleri eklendi).

## Akışlı seslendirme, belge okuma, takvim ve posta (2026-11-03 · altıncı tur)

Bu tur `YOL_HARITASI.md` içindeki **B2**, **B3** ve **B4** maddelerini kapatır. Hepsi **standart kütüphane** ile
çalışır: ek paket, bulut hesabı veya dış ağ bağlantısı yoktur.

### 1. Akışlı seslendirme + söz kesme (B2)

- Yanıt yazılmaya başlar başlamaz **ilk cümle** seslendirilir; kalan cümleler arka planda hazırlanır.
  Böylece 10 saniyelik bir yanıtın tamamı beklenmez (`sesli_yanit.AkisParcalayici`).
- Kısaltmalar (`Dr.`, `vb.`, `14.30`) cümle sonu sayılmaz; çok uzun cümleler kelime sınırından bölünür (en fazla 220 karakter).
- **Söz kesme (barge-in)**: mikrofon açıkken okuma sürerken sen konuşmaya başlarsan Emre susar ve seni dinlemeye geçer.
  Yanlış tetiklemeyi önlemek için eşik üstünde **3 ardışık ölçüm** gerekir (`sesli_yanit.BargeIn`).
- Ayar: Ayarlar › Ses › **Akışlı seslendirme** ve **Söz kesme** anahtarları (varsayılan açık).
  Kapalıyken eski davranış: yanıt bittiğinde tek parça okunur.

| Uç nokta | Açıklama |
| --- | --- |
| `POST /api/system/tts` | `{akis?: bool, barge_in?: bool}` → anahtarları kaydeder |
| `POST /api/tts/split` | `{text}` → `{sentences:[…]}` (cümlelere bölme; istemci de aynı mantığı kullanır) |

### 2. Belge okuma ve belgeye soru sorma (B3)

- Ayarlar › **Belgeler** sekmesinden PDF, Word (`.docx`), `.txt`, `.md`, `.csv`, `.json`, `.log`, `.html` ekle.
- Dosya **hiçbir yere yüklenmez**; sunucu metni çıkarır, sayfalara ve ~900 karakterlik parçalara böler,
  `docs` / `doc_chunks` tablolarına yazar. Tarayıcı yalnızca dosyayı base64 olarak yerel sunucuya iletir.
- **Belgeye sor**: soruyla en çok eşleşen bölümler bulunur, modele `[1] dosya · sayfa N` biçiminde kaynak verilir
  ve yanıtta kaynak numarası istenir. Ekranda kaynak listesi (dosya + sayfa) gösterilir.
- Arama Türkçe aksan duyarsızdır: `sukru` → `Şükrü`, `CARSAMBA` → `Çarşamba`.
- Sohbette `doc_id` gönderilirse (veya `belgeye sor: …` yazılırsa) ilgili bölümler sohbet bağlamına eklenir.
- Sınırlar: 20 MB dosya, 2000 sayfa, parça başına 900 karakter. **Taranmış (görüntü) PDF'lerde OCR yoktur**;
  metin bulunamazsa açık hata döner.

| Uç nokta | Açıklama |
| --- | --- |
| `POST /api/docs/import` | `{confirmed:true, name, content(base64)}` **veya** `{confirmed:true, path:'C:\\…\\a.pdf'}` |
| `GET /api/docs` | `{docs:[{id,name,kind,pages,chars,created}]}` |
| `POST /api/docs/delete` | `{id, confirmed:true}` → `{deleted}` (parçalar da silinir) |
| `POST /api/docs/ask` | `{question, id?}` → `{reply, sources:[{name,sayfa}], docs}` |

### 3. Takvim ve posta (B4) — salt okunur

- **Takvim**: `.ics` dosyası veya `.ics` dosyaları olan bir klasör. `SUMMARY`, `DTSTART`, `DTEND`, `LOCATION`,
  `DESCRIPTION` okunur; `TZID`, `RRULE` ve katlanmış satırlar desteklenir. Tekrarlayan etkinliklerde yalnızca
  ilk oluşum listelenir ve `⟳` ile işaretlenir.
- **Posta**: `.eml`, `.mbox` veya `.eml` dolu bir klasör. Gönderen, konu, tarih ve kısa önizleme okunur;
  ekler **açılmaz**, ileti **gönderilmez/silinmez**.
- Sohbette kural tabanlı tetikleme: “bu hafta takvimde ne var”, “yarın randevu var mı”, “son mailleri özetle”.
  Bu sorular model kapalıyken de yanıtlanır (Ollama/API gerekmez).
- **Bilinçli sınır**: IMAP/SMTP **yoktur**. Hesaba bağlanmak parola saklamayı ve dış ağa çıkmayı gerektirir;
  Emre'nin “yalnızca 127.0.0.1, onaysız dış işlem yok” kuralıyla çelişir. Bu yüzden posta yalnızca
  bilgisayarındaki dosyalardan okunur.

| Uç nokta | Açıklama |
| --- | --- |
| `GET /api/calendar?days=7` | `{path, events:[…], total}`; yol yoksa `message` alanı açıklama verir |
| `POST /api/calendar/path` | `{path}` → yolu doğrular ve kaydeder (boş gönderim kaldırır) |
| `GET /api/mail?limit=10` | `{path, messages:[…], total}` |
| `POST /api/mail/path` | `{path}` → `.eml`/`.mbox`/klasör yolu |

### 4. Windows'ta nasıl denerim?

1. Ayarlar › **Belgeler** → “Dosya seç” → bir PDF/Word/txt seç → “Seçilen dosyayı ekle”.
2. Aynı sekmede soru yaz → “Belgeye sor”. Yanıtın altında “Kaynaklar: [1] dosya.pdf · sayfa 3” görünür.
3. Ayarlar › **Takvim & posta** → takvim dosyanın yolunu yaz (örn. `C:\Users\SERVER\Desktop\takvim.ics`) →
   “Takvim yolunu kaydet” → “Bu haftayı göster”.
4. Ana ekranda mikrofona bas ve “bu hafta takvimde ne var” de; Emre kendi okur.
5. Mikrofon açıkken Emre konuşurken araya gir: okuma durur, seni dinlemeye geçer (söz kesme).

### Testler

`test_sesli_yanit.py` (15), `test_belge.py` (35), `test_takvim.py` (26), `test_posta.py` (20),
`test_server.py` +29 → **553 test**. Arayüz E2E **54/54**.

## Bellek yedeği ve sağlayıcı dayanıklılığı (2026-11-03 · beşinci tur)

### 1. Bellek: yedekleme, geri yükleme, unutma, yaşlandırma

- **Yedek indir**: tüm bellek kayıtları JSON olarak iner (`emre-bellek-YYYY-AA-GG.json`).
  Dosya yalnızca senin bilgisayarına yazılır; içinde kişisel notların olur.
- **Yedekten geri yükle**: JSON dosyası seçilir; aynı metinler **iki kez eklenmez** (`eklenen` / `atlanan` sayısı gösterilir).
  `mode: "degistir"` ile mevcut bellek tamamen değiştirilebilir.
- **Unutma**: sohbette `unut: Ahmet'in telefonu` (ya da `bunu unut: …`) yazınca eşleşen kayıtlar silinir;
  arayüzde de tek kayıt silme var. Silmeler denetim izine yazılır.
- **Yaşlandırma**: “Eski kayıtları temizle” hiç kullanılmamış (`hits=0`) ve 180 günden eski kayıtları siler.
  Gün sayısı uçtan ayarlanabilir (7–3650).

| Uç nokta | Açıklama |
| --- | --- |
| `GET /api/memory/export` | `{surum, tarih, kayitlar, baglantilar}` |
| `POST /api/memory/import` | `{backup, mode?, confirmed:true}` → `{eklenen, atlanan}` |
| `POST /api/memory/forget` | `{q, confirmed:true}` → `{deleted}` |
| `POST /api/memory/archive` | `{gun?, confirmed:true}` → `{silinen, gun}` |

### 2. Sağlayıcı yedeği (kota dolunca devam)

- **Yedek model** tanımlanabilir (Ayarlar › Sistem). Birincil model **429 / 402 / 5xx / zaman aşımı**
  döndürdüğünde Emre **bir kez** yedek modelle dener; yanıt gelirse konuşma kesilmez.
- Yedek modelle geçiş yalnızca **geçici** hatalarda yapılır; 401/403 veya “ulaşılamadı” hatasında denenmez
  (anahtar sorunu yedek modelle çözülmez, kullanıcı yanlış yönlendirilmez).
- Akışlı yolda ilk parça gelmeden hata olursa yedek modele geçilir; parça üretildikten sonra hata olursa
  yanıt yarıda kalmaz, hata açıkça bildirilir.
- **Kota sayacı**: günlük istek, hata ve yedek model sayısı `provider_usage` tablosunda tutulur;
  Ayarlar › Sistem'de “Bugün N istek …” olarak görünür. Sayaç yalnızca bilgilendirir, istek engellemez.

| Uç nokta | Açıklama |
| --- | --- |
| `POST /api/provider/fallback` | `{model}` → yedek modeli kaydeder (boş gönderim kaldırır) |
| `GET /api/provider/usage?days=7` | `{bugun:{requests,errors,fallback}, gunler:[…]}` |

### Testler

`test_bellek.py` +12 (yedek/geri yükleme/unutma/yaşlandırma), `test_saglayici.py` +10 (yedek model, kota geçişi),
`test_server.py` +14 → **436 test**. Arayüz E2E **51/51**.

## Beceriler, denetim izi ve tanılama (2026-11-03 · dördüncü tur)

### 1. Beceri (skill) sistemi

Kendi yeteneğini eklemek için tek klasör yeter: `beceriler/<ad>/SKILL.md`

```
---
ad: metin-analiz
aciklama: Verilen metnin karakter, kelime ve cümle sayısını hesaplar.
tetik: kelime say, karakter say
komut: python calistir.py
---
Bu beceri tamamen yerel çalışır.
```

- `komut` varsa beceri **alt süreç** olarak çalışır: stdin'e `{"metin": "...", "beceri": "...", "klasor": "..."}`
  JSON'u yazılır, stdout'tan `{"reply": "..."}` (veya düz metin) okunur. **Kabuk kullanılmaz**,
  `python`/`python3`/`py` otomatik olarak Emre'nin yorumlayıcısına çevrilir.
- `komut` yoksa beceri yalnızca açıklamadır; modelin sistem isteminde listelenir, çalıştırılmaz.
- Sınırlar: ad `a-z 0-9 _ -` (en fazla 40 karakter), 40 beceri, 20 sn zaman aşımı, çıktı 4000 karakter,
  giriş 2000 karakter.
- Çalıştırma **iki yolla** olur ve ikisi de senin açık isteğinle: arayüzde **Ayarlar › Beceriler › Çalıştır**
  (onay sorar) veya sohbette **`!beceri-adı metin`**. Her çalıştırma denetim izine yazılır.
- Depoda çalışan bir örnek var: `!metin-analiz bir iki üç` → “3 kelime …”.

| Uç nokta | Açıklama |
| --- | --- |
| `GET /api/skills` | `{skills:[{ad,klasor,aciklama,tetik,komut,calistirilabilir,hata?}], folder}` |
| `POST /api/skills/run` | `{ad, metin, confirmed:true}` → `{ok, ad, reply, sure}` |

### 2. Denetim izi (audit)

- Şeffaflık için önemli işlemler `audit` tablosuna yazılır: MCP araç çağrıları, beceri çalıştırmaları,
  ekran görüntüsü/sorusu, etkin pencereye yazma, defter ve bellek değişiklikleri, sağlayıcı bağlama/kesme,
  uygulama açma, otomatik başlatma ve global kısayol ayarları.
- **Sırlar maskelenir**: `Bearer …`, `sk-…`, `api_key:`, `token:`, `parola:` gibi değerler `[gizli]` olur.
- En fazla 2000 kayıt tutulur; eskiler otomatik budanır. Kayıtlar dışarı gönderilmez.

| Uç nokta | Açıklama |
| --- | --- |
| `GET /api/audit?limit=50&kind=` | son kayıtlar (yeniden eskiye) |
| `POST /api/audit/clear` | `{confirmed:true}` → tüm kayıtları siler |

### 3. Tanılama

- `tanilama.py` on kontrol yapar: Python sürümü, platform, disk alanı, yazma izni, veritabanı,
  port, Ollama, ses ortamı, beceriler, MCP ayarı.
- Her kontrol `ok` / `uyari` / `hata` döner; arayüzde **Ayarlar › Sistem › Kendi kendini kontrol** altında görünür.
- Yazma testi geçici bir dosya oluşturup hemen siler; başka hiçbir dosyaya dokunulmaz.

| Uç nokta | Açıklama |
| --- | --- |
| `GET /api/diagnose` | `{checks:[{ad,durum,mesaj}], ozet:{ok,uyari,hata,mesaj}}` |

### Testler

`tests/test_beceriler.py` (28), `test_denetim.py` (16), `test_tanilama.py` (16), `test_server.py` +12 →
**399 test**. Arayüz E2E **49/49**.

## Akışlı yanıt ve web araması (2026-11-03 · üçüncü tur)

### 1. Akışlı (streaming) yanıt

- Yeni `POST /api/chat/stream` ucu, yanıtı **kelime kelime** gönderir (SSE, `text/event-stream`).
  Sağlayıcı akışı OpenAI uyumlu `stream: true` ile, Ollama ise NDJSON akışıyla okunur.
- Arayüz yazılan metni anında ekrana basar; akış desteklenmezse **kendiliğinden** eski tek parça
  `/api/chat` yoluna döner (sessiz bozulma yok).
- Defter/hatırlatıcı gibi **kural tabanlı** yanıtlar model çağrılmadan tek parça döner; Ollama kapalıyken de çalışır.
- Sistem istemindeki güvenlik kuralları korunur; modelin ham düşünce blokları (`<think>`) temizlenir.
- Ayarlar › Sistem › “Yanıtı yazarken göster (akışlı)” ile kapatılabilir.

Olay biçimi:

```
data: {"type":"start","sources":[...]}
data: {"type":"delta","text":"Merhaba"}
data: {"type":"done","reply":"Merhaba dünya.","sources":[{"baslik":"...","url":"https://..."}]}
```

### 2. Web araması (ücretsiz, anahtar gerekmez)

- `arama.py` üç kaynağı sırayla dener: **DuckDuckGo Lite** → **DuckDuckGo Instant Answer** → **Türkçe Vikipedi**.
- Arama **yalnızca gerektiğinde** yapılır: “bugün, güncel, son dakika, hava, fiyat, kimdir, araştır, internetten bak”
  gibi kalıplar. “Ahmet 500 TL borç aldı” gibi komutlar aramaya gitmez.
- Sonuçlar sistem istemine kaynak numaralı olarak eklenir; arayüz yanıtın altında **tıklanabilir kaynak listesi** gösterir.
- Güvenlik: yalnızca **https**, 8 sn zaman aşımı, 600 KB yanıt sınırı; sayfalar açılmaz, form gönderilmez, giriş yapılmaz.
  Arama başarısız olursa sohbet **bozulmaz**, kaynak listesi boş kalır.
- Ayarlar › Sistem › “Güncel sorularda web’de ara” ile kapatılabilir (`web_arama` ayarı).

| Uç nokta | Açıklama |
| --- | --- |
| `POST /api/chat/stream` | `{messages, backend, model?, session?, web?}` → SSE akışı |
| `GET /api/web/search?q=...` | `{query, results:[{baslik,url,ozet}]}` (elle arama) |
| `POST /api/system/web` | `{aktif}` → web aramasını aç/kapa |

### Testler

`tests/test_arama.py` (21), `test_saglayici.py` +5 (SSE akışı), `test_server.py` +12 (web + akış uçları) →
toplam **329 test**. Arayüz E2E **47/47**.

## Sistem entegrasyonu (2026-11-03 · ikinci tur)

Emre'yi "açıp kapatılan bir program" olmaktan çıkarır: bilgisayarla birlikte başlar,
dikteyi her uygulamadan klavye kısayoluyla yönetir ve hatırlatıcıları tarayıcı kapalıyken de bildirir.
Üçü de **Ayarlar › Sistem** sekmesinden yönetilir.

### 1. Bilgisayar açılınca arka planda başlama

- Başlangıç klasörüne `EMRE.lnk` kısayolu kurulur; kısayol, proje kökünde üretilen
  `emre_arkaplan.vbs` dosyasını `wscript` ile sessizce çalıştırır → `pythonw server.py`
  **konsol penceresi açmadan** başlar.
- Kayıt defterine dokunulmaz, yönetici izni gerekmez, yalnızca kullanıcının kendi Başlangıç klasörü kullanılır.
- Kurulum/kaldırma **`confirmed:true`** ister. Yalnızca Windows'ta desteklenir; diğer platformlarda açık hata verir.

### 2. Global kısayol ile dikte (varsayılan `Ctrl+Alt+D`)

- `RegisterHotKey` ile sistem genelinde dinlenir; basıldığında Emre'de bir "dikte isteği" oluşur.
  Açık sayfa bunu **~1 saniye içinde** görüp dikteyi başlatır/durdurur.
- Sayfa kapalıysa (isteğe bağlı ayar açıksa) tarayıcı `?dikte=1` adresiyle açılır ve dikte kendiliğinden başlar.
- Kısayol **hiçbir komut çalıştırmaz**; yalnızca dikteyi açar/kapatır.
- Varsayılan **kapalı**; `ctrl+alt+d`, `ctrl+shift+e`, `shift+f5` gibi biçimler kabul edilir
  (en az bir değiştirici tuş, geçersiz biçim `400` ile reddedilir).

### 3. Hatırlatıcıların sunucu tarafında çalışması

- Sunucuda 20 saniyede bir çalışan bir işçi, süresi gelmiş hatırlatıcıları yakalar
  (`EMRE_BILDIRIM_ARALIK` ile değiştirilebilir), veritabanına bildirim yazar ve her hatırlatıcıyı
  **yalnızca bir kez** bildirir (`reminders.notified`).
- Açıksa Windows'ta masaüstü balonu + kısa uyarı sesi gösterilir (PowerShell `NotifyIcon`, ek bağımlılık yok).
- Sayfa kapalıyken oluşan bildirimler birikir; Emre açıldığında **"kaçırdığın bildirimler"** olarak gösterilir.

| Uç nokta | Açıklama |
| --- | --- |
| `GET /api/system/status` | otomatik başlatma, kısayol ve bildirim durumu |
| `POST /api/system/autostart` | `{aktif, confirmed:true}` → kısayolu kurar/kaldırır |
| `POST /api/system/hotkey` | `{aktif, kisayol?, tarayici?}` → kısayolu kaydeder/başlatır |
| `POST /api/system/notifications` | `{aktif}` → masaüstü bildirimi aç/kapa |
| `GET /api/hotkey/poll?since=N` | `{seq, basildi, aktif}` (sayfa 1,5 sn'de bir yoklar) |
| `GET /api/notifications?since=N` | okunmamış bildirimler |
| `POST /api/notifications/seen` | `{ids:[...]}` veya tümünü okundu işaretler |

### Testler

`tests/test_kisayol.py` (15), `tests/test_bildirim.py` (11), `tests/test_otomatik_baslat.py` (12),
`test_server.py` +13 → toplam **291 test**. Arayüz E2E **44/44**.

## Yeni özellikler (2026-11-03 · Jarvis turu)

`JARVIS_INCELEME.md` incelemesindeki ilk dört öneri eklendi. Hepsi **isteğe bağlı**, hepsi **onay** ya da kapatma anahtarı arkasında.

### 1. Uyandırma sözcüğü (wake word)

- Canlı dikte açıkken, ayar açıksa **yalnızca “Emre” ile başlayan cümleler** yazılır. Sözcük duyulduktan sonra **12 saniye** boyunca söylenenler beklemeden akar (toplu yazma yok).
- Uyandırma sözü **metinden** ayıklanır; “emreye/emreler” gibi kelimeler tetiklemez (kelime sınırı).
- Varsayılan **kapalı**; Ayarlar › Bellek sekmesinden açılır, kelimeler `emre, hey emre` gibi virgülle yazılır (en fazla 6 kelime).
- Ayar dosyası `uyandirma_ayar.json` (yerel, `.gitignore` içinde).

| Uç nokta | Açıklama |
| --- | --- |
| `GET /api/wake/status` | `{aktif, kelimeler, ses_modeli}` |
| `POST /api/wake/settings` | `{aktif?}`, `{kelimeler?}` → güncel ayar |
| `POST /api/dictate/window` | yanıtta `triggered`: cümle uyandırma sözcüğüyle mi geldi |

### 2. Kalıcı kişisel bellek

- Sohbette açık bilgiler otomatik çıkarılır: “hatırla/not al/kaydet”, “benim adım X”, “X’in telefonu N”, “ben X seviyorum”.
- Aynı metin ikinci kez kaydedilmez (`hits` sayacı artar); en fazla 5000 kayıt, kayıt başına 500 karakter.
- Sohbet sırasında yalnızca **ilgili** birkaç kayıt sistem istemine eklenir (semantik değil, kelime araması + Türkçe aksan duyarsız eşleşme).
- Veri `emre.sqlite3` içinde, `memories` tablosunda; dışarıya gönderilmez.

| Uç nokta | Açıklama |
| --- | --- |
| `GET /api/memory?q=&limit=` | `{items,total}` (q boşsa son kayıtlar) |
| `POST /api/memory/add` | `{text, subject?, kind?}` |
| `POST /api/memory/delete` | `{id, confirmed:true}` |

### 3. MCP (Model Context Protocol) araçları

- Proje kökündeki **`mcp_ayar.json`** dosyası okunur; şablon: `mcp_ayar.ornek.json`.
- Sunucular **stdout/stdin JSON-RPC** ile çalışır; **kabuk (shell) kullanılmaz**, komut ve argümanlar öğe öğe verilir.
- Her araç çağrısı **`confirmed:true`** ister; arayüz her çağrıdan önce sorar. Sunucu başına 20 sn başlatma, istek başına 60 sn zaman aşımı, en fazla 8 sunucu.

```json
{
  "sunucular": [
    {"ad": "dosyalar", "komut": "python",
     "argumanlar": ["-m", "mcp_server_filesystem", "C:\\Users\\SERVER\\Belgeler"],
     "env": {}}
  ]
}
```

| Uç nokta | Açıklama |
| --- | --- |
| `GET /api/mcp/status` | `{servers:[{ad,calisiyor,arac_sayisi}], configured}` |
| `GET /api/mcp/tools` | `{tools:[{sunucu, ad, aciklama, girdi}]}` (sunucu açılamazsa `hata`) |
| `POST /api/mcp/call` | `{server, tool, arguments, confirmed:true}` → `{ok, result}` |

### 4. Ekranı sor (ekran görme)

- Sohbet alanındaki **▣** düğmesi ekran görüntüsünü alır, onay ister ve bağlı **görsel destekli** sağlayıcıya sorar.
- Görüntü diske yazılmaz; 6 MB sınırı vardır. Windows’ta PowerShell + `System.Drawing` (ek bağımlılık yok), diğer platformlarda Pillow.
- Görsel destekli sağlayıcı bağlı değilse açık Türkçe hata verir; sessizce başarısız olmaz.

| Uç nokta | Açıklama |
| --- | --- |
| `POST /api/screen/capture` | `{confirmed:true}` → `{image, type}` (base64 PNG) |
| `POST /api/screen/ask` | `{question, confirmed:true}` → `{reply}` |

### Testler

`tests/test_uyandirma.py` (15), `tests/test_bellek.py` (15), `tests/test_mcp_istemci.py` (15, gerçek stdio alt süreç), `tests/test_ekran.py` (6), `test_server.py` +14 → toplam **239 test**. Arayüz E2E **40/40** (bellek, uyandırma anahtarı ve ekran onayı dâhil).

## Güncelleme (GitHub'daki yeni sürümü alma)

`git pull` tek başına çoğu zaman yetmez; en sık iki sebep vardır: **yanlış dal** ve **eski süreç**. Kısa yol:

```bat
guncelle.bat
```

PowerShell kullanıyorsan (aynı işi yapar, betik imzası sorunu olmadan):

```powershell
powershell -ExecutionPolicy Bypass -File .\guncelle.ps1
```

> PowerShell'de `cd /d` **çalışmaz** (`/d` cmd.exe'ye özgüdür) — `PositionalParameterNotFound` hatası ondan gelir. PowerShell'de sadece `cd C:\Users\SERVER\Desktop\jarvis` yaz.

Betik sırayla: depo kontrolü → yerel değişiklik uyarısı → `git fetch` → doğru dal kontrolü (gerekirse `arena/58f60478-depommmm` dalına geçiş) → `git pull --ff-only` → `server.py` içindeki sürümü yazdırır.

Elle yapmak istersen:

```bat
cd /d c:\Users\SERVER\Desktop\jarvis
git status -sb
git fetch origin
git checkout arena/58f60478-depommmm     :: yoksa: git checkout -b arena/58f60478-depommmm origin/arena/58f60478-depommmm
git pull --ff-only origin arena/58f60478-depommmm
```

Sonra **mutlaka**:

1. Açık Emre penceresini kapat (Ctrl+C) — `server.py` değiştiği için eski süreç eski kodu sunmaya devam eder.
2. `baslat.bat` ile yeniden başlat.
3. Tarayıcıda **Ctrl+F5** (önbelleği atlayarak yenile).

**Güncel sürümde olduğunu nasıl anlarsın?** Ayarlar sekmesinde `Sürüm: 2026-11-02.4` yazar ve sekmelerde **Ücretsiz API** görünür. Kontrol: `http://127.0.0.1:8765/api/status` yanıtındaki `version` alanı.

| Belirti | Sebep | Çözüm |
| --- | --- | --- |
| `git pull` → “Already up to date” ama sayfa değişmedi | `main` dalındasın; yeni işler özellik dalında | `guncelle.bat` veya `git checkout arena/58f60478-depommmm` |
| Sayfa güncellendi ama sekme yok | Sunucu yeniden başlatılmadı | Ctrl+C → `baslat.bat` |
| Sekme var ama eski görünüm | Tarayıcı önbelleği | Ctrl+F5 |
| `git pull` çakışma/hata verdi | Yerelde commit edilmemiş değişiklik var | `git stash` ya da `git commit -am "notlarım"`, sonra tekrar |
| “Bu klasör bir git deposu değil” | Yanlış klasörde çalışıyorsun | Depo klasörüne geç (`git rev-parse --show-toplevel` ile bul) |

### Sorun giderme: “401 / Missing API key” (liste geliyor, sohbet çalışmıyor)

9Router/OmniRoute ailesinde bilinen bir hata var: `GET /v1/models` anahtarı kabul eder ama `POST /v1/chat/completions` **“401: Missing API key”** döner ([OmniRoute #11030](https://github.com/diegosouzapw/OmniRoute/issues/11030)).

Emre bunun için iki şey yapar:

1. **Otomatik yedek başlık:** 401 gövdesi “missing api key” diyorsa istek bir kez de `x-api-key: <anahtar>` başlığıyla tekrarlanır. Bazı geçit sürümleri anahtarı yalnızca bu başlıktan okuyor.
2. **Bağlantıyı test et:** Ayarlar › Ücretsiz API › *Bağlantıyı test et* düğmesi (`POST /api/provider/test`) minik bir sohbet isteği gönderir; sağlayıcının kendi hata metnini gösterir.

Yine 401 alırsan sırayla dene:

| Adım | Ne yapılır |
| --- | --- |
| 1 | 9Router panelinde **API Keys** → anahtarın *Active* ve “tüm modeller” izinli olduğunu doğrula; anahtarı yeniden kopyala (maskeli kısmı değil) |
| 2 | **Başka model seç** — `yapay` gibi özel/combo modeller bağlı bir sağlayıcıya ihtiyaç duyar; `oc/…`, `kr/…`, `if/…` gibi hazır bir model dene |
| 3 | Geçidi **yeniden başlat** (`9router` penceresini kapat-aç) ve panelde sağlayıcının “test” düğmesiyle çalıştığını doğrula |
| 4 | Hâlâ 401 ise geçit hatasıdır: **OpenRouter** (`https://openrouter.ai/api/v1`, `:free` modeller) veya **Groq** (`https://api.groq.com/openai/v1`) gibi doğrudan bir sağlayıcıya geç |

Hata mesajları artık hangi arka ucun kullanıldığını söyler: *“Yapay zekâ sağlayıcısı ile bağlantı kurulamadı: Ücretsiz API (<adres> · <model>): …”*. Ayrıntı, `http://127.0.0.1:8765/api/provider/test` yanıtında da görünür.

## Konuşma tanıma: “eksik duyuyor” sorunu ve çözümü

Mikrofon (sol alttaki ◉ düğmesi) tamamen **yerel** çalışır: tarayıcı sesi kaydeder, Whisper bu bilgisayarda çözer, hiçbir ses dışarı gitmez. Eski sürümde cümleler erken kesiliyordu; şu an:

| Sorun (eski) | Şimdi |
| --- | --- |
| 1,2 sn sessizlikte cümle bölünüyordu | Varsayılan **2,2 sn** (Ayarlar › Ses › *Cümle bitiş sessizliği*: 1,2 / 1,8 / 2,2 / 2,8 / 3,5 sn) |
| En fazla 16 sn kayıt → uzun cümle yarıda kesiliyordu | **30 sn** (15/30/45/60 seçilebilir) |
| Sabit ses eşiği → sessiz konuşan hiç algılanmıyordu | **Uyarlanır eşik**: arka plan gürültüsü ölçülür, eşik onun 3 katına çıkar |
| Kayıt bitince ~1 sn boşluk → sonraki cümlenin başı kaçıyordu | Yeni kayıt **anında** başlar; cümlenin başı ve sonu korunur |
| İki parça ayrı ayrı komut sayılıyordu | 900 ms içinde gelen parçalar **birleştirilir**, tek komut olarak gönderilir |
| Asistan konuşurken söze girince yok sayılıyordu | **Söz kesme (barge-in)**: yüksek ses algılanınca okuma durur, dinlemeye geçilir |
| Ne anladığı görünmüyordu | *Ayarlar › Ses › Duyduğum metni göster* açıkken `Duyduğum: …` bildirimi çıkar |
| Whisper `base` modeli Türkçede kelime kaçırıyordu | VAD dolgusu + 600 ms konuşma payı, `beam_size=5`, Türkçe bağlam ipucu; **small** modeli seçilebilir |

Türkçe doğruluğu artırmak için (bir kez, internet gerekir):

```bat
ses_small_kur.bat
```

Sonra Ayarlar › Ses › *Tanıma modeli* → **small** → *Tanıma modelini kaydet*. Model seçimi `whisper_ayar.json` içinde tutulur (git'e girmez), bir sonraki konuşmada geçerli olur. `small` yavaştır ama belirgin şekilde daha doğrudur; eski bilgisayarda `base` ile devam edebilirsin.

Ayrıca sunucu tarafında tanıma şu şekilde iyileştirildi: `vad_parameters(min_silence_duration_ms=700, speech_pad_ms=600)`, `no_speech_threshold=0.6`, `compression_ratio_threshold=2.4`, tekrarlanan segmentlerin atılması ve Türkçe alan sözcükleri içeren `initial_prompt`. İşçi çökerse bir sonraki istekte kendini yeniden başlatır.

**Test:** `python3 -m unittest tests.test_ses_baglanti` (9 test) · `POST /api/speech/model {model:'base'|'small'}` · `GET /api/speech/status` → `{installed, model, models, hint}`

## Canlı dikte: konuş → anında yaz (Antigravity ve her uygulama)

Sohbet kutusunun yanındaki **⌨** düğmesi canlı dikte panelini açar. Eski mikrofon (◉) cümle bitmesini bekleyip **toplu** yazıyordu; canlı dikte ise konuşurken **~1 saniye içinde** metni üretir ve istersen doğrudan etkin pencereye yazar.

| Özellik | Nasıl |
| --- | --- |
| Anında yazım | Ses her 1 saniyede bir “son ~4,5 saniye” penceresi olarak yerel Whisper'a gider; cümle bitmesi beklenmez |
| Tekrar yok | Üst üste binen pencerelerin ortak kelimeleri `dikte.kaydir()` ile ayıklanır (kelime düzeyinde çakışma) |
| Noktalama + büyük harf | `dikte.bicimlendir()`: Türkçe büyük harf (i→İ, ı→I), soru cümlesi algılama, noktalama boşlukları, “Ankara'da” kesme işareti |
| Dolgu temizliği | “ıı, eee, hmm, öhö, ıh” gibi anlamsız sesler ve kekeleme (“ben ben ben” → “ben”) atılır; **“yani/işte/şey” korunur** (anlam taşır) |
| Etkin pencereye yazma | `dikte_yaz.py` → Windows `SendInput` + `KEYEVENTF_UNICODE` (Türkçe karakterler bozulmaz, panoya dokunulmaz) |
| Hedef pencere kilidi | “Hedef pencere” alanına `Antigravity` yazarsan metin **yalnızca** başlığı bu metni içeren pencereye yazılır; başka uygulama öndeyse yazmaz, uyarır |
| Yazımı düzeltme | “Durdurduğumda yazımı yapay zekâ düzeltsin” açıksa, durdurunca metin ücretsiz API sağlayıcısına gönderilip yalnızca noktalama/yazım düzeltmesi istenir (anlam değiştirmez, uzunluk kontrolü yapılır) |
| Emre cevaplasın | “Durdurduğumda Emre cevap versin” açıksa dikte metni sohbete gönderilir ve yanıt sesli okunur |

Akış (tek yönlü, hepsi yerel):

```
mikrofon ─► ham PCM (ScriptProcessor) ─► 1 sn'de bir WAV ─► /api/dictate/window
        ─► Whisper (yerel) ─► çakışma ayıklama ─► panelde anında metin
        ─► (isteğe bağlı) /api/dictate/type ─► etkin pencere (Antigravity)
```

### Uç noktalar

| Uç nokta | Açıklama |
| --- | --- |
| `POST /api/dictate/window` | `{audio (wav base64), session}` → `{text, added, full, model}` |
| `POST /api/dictate/finish` | `{session, polish?}` → biçimlendirilmiş tam metin (isteğe bağlı yapay zekâ düzeltmesi) |
| `POST /api/dictate/reset` | oturumu temizler |
| `POST /api/dictate/type` | `{text, confirmed:true, target?, enter?}` → etkin pencereye yazar (yalnızca Windows) |
| `POST /api/dictate/status` | oturum sayısı, model, yazma desteği, etkin pencere başlığı |

### Antigravity ile kullanım

1. Ayarlar › Ses › *Tanıma modeli* → **small** (Türkçe doğruluk için, `ses_small_kur.bat` ile kurulur).
2. ⌨ → **Hedef pencere** alanına `Antigravity` yaz → **Dikteyi başlat**.
3. Antigravity penceresini öne getir, konuş. Metin ~1 saniye içinde hem panelde görünür hem (canlı yazım açıksa) Antigravity'nin giriş alanına yazılır.
4. Cümle bitince Enter gönderilsin istersen *Her cümleden sonra Enter gönder* seçeneğini aç.
5. Durdurduğunda yazım/noktalama düzeltmesi ve Emre'nin cevabı için ilgili onay kutularını kullan.

> **Güvenlik:** yazma işlemi onay gerektirir (`confirmed:true`), yalnızca metin gönderir (komut çalıştırmaz, tuş kombinasyonu göndermez), satır sonu içeren metni reddeder ve hedef pencere eşleşmezse hiç yazmaz.
