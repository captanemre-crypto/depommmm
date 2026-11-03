# “En iyi Jarvis” incelemesi — 2026 sonu

> Bu belge, açık kaynak “Jarvis” tarzı kişisel asistanların karşılaştırması ve **Emre** projesiyle
> fark analizidir. Tüm bilgiler 2 Kasım 2026 itibarıyla kamuya açık kaynaklardan derlenmiştir;
> yıldız sayıları ve özellik listeleri hızla değişebilir.

---

## 1. Kısa cevap: tek bir “en iyi Jarvis” yok, üç ayrı lig var

| Lig | Ne yapar | Temsilciler | Kimin için |
| --- | --- | --- | --- |
| **A. Masaüstü kişisel asistan** | Sesle/klavyeyle konuşur, dikte eder, hatırlar, araç çağırır (MCP) | **isair/jarvis**, Jarvis (jarvis.ceo, Mac), Open WebUI | Günlük kullanım: not, dikte, sohbet, hatırlatma |
| **B. Otonom ajan platformu** | Bilgisayarda gerçek iş yapar: dosya, kabuk, tarayıcı, cron, alt-ajanlar | **OpenClaw**, **Hermes Agent**, Leon, OpenJarvis | Geliştirici / ileri kullanıcı: “benim yerime yap” |
| **C. Ses + ev/cihaz** | Uyandırma sözcüğü, odalara dağıtılmış mikrofonlar, ev kontrolü | Home Assistant Assist, xiaozhi-esp32, OpenVoiceOS | Ev otomasyonu, donanım meraklısı |

**Sizin profiliniz (Windows 11, Türkçe, ücretsiz, yerel, güvenlik sınırları olan, Python tabanlı Emre projesi) için en iyi hazır çözüm: `isair/jarvis`.**
En yetenekli ama en ağır olan: **Hermes Agent**. En “Jarvis gibi” ama en riskli varsayılanları olan: **OpenClaw**.

---

## 2. Adayların karşılaştırması

| Proje | Yıldız (yaklaşık) | Platform | Ses | Uyandırma sözcüğü | Bellek | Araç/eklenti | Lisans / risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **isair/jarvis** | 2,2 bin | macOS · **Windows** · Linux | ✅ çift yönlü | ✅ cümle içinde isim | ✅ günlük + bilgi grafiği | ✅ MCP | Non-commercial; hassas veriyi gizler |
| **Hermes Agent** | ~221 bin (iddia) | macOS · Linux · **Windows 11 22H2+** | ✅ akışlı TTS + söz kesme | ✅ açık sözlü, cihazda | ✅ kalıcı | ✅ 600 eklenti + MCP + A2A | Açık kaynak; bazı komutları otomatik onaylar |
| **OpenClaw** | çok yüksek, 124 bin commit | macOS · iOS · Android · sunucu | ✅ kesilebilir | ✅ | ✅ kalıcı yerel | ✅ 44.000+ skill (ClawHub) | MIT; **varsayılan olarak komutları sormadan çalıştırır** |
| **Leon** | ~17 bin | Node.js, her yerde | ✅ STT/TTS | ➖ | ✅ katmanlı | ✅ skill + SKILL.md ajanları + bilgisayar kullanımı | Açık kaynak; bilgisayar kullanımı riskli |
| **OpenJarvis** (Stanford) | 12,9 bin | macOS · Linux (+GUI) | ➖ | ➖ | ✅ iz tabanlı öğrenme | ✅ Claude Code dahil ajanlar | Araştırma; telemetri varsayılan açık |
| **Home Assistant Assist** | çok yüksek | Raspberry Pi/Docker | ✅ | ✅ | ➖ | ✅ ev cihazları | Açık kaynak; ev odaklı |
| **jarvis.ceo (Jarvis)** | — | yalnız macOS | ✅ ~240 ms dikte | ✅ | ✅ kalıcı | ✅ MCP | Ücretsiz + açık kaynak, Mac’e kilitli |
| **Open WebUI** | çok yüksek | Docker, tarayıcı | ✅ | ➖ | ✅ RAG | ✅ araçlar (BYOF) | Açık kaynak; “asistan”dan çok sohbet arayüzü |

