"""Respaldo de Civiq: captura del tablero con Brave/Playwright y lectura del texto.
Solo se usa si la API pública falla (fuentes.civiq_usar_navegador_respaldo)."""
from __future__ import annotations

import json, re, time, unicodedata
from dataclasses import dataclass, asdict, field
from datetime import date, datetime, timedelta
from math import sqrt, tanh
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import logging

from .tipos import FuenteNoDisponible, VotoTemprano

log = logging.getLogger(__name__)

# Se fijan con configurar(cfg)
INICIO_VOTO = date(2026, 10, 5)
DIA_ELECCION = date(2026, 11, 3)
URL_CIVIQ = 'https://abev.civiq.vote/'
SALIDA = Path('salidas/cache')


def configurar(cfg) -> None:
    global INICIO_VOTO, DIA_ELECCION, URL_CIVIQ, SALIDA
    INICIO_VOTO, DIA_ELECCION = cfg.inicio_voto, cfg.dia_eleccion
    URL_CIVIQ, SALIDA = cfg.fuentes.civiq_url_tablero, cfg.dir_cache / 'civiq_navegador'
    SALIDA.mkdir(parents=True, exist_ok=True)



def normalizar_texto(texto: str) -> str:
    texto = unicodedata.normalize('NFKC', texto)
    texto = texto.replace('\xa0', ' ').replace('–', '-').replace('—', '-')
    return re.sub(r'\s+', ' ', texto).strip()


def texto_html(html: str) -> str:
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise FuenteNoDisponible('Instala beautifulsoup4: python -m pip install beautifulsoup4') from exc
    soup = BeautifulSoup(html, 'html.parser')
    for x in soup(['script', 'style', 'noscript', 'svg']):
        x.decompose()
    return normalizar_texto(soup.get_text(' ', strip=True))


def _numero(texto: str) -> int:
    return int(texto.replace(',', '').replace(' ', ''))


def _buscar_entero(sect: str, label: str) -> int:
    # Civiq muestra "195,857 Returned"; se admite tambien "Returned 195,857".
    p = rf'(\d{{1,3}}(?:,\d{{3}})+|\d+)\s+{label}\b'
    match = re.search(p, sect, flags=re.I)
    if not match:
        match = re.search(rf'\b{label}\s+(\d{{1,3}}(?:,\d{{3}})+|\d+)', sect, flags=re.I)
    if not match:
        raise FuenteNoDisponible(f'No se encontro el indicador {label!r} en el tablero')
    return _numero(match.group(1))


def _entre(texto: str, inicio: str, fin: Optional[str] = None, limite: int = 1500) -> str:
    pos = texto.lower().find(inicio.lower())
    if pos < 0:
        raise FuenteNoDisponible(f'Seccion ausente: {inicio}')
    segmento = texto[pos + len(inicio):pos + len(inicio) + limite]
    if fin:
        end = segmento.lower().find(fin.lower())
        if end >= 0:
            segmento = segmento[:end]
    return segmento


def _partido_cifras(seccion: str, partido: str) -> int:
    # "Democrat 46.2% 0.9% turnout 90,481" y variaciones sin turnout.
    exp = rf'\b{re.escape(partido)}(?=\s|$)\s+\d{{1,3}}(?:\.\d+)?\s*%\s+(?:\d{{1,3}}(?:\.\d+)?\s*%\s*turnout\s+)?(\d{{1,3}}(?:,\d{{3}})+|\d+)'
    mat = re.search(exp, seccion, flags=re.I)
    if mat:
        return _numero(mat.group(1))
    # Si la nueva version coloca el conteo antes del porcentaje.
    exp = rf'\b{re.escape(partido)}(?=\s|$)\s+(\d{{1,3}}(?:,\d{{3}})+|\d+)\s+\d{{1,3}}(?:\.\d+)?\s*%'
    mat = re.search(exp, seccion, flags=re.I)
    if mat:
        return _numero(mat.group(1))
    raise FuenteNoDisponible(f'No pude identificar la cifra de {partido} en esta seccion')


