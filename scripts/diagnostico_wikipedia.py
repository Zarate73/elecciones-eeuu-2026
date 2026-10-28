"""Diagnóstico de Wikipedia (corre en GitHub Actions; guarda en crudo/): action=parse frente a la API REST (HTML de
Parsoid, cacheado en el borde) y comportamiento ante ráfagas (503 con Retry-After)."""
import json, time, urllib.parse
from pathlib import Path
import urllib.request, urllib.error


class R:
    def __init__(self, code, h, b):
        self.status_code, self.headers, self.content = code, h, b
        self.ok = code == 200


def get(url, params=None):
    if params:
        url += '?' + urllib.parse.urlencode(params)
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA_ACTUAL[0] or UA}), timeout=60)
        return R(r.status, {k.lower(): v for k, v in r.headers.items()}, r.read())
    except urllib.error.HTTPError as e:
        return R(e.code, {k.lower(): v for k, v in e.headers.items()}, e.read())

UA_ACTUAL = [None]
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/131.0 Safari/537.36 pronostico-elecciones/1.0')
OUT = Path('crudo'); OUT.mkdir(exist_ok=True)
log = []
T = '2026_United_States_Senate_election_in_North_Carolina'
P = {'action': 'parse', 'page': T, 'prop': 'text', 'format': 'json', 'formatversion': 2, 'redirects': 1}
UAS = {'politica': 'pronostico-elecciones/1.1 (https://github.com/Zarate73/elecciones-eeuu-2026) python-urllib',
       'navegador': UA}
for nom, ua in UAS.items():
    UA_ACTUAL[0] = ua
    for i in range(5):
        t0 = time.time()
        r = get('https://en.wikipedia.org/w/api.php', P)
        log.append(f'{nom} parse #{i}: HTTP {r.status_code} {time.time() - t0:.1f}s retry-after={r.headers.get("retry-after")} '
                   f'len={len(r.content)} {r.content[:160]!r}' if not r.ok else f'{nom} parse #{i}: HTTP 200 len={len(r.content)}')
        time.sleep(3)
    r = get(f'https://en.wikipedia.org/api/rest_v1/page/html/{T}')
    log.append(f'{nom} rest_v1: HTTP {r.status_code} len={len(r.content)} ' + ('' if r.ok else repr(r.content[:160])))
    if r.ok:
        (OUT / f'rest_v1_{nom}.html').write_bytes(r.content)
    time.sleep(20)
(OUT / '_log.txt').write_text('\n'.join(log))
print('\n'.join(log))
