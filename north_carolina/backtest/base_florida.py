"""Carga del histórico (538 + 2024) y utilidades del backtest de Florida, reutilizadas en Nevada (backtest_nevada.py).

Marco: leave-one-year-out (LOYO); todo parámetro (efectos de casa, τ, s, ν, sesgo estatal, cuota de indecisos)
se estima sin el año evaluado; el sesgo estatal además solo con años ANTERIORES.
Datos: FiveThirtyEight raw-polls (Gob/Sen/Pres 1998–2022) + 2024: 45 contiendas con encuestas finales de Wikipedia
(incluye Florida Presidente y Senado 2024), GA Pres y AZ Pres/Sen 2024.
Horizonte: encuestas con ≥ 12 días antes de la elección (corte 22-oct-2026 → 3-nov).

Variantes:
  G   Georgia V11 (sesgo estatal contraído por Bayes empírico)
  H8  V11 sin sesgo estatal (modelo de Arizona)
  F1  V11 con sesgo estatal sin contraer (todo el error pasado del estado)
  F2  V11 + reparto de indecisos de la primaria de Florida (FIX v8: 40 % proporcional, 35 % fragmentado,
      25 % consolidación hacia el líder)
  F3  F2 sin sesgo estatal
  y las de Arizona: indecisos proporcionales / cuota R estimada / escenarios AZ, Dirichlet, pesos ∝ n, vida media 10 d.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
import base_georgia as bt          # noqa: E402
import motor_backtest as BA        # noqa: E402

BA.H = 12
BA.ESTADO = 'FL'
BA.SAL = BASE / 'salida'
BA.SAL.mkdir(exist_ok=True)
_cargar_az = BA.cargar


def cargar() -> pd.DataFrame:
    d = _cargar_az()                                       # 538 + GA Pres 2024 + AZ 2024
    w = pd.read_csv(BASE / 'data' / 'encuestas_2024_wiki.csv', parse_dates=['polldate', 'electiondate'])
    w['rk'] = w['pop'].map({'LV': 0, 'RV': 1, 'A': 2}).fillna(3)
    w = w.sort_values('rk').drop_duplicates(['race', 'pollster', 'polldate'])
    w = w.assign(runoff=False, samplesize=w.n, cand1_pct=w.D, cand2_pct=w.R, cand3_pct=w.otros)
    w['partisan'] = w.partisan.fillna('')
    w['days'] = (w.electiondate - w.polldate).dt.days
    w['margin_poll'] = w.cand1_pct - w.cand2_pct
    w['margin_actual'] = w.cand1_actual - w.cand2_actual
    w['major_poll'] = w.cand1_pct + w.cand2_pct
    w['n'] = pd.to_numeric(w.samplesize, errors='coerce').fillna(600).clip(100, 3000)
    w['pollster_key'] = w.pollster.str.lower().str.replace(r'[^a-z]', '', regex=True).str[:14]
    w['cand3_pct'] = pd.to_numeric(w.cand3_pct, errors='coerce').fillna(0.0)
    w['otros_real'] = (100 - w.cand1_actual - w.cand2_actual).clip(lower=0)
    return pd.concat([d, w[d.columns]], ignore_index=True)


VARIANTES = {   # nombre: (media, indecisos, sesgo estatal, incertidumbre)
    'G  Georgia V11 (sesgo contraído)': ('v11', 'u50', True, 'sig'),
    'H8 V11 sin sesgo estatal (Arizona)': ('v11', 'u50', False, 'sig'),
    'F1 V11 sesgo estatal sin contraer': ('v11', 'u50', 'raw', 'sig'),
    'F2 V11 + indecisos de la primaria FL': ('v11', 'ufl', True, 'sig'),
    'F3 F2 sin sesgo estatal': ('v11', 'ufl', False, 'sig'),
    'H1 V11 + escenarios de indecisos de AZ': ('v11', 'umix', True, 'sig'),
    'H2 V11 + indecisos proporcionales': ('v11', 'uprop', True, 'sig'),
    'H3 V11 + cuota R de indecisos estimada': ('v11', 'ufit', True, 'sig'),
    'H4 V11 + Dirichlet y shocks': ('v11', 'u50', True, 'dir'),
    'H6 V11 con vida media 10 d': ('v11_hl10', 'u50', True, 'sig'),
    'H7 V11 con pesos ∝ n (primaria FL)': ('v11_n', 'u50', True, 'sig'),
}
REF = 'G  Georgia V11 (sesgo contraído)'


def errores_estado(b: pd.DataFrame, estado: str) -> pd.DataFrame:
    """Error del promedio de encuestas (V11, sin sesgo) por contienda del estado: positivo = encuestas pro-D."""
    x = b[b.location == estado].copy()
    x['error_pp'] = (x.D - x.R) - x.actual
    return x[['race', 'year', 'tipo', 'k', 'D', 'R', 'actual', 'error_pp']].sort_values('year')


def main():
    d = cargar()
    years = sorted(d.year.unique())
    casa = {y: bt.efectos_casa(d[d.year != y]) for y in years}
    bases = {m: BA.construir(d, casa, m) for m in ('v11', 'v11_hl10', 'v11_n')}
    comunes = set.intersection(*[set(b.race) for b in bases.values()])
    bases = {m: b[b.race.isin(comunes)].reset_index(drop=True) for m, b in bases.items()}
    P = pd.concat([BA.evaluar(bases[me], nom, ui, se, inc) for nom, (me, ui, se, inc) in VARIANTES.items()],
                  ignore_index=True)
    R = BA.resumen(P)
    T, _ = BA.porcentajes(bases['v11'], P[P.modelo.isin([REF, 'H8 V11 sin sesgo estatal (Arizona)'])])
    boot = []
    for amb, sel in [('Nacional', None), ('Nacional_Gob', P.tipo == 'Gov-G'), ('FL_todas', P.location == 'FL')]:
        for v in VARIANTES:
            if v != REF:
                boot.append({'ambito': amb, 'variante': v, 'P(variante mejor que G)': BA.bootstrap_por_anio(P, v, REF, sel)})
    Bt = pd.DataFrame(boot)
    E = errores_estado(bases['v11'], 'FL')
    # autocorrelación del error relativo de FL (error FL − error medio nacional del año) entre ciclos
    nac = bases['v11'].assign(e=lambda x: (x.D - x.R) - x.actual).groupby('year').e.mean()
    rel = E.groupby('year').error_pp.mean() - nac.reindex(E.year.unique())
    rel = rel.dropna()
    ac = float(np.corrcoef(rel.values[:-1], rel.values[1:])[0, 1]) if len(rel) > 3 else np.nan
    P.to_csv(BA.SAL / 'predicciones_LOYO.csv', index=False)
    R.to_csv(BA.SAL / 'metricas_margen.csv', index=False)
    T.to_csv(BA.SAL / 'metricas_porcentajes.csv', index=False)
    Bt.to_csv(BA.SAL / 'bootstrap_vs_G.csv', index=False)
    E.to_csv(BA.SAL / 'errores_encuestas_FL.csv', index=False)
    pd.DataFrame({'anio': rel.index, 'error_relativo_FL_pp': rel.values}).to_csv(BA.SAL / 'error_relativo_FL.csv', index=False)
    return d, bases, P, R, T, Bt, E, rel, ac


if __name__ == '__main__':
    pd.set_option('display.width', 230)
    d, bases, P, R, T, Bt, E, rel, ac = main()
    print(f'Contiendas (H={BA.H}): {P.race.nunique()} · FL: {P[P.location == "FL"].race.nunique()} · 2024: {P[P.year == 2024].race.nunique()}')
    for amb in R.ambito.unique():
        print('\n==', amb)
        print(R[R.ambito == amb].drop(columns='ambito').sort_values('CRPS').round(3).to_string(index=False))
    print('\n== Bootstrap por año: P(variante con menor CRPS que G)')
    print(Bt.pivot(index='variante', columns='ambito', values='P(variante mejor que G)').round(3).to_string())
    print('\n== Errores de las encuestas en FL (V11 sin sesgo; + = pro-D)')
    print(E.round(2).to_string(index=False))
    print('\nError relativo FL por año (FL − nacional):', rel.round(2).to_dict(), ' autocorrelación:', round(ac, 2))
    print('\n== Terceros'); print(T[T.ambito != 'Con terceros > 3%'].round(2).to_string(index=False))