def _fecha_actualizacion(texto: str) -> date:
    """Devuelve la fecha de los conteos, no la hora de actualización del sitio.

    Prefiere filas acumuladas verificadas contra el total del encabezado.
    Si no existe una tabla comparable, recurre a la fecha del encabezado.
    """
    cab = _entre(texto, 'Registration and Return Toplines',
                 'Ballot Return Trend', 1200)
    total = _buscar_entero(cab, 'Returned')
    # Se admiten ambas presentaciones de Civiq: Party / Age Date Trends.
    for identificador in ('Party Date Trends', 'Age Date Trends'):
        try:
            tabla = _entre(texto, identificador, limite=12500)
        except FuenteNoDisponible:
            continue
        patron = re.compile(
            r'(?<![\d/])(\d{1,2})/(\d{1,2})\s+'
            r'(\d{1,3}(?:,\d{3})+|\d+)\s+'
            r'\d{1,3}(?:\.\d+)?\s*%')
        for mm, dd, n in patron.findall(tabla):
            try:
                fecha = date(2026, int(mm), int(dd))
                if _numero(n) == total and INICIO_VOTO <= fecha <= DIA_ELECCION:
                    return fecha
            except ValueError:
                continue

    # Cabecera como «CALIFORNIA STATEWIDE · Updated Oct 12, 2026, 9:04 PM PDT»
    month_names = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,
                   'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}
    m = re.search(r'\bUpdated\s*:?\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+'
                  r'(\d{1,2}),?\s*(20\d{2})', texto, re.I)
    if m:
        return date(int(m.group(3)), month_names[m.group(1)[:3].lower()], int(m.group(2)))

    # Cabecera como «Updated: 10/13/2026, 4:04:20 AM».
    m = re.search(r'\bUpdated\s*:?\s*(\d{1,2})/(\d{1,2})/(20\d{2})', texto, re.I)
    if m:
        return date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
    raise FuenteNoDisponible('No se encontro fecha valida de actualizacion o de conteos')

def extraer_historico_mismo_dia(texto: str, fecha: date,
                                  dev_dem: int, dev_rep: int, devueltas: int) -> dict:
    """Lee la tabla pública «Daily party shares of returns» de Civiq.

    Las 8 columnas de tres porcentajes siguen el orden visible del tablero:
    2026 General, 2026 Primary, 2025 Special, 2024 General,
    2024 Primary, 2022 General, 2022 Primary, 2021 Special.
    Si la estructura cambia, se descarta la referencia: nunca se inventa.
    """
    dias = (DIA_ELECCION - fecha).days
    marcador = 'Daily party shares of returns'
    offset = texto.lower().find(marcador.lower())
    if offset < 0 or dias < 0:
        return {}
    # La tabla no excede 90 dias en condiciones normales.
    tabla = texto[offset + len(marcador):offset + len(marcador) + 50000]
    inicio = re.search(r'\bDays to election:\s*' + str(dias) + r'\b', tabla, re.I)
    if not inicio:
        return {}
    resto = tabla[inicio.end():]
    siguiente = re.search(r'\bDays to election:\s*\d+', resto, re.I)
    fila = resto[:siguiente.start() if siguiente else min(900, len(resto))]
    nums = [float(n) for n in re.findall(r'(\d{1,3}(?:\.\d+)?)\s*%', fila)]
    if len(nums) < 24:
        return {}
    nums = nums[:24]
    triples = [nums[i:i+3] for i in range(0, 24, 3)]
    if not all(98.0 <= sum(x) <= 102.0 for x in triples):
        return {}
    if devueltas <= 0:
        return {}
    margen_real = 100*(dev_dem - dev_rep)/devueltas
    margen_tabla = triples[0][0] - triples[0][2]
    if abs(margen_real - margen_tabla) > 1.5:
        return {}
    return {
        'dias_antes_eleccion': dias,
        '2024 General': triples[3][0] - triples[3][2],
        '2022 General': triples[5][0] - triples[5][2],
        'porcentajes_redondeados': True,
        'descripcion': 'Comparacion historica de devoluciones D-R; NO resultados de candidatos',
    }


