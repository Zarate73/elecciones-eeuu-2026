"""Captura de D.C., parte 3: resultados RCV (ronda por ronda) de la primaria del 16-jun-2026 en electionresults.dcboe.org.
La página es una app React: se abre con Chromium (Playwright) y se guardan todas las respuestas JSON/CSV que carga."""
import asyncio, json, re, subprocess, sys
from pathlib import Path

subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'playwright'], check=True)
subprocess.run([sys.executable, '-m', 'playwright', 'install', '--with-deps', 'chromium'], check=True)
from playwright.async_api import async_playwright  # noqa: E402

OUT = Path('crudo'); OUT.mkdir(exist_ok=True)
log = []
URLS = ['https://electionresults.dcboe.org/election_results/2026-Primary-Election',
        'https://electionresults.dcboe.org/election_results/2026-Primary-Election#rcv',
        'https://electionresults.dcboe.org/rcv_results/2026-Primary-Election',
        'https://electionresults.dcboe.org/']


async def main():
    n = 0
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page()

        async def resp(r):
            nonlocal n
            ct = (r.headers.get('content-type') or '')
            if any(k in ct for k in ('json', 'csv', 'text/plain', 'pdf', 'octet')) or re.search(r'\.(json|csv|pdf)', r.url):
                try:
                    body = await r.body()
                except Exception as e:                      # noqa: BLE001
                    log.append(f'ERR body {r.url} {e}'); return
                n += 1
                nom = f'resp_{n:03d}_' + re.sub(r'[^A-Za-z0-9._-]+', '_', r.url.split('://', 1)[1])[:120]
                (OUT / nom).write_bytes(body)
                log.append(f'OK {r.status} {len(body):>8} {ct[:30]} {r.url}')
        pg.on('response', lambda r: asyncio.ensure_future(resp(r)))
        for i, u in enumerate(URLS):
            try:
                await pg.goto(u, wait_until='networkidle', timeout=90000)
                await pg.wait_for_timeout(4000)
                (OUT / f'pagina_{i}.html').write_text(await pg.content())
                (OUT / f'texto_{i}.txt').write_text(await pg.inner_text('body'))
                # enlaces y botones con «RCV», «Round», «Mayor»
                for t in ('Ranked', 'RCV', 'Round', 'Tabulation', 'MAYOR', 'Mayor'):
                    for el in (await pg.query_selector_all(f'text={t}'))[:3]:
                        try:
                            await el.click(timeout=5000); await pg.wait_for_timeout(3000)
                        except Exception:                   # noqa: BLE001
                            pass
                (OUT / f'texto_{i}_tras_clics.txt').write_text(await pg.inner_text('body'))
                await pg.screenshot(path=str(OUT / f'pantalla_{i}.png'), full_page=True)
                hrefs = await pg.eval_on_selector_all('a', 'as => as.map(a => a.href + " | " + a.innerText)')
                (OUT / f'enlaces_{i}.txt').write_text('\n'.join(hrefs))
                log.append(f'PAGINA {u} -> {pg.url}')
            except Exception as e:                          # noqa: BLE001
                log.append(f'ERR pagina {u} {e}')
        await b.close()

asyncio.run(main())
(OUT / '_log.txt').write_text('\n'.join(log))
print('\n'.join(log[-40:]))
