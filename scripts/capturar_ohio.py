"""Captura cruda de fuentes de Ohio (corre en GitHub Actions; guarda en crudo/)."""
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
for p in ('2026_Ohio_gubernatorial_election', '2022_Ohio_gubernatorial_election', '2018_Ohio_gubernatorial_election',
          '2026_United_States_Senate_special_election_in_Ohio', '2024_United_States_Senate_election_in_Ohio',
          '2022_United_States_Senate_election_in_Ohio', '2024_United_States_presidential_election_in_Ohio',
          '2020_United_States_presidential_election_in_Ohio', '2023_Ohio_Issue_1_(November)'):
    get(W + p, f'wiki_{p}.json'); time.sleep(2)
get('https://www.270towin.com/2026-governor-polls/ohio', 't270_oh_gob.html')
get('https://www.270towin.com/2026-senate-polls/ohio', 't270_oh_sen.html')

# Kalshi
K = 'https://api.elections.kalshi.com/trade-api/v2'
fin = int(time.time())
for ev in ('GOVPARTYOH-26', 'SENATEOH-26'):
    e = js(f'{K}/events/{ev}?with_nested_markets=true', f'kalshi_evento_{ev}.json')
    ms = ((e or {}).get('event') or {}).get('markets') or (e or {}).get('markets') or []
    serie = ev.split('-')[0]
    for m in ms:
        t = m['ticker']
        js(f'{K}/series/{serie}/markets/{t}/candlesticks?start_ts={fin - 400 * 86400}&end_ts={fin}&period_interval=1440',
           f'kalshi_velas_{t}.json')
js(f'{K}/markets?event_ticker=GOVPARTYOH-26', 'kalshi_markets_GOVPARTYOH-26.json')
js(f'{K}/events?series_ticker=GOVMARGINOH&limit=20', 'kalshi_margen_series.json')
js(f'{K}/events?series_ticker=KXGOVOH&limit=20', 'kalshi_kxgovoh.json')
js(f'{K}/events?series_ticker=GOVPARTYOH&limit=20', 'kalshi_series_govpartyoh.json')

# Polymarket
G = 'https://gamma-api.polymarket.com'
vistos = set()
for q in ('ohio governor', 'ohio gubernatorial', 'acton ramaswamy', 'ramaswamy'):
    d = js(f'{G}/public-search?q={urllib.parse.quote(q)}&limit_per_type=30&events_status=all', f"poly_busqueda_{q.replace(' ', '_')}.json")
    for ev in (d or {}).get('events', []) or []:
        if '2026' not in (ev.get('endDate') or '') or 'ohio' not in (ev.get('title') or '').lower():
            continue
        (OUT / f"poly_evento_{ev.get('slug')[:100]}.json").write_text(json.dumps(ev))
        for m in ev.get('markets', []) or []:
            toks = m.get('clobTokenIds')
            toks = json.loads(toks) if isinstance(toks, str) else toks
            if toks and m.get('id') not in vistos:
                vistos.add(m.get('id'))
                js(f'https://clob.polymarket.com/prices-history?market={toks[0]}&interval=max&fidelity=1440', f"poly_hist_{m.get('id')}.json")
for slug in ('ohio-governor-winner-2026', 'ohio-governor-margin-of-victory-2026', 'ohio-governor-election-winner-2026'):
    js(f'{G}/events?slug={slug}', f'poly_slug_{slug}.json')

# Voto anticipado, registro y otros agregadores
CV = 'https://civicapi.org/api/v2/early-vote'
for c in ('capabilities', 'returned', 'requested', 'inperson', 'returned/demographics?by=party', 'inperson/demographics?by=party'):
    get(f'{CV}/OH/{c}', f"civic_OH_{c.replace('/', '_').replace('?', '_').replace('=', '_')}.json")
get('https://www.onpointpolitics.us/api/polls/oh-gov-2026', 'onpoint_oh_gov.json')
get('https://onpointpolitics.us/polls/oh/governor', 'onpoint_oh_gov.html')
get('https://civicapi.org/api/v2/forecast/governor/2026/civicapi', 'civic_forecast_gob.json')
get('https://poliagg.com/race/us-governor-2026-oh/', 'poliagg_oh_gob.html')
get('https://www.ohiosos.gov/elections/election-results-and-data/', 'ohsos_resultados.html')
get('https://www.ohiosos.gov/elections/election-results-and-data/historical-election-comparisons/voter-turnout-in-general-elections/', 'ohsos_participacion.html')
get('https://www.ohiosos.gov/media-center/press-releases/', 'ohsos_prensa.html')
get('https://www.ohiosos.gov/elections/voters/absentee-voting-data/', 'ohsos_ausente.html')
get('https://www.activote.net/polls/2026/oh-governor/', 'activote_oh.html')
get('https://www.bgsu.edu/news/polling.html', 'bgsu_polling.html')
get('https://pollfinity.com/polls', 'pollfinity_lista.html')

(OUT / '_log.txt').write_text('\n'.join(log))
print(sum(x.startswith('OK') for x in log), 'OK', sum(x.startswith('ERR') for x in log), 'ERR')