---

## 3. En iyi üçünün detaylı özellik dökümü

### 3.1 `isair/jarvis` — “konuşmanın içine giren” masaüstü asistanı

**Felsefe:** bulutta değil, senin donanımında yaşayan bir asistan; ses, bellek ve dikte yerel.

Yapabildikleri:

- **Sesli + yazılı sohbet:** konuşurken yanında duran biri gibi; mikrofon açıkken yakındaki konuşmanın
  kısa bir “yuvarlanan dökümünü” tutar, “Jarvis, sen ne düşünüyorsun?” dediğinde az önce konuşulanları
  bağlama katar.
- **Cümle içinde isimle çağırma:** “Jarvis” kelimesi cümlenin herhangi bir yerinde geçebilir; ayrı bir
  komut cümlesi kurmak gerekmez. Ekranda **amber renkli yüzen bir yüz** durum gösterir (dinliyor /
  düşünüyor / konuşuyor).
- **Kişisel bellek:** günlük (diary) + **bilgi grafiği** yerelde; kişiler, projeler, tercihler birikir.
- **Dikte:** konuşmayı metne çevirip etkin uygulamaya yazma (Emre’deki canlı dikteye en yakın özellik).
- **MCP araçları:** Model Context Protocol ile GitHub, takvim, dosya sistemi gibi dış araçlara bağlanır.
- **Yerel/uzak model seçimi:** Ollama ile tamamen çevrimdışı ya da OpenAI uyumlu her sunucu.
- **Gizlilik:** hassas bilgi, model bağlamına ve kaydedilen günlüğe gitmeden **maskelenir**.
- Platform: macOS, **Windows**, Linux.

Zayıf yönleri: lisans **ticari kullanıma kapalı** (non-commercial), Türkçe desteği topluluk elinde,
otonom “benim yerime dosya sil / komut çalıştır” iddiası yok.

### 3.2 `Hermes Agent` (Nous Research) — en kapsamlı platform

Yapabildikleri:

- **Gerçek zamanlı ses:** yanıt cümle cümle sentezlenir (akış), sen konuşmaya başlayınca **sözünü keser**,
  meşgul olduğunu bilen sessizlik algılama ile üstüne konuşmaz.
- **Cihazda uyandırma sözcüğü:** “hey Hermes” ya da kendi seçtiğin ifade; openWakeWord / sherpa / Porcupine;
  farklı uyandırma sözcükleri farklı profillere yönlenebilir.
- **Masaüstü uygulaması:** artefakt kartları (sandbox’ta canlı önizleme), eklenti SDK’sı, çoklu pencere,
  “Bot Mode” (isimli botlar, grup sohbetleri, bot-bot mesajlaşma).
- **Bellek + cron + skill:** kalıcı bellek, zamanlanmış görevler, yeniden kullanılabilir yetenekler.
- **Tarayıcı ve kod:** kendi penceresinde gezinir, tıklar, okur; Claude Code/Codex gibi kod ajanlarını çağırır.
- **Entegrasyon:** 600 eklenti, MCP kataloğu, A2A (ajanlar arası), imzalı webhook’lar.
- **Alt-ajanlar:** paralel görev, canlı izleme/durdurma/onay.

Zayıf yönleri: ağır (Python 3.14 yönetilen kurulum, Windows 11 22H2+ şartı), öğrenme eğrisi yüksek,
bazı komutları otomatik onaylayabiliyor — sizin “onaysız komut çalıştırma yok” kuralıyla çelişen
varsayılanlar var.

### 3.3 `OpenClaw` — “gerçekten bir şeyler yapan” ajan

Yapabildikleri:

