"""Backtest de los componentes de TODAS las versiones de Georgia (v5–v9) sobre la base V10.

Marco idéntico al backtest principal: LOYO por año, horizonte 15 días, 980 contiendas (701 con
encuestas a T−15). Base = V10 (casa + sesgo estatal pasado HL 4 años + sigma(k) empírica).

Componentes probados (origen):
  W1  pesos 1/var_muestral (V8-M1, V9)            vs √n (V10)
  W2  vida media 5 / 30 días (V8-M1 eligió 5)      vs 14 (V10)
  W3  penalización por firma 1/√repeticiones (V9)  vs 1/repeticiones (V10)
  K   filtro de Kalman nivel local (V8-M2) como agregador, (q, a) elegidos en entrenamiento
  T   colas Student-t (V8-M3), ν estimado en entrenamiento
  S   shocks Poisson (V9): en el marco del backtest equivale a varianza extra; se prueba como
      inflación de sigma (lambda·h·σ_salto²) con los parámetros de V9
  E   composición racial del voto anticipado a T−15 (M4-E, Civic Forge), sólo GA 2018–2024
No backtestables con datos reales: M4-H territorial (solo hay mapas 2018/2022 de GA), tres categorías
(es formato de reporte), escenarios de redistribución v8 (equivalen a reglas de indecisos ya probadas).
"""
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm, t as student_t
from scipy.special import beta as Bfun
import backtest_georgia as bt

OUT = bt.OUT
H = 15


def var_muestral(p):
    a, b = p.cand1_pct / 100, p.cand2_pct / 100
    return 1e4 * np.clip(a + b - (a - b) ** 2, .05, None) / p.n


def agregar(p, house, hl=14.0, pesos='sqrtn', firma='lineal'):
    if p.empty: return np.nan, 0
    m = p.margin_poll.to_numpy(float) - p.pollster_key.map(house).fillna(0).to_numpy(float)
    dt = (p.days - p.days.min()).to_numpy(float)
    base = np.sqrt(p.n.to_numpy(float)) if pesos == 'sqrtn' else 1 / var_muestral(p).to_numpy(float)
    w = np.exp(-np.log(2) * dt / hl) * base
    rep = p.pollster_key.map(p.pollster_key.value_counts()).to_numpy(float)
    w = w / (rep if firma == 'lineal' else np.sqrt(rep))
    return float(np.sum(w * m) / np.sum(w)), int(p.pollster_key.nunique())


def kalman(p, house, q, a):
    """Nivel local (V8-M2): estado = margen verdadero, var de transición q·Δdías, var de obs a·v_i."""
    if p.empty: return np.nan, 0
    p = p.sort_values('polldate')
    y = p.margin_poll.to_numpy(float) - p.pollster_key.map(house).fillna(0).to_numpy(float)
    v = a * var_muestral(p).to_numpy(float)
    d = p.polldate.to_numpy('datetime64[D]')
    m, P = y[0], v[0]
    for i in range(1, len(y)):
        P = P + q * max(int((d[i] - d[i - 1]).astype(int)), 0)
        K = P / (P + v[i]); m = m + K * (y[i] - m); P = (1 - K) * P
    return float(m), int(p.pollster_key.nunique())


def crps_t(y, mu, sc, nu):
    z = (y - mu) / sc
    F, f = student_t.cdf(z, nu), student_t.pdf(z, nu)
    term = 2 * np.sqrt(nu) * Bfun(.5, nu - .5) / ((nu - 1) * Bfun(.5, nu / 2) ** 2)
    return sc * (z * (2 * F - 1) + 2 * f * (nu + z ** 2) / (nu - 1) - term)


def sesgo_pasado(tr, y, hl=4.0):
    past = tr[tr.year < y].copy()
    if len(past) < 20: return {}
    past['w'] = 0.5 ** ((y - past.year) / hl)
    st = past.groupby('location').apply(lambda g: pd.Series({'m': np.average(g.e, weights=g.w),
        'neff': g.w.sum() ** 2 / (g.w ** 2).sum(), 'v': g.e.var() if len(g) > 1 else np.nan}), include_groups=False)
    st = st[st.neff >= 1.5]
    vs = max(float(st.m.var()) - float(np.nanmean(st.v / st.neff)), 0)
    return {l: (vs / (vs + r.v / r.neff)) * r.m if vs > 0 and not np.isnan(r.v) else 0.0 for l, r in st.iterrows()}


