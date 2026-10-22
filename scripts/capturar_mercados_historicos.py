"""Captura cruda para estimar el peso de los mercados (corre en GitHub Actions; guarda en crudo/).

- Kalshi 2024: eventos PRESPARTY{ST}-24, SENATE{ST}-24, GOVPARTY{ST}-24 y sus velas diarias (oct-nov 2024).
- Polymarket 2024 y 2022: búsqueda por estado y cargo, eventos y precios diarios de cada mercado.
- Wikipedia 2024: páginas de cada contienda (encuestas y resultados).
"""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36'
OUT = Path('crudo')
for sub in ('kalshi', 'poly', 'wiki'):
    (OUT / sub).mkdir(parents=True, exist_ok=True)
log = []

NOMBRES = {'AZ': 'Arizona', 'GA': 'Georgia', 'MI': 'Michigan', 'NV': 'Nevada', 'NC': 'North Carolina',
           'PA': 'Pennsylvania', 'WI': 'Wisconsin', 'FL': 'Florida', 'TX': 'Texas', 'OH': 'Ohio', 'MN': 'Minnesota',
           'NH': 'New Hampshire', 'VA': 'Virginia', 'IA': 'Iowa', 'NM': 'New Mexico', 'ME': 'Maine', 'CO': 'Colorado',
           'NY': 'New York', 'NJ': 'New Jersey', 'MO': 'Missouri', 'MT': 'Montana', 'SC': 'South Carolina',
           'MD': 'Maryland', 'WA': 'Washington', 'IN': 'Indiana', 'OR': 'Oregon', 'KS': 'Kansas', 'OK': 'Oklahoma',
           'CT': 'Connecticut', 'UT': 'Utah', 'IL': 'Illinois', 'CA': 'California', 'AK': 'Alaska', 'NE': 'Nebraska'}
PRES24 = ['AZ', 'GA', 'MI', 'NV', 'NC', 'PA', 'WI', 'FL', 'TX', 'OH', 'MN', 'NH', 'VA', 'IA', 'NM', 'ME', 'CO',
          'NY', 'NJ', 'MO', 'MT', 'SC']
SEN24 = ['AZ', 'MI', 'NV', 'PA', 'WI', 'OH', 'MT', 'TX', 'FL', 'MD', 'MN', 'NM', 'VA', 'NJ', 'NY', 'MO', 'WA']
GOB24 = ['NC', 'NH', 'WA', 'IN', 'MO', 'MT']
SEN22 = ['AZ', 'GA', 'NV', 'PA', 'WI', 'NH', 'OH', 'NC', 'FL', 'CO', 'WA', 'UT', 'MO', 'OK', 'IA', 'CT', 'NY']
GOB22 = ['AZ', 'GA', 'NV', 'PA', 'WI', 'MI', 'MN', 'NY', 'OR', 'KS', 'TX', 'FL', 'OH', 'NH', 'CO', 'NM', 'OK']


def get(url, nombre=None):
    for intento in range(3):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=40)
            b = r.read()
            if nombre:
                (OUT / nombre).write_bytes(b)
            log.append(f'OK  {r.status} {len(b):>8} {url}')
            return b.decode('utf-8', 'replace')
        except Exception as e:                       # noqa: BLE001
            err = e
            if '404' in str(e):
                break
            time.sleep(2 + 3 * intento)
    log.append(f'ERR {type(err).__name__}: {err} {url}')
    return None


def js(url, nombre=None):
    t = get(url, nombre)
    try:
        return json.loads(t) if t else None
    except Exception:                                # noqa: BLE001
        return None


# ------------------------------------------------------------------------------------ Kalshi 2024
K = 'https://api.elections.kalshi.com/trade-api/v2'
INI, FIN = 1727740800, 1730937600                    # 2024-10-01 .. 2024-11-07 UTC
eventos = [f'PRESPARTY{s}-24' for s in PRES24] + [f'SENATE{s}-24' for s in SEN24] + [f'GOVPARTY{s}-24' for s in GOB24]
for ev in eventos:
    e = js(f'{K}/events/{ev}?with_nested_markets=true', f'kalshi/evento_{ev}.json')
    ms = ((e or {}).get('event') or {}).get('markets') or (e or {}).get('markets') or []
    if not ms:
        h = js(f'{K}/historical/markets?event_ticker={ev}&limit=50', f'kalshi/histmk_{ev}.json')
        ms = (h or {}).get('markets') or []
    serie = ev.split('-')[0]
    for m in ms:
        t = m['ticker']
        for base in (f'{K}/series/{serie}/markets/{t}/candlesticks', f'{K}/historical/markets/{t}/candlesticks'):
            r = js(f'{base}?start_ts={INI}&end_ts={FIN}&period_interval=1440', f'kalshi/velas_{t}.json')
            if r and r.get('candlesticks'):
                break
        time.sleep(0.2)

# ------------------------------------------------------------------------------------ Polymarket
G = 'https://gamma-api.polymarket.com'
consultas = []
for s in PRES24:
    consultas.append(f'{NOMBRES[s]} presidential election')
for s in SEN24 + SEN22:
    consultas.append(f'{NOMBRES[s]} senate')
for s in GOB24 + GOB22:
    consultas.append(f'{NOMBRES[s]} governor')
vistos_ev, vistos_mk = set(), set()
for q in sorted(set(consultas)):
    d = js(f'{G}/public-search?q={urllib.parse.quote(q)}&limit_per_type=30&events_status=all')
    for ev in (d or {}).get('events', []) or []:
        slug = ev.get('slug') or ''
        titulo = (ev.get('title') or '').lower()
        fin = str(ev.get('endDate') or '')
        if slug in vistos_ev or not (fin.startswith('2022-11') or fin.startswith('2024-11') or '2022' in titulo or '2024' in titulo):
            continue
        vistos_ev.add(slug)
        (OUT / 'poly' / f'evento_{slug[:120]}.json').write_text(json.dumps(ev), encoding='utf-8')
        for m in ev.get('markets', []) or []:
            toks = m.get('clobTokenIds')
            toks = json.loads(toks) if isinstance(toks, str) else toks
            if not toks or m.get('id') in vistos_mk:
                continue
            vistos_mk.add(m.get('id'))
            js(f'https://clob.polymarket.com/prices-history?market={toks[0]}&interval=max&fidelity=1440',
               f"poly/hist_{m.get('id')}.json")
            time.sleep(0.15)

# ------------------------------------------------------------------------------------ Wikipedia 2024
W = 'https://en.wikipedia.org/w/api.php?action=parse&prop=text&format=json&formatversion=2&redirects=1&page='
paginas = ([f'2024 United States presidential election in {NOMBRES[s]}' for s in PRES24]
           + [f'2024 United States Senate election in {NOMBRES[s]}' for s in SEN24]
           + [f'2024 {NOMBRES[s]} gubernatorial election' for s in GOB24])
for p in paginas:
    get(W + urllib.parse.quote(p.replace(' ', '_')), f"wiki/{p.replace(' ', '_')}.json")
    time.sleep(0.3)

(OUT / '_log.txt').write_text('\n'.join(log), encoding='utf-8')
print(f'{sum(1 for x in log if x.startswith("OK"))} OK · {sum(1 for x in log if x.startswith("ERR"))} ERR')
