"""E2E testi için sunucuyu ayrı ve geçici bir veritabanıyla başlatır.

Ayrıca testlerin "ücretsiz API" akışını deneyebilmesi için OpenAI uyumlu sahte
bir sağlayıcıyı (varsayılan http://127.0.0.1:8899/v1) ayağa kaldırır.
"""
import os
import sys
import threading
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(Path(__file__).resolve().parent))

os.environ.setdefault('EMRE_BILDIRIM_ARALIK', '3')  # hatırlatıcı işçisi testte hızlı çalışsın

import sahte_saglayici  # noqa: E402

import server  # noqa: E402

server.DB = Path(os.getenv('EMRE_E2E_DB', Path(__file__).resolve().with_name('e2e.sqlite3')))
server.KEY = os.getenv('EMRE_E2E_TOKEN', 'e2e-anahtar')
PORT = int(os.getenv('EMRE_E2E_PORT', '8765'))
SAG_PORT = int(os.getenv('EMRE_E2E_FAKE_PROVIDER_PORT', '8899'))
threading.Thread(target=sahte_saglayici.baslat(SAG_PORT).serve_forever, daemon=True).start()
print(f'Sahte sağlayıcı hazır: http://127.0.0.1:{SAG_PORT}/v1', flush=True)
print(f'E2E sunucusu hazır: http://127.0.0.1:{PORT}', flush=True)
server.arka_planlari_baslat()  # hatırlatıcı işçisi + (açıksa) global kısayol
server.EmreServer(('127.0.0.1', PORT), server.Handler).serve_forever()
