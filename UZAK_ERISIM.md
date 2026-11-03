# Telefondan erişim — güvenli yol (kod değişikliği yapılmadan)

Bu belge `YOL_HARITASI.md` içindeki **C5** maddesi için yazıldı. Emre'nin sunucusu
**yalnızca `127.0.0.1`** dinler ve bu davranış **değiştirilmedi**. Aşağıdaki yöntem,
sunucuyu dışarı açmadan telefonundan kullanmanın en güvenli yolunu anlatır.

> Kısa cevap: **portu açma.** Aynı özel ağa bağlanan bir tünel (Tailscale/WireGuard) kur,
> Emre'yi yine `127.0.0.1:8765` üzerinde bırak.

---

## 1. Neden sunucu dışarı açılmıyor?

`server.py` şu üç koruma ile çalışır:

1. **Dinleme adresi**: `('127.0.0.1', 8765)` — yalnızca bu bilgisayar.
2. **Origin kontrolü**: tarayıcıdan gelen isteklerde `Origin`/`Host` doğrulanır; başka bir
   siteden tetiklenen istekler reddedilir.
3. **Token**: her istek `X-Emre-Token` başlığı ister; token sayfa ile birlikte üretilir.

Sunucuyu `0.0.0.0`'a almak bu üç korumanın ikisini (adres ve Origin varsayımını) zayıflatır:
yerel ağdaki her cihaz, hatta misafir Wi-Fi'daki telefonlar, arayüze ulaşabilir hâle gelir.
Ayrıca HTTPS olmadığı için token düz metin gider.

Bu yüzden kod tarafında **hiçbir değişiklik yapılmadı**.

---

## 2. Önerilen yöntem: Tailscale (özel ağ) + yerel port

Tailscale, cihazların arasında şifreli bir özel ağ kurar. Emre yine yalnızca `127.0.0.1`
dinler; telefondaki tarayıcı, tünelin **kendi cihazında** açtığı yerel adrese bağlanır.

### Adım adım (Windows bilgisayar)

1. `https://tailscale.com` adresinden hesap aç (ücretsiz katman kişisel kullanım için yeterli).
2. Windows'a Tailscale kur, hesabınla giriş yap. Bilgisayarın özel ağda bir ad alır
   (örnek: `masaustu-abcde`).
3. Telefona Tailscale uygulamasını kur, **aynı hesapla** giriş yap.
4. Telefonda Emre'yi açmak için iki seçenek var:

**A) En basit: yerel porta tünel (SSH gerekir)**
```powershell
# Windows'ta OpenSSH Sunucusu'nu etkinleştirdikten sonra, telefonda bir SSH uygulamasıyla:
ssh -L 8765:127.0.0.1:8765 SERVER@masaustu-abcde
# Sonra telefonda tarayıcıdan: http://127.0.0.1:8765/?token=...
```
Tünel açıkken telefonun kendi `127.0.0.1:8765` adresi Emre'ye bağlanır. Emre'nin dinlediği
adres değişmez.

**B) Tailscale'in kendi "serve" özelliği**
```powershell
tailscale serve --bg 8765
```
Bu komut yalnızca **özel ağ içindeki** cihazlara açık bir HTTPS adresi üretir
(`https://masaustu-abcde.<tailnet>.ts.net`). Adres internete açık değildir; aynı hesaba
bağlı cihazlar erişebilir.

> Not: yöntem B, Emre'nin Origin kontrolünü etkiler. Sayfa `https://…ts.net` üzerinden
> açıldığında tarayıcı bu adresi `Origin` olarak gönderir ve sunucu isteği reddedebilir.
> Bu durumda A yolunu kullan (adres yine `127.0.0.1` olur) ya da erişimi kapat.

---

## 3. Yapılmaması gerekenler

- **Modem/router'dan port yönlendirme** (8765'i dışarı açmak): token ağ dinleyicileri
  tarafından görülebilir, HTTPS yoktur, güncelleme yapılmadığında bilinen açıklar açık kalır.
- **ngrok / Cloudflare Tunnel gibi herkese açık tüneller**: adres tahmin edilebilir ve
  genelde kimlik doğrulaması yoktur; arayüzdeki “uygulama aç / kod çalıştır” düğmeleri
  yetkisiz kişilerin eline geçebilir.
- **Sunucuyu `0.0.0.0`'a almak** (kod değişikliği): README'deki “yalnızca 127.0.0.1” sınırı
  bilinçli bir karardır.

---

## 4. Telefonda ne çalışır, ne çalışmaz?

| Özellik | Telefonda |
| --- | --- |
| Sohbet, defter, hatırlatıcı, belgeler, takvim/posta | ✅ çalışır |
| Komut paleti, tema, “Bugün” kartı | ✅ çalışır |
| Sesli giriş (mikrofon) | ⚠️ tarayıcı izinleri ve WebM desteğine bağlı |
| Windows uygulaması açma, dikte ile pencereye yazma, ekran görüntüsü | ❌ yalnızca bilgisayarda |

---

## 5. Kararın özeti

- **Kod değişikliği**: yok.
- **Yeni bağımlılık**: yok.
- **Öneri**: telefondan erişim gerekiyorsa Tailscale + SSH tüneli (yöntem A).
- **Kural**: Emre her durumda yalnızca `127.0.0.1` dinler.