def _crosstab_partido_edad(texto: str):
    """Reconstruye registro y devoluciones de Civiq a partir de su tabla
    Party × Age, más estable y auditable que las etiquetas de sus gráficas.

    Se comprueba también que las columnas sumen los totales estatales.
    Se trabaja exclusivamente con conteos publicados por la fuente.
    """
    inicio = re.search(r'Crosstabs by Party', texto, flags=re.I)
    if not inicio:
        raise FuenteNoDisponible('No aparece la sección de conteos Crosstabs by Party')
    bloque = texto[inicio.end():inicio.end()+26000]
    cab = re.search(r'Party\s*[×x]\s*Age', bloque, flags=re.I)
    if not cab:
        raise FuenteNoDisponible('No aparece la tabla Party × Age')
    bloque = bloque[cab.end():]
    fin = re.search(r'Party\s*[×x]\s*Gender|Party\s*[×x]\s*Ethnicity|Gender\s*[×x]\s*Age', bloque, flags=re.I)
    if fin:
        bloque = bloque[:fin.start()]
    # Cada columna de edad publica: REG, share, RETURNS, share, turnout.
    patron = re.compile(
        r'(\d{1,3}(?:,\d{3})+|\d+)\s+'
        r'\d{1,3}(?:\.\d+)?\s*%\s+'
        r'(\d{1,3}(?:,\d{3})+|\d+)\s+'
        r'\d{1,3}(?:\.\d+)?\s*%\s+'
        r'\d{1,3}(?:\.\d+)?\s*%', re.I)
    # Limita cada fila al siguiente partido para no consumir números de otra tabla.
    nombres = re.compile(r'(?<!\w)(Democrat|Republican|Other|NPP/Oth)(?!\w)', re.I)
    marcas=list(nombres.finditer(bloque))
    datos={}
    for i,marca in enumerate(marcas):
        clave=marca.group(1).lower()
        clave='otro' if clave.startswith(('other','npp')) else ('dem' if clave=='democrat' else 'rep')
        if clave in datos:
            continue
        tramo=bloque[marca.end():(marcas[i+1].start() if i+1<len(marcas) else len(bloque))]
        pares=[(int(a.replace(',','')),int(b.replace(',',''))) for a,b in patron.findall(tramo)]
        if len(pares)!=4:
            continue
        datos[clave]=pares
    if set(datos)!={'dem','rep','otro'}:
        raise FuenteNoDisponible('No se pudieron verificar las 12 celdas de conteos de Party × Age')
    reg={k:sum(r for r,_ in pares) for k,pares in datos.items()}
    dev={k:sum(d for _,d in pares) for k,pares in datos.items()}
    etiquetas=('18-29','30-45','46-64','65+')
    edad_reg={a:sum(datos[k][i][0] for k in datos) for i,a in enumerate(etiquetas)}
    edad_dev={a:sum(datos[k][i][1] for k in datos) for i,a in enumerate(etiquetas)}
    return reg,dev,edad_reg,edad_dev,datos


def _resumen_partidos_civiq(texto: str):
    """Respaldo para tablas que Civiq carga perezosamente.

    Toma los 3 conteos desde «Ballot Returns by Party» y deja vacios
    los grupos de edad. La coherencia se valida en extraer_civiq.
    """
    seccion=_entre(texto,'Ballot Returns by Party','Ballot Returns by Age',3500)
    reg_part=_entre(seccion,'Registration Share','Returned Share',1500)
    dev_part=_entre(seccion,'Returned Share',limite=1500)
    nombres={'dem':'Democrat','rep':'Republican','otro':'NPP/Oth'}
    # Algunas versiones llaman «Other» a la tercera categoria.
    def buscar(sec,etiqueta):
        try: return _partido_cifras(sec,etiqueta)
        except FuenteNoDisponible:
            if etiqueta=='NPP/Oth':return _partido_cifras(sec,'Other')
            raise
    reg={k:buscar(reg_part,n) for k,n in nombres.items()}
    dev={k:buscar(dev_part,n) for k,n in nombres.items()}
    return reg,dev,{},{},{}

