"""Backtest de ideas de la metodología de On Point Politics sobre la base elegida para Arizona.

Mismo marco que backtest_arizona.py (LOYO, H = 13, 782 contiendas). Base: V11 (con y sin sesgo estatal).
  OP1 penalización por indecisos: peso × exp(−U/15)                     (On Point: «penalty for large undecided share»)
  OP2 excluir encuestas con ≥ 20 % de indecisos (si quedan otras)          (On Point, distritos de la Cámara)
  OP3 atípicas: margen recortado a la media ± 2 DE de la contienda          (On Point: «pulled back toward the line»)
  OP4 calidad de la encuestadora: peso × 1/(1 + exceso de error² / 25),
      error estimado sin el año evaluado y contraído (k = 8)               (On Point: grades de su rating)
  OP5 OP1 + OP3 + OP4
Terceros: T2 (a + c·encuesta) contra T5 (a + c·encuesta + d·media pasada del estado)   (On Point: «typical label
draw, past state third-party vote, polls that asked»)
Fundamentales (entorno nacional + lean) NO se prueban aquí: el backtest de Georgia ya mostró que empeoran el CRPS
en gobernadores (3.655 → 3.705), y el propio backtest de On Point en gobernadores da 15 pp de error medio.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
import backtest_arizona as BA  # noqa: E402
import base_georgia as bt      # noqa: E402

H = BA.H


def calidad(train: pd.DataFrame, k: float = 8.0) -> dict:
    """Exceso de error cuadrático de cada encuestadora frente a la media de su contienda (contraído)."""
    t = train[train.days >= H].copy()
    t['dev'] = t.margin_poll - t.groupby('race').margin_poll.transform('mean')
    t = t[t.groupby('race').margin_poll.transform('size') >= 3]
    g = t.groupby('pollster_key').dev.agg(lambda s: np.sum(s ** 2)).rename('ss').to_frame()
    g['n'] = t.groupby('pollster_key').size()
    base = float(np.median(t.dev ** 2))
    g['msd'] = (g.ss + k * base) / (g.n + k)
    return (g.msd - base).clip(lower=0).to_dict()


def agregar_op(p: pd.DataFrame, house: dict, qual: dict, pen_u=False, excl_u=False, atip=False, cal=False):
    if p.empty:
        return None
    U = (100 - p.cand1_pct - p.cand2_pct - p.cand3_pct).clip(lower=0).to_numpy(float)
    if excl_u and (U < 20).sum() >= 1:
        p, U = p[U < 20], U[U < 20]
    m = p.margin_poll.to_numpy(float) - p.pollster_key.map(house).fillna(0).to_numpy(float)
    dt = (p.days - p.days.min()).to_numpy(float)
    w = np.exp(-np.log(2) * dt / 14.0) * np.sqrt(p.n.to_numpy(float))
    w = w / p.pollster_key.map(p.pollster_key.value_counts()).to_numpy(float)
    if pen_u:
        w = w * np.exp(-U / 15.0)
    if cal:
        w = w / (1 + p.pollster_key.map(qual).fillna(0).to_numpy(float) / 25.0)
    w = w / w.sum()
    if atip and len(m) >= 3:
        mu = float(w @ m); sd = float(np.sqrt(w @ (m - mu) ** 2))
        if sd > 0:
            m = np.clip(m, mu - 2 * sd, mu + 2 * sd)
    D, R, O = p.cand1_pct.to_numpy(float), p.cand2_pct.to_numpy(float), p.cand3_pct.to_numpy(float)
    Dm, Rm = float(w @ D), float(w @ R)
    mm = float(w @ m)
    # se conserva D+R del promedio y se impone el margen corregido
    s = Dm + Rm
    return {'D': (s + mm) / 2, 'R': (s - mm) / 2, 'O': float(w @ O), 'U': max(100 - s - float(w @ O), 0.0),
            'k': int(p.pollster_key.nunique())}


def construir_op(d, casa, qual, **kw):
    filas = []
    for race, p in d.groupby('race'):
        y = int(p.year.iloc[0])
        a = agregar_op(p[p.days >= H], casa[y][0], qual[y], **kw)
        if a is None:
            continue
        filas.append({'race': race, 'year': y, 'location': p.location.iloc[0], 'tipo': p.type_simple.iloc[0],
                      'runoff': bool(p.runoff.iloc[0]), **a, 'actual': float(p.margin_actual.iloc[0]),
                      'D_real': float(p.cand1_actual.iloc[0]), 'R_real': float(p.cand2_actual.iloc[0]),
                      'O_real': float(p.otros_real.iloc[0])})
    return pd.DataFrame(filas)


VARIANTES = {
    'base': {},
    'OP1 penalización por indecisos': {'pen_u': True},
    'OP2 excluir ≥20 % indecisos': {'excl_u': True},
    'OP3 recorte de atípicas (±2 DE)': {'atip': True},
    'OP4 calidad de la encuestadora': {'cal': True},
    'OP5 OP1 + OP3 + OP4': {'pen_u': True, 'atip': True, 'cal': True},
}


def terceros(P: pd.DataFrame) -> pd.DataFrame:
    out = []
    for y in sorted(P.year.unique()):
        te, tr = P[P.year == y].copy(), P[P.year != y]
        past = lambda df, yy: df.location.map(tr[tr.year < yy].groupby('location').O_real.mean())
        trp = tr.assign(hist=tr.apply(lambda r: tr[(tr.location == r.location) & (tr.year < r.year)].O_real.mean(), axis=1))
        trp['hist'] = trp['hist'].fillna(trp.O_real.mean())
        A2 = np.c_[np.ones(len(trp)), trp.O]
        c2 = np.linalg.lstsq(A2, trp.O_real, rcond=None)[0]
        A5 = np.c_[np.ones(len(trp)), trp.O, trp['hist']]
        c5 = np.linalg.lstsq(A5, trp.O_real, rcond=None)[0]
        h = past(te, y).fillna(tr.O_real.mean())
        te['T2'] = np.clip(c2[0] + c2[1] * te.O, 0, None)
        te['T5'] = np.clip(c5[0] + c5[1] * te.O + c5[2] * h, 0, None)
        out.append(te)
    Q = pd.concat(out)
    filas = []
    for amb, m in [('Nacional', Q.index == Q.index), ('AZ_todas', Q.location == 'AZ'), ('Con terceros > 3%', Q.O_real > 3)]:
        g = Q[m]
        for col in ('T2', 'T5'):
            Dp = (100 - g[col] + g.mu) / 2
            filas.append({'ambito': amb, 'regla': col, 'n': len(g), 'MAE_terceros': (g[col] - g.O_real).abs().mean(),
                          'MAE_%D': (Dp - g.D_real).abs().mean()})
    return pd.DataFrame(filas)


def main():
    d = BA.cargar()
    years = sorted(d.year.unique())
    casa = {y: bt.efectos_casa(d[d.year != y]) for y in years}
    qual = {y: calidad(d[d.year != y]) for y in years}
    bases = {n: construir_op(d, casa, qual, **kw) for n, kw in VARIANTES.items()}
    comunes = set.intersection(*[set(b.race) for b in bases.values()])
    P = []
    for n, b in bases.items():
        b = b[b.race.isin(comunes)].reset_index(drop=True)
        for sesgo, suf in ((True, ' | con sesgo estatal'), (False, ' | sin sesgo estatal')):
            P.append(BA.evaluar(b, n + suf, 'u50', sesgo, 'sig'))
    P = pd.concat(P, ignore_index=True)
    R = BA.resumen(P)
    boot = []
    for amb, sel in [('Nacional', None), ('AZ_todas', P.location == 'AZ')]:
        for v in P.modelo.unique():
            ref = 'base' + v.split('base')[-1] if v.startswith('base') else 'base' + v[v.index(' | '):]
            if v == ref:
                continue
            boot.append({'ambito': amb, 'variante': v, 'P(mejor que su base)': BA.bootstrap_por_anio(P, v, ref, sel, B=1000)})
    T = terceros(P[P.modelo == 'base | sin sesgo estatal'])
    R.to_csv(BA.SAL / 'onpoint_metricas.csv', index=False)
    pd.DataFrame(boot).to_csv(BA.SAL / 'onpoint_bootstrap.csv', index=False)
    T.to_csv(BA.SAL / 'onpoint_terceros.csv', index=False)
    return R, pd.DataFrame(boot), T


if __name__ == '__main__':
    pd.set_option('display.width', 220)
    R, Bt, T = main()
    for amb in ('Nacional', 'Nacional_Gob', 'AZ_todas'):
        print('\n==', amb)
        print(R[R.ambito == amb].drop(columns='ambito').sort_values('CRPS').round(3).to_string(index=False))
    print('\n== Bootstrap por año')
    print(Bt.pivot(index='variante', columns='ambito', values='P(mejor que su base)').round(3).to_string())
    print('\n== Terceros'); print(T.round(3).to_string(index=False))
