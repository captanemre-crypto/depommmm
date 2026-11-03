# Windows'ta elle doğrulama listesi

Bu liste, **yalnızca gerçek Windows makinesinde** doğrulanabilecek özellikleri adım adım kontrol etmek için
hazırlandı. Linux CI bu özelliklerin çoğunu çalıştıramaz (SAPI/Piper sesleri, WebView2 masaüstü penceresi,
tepsi simgesi, `.bat` dosyaları, global kısayol, uygulama açma, ekran görüntüsü, etkin pencereye yazma).

Toplam süre: ~25 dakika. Her satırda **Beklenen** davranış yazıyor; farklı bir şey görürsen o satırı not al.

---

## 0. Hazırlık

```powershell
cd C:\Users\SERVER\Desktop\jarvis
git pull
py -3 --version          # 3.11 veya 3.12
baslat.bat
```

- [ ] Tarayıcı `http://127.0.0.1:8765` adresinde açılıyor, karşılama mesajı görünüyor.
- [ ] Sağ üstteki **PROTOTİP** yanında sürüm `2026-11-03.9` (Ayarlar › Sistem'de de yazar).
- [ ] Konsol penceresinde Python hatası (traceback) yok.

---

## 1. Temel sohbet ve akış

| Kontrol | Beklenen |
| --- | --- |
| [ ] “merhaba” yaz | Yanıt **yazılarak** akar (tek blok hâlinde gelmez) |
| [ ] `Ctrl+C` / ağ kablosunu çek | Akış sessizce durmaz; açık Türkçe hata görünür |
| [ ] Ayarlar › Sistem › “Sistemi tanı” | 10 kontrol listelenir, hepsi yeşil/sarı gerekçeli |

---

## 2. Ses: Türkçe konuşma, akışlı okuma, söz kesme (B2)

1. Ayarlar › **Ses** → bir Türkçe ses seç → **Örneği dinle**.
   - [ ] Ses duyuluyor, anlaşılır. (Ses yoksa `ses_model_kur.bat` çalıştır.)
2. Aynı ekranda **Akışlı seslendirme** ve **Söz kesme** açık olsun.
3. Sol alttaki **◉ Ses kapalı** düğmesine bas (mikrofon açılır).
   - [ ] “Yerel mikrofon açık…” bildirimi geliyor.
4. “Bana üç cümlelik bir hikâye anlat” de.
   - [ ] Emre metni yazmaya başladıktan **kısa süre sonra** okumaya başlıyor (yanıtın tamamını beklemiyor).
   - [ ] Okuma sürerken araya gir: **okuma durur**, seni dinlemeye geçer.
5. “Akışlı seslendirme”yi **kapat**, aynı soruyu sor.
   - [ ] Bu kez yanıt bittikten sonra tek parça okuyor (eski davranış).

---

## 3. Belgeler (B3 · yalnızca Windows'ta gerçek dosyalarla)

| Adım | Beklenen |
| --- | --- |
| [ ] Ayarlar › Belgeler → bir **PDF** seç → ekle | “Eklendi: … · N sayfa” |
| [ ] Aynı sekmede “sözleşme kaç ay?” → **Belgeye sor** | Yanıt + “Kaynaklar: [1] dosya.pdf · sayfa N” |
| [ ] Bir **.docx** dosyası ekle | Metin çıkarılır (boş uyarısı gelmez) |
| [ ] Taranmış (fotoğraf) PDF ekle | “Belgede metin bulunamadı (taranmış PDF olabilir; OCR desteklenmiyor)” |
| [ ] Belgeyi **Sil** | Onay sorar, listeden kalkar |
| [ ] 25 MB'lık bir dosya ekle | “Dosya çok büyük (en fazla 20 MB)” |

---

## 4. Takvim ve posta (B4)

1. Ayarlar › **Takvim & posta** → takvim yolunu yaz:
   `C:\Users\SERVER\Desktop\takvim.ics` → **Takvim yolunu kaydet** → **Bu haftayı göster**.
   - [ ] Etkinlikler listelenir; tekrarlayanlar `⟳` ile işaretli.
2. Posta yolu: bir `.eml` dosyası veya `.mbox` arşivi → **Posta yolunu kaydet** → **Son 5 iletiyi göster**.
   - [ ] Konu/gönderen/tarih görünür, ekler açılmaz.
3. Mikrofon açıkken “bu hafta takvimde ne var” de.
   - [ ] Emre **model olmadan** yanıtlar (Ollama kapalıyken de çalışır).

---

## 5. “Bugün” kartı (D1)

- [ ] Ana sayfada 4 bölüm: Hatırlatıcılar · Defter · Takvim · Bellek ve belgeler.
- [ ] Bir hatırlatıcıyı 1 saat sonrasına ekle → **Yenile** → kartta görünür.
- [ ] Süresi geçmiş bir hatırlatıcı ⚠ ile kırmızı görünür.
- [ ] Takvim yolu boşsa kart “Takvim yolu tanımlı değil” der (hata değil).

---

## 6. Komut paleti, kısayol yardımı, tema (D2 · D3)

| Tuş | Beklenen |
| --- | --- |
| [ ] `/` | Palet açılır, yazdıkça filtrelenir |
| [ ] `Ctrl+K` | Palet açılır (metin alanında yazarken de) |
| [ ] `↑` `↓` `Enter` | Seçili komut çalışır |
| [ ] `Esc` | Palet/panel kapanır |
| [ ] `?` | Kısayol yardım paneli açılır |
| [ ] Ayarlar › Görünüm → **Açık** | Tüm paneller açık temaya geçer, yazılar okunur |
| [ ] Yazı boyutu **18 px** | Metin büyür, düzen bozulmaz |
| [ ] Tarayıcıyı kapat/aç | Tema ve yazı boyutu hatırlanır (koyu varsayılan) |

---

## 7. Görsel üretimi (B5 · sağlayıcıya bağlı)

- [ ] Ayarlar › Ücretsiz API'de bir sağlayıcı bağlı mı? Bağlı değilse bu bölümü atla.
- [ ] Görünüm › **Görsel üret panelini aç** → istem yaz → **Görsel üret** → onay.
  - [ ] Görsel görünür veya “Sağlayıcı görsel üretimini desteklemiyor…” açık hatası gelir.
- [ ] **Görseli indir** → `emre-gorsel.png` bilgisayara iner.
- [ ] `jarvis` klasöründe yeni bir görsel dosyası **oluşmadığını** doğrula (diske yazılmıyor).

---

## 8. Yalnızca Windows'ta çalışan özellikler

| Kontrol | Beklenen |
| --- | --- |
| [ ] Ayarlar › Sistem › **Bilgisayar açılınca başlat** | Başlangıç klasörüne kısayol eklenir (yönetici izni istemez) |
| [ ] `Ctrl+Alt+D` (başka bir pencerede) | Dikte paneli açılır / sayfa dikte moduna geçer |
| [ ] Dikte panelinde **Aktif pencereye yaz** | Hedef pencerede metin belirir (yönetici olarak açılmış pencereler hariç) |
| [ ] Uygulamalar › **Not Defteri** | Onay sonrası Not Defteri açılır |
| [ ] Sohbette **▣** (ekranı sor) | Onaylı ekran görüntüsü alınır, soru yanıtlanır |
| [ ] `masaustu_baslat.bat` | WebView2 penceresi açılır, tepsi simgesi görünür |
| [ ] Hatırlatıcı süresi gelsin (tarayıcı kapalı) | Windows bildirimi/balonu + ses gelir, açılışta listede görünür |

---

## 9. Güvenlik sınırları (hepsi Windows'ta da geçerli)

- [ ] Başka bir cihazdan `http://<bilgisayar-ip>:8765` → **bağlanamaz** (sunucu yalnızca `127.0.0.1`).
- [ ] Tarayıcı konsolunda `fetch('http://127.0.0.1:8765/api/status')` (token olmadan) → **403**.
- [ ] Sayfa kaynağını görüntüle → token `<meta name="emre-token">` içinde, `localStorage`'da **yok**.
- [ ] `saglayici_ayar.json` içinde anahtar var, git'e eklenmiyor (`git status` temiz).
- [ ] Ekran görüntüsü, uygulama açma, mesaj gönderme, dosya yazma: hepsi **onay** istiyor.

---

## 10. Telefondan erişim (isteğe bağlı)

- [ ] Gerekmiyorsa bu bölümü atla. Gerekiyorsa **[`UZAK_ERISIM.md`](UZAK_ERISIM.md)** içindeki
      Tailscale + SSH tüneli adımlarını uygula; sunucuyu `0.0.0.0`'a **alma**.
- [ ] Tünel açıkken telefondan `http://127.0.0.1:8765` açılıyor mu?

---

## 11. Sonuç

Her satırı işaretledikten sonra:

```powershell
py -3 -m unittest discover -s tests -t . -v      # 580 test
cd tools\e2e; npm test                            # 63/63 kontrol (Node gerekir)
```

Bir satır başarısızsa: konsol çıktısı + hangi satır olduğunu not et. Sunucu günlüğü `ses_hata.log`
ve terminal penceresinde; arayüz hataları tarayıcı konsolunda görünür.

> Bu dosya bir **kontrol listesidir**; otomatik testler Linux CI'da koşar ve Windows'a özgü
> bileşenleri (SAPI, WebView2, tepsi, global kısayol) kapsamaz.
