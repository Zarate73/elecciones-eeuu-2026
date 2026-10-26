"""Encuestas EN VIVO: Wikipedia (API MediaWiki) + 270toWin + encuestas propias G-Ratings (Excel).

Flujo por carrera (gobernador / senado):
  1. Descarga cada fuente; si falla, usa su última copia en caché y lo reporta.
  2. Normaliza: fechas de campo, muestra y universo (LV/RV/A), % D y % R, clave de encuestadora (FiveThirtyEight).
  3. Elige UNA versión por encuesta (misma firma y fecha): LV > RV > A, luego mayor n, luego más indecisos
     (versión sin 'leaners' ni reasignación).
  4. Combina fuentes sin duplicar ni fundir olas distintas (identidad.py: firma + periodo de campo; auditoría T3
     del 26-oct): prioridad Wikipedia > propias > 270toWin.
  5. Aplica data/ajustes_encuestas.csv (correcciones documentadas: reemplazar / excluir / agregar).
  6. Filtra por fecha (nominación <= fin <= corte) y valida (errores detienen la corrida).
"""
from __future__ import annotations

import logging
import re
from datetime import date
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd

from . import identidad
from .red import get_json, get_text

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


def parse_gratings(ruta: Path, cfg) -> dict[str, pd.DataFrame]:
    """Excel G-Ratings (hojas METHODOLOGY + estado). Devuelve {'gob': df, 'sen': df}."""
    x = pd.read_excel(ruta, sheet_name=None, header=None)
    texto_met = ' '.join(limpiar(v) for h, t in x.items() if 'METHOD' in h.upper() for v in t.values.ravel() if limpiar(v))
    m = re.search(r'between\s+([A-Za-z]+\.?\s+\d{1,2})\s+and\s+([A-Za-z]+\.?\s+\d{1,2}),?\s*(\d{4})', texto_met)
    if not m:
        raise ValueError(f'{ruta.name}: no se encontraron fechas de campo en METHODOLOGY')
    ini, _ = parse_fechas(f'{m.group(1)}, {m.group(3)}', int(m.group(3)))
    fin, _ = parse_fechas(f'{m.group(2)}, {m.group(3)}', int(m.group(3)))
    nm = re.search(r'(\d[\d,]*)\s+complete', texto_met)
    n = float(nm.group(1).replace(',', '')) if nm else np.nan
    pop = 'RV' if re.search(r'registered', texto_met, re.I) else 'A'
    out = {}
    hoja = next(t for h, t in x.items() if 'METHOD' not in h.upper())
    filas = [(limpiar(r[0]), a_numero(r[1]) if len(r) > 1 else np.nan) for r in hoja.itertuples(index=False)]
    for carrera, (cd, cr, clave_q) in {'gob': (cfg.eleccion.candidato_d, cfg.eleccion.candidato_r, 'governor'),
                                       'sen': (cfg.senado.candidato_d, cfg.senado.candidato_r, 'senate')}.items():
        i0 = next((i for i, (t, _) in enumerate(filas) if clave_q in t.lower() and '?' in t), None)
        if i0 is None:
            continue
        bloque = filas[i0 + 1:i0 + 8]
        D = next((v for t, v in bloque if cd.lower() in t.lower()), np.nan)
        R = next((v for t, v in bloque if cr.lower() in t.lower()), np.nan)
        if np.isnan(D) or np.isnan(R):
            continue
        out[carrera] = _completar(pd.DataFrame([{'pollster': 'G-Ratings', 'inicio': ini, 'fin': fin, 'n': n,
                                                 'pop': pop, 'D': D, 'R': R, 'otros': np.nan,
                                                 'indecisos': 100 - D - R, 'origen': f'propia:{ruta.name}'}]), None)
    return out


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


def combinar(*fuentes: pd.DataFrame) -> pd.DataFrame:
    """Une fuentes en orden de prioridad; una fila de menor prioridad se descarta si es el MISMO estudio que una ya
    incluida (identidad.py: periodo de campo, o fecha de publicación de 270toWin coherente con el cierre). La fila de
    mayor prioridad se conserva tal cual. Las decisiones quedan en .attrs['decisiones']."""
    regs = []
    for f in fuentes:
        if f is None or f.empty:
            continue
        regs.append([dict(r, clave=r.get('clave_538'), _fila=r) for r in f.to_dict('records')])
    base, dec = identidad.combinar_registros(regs, fusionar_campos=False)
    out = pd.DataFrame([b['_fila'] for b in base]) if base else pd.DataFrame(columns=COLUMNAS)
    out.attrs['decisiones'] = dec
    for d_ in dec:
        log.info('Identidad %s (%s): %s | %s', d_['decision'], d_['razon'], d_['conservada'], d_['nueva'])
    return out.reset_index(drop=True)


