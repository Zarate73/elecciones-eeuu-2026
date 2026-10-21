"""Fuentes externas: Kalshi (mercado), GDELT (tono mediático) y PDI (contraste manual)."""
from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from .red import get_json

log = logging.getLogger(__name__)


# ======================================================================================
# Kalshi
# ======================================================================================
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


def obtener_kalshi(cfg, corte: date) -> dict:
    f = cfg.fuentes
    snap = cfg.dir_cache / 'kalshi_snapshots.csv'
    ahora = datetime.now(ZoneInfo(cfg.eleccion.zona_horaria))
    try:
        js = get_json(f'{f.kalshi_api}/markets', params={'event_ticker': f.kalshi_evento},
                      offline=cfg.offline, timeout=f.timeout_http_s)
        mk = {m['ticker']: m for m in js.get('markets', [])}
        pd_, pr_ = _mid(mk[f.kalshi_ticker_d]), _mid(mk[f.kalshi_ticker_r])
        pd.DataFrame([{'consulta': ahora.isoformat(timespec='seconds'), 'fecha': ahora.date().isoformat(),
                       'p_d': pd_, 'p_r': pr_}]).to_csv(snap, mode='a', header=not snap.exists(),
                                                       index=False, encoding='utf-8-sig')
        return _armar(cfg, pd_, pr_, ahora.date(), 'en_vivo', corte)
    except Exception as exc:
        error = f'{type(exc).__name__}: {exc}'
    if snap.exists():
        s = pd.read_csv(snap).iloc[-1]
        return _armar(cfg, s.p_d, s.p_r, date.fromisoformat(s.fecha), f'cache_snapshot ({error})', corte)
    h = pd.read_csv(cfg.dir_datos / 'kalshi_general_ganador.csv')
    h['mid'] = np.where(h.yes_bid_close > 0, (h.yes_bid_close + h.yes_ask_close) / 2, h.price_close)
    h['fecha'] = (pd.to_datetime(h.end_period_ts, unit='s') - pd.Timedelta(hours=4)).dt.date - timedelta(days=1)
    w = h.pivot_table(index='fecha', columns='ticker', values='mid').dropna().iloc[-1]
    return _armar(cfg, w[f.kalshi_ticker_d], w[f.kalshi_ticker_r], w.name, f'cache_historico ({error})', corte)


def _armar(cfg, p_d, p_r, fecha, estado, corte) -> dict:
    p_d, p_r = float(p_d), float(p_r)
    antig = (corte - fecha).days
    usable = (not cfg.ejecucion.modo_conteo and np.isfinite(p_d) and np.isfinite(p_r)
              and 0 <= antig <= cfg.fuentes.kalshi_max_dias_antiguedad)
    return {'p_d': p_d, 'p_r': p_r, 'p_d_normalizada': p_d / (p_d + p_r), 'overround': p_d + p_r - 1,
            'fecha': str(fecha), 'antiguedad_dias': antig, 'estado': estado, 'usable_en_mezcla': bool(usable)}


# ======================================================================================
# GDELT (DOC 2.0, timelinetone). Solo diagnóstico mientras modelo.validado_sentimiento = false.
# ======================================================================================
def _gdelt_timeline(cfg, consulta: str, dias: int = 90) -> pd.DataFrame:
    f = cfg.fuentes
    fin = datetime.now(ZoneInfo('UTC'))
    js = get_json(f.gdelt_api, params={'query': consulta, 'mode': 'timelinetone', 'format': 'json',
                                       'timelinesmooth': 0,
                                       'startdatetime': (fin - timedelta(days=dias)).strftime('%Y%m%d%H%M%S'),
                                       'enddatetime': fin.strftime('%Y%m%d%H%M%S')},
                  offline=cfg.offline, timeout=f.timeout_http_s, reintentos=f.gdelt_reintentos,
                  pausa_base=f.gdelt_pausa_s / 2)
    datos = (js.get('timeline') or [{}])[0].get('data', [])
    df = pd.DataFrame(datos)
    if df.empty:
        return df
    df['fecha'] = pd.to_datetime(df['date'].str[:8], format='%Y%m%d')
    return df.groupby('fecha', as_index=False)['value'].mean().rename(columns={'value': 'tono'})


