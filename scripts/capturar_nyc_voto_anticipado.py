"""Diagnóstico: ¿se puede leer desde GitHub Actions el voto anticipado de la Junta Electoral de NYC? (guarda en crudo/)."""
import time, urllib.request
from pathlib import Path

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36'
OUT = Path('crudo'); OUT.mkdir(exist_ok=True)
log = []
for url, nom in (('https://www.vote.nyc/page/early-voting-check-ins', 'nyc_ev.html'),
                 ('https://vote.nyc/page/early-voting-check-ins', 'nyc_ev_sin_www.html'),
                 ('https://www.elections.ny.gov/node/411', 'nysboe_ev.html')):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'text/html,*/*'}), timeout=45)
        b = r.read(); (OUT / nom).write_bytes(b); log.append(f'OK  {r.status} {len(b):>8} {url}')
    except Exception as e:                                   # noqa: BLE001
        log.append(f'ERR {type(e).__name__}: {str(e)[:90]} {url}')
    time.sleep(2)
(OUT / '_log.txt').write_text('\n'.join(log)); print('\n'.join(log))
