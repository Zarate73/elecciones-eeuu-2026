"""¿Funciona el modelo de gobernador (V11 + sesgo estatal) para el SENADO? Pruebas específicas de North Carolina.

Todas son leave-one-year-out (LOYO) con la ventana de producción (7 ≤ días ≤ 21) y se evalúan en las contiendas de
Senado (nacional y NC). Cada variante cambia una sola pieza de G:
  G      producción: V11 + sesgo estatal contraído (todas las contiendas del estado) + σ = √(τ² + s²/k) nacional
  S1     σ (τ, s, ν) calibrada solo con contiendas del MISMO cargo
  S2     sesgo estatal estimado solo con contiendas del mismo cargo (estado × cargo)
  S3     G + sesgo nacional del cargo: error medio de las encuestas del mismo cargo en años ANTERIORES (vida media 4 años)
  S4     G mezclado con fundamentales: μ = μ_G + β·(fund − μ_G), fund = lean presidencial previo + entorno del año
         (mediana de encuesta − lean en las OTRAS contiendas del año: no usa resultados), β estimado sin el año evaluado
         solo con contiendas del mismo cargo
  S5     G con escala del margen por cargo: actual = a + b·μ_G (LOYO, mismo cargo): ¿comprimen las encuestas las ventajas
         grandes en el Senado? (la carrera de NC hoy: Cooper +10)
  H8     sin sesgo estatal (control)
Uso: python revision_senado_north_carolina.py (después de backtest_north_carolina.py) → salida/revision_senado*.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as st_t

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
import backtest_north_carolina as BM   # noqa: E402,F401  (fija H = 7 y ESTADO = NC)
import base_georgia as bt              # noqa: E402
import motor_backtest as BA            # noqa: E402
import revision_observaciones as RO    # noqa: E402

EST = 'NC'
LOG: list[str] = []


def p_(*x):
    s = ' '.join(str(v) for v in x)
    print(s)
    LOG.append(s)


def metricas_t(P: pd.DataFrame) -> pd.DataFrame:
    P = P.copy()
    P['crps'] = BA.crps_t(P.actual, P.mu, P.sd, P.nu)
    sc = P.sd * np.sqrt((P.nu - 2) / P.nu)
    P['pD'] = st_t.cdf(P.mu / sc, P.nu)
    P['c80'] = np.abs(P.mu - P.actual) <= st_t.ppf(.9, P.nu) * sc
    P['c95'] = np.abs(P.mu - P.actual) <= st_t.ppf(.975, P.nu) * sc
    P['sd_eff'] = P.sd
    return P


def sesgo_cargo_pasado(tr: pd.DataFrame, y: int, tipo: str) -> float:
    p = tr[(tr.year < y) & (tr.tipo == tipo)]
    if len(p) < 10:
        return 0.0
    w = 0.5 ** ((y - p.year) / 4.0)
    return float(np.average(p.mu0 - p.actual, weights=w))


def evaluar_variantes(b: pd.DataFrame) -> pd.DataFrame:
    b = b.copy()
    b['mu0'] = b.D - b.R
    leans = bt.lean_estatal(RO.cargar())
    b['lean'] = [leans.get((l, y), np.nan) for l, y in zip(b.location, b.year)]
    b['env'] = np.nan
    for i, r in b.iterrows():
        o = b[(b.year == r.year) & (b.race != r.race) & b.lean.notna() & ~b.runoff]
        if len(o) >= 5:
            b.at[i, 'env'] = float((o.mu0 - o.lean).median())
    b['fund'] = b.lean + b.env
    out = []
    for y in sorted(b.year.unique()):
        te, tr = b[b.year == y].copy(), b[b.year != y].copy()
        bias = BA.sesgo_pasado(tr, y)
        bc = tr.assign(location=tr.location + '_' + tr.tipo)
        bias_c = BA.sesgo_pasado(bc, y)
        te['mu_G'] = te.mu0 - te.location.map(bias).fillna(0.0)
        tr['mu_G'] = tr.mu0                       # en entrenamiento, el sesgo de cada estado se aproxima a 0 en media
        e = (tr.mu0 - tr.actual).to_numpy()
        tau, s = bt.ajustar_sigma(e, tr.k.to_numpy())
        nu = BA.nu_entrenado(e, tr.k.to_numpy(), tau, s)
        base = te.assign(sd=np.sqrt(tau ** 2 + s ** 2 / np.maximum(te.k, 1)), nu=nu)
        out.append(base.assign(mu=te.mu_G, modelo='G'))
        out.append(base.assign(mu=te.mu0, modelo='H8 sin sesgo'))
        # S2 sesgo por estado × cargo
        out.append(base.assign(mu=te.mu0 - (te.location + '_' + te.tipo).map(bias_c).fillna(0.0), modelo='S2 sesgo por cargo'))
        for tipo, g in te.groupby('tipo'):
            gt = tr[tr.tipo == tipo]
            et = (gt.mu0 - gt.actual).to_numpy()
            ta, sa = bt.ajustar_sigma(et, gt.k.to_numpy())
            na = BA.nu_entrenado(et, gt.k.to_numpy(), ta, sa)
            out.append(base.loc[g.index].assign(sd=np.sqrt(ta ** 2 + sa ** 2 / np.maximum(g.k, 1)), nu=na,
                                                mu=g.mu_G, modelo='S1 σ por cargo'))
            sn = sesgo_cargo_pasado(tr, y, tipo)
            out.append(base.loc[g.index].assign(mu=g.mu_G - sn, modelo='S3 G + sesgo nacional del cargo', sesgo_cargo=sn))
            f = gt[gt.fund.notna()]
            beta = float(np.clip(np.sum((f.fund - f.mu0) * (f.actual - f.mu0)) / np.sum((f.fund - f.mu0) ** 2), 0, 1)) if len(f) > 10 else 0.0
            fu = g.fund.where(g.fund.notna(), g.mu_G)
            out.append(base.loc[g.index].assign(mu=g.mu_G + beta * (fu - g.mu_G), modelo='S4 G + fundamentales', beta=beta))
            a_, b_ = np.linalg.lstsq(np.c_[np.ones(len(gt)), gt.mu0], gt.actual, rcond=None)[0]
            out.append(base.loc[g.index].assign(mu=a_ + b_ * g.mu_G, modelo='S5 G + escala por cargo', escala_b=b_))
    return metricas_t(pd.concat(out, ignore_index=True))


def main():
    pd.set_option('display.width', 220)
    d = RO.cargar()
    d['partisan'] = d.partisan.fillna('').astype(str).str[:1].replace({'n': ''})
    years = sorted(d.year.unique())
    casa = {y: bt.efectos_casa(d[d.year != y]) for y in years}
    b = BA.construir(d, casa, 'v11')
    P = evaluar_variantes(b)
    gr = P[P.modelo == 'G'].set_index('race').mu.abs()
    amb = {'Nacional': P.index == P.index, 'Nacional_Sen': P.tipo == 'Sen-G', 'Nacional_Gob': P.tipo == 'Gov-G',
           'Sen, ventaja ≥ 8 pp': (P.tipo == 'Sen-G') & (P.race.map(gr) >= 8),
           'Sen 2014+': (P.tipo == 'Sen-G') & (P.year >= 2014),
           EST: P.location == EST, f'{EST}_Sen': (P.location == EST) & (P.tipo == 'Sen-G')}
    filas = []
    for a, m in amb.items():
        for mod, g in P[m].groupby('modelo'):
            e = g.mu - g.actual
            fila = {'ambito': a, 'modelo': mod, 'n': len(g), 'CRPS': g.crps.mean(), 'MAE': e.abs().mean(),
                    'sesgo': e.mean(), 'Cob80': g.c80.mean(), 'Cob95': g.c95.mean(),
                    'Brier': ((g.pD - (g.actual > 0)) ** 2).mean(), 'sd_media': g.sd.mean()}
            if mod != 'G' and P[m].year.nunique() > 2:
                fila['P(mejor que G)'] = BA.bootstrap_por_anio(P, mod, 'G', pd.Series(np.asarray(m), index=P.index))
            filas.append(fila)
    T = pd.DataFrame(filas)
    for a in amb:
        p_(f'\n== {a}')
        p_(T[T.ambito == a].drop(columns='ambito').sort_values('CRPS').round(3).to_string(index=False))
    S = P[P.modelo == 'G']
    e = S.assign(err=S.mu0 - S.actual).groupby('tipo').agg(n=('err', 'size'), sesgo_encuestas=('err', 'mean'),
                                                             MAE=('err', lambda x: x.abs().mean()))
    p_('\n== Error de las encuestas (V11 sin sesgo) por cargo, nacional (+ = pro-D)')
    p_(e.round(2).to_string())
    p_('\n== Error por año en el Senado (nacional, + = pro-D)')
    p_(S[S.tipo == 'Sen-G'].assign(err=lambda x: x.mu0 - x.actual).groupby('year').err.agg(['size', 'mean']).round(2).T.to_string())
    s4 = P[P.modelo == 'S4 G + fundamentales']
    p_(f"\nβ de fundamentales (Senado): media {s4[s4.tipo == 'Sen-G'].beta.mean():.3f}; "
       f"escala b (Senado): {P[(P.modelo == 'S5 G + escala por cargo') & (P.tipo == 'Sen-G')].escala_b.mean():.3f}; "
       f"sesgo nacional del cargo (Senado, media de los años): "
       f"{P[(P.modelo == 'S3 G + sesgo nacional del cargo') & (P.tipo == 'Sen-G')].sesgo_cargo.mean():+.2f}")
    cols = ['race', 'k', 'mu0', 'mu', 'sd', 'actual', 'crps']
    p_(f'\n== Contiendas de {EST} (G)')
    p_(S[S.location == EST][cols].sort_values('race').round(2).to_string(index=False))
    T.to_csv(BA.SAL / 'revision_senado.csv', index=False)
    P[P.location == EST].to_csv(BA.SAL / 'revision_senado_predicciones_NC.csv', index=False)
    (BA.SAL / 'revision_senado.txt').write_text('\n'.join(LOG), encoding='utf-8')


if __name__ == '__main__':
    main()
