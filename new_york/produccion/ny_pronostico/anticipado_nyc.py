"""Voto anticipado en persona de la Ciudad de Nueva York: «Early Voting Check-Ins» de la Junta Electoral de NYC (vote.nyc).

civicAPI no publica Nueva York (404) y la Junta Electoral del estado bloquea las consultas automáticas (403). La Junta de
NYC publica cada noche los check-ins acumulados por condado (borough): solo la ciudad (poco más de un tercio del voto estatal), solo voto
en persona, sin partido. SOLO DIAGNÓSTICO: no entra al pronóstico.

Formato de la página (texto):
    October 25, 2026 - Day 2
    Manhattan - 46,314
    ...
    *As of Close of Polls – Unofficial and Cumulative 165,143
Cada corrida agrega una fila a salidas/nyc_voto_anticipado_historial.csv.
"""
from __future__ import annotations

import html as _html
import logging
import re
from datetime import datetime

import pandas as pd

from .red import get_text

log = logging.getLogger(__name__)

BOROUGHS = ('Manhattan', 'Bronx', 'Brooklyn', 'Queens', 'Staten Island')
_DIA = re.compile(r'([A-Z][a-z]+ \d{1,2}, \d{4})\s*-\s*Day\s*(\d+)')
_BOR = re.compile(r'(Manhattan|Bronx|Brooklyn|Queens|Staten Island)\s*[-–]\s*([\d,]+)')
_TOT = re.compile(r'(?:Cumulative|Close of Polls)\s*([\d,]{4,})')


def _texto(h: str) -> str:
    t = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', h, flags=re.S | re.I)
    t = _html.unescape(re.sub(r'<[^>]+>', ' ', t))
    return re.sub(r'\s+', ' ', t)


def parse_checkins(h: str, eleccion: str | None = None) -> pd.DataFrame:
    """Una fila por día publicado: fecha, día, check-ins acumulados por borough y total. Si la página trae más de una
    elección, `eleccion` (p. ej. 'General Election 2026') limita al bloque de esa elección."""
    t = _texto(h)
    if eleccion and eleccion in t:
        t = t[t.index(eleccion):]
        sig = re.search(r'(General|Primary|Special) Election \d{4}', t[len(eleccion):])
        if sig:
            t = t[:len(eleccion) + sig.start()]
    marcas = list(_DIA.finditer(t))
    filas = []
    for i, mk in enumerate(marcas):
        bloque = t[mk.end(): marcas[i + 1].start() if i + 1 < len(marcas) else len(t)]
        bor = {b: int(v.replace(',', '')) for b, v in _BOR.findall(bloque)}
        if set(bor) != set(BOROUGHS):
            continue
        tot = _TOT.search(bloque)
        filas.append({'fecha': datetime.strptime(mk.group(1), '%B %d, %Y').date(), 'dia': int(mk.group(2)), **bor,
                      'total': sum(bor.values()), 'total_publicado': int(tot.group(1).replace(',', '')) if tot else None})
    d = pd.DataFrame(filas)
    if d.empty:
        raise ValueError('sin bloques de check-ins por borough en la página')
    return d.sort_values('fecha').drop_duplicates('fecha', keep='last').reset_index(drop=True)


def obtener_nyc(cfg) -> dict:
    f = cfg.fuentes
    url = f.get('nyc_voto_anticipado_url')
    if not url:
        return {'disponible': False, 'estado': 'no_configurado'}
    cache = cfg.dir_cache / 'nyc_voto_anticipado.csv'
    try:
        d = parse_checkins(get_text(url, offline=cfg.offline, timeout=f.timeout_http_s), f.get('nyc_eleccion'))
        d = d[pd.to_datetime(d.fecha) <= pd.Timestamp(cfg.corte)]
        if d.empty:
            raise ValueError(f'sin días publicados hasta el corte {cfg.corte}')
        d.to_csv(cache, index=False)
        estado = 'en_vivo'
    except Exception as exc:                                # nunca se presenta un dato guardado como si fuera en vivo
        err = f'{type(exc).__name__}: {str(exc)[:120]}'
        if not cache.exists():
            log.warning('Voto anticipado de NYC no disponible: %s', err)
            return {'disponible': False, 'estado': f'no_disponible ({err})'}
        d = pd.read_csv(cache, parse_dates=['fecha'])
        d['fecha'] = d.fecha.dt.date
        d = d[pd.to_datetime(d.fecha) <= pd.Timestamp(cfg.corte)]
        if d.empty:
            return {'disponible': False, 'estado': f'no_disponible ({err})'}
        estado = f'cache ({err})'
    u = d.iloc[-1]
    tot = int(u.total)
    cond = pd.DataFrame({'condado': list(BOROUGHS), 'emitidos': [int(u[b]) for b in BOROUGHS]})
    cond['pct'] = 100 * cond.emitidos / tot
    principal = cond.sort_values('emitidos', ascending=False).iloc[0]
    if u.total_publicado and int(u.total_publicado) != tot:
        log.warning('NYC: la suma por borough (%d) no coincide con el total publicado (%s)', tot, u.total_publicado)
    res = {'disponible': True, 'estado': estado, 'tipo': 'nyc_checkins', 'por_partido': False, 'tiene_en_persona': True,
           'ambito': 'Ciudad de Nueva York (5 condados)', 'fecha': str(u.fecha), 'dia': int(u.dia), 'emitidos': tot,
           'en_persona': tot, 'por_correo': None, 'total_publicado': None if pd.isna(u.total_publicado) else int(u.total_publicado),
           'condado_principal': principal.condado, 'condado_principal_pct': float(principal.pct),
           'condados': cond, 'condados_lista': cond.round(2).to_dict('records'), 'serie': d[['fecha', 'dia', 'total']].to_dict('records'),
           'uso': 'diagnóstico; no entra al pronóstico',
           'fuente': 'Junta Electoral de la Ciudad de Nueva York (vote.nyc), check-ins de voto anticipado, no oficiales'}
    hist = cfg.dir_salidas / 'nyc_voto_anticipado_historial.csv'
    h = pd.read_csv(hist) if hist.exists() else pd.DataFrame()
    fila = pd.DataFrame([{'fecha': res['fecha'], 'dia': res['dia'], 'emitidos': tot,
                          **{b: int(u[b]) for b in BOROUGHS}}])
    if len(h):
        h = h[h.fecha.astype(str) != res['fecha']]
    pd.concat([h, fila], ignore_index=True).sort_values('fecha').to_csv(hist, index=False)
    return res