def _coincidencia_ajuste(d: pd.DataFrame, a) -> pd.Series:
    """Fila (UNA, la más cercana) a la que se refiere un ajuste: misma clave y calendario compatible con su periodo de
    campo (solapado, o fecha de publicación de 270toWin 0–14 días después del cierre). Antes: todas las filas de la
    firma con fin a ±7 días, que podía tocar dos olas distintas."""
    m = pd.Series(False, index=d.index)
    ref = {'inicio': a.inicio if pd.notna(a.get('inicio')) else a.fin, 'fin': a.fin}
    mejor, mejor_d = None, None
    for i, r in d[d.clave_538 == a.clave_538].iterrows():
        cal, dist = identidad.calendario({'inicio': r.inicio, 'fin': r.fin}, ref)
        if cal in ('solapados', 'publicacion', 'puntuales') and (mejor_d is None or dist < mejor_d):
            mejor, mejor_d = i, dist
    if mejor is not None:
        m.loc[mejor] = True
    return m


def aplicar_ajustes(df: pd.DataFrame, ajustes: pd.DataFrame, carrera: str, alias=None) -> tuple[pd.DataFrame, list]:
    log_aj = []
    if ajustes is None or ajustes.empty:
        return df, log_aj
    d = df.copy()
    for _, a in ajustes[ajustes.carrera == carrera].iterrows():
        fin_ref = pd.Timestamp(a.fin)
        m = _coincidencia_ajuste(d, a) if len(d) else pd.Series([], dtype=bool)
        if a.accion == 'excluir':
            if m.any():
                d = d[~m]; log_aj.append(f'excluida {a.clave_538} {a.fin}: {a.motivo}')
        elif a.accion in ('reemplazar', 'agregar'):
            if a.accion == 'agregar' and m.any() and not (d.loc[m, 'origen'] == '270towin').all():
                continue                                 # ya llegó por Wikipedia / propia: manda la fuente en vivo
            # (si solo vino de 270toWin -fecha de publicación, cifras redondeadas- se usa la versión verificada)
            fila = {'pollster': a.pollster, 'clave_538': a.clave_538, 'inicio': pd.Timestamp(a.inicio).date(),
                    'fin': fin_ref.date(), 'n': float(a.n), 'pop': a['pop'], 'D': float(a.D), 'R': float(a.R),
                    'otros': np.nan, 'indecisos': 100 - float(a.D) - float(a.R), 'tipo_pregunta': a.tipo_pregunta,
                    'fuente': a.fuente, 'origen': f'ajuste:{a.accion}', 'nota': a.motivo}
            if a.accion == 'reemplazar' and not m.any():
                log_aj.append(f'AVISO: reemplazo sin coincidencia {a.clave_538} {a.fin} (se agrega)')
            d = pd.concat([d[~m] if m.any() else d, pd.DataFrame([fila])], ignore_index=True)
            log_aj.append(f'{a.accion} {a.clave_538} {a.fin}: {a.motivo}')
    return d.reset_index(drop=True), log_aj


def validar(df: pd.DataFrame) -> list[str]:
    err, avisos = [], []
    if df.empty:
        raise ValueError('No hay encuestas')
    if df[['pollster', 'clave_538', 'fin', 'D', 'R', 'n', 'pop', 'tipo_pregunta']].isna().any().any():
        err.append('campos obligatorios vacíos')
    if ((df.D + df.R) > 100.5).any() or (df.D < 0).any() or (df.R < 0).any():
        err.append(f'D+R > 100 o negativos: {df.loc[(df.D + df.R) > 100.5, "pollster"].tolist()}')
    if (pd.to_datetime(df.fin) < pd.to_datetime(df.inicio)).any():
        err.append('fin anterior a inicio')
    if set(df.tipo_pregunta) - TIPOS_PREGUNTA:
        err.append(f'tipo_pregunta inválido: {set(df.tipo_pregunta) - TIPOS_PREGUNTA}')
    if not df.clave_538.astype(str).str.fullmatch(r'[a-z]{1,14}').all():
        err.append('clave_538 inválida (minúsculas, máx. 14 letras)')
    if not df['pop'].isin(list(RANGO_POP)).all():
        err.append('pop debe ser LV, RV o A')
    dup = df[df.duplicated(['clave_538', 'inicio', 'fin'], keep=False)]
    if len(dup):
        err.append(f'duplicadas: {dup.pollster.tolist()}')
    if (df.n < 100).any():
        avisos.append(f'muestras < 100: {df.loc[df.n < 100, "pollster"].tolist()}')
    if err:
        raise ValueError('Encuestas con errores:\n - ' + '\n - '.join(err))
    return avisos


