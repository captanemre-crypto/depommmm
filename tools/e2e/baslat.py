"""E2E testi için sunucuyu ayrı ve geçici bir veritabanıyla başlatır."""
import os
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
import server  # noqa: E402

server.DB = Path(os.getenv('EMRE_E2E_DB', Path(__file__).resolve().with_name('e2e.sqlite3')))
server.KEY = os.getenv('EMRE_E2E_TOKEN', 'e2e-anahtar')
PORT = int(os.getenv('EMRE_E2E_PORT', '8765'))
print(f'E2E sunucusu hazır: http://127.0.0.1:{PORT}', flush=True)
server.EmreServer(('127.0.0.1', PORT), server.Handler).serve_forever()