def extraer_civiq(texto: str, fecha_consulta: Optional[datetime] = None) -> VotoTemprano:
    texto = normalizar_texto(texto)
    # Civiq suele presentar solo «CALIFORNIA STATEWIDE», sin repetir
    # el nombre de la eleccion. Identificar la pagina con el encabezado
    # estatal y verificar independientemente fecha, totales y partidos.
    # El texto por si solo NO demuestra una eleccion valida.
    titulo_valido = bool(re.search(
        r'\b(?:2026 California (?:Statewide )?General(?: Election)?|CALIFORNIA STATEWIDE)\b',
        texto, flags=re.I))
    if not titulo_valido:
        raise FuenteNoDisponible(
            'No se identifico un tablero estatal de California. '
            'Revisa el archivo diagnostico_civiq_ultima_captura.txt')
    fecha = _fecha_actualizacion(texto)
    if not (INICIO_VOTO <= fecha <= DIA_ELECCION):
        raise FuenteNoDisponible(f'Fecha incompatible con seguimiento 2026: {fecha}')
    totales = _entre(texto, 'Registration and Return Toplines', 'Ballot Return Trend', 700)
    registrados = _buscar_entero(totales, 'Registered')
    devueltas = _buscar_entero(totales, 'Returned')
    try:
        registro,devuelto,edades_reg,edades_dev,datos_pe=_crosstab_partido_edad(texto)
    except FuenteNoDisponible:
        registro,devuelto,edades_reg,edades_dev,datos_pe=_resumen_partidos_civiq(texto)
    reg_dem,reg_rep,reg_oth = registro['dem'],registro['rep'],registro['otro']
    dev_dem,dev_rep,dev_oth = devuelto['dem'],devuelto['rep'],devuelto['otro']

    if not (15_000_000 <= registrados <= 30_000_000) or devueltas < 0 or devueltas > registrados:
        raise FuenteNoDisponible('Totales de boletas o registro invalidos')
    if sum((reg_dem, reg_rep, reg_oth)) != registrados:
        raise FuenteNoDisponible(f'Los totales de registro no concuerdan ({reg_dem}+{reg_rep}+{reg_oth} != {registrados})')
    if sum((dev_dem, dev_rep, dev_oth)) != devueltas:
        raise FuenteNoDisponible(f'Los totales de devoluciones por partido no concuerdan ({dev_dem}+{dev_rep}+{dev_oth} != {devueltas})')
    if edades_reg and sum(edades_reg.values()) != registrados:
        edades_reg, edades_dev = {}, {}
    if edades_dev and sum(edades_dev.values()) != devueltas:
        edades_reg, edades_dev = {}, {}
    consulta = fecha_consulta or datetime.now(ZoneInfo('America/Los_Angeles'))
    return VotoTemprano(
        fuente='Civiq / Optiq Data', url=URL_CIVIQ,
        fecha_datos=fecha.isoformat(), fecha_consulta=consulta.isoformat(timespec='seconds'),
        registrados=registrados, devueltas=devueltas,
        registro_dem=reg_dem, registro_rep=reg_rep, registro_otro=reg_oth,
        devueltas_dem=dev_dem, devueltas_rep=dev_rep, devueltas_otro=dev_oth,
        registro_edad=edades_reg, devueltas_edad=edades_dev,
        partido_edad=({k: [list(p) for p in v] for k, v in datos_pe.items()} if edades_reg else {}),
        origen='navegador',
        referencia_historica=extraer_historico_mismo_dia(
            texto, fecha, dev_dem, dev_rep, devueltas),
    )

