"""Aplica el modelo ganador del backtest a Georgia Gobernador 2026 (corte 19-oct, T−15).

Modelo ganador (LOYO, horizonte 15 días):
  mu    = promedio ponderado (recencia, sqrt(n), 1 voto por firma) de márgenes corregidos por efecto de casa
          − sesgo estatal GA (sólo ciclos pasados, vida media 4 años, contracción bayes empírica)
  sigma = sqrt(tau² + s²/k), k = encuestadoras distintas, (tau, s) por MLE sobre errores históricos a T−15
  Indecisos: reparto 50/50 (el backtest descarta el 43.6% a R de V9). Sin terceros en boleta (WABE 10-jul-2026).
"""
from pathlib import Path
import json
import numpy as np, pandas as pd
from scipy.stats import norm
import backtest_georgia as bt

CORTE = pd.Timestamp('2026-10-19')
ELECCION = pd.Timestamp('2026-11-03')
VIDA_SESGO = 4.0
OUT = bt.OUT
rng = np.random.default_rng(20261019)


def parametros_historicos(horizonte=15):
    d = bt.cargar_encuestas()
    years = sorted(d.year.unique())
    casa_loyo = {y: bt.efectos_casa(d[d.year != y]) for y in years}
    b = bt.construir_contiendas(d, horizonte, 'casa', casa_loyo)
    b['e'] = b.poll - b.actual
    tau, s = bt.ajustar_sigma(b.e.to_numpy(), b.k.to_numpy())
    # sesgo GA con decaimiento (sólo pasado relativo a 2026 = todo el histórico)
    b['w'] = 0.5 ** ((2026 - b.year) / VIDA_SESGO)
    st = b.groupby('location').apply(lambda g: pd.Series({
        'm': np.average(g.e, weights=g.w), 'neff': g.w.sum() ** 2 / (g.w ** 2).sum(),
        'v': g.e.var() if len(g) > 1 else np.nan}), include_groups=False)
    st = st[st.neff >= 1.5]
    vs = max(float(st.m.var()) - float(np.nanmean(st.v / st.neff)), 0)
    ga = st.loc['GA']
    shrink = vs / (vs + ga.v / ga.neff)
    house, part = bt.efectos_casa(d)                 # efectos de casa con todo el histórico
    ga_hist = b[b.location == 'GA'][['race', 'year', 'poll', 'actual', 'e', 'k', 'w']]
    return {'tau': tau, 's': s, 'sesgo_ga_bruto': float(ga.m), 'contraccion': float(shrink),
            'sesgo_ga': float(shrink * ga.m), 'var_entre_estados': vs, 'house': house,
            'ga_hist': ga_hist}


def encuestas_2026():
    p = pd.read_csv(bt.DATA / 'ga_gob2026_encuestas.csv', parse_dates=['inicio', 'fin'])
    p = p[p.fin <= CORTE].copy()
    p['days'] = (ELECCION - p.fin).dt.days
    p['margin_poll'] = p.D - p.R
    p['n'] = p.n.clip(100, 3000)
    p['pollster_key'] = p.clave_538
    p['partisan'] = ''
    return p


def pronostico(p, par, ventana_dias, sesgo=True, casa=True, nombre=''):
    q = p[p.fin >= CORTE - pd.Timedelta(days=ventana_dias)]
    mu, k = bt.promedio(q.assign(days=q.days), 'casa' if casa else 'pond', par['house'], {}, 0)
    if sesgo:
        mu -= par['sesgo_ga']
    sd = float(np.sqrt(par['tau'] ** 2 + par['s'] ** 2 / max(k, 1)))
    # segunda vuelta: en boleta sólo D y R; 7 write-ins certificados (SOS 15-sep-2026).
    # Write-ins históricos: 81 votos (2018), 25 (2022) ≈ 0.001–0.002 % -> rango holgado 0.001–0.02 pp
    M = rng.normal(mu, sd, 400000)
    W = rng.uniform(0.001, 0.02, M.size)
    B = (100 - W + M) / 2; J = (100 - W - M) / 2
    return {'escenario': nombre, 'ventana_dias': ventana_dias, 'encuestas': len(q), 'k_firmas': k,
            'margen_B_J': mu, 'sd': sd, 'IC80_bajo': mu - 1.2816 * sd, 'IC80_alto': mu + 1.2816 * sd,
            'IC95_bajo': mu - 1.96 * sd, 'IC95_alto': mu + 1.96 * sd,
            'P_Bottoms_gana_pluralidad': float(norm.cdf(mu / sd)),
            'P_segunda_vuelta': float(((B <= 50) & (J <= 50)).mean()),
            'Bottoms_pct': (100 - 0.005 + mu) / 2, 'Jackson_pct': (100 - 0.005 - mu) / 2}


