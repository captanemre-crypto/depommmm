"""Testler için minik stdio MCP sunucusu (satır başına JSON-RPC)."""
import json
import sys


def yanit(kimlik, sonuc=None, hata=None):
    govde = {'jsonrpc': '2.0', 'id': kimlik}
    if hata:
        govde['error'] = {'code': -32000, 'message': hata}
    else:
        govde['result'] = sonuc or {}
    print(json.dumps(govde), flush=True)


for satir in sys.stdin:
    satir = satir.strip()
    if not satir:
        continue
    try:
        istek = json.loads(satir)
    except ValueError:
        continue
    yontem = istek.get('method')
    kimlik = istek.get('id')
    if kimlik is None:
        continue  # bildirim
    if yontem == 'initialize':
        yanit(kimlik, {'protocolVersion': '2024-11-05', 'capabilities': {},
                       'serverInfo': {'name': 'sahte', 'version': '0.1'}})
    elif yontem == 'tools/list':
        yanit(kimlik, {'tools': [
            {'name': 'echo', 'description': 'Girdiyi aynen döndürür',
             'inputSchema': {'type': 'object', 'properties': {'metin': {'type': 'string'}}}},
            {'name': 'topla', 'description': 'İki sayıyı toplar',
             'inputSchema': {'type': 'object', 'properties': {'a': {'type': 'number'}, 'b': {'type': 'number'}}}},
            {'name': 'patlat', 'description': 'Her zaman hata verir',
             'inputSchema': {'type': 'object', 'properties': {}}}]})
    elif yontem == 'tools/call':
        params = istek.get('params') or {}
        ad = params.get('name')
        arg = params.get('arguments') or {}
        if ad == 'echo':
            yanit(kimlik, {'content': [{'type': 'text', 'text': 'yankı: ' + str(arg.get('metin', ''))}]})
        elif ad == 'topla':
            yanit(kimlik, {'content': [{'type': 'text', 'text': str(arg.get('a', 0) + arg.get('b', 0))}]})
        elif ad == 'patlat':
            yanit(kimlik, hata='araç patladı')
        else:
            yanit(kimlik, hata='bilinmeyen araç')
    else:
        yanit(kimlik, hata='bilinmeyen yöntem')
