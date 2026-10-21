"""Kalshi vs Polymarket en Arizona: ¿son el mismo precio?

Contiendas con historia en ambos: Gobernador 2026 (D), Presidente 2024 (D), Senado 2024 (D).
Serie diaria: Kalshi = punto medio bid/ask al cierre (o precio de cierre), normalizado D/(D+R);
Polymarket = precio diario del «Sí» demócrata (prices-history, fidelity 1 día).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
M = BASE / 'data' / 'mercados'
SAL = BASE / 'salida'; SAL.mkdir(exist_ok=True)


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return np.nan


def kalshi(ticker):
    c = json.loads((M / f'kalshi_velas_{ticker}.json').read_text())['candlesticks']
    filas = []
    for v in c:
        p, b, a = v.get('price', {}), v.get('yes_bid', {}), v.get('yes_ask', {})
        bid = _f(b.get('close_dollars', b.get('close'))); ask = _f(a.get('close_dollars', a.get('close')))
        cierre = _f(p.get('close_dollars', p.get('close')))
        medio = (bid + ask) / 2 if np.isfinite(bid) and np.isfinite(ask) and ask - bid <= 0.10 else cierre
        vol = _f(v.get('volume_fp', v.get('volume')))
        filas.append({'fecha': pd.to_datetime(v['end_period_ts'], unit='s').normalize(), 'p': medio, 'vol': vol})
    return pd.DataFrame(filas).dropna(subset=['p']).set_index('fecha')


def kalshi_d(ev):
    d, r = kalshi(f'{ev}-D'), kalshi(f'{ev}-R')
    x = pd.concat({'d': d.p, 'r': r.p, 'vol': d.vol + r.vol}, axis=1).dropna(subset=['d', 'r'])
    x['p'] = x.d / (x.d + x.r)
    return x[['p', 'vol']]


def poly(mid):
    h = json.loads((M / f'poly_hist_{mid}.json').read_text())['history']
    s = pd.DataFrame(h)
    s['fecha'] = pd.to_datetime(s.t, unit='s').dt.normalize()
    return s.groupby('fecha').p.last()


CASOS = {  # contienda: (evento Kalshi, mercado Polymarket «D», mercado «R» o None, si invertir, resultado D gana)
    'Gobernador AZ 2026': ('GOVPARTYAZ-26', 629183, 629184, None),
    'Presidente AZ 2024': ('PRESPARTYAZ-24', 255050, 255051, 0),
    'Senado AZ 2024': ('SENATEAZ-24', 500614, 500615, 1),
}

filas, series = [], {}
for nombre, (ev, md, mr, res) in CASOS.items():
    k = kalshi_d(ev)
    pdm, prm = poly(md), poly(mr)
    pp = (pdm / (pdm + prm.reindex(pdm.index))).fillna(pdm)
    x = pd.concat({'kalshi': k.p, 'polymarket': pp, 'vol_kalshi': k.vol}, axis=1).dropna(subset=['kalshi', 'polymarket'])
    if res is not None:                                   # solo hasta la víspera de la elección
        x = x[x.index < pd.Timestamp('2024-11-05')]
    series[nombre] = x
    dif = x.kalshi - x.polymarket
    lg = lambda p: np.log(p.clip(.005, .995) / (1 - p.clip(.005, .995)))
    dk, dp = lg(x.kalshi).diff(), lg(x.polymarket).diff()
    cc = {L: dk.corr(dp.shift(L)) for L in range(-3, 4)}            # L>0: Polymarket se mueve antes
    ult30 = x[x.index >= x.index.max() - pd.Timedelta(days=30)]
    fila = {'contienda': nombre, 'dias_comunes': len(x), 'desde': x.index.min().date(), 'hasta': x.index.max().date(),
            'kalshi_ultimo': x.kalshi.iloc[-1], 'polymarket_ultimo': x.polymarket.iloc[-1],
            'dif_media_pp': 100 * dif.mean(), 'dif_abs_media_pp': 100 * dif.abs().mean(),
            'dif_abs_max_pp': 100 * dif.abs().max(), 'dif_abs_ult30_pp': 100 * (ult30.kalshi - ult30.polymarket).abs().mean(),
            'corr_niveles': x.kalshi.corr(x.polymarket), 'corr_cambios_logit': dk.corr(dp),
            'lag_max_corr': max(cc, key=lambda L: cc[L] if np.isfinite(cc[L]) else -9),
            'corr_lag0': cc[0], 'corr_lag+1': cc[1], 'corr_lag-1': cc[-1]}
    if res is not None:
        for m in ('kalshi', 'polymarket'):
            fila[f'brier_ult30_{m}'] = float(((ult30[m] - res) ** 2).mean())
    filas.append(fila)
t = pd.DataFrame(filas)
t.round(4).to_csv(SAL / 'mercados_comparacion.csv', index=False)
pd.concat(series, names=['contienda']).to_csv(SAL / 'mercados_series_diarias.csv')
pd.set_option('display.width', 250)
print(t.round(3).T.to_string())

# Margen implícito de Polymarket (mercado por rangos) para el Gobernador 2026
rangos = {3364330: (-30, -6), 3364332: (-6, -3), 3364334: (-3, 0), 3364336: (0, 3), 3364339: (3, 6), 3364341: (6, 9),
          3364346: (9, 12), 3364353: (12, 15), 3364356: (15, 18), 3364358: (18, 30)}
ult = {}
for mid, (a, b) in rangos.items():
    s = poly(mid)
    ult[(a, b)] = s.iloc[-1]
r = pd.DataFrame([{'desde': a, 'hasta': b, 'p': p} for (a, b), p in ult.items()]).sort_values('desde')
r['p_norm'] = r.p / r.p.sum()
centro = (r.desde.clip(lower=-9) + r.hasta.clip(upper=21)) / 2
media = float((centro * r.p_norm).sum()); sd = float(np.sqrt(((centro - media) ** 2 * r.p_norm).sum()))
r.to_csv(SAL / 'polymarket_margen_rangos.csv', index=False)
print(r.round(3).to_string(index=False))
print(f'Margen implícito Polymarket (Hobbs − Biggs): media {media:+.1f} pp, DE {sd:.1f} pp; suma de precios {r.p.sum():.3f}; '
      f'P(D) por rangos {r[r.desde >= 0].p_norm.sum():.3f}')
