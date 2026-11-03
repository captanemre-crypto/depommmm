# EMRE — Sıradaki Eksikler ve Yol Haritası (2026-11-03)

Bu dosya, `JARVIS_INCELEME.md` karşılaştırmasından sonra **hâlâ eksik olan** işleri öncelik sırasıyla listeler.
Her maddede: neden gerekli, bugün ne var/ne yok, tahmini emek (S ≤ 1 gün, M 2–4 gün, L 1 hafta+), risk.

Mevcut durum (özet): sohbet (Ollama + ücretsiz API), Türkçe sesli giriş, canlı dikte + etkin pencereye yazma,
uyandırma sözcüğü (metin tabanlı), kişisel bellek, MCP araçları, ekranı sor, defter, hatırlatıcılar,
Telegram, kod çalışma alanı, Windows uygulama açma, masaüstü (pywebview) prototipi, 239 test + 40 E2E kontrol.

---

## A. Günlük kullanımı doğrudan etkileyenler (önce bunlar)

| # | Eksik | Bugün ne var | Neden gerekli | Emek | Risk |
| --- | --- | --- | --- | --- | --- |
| A1 | **Windows açılışında otomatik başlama + arka planda çalışma** | `baslat.bat` / `masaustu_baslat.bat` elle çalıştırılıyor; tepsi simgesi var ama girişte başlatma yok | “Jarvis hep açık” hissi buna bağlı. Bilgisayarı açınca kendiliğinden gelmeli | S | Düşük |
| A2 | **Global kısayol ile dikte** (ör. `Ctrl+Alt+D`) | Dikte yalnız tarayıcı sekmesi açıkken panelden başlıyor | Antigravity’ye yazarken fareyle sekmeye dönmek gerekiyor; dikte pratik değil | S–M | Düşük |
| A3 | **Pencere kapalıyken hatırlatıcı** | Tarayıcı 30 sn’de bir `/api/reminders` yokluyor; sekme kapalıysa bildirim yok | Hatırlatıcının işe yaraması için tarayıcının açık olması şart — gerçek asistan davranışı değil | S | Düşük |
| A4 | **Web’den bilgi getirme (arama + kaynaklı özet)** | Yalnızca `internet_available()` bayrağı; model kendi bilgisiyle konuşuyor | “Bugün hava nasıl”, “bu ürün fiyatı ne” gibi sorularda model uyduruyor; kaynak/link yok | M | Orta (CSP + dış servis) |
| A5 | **Akışlı (streaming) yanıt** | Yanıt tamamen bitince tek parça geliyor | Uzun yanıtta 5–20 sn boş ekran; algılanan hız düşük | M | Düşük |

## B. “Jarvis hissi”ni tamamlayanlar

| # | Eksik | Notlar | Emek |
| --- | --- | --- | --- |
| B1 | **Skill (yetenek) sistemi** | `skills/<ad>/SKILL.md` + basit yükleyici; her skill bir Python fonksiyonu veya MCP sunucusu. Leon/Hermes’in eklenti modelinin hafif karşılığı. İncelemedeki kalan 5. madde | M |
| B2 | **Akışlı TTS + barge-in** | Yanıtı cümle cümle seslendir, kullanıcı konuşmaya başlayınca sesi kes. Şu an tek parça WAV | M |
| B3 | **Belge okuma ve soru-cevap** | PDF/Word/txt içe aktarma, yerel parçalama + arama, yanıtta sayfa referansı | L |
| B4 | **Takvim / e-posta** | ICS okuma (salt okunur, en güvenli seçenek); IMAP ile “son 10 maili özetle” | L |
| B5 | **Görsel üretimi** | Ücretli servis gerektirir; sağlayıcı katmanına eklenebilir | S (servis varsa) |

## C. Güvenlik, dayanıklılık, bakım

| # | Eksik | Notlar | Emek |
| --- | --- | --- | --- |
| C1 | **Araç çağrısı denetim izi** | MCP çağrıları, uygulama açma, dosya yazma, dikte yazımı için “son 100 işlem” kaydı + panel. Onay disiplinini görünür kılar | S |
| C2 | **Bellek dışa/içe aktarma ve yaşlandırma** | JSON yedeği, eski kayıtları arşivleme, “bunu unut” komutu | S |
| C3 | **Sağlayıcı yedeği ve kota sayacı** | 429/401’de ikinci ücretsiz modele otomatik geçiş; günlük istek sayacı | M |
| C4 | **Açılışta kendi kendini kontrol** | Python sürümü, port, DB yazılabilirliği, mikrofon, model hazırlığı → “Tanılama” paneli | S |
| C5 | **Telefondan erişim** | README’de bilinçli sınır. Ancak Tailscale/ZeroTier + token ile mümkün; **önerilmez** (yüzey alanı büyür) | L |

## D. Deneyim / kozmetik

| # | Eksik | Emek |
| --- | --- | --- |
| D1 | Ana sayfada “bugün” özeti (yaklaşan hatırlatıcı + defter bakiyesi + son bellek kayıtları) | S |
| D2 | Klavye kısayolları (`/` komut paleti, `Esc` panel kapat) | S |
| D3 | Tema seçimi (koyu/açık), yazı boyutu | S |

---

## Bilinçli olarak yapılmayacaklar

- Onaysız komut/uygulama çalıştırma (OpenClaw modeli) — README sınırı.
- CAPTCHA/giriş atlatma, gerçek para işlemi, AI’nın önerdiği komutu otomatik çalıştırma.
- Tarayıcı erişimi “tam” modunu etkinleştirme; şu an yalnızca hazırlık tercihi.

## Önerilen sıra

1. **A1 + A3** (otomatik başlatma, sunucu tarafı hatırlatıcı) — en yüksek fayda/emek oranı.
2. **A2** (global dikte kısayolu) — dikteyi gerçekten günlük kullanıma açar.
3. **A5 → A4** (akışlı yanıt, sonra web araması).
4. **B1** (skill sistemi) — MCP’nin üzerine hafif eklenti katmanı.
5. **B2** (akışlı TTS + barge-in) — tam çift yönlü ses.
6. **C1 + C2 + C4** — güvenlik/bakım paketi.

Yaklaşık toplam: A bloğu ~1,5 hafta, B1–B2 ~1 hafta, C1–C4 ~3 gün.
