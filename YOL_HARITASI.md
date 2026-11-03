# EMRE — Sıradaki Eksikler ve Yol Haritası (2026-11-03)

Bu dosya, `JARVIS_INCELEME.md` karşılaştırmasından sonra **hâlâ eksik olan** işleri öncelik sırasıyla listeler.
Her maddede: neden gerekli, bugün ne var/ne yok, tahmini emek (S ≤ 1 gün, M 2–4 gün, L 1 hafta+), risk.

Mevcut durum (özet): sohbet (Ollama + ücretsiz API), Türkçe sesli giriş, canlı dikte + etkin pencereye yazma,
uyandırma sözcüğü (metin tabanlı), kişisel bellek, MCP araçları, ekranı sor, defter, hatırlatıcılar,
Telegram, kod çalışma alanı, Windows uygulama açma, masaüstü (pywebview) prototipi, 580 test + 63 E2E kontrol.

---

## A. Günlük kullanımı doğrudan etkileyenler (önce bunlar)

| # | Eksik | Bugün ne var | Neden gerekli | Emek | Risk |
| --- | --- | --- | --- | --- | --- |
| ~~A1~~ ✅ | **Windows açılışında otomatik başlama + arka planda çalışma** | **Eklendi (2026-11-03):** Başlangıç klasörü kısayolu + sessiz `pythonw` başlatma, Ayarlar › Sistem | — | Düşük |
| ~~A2~~ ✅ | **Global kısayol ile dikte** (varsayılan `Ctrl+Alt+D`) | **Eklendi:** `kisayol.py` + `/api/hotkey/poll`; sayfa açıksa 1,5 sn içinde tepki, kapalıysa `?dikte=1` ile açılır | — | Düşük |
| ~~A3~~ ✅ | **Pencere kapalıyken hatırlatıcı** | **Eklendi:** sunucu işçisi (20 sn) + `notifications` tablosu + masaüstü balonu/ses; birikenler açılışta gösterilir | — | Düşük |
| ~~A4~~ ✅ | **Web’den bilgi getirme (arama + kaynaklı özet)** | **Eklendi:** `arama.py` (DDG Lite → Instant Answer → Vikipedi), yalnızca gerektiğinde, kaynak listesi arayüzde | — | Orta (dış servis) |
| ~~A5~~ ✅ | **Akışlı (streaming) yanıt** | **Eklendi:** `/api/chat/stream` (SSE), Ollama NDJSON akışı, başarısızlıkta tek parça yola dönüş | — | Düşük |

## B. “Jarvis hissi”ni tamamlayanlar

| # | Eksik | Notlar | Emek |
| --- | --- | --- | --- |
| ~~B1~~ ✅ | **Skill (yetenek) sistemi** | **Eklendi (2026-11-03):** `beceriler/<ad>/SKILL.md` + alt süreçle çalıştırma, `!ad` komutu, arayüz paneli, örnek beceri | M |
| ~~B2~~ ✅ | **Akışlı TTS + barge-in** | **Eklendi (2026-11-03):** `sesli_yanit.py` cümle bölme + akış parçalayıcı + hiserezisli söz kesme; `/api/tts/split`, `/api/system/tts`, Ayarlar › Ses anahtarları | — |
| ~~B3~~ ✅ | **Belge okuma ve soru-cevap** | **Eklendi:** `belge.py` (PDF/DOCX/txt/md/csv/html, stdlib), parçalama + aksan duyarsız arama, `/api/docs/*`, kaynak numaralı yanıt, Ayarlar › Belgeler | — |
| ~~B4~~ ✅ | **Takvim / e-posta** | **Eklendi:** `takvim.py` (.ics, salt okunur) ve `posta.py` (.eml/.mbox, salt okunur); **IMAP/SMTP bilinçli olarak yok** (parola + dış ağ gerekir) | — |
| ~~B5~~ ✅ | **Görsel üretimi** | **Eklendi (2026-11-03):** ücretsiz API sağlayıcısının `/images/generations` ucu, `/api/image/generate`, Ayarlar › Görünüm'de model alanı ve “Görsel üret” paneli. Sağlayıcı desteklemiyorsa açık hata verir; görsel diske yazılmaz, dış bağlantıdan indirilmez | — |

## C. Güvenlik, dayanıklılık, bakım

