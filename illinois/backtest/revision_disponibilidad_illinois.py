"""¿El backtest usa encuestas que no estaban disponibles en el corte? (revisión del 25-oct)

FiveThirtyEight fecha cada encuesta en la MEDIANA de su campo (`polldate`). El backtest toma las encuestas con
días_mediana ≥ H (H = días del corte a la elección): una encuesta cuya mediana cae antes del corte pero que termina (o
se publica) después pasaría el filtro sin haber estado disponible. No hay fechas de cierre ni de publicación en el
histórico, así que se prueba una regla conservadora de disponibilidad:

    disponible si  mediana + L ≤ corte   ⇔   días_mediana ≥ H + L,   L = 0 (actual), 2, 4, 7

Dos maneras de aplicar L (segunda revisión del 25-oct):
  A «estrés»: solo se mueve el límite inferior → medianas en [H + L, 21] (la ventana se estrecha);
  B «ventana desplazada»: se mueven los dos límites → medianas en [H + L, 21 + L], que reproduce una ventana de 9 a 21
    días medida desde el CIERRE si L ≈ mediana→cierre. Solo a las filas de FiveThirtyEight (fechadas por mediana); las
    de 2024 ya están fechadas por el fin y no se desplazan.
LÍMITE DE LOS DATOS: raw-polls de FiveThirtyEight solo trae encuestas con mediana ≤ 21 días antes de la elección, así
que en B el tramo (21, 21 + L] no existe y la ventana sigue algo más estrecha que la de producción.
Para cada L se repiten el LOYO (G, H8, H2) y el cronológico (G con sesgo, H8 sin sesgo); la comparación justa usa las
contiendas presentes con todas las L de cada modo («comunes»).
Uso: python revision_disponibilidad_illinois.py → salida/revision_disponibilidad.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
import backtest_illinois as BM            # noqa: E402,F401  (fija H = 9 y ESTADO = IL)
import base_georgia as bt                 # noqa: E402
import motor_backtest as BA               # noqa: E402
import revision_observaciones as RO       # noqa: E402

EST = 'IL'
H0 = BA.H
RETRASOS = (0, 2, 4, 7)
MODOS = ('A estrés', 'B ventana desplazada')
VARIANTES = {'G con sesgo (producción)': ('u50', True), 'H8 sin sesgo': ('u50', False),
             'H2 indecisos proporcionales': ('uprop', True)}


def main():
    pd.set_option('display.width', 220)
    d = RO.cargar()
    d['partisan'] = d.partisan.fillna('').astype(str).str[:1].replace({'n': ''})
    years = sorted(d.year.unique())
    casa = {y: bt.efectos_casa(d[d.year != y]) for y in years}
    todas = []
    es538 = d.year < 2024
    for modo in MODOS:
        for L in RETRASOS:
            if modo.startswith('A'):
                BA.H = RO.H = H0 + L
                dd = d
            else:                                   # días «desde el cierre» ≈ mediana − L, solo en FiveThirtyEight
                BA.H = RO.H = H0
                dd = d.assign(days=np.where(es538, d.days - L, d.days))
            b = BA.construir(dd, casa, 'v11')
            P = pd.concat([BA.evaluar(b, nom, ui, se, 'sig') for nom, (ui, se) in VARIANTES.items()], ignore_index=True)
            P['marco'] = 'LOYO'
            C = RO.base_cronologica(dd)
            C = pd.concat([RO.evaluar_cronologico(C, True).assign(modelo='G con sesgo (producción)'),
                           RO.evaluar_cronologico(C, False).assign(modelo='H8 sin sesgo')], ignore_index=True)
            C['marco'] = 'cronológico'
            X = pd.concat([P, C], ignore_index=True).assign(L=L, modo=modo)
            todas.append(X[['race', 'year', 'location', 'tipo', 'k', 'modelo', 'marco', 'modo', 'L', 'mu', 'sd', 'actual',
                            'crps', 'c80']])
            print(f'{modo} · L = {L}: {b.race.nunique()} contiendas (IL {b[b.location == EST].race.nunique()}), '
                  f'k medio {b.k.mean():.2f}', flush=True)
    T = pd.concat(todas, ignore_index=True)
    filas = []
    for modo in MODOS:
        Tm = T[T.modo == modo]
        comunes = set.intersection(*[set(Tm[Tm.L == L].race) for L in RETRASOS])
        for (marco, mod, L), g in Tm.groupby(['marco', 'modelo', 'L']):
            for amb, m in (('Nacional', g.index == g.index), ('Nacional, comunes', g.race.isin(comunes)),
                           (EST, g.location == EST), (f'{EST}, comunes', (g.location == EST) & g.race.isin(comunes))):
                x = g[np.asarray(m)]
                if len(x):
                    filas.append({'modo': modo, 'marco': marco, 'modelo': mod, 'ambito': amb, 'L_dias': L, 'n': len(x),
                                  'CRPS': x.crps.mean(), 'MAE': (x.mu - x.actual).abs().mean(), 'Cob80': x.c80.mean(),
                                  'sd_media': x.sd.mean()})
    R = pd.DataFrame(filas)
    print(R.round(3).to_string(index=False))
    for modo in MODOS:
        for marco in ('LOYO', 'cronológico'):
            for amb in ('Nacional', 'Nacional, comunes', f'{EST}, comunes'):
                r = R[(R.modo == modo) & (R.marco == marco) & (R.ambito == amb)].pivot(index='L_dias', columns='modelo', values='CRPS')
                nn = R[(R.modo == modo) & (R.marco == marco) & (R.ambito == amb) & (R.modelo == 'H8 sin sesgo')].set_index('L_dias').n
                print(f'\n{modo} · {marco} · {amb}: CRPS por L (G − H8 < 0: el sesgo ayuda)')
                print(r.assign(**{'G − H8': r['G con sesgo (producción)'] - r['H8 sin sesgo'], 'n': nn}).round(3).to_string())
    R.to_csv(BA.SAL / 'revision_disponibilidad.csv', index=False)


if __name__ == '__main__':
    main()
