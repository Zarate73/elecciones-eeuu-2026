import sys
from pathlib import Path
import numpy as np, pandas as pd
B = Path(sys.argv[1]); sys.path.insert(0, str(B))
import backtest_illinois as BM, base_georgia as bt, motor_backtest as BA, revision_observaciones as RO
d = RO.cargar(); d['partisan'] = d.partisan.fillna('').astype(str).str[:1].replace({'n': ''})
Y = sorted(d.year.unique())
V = {'G con sesgo (producción)': ('u50', True), 'H8 sin sesgo': ('u50', False)}
casa = {y: bt.efectos_casa(d[d.year != y]) for y in Y}
b = BA.construir(d, casa, 'v11')
orig = pd.concat([BA.evaluar(b, n, u, s, 'sig') for n, (u, s) in V.items()])
nest = []
for yo in Y:                                   # fold externo: NADA del año yo entra en el ajuste
    cy = {y: (casa[yo] if y == yo else bt.efectos_casa(d[~d.year.isin([yo, y])])) for y in Y}
    by = BA.construir(d, cy, 'v11')
    for n, (u, s) in V.items():
        P = BA.evaluar(by, n, u, s, 'sig'); nest.append(P[P.year == yo])
nest = pd.concat(nest)
def res(P):
    P = P.assign(ae=(P.mu - P.actual).abs(), br=(P.pD - (P.actual > 0)) ** 2)
    return P.groupby('modelo').agg(n=('crps', 'size'), CRPS=('crps', 'mean'), MAE=('ae', 'mean'), Brier=('br', 'mean'), Cob80=('c80', 'mean'), Cob95=('c95', 'mean'))
print('LOYO actual'); print(res(orig).round(4)); print('LOYO anidado (T2 corregido)'); print(res(nest).round(4))
m = orig.merge(nest, on=['race', 'modelo'], suffixes=('_o', '_n'))
print('máx |Δmu| =', round((m.mu_o - m.mu_n).abs().max(), 3), ' máx |Δsd| =', round((m.sd_o - m.sd_n).abs().max(), 3))
