"""Encuestas 2026: Wikipedia (API MediaWiki) y 270toWin en vivo + base verificada (Excel o CSV), sin duplicados.

Prioridad al combinar: Wikipedia > base verificada > 270toWin (Wikipedia trae n, población y terceros).
Identidad de cada encuesta: firma (con ALIAS) + periodo de campo; ver identidad.py (auditoría T3, 26-oct).
Nevada: la columna de Aaron Ford se busca por nombre completo (hay otra candidata «Danielle Ford», independiente,
que cuenta como tercero).
"""
from __future__ import annotations

import logging
import re
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from . import encuestas_web as W
from . import identidad
from .red import get_json, get_text

log = logging.getLogger(__name__)

COLS = ['pollster', 'clave', 'inicio', 'fin', 'n', 'pop', 'D', 'R', 'otros', 'indecisos', 'origen']
MESES = {'ene': 1, 'jan': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'apr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'ago': 8, 'aug': 8,
         'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12, 'dec': 12}
# misma encuestadora con nombres distintos entre fuentes (clave de 14 letras, como FiveThirtyEight)
ALIAS = {'noblepredictive': 'noblepredictiv', 'npi': 'noblepredictiv', 'emerson': 'emersoncollege',
         'globalstrategygroupforford': 'globalstrategy', 'publicpolicypolling': 'publicpolicypo', 'ppp': 'publicpolicypo'}
HOJA_EXCEL = 'Gobernador Nevada'                       # NEVADA_GOBERNADOR-v2.xlsx
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
    """Bloque «Individual surveys» de la hoja «Gobernador Nevada» (encuestadoras en columnas).
    Se excluyen promedios, preguntas de primaria, careos hipotéticos («Ford vs. Hansen») y versiones RV repetidas."""
    m = pd.read_excel(ruta, sheet_name=HOJA_EXCEL, header=None, dtype=object).values.tolist()
    fila = lambda pref: next(i for i, r in enumerate(m) if str(r[0]).lower().startswith(pref))
    i_n, i_f, i_d, i_r = fila('encuestadora'), fila('fechas de encuesta'), fila('aaron ford'), fila('joe lombardo')
    out = []
    for j in range(1, len(m[i_n])):
        nombre = m[i_n][j]
        if pd.isna(nombre) or not str(nombre).strip() or pd.isna(m[i_f][j]):
            continue
        if any(x in str(nombre).upper().replace('\n', ' ') for x in EXCLUIR_EXCEL):
            continue
        D, R = pd.to_numeric(m[i_d][j], errors='coerce'), pd.to_numeric(m[i_r][j], errors='coerce')
        if not (np.isfinite(D) and np.isfinite(R)):
            continue
        ini, fin = _fechas_es(m[i_f][j])
        out.append({'pollster': str(nombre).strip(), 'inicio': ini, 'fin': fin, 'n': np.nan, 'pop': None,
                    'D': float(D), 'R': float(R), 'otros': np.nan, 'indecisos': np.nan})
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
    """Une las fuentes sin contar dos veces la misma encuesta ni fundir olas distintas: identidad por periodo de campo
    (identidad.py, común a los diez paquetes; auditoría T3 del 26-oct). Las decisiones quedan en .attrs['decisiones']."""
    return identidad.combinar_df(*fuentes, cols=COLS)


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
    for d_ in p.attrs.get('decisiones', []):
        log.info('Identidad %s (%s): %s | %s', d_['decision'], d_['razon'], d_['conservada'], d_['nueva'])
    p = p[(pd.to_datetime(p.fin) > pd.Timestamp(cfg.fecha_nominacion)) &
          (pd.to_datetime(p.fin) <= pd.Timestamp(cfg.corte))].copy()
    p['partidista'] = p.pollster.str.contains(r'\((?:R|D)\)')
    p['n'] = pd.to_numeric(p.n, errors='coerce').fillna(600).clip(100, 3000)
    p['fin'] = pd.to_datetime(p.fin)
    p['days'] = (pd.Timestamp(cfg.dia_eleccion) - p.fin).dt.days
    p['margin_poll'] = p.D - p.R
    p['pollster_key'] = p.clave
    p['otros'] = pd.to_numeric(p.otros, errors='coerce')
    if p.duplicated(['pollster_key', 'inicio', 'fin']).any():
        raise ValueError('encuestas duplicadas tras combinar: '
                         + str(p[p.duplicated(['pollster_key', 'inicio', 'fin'], keep=False)].pollster.tolist()))
    vivas = int((p.origen.isin(['wikipedia', '270towin']) | p.tambien_en.str.contains('wikipedia|270towin')).sum())
    if vivas < f.min_encuestas_vivas:
        avisos.append(f'solo {vivas} encuestas aparecen en fuentes web (< {f.min_encuestas_vivas})')
    log.info('Encuestas: %d combinadas (wiki %d, base %d, 270 %d)', len(p), len(wiki), len(base), len(t270))
    return {'encuestas': p.sort_values('fin').reset_index(drop=True), 'estados': estados, 'avisos': avisos,
            'conteos': {'wikipedia': len(wiki), 'base': len(base), '270towin': len(t270)}}