def actualizar_gdelt(cfg) -> tuple[pd.DataFrame, str]:
    f = cfg.fuentes
    ruta = cfg.dir_cache / 'gdelt_tono_diario.csv'
    cache = pd.read_csv(ruta, parse_dates=['fecha']) if ruta.exists() else pd.DataFrame()
    n_cache = cache.groupby('candidato').size().to_dict() if not cache.empty else {}
    # La hora de la última consulta se guarda aparte: la fecha del archivo no sirve en un checkout de git
    marca = cfg.dir_cache / 'gdelt_ultima_consulta.txt'
    try:
        ultima = float(marca.read_text().strip())
    except (OSError, ValueError):
        ultima = ruta.stat().st_mtime if ruta.exists() else 0.0
    fresca = ruta.exists() and (time.time() - ultima) < f.gdelt_horas_cache * 3600
    consultas = {'BECERRA': f.gdelt_consulta_d, 'HILTON': f.gdelt_consulta_r}
    pendientes = [c for c in sorted(consultas, key=lambda c: n_cache.get(c, 0))
                  if not (fresca and n_cache.get(c, 0) >= 30)]
    if not pendientes:
        return cache, 'cache (< %d h)' % f.gdelt_horas_cache
    partes, errores = [], []
    for i, cand in enumerate(pendientes):
        if i:
            time.sleep(f.gdelt_pausa_s)
        try:
            d = _gdelt_timeline(cfg, consultas[cand])
            if not d.empty:
                partes.append(d.assign(candidato=cand))
        except Exception as exc:
            errores.append(f'{cand}: {type(exc).__name__}: {exc}')
            if isinstance(exc, RuntimeError):      # 429 persistente: no insistir
                break
    if partes:
        cache = pd.concat([cache, *partes]).drop_duplicates(['fecha', 'candidato'], keep='last')
        cache.sort_values(['candidato', 'fecha']).to_csv(ruta, index=False, encoding='utf-8-sig')
        if not errores:
            marca.write_text(f'{time.time():.0f}\n')
    estado = 'en_vivo' if not errores else ('parcial: ' if partes else 'cache: ') + '; '.join(errores)
    return cache, estado


def senal_gdelt(cfg, df: pd.DataFrame, corte: date) -> dict:
    """Innovación sin traslape: brecha7d(t) − brecha7d(t−7), escalada por MAD (≥ 4 semanas)."""
    if df is None or df.empty:
        return {'disponible': False, 'nota': 'sin datos GDELT'}
    p = df.pivot_table(index='fecha', columns='candidato', values='tono')
    p = p[p.index <= pd.Timestamp(corte)].asfreq('D')
    faltan = {'BECERRA', 'HILTON'} - set(p.columns)
    if faltan:
        return {'disponible': False, 'nota': f"falta {', '.join(sorted(faltan))}"}
    if len(p) < 42:
        return {'disponible': False, 'nota': f'historia insuficiente ({len(p)} días; se requieren 42)'}
    brecha7 = (p['BECERRA'] - p['HILTON']).rolling(7, min_periods=5).mean()
    innov = (brecha7 - brecha7.shift(7)).dropna()
    hist, ultimo = innov.iloc[:-7], innov.iloc[-1]
    mad = 1.4826 * float(np.median(np.abs(hist - hist.median())))
    z = float((ultimo - hist.median()) / max(mad, 1e-6))
    s = cfg.sentimiento_odiseo
    return {'disponible': True, 'fecha': str(innov.index[-1].date()), 'brecha_7d': float(brecha7.iloc[-1]),
            'innovacion_7d': float(ultimo), 'z_innovacion': z,
            'k_sent_candidato': float(min(cfg.modelo.k_sent_max, np.exp(s.gamma * min(abs(z), 3))))}


# ======================================================================================
# PDI (captura manual: data/pdi_retornos_manual.csv)
# ======================================================================================
def cargar_pdi(cfg) -> dict:
    p = cfg.dir_datos / 'pdi_retornos_manual.csv'
    if not p.exists():
        return {'disponible': False}
    d = pd.read_csv(p).iloc[-1]
    tot = d.dem + d.rep + d.otro
    return {'disponible': True, 'fecha': str(d.fecha), 'devueltas': int(tot), 'dem_pct': 100 * d.dem / tot,
            'rep_pct': 100 * d.rep / tot, 'margen_dr_pp': 100 * (d.dem - d.rep) / tot, 'fuente': str(d.fuente)}
