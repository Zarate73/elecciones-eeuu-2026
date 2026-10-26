"""¿Las encuestas comprimen los márgenes grandes? (Nueva York: Hochul +10 a +16 en las encuestas.)

Variante E (de Pennsylvania): actual = a + b·μ_G, estimada sin el año evaluado (LOYO) sobre las predicciones de
backtest_new_york.py (salida/predicciones_LOYO.csv). Se compara con G en todas las contiendas, en IL y en las de
ventaja ≥ 15 pp. Uso: python revision_escala_new_york.py (después de backtest_new_york.py) → salida/revision_escala.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as st_t

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
import backtest_new_york as BM            # noqa: E402,F401  (fija H y ESTADO)
import motor_backtest as BA               # noqa: E402

EST = 'NY'
REF = 'G  V11 + sesgo estatal contraído (Florida)'


def main():
    P = pd.read_csv(BA.SAL / 'predicciones_LOYO.csv')
    G = P[P.modelo == REF].copy()
    filas = []
    for y in sorted(G.year.unique()):
        tr, te = G[G.year != y], G[G.year == y].copy()
        a_, b_ = np.linalg.lstsq(np.c_[np.ones(len(tr)), tr.mu], tr.actual, rcond=None)[0]
        te['mu'] = a_ + b_ * te.mu
        te['escala_b'] = b_
        filas.append(te)
    E = pd.concat(filas, ignore_index=True).assign(modelo='E  G + escala del margen (LOYO)')
    E['crps'] = BA.crps_t(E.actual, E.mu, E.sd, E.nu)
    sc = E.sd * np.sqrt((E.nu - 2) / E.nu)
    E['c80'] = np.abs(E.mu - E.actual) <= st_t.ppf(.9, E.nu) * sc
    Q = pd.concat([G, E[G.columns]], ignore_index=True)
    grande = Q.race.map(G.set_index('race').mu.abs() >= 15)
    out = []
    for amb, m in (('Nacional', Q.index == Q.index), (EST, Q.location == EST), ('Ventaja ≥ 15 pp', grande),
                   (f'{EST}, ventaja ≥ 15 pp', (Q.location == EST) & grande)):
        for mod, g in Q[m].groupby('modelo'):
            fila = {'ambito': amb, 'modelo': mod, 'n': len(g), 'CRPS': g.crps.mean(), 'MAE': (g.mu - g.actual).abs().mean(),
                    'Cob80': g.c80.mean()}
            if mod != REF and Q[m].year.nunique() > 2:
                fila['P(E mejor que G)'] = BA.bootstrap_por_anio(Q, mod, REF, pd.Series(np.asarray(m), index=Q.index))
            out.append(fila)
    T = pd.DataFrame(out)
    Gg = G[G.mu.abs() >= 15]
    print(f'b medio fuera de muestra {E.escala_b.mean():.3f} (b > 1: las encuestas comprimen los márgenes)')
    print(f'Ventaja ≥ 15 pp (n = {len(Gg)}): error con signo del líder {np.mean(np.sign(Gg.mu) * (Gg.mu - Gg.actual)):+.2f} pp '
          '(negativo = el líder ganó por más de lo pronosticado)')
    print(T.round(3).to_string(index=False))
    T.to_csv(BA.SAL / 'revision_escala.csv', index=False)


if __name__ == '__main__':
    main()