| # | Eksik | Notlar | Emek |
| --- | --- | --- | --- |
| ~~C1~~ ✅ | **Araç çağrısı denetim izi** | **Eklendi:** `audit` tablosu + Ayarlar › Sistem › Denetim izi (sırlar maskeli, 2000 kayıt) | S |
| ~~C2~~ ✅ | **Bellek dışa/içe aktarma ve yaşlandırma** | **Eklendi:** JSON yedek indir/geri yükle, `unut:` komutu, 180 gün yaşlandırma | S |
| ~~C3~~ ✅ | **Sağlayıcı yedeği ve kota sayacı** | **Eklendi:** 429/402/5xx’te tek denemeli yedek model, günlük istek/hata sayacı | M |
| ~~C4~~ ✅ | **Açılışta kendi kendini kontrol** | **Eklendi:** `tanilama.py` 10 kontrol + Ayarlar › Sistem paneli | S |
| C5 | **Telefondan erişim** | **Kod değişikliği yapılmadı (bilinçli).** Rehber eklendi: [`UZAK_ERISIM.md`](UZAK_ERISIM.md) — Tailscale + SSH tüneli ile sunucu yine `127.0.0.1` dinler | L |

## D. Deneyim / kozmetik

| # | Eksik | Emek |
| --- | --- | --- |
| ~~D1~~ ✅ | **Eklendi:** ana sayfada “Bugün” kartı — hatırlatıcılar (geciken/bugün/hafta), defter bakiyesi, bugünün takvim etkinlikleri, son bellek kayıtları ve belge sayısı; `/api/today` + 2 dakikalık tazeleme | — |
| ~~D2~~ ✅ | **Eklendi:** `/` veya `Ctrl+K` komut paleti (15 komut, filtre, ↑↓, Enter), `Esc` panel/palet kapatma | — |
| ~~D3~~ ✅ | **Eklendi:** Ayarlar › Görünüm — Koyu/Açık/Sistem teması ve 13/14/16/18 px yazı boyutu (tarayıcıda saklanır) | — |

---

## Bilinçli olarak yapılmayacaklar

- Onaysız komut/uygulama çalıştırma (OpenClaw modeli) — README sınırı.
- CAPTCHA/giriş atlatma, gerçek para işlemi, AI’nın önerdiği komutu otomatik çalıştırma.
- Tarayıcı erişimi “tam” modunu etkinleştirme; şu an yalnızca hazırlık tercihi.
- **C5 — telefondan erişim**: sunucu yalnızca `127.0.0.1` dinler. Dışarı açmak token + TLS + yama yönetimi gerektirir
  ve “yalnızca bu bilgisayar” sınırını bozar. Kod tarafında değişiklik **yapılmadı**; güvenli yol
  [`UZAK_ERISIM.md`](UZAK_ERISIM.md) içinde adım adım anlatıldı (Tailscale + SSH tüneli).

## Önerilen sıra

1. ~~A1 + A2 + A3~~ ✅ (2026-11-03'te eklendi: otomatik başlatma, global dikte kısayolu, sunucu taraflı hatırlatıcı).
2. ~~A5 (akışlı yanıt) + A4 (web araması)~~ ✅ (2026-11-03'te eklendi).
4. ~~B1 (skill sistemi) + C1 (denetim izi) + C4 (tanılama)~~ ✅ (2026-11-03'te eklendi).
5. ~~**B2** (akışlı TTS + barge-in)~~ ✅ — tam çift yönlü ses.
6. ~~**B3** (belge okuma)~~ ✅ · ~~**B4** (takvim/e-posta)~~ ✅.
7. ~~**D1** (bugün özeti) + **D2** (komut paleti) + **D3** (tema/yazı boyutu) + **B5** (görsel üretimi)~~ ✅ (2026-11-03).
8. ~~**Kapanış turu**: WCAG AA kontrast düzeltmeleri + kontrast testi, uzun sohbet DOM sınırı,
   `?` kısayol yardımı, C5 erişim rehberi, arayüze bağlanmamış uçların kapatılması,
   uç kapsamı testi, Windows elle doğrulama listesi, CI sözdizimi kontrolünün genişletilmesi~~ ✅ (2026-11-03).
   **Yol haritasındaki her madde kapandı.** Açık kalan tek başlık “bilinçli olarak yapılmayacaklar”:
   tam tarayıcı erişimi ve sunucuyu dışarı açmak.

Yaklaşık toplam: A bloğu ~1,5 hafta, B1–B2 ~1 hafta, C1–C4 ~3 gün.
