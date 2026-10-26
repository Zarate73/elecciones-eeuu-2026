"""Encuestas EN VIVO para California: Wikipedia (API MediaWiki) y 270toWin.

Los parsers son los mismos de Georgia (georgia/produccion/ga_pronostico/encuestas.py), probados con las
páginas reales. Flujo:
  1. Descarga cada fuente; si falla, usa su última copia en caché y lo reporta.
  2. Una versión por encuesta (misma firma y fecha): LV > RV > A, luego mayor n, luego más indecisos.
  3. Combina con la base verificada (Excel local o data/encuestas_verificadas.csv) sin duplicar:
     prioridad Wikipedia (fechas de campo exactas) > base verificada > 270toWin (fecha de publicación).
     Identidad: familia de encuestadora + periodo de campo (identidad.py; auditoría T3 del 26-oct).
  4. Se descartan las de la primaria (multicandidato) por fecha, igual que con el Excel.
  5. Filas que no son encuestas de la elección general (data/encuestas_excluidas.csv) se aíslan ANTES de combinar y se
     escriben en salidas/encuestas_excluidas.csv: Berkeley IGS 29-may 25–21 de 270toWin es la primaria del 2-jun.
"""
from __future__ import annotations

import logging
import re
from datetime import date, timedelta
from io import StringIO

import numpy as np
import pandas as pd

from .encuestas import Encuesta, crear_encuesta, simplificar
from .red import get_json, get_text

from . import identidad
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
            otros = sum(np.nan_to_num(a_numero(r[c])) for c in terceros) + (np.nan_to_num(a_numero(r[c_otro])) if c_otro else 0)
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




