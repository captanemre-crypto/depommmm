---
ad: metin-analiz
aciklama: Verilen metnin karakter, kelime ve cümle sayısını hesaplar.
tetik: kelime say, karakter say, metni analiz et, kaç kelime
komut: python calistir.py
---
Bu beceri tamamen yerel çalışır; metin hiçbir yere gönderilmez.

Kullanım: sohbette `!metin-analiz <metin>` yaz ya da Ayarlar › Beceriler
bölümünden metni girip "Çalıştır" düğmesine bas.

Kendi becerini eklemek için `beceriler/<ad>/` klasörü aç, `SKILL.md` dosyasını
bu dosyaya benzet ve isteğe bağlı bir `calistir.py` yaz. stdin'den
`{"metin": "..."}` JSON'u okunur; stdout'a `{"reply": "..."}` yazılır.