# El worker se incluye en el propio notebook y se materializa al ejecutar.
CIVIQ_WORKER_SOURCE = '"""Civiq capture using Brave in a bounded external process."""\nimport asyncio\nimport os\nimport sys\nfrom pathlib import Path\n\nURL = sys.argv[1]\nOUTPUT = Path(sys.argv[2])\nHEADLESS = os.getenv(\'CIVIQ_HEADLESS\',\'1\').lower() not in (\'0\',\'false\',\'no\')\nif sys.platform == \'win32\':\n    try:\n        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())\n    except AttributeError:\n        pass\n\ndef encontrar_brave():\n    env = os.getenv(\'CIVIQ_BRAVE_PATH\') or os.getenv(\'BRAVE_PATH\')\n    if env:\n        path = Path(env).expanduser()\n        if not path.is_file(): raise FileNotFoundError(f\'Ruta Brave inexistente: {path}\')\n        return path\n    candidates=[]\n    if sys.platform == \'win32\':\n        for parent in (os.getenv(\'PROGRAMFILES\'),os.getenv(\'PROGRAMFILES(X86)\'),os.getenv(\'LOCALAPPDATA\')):\n            if parent:\n                candidates.append(Path(parent)/\'BraveSoftware\'/\'Brave-Browser\'/\'Application\'/\'brave.exe\')\n    elif sys.platform==\'darwin\':\n        candidates.append(Path(\'/Applications/Brave Browser.app/Contents/MacOS/Brave Browser\'))\n    else:\n        import shutil\n        path=shutil.which(\'brave-browser\') or shutil.which(\'brave\')\n        if path: candidates.append(Path(path))\n    return next((p for p in candidates if p.is_file()),None)\n\nasync def extraer():\n    from playwright.async_api import async_playwright\n    brave=encontrar_brave()\n    kwargs={\'executable_path\':str(brave)} if brave else {}\n    async with async_playwright() as play:\n        browser=None\n        try:\n            browser=await play.chromium.launch(headless=HEADLESS,timeout=7500,**kwargs)\n            page=await browser.new_page(locale=\'en-US\',timezone_id=\'America/Los_Angeles\')\n            try:\n                await page.goto(URL,wait_until=\'domcontentloaded\',timeout=9000)\n            except Exception as exc:\n                print(f\'Navegación incompleta: {type(exc).__name__}: {str(exc)[:150]}\',file=sys.stderr)\n            try:\n                await page.wait_for_function(\'\'\'() => {\n                    const t=document.body?.innerText || \'\';\n                    return t.includes(\'Registration and Return Toplines\') &&\n                           t.includes(\'Ballot Returns by Party\') &&\n                           t.includes(\'Returned Share\');\n                }\'\'\',timeout=7000)\n            except Exception:\n                print(\'Tablas no visibles a los 8 segundos. Se toma instantánea para diagnóstico.\',file=sys.stderr)\n            content=await page.locator(\'body\').inner_text(timeout=3500)\n            OUTPUT.parent.mkdir(parents=True,exist_ok=True)\n            OUTPUT.write_text(content,encoding=\'utf-8\')\n            print(f\'Brave detectado={bool(brave)}; caracteres={len(content)}; URL final={page.url}; titulo={(await page.title())[:100]}\')\n        finally:\n            if browser:\n                try: await asyncio.wait_for(browser.close(),timeout=2)\n                except Exception: pass\n\nif __name__ == \'__main__\':\n    try:\n        asyncio.run(asyncio.wait_for(extraer(),timeout=23))\n    except Exception as exc:\n        print(f\'ERROR_NAVEGADOR {type(exc).__name__}: {str(exc)[:500]}\',file=sys.stderr)\n        sys.exit(2)\n'

def _fetch_browser_subproceso(url: str, timeout_s: int = 40) -> str:
    """Una sola sesión Brave, con duración máxima; siempre termina o lanza error."""
    import subprocess, sys, uuid
    SALIDA.mkdir(parents=True,exist_ok=True)
    worker_path=SALIDA/'_civiq_browser_worker.py'
    if not worker_path.exists() or worker_path.read_text(encoding='utf-8') != CIVIQ_WORKER_SOURCE:
        worker_path.write_text(CIVIQ_WORKER_SOURCE,encoding='utf-8')
    output_path=SALIDA/f'_civiq_page_{uuid.uuid4().hex[:12]}.txt'
    cmd=[sys.executable,str(worker_path.resolve()),url,str(output_path.resolve())]
    started=time.monotonic()
    try:
        # subprocess.run mata al worker al superar el límite, sin bloquear el kernel.
        p=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',
                         errors='replace',timeout=timeout_s,check=False)
        duracion=time.monotonic()-started
        log.info('Captura navegador: %.1fs; estado de proceso=%s', duracion, p.returncode)
        if p.returncode != 0:
            detail=((p.stderr or '')+' '+(p.stdout or '')).strip()[-1100:]
            raise FuenteNoDisponible(f'Brave no devolvió una captura válida: {detail}')
        if not output_path.exists():
            raise FuenteNoDisponible('El worker de Brave no creó el archivo temporal')
        body=output_path.read_text(encoding='utf-8')
        if len(body)<400:
            raise FuenteNoDisponible('La web devolvió una página vacía/incompleta')
        return normalizar_texto(body)
    except subprocess.TimeoutExpired as exc:
        raise FuenteNoDisponible(f'Consulta de Brave excedió {timeout_s}s y se interrumpió. '
                                 'El modelo continúa sin señal nueva.') from exc
    finally:
        output_path.unlink(missing_ok=True)



