"""Segunda pasada: páginas de Wikipedia que dieron 429 y precios de Polymarket 2022 con otros parámetros."""
import json, time, urllib.parse, urllib.request
from pathlib import Path
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36'
OUT = Path('crudo'); (OUT / 'wiki').mkdir(parents=True, exist_ok=True); (OUT / 'poly22').mkdir(parents=True, exist_ok=True)
log = []
def get(url, nombre, intentos=4):
    for i in range(intentos):
        try:
            b = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=40).read()
            (OUT / nombre).write_bytes(b); log.append(f'OK {len(b)} {url}'); return b
        except Exception as e:
            err = e
            if i + 1 < intentos: time.sleep(10 * (i + 1))
    log.append(f'ERR {err} {url}')
W = 'https://en.wikipedia.org/w/api.php?action=parse&prop=text&format=json&formatversion=2&redirects=1&page='
for p in ['2024_United_States_presidential_election_in_Minnesota', '2024_United_States_presidential_election_in_New_Hampshire',
          '2024_United_States_Senate_election_in_Arizona', '2024_United_States_Senate_election_in_Michigan',
          '2024_United_States_Senate_election_in_Nevada', '2024_United_States_Senate_election_in_New_Jersey',
          '2024_United_States_Senate_election_in_New_York', '2024_United_States_Senate_election_in_Missouri']:
    get(W + p, f'wiki/{p}.json'); time.sleep(3)
toks = json.loads(Path('scripts/_poly2022_tokens.json').read_text())
for t in toks:
    if not t['token']:
        continue
    for nom, q in (('a', f"interval=max&fidelity=60"), ('b', 'startTs=1664582400&endTs=1668038400&fidelity=60'),
                   ('c', 'startTs=1664582400&endTs=1668038400&fidelity=1440')):
        get(f"https://clob.polymarket.com/prices-history?market={t['token']}&{q}", f"poly22/hist_{t['id']}_{nom}.json", 1)
    if t.get('cond'):
        get(f"https://data-api.polymarket.com/trades?market={t['cond']}&limit=500", f"poly22/trades_{t['id']}.json", 1)
    time.sleep(0.3)
(OUT / '_log_faltantes.txt').write_text('\n'.join(log))
print(sum(x.startswith('OK') for x in log), 'OK', sum(x.startswith('ERR') for x in log), 'ERR')
