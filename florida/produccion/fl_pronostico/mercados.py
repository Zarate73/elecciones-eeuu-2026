"""Mercados de predicción en vivo: Kalshi y Polymarket (ganador), y Polymarket por rangos de margen.

Kalshi y Polymarket NO son el mismo precio (Florida: correlación de niveles 0.86 pero de cambios diarios 0.20,
diferencia media 2.2 pp; Arizona: 0.16 y 3.3 pp), así que se promedian. Precio = punto medio bid/ask si el diferencial es ≤ 0.10; si no, último precio.
Probabilidad D normalizada: D / (D + R). Cada consulta se guarda; si una API falla se usa el último precio
guardado mientras tenga ≤ mercado_max_dias_antiguedad días. Un mercado sin precio usable sale de la mezcla.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from .red import get_json

log = logging.getLogger(__name__)


def _f(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return float('nan')


# ======================================================================================== Kalshi
def _precio_kalshi(m: dict, base: str) -> float:
    if m.get(f'{base}_dollars') not in (None, ''):
        return _f(m[f'{base}_dollars'])
    if m.get(base) is not None:
        return _f(m[base]) / 100
    return float('nan')


def precio_kalshi(m: dict) -> float:
    b, a = _precio_kalshi(m, 'yes_bid'), _precio_kalshi(m, 'yes_ask')
    if np.isfinite(b) and np.isfinite(a) and 0 < b <= a < 1 and a - b <= 0.10:
        return (a + b) / 2
    return _precio_kalshi(m, 'last_price')


def kalshi_vivo(cfg) -> tuple[float, float]:
    f = cfg.fuentes
    js = get_json(f'{f.kalshi_api}/markets', params={'event_ticker': f.kalshi_evento},
                  offline=cfg.offline, timeout=f.timeout_http_s)
    ms = js.get('markets') or (js.get('event') or {}).get('markets') or []
    mk = {m['ticker']: m for m in ms}
    if f.kalshi_ticker_d not in mk or f.kalshi_ticker_r not in mk:
        raise KeyError(f'Kalshi: faltan {f.kalshi_ticker_d}/{f.kalshi_ticker_r} en {f.kalshi_evento}')
    return precio_kalshi(mk[f.kalshi_ticker_d]), precio_kalshi(mk[f.kalshi_ticker_r])


# ==================================================================================== Polymarket
def _evento_poly(cfg, slug: str) -> dict:
    f = cfg.fuentes
    js = get_json(f'{f.polymarket_api}/events', params={'slug': slug}, offline=cfg.offline, timeout=f.timeout_http_s)
    evs = js if isinstance(js, list) else js.get('events', [])
    if not evs:
        raise LookupError(f'Polymarket: evento {slug} no encontrado')
    return evs[0]


def precio_poly(m: dict) -> float:
    b, a = _f(m.get('bestBid')), _f(m.get('bestAsk'))
    if np.isfinite(b) and np.isfinite(a) and 0 < b <= a < 1 and a - b <= 0.10:
        return (a + b) / 2
    op = m.get('outcomePrices')
    op = json.loads(op) if isinstance(op, str) else op
    if op:
        return _f(op[0])
    return _f(m.get('lastTradePrice'))


def ganador_poly(ev: dict) -> tuple[float, float]:
    d = r = None
    for m in ev.get('markets', []):
        if m.get('closed'):
            continue
        q = (m.get('question') or '').lower()
        if re.search(r'\bdemocrat', q):
            d = precio_poly(m)
        elif re.search(r'\brepublican', q):
            r = precio_poly(m)
    if d is None or r is None:
        raise LookupError('Polymarket: no se encontraron los mercados demócrata y republicano')
    return d, r


def rangos_poly(ev: dict) -> pd.DataFrame:
    """Mercado de margen por rangos -> tabla (desde, hasta, p, p_norm) en margen D−R (pp)."""
    filas = []
    for m in ev.get('markets', []):
        q = m.get('question') or ''
        par = re.search(r'(Republican|Democratic) Party candidate win .*? by (\d+(?:\.\d+)?)%\s*(?:-|–|to)\s*(\d+(?:\.\d+)?)%', q)
        mas = re.search(r'(Republican|Democratic) Party candidate win .*? by (\d+(?:\.\d+)?)% or more', q)
        if par:
            lado, a, b = par.group(1), float(par.group(2)), float(par.group(3))
        elif mas:
            lado, a, b = mas.group(1), float(mas.group(2)), 30.0
        else:
            continue
        lo, hi = (a, b) if lado == 'Democratic' else (-b, -a)
        filas.append({'desde': lo, 'hasta': hi, 'p': precio_poly(m)})
    t = pd.DataFrame(filas).sort_values('desde').reset_index(drop=True)
    if len(t) < 4:
        raise LookupError('Polymarket: mercado de margen sin rangos reconocibles')
    t['p_norm'] = t.p / t.p.sum()
    return t


def resumen_rangos(t: pd.DataFrame) -> dict:
    medio = (t.desde + t.hasta) / 2
    media = float(np.sum(t.p_norm * medio))
    return {'margen_media': media, 'margen_sd': float(np.sqrt(np.sum(t.p_norm * (medio - media) ** 2))),
            'P_D': float(t[t.desde >= 0].p_norm.sum())}


# ==================================================================================== orquestación
def _snapshot(cfg, nombre: str, funcion, ahora: datetime) -> dict:
    """Consulta en vivo y guarda; si falla, último precio guardado (≤ corte)."""
    ruta = cfg.dir_cache / f'mercado_{nombre}.csv'
    try:
        p_d, p_r = funcion()
        if not (np.isfinite(p_d) and np.isfinite(p_r) and p_d + p_r > 0):
            raise ValueError(f'precios inválidos {p_d}, {p_r}')
        pd.DataFrame([{'consulta': ahora.isoformat(timespec='seconds'), 'fecha': ahora.date().isoformat(),
                       'p_d': p_d, 'p_r': p_r}]).to_csv(ruta, mode='a', header=not ruta.exists(), index=False)
        return _armar(cfg, p_d, p_r, ahora.date(), 'en_vivo')
    except Exception as exc:
        err = f'{type(exc).__name__}: {str(exc)[:140]}'
    if ruta.exists():
        s = pd.read_csv(ruta)
        s = s[pd.to_datetime(s.fecha).dt.date <= cfg.corte]
        if len(s):
            u = s.iloc[-1]
            return _armar(cfg, u.p_d, u.p_r, date.fromisoformat(str(u.fecha)), f'cache ({err})')
    log.warning('%s no disponible: %s', nombre, err)
    return {'usable': False, 'estado': f'no_disponible ({err})'}


def _armar(cfg, p_d, p_r, fecha: date, estado: str) -> dict:
    p_d, p_r = float(p_d), float(p_r)
    antig = (cfg.corte - fecha).days
    return {'p_d': p_d, 'p_r': p_r, 'p_D': p_d / (p_d + p_r), 'overround': p_d + p_r - 1, 'fecha': str(fecha),
            'antiguedad_dias': antig, 'estado': estado,
            'usable': bool(estado == 'en_vivo' or -1 <= antig <= cfg.fuentes.mercado_max_dias_antiguedad)}


def obtener_mercados(cfg) -> dict:
    f = cfg.fuentes
    ahora = datetime.now(ZoneInfo(cfg.eleccion.zona_horaria))
    k = _snapshot(cfg, 'kalshi', lambda: kalshi_vivo(cfg), ahora)
    p = _snapshot(cfg, 'polymarket', lambda: ganador_poly(_evento_poly(cfg, f.polymarket_evento_ganador)), ahora)
    usables = [m['p_D'] for m in (k, p) if m.get('usable')]
    res = {'kalshi': k, 'polymarket': p, 'n_usables': len(usables),
           'promedio_D': float(np.mean(usables)) if usables else None,
           'dif_pp': (100 * (k['p_D'] - p['p_D'])) if k.get('usable') and p.get('usable') else None}
    ruta = cfg.dir_cache / 'polymarket_rangos.csv'
    try:
        t = rangos_poly(_evento_poly(cfg, f.polymarket_evento_margen))
        t.assign(consulta=ahora.isoformat(timespec='seconds')).to_csv(ruta, index=False)
        res['rangos'] = {**resumen_rangos(t), 'estado': 'en_vivo', 'tabla': t}
    except Exception as exc:
        err = f'{type(exc).__name__}: {str(exc)[:120]}'
        if ruta.exists():
            t = pd.read_csv(ruta)
            res['rangos'] = {**resumen_rangos(t), 'estado': f'cache ({err})', 'tabla': t}
        else:
            res['rangos'] = {'estado': f'no_disponible ({err})'}
    return res
