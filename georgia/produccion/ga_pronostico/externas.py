"""Fuentes externas en vivo: Kalshi (mercado) y Civic Forge (voto anticipado, solo diagnóstico)."""
from __future__ import annotations

import json
import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from .red import get_json

log = logging.getLogger(__name__)


# ======================================================================================== Kalshi
def _precio(m: dict, base: str) -> float:
    if m.get(f'{base}_dollars') not in (None, ''):
        return float(m[f'{base}_dollars'])
    if m.get(base) is not None:
        return float(m[base]) / 100
    return float('nan')


def _mid(m: dict) -> float:
    b, a = _precio(m, 'yes_bid'), _precio(m, 'yes_ask')
    if np.isfinite(b) and np.isfinite(a) and 0 < b <= a < 1:
        return (a + b) / 2
    return _precio(m, 'last_price')


def obtener_kalshi(cfg) -> dict:
    f = cfg.fuentes
    snap = cfg.dir_cache / 'kalshi_snapshots.csv'
    ahora = datetime.now(ZoneInfo(cfg.eleccion.zona_horaria))
    try:
        js = get_json(f'{f.kalshi_api}/markets', params={'event_ticker': f.kalshi_evento},
                      offline=cfg.offline, timeout=f.timeout_http_s)
        mk = {m['ticker']: m for m in js.get('markets', [])}
        p_d, p_r = _mid(mk[f.kalshi_ticker_d]), _mid(mk[f.kalshi_ticker_r])
        pd.DataFrame([{'consulta': ahora.isoformat(timespec='seconds'), 'fecha': ahora.date().isoformat(),
                       'p_d': p_d, 'p_r': p_r}]).to_csv(snap, mode='a', header=not snap.exists(), index=False)
        return _armar(cfg, p_d, p_r, ahora.date(), 'en_vivo')
    except Exception as exc:
        error = f'{type(exc).__name__}: {str(exc)[:160]}'
    if snap.exists():
        s = pd.read_csv(snap)
        s = s[pd.to_datetime(s.fecha).dt.date <= cfg.corte]
        if len(s):
            u = s.iloc[-1]
            return _armar(cfg, u.p_d, u.p_r, date.fromisoformat(u.fecha), f'cache ({error})')
    log.warning('Kalshi no disponible: %s', error)
    return {'usable_en_mezcla': False, 'estado': f'no_disponible ({error})'}


def _armar(cfg, p_d, p_r, fecha, estado) -> dict:
    p_d, p_r = float(p_d), float(p_r)
    antig = (cfg.corte - fecha).days
    usable = bool(np.isfinite(p_d) and np.isfinite(p_r) and -1 <= antig <= cfg.fuentes.kalshi_max_dias_antiguedad)
    return {'p_d': p_d, 'p_r': p_r, 'p_d_normalizada': p_d / (p_d + p_r), 'overround': p_d + p_r - 1,
            'fecha': str(fecha), 'antiguedad_dias': antig, 'estado': estado, 'usable_en_mezcla': usable}


# =================================================================================== Civic Forge
def _filas(js: dict, clave: str) -> dict:
    return {r[clave]: float(r.get('accepted') or 0) for r in js.get('rows', []) if clave in r}


def obtener_anticipado(cfg) -> dict:
    """% por raza y edad de las boletas aceptadas, 2026 y años previos AL MISMO número de días antes de la
    elección (mode=matched). Diagnóstico: no entra al pronóstico (empeoró el RMSE en el backtest GA)."""
    f = cfg.fuentes
    ruta = cfg.dir_cache / 'civicforge_diagnostico.json'
    try:
        filas, meta = [], {}
        for grupo in ('race', 'age_range'):
            js = get_json(f'{f.civicforge_api}/crosstab', params={'groupBy': grupo, 'compact': 1},
                          offline=cfg.offline, timeout=f.timeout_http_s)
            meta = js.get('meta', meta)
            filas.append({'anio': cfg.dia_eleccion.year, 'grupo': grupo, 'fecha': meta.get('dataThrough'),
                          'dias': cfg.dias_a_eleccion, **_filas(js, grupo)})
            for anio in f.civicforge_anios:
                h = get_json(f'{f.civicforge_api}/history/{anio}/crosstab',
                             params={'groupBy': grupo, 'mode': 'matched', 'compact': 1},
                             offline=cfg.offline, timeout=f.timeout_http_s)
                hist = h.get('history', {})
                filas.append({'anio': anio, 'grupo': grupo, 'fecha': hist.get('matchedTo'),
                              'dias': hist.get('daysToElection'), **_filas(h, grupo)})
        tabla = _resumir(pd.DataFrame(filas))
        ruta.write_text(json.dumps({'meta': meta, 'tabla': tabla.to_dict('records')}, default=str), encoding='utf-8')
        estado = 'en_vivo'
    except Exception as exc:
        err = f'{type(exc).__name__}: {str(exc)[:160]}'
        if not ruta.exists():
            log.warning('Civic Forge no disponible: %s', err)
            return {'estado': f'no_disponible ({err})', 'tabla': pd.DataFrame()}
        c = json.loads(ruta.read_text(encoding='utf-8'))
        meta, tabla, estado = c['meta'], pd.DataFrame(c['tabla']), f'cache ({err})'
    act = tabla[tabla.anio == cfg.dia_eleccion.year]
    ref = tabla[tabla.anio == 2022]
    delta = {}
    if len(act) and len(ref):
        for c in ('pct_negro', 'pct_65mas', 'boletas'):
            if c in act and c in ref:
                delta[c] = float(act[c].iloc[0] - ref[c].iloc[0])
    return {'estado': estado, 'fecha_datos': meta.get('dataThrough'), 'tabla': tabla, 'delta_vs_2022': delta,
            'uso': 'diagnóstico; no entra al pronóstico'}


def _resumir(df: pd.DataFrame) -> pd.DataFrame:
    raza = df[df.grupo == 'race'].set_index('anio')
    edad = df[df.grupo == 'age_range'].set_index('anio')
    out = pd.DataFrame(index=sorted(set(raza.index) | set(edad.index)))
    num = lambda t: t.drop(columns=['grupo', 'fecha', 'dias'], errors='ignore').apply(pd.to_numeric, errors='coerce')
    if len(raza):
        r = num(raza)
        out['boletas'] = r.sum(axis=1)
        out['pct_negro'] = 100 * r.get('BLACK', np.nan) / r.sum(axis=1)
        out['pct_blanco'] = 100 * r.get('WHITE', np.nan) / r.sum(axis=1)
        out['fecha_comparable'] = raza['fecha']
        out['dias_eleccion'] = raza['dias']
    if len(edad):
        e = num(edad)
        out['pct_18_34'] = 100 * e.get('18-34', np.nan) / e.sum(axis=1)
        out['pct_65mas'] = 100 * e.get('65+', np.nan) / e.sum(axis=1)
    return out.reset_index().rename(columns={'index': 'anio'})