PESO_KALSHI = 0.30   # mismo peso que California M5; NO validado en backtest (ver README)


def kalshi_hoy():
    k = pd.read_csv(bt.DATA / 'kalshi_GOVPARTYGA-26-D_diario.csv', parse_dates=['date_utc'])
    k = k[k.date_utc <= CORTE + pd.Timedelta(days=1)]
    h = k.iloc[-1]
    mid_d = (h.yes_bid_close + h.yes_ask_close) / 2
    # Mercado R (API 20-oct-2026): bid 0.51–0.52 / ask 0.52–0.53 -> mid 0.515. Normalizamos D/(D+R).
    return str(h.date_utc.date()), float(mid_d / (mid_d + 0.515)), k


def mezclar_kalshi(fila, p_k, w=PESO_KALSHI):
    from scipy.special import logit, expit
    p = float(expit((1 - w) * logit(fila['P_Bottoms_gana_pluralidad']) + w * logit(p_k)))
    out = dict(fila); out['escenario'] = fila['escenario'] + f' + Kalshi (w={w})'
    out['P_Bottoms_gana_pluralidad'] = p
    out['margen_B_J'] = fila['sd'] * norm.ppf(p)      # margen equivalente con la misma sigma
    for c in ['IC80_bajo', 'IC80_alto', 'IC95_bajo', 'IC95_alto']:
        out[c] = fila[c] - fila['margen_B_J'] + out['margen_B_J']
    out['Bottoms_pct'] = (100 - 0.005 + out['margen_B_J']) / 2; out['Jackson_pct'] = (100 - 0.005 - out['margen_B_J']) / 2
    return out


if __name__ == '__main__':
    pd.set_option('display.width', 220)
    par = parametros_historicos(15)
    p = encuestas_2026()
    adj = p.assign(efecto_casa=p.pollster_key.map(par['house']).fillna(0.0))
    adj['margen_corregido'] = adj.margin_poll - adj.efecto_casa
    adj.to_csv(OUT / '2026_encuestas_corregidas.csv', index=False)
    rows = [
        pronostico(p, par, 7, nombre='PRINCIPAL: T−21..T−15 (igual que backtest)'),
        pronostico(p, par, 30, nombre='Sensibilidad: 30 días'),
        pronostico(p, par, 45, nombre='Sensibilidad: 45 días'),
        pronostico(p[~p.pollster.str.contains('G-Ratings')], par, 30, nombre='30 días sin G-Ratings'),
        pronostico(p, par, 7, sesgo=False, nombre='Sin sesgo estatal GA'),
        pronostico(p, par, 7, sesgo=False, casa=False, nombre='Sólo encuestas + sigma empírica'),
    ]
    fecha_k, p_k, serie_k = kalshi_hoy()
    rows.insert(1, mezclar_kalshi(rows[0], p_k))
    rows.append({'escenario': f'Kalshi solo ({fecha_k})', 'P_Bottoms_gana_pluralidad': p_k,
                 'margen_B_J': rows[0]['sd'] * norm.ppf(p_k), 'sd': rows[0]['sd']})
    T = pd.DataFrame(rows)
    T.to_csv(OUT / '2026_pronostico.csv', index=False)
    meta = {k: v for k, v in par.items() if k not in ('house', 'ga_hist')}
    meta.update({'corte': str(CORTE.date()), 'eleccion': str(ELECCION.date()), 'vida_media_sesgo_anios': VIDA_SESGO})
    (OUT / '2026_parametros.json').write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    par['ga_hist'].to_csv(OUT / 'GA_errores_historicos_h15.csv', index=False)
    print(json.dumps(meta, indent=2))
    print(adj[['fin', 'pollster', 'D', 'R', 'margin_poll', 'efecto_casa', 'margen_corregido']].to_string(index=False))
    print(T.round(3).to_string(index=False))
