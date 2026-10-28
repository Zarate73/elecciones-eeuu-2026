"""Diagnóstico de Wikipedia (corre en GitHub Actions; guarda en crudo/): action=parse frente a la API REST (HTML de
Parsoid, cacheado en el borde) y comportamiento ante ráfagas (503 con Retry-After)."""
import json, time, urllib.parse
from pathlib import Path
import requests

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/131.0 Safari/537.36 pronostico-elecciones/1.0')
OUT = Path('crudo'); OUT.mkdir(exist_ok=True)
log = []
T = '2026_United_States_Senate_election_in_North_Carolina'
P = {'action': 'parse', 'page': T, 'prop': 'text', 'format': 'json', 'formatversion': 2, 'redirects': 1}
for i in range(6):                                   # ráfaga de action=parse
    t0 = time.time()
    r = requests.get('https://en.wikipedia.org/w/api.php', params=P, headers={'User-Agent': UA}, timeout=60)
    log.append(f'parse #{i}: HTTP {r.status_code} {time.time() - t0:.1f}s retry-after={r.headers.get("retry-after")} '
               f'x-cache={r.headers.get("x-cache-status")} len={len(r.content)}')
    if i == 0 and r.ok:
        (OUT / 'parse.json').write_bytes(r.content)
for nom, url in (('rest_v1', f'https://en.wikipedia.org/api/rest_v1/page/html/{T}'),
                 ('rest_php', f'https://en.wikipedia.org/w/rest.php/v1/page/{T}/html')):
    for i in range(3):
        t0 = time.time()
        r = requests.get(url, headers={'User-Agent': UA}, timeout=60)
        log.append(f'{nom} #{i}: HTTP {r.status_code} {time.time() - t0:.1f}s x-cache={r.headers.get("x-cache-status")} '
                   f'etag={r.headers.get("etag", "")[:40]} len={len(r.content)}')
        if i == 0 and r.ok:
            (OUT / f'{nom}.html').write_bytes(r.content)
(OUT / '_log.txt').write_text('\n'.join(log))
print('\n'.join(log))
