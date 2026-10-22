"""Parsers de encuestas de Wikipedia (API MediaWiki) y 270toWin.

Mismos parsers que la producción de Georgia (georgia/produccion/ga_pronostico/encuestas.py).
"""
from __future__ import annotations

import logging
import re
from datetime import date
from io import StringIO

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

MESES = {m: i for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'], 1)}
COLUMNAS = ['pollster', 'clave_538', 'inicio', 'fin', 'n', 'pop', 'D', 'R', 'otros', 'indecisos',
            'tipo_pregunta', 'fuente', 'origen', 'nota']
TIPOS_PREGUNTA = {'general', 'dos_opciones', 'reasignacion'}
RANGO_POP = {'LV': 0, 'RV': 1, 'A': 2}


# ----------------------------------------------------------------------------------- utilidades
def limpiar(txt) -> str:
    s = '' if txt is None or (isinstance(txt, float) and np.isnan(txt)) else str(txt)
    s = re.sub(r'\[[^\]]*\]', '', s)                      # notas [a], [12]
    return re.sub(r'\s+', ' ', s).strip()


def a_numero(txt) -> float:
    s = limpiar(txt).replace(',', '')
    if s.startswith('<'):
        return 0.5
    m = re.search(r'-?\d+(?:\.\d+)?', s)
    return float(m.group()) if m else np.nan


def parse_muestra(txt) -> tuple[float, str | None]:
    s = limpiar(txt).upper()
    pop = next((p for p in ('LV', 'RV', 'A') if re.search(rf'\b{p}\b', s)), None)
    return a_numero(s.split('(')[0] if '(' in s else s), pop


def _mes(token: str) -> int | None:
    t = token.strip().lower()[:3]
    return MESES.get(t)


def parse_fechas(txt, anio_defecto: int) -> tuple[date | None, date | None]:
    """'October 12–13, 2026' · 'Sep 28 – Oct 2, 2026' · 'July 29 – August 1, 2026' · '10/14/2026' · 'Sept. 14, 2026'."""
    s = limpiar(txt).replace('—', '–').replace('-', '–').replace('Sept', 'Sep')
    m = re.fullmatch(r'(\d{1,2})/(\d{1,2})/(\d{4})', s)
    if m:
        d = date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
        return d, d
    anio = re.search(r'(\d{4})\s*$', s)
    anio = int(anio.group(1)) if anio else anio_defecto
    s = re.sub(r',?\s*\d{4}\s*$', '', s).replace('.', '')
    partes = [p.strip() for p in s.split('–') if p.strip()]
    if not partes:
        return None, None
    m1 = re.match(r'([A-Za-z]+)\s+(\d{1,2})', partes[0])
    if not m1 or _mes(m1.group(1)) is None:
        return None, None
    mes_i, dia_i = _mes(m1.group(1)), int(m1.group(2))
    if len(partes) == 1:
        d = date(anio, mes_i, dia_i)
        return d, d
    m2 = re.match(r'(?:([A-Za-z]+)\s+)?(\d{1,2})', partes[-1])
    if not m2:
        return None, None
    mes_f = _mes(m2.group(1)) if m2.group(1) else mes_i
    anio_i = anio - 1 if mes_f is not None and mes_f < mes_i else anio
    return date(anio_i, mes_i, dia_i), date(anio, mes_f or mes_i, int(m2.group(2)))


def clave_firma(nombre: str, alias: pd.DataFrame | None = None) -> str:
    n = limpiar(nombre)
    if alias is not None:
        for _, a in alias.iterrows():
            if re.search(a.patron, n, flags=re.IGNORECASE):
                return a.clave_538
    n = re.sub(r'\([^)]*\)', '', n)                        # (R), (D), (Fox News)
    n = n.split('/')[0]
    return re.sub(r'[^a-z]', '', n.lower())[:14] or 'desconocida'


def _aplanar_columnas(t: pd.DataFrame) -> pd.DataFrame:
    if isinstance(t.columns, pd.MultiIndex):
        cols = []
        for tup in t.columns:
            vals = [limpiar(x) for x in tup if limpiar(x) and not limpiar(x).lower().startswith('unnamed')]
            dedup = []
            for v in vals:
                if v not in dedup:
                    dedup.append(v)
            cols.append(' '.join(dedup))
        t = t.copy(); t.columns = cols
    else:
        t = t.copy(); t.columns = [limpiar(c) for c in t.columns]
    return t


def _buscar(cols, *claves):
    for c in cols:
        lc = c.lower()
        if any(k in lc for k in claves):
            return c
    return None


def _columna_firma(t: pd.DataFrame, cols):
    """270toWin usa 'Source' con colspan=2: la 1ª columna es el logo (vacía) y el nombre va en 'Source.1'.
    Entre las columnas tipo source/pollster se elige la que tiene más texto no vacío."""
    cands = [c for c in cols if any(k in c.lower() for k in ('source', 'pollster'))]
    if not cands:
        return None
    llenas = {c: t[c].map(lambda v: bool(limpiar(v)) and not re.search(r'average of', limpiar(v), re.I)).sum() for c in cands}
    return max(cands, key=lambda c: llenas[c])


# ----------------------------------------------------------------------------------- parsers
def parse_tabla_wikipedia(html: str, cand_d: str, cand_r: str, anio: int, alias=None) -> pd.DataFrame:
    """Tablas de encuestas con columnas de AMBOS candidatos (descarta hipotéticas con otros D/R y agregadores)."""
    try:
        tablas = pd.read_html(StringIO(html))
    except ValueError:
        return pd.DataFrame(columns=COLUMNAS)
    filas = []
    for t in tablas:
        t = _aplanar_columnas(t)
        cols = list(t.columns)
        cd = next((c for c in cols if cand_d.lower() in c.lower()), None)
        cr = next((c for c in cols if cand_r.lower() in c.lower()), None)
        fuente = _buscar(cols, 'poll source', 'pollster')
        fechas = _buscar(cols, 'date')
        muestra = _buscar(cols, 'sample')
        if not (cd and cr and fuente and fechas and muestra) or _buscar(cols, 'aggregat', 'updated'):
            continue
        otros_cand = [c for c in cols if c not in (cd, cr) and re.search(r'\((D|R)\)', c)]
        if otros_cand:                                   # careo hipotético con otro demócrata/republicano
            continue
        terceros = [c for c in cols if c not in (cd, cr) and re.search(r'\((L|I|G|C)\)', c)]
        c_otro, c_ind = _buscar(cols, 'other'), _buscar(cols, 'undecided')
        for _, r in t.iterrows():
            D, R = a_numero(r[cd]), a_numero(r[cr])
            if np.isnan(D) or np.isnan(R) or D <= 0 or R <= 0:
                continue
            ini, fin = parse_fechas(r[fechas], anio)
            n, pop = parse_muestra(r[muestra])
            if fin is None:
                continue
            # «—» = la encuesta no reporta terceros: NaN, no 0 % (revisión del 22-oct: no reportado ≠ 0)
            vals = [a_numero(r[c]) for c in terceros] + ([a_numero(r[c_otro])] if c_otro else [])
            otros = float(np.nansum(vals)) if any(np.isfinite(v) for v in vals) else np.nan
            filas.append({'pollster': limpiar(r[fuente]), 'inicio': ini, 'fin': fin, 'n': n, 'pop': pop or 'LV',
                          'D': D, 'R': R, 'otros': otros,
                          'indecisos': a_numero(r[c_ind]) if c_ind else np.nan, 'origen': 'wikipedia'})
    df = pd.DataFrame(filas, columns=[c for c in COLUMNAS if c not in ('clave_538', 'tipo_pregunta', 'fuente', 'nota')])
    return _completar(df, alias)


def parse_tabla_270(html: str, cand_d: str, cand_r: str, anio: int, alias=None) -> pd.DataFrame:
    try:
        tablas = pd.read_html(StringIO(html))
    except ValueError:
        return pd.DataFrame(columns=COLUMNAS)
    filas = []
    for t in tablas:
        t = _aplanar_columnas(t)
        cols = list(t.columns)
        cd = next((c for c in cols if cand_d.lower() in c.lower()), None)
        cr = next((c for c in cols if cand_r.lower() in c.lower()), None)
        fuente = _columna_firma(t, cols)
        fecha = _buscar(cols, 'date')
        if not (cd and cr and fuente and fecha):
            continue
        muestra = _buscar(cols, 'sample')
        c_otro = _buscar(cols, 'other', 'undecided')
        for _, r in t.iterrows():
            D, R = a_numero(r[cd]), a_numero(r[cr])
            if np.isnan(D) or np.isnan(R) or D <= 0 or R <= 0:
                continue
            ini, fin = parse_fechas(r[fecha], anio)
            if fin is None:
                continue
            firma = limpiar(r[fuente])
            if not firma or re.search(r'average of', firma, re.I):
                continue                                   # sin firma no se puede deduplicar ni corregir casa
            texto_fila = ' '.join(limpiar(x) for x in r.values)
            n, pop = parse_muestra(r[muestra]) if muestra else (np.nan, None)
            pop = pop or next((p for p in ('LV', 'RV') if re.search(rf'\b{p}\b', texto_fila)), 'LV')
            filas.append({'pollster': firma, 'inicio': ini, 'fin': fin, 'n': n, 'pop': pop, 'D': D, 'R': R,
                          'otros': np.nan, 'indecisos': a_numero(r[c_otro]) if c_otro else np.nan, 'origen': '270towin'})
    df = pd.DataFrame(filas, columns=[c for c in COLUMNAS if c not in ('clave_538', 'tipo_pregunta', 'fuente', 'nota')])
    return _completar(df, alias)


def _completar(df: pd.DataFrame, alias) -> pd.DataFrame:
    df = df.copy()
    if df.empty:
        return pd.DataFrame(columns=COLUMNAS)
    df['clave_538'] = [clave_firma(p, alias) for p in df.pollster]
    df['n'] = pd.to_numeric(df.n, errors='coerce').fillna(600)
    df['tipo_pregunta'] = np.where((df.D + df.R) >= 99.5, 'reasignacion', 'general')
    df['fuente'] = df.origen
    df['nota'] = ''
    df['inicio'] = df.inicio.fillna(df.fin)
    return df[COLUMNAS]


# ----------------------------------------------------------------------------------- selección
def elegir_versiones(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    d = df.copy()
    d['_pop'] = d['pop'].map(RANGO_POP).fillna(3)
    d['_ind'] = d.indecisos.fillna(-1)
    d = d.sort_values(['clave_538', 'fin', '_pop', 'n', '_ind'], ascending=[True, True, True, False, False])
    elegidas = d.groupby(['clave_538', 'fin'], as_index=False).head(1)
    descartes = len(d) - len(elegidas)
    if descartes:
        log.info('Versiones alternativas descartadas (RV/leaners/reasignadas): %d', descartes)
    return elegidas.drop(columns=['_pop', '_ind']).reset_index(drop=True)


