"""Encuestas 2026: Wikipedia (API MediaWiki) y 270toWin en vivo + base verificada (Excel o CSV), sin duplicados.

Prioridad al combinar: Wikipedia > base verificada > 270toWin (Wikipedia trae n, población y terceros).
Misma encuesta = misma firma (con ALIAS) y fin a ≤ 7 días, o misma firma con las mismas cifras (±0.5) a ≤ 60 días
(270toWin fecha por publicación). Firmas distintas solo se fusionan si coinciden cifras Y tamaño de muestra (n ≥ 300) a
≤ 30 días: 270toWin rotula «YouGov» encuestas que Wikipedia atribuye al patrocinador.
Nueva York: Siena College Research Institute (encuestas propias) ≠ NYT/Siena; Marist University = Marist College;
co/efficient, McLaughlin, OnMessage y Red Oak son firmas republicanas. Si una fuente trae la versión LV y otra la RV
de la misma encuesta, se conserva la LV. La identidad de una encuesta es firma + periodo de campo (ver combinar).
"""
from __future__ import annotations

import logging
import re
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from . import encuestas_web as W
from .red import get_json, get_text

log = logging.getLogger(__name__)

COLS = ['pollster', 'clave', 'inicio', 'fin', 'n', 'pop', 'D', 'R', 'otros', 'indecisos', 'origen']
MESES = {'ene': 1, 'jan': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'apr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'ago': 8, 'aug': 8,
         'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12, 'dec': 12}
# misma encuestadora con nombres distintos entre fuentes (clave de 14 letras, como FiveThirtyEight)
# misma encuestadora con nombres distintos entre fuentes → clave de 14 letras del histórico de FiveThirtyEight
# (así conserva su efecto de casa): Excel · Wikipedia · 270toWin
# Nueva York: «Siena College» (Siena College Research Institute) tiene su propio historial en FiveThirtyEight (62 encuestas,
# casi todas de NY), distinto de «The New York Times/Siena College»: NO se unifican (en los otros estados Siena = NYT/Siena)
ALIAS = {'nyt': 'thenewyorktime', 'newyorktimes': 'thenewyorktime', 'siena': 'sienacollege', 'sienaresearch': 'sienacollege',
         'sienacollegere': 'sienacollege', 'sienauniversit': 'sienacollege',
         'beacon': 'beaconresearch', 'foxnews': 'beaconresearch',
         'umasslowell': 'universityofma',
         'fabriziolee': 'fabrizioleeass', 'fabrizioward': 'fabrizioleeass', 'aarp': 'fabrizioleeass',
         'cbs': 'cbsnews',
         'maristuniversi': 'maristcollege', 'maristpoll': 'maristcollege',
         'masondixon': 'masondixonpoll', 'masondixontele': 'masondixonpoll',
         'univofhouston': 'universityofho', 'univofhoustonh': 'universityofho',
         'newriver': 'gsstrategygrou', 'newrivergsg': 'gsstrategygrou', 'cookpoliticalr': 'gsstrategygrou',  # Cook encarga a GS/New River
         'texasam': 'reconmr', 'texasamreconmr': 'reconmr', 'texasamunivers': 'reconmr',
         'texassouthernu': 'texassouthernu', 'texassouthern': 'texassouthernu',
         'uttyler': 'universityofte', 'publicpolicypol': 'publicpolicypo', 'ppp': 'publicpolicypo',
         'overtoninsight': 'overtoninsight', 'overton': 'overtoninsight',
         'chicagonewswee': 'publicpolicypo', 'emersoncollegew': 'emersoncollege', 'wgntv': 'emersoncollege',
         'victoryresearc': 'victoryresearc',
         'mclaughlinasso': 'mclaughlinasso', 'mclaughlin': 'mclaughlinasso', 'quinnipiac': 'quinnipiacuniv',
         'coefficient': 'co', 'onmessage': 'onmessageinc'}
# claves que dependen del nombre completo (el Excel nombra «Public Policy Polling — Chicago News Weekly»)
POR_NOMBRE = (('new york times', 'thenewyorktime'), ('public policy polling', 'publicpolicypo'))
HOJA_EXCEL = 'Histórico encuestas'                   # NUEVA_YORK_GOBERNADOR-v1.xlsx (bloque 1: elección general)
ANIO_DEFECTO = 2026                                    # fechas del Excel sin año
# columnas del Excel que no son encuestas generales de los dos candidatos
EXCLUIR_EXCEL = ('PROME', 'PRIMARIA', ' VS.', 'MISMA ENCUESTA')


def clave(nombre: str) -> str:
    n = str(nombre).lower()
    for sub, k in POR_NOMBRE:
        if sub in n:
            return k
    k = W.clave_firma(nombre)
    return ALIAS.get(k, k)


# ----------------------------------------------------------------------------------- base verificada
def _fechas_es(txt: str, anio_defecto: int = ANIO_DEFECTO) -> tuple[date, date]:
    """Fechas del Excel, en inglés o español, con o sin año:
    'Sep 22–26' · 'Nov 16–18, 2025' · 'Dic 11–18, 2025' · 'Jun 27–Jul 2' · '30 sep–05 oct 2026'."""
    s = str(txt).strip().lower().replace('—', '–').replace('-', '–').replace('.', '')
    m_anio = re.search(r'(\d{4})', s)
    anio = int(m_anio.group(1)) if m_anio else anio_defecto
    s = re.sub(r',?\s*\d{4}\s*$', '', s).strip()
    ini, fin = [x.strip() for x in s.split('–', 1)] if '–' in s else (s, s)

    def parte(x: str, mes_previo: int | None):
        x = x.strip()
        m = re.match(r'([a-z]{3})[a-z]*\s+(\d{1,2})$', x)           # 'sep 22'
        if m:
            return int(m.group(2)), MESES[m.group(1)]
        m = re.match(r'(\d{1,2})\s+([a-z]{3})', x)                  # '22 sep'
        if m:
            return int(m.group(1)), MESES[m.group(2)]
        return int(re.match(r'(\d{1,2})', x).group(1)), mes_previo  # '26' (mismo mes)

    di, mi = parte(ini, None)
    df_, mf = parte(fin, mi)
    if mi is None:                                                   # '05–07 oct': el mes viene al final
        mi = mf
    return date(anio - (mi > mf), mi, di), date(anio, mf, df_)


def encuestas_excel(ruta: Path) -> pd.DataFrame:
    """Bloque 1 (elección general) de la hoja «Histórico encuestas»: encuestadoras en columnas, con fechas de inicio y
    fin, población, candidato (D), candidato (R) e «Indecisos / Otros» (en proporciones; «n.d.» = no reportado). Las filas
    de los candidatos se reconocen por la etiqueta «(D)» / «(R)». El Excel no separa a los terceros de los indecisos, así
    que «otros» queda como no reportado (≠ 0)."""
    m = pd.read_excel(ruta, sheet_name=HOJA_EXCEL, header=None, dtype=object).values.tolist()
    ini_bloque = next(i for i, r in enumerate(m) if str(r[0]).strip().lower() == 'encuestadora')
    fin_bloque = next((i for i in range(ini_bloque + 1, len(m)) if str(m[i][0]).strip().lower() == 'encuestadora'), len(m))
    b = m[ini_bloque:fin_bloque]
    fila = lambda pref: next(r for r in b if str(r[0]).strip().lower().startswith(pref))
    f_n, f_i, f_f, f_p = fila('encuestadora'), fila('inicio'), fila('fin de'), fila('población')
    f_d = next(r for r in b if str(r[0]).strip().lower().endswith('(d)'))
    f_r = next(r for r in b if str(r[0]).strip().lower().endswith('(r)'))
    f_u = fila('indecisos')
    f_b = next((r for r in b if str(r[0]).strip().lower().startswith(('terceros', 'otros candidatos'))), [None] * len(f_n))
    num = lambda x: pd.to_numeric(x, errors='coerce')
    out = []
    for j in range(1, len(f_n)):
        nombre = f_n[j]
        if pd.isna(nombre) or not str(nombre).strip() or pd.isna(f_f[j]):
            continue
        D, R = num(f_d[j]), num(f_r[j])
        if not (np.isfinite(D) and np.isfinite(R)):
            continue
        esc = 100.0 if D <= 1 and R <= 1 else 1.0                         # proporciones → %
        pop = {'votantes probables': 'LV', 'registrados': 'RV'}.get(str(f_p[j]).strip().lower())
        B, U = num(f_b[j]), num(f_u[j])
        out.append({'pollster': str(nombre).strip(), 'inicio': pd.Timestamp(f_i[j]).date(), 'fin': pd.Timestamp(f_f[j]).date(),
                    'n': np.nan, 'pop': pop, 'D': round(esc * float(D), 2), 'R': round(esc * float(R), 2),
                    'otros': round(esc * float(B), 2) if np.isfinite(B) else np.nan,
                    'indecisos': round(esc * float(U), 2) if np.isfinite(U) else np.nan})
    return pd.DataFrame(out)


def cargar_base(ruta: Path) -> pd.DataFrame:
    if ruta.suffix.lower() in ('.xlsx', '.xlsm', '.xls'):
        df = encuestas_excel(ruta)
    else:
        df = pd.read_csv(ruta)
        faltan = {'pollster', 'inicio', 'fin', 'D', 'R'} - set(df.columns)
        if faltan:
            raise ValueError(f'{ruta.name}: faltan columnas {sorted(faltan)}')
        for c in ('n', 'pop', 'otros', 'indecisos'):
            if c not in df:
                df[c] = np.nan
    df['origen'] = 'base'
    return df


def exportar_base_csv(ruta_excel: Path, ruta_csv: Path) -> pd.DataFrame:
    """Convierte el Excel verificado a CSV (la versión que se publica en el repositorio)."""
    df = encuestas_excel(ruta_excel)
    df[['pollster', 'inicio', 'fin', 'D', 'R', 'n', 'pop', 'otros', 'indecisos']].to_csv(ruta_csv, index=False)
    return df


# ----------------------------------------------------------------------------------- combinar
def _normalizar(f: pd.DataFrame, origen: str | None = None) -> pd.DataFrame:
    f = f.copy()
    if origen:
        f['origen'] = origen
    f['clave'] = f.pollster.map(clave)
    for c in ('inicio', 'fin'):
        f[c] = pd.to_datetime(f[c]).dt.date
    f['inicio'] = f.inicio.fillna(f.fin)
    for c in COLS:
        if c not in f:
            f[c] = np.nan
    return f[COLS]


def _intervalo(r: dict) -> tuple[pd.Timestamp, pd.Timestamp, bool]:
    """(inicio, fin, puntual). «Puntual» = la fuente solo da una fecha (270toWin): suele ser la de PUBLICACIÓN, no el
    cierre de campo (Verasight/VoteHub: campo 1–20 oct, publicada el 23-oct)."""
    fin = pd.Timestamp(r['fin'])
    ini = pd.Timestamp(r['inicio']) if pd.notna(r.get('inicio')) else fin
    return ini, fin, ini == fin


def _distancia(a: tuple, b: tuple) -> int:
    """Días entre dos periodos de campo (0 si se solapan o se tocan)."""
    return max((a[0] - b[1]).days, (b[0] - a[1]).days, 0)


def combinar(*fuentes: pd.DataFrame) -> pd.DataFrame:
    """Une las fuentes sin contar dos veces la misma encuesta.

    La identidad de una encuesta es (firma, PERIODO DE CAMPO), no (firma, fecha cercana):
      - misma firma y periodos que se solapan o se tocan → misma encuesta (versiones LV/RV o la misma en dos fuentes);
      - misma firma, periodos distintos y ambos con rango → encuestas DISTINTAS aunque estén a pocos días (ActiVote
        30 sep–14 oct y 17–21 oct; antes la regla «≤ 7 días» las fundía y se perdía la más reciente);
      - una fuente con fecha puntual (publicación) a ≤ 7 días del periodo de otra con las mismas cifras, o a ≤ 3 días
        con cualquier cifra → misma encuesta (Verasight 23-oct en 270toWin = campo 1–20 oct en Wikipedia);
      - mismas cifras entre fuentes distintas a ≤ 60 días → misma encuesta con la fecha mal capturada.
    Ninguna fuente publica un identificador de estudio, así que el periodo de campo es la mejor llave disponible.
    Se elige la candidata MÁS CERCANA (no la primera que cumpla): Beacon/Shaw repitió 47–52 el 28-sep y el 19-oct.
    """
    base: list[dict] = []
    for f in fuentes:
        for r in f.to_dict('records'):
            ir = _intervalo(r)
            mejor, mejor_d = None, None
            for b in base:
                ib = _intervalo(b)
                dist = _distancia(ir, ib)
                dias = abs((ir[1] - ib[1]).days)
                mismas = abs(r['D'] - b['D']) <= 0.51 and abs(r['R'] - b['R']) <= 0.51
                otra_fuente = r['origen'] != b['origen']
                # 270toWin rotula «YouGov» encuestas que otras fuentes atribuyen al patrocinador (UT/Texas Politics Project,
                # CBS, Univision…): mismo n (≥ 300) y mismas cifras a ≤ 30 días = misma encuesta aunque cambie el nombre
                mismo_n = pd.notna(r.get('n')) and pd.notna(b.get('n')) and r['n'] >= 300 and abs(r['n'] - b['n']) < 0.5
                # «YouGov» genérico frente a «<patrocinador>/YouGov» con las mismas cifras a ≤ 7 días (el n puede diferir:
                # CBS/YouGov 16-oct trae 1,492 en Wikipedia y 1,460 en 270toWin)
                generico = mismas and dist <= 7 and 'yougov' in (r['clave'], b['clave']) and \
                    'yougov' in str(r.get('pollster', '')).lower() and 'yougov' in str(b.get('pollster', '')).lower()
                puntual = ir[2] or ib[2]
                misma_firma = r['clave'] == b['clave'] and (
                    dist == 0 and not puntual                                   # periodos de campo que se solapan
                    or puntual and (dist <= 3 or (mismas and dist <= 7))        # fecha de publicación de otra fuente
                    or mismas and otra_fuente and dias <= 60)                   # misma encuesta, fecha mal capturada
                if (misma_firma or (mismas and mismo_n and dias <= 30) or generico) and \
                        (mejor_d is None or (dist, dias) < mejor_d):
                    mejor, mejor_d = b, (dist, dias)
            if mejor is None:
                base.append(dict(r))
                continue
            b = mejor
            rk = {'LV': 0, 'RV': 1, 'A': 2}
            if rk.get(str(r.get('pop')), 3) < rk.get(str(b.get('pop')), 3):   # misma encuesta, mejor población
                for c in ('D', 'R', 'otros', 'indecisos', 'n', 'pop'):
                    b[c] = r[c]
                b['nota_version'] = f"versión {r.get('pop')} de {r['origen']}"
            # cifras con decimales del Excel verificado (Emerson 52.4–39.7, McLaughlin 49.6–45.7) frente a las redondeadas de
            # Wikipedia/270toWin (52–40, 50–46): si son compatibles con el redondeo (±0.5), se conservan las del Excel
            if (r['origen'] == 'base' and b['origen'] != 'base'
                    and abs(r['D'] - b['D']) <= 0.5 and abs(r['R'] - b['R']) <= 0.5
                    and (r['D'] % 1 or r['R'] % 1)):
                b['D'], b['R'] = r['D'], r['R']
                b['nota_version'] = (b.get('nota_version') or '') + ' cifras con decimales del Excel verificado'
            if _intervalo(b)[2] and not ir[2]:                   # conserva el periodo de campo, no la fecha de publicación
                b['inicio'], b['fin'] = r['inicio'], r['fin']
            for c in ('n', 'pop', 'otros', 'indecisos'):       # completa datos que falten
                if pd.isna(b.get(c)) and pd.notna(r.get(c)):
                    b[c] = r[c]
            b.setdefault('tambien_en', set()).add(r['origen'])
    out = pd.DataFrame(base, columns=COLS + ['tambien_en', 'nota_version'])
    out['tambien_en'] = out.tambien_en.map(lambda s: ', '.join(sorted(s)) if isinstance(s, set) else '')
    out['nota_version'] = out.nota_version.astype(object).where(out.nota_version.notna(), '')
    return out


def aplicar_correcciones_cifras(p: pd.DataFrame, cfg) -> tuple[pd.DataFrame, list[str]]:
    """Reemplaza D y R con las cifras de la publicación original (data/correcciones_cifras.csv: clave, fin, pop, D, R,
    fuente). Wikipedia redondea a enteros por separado: ActiVote 47.5–52.5 aparece como 48–53 (suma 101). El margen D−R
    no cambia en ese caso, pero las cifras deben ser las publicadas."""
    txt = str(cfg.rutas.get('correcciones_cifras', '') or '').strip()
    if not txt or not cfg.ruta('correcciones_cifras').exists():
        return p, []
    c = pd.read_csv(cfg.ruta('correcciones_cifras'), comment='#')
    hechas = []
    for _, r in c.iterrows():
        m = ((p.clave == str(r.clave)) & (pd.to_datetime(p.fin) == pd.Timestamp(r.fin))
             & (p['pop'].astype(str).str.upper() == str(r['pop']).upper()))
        if m.any():
            antes = f"{p.loc[m, 'D'].iloc[0]:g}–{p.loc[m, 'R'].iloc[0]:g}"
            p.loc[m, 'D'], p.loc[m, 'R'] = float(r.D), float(r.R)
            hechas.append(f"{r.clave} {r.fin} {r['pop']}: {antes} → {r.D:g}–{r.R:g} ({r.fuente})")
    return p, hechas


# ----------------------------------------------------------------------------------- en vivo con caché
def _con_cache(cfg, nombre: str, funcion):
    """Ejecuta funcion(); si falla o viene vacía, usa la caché. Devuelve (df, estado)."""
    ruta = cfg.dir_cache / f'encuestas_{nombre}.csv'
    try:
        df = funcion()
        if df is None or df.empty:
            raise ValueError('sin encuestas reconocibles (¿cambió el formato de la página?)')
        df.to_csv(ruta, index=False, encoding='utf-8')
        return df, 'en_vivo'
    except Exception as exc:
        err = f'{type(exc).__name__}: {str(exc)[:160]}'
        if ruta.exists():
            df = pd.read_csv(ruta)
            df = df[df.pollster.notna() & (df.pollster.astype(str).str.strip() != '')].reset_index(drop=True)
            log.warning('Encuestas %s: uso caché (%s)', nombre, err)
            return df, f'cache ({err})'
        log.warning('Encuestas %s: sin datos ni caché (%s)', nombre, err)
        return pd.DataFrame(columns=COLS), f'no_disponible ({err})'


def aplicar_correcciones_n(p: pd.DataFrame, cfg) -> tuple[pd.DataFrame, list[str]]:
    """Reemplaza n con el tamaño verificado de data/correcciones_tamano_muestra.csv (clave, fin, pop, n, fuente).

    La coincidencia es por clave de encuestadora, fecha de fin y población (LV/RV): una corrección de la versión LV no
    toca la RV de la misma encuesta. Se usa cuando la fuente web no publica el n de esa versión (p. ej. Wikipedia da el
    n de la muestra RV completa en una celda compartida con la fila LV).
    """
    txt = str(cfg.rutas.get('correcciones_n', '') or '').strip()
    if not txt:
        return p, []
    ruta = cfg.ruta('correcciones_n')
    if not ruta.exists():
        return p, []
    c = pd.read_csv(ruta, comment='#')
    hechas = []
    for _, r in c.iterrows():
        m = ((p.clave == str(r.clave)) & (pd.to_datetime(p.fin) == pd.Timestamp(r.fin))
             & (p['pop'].astype(str).str.upper() == str(r['pop']).upper()))
        if m.any():
            antes = p.loc[m, 'n'].iloc[0]
            p.loc[m, 'n'] = float(r.n)
            p.loc[m, 'n_fuente'] = f'corregido ({r.fuente})'
            hechas.append(f"{r.clave} {r.fin} {r['pop']}: {('sin n' if pd.isna(antes) else int(antes))} → {int(r.n)}")
    return p, hechas


def obtener_encuestas(cfg) -> dict:
    f, e = cfg.fuentes, cfg.eleccion
    anio = cfg.dia_eleccion.year

    def _wiki():
        js = get_json(f.wikipedia_api, params={'action': 'parse', 'page': f.wikipedia_pagina, 'prop': 'text',
                                               'format': 'json', 'formatversion': 2, 'redirects': 1},
                      offline=cfg.offline, timeout=f.timeout_http_s)
        # atributos «rowspan="2;"» mal formados (aparecen en páginas de Wikipedia) rompen el parser: se normalizan
        html = re.sub(r'(rowspan|colspan)="\s*(\d+)[^"]*"', r'\1="\2"', js['parse']['text'])
        return W.elegir_versiones(W.parse_tabla_wikipedia(html, e.candidato_d, e.candidato_r, anio))

    def _t270():
        html = get_text(f.t270_url, offline=cfg.offline, timeout=f.timeout_http_s)
        t = W.parse_tabla_270(html, e.candidato_d, e.candidato_r, anio)
        if t.empty:                                    # 270toWin rotula solo con el apellido
            t = W.parse_tabla_270(html, e.candidato_d.split()[-1], e.candidato_r.split()[-1], anio)
        return W.elegir_versiones(t)

    estados, avisos = {}, []
    wiki, estados['wikipedia'] = _con_cache(cfg, 'wikipedia', _wiki)
    t270, estados['270towin'] = _con_cache(cfg, '270towin', _t270)
    base = pd.DataFrame(columns=COLS)
    rb = cfg.ruta_encuestas_base
    if rb is not None:
        if rb.exists():
            try:
                base = cargar_base(rb)
                estados['base_verificada'] = f'archivo ({rb.name}, {len(base)} encuestas)'
            except Exception as exc:
                estados['base_verificada'] = f'error ({type(exc).__name__}: {exc})'
                avisos.append(f'no se pudo leer {rb.name}: {exc}')
        else:
            estados['base_verificada'] = f'no_encontrado ({rb})'
            avisos.append(f'no existe la base verificada {rb}')
    if wiki.empty and t270.empty and base.empty:
        raise ValueError('ninguna fuente de encuestas disponible (ni en vivo, ni caché, ni base verificada)')
    fuentes = [_normalizar(x, o) for x, o in ((wiki, 'wikipedia'), (base, 'base'), (t270, '270towin')) if len(x)]
    p = combinar(*fuentes)
    p = p[(pd.to_datetime(p.fin) > pd.Timestamp(cfg.fecha_nominacion)) &
          (pd.to_datetime(p.fin) <= pd.Timestamp(cfg.corte))].copy()
    p['partidista'] = p.pollster.map(lambda x: len(set(re.findall(r'\((D|R)\)', str(x)))) == 1)   # bipartidista ≠ partidista
    # Wikipedia marca «(D)» a firmas de inclinación partidista aunque la encuesta la pague un medio (PPP para Chicago
    # News Weekly). Para el ajuste partidista cuenta el PATROCINIO (como la columna partisan de FiveThirtyEight)
    sin_pat = set(cfg.eleccion.get('firmas_sin_patrocinio_partidista', []) or [])
    p.loc[p.clave.isin(sin_pat), 'partidista'] = False
    p['n'] = pd.to_numeric(p.n, errors='coerce')
    p['n_fuente'] = np.where(p.n.notna(), 'reportado', '')
    p, aplicadas = aplicar_correcciones_n(p, cfg)
    if aplicadas:
        log.info('Tamaños de muestra corregidos: %s', '; '.join(aplicadas))
    p, cifras = aplicar_correcciones_cifras(p, cfg)
    if cifras:
        log.info('Cifras corregidas con la publicación original: %s', '; '.join(cifras))
    p['n_imputado'] = p.n.isna()
    p.loc[p.n_imputado, 'n_fuente'] = 'imputado (600)'
    p['n'] = p.n.fillna(600).clip(100, 3000)
    p['fin'] = pd.to_datetime(p.fin)
    p['days'] = (pd.Timestamp(cfg.dia_eleccion) - p.fin).dt.days
    p['margin_poll'] = p.D - p.R
    p['pollster_key'] = p.clave
    p['otros'] = pd.to_numeric(p.otros, errors='coerce')
    if p.duplicated(['pollster_key', 'fin']).any():
        raise ValueError('encuestas duplicadas tras combinar: '
                         + str(p[p.duplicated(['pollster_key', 'fin'], keep=False)].pollster.tolist()))
    vivas = int((p.origen.isin(['wikipedia', '270towin']) | p.tambien_en.str.contains('wikipedia|270towin')).sum())
    if vivas < f.min_encuestas_vivas:
        avisos.append(f'solo {vivas} encuestas aparecen en fuentes web (< {f.min_encuestas_vivas})')
    log.info('Encuestas: %d combinadas (wiki %d, base %d, 270 %d)', len(p), len(wiki), len(base), len(t270))
    return {'encuestas': p.sort_values('fin').reset_index(drop=True), 'estados': estados, 'avisos': avisos,
            'conteos': {'wikipedia': len(wiki), 'base': len(base), '270towin': len(t270)}}