- **24+ mesaj kanalı:** WhatsApp, Telegram, Slack, Discord, iMessage, Signal… asistanı sohbet
  uygulamalarından kullanırsın.
- **Tam sistem erişimi:** dosya okuma/yazma, kabuk komutu, tarayıcı otomasyonu, cron.
- **Kalıcı bellek** (yerel) + **ClawHub**: 44.000+ hazır skill; ajan kendine yeni skill kurabiliyor.
- **Yerel/uzak model:** MIT lisanslı, abonelik yok (model maliyeti sana ait).
- Native macOS / iOS / Android uygulamaları, uyandırma sözcüğü, kesilebilir konuşma modu, yörünge (orb) kaplaması.

Zayıf yönleri (kritik): **varsayılan olarak komutları sormadan çalıştırır**; “sınırsız sistem erişimi”
gerçek anlamda sınırsızdır. Kurumsal/ciddi veri olan makinede önerilmez.

---

## 4. Emre ile fark analizi

| Yetenek | Emre (bu proje) | isair/jarvis | Hermes | OpenClaw |
| --- | --- | --- | --- | --- |
| Yerel STT (Whisper) | ✅ faster-whisper, base/small | ✅ | ✅ | ✅ |
| Canlı dikte (konuşurken yazma) | ✅ ~1 sn pencere + biçimlendirme | ✅ | ✅ | ✅ |
| Etkin pencereye yazma (Antigravity) | ✅ SendInput + hedef pencere kilidi | ✅ | ✅ | ✅ |
| Yerel TTS | ✅ Piper + Windows SAPI | ✅ | ✅ | ✅ |
| Söz kesme (barge-in) | ◐ diktede var, sohbette kısmi | ✅ | ✅ | ✅ |
| Uyandırma sözcüğü | ❌ | ✅ | ✅ | ✅ |
| Kalıcı bellek (kişi/proje/tercih) | ◐ defter + sohbet geçmişi | ✅ günlük + bilgi grafiği | ✅ | ✅ |
| MCP araçları | ❌ | ✅ | ✅ | ✅ |
| Skill/eklenti ekosistemi | ❌ (sabit araçlar) | ◐ | ✅ 600 | ✅ 44.000 |
| Zamanlanmış görev / cron | ✅ hatırlatıcılar | ➖ | ✅ | ✅ |
| Tarayıcı otomasyonu | ◐ Arena köprüsü (onaylı) | ◐ | ✅ | ✅ |
| Ekran görme (vision) | ❌ (kamera önizleme var) | ◐ | ✅ | ✅ |
| Mesaj kanalları | ✅ Telegram | ➖ | ✅ çok | ✅ 24+ |
| Onay mekanizması | ✅ her tehlikeli işlemde `confirmed:true` | ✅ | ◐ | ❌ zayıf |
| Yerel/ücretsiz model | ✅ 9Router/Ollama/OpenRouter `:free` | ✅ | ✅ | ✅ |
| Test altyapısı | ✅ 174 birim + 37 E2E | ✅ pytest + evals | ✅ | ✅ |
| Türkçe arayüz ve Türkçe niyet çözümü | ✅ | ❌ | ◐ | ❌ |

Emre’nin öne çıktığı yerler: **Türkçe**, **tek tıkla Windows kurulumu**, **onay disiplini**,
**defter/hatırlatıcı gibi gerçek günlük işler**, **test kapsamı**.

Eksik olduğu yerler: **uyandırma sözcüğü**, **MCP**, **kalıcı anlamsal bellek**, **ekran görme**,
**skill ekosistemi**, **tam çift yönlü ses**.

---

## 5. Emre’ye alınabilecek özellikler (öncelik sırası)

