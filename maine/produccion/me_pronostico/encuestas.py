"""Encuestas 2026: Wikipedia (API MediaWiki) y 270toWin en vivo + base verificada (Excel o CSV), sin duplicados.

Prioridad al combinar: Wikipedia > base verificada > 270toWin (Wikipedia trae n, población y terceros).
Misma encuesta = misma firma (con ALIAS) y fin a ≤ 7 días, o misma firma con las mismas cifras (±0.5) a ≤ 60 días
(270toWin fecha por publicación). Nunca se fusionan firmas distintas solo por coincidir en cifras.
Maine: las encuestas aparecen con el medio o con la firma (NYT/Portland Press Herald/Siena = Siena; AARP = Fabrizio
Ward/Impact; Fox News = Beacon/Shaw; CNN = SSRS; WaPo/George Mason = Schar School). Si una fuente trae la versión LV y
otra la RV de la misma encuesta, se conserva la LV.
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
ALIAS = {'nyt': 'thenewyorktime', 'newyorktimes': 'thenewyorktime', 'sienacollege': 'thenewyorktime', 'siena': 'thenewyorktime',
         'beacon': 'beaconresearch', 'foxnews': 'beaconresearch',
         'univofnewhamps': 'universityofne',
         'cnn': 'ssrs',
         'umasslowell': 'universityofma',
         'fabriziolee': 'fabrizioleeass', 'fabrizioward': 'fabrizioleeass', 'aarp': 'fabrizioleeass',
         'cbs': 'cbsnews',
         'maristuniversi': 'maristcollege', 'maristpoll': 'maristcollege',
         'washingtonpost': 'thewashingtonp', 'washpostschars': 'thewashingtonp'}
HOJA_EXCEL = 'Histórico encuestas'                   # MAINE_GOBERNADOR-v1.xlsx (bloque 1: elección general)
ANIO_DEFECTO = 2026                                    # fechas del Excel sin año
# columnas del Excel que no son encuestas generales de los dos candidatos
EXCLUIR_EXCEL = ('PROME', 'PRIMARIA', ' VS.', 'MISMA ENCUESTA')


def clave(nombre: str) -> str:
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
    fin, población, Pingree, Charles, Bennett e indecisos (en proporciones; «n.d.» = no reportado).
    Bennett es un tercero real: «n.d.» significa que la encuesta no lo preguntó (p. ej. CBS/YouGov, careo forzado), no 0."""
    m = pd.read_excel(ruta, sheet_name=HOJA_EXCEL, header=None, dtype=object).values.tolist()
    ini_bloque = next(i for i, r in enumerate(m) if str(r[0]).strip().lower() == 'encuestadora')
    fin_bloque = next((i for i in range(ini_bloque + 1, len(m)) if str(m[i][0]).strip().lower() == 'encuestadora'), len(m))
    b = m[ini_bloque:fin_bloque]
    fila = lambda pref: next(r for r in b if str(r[0]).strip().lower().startswith(pref))
    f_n, f_i, f_f, f_p = fila('encuestadora'), fila('inicio'), fila('fin de'), fila('población')
    f_d, f_r, f_b, f_u = fila('hannah pingree'), fila('bobby charles'), fila('rick bennett'), fila('indecisos')
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


def combinar(*fuentes: pd.DataFrame) -> pd.DataFrame:
    base: list[dict] = []
    for f in fuentes:
        for r in f.to_dict('records'):
            dup = False
            for b in base:
                dias = abs((pd.Timestamp(r['fin']) - pd.Timestamp(b['fin'])).days)
                mismas = abs(r['D'] - b['D']) <= 0.51 and abs(r['R'] - b['R']) <= 0.51
                if r['clave'] == b['clave'] and (dias <= 7 or (mismas and dias <= 60)):
                    dup = True
                    rk = {'LV': 0, 'RV': 1, 'A': 2}
                    if rk.get(str(r.get('pop')), 3) < rk.get(str(b.get('pop')), 3):   # misma encuesta, mejor población
                        for c in ('D', 'R', 'otros', 'indecisos', 'n', 'pop'):
                            b[c] = r[c]
                        b['nota_version'] = f"versión {r.get('pop')} de {r['origen']}"
                    for c in ('n', 'pop', 'otros', 'indecisos'):       # completa datos que falten
                        if pd.isna(b.get(c)) and pd.notna(r.get(c)):
                            b[c] = r[c]
                    b.setdefault('tambien_en', set()).add(r['origen'])
                    break
            if not dup:
                base.append(dict(r))
    out = pd.DataFrame(base, columns=COLS + ['tambien_en', 'nota_version'])
    out['tambien_en'] = out.tambien_en.map(lambda s: ', '.join(sorted(s)) if isinstance(s, set) else '')
    out['nota_version'] = out.nota_version.fillna('')
    return out


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
    p['n'] = pd.to_numeric(p.n, errors='coerce')
    p['n_fuente'] = np.where(p.n.notna(), 'reportado', '')
    p, aplicadas = aplicar_correcciones_n(p, cfg)
    if aplicadas:
        log.info('Tamaños de muestra corregidos: %s', '; '.join(aplicadas))
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
