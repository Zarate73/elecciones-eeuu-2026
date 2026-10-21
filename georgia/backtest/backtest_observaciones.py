"""Validación de observaciones externas sobre V11.

G) Prior estructural (lean presidencial del estado + entorno nacional del año) mezclado con el modelo V11
   (casa + sesgo estatal + t). Peso beta estimado LOYO; también se prueba un peso fijo de 0.20 (sugerido)
   y se reporta por horizonte (T−15 y T−0) para ver si 'se diluye' al acercarse la elección.
H) Correlación del error de encuestas entre Gobernador y Senado del MISMO estado-año (para simulación conjunta).
"""
import numpy as np, pandas as pd
from scipy.stats import t as student_t
import backtest_georgia as bt
import backtest_componentes_versiones as cv

OUT = bt.OUT


def preparar(h):
    d = bt.cargar_encuestas(); years = sorted(d.year.unique())
    casa = {y: bt.efectos_casa(d[d.year != y]) for y in years}
    cv.H = h
    b = cv.construir(d, casa, lambda q, hh: cv.agregar(q, hh))
    leans = bt.lean_estatal(d)
    b['lean'] = [leans.get((l, y), np.nan) for l, y in zip(b.location, b.year)]
    b['env'] = np.nan
    for i, r in b.iterrows():                       # entorno con encuestas de OTRAS contiendas del año
        o = b[(b.year == r.year) & (b.race != r.race) & b.lean.notna() & ~b.runoff]
        if len(o) >= 5:
            b.at[i, 'env'] = float((o.poll - o.lean).median())
    b['fund'] = b.lean + b.env
    return b, years


def evaluar_prior(b, years, modo):
    preds = []
    for y in years:
        te = b.year == y
        if not te.any(): continue
        tr = b[~te].copy()
        bias = cv.sesgo_pasado(tr, y)
        tr['mu0'] = tr.poll - tr.location.map(cv.sesgo_pasado(tr, y + 0)).fillna(0)  # mismo tratamiento
        f = tr[tr.fund.notna()]
        if modo == 'beta_LOYO':
            x = f.fund - f.mu0; yv = f.actual - f.mu0
            beta = float(np.clip(np.sum(x * yv) / np.sum(x * x), 0, 1))
        elif modo == 'fijo_0.20':
            beta = 0.20
        else:
            beta = 0.0
        tr['mu'] = np.where(tr.fund.notna(), tr.mu0 + beta * (tr.fund - tr.mu0), tr.mu0)
        tr['e2'] = tr.mu - tr.actual
        tau, s = bt.ajustar_sigma(tr.e2.to_numpy(), tr.k.to_numpy())
        sd_tr = np.sqrt(tau ** 2 + s ** 2 / np.maximum(tr.k, 1))
        nus = np.linspace(2.5, 60, 116)
        nu = nus[int(np.argmax([np.sum(student_t.logpdf(tr.e2 / sd_tr, v, scale=np.sqrt((v - 2) / v))) for v in nus]))]
        t = b[te].copy()
        mu0 = t.poll - t.location.map(bias).fillna(0)
        t['mu'] = np.where(t.fund.notna(), mu0 + beta * (t.fund - mu0), mu0)
        t['sd'] = np.sqrt(tau ** 2 + s ** 2 / np.maximum(t.k, 1)); t['nu'] = nu; t['beta'] = beta
        preds.append(t)
    P = pd.concat(preds)
    rows = []
    for amb, m in [('Nacional', P.index == P.index), ('Nacional_Gob', P.tipo == 'Gov-G'),
                   ('GA_generales', (P.location == 'GA') & ~P.runoff)]:
        g = P[m]; sc = g.sd * np.sqrt((g.nu - 2) / g.nu)
        e = g.mu - g.actual
        rows.append({'ambito': amb, 'modo': modo, 'n': len(g), 'beta_medio': g.beta.mean(),
                     'RMSE': np.sqrt((e ** 2).mean()), 'CRPS': cv.crps_t(g.actual, g.mu, sc, g.nu).mean(),
                     'LogScore': (-student_t.logpdf(g.actual, g.nu, g.mu, sc)).mean(),
                     'Cob80': (np.abs(e) <= student_t.ppf(.9, g.nu) * sc).mean()})
    return pd.DataFrame(rows), P


def correlacion_gob_sen(b):
    g = b[~b.runoff & b.tipo.isin(['Gov-G', 'Sen-G'])].copy()
    piv = g.pivot_table(index=['location', 'year'], columns='tipo', values='e', aggfunc='first').dropna()
    # error 'puro de encuestas' también restando la media del año (lo común a todo el país)
    g['e_c'] = g.e - g.groupby('year').e.transform('mean')
    piv_c = g.pivot_table(index=['location', 'year'], columns='tipo', values='e_c', aggfunc='first').dropna()
    r = float(np.corrcoef(piv['Gov-G'], piv['Sen-G'])[0, 1])
    rc = float(np.corrcoef(piv_c['Gov-G'], piv_c['Sen-G'])[0, 1])
    rng = np.random.default_rng(1); idx = np.arange(len(piv)); bs = []
    for _ in range(4000):
        i = rng.choice(idx, len(idx)); bs.append(np.corrcoef(piv['Gov-G'].iloc[i], piv['Sen-G'].iloc[i])[0, 1])
    ga = piv.loc['GA'] if 'GA' in piv.index.get_level_values(0) else None
    return {'n_pares_estado_anio': len(piv), 'rho_errores': r, 'rho_IC95': (float(np.quantile(bs, .025)), float(np.quantile(bs, .975))),
            'rho_sin_componente_anual': rc}, piv, ga


if __name__ == '__main__':
    pd.set_option('display.width', 200)
    todo = []
    for h in (15, 0):
        b, years = preparar(h)
        for modo in ('sin_prior', 'beta_LOYO', 'fijo_0.20'):
            r, _ = evaluar_prior(b, years, modo); r['horizonte'] = h; todo.append(r)
        if h == 15:
            info, piv, ga = correlacion_gob_sen(b)
    G = pd.concat(todo); G.to_csv(OUT / 'G_prior_estructural.csv', index=False)
    print(G.round(3).to_string(index=False))
    print('\nH) Correlación Gob–Sen mismo estado-año:', info)
    print(ga.round(2) if ga is not None else 'sin pares GA')
    pd.DataFrame([info]).to_csv(OUT / 'H_correlacion_gob_sen.csv', index=False)
    piv.to_csv(OUT / 'H_pares_gob_sen.csv')
