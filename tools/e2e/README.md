# EMRE — Arayüz uçtan uca (E2E) testi

Gerçek `server.py` süreci + gerçek `index.html` üzerinde, jsdom ile arayüzü sürer.
Amaç: Python birim testlerinin göremediği **arayüz kırılmalarını** (boş bölüm,
çalışmayan düğme, sessiz JS hatası, yanlış API sözleşmesi) yakalamak.

## Gereksinimler
- Node.js 18+ (yalnızca geliştirme/test için; uygulama Node kullanmaz)
- Python 3.11+

## Çalıştırma

```bash
# 1) Sunucuyu geçici veritabanıyla başlat (ayrı terminal)
python3 tools/e2e/baslat.py

# 2) Bağımlılıkları kur ve testi koş
cd tools/e2e
npm install
npm test
```

Varsayılan adres `http://127.0.0.1:8765`, anahtar `e2e-anahtar`. Farklı değerler için:

```bash
EMRE_E2E_PORT=8899 python3 tools/e2e/baslat.py
EMRE_E2E_BASE=http://127.0.0.1:8899 npm test
```

> Not: `baslat.py` portu dinlerken açık bir Emre sunucusu varsa çakışır; önce onu kapatın.
> Test veritabanı `tools/e2e/e2e.sqlite3` dosyasıdır (`.gitignore` kapsamında) ve gerçek
> `emre.sqlite3` dosyanıza dokunmaz.

## Neyi kontrol eder?
Sayfa yüklenmesi, token meta etiketi, canlı durum paneli, yaklaşan hatırlatıcı kartı,
tüm sol menü bölümleri, sohbet gönderimi (Ollama kapalıyken anlaşılır hata), defter
(hesap aç → işlem ekle → listele), mükerrer hesap reddi (Türkçe büyük/küçük harf),
hatırlatıcı ekleme/silme, ayarların altı sekmeleri, geliştirici dosya kaydetme,
mikrofon uyarısı, uygulama kartı, yeni sohbet, geçersiz oturum anahtarında yenileme
uyarısı ve token'ın `localStorage`'a yazılmaması.

Çıktı JSON'dur: `basarisiz` dizisi boşsa ve `js_problemleri` boşsa test geçmiştir.
