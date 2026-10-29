"""Captura de D.C., parte 4: informes RCV detallados (CSV ronda por ronda) de la primaria certificada (17-jul-2026) y la
visualización de RCVis de la alcaldía. Usa el contexto de Chromium (la DCBOE está detrás de Cloudflare)."""
import asyncio, json, re, subprocess, sys
from pathlib import Path

subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'playwright'], check=True)
subprocess.run([sys.executable, '-m', 'playwright', 'install', '--with-deps', 'chromium'], check=True)
from playwright.async_api import async_playwright  # noqa: E402

OUT = Path('crudo'); OUT.mkdir(exist_ok=True)
log = []
B = 'https://electionresults.dcboe.org'


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context()
        pg = await ctx.new_page()
        await pg.goto(f'{B}/election_results/2026-Primary-Election', wait_until='networkidle', timeout=90000)
        r = await pg.request.get(f'{B}/RCV/GetContestStats/2026-Primary-Election?displayName=Certified%20RCV%20Results%20-%20Published%20July%2017%2C%202026')
        stats = json.loads(await r.text())
        (OUT / 'rcv_stats.json').write_text(json.dumps(stats, indent=1))
        for c in stats:
            nom = re.sub(r'[^A-Za-z0-9]+', '_', c['OfficeName'])[:60]
            for intento in range(2):
                r = await pg.request.get(B + c['DetailedReportUrl'])
                body = await r.body()
                if r.status == 200 and body[:15].lower() != b'<!doctype html>':
                    break
                await pg.wait_for_timeout(3000)
            (OUT / f'rcv_{c["ContestNumber"]}_{nom}.csv').write_bytes(body)
            log.append(f'{r.status} {len(body):>8} {c["OfficeName"]} {c["DetailedReportUrl"]}')
            if 'MAYOR' in c['OfficeName']:
                v = c['VisualizationSourceURL']
                for u in (v, v + '/', v.replace('/v/', '/vo/'), v + '?format=json'):
                    try:
                        await pg.goto(u, wait_until='networkidle', timeout=60000)
                        (OUT / f'rcvis_{re.sub(r"[^A-Za-z0-9]+", "_", u)[-40:]}.txt').write_text(await pg.inner_text('body'))
                        (OUT / f'rcvis_{re.sub(r"[^A-Za-z0-9]+", "_", u)[-40:]}.html').write_text(await pg.content())
                        log.append(f'RCVIS {u} ok')
                    except Exception as e:                  # noqa: BLE001
                        log.append(f'RCVIS {u} ERR {str(e)[:80]}')
        await b.close()

asyncio.run(main())
(OUT / '_log.txt').write_text('\n'.join(log))
print('\n'.join(log))