# ----------------------------------------------------------------------------------- orquestación
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


def obtener_encuestas(cfg, carrera: str = 'gob') -> dict:
    f = cfg.fuentes
    anio = cfg.dia_eleccion.year
    cd, cr = ((cfg.eleccion.candidato_d, cfg.eleccion.candidato_r) if carrera == 'gob'
              else (cfg.senado.candidato_d, cfg.senado.candidato_r))
    pagina = f.wikipedia_pagina_gob if carrera == 'gob' else f.wikipedia_pagina_sen
    url270 = f.t270_url_gob if carrera == 'gob' else f.t270_url_sen
    alias = pd.read_csv(cfg.dir_datos / 'alias_encuestadoras.csv')
    ajustes = pd.read_csv(cfg.dir_datos / 'ajustes_encuestas.csv')

    def _wiki():
        js = get_json(f.wikipedia_api, params={'action': 'parse', 'page': pagina, 'prop': 'text', 'format': 'json',
                                               'formatversion': 2, 'redirects': 1},
                      offline=cfg.offline, timeout=f.timeout_http_s)
        return parse_tabla_wikipedia(js['parse']['text'], cd, cr, anio, alias)

    def _t270():
        return parse_tabla_270(get_text(url270, offline=cfg.offline, timeout=f.timeout_http_s), cd, cr, anio, alias)

    estados = {}
    wiki, estados[f'wikipedia_{carrera}'] = _con_cache(cfg, f'{carrera}_wikipedia', _wiki)
    t270, estados[f'270towin_{carrera}'] = _con_cache(cfg, f'{carrera}_270towin', _t270)
    propias = []
    for ruta in cfg.rutas_encuestas_propias():
        if ruta.exists():
            try:
                g = parse_gratings(ruta, cfg).get(carrera)
                if g is not None:
                    propias.append(g)
                estados[f'propia_{ruta.name}'] = 'archivo'
            except Exception as exc:
                estados[f'propia_{ruta.name}'] = f'error ({exc})'
        else:
            estados[f'propia_{ruta.name}'] = 'no_encontrado'
    propias = pd.concat(propias, ignore_index=True) if propias else pd.DataFrame(columns=COLUMNAS)
    if wiki.empty and t270.empty and propias.empty:
        raise ValueError(f'ninguna fuente de encuestas disponible para {carrera} (ni en vivo, ni caché, ni propias); '
                         'los ajustes manuales por sí solos no bastan')
    df = combinar(elegir_versiones(wiki), elegir_versiones(propias), elegir_versiones(t270))
    df, log_aj = aplicar_ajustes(df, ajustes, carrera, alias)
    for c in ('inicio', 'fin'):
        df[c] = pd.to_datetime(df[c]).dt.date
    antes = len(df)
    df = df[(df.fin >= cfg.fecha_nominacion) & (df.fin <= cfg.corte)].sort_values('fin').reset_index(drop=True)
    avisos = validar(df)
    vivas = int(df.origen.isin(['wikipedia', '270towin']).sum())
    if not (wiki.empty and t270.empty) and vivas < f.min_encuestas_vivas:
        avisos.append(f'solo {vivas} encuestas en vivo (< {f.min_encuestas_vivas})')
    log.info('Encuestas %s: %d (wiki %d, 270 %d, propias %d) · fuera de fechas %d · ajustes %d',
             carrera, len(df), len(wiki), len(t270), len(propias), antes - len(df), len(log_aj))
    return {'encuestas': df, 'estados': estados, 'avisos': avisos, 'ajustes': log_aj}
