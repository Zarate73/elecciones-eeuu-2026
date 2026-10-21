"""Captura cruda de fuentes para Arizona (corre en GitHub Actions; guarda en crudo/)."""
import json, time, urllib.parse, urllib.request
from pathlib import Path

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36'
OUT = Path('crudo'); OUT.mkdir(exist_ok=True)
log = []

def get(url, nombre=None, binario=False):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=40)
        b = r.read()
        if nombre:
            (OUT / nombre).write_bytes(b)
        log.append(f'OK  {r.status} {len(b):>8} {url}')
        return b if binario else b.decode('utf-8', 'replace')
    except Exception as e:
        log.append(f'ERR {type(e).__name__}: {e} {url}')
        return None

def js(url, nombre=None):
    t = get(url, nombre)
    try:
        return json.loads(t) if t else None
    except Exception:
        return None

# --- encuestas
get('https://en.wikipedia.org/w/api.php?action=parse&page=2026_Arizona_gubernatorial_election&prop=text&format=json&formatversion=2&redirects=1', 'wiki_az_gob.json')
get('https://www.270towin.com/2026-governor-polls/arizona', 't270_az_gob.html')
get('https://en.wikipedia.org/w/api.php?action=parse&page=2022_Arizona_gubernatorial_election&prop=text&format=json&formatversion=2&redirects=1', 'wiki_az_gob2022.json')
get('https://en.wikipedia.org/w/api.php?action=parse&page=2018_Arizona_gubernatorial_election&prop=text&format=json&formatversion=2&redirects=1', 'wiki_az_gob2018.json')
get('https://en.wikipedia.org/w/api.php?action=parse&page=2024_United_States_presidential_election_in_Arizona&prop=text&format=json&formatversion=2&redirects=1', 'wiki_az_pres2024.json')
get('https://en.wikipedia.org/w/api.php?action=parse&page=2024_United_States_Senate_election_in_Arizona&prop=text&format=json&formatversion=2&redirects=1', 'wiki_az_sen2024.json')

# --- Kalshi (actual + históricos)
K = 'https://api.elections.kalshi.com/trade-api/v2'
fin = int(time.time())
def mercados(ev):
    e = js(f'{K}/events/{ev}?with_nested_markets=true', f'kalshi_evento_{ev}.json')
    ms = ((e or {}).get('event') or {}).get('markets') or (e or {}).get('markets') or []
    if not ms:
        h = js(f'{K}/historical/markets?event_ticker={ev}&limit=50', f'kalshi_histmk_{ev}.json')
        ms = (h or {}).get('markets') or []
    return ms
for ev, dias in (('GOVPARTYAZ-26', 700), ('PRESPARTYAZ-24', 1100), ('SENATEAZ-24', 1100), ('GOVPARTYAZ-22', 1600)):
    serie = ev.split('-')[0]
    for m in mercados(ev):
        t = m['ticker']
        for base in (f'{K}/series/{serie}/markets/{t}/candlesticks', f'{K}/historical/markets/{t}/candlesticks'):
            r = js(f'{base}?start_ts={fin - dias*86400}&end_ts={fin}&period_interval=1440', f'kalshi_velas_{t}.json')
            if r and r.get('candlesticks'):
                break

# --- Polymarket
G = 'https://gamma-api.polymarket.com'
for q in ('arizona governor', 'arizona gubernatorial', 'arizona presidential', 'arizona senate'):
    js(f'{G}/public-search?q={urllib.parse.quote(q)}&limit_per_type=20&events_status=all', f"poly_busqueda_{q.replace(' ', '_')}.json")
for slug in ('arizona-governor-election-2026', 'arizona-gubernatorial-election-2026', 'arizona-governor-election',
             'arizona-presidential-election-winner', 'arizona-us-senate-election-winner', 'arizona-governor-election-2022'):
    js(f'{G}/events?slug={slug}', f'poly_evento_{slug}.json')
# historial de precios de todos los mercados encontrados
vistos = set()
for p in OUT.glob('poly_*.json'):
    try:
        d = json.loads(p.read_text())
    except Exception:
        continue
    evs = d.get('events', []) if isinstance(d, dict) else d
    for ev in evs or []:
        titulo = (ev.get('title') or '').lower()
        if 'arizona' not in titulo:
            continue
        for m in ev.get('markets', []):
            toks = m.get('clobTokenIds')
            toks = json.loads(toks) if isinstance(toks, str) else toks
            if not toks or m.get('id') in vistos:
                continue
            vistos.add(m.get('id'))
            js(f'https://clob.polymarket.com/prices-history?market={toks[0]}&interval=max&fidelity=1440', f"poly_hist_{m.get('id')}.json")
            (OUT / f"poly_meta_{m.get('id')}.json").write_text(json.dumps({'evento': ev.get('title'), 'slug': ev.get('slug'),
                'pregunta': m.get('question'), 'outcomes': m.get('outcomes'), 'token_si': toks[0], 'cierre': m.get('endDate'),
                'volumen': m.get('volume')}, ensure_ascii=False))

# --- voto anticipado y otros pronósticos
for d in ('ARIZONA%20STATEWIDE', 'ARIZONA', 'MARICOPA'):
    js(f'https://abev.civiq.vote/api/historical-elections/{d}', f'civiq_hist_{d}.json')
    js(f'https://abev.civiq.vote/api/ballot-returns/{d}', f'civiq_returns_{d}.json')
get('https://abev.civiq.vote/', 'civiq_tablero.html')
get('https://www.fiftyplusone.news/', 'fiftyplusone_inicio.html')
get('https://blog.fiftyplusone.news/p/2026-forecast-methodology', 'fiftyplusone_metodologia.html')
get('https://votes.decisiondeskhq.com/forecast/2026/governor', 'ddhq_gob.html')
get('https://www.racetothewh.com/governor/arizona26', 'rtwh_az.html')
(OUT / '_log.txt').write_text('\n'.join(log))
print('\n'.join(log))
