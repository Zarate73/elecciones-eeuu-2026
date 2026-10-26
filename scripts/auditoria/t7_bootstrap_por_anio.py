import sys
from pathlib import Path
import numpy as np, pandas as pd
B = Path(sys.argv[1]); sys.path.insert(0, str(B))
import backtest_illinois as BM, base_georgia as bt, motor_backtest as BA, revision_observaciones as RO
d = RO.cargar(); d['partisan'] = d.partisan.fillna('').astype(str).str[:1].replace({'n': ''})
casa = {y: bt.efectos_casa(d[d.year != y]) for y in sorted(d.year.unique())}
b = BA.construir(d, casa, 'v11')
G = BA.evaluar(b, 'G', 'u50', True, 'sig'); S0 = BA.evaluar(b, 'H8', 'u50', False, 'sig')
m = G.merge(S0, on='race', suffixes=('_g', '_s'))
m['dcrps'] = m.crps_g - m.crps_s
m['dbr'] = (m.pD_g - (m.actual_g > 0)) ** 2 - (m.pD_s - (m.actual_s > 0)) ** 2
m['dae'] = (m.mu_g - m.actual_g).abs() - (m.mu_s - m.actual_s).abs()
yrs = m.year_g.unique(); rng = np.random.default_rng(7); g = {y: m[m.year_g == y] for y in yrs}
bs = []
for _ in range(4000):
    x = pd.concat([g[y] for y in rng.choice(yrs, len(yrs))]); bs.append([x.dcrps.mean(), x.dae.mean(), x.dbr.mean()])
bs = np.array(bs)
for i, nm in enumerate(['ΔCRPS', 'ΔMAE', 'ΔBrier']):
    print(f'{nm} (con sesgo − sin sesgo) = {[m.dcrps, m.dae, m.dbr][i].mean():+.4f}  IC95 bootstrap por año [{np.quantile(bs[:,i],.025):+.4f}, {np.quantile(bs[:,i],.975):+.4f}]  P(>0)={np.mean(bs[:,i]>0):.3f}')
print('años:', len(yrs))
