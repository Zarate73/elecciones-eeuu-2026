"""Diagnóstico: el cliente red.py de nc_pronostico (UA de Wikimedia + Retry-After) contra la API de Wikipedia, en
corridas seguidas como las de un notebook (guarda en crudo/)."""
import logging, subprocess, sys, time
from pathlib import Path
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'requests'], check=True)
sys.path.insert(0, str(Path('north_carolina/produccion').resolve()))
from nc_pronostico import red  # noqa: E402

OUT = Path('crudo'); OUT.mkdir(exist_ok=True)
log = []
logging.basicConfig(level=logging.WARNING, handlers=[logging.FileHandler(OUT / 'avisos.txt'), logging.StreamHandler()])
P = {'action': 'parse', 'page': '2026_United_States_Senate_election_in_North_Carolina', 'prop': 'text', 'format': 'json',
     'formatversion': 2, 'redirects': 1}
for i in range(6):
    t0 = time.time()
    try:
        js = red.get_json('https://en.wikipedia.org/w/api.php', params=P, timeout=30)
        log.append(f'corrida {i}: OK {len(js["parse"]["text"])} en {time.time() - t0:.1f} s')
    except Exception as e:  # noqa: BLE001
        log.append(f'corrida {i}: ERROR {e} en {time.time() - t0:.1f} s')
    time.sleep(5)
(OUT / '_log.txt').write_text('\n'.join(log))
print('\n'.join(log))
