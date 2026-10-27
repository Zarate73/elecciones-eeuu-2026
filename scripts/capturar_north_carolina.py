"""Captura cruda de fuentes de North Carolina (corre en GitHub Actions; guarda en crudo/)."""
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
for p in ('2026_United_States_Senate_election_in_North_Carolina',
          '2022_United_States_Senate_election_in_North_Carolina', '2020_United_States_Senate_election_in_North_Carolina',
          '2016_United_States_Senate_election_in_North_Carolina', '2014_United_States_Senate_election_in_North_Carolina',
          '2010_United_States_Senate_election_in_North_Carolina', '2008_United_States_Senate_election_in_North_Carolina',
          '2024_North_Carolina_gubernatorial_election', '2020_North_Carolina_gubernatorial_election',
          '2016_North_Carolina_gubernatorial_election',
          '2024_United_States_presidential_election_in_North_Carolina',
          '2020_United_States_presidential_election_in_North_Carolina',
          '2026_North_Carolina_elections', 'Michael_Whatley', 'Roy_Cooper'):
    get(W + p, f'wiki_{p}.json'); time.sleep(2)
get('https://www.270towin.com/2026-senate-polls/north-carolina', 't270_nc_sen.html')
get('https://www.270towin.com/2024-governor-polls/north-carolina', 't270_nc_gob24.html')

# Kalshi: buscar el evento del Senado de NC
K = 'https://api.elections.kalshi.com/trade-api/v2'
fin = int(time.time())
cand = set()
for serie in ('SENATENC', 'KXSENATENC', 'SENNC', 'SENATEMARGINNC', 'KXSENATENCMARGIN', 'POWER', 'SENATECTRL'):
    d = js(f'{K}/events?series_ticker={serie}&limit=20&with_nested_markets=true', f'kalshi_serie_{serie}.json')
    for e in (d or {}).get('events', []) or []:
        cand.add((serie, e.get('event_ticker')))
for ev in ('SENATENC-26',):
    cand.add(('SENATENC', ev))
for serie, ev in sorted(cand):
    if not ev:
        continue
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
for q in ('north carolina senate', 'cooper whatley', 'whatley', 'roy cooper'):
    d = js(f'{G}/public-search?q={urllib.parse.quote(q)}&limit_per_type=30&events_status=all', f"poly_busqueda_{q.replace(' ', '_')}.json")
    for ev in (d or {}).get('events', []) or []:
        t = (ev.get('title') or '').lower()
        if '2026' not in (ev.get('endDate') or '') or not ('north carolina' in t or 'cooper' in t or 'whatley' in t):
            continue
        (OUT / f"poly_evento_{ev.get('slug')[:100]}.json").write_text(json.dumps(ev))
        for m in ev.get('markets', []) or []:
            toks = m.get('clobTokenIds')
            toks = json.loads(toks) if isinstance(toks, str) else toks
            if toks and m.get('id') not in vistos:
                vistos.add(m.get('id'))
                js(f'https://clob.polymarket.com/prices-history?market={toks[0]}&interval=max&fidelity=1440', f"poly_hist_{m.get('id')}.json")
for slug in ('north-carolina-senate-election-winner', 'north-carolina-senate-election-margin-of-victory',
             'north-carolina-senate-margin-of-victory-2026', 'north-carolina-senate-election-winner-2026'):
    js(f'{G}/events?slug={slug}', f'poly_slug_{slug}.json')

# Voto anticipado, registro y otros agregadores
CV = 'https://civicapi.org/api/v2/early-vote'
for c in ('capabilities', 'returned', 'requested', 'inperson', 'returned/demographics?by=party',
          'inperson/demographics?by=party', 'requested/demographics?by=party'):
    get(f'{CV}/NC/{c}', f"civic_NC_{c.replace('/', '_').replace('?', '_').replace('=', '_')}.json")
get('https://www.onpointpolitics.us/api/polls/nc-sen-2026', 'onpoint_nc_sen.json')
get('https://onpointpolitics.us/polls/nc/senate', 'onpoint_nc_sen.html')
get('https://civicapi.org/api/v2/forecast/senate/2026/civicapi', 'civic_forecast_sen.json')
get('https://poliagg.com/race/us-senate-2026-nc/', 'poliagg_nc_sen.html')
get('https://www.ncsbe.gov/results-data/voter-registration-data', 'ncsbe_registro.html')
get('https://vt.ncsbe.gov/RegStat/', 'ncsbe_regstat.html')
get('https://vt.ncsbe.gov/RegStat/Results/?date=10%2F25%2F2026', 'ncsbe_regstat_20261025.html')
get('https://www.ncsbe.gov/results-data/absentee-data', 'ncsbe_ausente.html')
get('https://www.ncsbe.gov/news/press-releases', 'ncsbe_prensa.html')
get('https://dl.ncsbe.gov/?prefix=ENRS/2026_11_03/', 'ncsbe_dl_enrs.html')
get('https://s3.amazonaws.com/dl.ncsbe.gov?list-type=2&prefix=ENRS/2026_11_03/', 'ncsbe_s3_enrs.xml')
get('https://s3.amazonaws.com/dl.ncsbe.gov?list-type=2&prefix=Elections/2026/', 'ncsbe_s3_elec2026.xml')
get('https://www.activote.net/polls/2026/nc-senate/', 'activote_nc.html')
get('https://www.elon.edu/u/elon-poll/', 'elon_poll.html')
get('https://www.highpoint.edu/poll/', 'hpu_poll.html')
get('https://catawba.edu/the-catawba-college-ycg-polls/', 'catawba_poll.html')
get('https://news.ecu.edu/category/ecu-poll/', 'ecu_poll.html')
get('https://www.carolinajournal.com/tag/carolina-journal-poll/', 'cj_poll.html')
get('https://www.oldnorthstatepolitics.com/', 'onsp.html')

(OUT / '_log.txt').write_text('\n'.join(log))
print(sum(x.startswith('OK') for x in log), 'OK', sum(x.startswith('ERR') for x in log), 'ERR')