def construir(d, casa, fn):
    rows = []
    for race, p in d.groupby('race'):
        y = int(p.year.iloc[0]); q = p[p.days >= H]
        mu, k = fn(q, casa[y][0])
        if np.isnan(mu): continue
        rows.append({'race': race, 'year': y, 'location': p.location.iloc[0], 'runoff': bool(p.runoff.iloc[0]),
                     'tipo': p.type_simple.iloc[0], 'poll': mu, 'k': k, 'actual': float(p.margin_actual.iloc[0])})
    b = pd.DataFrame(rows); b['e'] = b.poll - b.actual
    return b


def evaluar(b, years, dist='normal', extra_var=0.0, nombre=''):
    preds = []
    for y in years:
        te = b.year == y
        if not te.any(): continue
        tr = b[~te]
        tau, s = bt.ajustar_sigma(tr.e.to_numpy(), tr.k.to_numpy())
        bias = sesgo_pasado(tr, y)
        t = b[te].copy()
        t['mu'] = t.poll - t.location.map(bias).fillna(0)
        t['sd'] = np.sqrt(tau ** 2 + s ** 2 / np.maximum(t.k, 1) + extra_var)
        if dist == 't':
            ztr = tr.e / np.sqrt(tau ** 2 + s ** 2 / np.maximum(tr.k, 1))
            nus = np.linspace(2.5, 60, 116)
            ll = [np.sum(student_t.logpdf(ztr, nu, scale=np.sqrt((nu - 2) / nu))) for nu in nus]
            t['nu'] = nus[int(np.argmax(ll))]
        preds.append(t)
    P = pd.concat(preds)
    out = []
    for amb, m in [('Nacional', P.index == P.index), ('GA_generales', (P.location == 'GA') & ~P.runoff),
                   ('GA_2014+', (P.location == 'GA') & (P.year >= 2014))]:
        g = P[m]
        r = bt.metricas(g)
        if dist == 't':
            sc = g.sd * np.sqrt((g.nu - 2) / g.nu)
            r['CRPS'] = float(crps_t(g.actual, g.mu, sc, g.nu).mean())
            r['LogScore'] = float((-student_t.logpdf(g.actual, g.nu, g.mu, sc)).mean())
            r['Cob80'] = float((np.abs(g.mu - g.actual) <= student_t.ppf(.9, g.nu) * sc).mean())
            r['Cob95'] = float((np.abs(g.mu - g.actual) <= student_t.ppf(.975, g.nu) * sc).mean())
            r['nu_medio'] = float(g.nu.mean())
        r.update({'variante': nombre, 'ambito': amb}); out.append(r)
    return pd.DataFrame(out), P


