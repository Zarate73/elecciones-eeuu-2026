import json, time, urllib.request
from pathlib import Path
OUT = Path('crudo'); OUT.mkdir(exist_ok=True)
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
log = []
def get(u, nom, h=None):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': UA, 'Accept': '*/*', 'Cache-Control': 'no-cache', **(h or {})}), timeout=60)
        b = r.read(); (OUT / nom).write_bytes(b[:3_000_000]); log.append(f'OK {r.status} {len(b)} lm={r.headers.get("Last-Modified")} age={r.headers.get("Age")} cache={r.headers.get("X-Cache") or r.headers.get("cf-cache-status")} {u}'); return b
    except Exception as e:
        log.append(f'ERR {e} {u}')
t = int(time.time())
b = get(f'https://flelectionfiles.floridados.gov/enightfilespublic/20261103_ElecResultsFL.txt?t={t}', 'fl_nc.txt')
if b:
    gov = [l for l in b.decode('utf-8', 'replace').splitlines() if '\tGOV\t' in l]
    log.append('FL nocache suma gob ' + str(sum(int(l.split('\t')[14] or 0) for l in gov)))
get('https://flelectionfiles.floridados.gov/enightfilespublic/', 'fl_dir.html')
get('https://results.elections.myflorida.com/', 'fl_home.html')
get('https://results.texas-election.com/', 'tx_home.html')
get(f'https://results.texas-election.com/static/data/Version.json?t={t}', 'tx_v.json')
for w in ('2026_Ohio_gubernatorial_election', '2026_Florida_gubernatorial_election', '2026_Texas_gubernatorial_election'):
    get(f'https://en.wikipedia.org/w/api.php?action=parse&page={w}&prop=text&format=json&formatversion=2', f'wiki_{w}.json',
        {'User-Agent': 'pronostico-elecciones/1.1 (https://github.com/Zarate73/elecciones-eeuu-2026)'})
(OUT / '_log.txt').write_text('\n'.join(log)); print('\n'.join(log))
