"""Captura cruda de On Point Politics y civicAPI (corre en GitHub Actions; guarda en crudo/).
Descubre endpoints /api/ en el HTML y en los bundles JS de cada sitio y los descarga."""
import json, re, urllib.parse, urllib.request
from pathlib import Path

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36'
OUT = Path('crudo'); OUT.mkdir(exist_ok=True)
log = []

def nombre_de(url):
    return re.sub(r'[^A-Za-z0-9._-]+', '_', url.split('://', 1)[1])[:150]

def get(url, guardar=True):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': '*/*'}), timeout=40)
        b = r.read()
        if guardar:
            (OUT / nombre_de(url)).write_bytes(b)
        log.append(f'OK  {r.status} {len(b):>8} {r.headers.get("content-type", "")[:30]:30} {url}')
        return b.decode('utf-8', 'replace')
    except Exception as e:
        log.append(f'ERR {type(e).__name__}: {str(e)[:80]} {url}')
        return None

def descubrir(base, paginas, max_js=40):
    textos, js = [], set()
    for p in paginas:
        t = get(base + p)
        if t:
            textos.append(t)
            js |= {urllib.parse.urljoin(base + p, s) for s in re.findall(r'src="([^"]+\.js[^"]*)"', t)}
    for u in sorted(js)[:max_js]:
        t = get(u, guardar='civicapi' in u)
        if t:
            textos.append(t)
    rutas = set()
    for t in textos:
        rutas |= set(re.findall(r'["\'`](/api/[A-Za-z0-9_\-/.${}?=&]+)', t))
        rutas |= set(re.findall(r'(https?://[A-Za-z0-9.\-]*(?:civicapi|onpointpolitics)[A-Za-z0-9.\-]*/[A-Za-z0-9_\-/.?=&]*api[A-Za-z0-9_\-/.?=&]*)', t))
    (OUT / f'rutas_{nombre_de(base)}.txt').write_text('\n'.join(sorted(rutas)))
    return rutas

# --- On Point Politics
OP = 'https://www.onpointpolitics.us'
for p in ('/api/polls/az-gov-2026', '/api/polls/ga-gov-2026', '/api/polls/ca-gov-2026', '/api/polls/generic-ballot',
          '/api/polls/approval', '/api/forecast/az/governor', '/api/forecast/governor', '/api/forecast',
          '/api/early-vote', '/api/early-vote/az'):
    get(OP + p)
rutas = descubrir(OP, ['/', '/forecast', '/forecast/az/governor', '/polls/az/governor', '/forecast/methodology',
                       '/maps/early-vote', '/maps/party-registration', '/on-point-polling', '/on-point-polling/polls'])
for r in sorted(rutas):
    if r.startswith('/api/') and '$' not in r and '{' not in r:
        get(OP + r)

# --- civicAPI
CV = 'https://civicapi.org'
rutas_c = descubrir(CV, ['/', '/early-vote/', '/early-vote/az', '/early-vote/arizona'])
for r in sorted(rutas_c):
    u = r if r.startswith('http') else CV + r
    if '$' not in u and '{' not in u:
        get(u)
for g in ('/api/v2/early-vote/US/AZ/', '/api/v2/early-vote/US/AZ', '/api/v2/early-vote/US/?state=AZ',
          '/api/v2/early-vote/US/?state=AZ&year=2026', '/api/v2/early-vote/US/?year=2026', '/api/v2/early-vote/US/2026/',
          '/api/v2/early-vote/US/2026/AZ', '/api/v2/early-vote/historical/?state=AZ',
          '/api/v2/early-vote/historical/US/AZ', '/api/v2/early-vote/historical/?country=US&state=AZ',
          '/api/v2/early-vote/US/GA/', '/api/v2/early-vote/US/CA/'):
    get(CV + g)

(OUT / 'log.txt').write_text('\n'.join(log))
print('\n'.join(log))
