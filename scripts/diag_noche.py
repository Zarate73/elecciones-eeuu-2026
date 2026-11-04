"""Diagnóstico de la noche electoral: qué devuelven ahora las fuentes que siguen en cero."""
import json, re, urllib.request
from pathlib import Path
OUT = Path('crudo'); OUT.mkdir(exist_ok=True)
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
log = []
def get(u, nom):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': UA, 'Accept': '*/*'}), timeout=60)
        b = r.read(); (OUT / nom).write_bytes(b[:5_000_000]); log.append(f'OK {r.status} {len(b)} {u}'); return b
    except Exception as e:
        log.append(f'ERR {e} {u}')
for u, n in [('https://flelectionfiles.floridados.gov/enightfilespublic/20261103_ElecResultsFL.txt', 'fl.txt'),
             ('https://results.texas-election.com/static/data/Version.json', 'tx_version.json'),
             ('https://api.sos.ca.gov/returns/governor', 'ca.json'),
             ('https://er.ncsbe.gov/enr/20261103/data/results_0.txt', 'nc.json'),
             ('https://results.sos.ga.gov/results/public/api/jurisdictions/Georgia', 'ga_j.json'),
             ('https://liveresults.ohiosos.gov/Api/v1/Contest/getMarquee', 'oh_marquee.json'),
             ('https://liveresults.ohiosos.gov/Api/v1/Contest/getDefaultingContestName', 'oh_def.json')]:
    get(u, n)
try:
    v = json.load(open(OUT / 'tx_version.json'))['___versionNo']
    get(f'https://results.texas-election.com/static/data/ElectionConstants_{v}.json', 'tx_const.json')
    c = json.load(open(OUT / 'tx_const.json'))
    log.append('TX años: ' + str(sorted(c.get('electionInfo', {}).keys())) + ' current: ' + json.dumps(c.get('currentelectionInfo'))[:400])
except Exception as e:
    log.append(f'TX ERR {e}')
try:
    t = (OUT / 'fl.txt').read_text(errors='replace').splitlines()
    gov = [l for l in t if '\tGOV\t' in l]
    log.append(f'FL lineas {len(t)} gob {len(gov)} suma votos gob ' + str(sum(int(l.split("\t")[14] or 0) for l in gov)))
    log.append('FL ejemplo ' + (gov[0] if gov else ''))
except Exception as e:
    log.append(f'FL ERR {e}')
(OUT / '_log.txt').write_text('\n'.join(log)); print('\n'.join(log))
