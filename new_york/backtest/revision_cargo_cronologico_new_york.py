"""Validación cronológica del sesgo estimado por cargo (Gob con Gob, Sen con Sen, Pres con Pres) frente a «todas».

Sesgo por cargo frente a «todas» (en Nueva York por cargo es peor también en LOYO, P = 0.04). LOYO usa años futuros;
aquí solo se usan contiendas anteriores al año evaluado (como en producción).
Uso: python revision_cargo_cronologico_texas.py → salida/revision_cargo_cronologico.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
import backtest_new_york as BM            # noqa: E402,F401  (fija H = 9 y ESTADO = NY)
import motor_backtest as BA            # noqa: E402
import revision_observaciones as RO    # noqa: E402

EST = 'NY'


def main():
    pd.set_option('display.width', 200)
    d = RO.cargar()
    d['partisan'] = d.partisan.fillna('').astype(str).str[:1].replace({'n': ''})
    bc = RO.base_cronologica(d)
    C = [RO.evaluar_cronologico(bc, True).assign(modelo='G todas'),
         RO.evaluar_cronologico(bc, False).assign(modelo='sin sesgo')]
    cc = bc.assign(loc_real=bc.location, location=bc.location + '_' + bc.tipo)
    g = RO.evaluar_cronologico(cc, True)
    g = g.assign(location=g.location.str.split('_').str[0], modelo='G por cargo')
    C = pd.concat(C + [g.drop(columns='loc_real', errors='ignore')], ignore_index=True)
    filas = []
    for amb, m in (('Nacional', C.index == C.index), ('Nacional_Gob', C.tipo == 'Gov-G'), (EST, C.location == EST),
                   (f'{EST}_Gob', (C.location == EST) & (C.tipo == 'Gov-G'))):
        for mod, x in C[m].groupby('modelo'):
            fila = {'ambito': amb, 'modelo': mod, 'n': len(x), 'CRPS': x.crps.mean(), 'MAE': (x.mu - x.actual).abs().mean(),
                    'Cob80': x.c80.mean()}
            if mod != 'G todas' and C[m].year.nunique() > 2:
                fila['P(mejor que G todas)'] = BA.bootstrap_por_anio(C, mod, 'G todas', pd.Series(np.asarray(m), index=C.index))
            filas.append(fila)
    T = pd.DataFrame(filas)
    print(T.round(3).to_string(index=False))
    T.to_csv(BA.SAL / 'revision_cargo_cronologico.csv', index=False)


if __name__ == '__main__':
    main()
