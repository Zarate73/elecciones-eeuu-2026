"""Sondeo de fuentes OFICIALES de resultados preliminares (noche electoral) para los 14 estados.

1) URLs conocidas de elecciones pasadas y su versión 2026 (urllib): ¿responden?, ¿formato?
2) Sitios de resultados que son apps (Playwright): qué peticiones JSON hacen, para descubrir la API.
Guarda todo en crudo/ (una rama propia; no toca main)."""
import asyncio, json, re, subprocess, sys, time, urllib.request
from pathlib import Path

OUT = Path('crudo'); OUT.mkdir(exist_ok=True)
log = []
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36'


def nom(u):
    return re.sub(r'[^A-Za-z0-9._-]+', '_', u.split('://', 1)[1])[:140]


def get(u):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': UA, 'Accept': '*/*'}), timeout=40)
        b = r.read()
        (OUT / ('u_' + nom(u))).write_bytes(b[:3_000_000])
        log.append(f'OK  {r.status} {len(b):>9} {r.headers.get("content-type", "")[:30]:30s} {u}')
    except Exception as e:                                   # noqa: BLE001
        log.append(f'ERR {str(e)[:60]:60s} {u}')


URLS = [
    # North Carolina (NCSBE, JSON por contienda)
    'https://er.ncsbe.gov/enr/20241105/data/results_0.txt', 'https://er.ncsbe.gov/enr/20261103/data/results_0.txt',
    'https://er.ncsbe.gov/enr/20221108/data/results_0.txt',
    # Florida (archivo tab de la noche electoral)
    'https://flelectionfiles.floridados.gov/enightfilespublic/20241105_ElecResultsFL.txt',
    'https://flelectionfiles.floridados.gov/enightfilespublic/20261103_ElecResultsFL.txt',
    'https://flelectionfiles.floridados.gov/enightfilespublic/20221108_ElecResultsFL.txt',
    # California (API del SOS)
    'https://api.sos.ca.gov/returns/governor', 'https://api.sos.ca.gov/returns/president', 'https://api.sos.ca.gov/returns/status',
    'https://api.sos.ca.gov/returns/',
    # Washington D.C. (DCBOE)
    'https://electionresults.dcboe.org/cityWide/getCityWide/2024-General-Election',
    'https://electionresults.dcboe.org/cityWide/getCityWide/2026-General-Election',
    'https://electionresults.dcboe.org/electionResults/getElectionResultsId',
    'https://electionresults.dcboe.org/electionResults/getElectionInfo/2026-General-Election',
    # Georgia / Arizona (Enhanced Voting)
    'https://results.sos.ga.gov/cdn/results/Georgia/export-2024NovGen.json',
    'https://results.sos.ga.gov/cdn/results/Georgia/export-2022NovGen.json',
    'https://results.sos.ga.gov/cdn/results/Georgia/export-2026NovGen.json',
    # Pennsylvania
    'https://www.electionreturns.pa.gov/api/ElectionReturn/GetAllElections',
    # Ohio
    'https://liveresults.ohiosos.gov/', 'https://liveresults.ohiosos.gov/Api/v1/download?filename=Statewide&format=json',
]
for u in URLS:
    get(u); time.sleep(0.5)

subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'playwright'], check=True)
subprocess.run([sys.executable, '-m', 'playwright', 'install', '--with-deps', 'chromium'], check=True)
from playwright.async_api import async_playwright  # noqa: E402

SITIOS = {
    'GA': 'https://results.sos.ga.gov/', 'AZ': 'https://results.arizona.vote/', 'TX': 'https://results.texas-election.com/',
    'TX2': 'https://goelect.txelections.civixapps.com/ivis-enr-ui/races', 'OH': 'https://liveresults.ohiosos.gov/',
    'NV': 'https://silverstateelection.nv.gov/', 'PA': 'https://www.electionreturns.pa.gov/',
    'NY': 'https://nyenr.elections.ny.gov/', 'CA': 'https://electionresults.sos.ca.gov/',
    'DC': 'https://electionresults.dcboe.org/election_results/2026-General-Election',
    'FL': 'https://results.elections.myflorida.com/', 'NC': 'https://er.ncsbe.gov/',
    'IL': 'https://www.elections.il.gov/', 'WI': 'https://elections.wi.gov/elections/election-results',
    'ME': 'https://www.maine.gov/sos/elections-voting/results',
}


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for clave, u in SITIOS.items():
            ctx = await b.new_context(user_agent=UA)
            pg = await ctx.new_page()
            peticiones = []

            async def resp(r, peticiones=peticiones, clave=clave):
                ct = r.headers.get('content-type') or ''
                peticiones.append(f'{r.status} {r.request.resource_type:10s} {ct[:30]:30s} {r.url}')
                if r.request.resource_type in ('xhr', 'fetch') or 'json' in ct:
                    try:
                        body = await r.body()
                        (OUT / f'pw_{clave}_{len(peticiones):03d}_{nom(r.url)[:90]}').write_bytes(body[:2_000_000])
                    except Exception:                        # noqa: BLE001
                        pass
            pg.on('response', lambda r, f=resp: asyncio.ensure_future(f(r)))
            try:
                await pg.goto(u, wait_until='networkidle', timeout=60000)
                await pg.wait_for_timeout(5000)
                (OUT / f'pw_{clave}_texto.txt').write_text((await pg.inner_text('body'))[:20000])
                hrefs = await pg.eval_on_selector_all('a', 'as => as.map(a => a.href + " | " + a.innerText.trim().slice(0,80))')
                (OUT / f'pw_{clave}_enlaces.txt').write_text('\n'.join(hrefs[:400]))
                log.append(f'PW  {clave} {u} -> {pg.url}')
            except Exception as e:                           # noqa: BLE001
                log.append(f'PW  {clave} ERR {str(e)[:80]}')
            (OUT / f'pw_{clave}_peticiones.txt').write_text('\n'.join(peticiones))
            await ctx.close()
        await b.close()

asyncio.run(main())
(OUT / '_log.txt').write_text('\n'.join(log))
print('\n'.join(log))
