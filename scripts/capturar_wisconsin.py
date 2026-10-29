"""Captura cruda de fuentes de Wisconsin (corre en GitHub Actions; guarda en crudo/)."""
import json, re, time, urllib.parse, urllib.request
from pathlib import Path

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36'
OUT = Path('crudo'); OUT.mkdir(exist_ok=True)
log = []


def nombre(url):
    return re.sub(r'[^A-Za-z0-9._-]+', '_', url.split('://', 1)[1])[:150]


def get(url, archivo=None, intentos=2):
    err = None
    for i in range(intentos):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': '*/*'}), timeout=45)
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
for p in ('2026_Wisconsin_gubernatorial_election', '2022_Wisconsin_gubernatorial_election', '2018_Wisconsin_gubernatorial_election',
          '2014_Wisconsin_gubernatorial_election', '2024_United_States_Senate_election_in_Wisconsin',
          '2022_United_States_Senate_election_in_Wisconsin', '2018_United_States_Senate_election_in_Wisconsin',
          '2024_United_States_presidential_election_in_Wisconsin', '2020_United_States_presidential_election_in_Wisconsin',
          '2016_United_States_presidential_election_in_Wisconsin', '2025_Wisconsin_Supreme_Court_election',
          '2026_Wisconsin_elections', 'David_Crowley_(politician)', 'Tom_Tiffany'):
    get(W + p, f'wiki_{p}.json'); time.sleep(4)
get('https://www.270towin.com/2026-governor-polls/wisconsin', 't270_wi_gob.html')

# Kalshi
K = 'https://api.elections.kalshi.com/trade-api/v2'
fin = int(time.time())
cand = {('GOVPARTYWI', 'GOVPARTYWI-26')}
for serie in ('GOVPARTYWI', 'KXGOVWI', 'GOVMARGINWI', 'KXGOVWIMARGIN'):
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

# Polymarket
G = 'https://gamma-api.polymarket.com'
vistos = set()
for q in ('wisconsin governor', 'crowley tiffany', 'tom tiffany'):
    d = js(f'{G}/public-search?q={urllib.parse.quote(q)}&limit_per_type=30&events_status=all', f"poly_busqueda_{q.replace(' ', '_')}.json")
    for ev in (d or {}).get('events', []) or []:
        t = (ev.get('title') or '').lower()
        if '2026' not in (ev.get('endDate') or '') or 'wisconsin' not in t:
            continue
        (OUT / f"poly_evento_{ev.get('slug')[:100]}.json").write_text(json.dumps(ev))
        for m in ev.get('markets', []) or []:
            toks = m.get('clobTokenIds')
            toks = json.loads(toks) if isinstance(toks, str) else toks
            if toks and m.get('id') not in vistos:
                vistos.add(m.get('id'))
                js(f'https://clob.polymarket.com/prices-history?market={toks[0]}&interval=max&fidelity=1440', f"poly_hist_{m.get('id')}.json")
for slug in ('wisconsin-governor-winner-2026', 'wisconsin-governor-margin-of-victory-2026', 'wisconsin-governor-election-winner',
             'wisconsin-governor-election-winner-2026'):
    js(f'{G}/events?slug={slug}', f'poly_slug_{slug}.json')

# Voto anticipado y otros
CV = 'https://civicapi.org/api/v2/early-vote'
for c in ('capabilities', 'returned', 'requested', 'inperson', 'returned/demographics?by=party'):
    get(f'{CV}/WI/{c}', f"civic_WI_{c.replace('/', '_').replace('?', '_').replace('=', '_')}.json")
get('https://www.onpointpolitics.us/api/polls/wi-gov-2026', 'onpoint_wi_gov.json')
get('https://onpointpolitics.us/polls/wi/governor', 'onpoint_wi_gov.html')
get('https://poliagg.com/race/us-governor-2026-wi/', 'poliagg_wi_gob.html')
get('https://elections.wi.gov/statistics-data/absentee-ballot-reports', 'wec_ausente.html')
get('https://elections.wi.gov/statistics-data/voter-registration-statistics', 'wec_registro.html')
get('https://law.marquette.edu/poll/', 'marquette_poll.html')
get('https://www.activote.net/polls/2026/wi-governor/', 'activote_wi.html')

(OUT / '_log.txt').write_text('\n'.join(log))
print(sum(x.startswith('OK') for x in log), 'OK', sum(x.startswith('ERR') for x in log), 'ERR')
