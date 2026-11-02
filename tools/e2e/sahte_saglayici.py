"""E2E testleri için OpenAI uyumlu sahte sağlayıcı (internet gerekmez)."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODELLER = ['meta-llama/llama-3.3-70b-instruct:free', 'openai/gpt-oss-20b:free', 'ornek/paid-model']


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _json(self, kod, govde):
        veri = json.dumps(govde, ensure_ascii=False).encode()
        self.send_response(kod)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(veri)))
        self.end_headers()
        self.wfile.write(veri)

    def do_GET(self):
        if self.path.endswith('/models'):
            return self._json(200, {'data': [{'id': m} for m in MODELLER]})
        self._json(404, {'error': 'yok'})

    def do_POST(self):
        n = int(self.headers.get('Content-Length', '0'))
        govde = json.loads(self.rfile.read(n) or b'{}')
        if govde.get('model') == 'tool-model':
            return self._json(200, {'choices': [{'message': {
                'role': 'assistant', 'content': None,
                'tool_calls': [{'id': '1', 'type': 'function',
                                'function': {'name': 'ledger_list', 'arguments': '{}'}}]}}]})
        return self._json(200, {'choices': [{'message': {
            'role': 'assistant',
            'content': 'Sahte sağlayıcı yanıtı: sorunu aldım.'}}]})


def baslat(port=8899):
    httpd = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    return httpd
