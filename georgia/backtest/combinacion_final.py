"""Combinación final: base V10 + colas Student-t (+/− vida media 5) y bootstrap por año contra la base."""
import numpy as np, pandas as pd
import backtest_georgia as bt
import backtest_componentes_versiones as cv
from scipy.stats import norm

rng = np.random.default_rng(20261019)
d = bt.cargar_encuestas(); years = sorted(d.year.unique())
casa = {y: bt.efectos_casa(d[d.year != y]) for y in years}
b14 = cv.construir(d, casa, lambda q, h: cv.agregar(q, h))
b5 = cv.construir(d, casa, lambda q, h: cv.agregar(q, h, hl=5))
res = []
_, Pn = cv.evaluar(b14, years, nombre='base')
_, Pt = cv.evaluar(b14, years, dist='t', nombre='t')
R5t, P5t = cv.evaluar(b5, years, dist='t', nombre='t + HL5')
res.append(R5t)
def crps_row(P, dist):
    if dist == 't':
        sc = P.sd * np.sqrt((P.nu - 2) / P.nu); return cv.crps_t(P.actual, P.mu, sc, P.nu)
    return bt.crps_normal(P.actual, P.mu, P.sd)
A = Pn.assign(c_base=crps_row(Pn, 'n'))[['race', 'year', 'location', 'runoff', 'c_base']]
A = A.merge(Pt.assign(c_t=crps_row(Pt, 't'))[['race', 'c_t']]).merge(P5t.assign(c_t5=crps_row(P5t, 't'))[['race', 'c_t5']])
filas = []
for amb, m in [('Nacional', A.index == A.index), ('GA', (A.location == 'GA') & ~A.runoff)]:
    g = A[m]
    for col in ['c_t', 'c_t5']:
        dif = g[col] - g.c_base; yrs = g.year.unique(); by = {y: dif[g.year == y].to_numpy() for y in yrs}
        st = np.array([np.concatenate([by[y] for y in rng.choice(yrs, len(yrs))]).mean() for _ in range(4000)])
        filas.append({'ambito': amb, 'modelo': 't' if col == 'c_t' else 't + HL5', 'dif_CRPS_vs_base': dif.mean(),
                      'IC95_bajo': np.quantile(st, .025), 'IC95_alto': np.quantile(st, .975), 'P(mejor)': (st < 0).mean()})
B = pd.DataFrame(filas)
print(pd.concat(res).round(3).to_string(index=False)); print(B.round(4).to_string(index=False))
B.to_csv(bt.OUT / 'F_bootstrap_t_vs_base.csv', index=False)
# nu final con todo el histórico (para producción)
tau, s = bt.ajustar_sigma(b14.e.to_numpy(), b14.k.to_numpy())
z = b14.e / np.sqrt(tau ** 2 + s ** 2 / np.maximum(b14.k, 1))
from scipy.stats import t as st_
nus = np.linspace(2.5, 60, 576); ll = [np.sum(st_.logpdf(z, nu, scale=np.sqrt((nu - 2) / nu))) for nu in nus]
print('nu (todo el histórico):', nus[int(np.argmax(ll))], ' tau,s', tau, s)