| # | Özellik | Neden | Zorluk | Notlar |
| --- | --- | --- | --- | --- |
| 1 | **Uyandırma sözcüğü** (“Emre” / “Hey Emre”) | Eller serbest kullanım; her seferinde düğmeye basmamak | Orta | openWakeWord (yerel, ücretsiz) veya sherpa-onnx; yanlış tetiklenmeyi azaltmak için 3 kare kuralı |
| 2 | **Kalıcı bellek + bilgi grafiği** | “Geçen hafta Ahmet’le ne konuştuk?” gibi sorular | Orta | SQLite + özet + kişi/proje düğümleri; gizlilik için yerel |
| 3 | **MCP istemcisi** | GitHub, takvim, dosya, tarayıcı araçları tek protokolle | Orta | stdio tabanlı MCP sunucuları; her araç çağrısı onaya tabi |
| 4 | **Ekran görme (vision)** | “Bu ekrandaki hatayı açıkla” | Kolay–Orta | Ekran görüntüsü → sağlayıcıya (görsel destekli model) veya yerel VLM |
| 5 | **Tam çift yönlü ses** | Asistan konuşurken söz kesme, anında yanıt | Orta | Mevcut barge-in mantığını sohbet akışına da uygula |
| 6 | **Skill/eklenti sistemi** | Yeni yeteneği kod yazmadan eklemek | Zor | `skills/<ad>/SKILL.md` + izin bildirimi |
| 7 | **Çoklu mesaj kanalı** | Telegram var; Discord/WhatsApp eklenebilir | Orta | Webhook tabanlı, onay mekanizması korunarak |
| 8 | **Zamanlanmış ajan görevleri** | “Her sabah 08:00’de günlük özet” | Kolay | Mevcut hatırlatıcı altyapısı genişletilir |
| 9 | **Ses profili/persona** | Farklı ton, hız, duygu | Kolay | Piper sesleri + konuşma hızı |
| 10 | **Çoklu kullanıcı/oturum** | Aile içinde ayrı bellek | Orta | Oturum başına bellek ayrımı |

---

## 6. Güvenlik uyarıları (bu projeleri denerken)

1. **Varsayılan izinleri okumadan çalıştırma.** OpenClaw ve benzeri ajanlar “komutları sormadan çalıştırır”;
   ilk denemeyi sanal makinede veya ayrı kullanıcı hesabında yapın.
2. **Telemetri.** OpenJarvis’te varsayılan açık, kapatılamıyor (kurulum telemetrisi). AIRI’de opt-out.
3. **Kimlik bilgisi hırsızlığına açık kurulumlar.** Hermes Agent bazı yapılandırmalarda Claude Code oturumunu
   devralabiliyor; hesap anahtarlarını aynı makinede tutmayın.
4. **“Sınırsız” vaatleri abartılı.** Uyandırma sözcüğü, ses, model kalitesi donanıma bağlı; CPU-only sistemde
   gecikme 2 saniyeyi aşabilir.
5. **Lisans kontrolü.** `isair/jarvis` ticari kullanıma kapalı; OpenClaw MIT; Hermes ve Leon açık kaynak.

---

## 7. Kurulum notları (Windows)

- **isair/jarvis:** GitHub Releases’ten Windows paketini indir; Ollama veya yerel OpenAI uyumlu sunucu
  (9Router / LM Studio) bağla. Mikrofon izni + uyandırma sözcüğü ayarı.
- **Hermes Agent:** `pipx`/yönetilen kurulum; Windows 11 22H2+; ilk açılışta rehberli kurulum ve
  “ücretsiz deneme modeli”. Daha sonra yerel llama.cpp modeline geçilebilir.
- **OpenClaw:** Node.js 24+; `npm` ile kurulum; API anahtarı; **önce izinleri sıkılaştır** (exec onayı zorunlu).
- **Leon:** Node.js 24+; `npm install`; dil paketi olarak Türkçe mevcut; yerel model için Ollama.

---

## 8. Sonuç

