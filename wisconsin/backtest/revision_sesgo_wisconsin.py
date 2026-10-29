"""¿De dónde debe salir el sesgo estatal de Wisconsin? (28-oct; heredada de Ohio y North Carolina)

Reglas nacionales (no solo en OH), LOYO con la ventana de producción:
  G       sesgo con todas las contiendas del estado (producción);
  G_cargo sesgo solo con contiendas del mismo cargo en el estado;
  G_k2    sesgo sin contiendas de una sola encuestadora;
  H8      sin sesgo.
Uso: python revision_sesgo_wisconsin.py (requiere backtest_wisconsin.py importable) → salida/revision_sesgo_*.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
import backtest_wisconsin as BM            # noqa: E402  (fija H = 6 y ESTADO = WI)
import base_georgia as bt              # noqa: E402
import motor_backtest as BA            # noqa: E402
import revision_observaciones as RO    # noqa: E402

EST = 'WI'
ORIG = BA.sesgo_pasado


def sesgo_k2(tr, y, contraer=True):
    return ORIG(tr[tr.k >= 2], y, contraer)


def main():
    pd.set_option('display.width', 220)
    d = RO.cargar()
    d['partisan'] = d.partisan.fillna('').astype(str).str[:1].replace({'n': ''})
    years = sorted(d.year.unique())
    casa = {y: bt.efectos_casa(d[d.year != y]) for y in years}
    b = BA.construir(d, casa, 'v11')
    P = [BA.evaluar(b, 'G', 'u50', True, 'sig'), BA.evaluar(b, 'H8', 'u50', False, 'sig')]
    bc = b.assign(loc_real=b.location, location=b.location + '_' + b.tipo)       # sesgo por estado × cargo
    pc = BA.evaluar(bc, 'G_cargo', 'u50', True, 'sig')
    P.append(pc.assign(location=pc.loc_real).drop(columns='loc_real'))
    BA.sesgo_pasado = sesgo_k2
    P.append(BA.evaluar(b, 'G_k2', 'u50', True, 'sig'))
    BA.sesgo_pasado = ORIG
    P = pd.concat(P, ignore_index=True)
    filas = []
    ambitos = {'Nacional': P.index == P.index, 'Nacional_Gob': P.tipo == 'Gov-G', EST: P.location == EST,
               f'{EST}_Gob': (P.location == EST) & (P.tipo == 'Gov-G')}
    for amb, m in ambitos.items():
        for mod, g in P[m].groupby('modelo'):
            filas.append({'ambito': amb, 'modelo': mod, 'n': len(g), 'CRPS': g.crps.mean(),
                          'MAE': (g.mu - g.actual).abs().mean(), 'Cob80': g.c80.mean()})
            if mod != 'G' and P[m & (P.modelo == 'G')].year.nunique() > 2:
                filas[-1]['P(mejor que G)'] = BA.bootstrap_por_anio(P, mod, 'G', pd.Series(np.asarray(m), index=P.index))
    T = pd.DataFrame(filas)
    print(T.round(3).to_string(index=False))
    T.to_csv(BA.SAL / 'revision_sesgo_metricas.csv', index=False)
    P[P.location == EST].to_csv(BA.SAL / 'revision_sesgo_predicciones_WI.csv', index=False)


if __name__ == '__main__':
    main()
