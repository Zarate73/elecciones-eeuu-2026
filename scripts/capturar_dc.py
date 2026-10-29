"""Captura cruda de fuentes de Washington D.C. (corre en GitHub Actions; guarda en crudo/)."""
import json, re, time, urllib.parse, urllib.request
from pathlib import Path

UA_WM = 'pronostico-elecciones/1.1 (https://github.com/Zarate73/elecciones-eeuu-2026) python-urllib'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36'
OUT = Path('crudo'); OUT.mkdir(exist_ok=True)
log = []


def nombre(url):
    return re.sub(r'[^A-Za-z0-9._-]+', '_', url.split('://', 1)[1])[:150]


def get(url, archivo=None, intentos=2):
    err = None
    for i in range(intentos):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA_WM if 'wiki' in url else UA, 'Accept': '*/*'}), timeout=45)
            b = r.read()
            (OUT / (archivo or nombre(url))).write_bytes(b)
            log.append(f'OK  {r.status} {len(b):>8} {url}')
            return b.decode('utf-8', 'replace')
        except Exception as e:                       # noqa: BLE001
            err = e
            if '404' in str(e) or '403' in str(e):
                break
            time.sleep(4)
    log.append(f'ERR {type(err).__name__}: {str(err)[:90]} {url}')
    return None


def js(url, archivo=None):
    t = get(url, archivo)
    try:
        return json.loads(t) if t else None
    except Exception:                                # noqa: BLE001
        return None


W = 'https://en.wikipedia.org/w/api.php?action=parse&prop=text&format=json&formatversion=2&redirects=1&page='
for p in ('2026_Washington,_D.C.,_mayoral_election', '2022_Washington,_D.C.,_mayoral_election',
          '2018_Washington,_D.C.,_mayoral_election', '2014_Washington,_D.C.,_mayoral_election',
          '2010_Washington,_D.C.,_mayoral_election', '2006_Washington,_D.C.,_mayoral_election',
          '2002_Washington,_D.C.,_mayoral_election', '1998_Washington,_D.C.,_mayoral_election',
          '2026_Council_of_the_District_of_Columbia_election', '2025_New_York_City_mayoral_election',
          '2021_Buffalo_mayoral_election', 'Janeese_Lewis_George', 'Initiative_83'):
    get(W + p, f'wiki_{p}.json'); time.sleep(6)

# Kalshi: búsqueda de series de la alcaldía de DC
K = 'https://api.elections.kalshi.com/trade-api/v2'
fin = int(time.time())
cand = set()
for serie in ('KXMAYORDC', 'MAYORDC', 'KXDCMAYOR', 'DCMAYOR', 'KXMAYORWASHINGTONDC', 'KXMAYORDCPARTY'):
    d = js(f'{K}/events?series_ticker={serie}&limit=20&with_nested_markets=true', f'kalshi_serie_{serie}.json')
    for e in (d or {}).get('events', []) or []:
        cand.add((serie, e.get('event_ticker')))
for serie, ev in sorted(cand):
    e = js(f'{K}/events/{ev}?with_nested_markets=true', f'kalshi_evento_{ev}.json')
    ms = ((e or {}).get('event') or {}).get('markets') or (e or {}).get('markets') or []
    for m in ms:
        t = m['ticker']
        js(f'{K}/series/{serie}/markets/{t}/candlesticks?start_ts={fin - 400 * 86400}&end_ts={fin}&period_interval=1440',
           f'kalshi_velas_{t}.json')
    js(f'{K}/markets?event_ticker={ev}', f'kalshi_markets_{ev}.json')
# búsqueda amplia en Kalshi (eventos abiertos de elecciones con «D.C.» o «Washington»)
cursor = ''
for pag in range(15):
    d = js(f'{K}/events?status=open&limit=200&with_nested_markets=false' + (f'&cursor={cursor}' if cursor else ''), f'kalshi_eventos_abiertos_{pag}.json')
    if not d:
        break
    cursor = d.get('cursor') or ''
    if not cursor:
        break

# Polymarket
G = 'https://gamma-api.polymarket.com'
vistos = set()
for q in ('dc mayor', 'washington dc mayor', 'janeese lewis george', 'd.c. mayoral'):
    d = js(f'{G}/public-search?q={urllib.parse.quote(q)}&limit_per_type=30&events_status=all', f"poly_busqueda_{q.replace(' ', '_').replace('.', '')}.json")
    for ev in (d or {}).get('events', []) or []:
        t = (ev.get('title') or '').lower()
        if '2026' not in (ev.get('endDate') or '') or not ('mayor' in t and ('d.c' in t or 'dc' in t or 'washington' in t)):
            continue
        (OUT / f"poly_evento_{ev.get('slug')[:100]}.json").write_text(json.dumps(ev))
        for m in ev.get('markets', []) or []:
            toks = m.get('clobTokenIds')
            toks = json.loads(toks) if isinstance(toks, str) else toks
            if toks and m.get('id') not in vistos:
                vistos.add(m.get('id'))
                js(f'https://clob.polymarket.com/prices-history?market={toks[0]}&interval=max&fidelity=1440', f"poly_hist_{m.get('id')}.json")

# Voto anticipado y resultados oficiales
CV = 'https://civicapi.org/api/v2/early-vote'
for c in ('capabilities', 'returned', 'requested', 'inperson', 'returned/demographics?by=party', 'inperson/demographics?by=party'):
    get(f'{CV}/DC/{c}', f"civic_DC_{c.replace('/', '_').replace('?', '_').replace('=', '_')}.json")
get('https://electionresults.dcboe.org/election_results/2026-Primary-Election', 'dcboe_primaria_2026.html')
get('https://electionresults.dcboe.org/election_results/2022-General-Election', 'dcboe_general_2022.html')
get('https://www.dcboe.org/elections/2026-elections', 'dcboe_2026.html')
get('https://www.dcboe.org/data,-maps,-forms/voter-registration-statistics', 'dcboe_registro.html')
get('https://www.dcboe.org/candidates/2026-candidates', 'dcboe_candidatos.html')
get('https://www.onpointpolitics.us/api/polls/dc-mayor-2026', 'onpoint_dc.json')

(OUT / '_log.txt').write_text('\n'.join(log))
print(sum(x.startswith('OK') for x in log), 'OK', sum(x.startswith('ERR') for x in log), 'ERR')
