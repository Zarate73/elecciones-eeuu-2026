"""Captura cruda de fuentes de Texas (corre en GitHub Actions; guarda en crudo/)."""
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
for p in ('2026_Texas_gubernatorial_election', '2022_Texas_gubernatorial_election', '2018_Texas_gubernatorial_election',
          '2026_United_States_Senate_election_in_Texas', '2024_United_States_Senate_election_in_Texas',
          '2020_United_States_Senate_election_in_Texas', '2018_United_States_Senate_election_in_Texas',
          '2024_United_States_presidential_election_in_Texas', '2020_United_States_presidential_election_in_Texas'):
    get(W + p, f'wiki_{p}.json'); time.sleep(2)
get('https://www.270towin.com/2026-governor-polls/texas', 't270_tx_gob.html')

# Kalshi
K = 'https://api.elections.kalshi.com/trade-api/v2'
fin = int(time.time())
for ev in ('GOVPARTYTX-26',):
    e = js(f'{K}/events/{ev}?with_nested_markets=true', f'kalshi_evento_{ev}.json')
    ms = ((e or {}).get('event') or {}).get('markets') or (e or {}).get('markets') or []
    serie = ev.split('-')[0]
    for m in ms:
        t = m['ticker']
        js(f'{K}/series/{serie}/markets/{t}/candlesticks?start_ts={fin - 400 * 86400}&end_ts={fin}&period_interval=1440',
           f'kalshi_velas_{t}.json')
js(f'{K}/markets?event_ticker=GOVPARTYTX-26', 'kalshi_markets_GOVPARTYTX-26.json')
js(f'{K}/events?series_ticker=GOVMARGINTX&limit=20', 'kalshi_margen_series.json')
js(f'{K}/events?series_ticker=KXGOVTX&limit=20', 'kalshi_kxgovme.json')

# Polymarket
G = 'https://gamma-api.polymarket.com'
vistos = set()
for q in ('texas governor', 'texas gubernatorial', 'abbott hinojosa'):
    d = js(f'{G}/public-search?q={urllib.parse.quote(q)}&limit_per_type=30&events_status=all', f"poly_busqueda_{q.replace(' ', '_')}.json")
    for ev in (d or {}).get('events', []) or []:
        if '2026' not in (ev.get('endDate') or '') or 'texas' not in (ev.get('title') or '').lower():
            continue
        (OUT / f"poly_evento_{ev.get('slug')[:100]}.json").write_text(json.dumps(ev))
        for m in ev.get('markets', []) or []:
            toks = m.get('clobTokenIds')
            toks = json.loads(toks) if isinstance(toks, str) else toks
            if toks and m.get('id') not in vistos:
                vistos.add(m.get('id'))
                js(f'https://clob.polymarket.com/prices-history?market={toks[0]}&interval=max&fidelity=1440', f"poly_hist_{m.get('id')}.json")
for slug in ('texas-governor-winner-2026', 'texas-governor-margin-of-victory-2026', 'texas-governor-election-winner-2026'):
    js(f'{G}/events?slug={slug}', f'poly_slug_{slug}.json')

# Voto anticipado (ausente), registro y otros agregadores
CV = 'https://civicapi.org/api/v2/early-vote'
for c in ('capabilities', 'returned', 'requested', 'inperson', 'returned/demographics?by=party', 'inperson/demographics?by=party'):
    get(f'{CV}/TX/{c}', f"civic_TX_{c.replace('/', '_').replace('?', '_').replace('=', '_')}.json")
get('https://earlyvoting.texas-election.com/Elections/getElectionDetails.do', 'txsos_voto_anticipado.html')
get('https://www.sos.state.tx.us/elections/historical/70-92.shtml', 'txsos_registro.html')
get('https://www.onpointpolitics.us/api/polls/tx-gov-2026', 'onpoint_tx_gov.json')
get('https://civicapi.org/api/v2/forecast/governor/2026/civicapi', 'civic_forecast_gob.json')
get('https://poliagg.com/race/us-governor-2026-tx/', 'poliagg_tx_gob.html')
get('https://votes.decisiondeskhq.com/polls/general-ballot-test/2026-tx-governor/texas', 'ddhq_tx_gob.html')

(OUT / '_log.txt').write_text('\n'.join(log))
print(sum(x.startswith('OK') for x in log), 'OK', sum(x.startswith('ERR') for x in log), 'ERR')
