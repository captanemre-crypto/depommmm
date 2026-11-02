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
PowerShell'de `py -m pip install playwright` ve sonra `py -m playwright install chromium` çalıştırın. Sunucuyu yeniden başlatın. Keşfet > Arena tarayıcısını aç ile açılan tarayıcıda Arena hesabınıza giriş yapın ve güvenlik doğrulamalarını kendiniz tamamlayın. Soruyu yazıp onaylayarak gönderin. Bağlantı yalnızca tanımlanabilen asistan yanıtlarını okur; Arena arayüzü değişirse veya bu tanımlayıcıları kullanmıyorsa yanıtı bulamayabilir. CAPTCHA atlatılmaz. Yanıtın doğru ve tamamlanmış olduğunu Arena ekranında kontrol edin; kısa süreli duraklamalar tamamlanma sanılabilir. Oturum çerezleri `arena_profile` klasöründe saklanır: bu klasörü başkalarıyla paylaşmayın ve yedeklerken kişisel bilgi içerdiğini unutmayın. Profil silinirse tekrar giriş gerekir. Sorular ve cevaplar Arena servisine gönderilir; hizmet şartları ve gizlilik kuralları geçerlidir. Bu özellik otomatik ihtiyaç tespiti yapmaz; her soru kullanıcı tarafından onaylanır.

## başlat.bat
Windows'ta klasördeki `baslat.bat` dosyasına çift tıklayın. Python 3 kurulu olmalıdır. Playwright kurulu değilse Arena için kurmayı teklif eder; onay verirseniz paket ve Chromium indirilir. Kurulumu reddederseniz Emre yine açılır fakat Arena otomasyonu çalışmaz. Tarayıcıda http://127.0.0.1:8765 adresini açın. Playwright önceden kurulu ama Chromium eksikse PowerShell'de `py -3 -m playwright install chromium` çalıştırın. Açık eski sunucuyu önce Ctrl+C ile kapatın.

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
