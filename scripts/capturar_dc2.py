"""Captura cruda de D.C., parte 2: alcaldías 1974–1994, registro, candidatos, resultados certificados y Kalshi completo."""
import json, re, time, urllib.parse, urllib.request
from pathlib import Path

UA_WM = 'pronostico-elecciones/1.1 (https://github.com/Zarate73/elecciones-eeuu-2026) python-urllib'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36'
OUT = Path('crudo'); OUT.mkdir(exist_ok=True)
log = []


def get(url, archivo, intentos=2):
    err = None
    for i in range(intentos):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA_WM if 'wiki' in url else UA, 'Accept': '*/*'}), timeout=60)
            b = r.read()
            (OUT / archivo).write_bytes(b)
            log.append(f'OK  {r.status} {len(b):>8} {url}')
            return b.decode('utf-8', 'replace')
        except Exception as e:                       # noqa: BLE001
            err = e
            if '404' in str(e) or '403' in str(e):
                break
            time.sleep(4)
    log.append(f'ERR {type(err).__name__}: {str(err)[:90]} {url}')
    return None


W = 'https://en.wikipedia.org/w/api.php?action=parse&prop=text&format=json&formatversion=2&redirects=1&page='
for a in (1974, 1978, 1982, 1986, 1990, 1994):
    p = f'{a}_Washington,_D.C.,_mayoral_election'
    get(W + p, f'wiki_{p}.json'); time.sleep(6)
for p in ('Rhonda_Hamilton', 'Elections_in_the_District_of_Columbia', '2014_Council_of_the_District_of_Columbia_election',
          '2022_Council_of_the_District_of_Columbia_election', '2025_Minneapolis_mayoral_election',
          '2024_United_States_presidential_election_in_the_District_of_Columbia'):
    get(W + p, f'wiki_{p}.json'); time.sleep(6)

B = 'https://www.dcboe.org'
for nom, ruta in (('registro_2026_09.pdf', '/getContentAsset/a743f9d8-0f69-4f70-bb69-489990d81cce/5ebbd046-860b-4ee1-81c8-43d0e3bc446e/Data-Statistics-Report-9_2026.pdf?language=en'),
                  ('registro_2022_09.pdf', '/getmedia/9733c15a-1756-44c3-a6f4-e93ead9974f7/Data-Statistics-Report-09_2022.pdf'),
                  ('registro_2018_09.pdf', '/getmedia/a28b773f-1af5-4c49-9e71-a5a1d23c65e4/DC-VOTER-REGISTRATION-STATS-SEPTEMBER-2018.PDF'),
                  ('registro_2014_09.pdf', '/getmedia/9c6b8b1e-62e2-486c-b967-52f58f79fbee/StatRep_30Sep2014.PDF'),
                  ('candidatos_general_2026.pdf', '/getContentAsset/1029b813-fb27-4055-9218-fbe40360aacb/5ebbd046-860b-4ee1-81c8-43d0e3bc446e/2026-General-CANDIDATES-07152026.pdf?language=en'),
                  ('writein_general_2026.pdf', '/getContentAsset/baa7b20c-9cbd-45fe-9842-986da48d2123/5ebbd046-860b-4ee1-81c8-43d0e3bc446e/2026-General-Election-WRITE-IN-CANDIDATES-07222026.pdf?language=en'),
                  ('rcv.html', '/rcv')):
    get(B + ruta, f'dcboe_{nom}')
get('https://earlyvoting.dcboe.org/', 'dcboe_earlyvoting.html')
# resultados certificados (CSV) y la app de resultados
R = 'https://electionresults.dcboe.org'
t = get(R + '/election_results/2022-General-Election', 'er_2022.html') or ''
for s in re.findall(r'src="(/static/js/[^"]+)"', t):
    get(R + s, 'er_js_' + s.rsplit('/', 1)[-1])
for nom in ('June_16_2026_Primary_Election_Certified_Results.csv', 'November_8_2022_General_Election_Certified_Results.csv',
            'November_6_2018_General_Election_Certified_Results.csv', 'November_4_2014_General_Election_Certified_Results.csv',
            'June_21_2022_Primary_Election_Certified_Results.csv'):
    get(f'{R}/Downloads/Reports/{nom}', f'cert_{nom}')
    get(f'https://electionresults.dcboe.org/Downloads/Reports/{nom}'.replace('Reports/', ''), f'cert2_{nom}')
for ruta in ('/api/elections', '/api/election', '/data/elections.json', '/election_results/api/elections'):
    get(R + ruta, 'er_api_' + ruta.strip('/').replace('/', '_'))

# Kalshi: paginación completa de eventos abiertos y filtro
K = 'https://api.elections.kalshi.com/trade-api/v2'
cursor, hits = '', []
for pag in range(80):
    try:
        r = urllib.request.urlopen(urllib.request.Request(f'{K}/events?status=open&limit=200&with_nested_markets=false' + (f'&cursor={cursor}' if cursor else ''), headers={'User-Agent': UA}), timeout=45)
        d = json.loads(r.read())
    except Exception as e:                           # noqa: BLE001
        log.append(f'ERR kalshi pag {pag}: {e}'); break
    for e in d.get('events', []) or []:
        tt = (e.get('title', '') + ' ' + e.get('event_ticker', '') + ' ' + (e.get('sub_title') or '')).lower()
        if ('mayor' in tt and ('d.c' in tt or 'washington' in tt or 'dc' in e.get('event_ticker', '').lower())) or 'lewis george' in tt:
            hits.append(e)
    cursor = d.get('cursor') or ''
    log.append(f'OK  kalshi pag {pag} {len(d.get("events", []))}')
    if not cursor:
        break
    time.sleep(0.3)
(OUT / 'kalshi_hits_dc.json').write_text(json.dumps(hits))
log.append(f'kalshi hits DC: {len(hits)}')
G = 'https://gamma-api.polymarket.com'
for q in ('Lewis George mayor', 'DC mayoral election', 'Washington DC mayor 2026'):
    get(f'{G}/public-search?q={urllib.parse.quote(q)}&limit_per_type=30&events_status=active', f"poly2_{q.replace(' ', '_')}.json")

(OUT / '_log.txt').write_text('\n'.join(log))
print(sum(x.startswith('OK') for x in log), 'OK', sum(x.startswith('ERR') for x in log), 'ERR')