def elegir_versiones(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    d = df.copy()
    d['_pop'] = d['pop'].map(RANGO_POP).fillna(3)
    d['_ind'] = d.indecisos.fillna(-1)
    d = d.sort_values(['clave_538', 'fin', '_pop', 'n', '_ind'], ascending=[True, True, True, False, False])
    return d.groupby(['clave_538', 'fin'], as_index=False).head(1).drop(columns=['_pop', '_ind']).reset_index(drop=True)


# ----------------------------------------------------------------------------------- California
def _a_encuestas(df: pd.DataFrame, fecha_primaria: date) -> list[Encuesta]:
    out = []
    for r in df.itertuples():
        otro = max(100.0 - r.D - r.R, 0.0)
        rango = r.origen == 'wikipedia' and r.inicio is not None
        try:
            e = crear_encuesta(r.pollster, f'{r.inicio}–{r.fin}' if rango else f'publicada {r.fin}',
                               r.D, r.R, otro, fecha_primaria, inicio=r.inicio or r.fin, fin=r.fin,
                               rango=rango, origen=r.origen)
        except ValueError as exc:
            log.warning('Encuesta web descartada: %s (%s)', r.pollster, exc)
            continue
        out.append(e)
    return out


def _registro(e: Encuesta) -> dict:
    """Encuesta → registro de identidad.py. Sin intervalo conocido (270toWin) la fecha es puntual (publicación)."""
    ini = e.inicio if e.intervalo_conocido else e.fin
    return {'clave': e.familia, 'pollster': e.encuestadora, 'inicio': ini, 'fin': e.fin, 'n': float('nan'),
            'pop': None, 'D': e.becerra, 'R': e.hilton, 'origen': e.origen, '_obj': e}


def combinar(*fuentes: list[Encuesta]) -> list[Encuesta]:
    """Une fuentes en orden de prioridad sin duplicar ni fundir olas distintas (identidad.py: periodo de campo, o fecha
    de publicación coherente con el cierre; auditoría T3 del 26-oct). Antes: misma familia con fin a ≤ 7 días o mismas
    cifras a ≤ 21 días. La encuesta de mayor prioridad se conserva tal cual."""
    base, dec = identidad.combinar_registros([[_registro(e) for e in f] for f in fuentes if f], fusionar_campos=False)
    for d_ in dec:
        log.info('Identidad %s (%s): %s | %s', d_['decision'], d_['razon'], d_['conservada'], d_['nueva'])
    return sorted((b['_obj'] for b in base), key=lambda e: e.fin, reverse=True)


def _con_cache(cfg, nombre: str, funcion):
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
            for c in ('inicio', 'fin'):
                df[c] = pd.to_datetime(df[c]).dt.date
            sin_firma = df.pollster.isna() | (df.pollster.astype(str).str.strip() == '')
            if sin_firma.any():                      # caché de una versión anterior del parser
                log.warning('Encuestas %s: %d filas de caché sin encuestadora descartadas', nombre, int(sin_firma.sum()))
                df = df[~sin_firma].reset_index(drop=True)
            log.warning('Encuestas %s: uso caché (%s)', nombre, err)
            return df, f'cache ({err})'
        log.warning('Encuestas %s: sin datos ni caché (%s)', nombre, err)
        return pd.DataFrame(columns=COLUMNAS), f'no_disponible ({err})'


def aislar_excluidas(df: pd.DataFrame, nombre: str, cfg) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separa las filas listadas en data/encuestas_excluidas.csv (coincidencia exacta: origen, clave_538, fin, D, R)."""
    txt = str(cfg.rutas.get('encuestas_excluidas', '') or '').strip()
    vacio = df.iloc[0:0].assign(razon='')
    if not txt or df.empty or not cfg.ruta('encuestas_excluidas').exists():
        return df, vacio
    x = pd.read_csv(cfg.ruta('encuestas_excluidas'), comment='#')
    x = x[x.origen == nombre]
    if x.empty:
        return df, vacio
    fin = pd.to_datetime(df.fin).dt.date
    m = pd.Series(False, index=df.index)
    razon = pd.Series('', index=df.index, dtype=object)
    for r in x.itertuples():
        k = ((df.clave_538 == r.clave_538) & (fin == pd.Timestamp(r.fin).date())
             & ((df.D - float(r.D)).abs() < 0.01) & ((df.R - float(r.R)).abs() < 0.01))
        m |= k
        razon[k] = r.razon
    if m.any():
        for r in df[m].itertuples():
            log.warning('Encuesta aislada (%s): %s %s %g–%g · %s', nombre, r.pollster, r.fin, r.D, r.R, razon[r.Index])
    return df[~m].reset_index(drop=True), df[m].assign(razon=razon[m]).reset_index(drop=True)


def obtener_web(cfg) -> tuple[dict[str, list[Encuesta]], dict[str, str]]:
    """Encuestas de Wikipedia y 270toWin como objetos Encuesta (sin filtrar por corte)."""
    f, e = cfg.fuentes, cfg.eleccion
    anio = cfg.dia_eleccion.year

    def _wiki():
        js = get_json(f.wikipedia_api, params={'action': 'parse', 'page': f.wikipedia_pagina, 'prop': 'text',
                                               'format': 'json', 'formatversion': 2, 'redirects': 1},
                      offline=cfg.offline, timeout=f.timeout_http_s)
        tx = js['parse']['text']
        return elegir_versiones(parse_tabla_wikipedia(tx['*'] if isinstance(tx, dict) else tx,
                                                      e.candidato_d, e.candidato_r, anio))

    def _t270():
        html = get_text(f.t270_url, offline=cfg.offline, timeout=f.timeout_http_s)
        return elegir_versiones(parse_tabla_270(html, e.candidato_d, e.candidato_r, anio))

    estados, salida, aisladas = {}, {}, []
    for nombre, fn in (('wikipedia', _wiki), ('270towin', _t270)):
        df, estados[f'encuestas_{nombre}'] = _con_cache(cfg, nombre, fn)
        df, fuera = aislar_excluidas(df, nombre, cfg)
        if len(fuera):
            aisladas.append(fuera)
        salida[nombre] = _a_encuestas(df, cfg.fecha_primaria) if not df.empty else []
    ruta = cfg.dir_salidas / 'encuestas_excluidas.csv'
    if aisladas:
        pd.concat(aisladas, ignore_index=True).to_csv(ruta, index=False, encoding='utf-8-sig')
    elif ruta.exists():
        ruta.unlink()
    return salida, estados