# M5: el tablero de Civiq (oct-2026) pliega las tablas históricas. El worker las expande
# antes de leer el texto (se modifica el código del worker en tiempo de ejecución).
_EXPANDIR = r'''
            try:
                await page.evaluate("""() => {
                    document.querySelectorAll('details').forEach(d => d.open = true);
                    for (const el of document.querySelectorAll('button, summary, [role=button], [aria-expanded=false]')) {
                        const t = (el.innerText || '').trim();
                        if (/^(Detailed daily tables|Show all|All elections)/i.test(t)) { try { el.click(); } catch (e) {} }
                    }
                }""")
                await page.wait_for_timeout(3000)
            except Exception as exc_exp:
                print(f'No se pudieron expandir tablas: {exc_exp}', file=sys.stderr)
'''
_ANCLA = "            content=await page.locator('body')"
assert _ANCLA in CIVIQ_WORKER_SOURCE, 'Cambió el worker de Civiq'
CIVIQ_WORKER_SOURCE = (CIVIQ_WORKER_SOURCE.replace(_ANCLA, _EXPANDIR.lstrip('\n') + _ANCLA)
                       .replace('asyncio.wait_for(extraer(),timeout=23)', 'asyncio.wait_for(extraer(),timeout=34)'))

# M5: además del texto, el worker guarda el HTML y TODAS las respuestas JSON que descarga
# el tablero (ahí viajan las series históricas aunque la tabla esté plegada).
_ESCUCHA = r'''
            respuestas = []
            async def _guardar_resp(resp):
                try:
                    if 'json' in (resp.headers.get('content-type') or ''):
                        cuerpo = await resp.text()
                        if len(cuerpo) < 20_000_000:
                            respuestas.append({'url': resp.url, 'status': resp.status, 'body': cuerpo})
                except Exception:
                    pass
            page.on('response', lambda r: asyncio.ensure_future(_guardar_resp(r)))
'''
_ANCLA_PAG = "            page=await browser.new_page(locale='en-US',timezone_id='America/Los_Angeles')\n"
_ANCLA_OUT = "            OUTPUT.write_text(content,encoding='utf-8')\n"
_VOLCADO = r'''
            try:
                import json as _json
                (OUTPUT.parent / '_civiq_ultima_captura.html').write_text(await page.content(), encoding='utf-8')
                (OUTPUT.parent / '_civiq_respuestas.json').write_text(_json.dumps(respuestas), encoding='utf-8')
                print(f'Respuestas JSON capturadas: {len(respuestas)}')
            except Exception as exc_v:
                print(f'No se pudo volcar HTML/JSON: {exc_v}', file=sys.stderr)
'''
assert _ANCLA_PAG in CIVIQ_WORKER_SOURCE and _ANCLA_OUT in CIVIQ_WORKER_SOURCE, 'Cambió el worker de Civiq'
CIVIQ_WORKER_SOURCE = (CIVIQ_WORKER_SOURCE.replace(_ANCLA_PAG, _ANCLA_PAG + _ESCUCHA.lstrip('\n'))
                       .replace(_ANCLA_OUT, _ANCLA_OUT + _VOLCADO.lstrip('\n')))
compile(CIVIQ_WORKER_SOURCE, 'worker', 'exec')   # falla aquí, no en el subproceso, si algo quedó mal



def capturar_y_extraer(url: Optional[str] = None) -> VotoTemprano:
    """Captura el tablero con el navegador y lo convierte en VotoTemprano."""
    pagina = _fetch_browser_subproceso(url or URL_CIVIQ)
    (SALIDA / '_civiq_ultima_captura.txt').write_text(pagina[:400_000], encoding='utf-8')
    return extraer_civiq(pagina)