def main():
    d = bt.cargar_encuestas()
    years = sorted(d.year.unique())
    casa = {y: bt.efectos_casa(d[d.year != y]) for y in years}
    res, preds = [], {}
    variantes = {
        'V10 base (√n, HL14, 1/rep)': lambda q, h: agregar(q, h),
        'W1 pesos 1/var (V8/V9)': lambda q, h: agregar(q, h, pesos='ivar'),
        'W2 HL 5 días (V8)': lambda q, h: agregar(q, h, hl=5),
        'W2 HL 30 días': lambda q, h: agregar(q, h, hl=30),
        'W3 firma 1/√rep (V9)': lambda q, h: agregar(q, h, firma='raiz'),
    }
    bases = {}
    for nom, fn in variantes.items():
        b = construir(d, casa, fn); bases[nom] = b
        r, P = evaluar(b, years, nombre=nom); res.append(r); preds[nom] = P
    # Kalman (V8-M2): (q, a) elegidos por RMSE en entrenamiento, por año (LOYO)
    grid = [(q, a) for q in (0.02, 0.1, 0.5, 2.0) for a in (1.0, 2.0, 4.0)]
    kb = {g: construir(d, casa, lambda qq, h, g=g: kalman(qq, h, *g)) for g in grid}
    sel = []
    for y in years:
        best = min(grid, key=lambda g: np.sqrt(np.mean(kb[g].loc[kb[g].year != y, 'e'] ** 2)))
        sel.append(kb[best][kb[best].year == y].assign(qa=str(best)))
    bK = pd.concat(sel)
    r, P = evaluar(bK, years, nombre='K Kalman nivel local (V8-M2)'); res.append(r); preds['K'] = P
    # Student-t (V8-M3) sobre la base V10
    r, P = evaluar(bases['V10 base (√n, HL14, 1/rep)'], years, dist='t', nombre='T colas Student-t (V8-M3)')
    res.append(r); preds['T'] = P
    # Shocks Poisson V9: var extra = E[N]·σ² = λ·h/7·1.2²  (λ=0.253/sem) -> se suma a sigma
    ev = 0.253 * H / 7 * 1.2 ** 2
    r, P = evaluar(bases['V10 base (√n, HL14, 1/rep)'], years, extra_var=ev, nombre='S shocks Poisson V9 (+var)')
    res.append(r); preds['S'] = P
    R = pd.concat(res)
    R = R[['ambito', 'variante', 'n', 'sesgo', 'MAE', 'RMSE', 'CRPS', 'LogScore', 'Cob80', 'Cob95', 'Brier', 'sd_media'] +
          (['nu_medio'] if 'nu_medio' in R else [])]
    R.to_csv(OUT / 'E_componentes_versiones.csv', index=False)
    kq = bK.groupby('year').qa.first(); kq.to_csv(OUT / 'E_kalman_parametros_por_anio.csv')
    return R, preds, bases


def voto_anticipado_ga():
    """M4-E con Civic Forge: % negro de boletas aceptadas a T−15 (matched) vs error de encuestas GA."""
    cf = pd.read_csv(bt.DATA / 'civicforge_raza_T15.csv')
    cf['negro_pct'] = 100 * cf.BLACK / cf[['ASIAN', 'BLACK', 'HISPANIC', 'NA', 'OTHER', 'WHITE']].sum(axis=1)
    P = pd.read_csv(OUT / 'predicciones_h15.csv')
    g = P[(P.modelo == 'casa|sd_empirica') & (P.location == 'GA') & ~P.runoff][['race', 'year', 'poll', 'actual']]
    g['e'] = g.poll - g.actual
    g = g.merge(cf[['anio', 'negro_pct']], left_on='year', right_on='anio')
    filas = []
    for y in sorted(g.year.unique()):                     # LOYO por ciclo
        tr, te = g[g.year != y], g[g.year == y]
        X = tr.negro_pct - tr.negro_pct.mean()
        b = float(np.sum(X * (tr.e - tr.e.mean())) / np.sum(X ** 2))
        pred = tr.e.mean() + b * (te.negro_pct - tr.negro_pct.mean())
        for (_, r), pe in zip(te.iterrows(), pred):
            filas.append({'race': r.race, 'year': y, 'negro_pct': r.negro_pct, 'error_real': r.e,
                          'pred_error_con_raza': pe, 'pred_error_media': tr.e.mean(), 'pendiente_LOYO': b})
    F = pd.DataFrame(filas)
    resumen = {'RMSE_con_raza': float(np.sqrt(np.mean((F.error_real - F.pred_error_con_raza) ** 2))),
               'RMSE_solo_media': float(np.sqrt(np.mean((F.error_real - F.pred_error_media) ** 2))),
               'RMSE_sin_corregir': float(np.sqrt(np.mean(F.error_real ** 2))),
               'corr_negro_error': float(np.corrcoef(g.negro_pct, g.e)[0, 1]), 'n_contiendas': len(g),
               'n_ciclos': g.year.nunique()}
    F.to_csv(OUT / 'E_voto_anticipado_raza_LOYO.csv', index=False)
    return F, resumen


if __name__ == '__main__':
    pd.set_option('display.width', 220)
    R, preds, bases = main()
    for amb in ['Nacional', 'GA_generales', 'GA_2014+']:
        print('\n--', amb)
        print(R[R.ambito == amb].drop(columns='ambito').sort_values('CRPS').round(3).to_string(index=False))
    F, s = voto_anticipado_ga()
    print('\nM4-E voto anticipado por raza (Civic Forge, GA):', {k: round(v, 3) if isinstance(v, float) else v for k, v in s.items()})
    print(F.round(2).to_string(index=False))