- **Günlük kullanım + dikte + bellek** istiyorsan: **isair/jarvis** (Windows desteği var, yerel, ücretsiz).
- **En fazla yetenek, en çok karmaşıklık** istiyorsan: **Hermes Agent**.
- **“Gerçekten bir şeyler yapsın”** istiyorsan: **OpenClaw** — ama izinleri sıkılaştırmadan kullanma.
- **Emre** ise bu üçünün arasında bir yerde: Türkçe, Windows, onay odaklı, test edilmiş bir **kişisel asistan**.
  Yukarıdaki 1–5 numaralı özellikler eklendiğinde, hazır projelerin günlük kullanım için sunduğu
  deneyimin büyük kısmı Türkçe olarak elde edilir.

---

## 9. Eklenen özellikler (2026-11-03 · “ekle” turu)

Bölüm 5’teki öneri tablosunun tamamı Emre’ye eklendi (kapanış turu: 2026-11-03).
Skill ekosistemi, akışlı TTS + barge-in, belge okuma, takvim/posta, günlük özet, komut paleti,
tema ve görsel üretimi artık mevcut.

| Öneri | Emre’de durumu | Dosya / uç |
| --- | --- | --- |
| Uyandırma sözcüğü | ✅ “Emre” ile başlayan cümleler yazılır, 12 sn devam penceresi, varsayılan kapalı | `uyandirma.py`, `GET /api/wake/status`, `POST /api/wake/settings`, `/api/dictate/window` → `triggered` |
| Kalıcı bellek | ✅ Otomatik çıkarım + mükerrer engeli + Türkçe aksan duyarsız arama + sohbet bağlamı | `bellek.py`, `/api/memory*` |
| MCP istemcisi | ✅ stdio JSON-RPC, kabuk yok, her çağrı onaylı | `mcp_istemci.py`, `mcp_ayar.json`, `/api/mcp/*` |
| Ekran görme | ✅ Onaylı ekran görüntüsü + görsel destekli sağlayıcıya soru | `ekran.py`, `/api/screen/*`, sohbet alanındaki **▣** |
| Skill ekosistemi | ✅ `beceriler/<ad>/SKILL.md`, `!ad` komutu, panel | `beceriler.py`, `/api/skills*` |
| Barge-in / akışlı TTS | ✅ Cümle cümle okuma + sen konuşunca susma | `sesli_yanit.py`, `/api/tts/split`, Ayarlar › Ses |
| Belge okuma | ✅ PDF/DOCX/txt/md/csv/html + belgeye soru (kaynak numaralı) | `belge.py`, `/api/docs/*` |
| Takvim / posta | ✅ `.ics` ve `.eml`/`.mbox` salt okunur (IMAP/SMTP yok) | `takvim.py`, `posta.py`, `/api/calendar`, `/api/mail` |
| Günlük özet | ✅ Ana sayfada “Bugün” kartı | `/api/today` |
| Komut paleti · tema | ✅ `/`, `Ctrl+K`, `?`; Koyu/Açık/Sistem + yazı boyutu | `index.html` |
| Görsel üretimi | ✅ Sağlayıcının `/images/generations` ucu (onaylı) | `saglayici.gorsel()`, `/api/image/generate` |

Kıyasla nerede kalıyoruz:

- **isair/jarvis** ve **Hermes Agent** uyandırma sözcüğünü **ses** üzerinde (openWakeWord/Porcupine) çözer;
  Emre’de bu, Whisper metni üzerinde çalışır — bu yüzden 1–2 sn gecikme ve yazım hatasına duyarlılık var,
  ama ek model/bağımlılık gerekmiyor ve tamamen yerel kalıyor.
- **OpenClaw** araçları sormadan çalıştırır; Emre’de MCP çağrıları dâhil her tehlikeli işlem `confirmed:true` ister.
- **Leon / Hermes** skill mağazasına sahip; Emre'de eşdeğeri `beceriler/<ad>/SKILL.md` dizini
  (`!ad` ile elle çalıştırma, onay zorunlu) ve `kodlar/` geliştirici alanı. Otomatik beceri *indirme* yoktur:
  beceri dosyasını sen eklersin, Emre kendi başına kod çalıştırmaz.
