"""Mercados de predicción en vivo: Kalshi y Polymarket (ganador), y Polymarket por rangos de margen.

Kalshi y Polymarket NO son el mismo precio (en Nevada, Florida y Arizona los cambios diarios casi
no se correlacionan); se promedian en una sola señal. En North Carolina Kalshi (SENATENC-26) da a Cooper ~96.5 % y Polymarket ~97.5 % (27-oct)
(Kalshi solo lista D y R): la probabilidad comparable con el modelo es D / (D + R). Precio = punto medio bid/ask si el diferencial es ≤ 0.10; si no, último precio.
Probabilidad D normalizada: D / (D + R). Cada consulta se guarda; si una API falla se usa el último precio
guardado mientras tenga ≤ mercado_max_dias_antiguedad días. Un mercado sin precio usable sale de la mezcla.

Reconstrucción de un corte pasado (revisión OH-05): el precio de hoy es información posterior al corte. Se usa el precio
al CIERRE del día del corte (24:00 en la zona del estado): vela diaria de Kalshi (`.../candlesticks`, close) e historial
de Polymarket (`clob.polymarket.com/prices-history`, último punto ≤ cierre) para el ganador y para cada rango de margen.
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


def kalshi_independiente(cfg) -> float | None:
    """Precio del contrato del independiente en Kalshi (si config trae kalshi_ticker_i; Maine: Bennett). Solo diagnóstico; NC no tiene."""
    t = str(cfg.fuentes.get('kalshi_ticker_i', '') or '')
    if not t:
        return None
    js = get_json(f'{cfg.fuentes.kalshi_api}/markets', params={'event_ticker': cfg.fuentes.kalshi_evento},
                  offline=cfg.offline, timeout=cfg.fuentes.timeout_http_s)
    ms = {m['ticker']: m for m in (js.get('markets') or [])}
    return precio_kalshi(ms[t]) if t in ms else None


# ==================================================================================== precios al corte (reconstrucción)
def _cierre_corte(cfg) -> int:
    """Marca de tiempo (s) del fin del día del corte en la zona del estado."""
    z = ZoneInfo(cfg.eleccion.zona_horaria)
    return int(datetime(cfg.corte.year, cfg.corte.month, cfg.corte.day, tzinfo=z).timestamp()) + 86400


def kalshi_al_corte(cfg) -> tuple[float, float]:
    """Cierre de la última vela diaria de D y R que termina a más tardar al final del día del corte."""
    f = cfg.fuentes
    fin = _cierre_corte(cfg)
    serie = f.kalshi_evento.split('-')[0]
    out = []
    for t in (f.kalshi_ticker_d, f.kalshi_ticker_r):
        js = get_json(f'{f.kalshi_api}/series/{serie}/markets/{t}/candlesticks',
                      params={'start_ts': fin - 30 * 86400, 'end_ts': fin, 'period_interval': 1440},
                      offline=cfg.offline, timeout=f.timeout_http_s)
        cierre = lambda c: _f((c.get('price') or {}).get('close_dollars', (c.get('price') or {}).get('close')))
        velas = [c for c in js.get('candlesticks', []) if int(c['end_period_ts']) <= fin and np.isfinite(cierre(c))]
        if not velas:
            raise LookupError(f'Kalshi: sin velas de {t} hasta el {cfg.corte}')
        v = cierre(max(velas, key=lambda c: int(c['end_period_ts'])))
        out.append(v / 100 if v > 1 else v)
    return out[0], out[1]


def _historial_poly(cfg, token: str) -> float:
    f = cfg.fuentes
    fin = _cierre_corte(cfg)
    js = get_json(f.get('polymarket_clob', 'https://clob.polymarket.com') + '/prices-history',
                  params={'market': token, 'interval': 'max', 'fidelity': 1440}, offline=cfg.offline, timeout=f.timeout_http_s)
    pts = [x for x in js.get('history', []) if int(x['t']) <= fin]
    if not pts:
        raise LookupError(f'Polymarket: sin historial del token {token[:12]}… hasta el {cfg.corte}')
    return float(max(pts, key=lambda x: int(x['t']))['p'])


def evento_poly_al_corte(cfg, ev: dict) -> dict:
    """Copia del evento con el precio de cada mercado activo reemplazado por su precio al cierre del día del corte."""
    ev = json.loads(json.dumps(ev))
    for m in ev.get('markets', []):
        if m.get('closed') or m.get('active') is False:
            continue
        toks = m.get('clobTokenIds')
        toks = json.loads(toks) if isinstance(toks, str) else toks
        if not toks:
            m['active'] = False
            continue
        p = _historial_poly(cfg, toks[0])
        m['outcomePrices'] = json.dumps([str(p), str(1 - p)])
        for k in ('bestBid', 'bestAsk', 'lastTradePrice'):
            m.pop(k, None)
    return ev


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
    """Mercado de margen por rangos -> tabla (desde, hasta, p, p_norm, contrato) en margen D−R (pp).

    Reconoce tres tipos de contrato:
      - «<Partido> Party candidate win ... by X%–Y%»    → intervalo [X, Y] (con signo según el partido);
      - «<Partido> Party candidate win ... by X% or more» → intervalo abierto [X, ∞);
      - «Will the <Partido> Party candidate win ...?» sin rango → todo el lado de ese partido, (−∞, 0) o (0, ∞).
    El tercero existe en PA («Republican wins»): sin él, la partición solo tiene márgenes positivos y P(D) sale 1
    por construcción. Si hay un contrato «Will an Independent win…?» (Maine; NC no lo tiene): no tiene margen D−R, pero cuenta en el
    denominador de P(D). Se ignoran los contratos cerrados o inactivos (p. ej., «Person A», «a candidate not listed»).
    """
    filas = []
    for m in ev.get('markets', []):
        if m.get('closed') or m.get('active') is False:
            continue
        q = m.get('question') or ''
        par = re.search(r'(Republican|Democratic) Party candidate win .*? by (\d+(?:\.\d+)?)%\s*(?:-|–|to)\s*(\d+(?:\.\d+)?)%', q)
        mas = re.search(r'(Republican|Democratic) Party candidate win .*? by (\d+(?:\.\d+)?)% or more', q)
        lado_solo = re.search(r'(Republican|Democratic) Party candidate win [^?]*?election\?\s*$', q)
        indep = re.search(r'Will an Independent win', q)
        if indep:                       # gana un independiente → fuera del eje D−R, cuenta en P(D)
            filas.append({'desde': np.nan, 'hasta': np.nan, 'p': precio_poly(m), 'contrato': 'independiente'})
            continue
        if par:
            lado, a, b, tipo = par.group(1), float(par.group(2)), float(par.group(3)), 'rango'
        elif mas:
            lado, a, b, tipo = mas.group(1), float(mas.group(2)), np.inf, 'abierto'
        elif lado_solo and ' by ' not in q:
            lado, a, b, tipo = lado_solo.group(1), 0.0, np.inf, 'lado_completo'
        else:
            continue
        lo, hi = (a, b) if lado == 'Democratic' else (-b, 0.0 if a == 0 else -a)
        filas.append({'desde': lo, 'hasta': hi, 'p': precio_poly(m), 'contrato': tipo})
    t = pd.DataFrame(filas)
    if len(t) < 4:
        raise LookupError('Polymarket: mercado de margen sin rangos reconocibles')
    t = t.sort_values('desde', na_position='last').reset_index(drop=True)
    t['p_norm'] = t.p / t.p.sum()
    return t


def _particion_completa(t: pd.DataFrame) -> bool:
    """Los intervalos cubren toda la recta (−∞ a ∞) sin huecos ni traslapes."""
    d, h = t.desde.to_numpy(float), t.hasta.to_numpy(float)
    return bool(np.isneginf(d[0]) and np.isposinf(h[-1]) and np.allclose(h[:-1], d[1:]))


def _ajuste_normal(t: pd.DataFrame) -> tuple[float, float]:
    """Normal ajustada a los precios normalizados por máxima verosimilitud con censura por intervalos.

    max_{μ,σ} Σ p̃_i · log[Φ((hasta_i − μ)/σ) − Φ((desde_i − μ)/σ)]
    Usa los intervalos abiertos tal como son (sin inventar cotas para «X % o más» ni un margen medio del lado perdedor).
    """
    from scipy.optimize import minimize
    from scipy.stats import norm
    p = t.p_norm.to_numpy(float)
    lo, hi = t.desde.to_numpy(float), t.hasta.to_numpy(float)
    medio = np.where(np.isfinite(lo) & np.isfinite(hi), (lo + hi) / 2, np.where(np.isfinite(lo), lo + 5, hi - 5))
    m0 = float(np.sum(p * medio))

    def nll(th):
        mu, sd = th[0], np.exp(th[1])
        q = np.clip(norm.cdf(hi, mu, sd) - norm.cdf(lo, mu, sd), 1e-12, 1.0)
        return -float(np.sum(p * np.log(q)))

    r = minimize(nll, [m0, np.log(8.0)], method='Nelder-Mead', options={'xatol': 1e-4, 'fatol': 1e-8, 'maxiter': 2000})
    return float(r.x[0]), float(np.exp(r.x[1]))


def resumen_rangos(t: pd.DataFrame) -> dict:
    """Resumen del mercado por rangos.

    - suma_precios: Σ p antes de normalizar (≠ 1 por diferenciales y cotizaciones no sincronizadas); la normalización
      proporcional da una distribución, no garantiza que esté calibrada.
    - Si la partición es completa: P_D = Σ p̃ de los intervalos con margen > 0 (directo de los contratos, con el
      contrato «gana un independiente» en el denominador) y margen_media / margen_sd de la normal ajustada a los rangos
      D/R, con P_D_normal = Φ(μ/σ) como control. Con independiente, la normal es CONDICIONAL a que gane un partido principal
      (el contrato independiente no tiene margen D−R): es diagnóstico, no un resumen de toda la incertidumbre.
    - Siempre: margen_cond_D = E[M | D] con los intervalos positivos renormalizados (punto medio; «X % o más» → X + 5).
    Sin partición completa no se publica P_D ni margen incondicional (solo el condicional).
    """
    from scipy.stats import norm
    t = t.copy()
    t['desde'] = pd.to_numeric(t.desde, errors='coerce')
    t['hasta'] = pd.to_numeric(t.hasta, errors='coerce')
    if 'contrato' not in t:
        t['contrato'] = 'rango'
    es_ind = t.contrato.eq('independiente')
    p_ind = float(t[es_ind].p.sum())
    total = float(t.p.sum())
    t = t[~es_ind].sort_values('desde').reset_index(drop=True)          # eje D−R
    t['p_norm'] = t.p / t.p.sum()
    out = {'suma_precios': total, 'n_contratos': int(len(t) + es_ind.sum()), 'completo': _particion_completa(t)}
    if es_ind.any():
        out['P_independiente'] = p_ind / total
    pos = t[(t.desde >= 0) & (t.contrato != 'lado_completo')]          # el lado D completo no informa sobre M | D
    if len(pos):
        w = pos.p / pos.p.sum()
        med = np.where(np.isfinite(pos.hasta), (pos.desde + pos.hasta) / 2, pos.desde + 5)
        out['margen_cond_D'] = float(np.sum(w * med))
    if out['completo']:
        mu, sd = _ajuste_normal(t)
        out.update({'P_D': float(t[t.desde >= 0].p.sum() / total), 'margen_media': mu, 'margen_sd': sd,
                    'P_D_normal': float(1 - norm.cdf(0, mu, sd))})
    return out


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


def _al_corte(cfg, nombre: str, funcion) -> dict:
    """Reconstrucción: precio al cierre del día del corte (sin escribir en la caché de consultas en vivo)."""
    try:
        p_d, p_r = funcion()
        if not (np.isfinite(p_d) and np.isfinite(p_r) and p_d + p_r > 0):
            raise ValueError(f'precios inválidos {p_d}, {p_r}')
        return _armar(cfg, p_d, p_r, cfg.corte, f'historico (cierre {cfg.corte})')
    except Exception as exc:
        err = f'{type(exc).__name__}: {str(exc)[:140]}'
    ruta = cfg.dir_cache / f'mercado_{nombre}.csv'
    if ruta.exists():
        s = pd.read_csv(ruta)
        s = s[pd.to_datetime(s.fecha).dt.date <= cfg.corte]
        if len(s):
            u = s.iloc[-1]
            return _armar(cfg, u.p_d, u.p_r, date.fromisoformat(str(u.fecha)), f'cache ({err})')
    log.warning('%s sin precio al corte: %s', nombre, err)
    return {'usable': False, 'estado': f'no_disponible ({err})'}


def obtener_mercados(cfg) -> dict:
    f = cfg.fuentes
    ahora = datetime.now(ZoneInfo(cfg.eleccion.zona_horaria))
    if cfg.es_reconstruccion:
        return _obtener_al_corte(cfg)
    k = _snapshot(cfg, 'kalshi', lambda: kalshi_vivo(cfg), ahora)
    p = _snapshot(cfg, 'polymarket', lambda: ganador_poly(_evento_poly(cfg, f.polymarket_evento_ganador)), ahora)
    usables = [m['p_D'] for m in (k, p) if m.get('usable')]
    res = {'kalshi': k, 'polymarket': p, 'n_usables': len(usables),
           'promedio_D': float(np.mean(usables)) if usables else None,
           'dif_pp': (100 * (k['p_D'] - p['p_D'])) if k.get('usable') and p.get('usable') else None}
    try:                            # P(D)/(P(D)+P(R)) es una probabilidad CONDICIONAL a que gane un partido principal
        res['kalshi_independiente'] = kalshi_independiente(cfg)
    except Exception as exc:        # noqa: BLE001
        res['kalshi_independiente'] = None
        log.info('Kalshi independiente no disponible: %s', exc)
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


def _obtener_al_corte(cfg) -> dict:
    """Reconstrucción de un corte pasado: Kalshi y Polymarket (ganador y rangos) al cierre del día del corte."""
    f = cfg.fuentes
    k = _al_corte(cfg, 'kalshi', lambda: kalshi_al_corte(cfg))
    p = _al_corte(cfg, 'polymarket', lambda: ganador_poly(evento_poly_al_corte(cfg, _evento_poly(cfg, f.polymarket_evento_ganador))))
    usables = [m['p_D'] for m in (k, p) if m.get('usable')]
    res = {'kalshi': k, 'polymarket': p, 'n_usables': len(usables),
           'promedio_D': float(np.mean(usables)) if usables else None,
           'dif_pp': (100 * (k['p_D'] - p['p_D'])) if k.get('usable') and p.get('usable') else None,
           'kalshi_independiente': None}
    try:
        t = rangos_poly(evento_poly_al_corte(cfg, _evento_poly(cfg, f.polymarket_evento_margen)))
        res['rangos'] = {**resumen_rangos(t), 'estado': f'historico (cierre {cfg.corte})', 'tabla': t}
    except Exception as exc:        # noqa: BLE001 — diagnóstico: sin rangos no hay escenario, pero no es error
        err = f'{type(exc).__name__}: {str(exc)[:100]}'
        ruta = cfg.dir_cache / 'polymarket_rangos.csv'           # consulta guardada en una corrida en vivo ≤ corte
        t = pd.read_csv(ruta) if ruta.exists() else None
        if t is not None and 'consulta' in t and str(t.consulta.iloc[0])[:10] <= str(cfg.corte):
            res['rangos'] = {**resumen_rangos(t.drop(columns='consulta')), 'estado': f'cache ({err})', 'tabla': t}
        else:
            res['rangos'] = {'estado': f'no_disponible (reconstrucción: {err})'}
    return res
