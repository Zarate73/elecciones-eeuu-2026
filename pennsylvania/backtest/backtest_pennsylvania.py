"""Backtest para la general de Pennsylvania (gobernador 2026, corte 23-oct → 11 días a la elección).

Base: Nevada v1.1.0 / Florida v1.1.0 (Georgia V11 + sesgo estatal contraído + terceros con «no reportado» ≠ 0 +
mercados) y la regla de Arizona (sin sesgo). Piezas específicas de Pennsylvania:
  - ventaja enorme del gobernador (Shapiro +20 a +25) con muchos indecisos en algunas encuestas → ¿subestiman las
    encuestas los márgenes grandes? Variante E (escala del margen estimada fuera de muestra) y repartos de indecisos;
  - mezcla de encuestas RV y LV con indecisos muy distintos (F&M y PennLive con 14–19 % de indecisos);
  - encuestas partidistas (Susquehanna R, National Public Affairs R, Z to A D).

Marco: leave-one-year-out con la ventana de producción (11 ≤ días ≤ 21), 1998–2024, más validación cronológica.
Uso: python backtest_pennsylvania.py   → salida/*.csv y salida/consola.txt
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
import base_florida as BF          # noqa: E402  (carga: 538 + 2024)
import base_georgia as bt              # noqa: E402
import motor_backtest as BA            # noqa: E402
import revision_observaciones as RO    # noqa: E402  (base cronológica, terceros con «reportado»)

EST = 'PA'
BA.H = 11
BA.ESTADO = EST
BA.SAL = BASE / 'salida'
BA.SAL.mkdir(exist_ok=True)
RO.SAL = BA.SAL
RO.ESTADO = EST
RO.H = BA.H
LOG: list[str] = []


def p_(*x):
    s = ' '.join(str(v) for v in x)
    print(s)
    LOG.append(s)


# ----------------------------------------------------------------------------- promedio con variantes partidistas
def construir_part(d: pd.DataFrame, casa: dict, regla: str) -> pd.DataFrame:
    """Como motor.construir (V11), con tratamiento de encuestas de patrocinio partidista:
    casa_part : firma con historia → su efecto de casa; sin historia → efecto medio de su patrocinador (D o R)
    sin_part  : se descartan las encuestas partidistas si en la ventana hay al menos una no partidista
    medio_part: las encuestas partidistas pesan la mitad."""
    filas = []
    for race, p in d.groupby('race'):
        y = int(p.year.iloc[0])
        q = p[(p.days >= BA.H) & (p.days <= BA.VENTANA)].copy()
        if q.empty:
            continue
        house, part = casa[y]
        lado = q.partisan.fillna('').astype(str).str[:1]
        es_part = lado.isin(['D', 'R'])
        if regla == 'sin_part' and (~es_part).any():
            q, lado, es_part = q[~es_part], lado[~es_part], es_part[~es_part]
        adj = q.pollster_key.map(house)
        if regla == 'casa_part':
            adj = adj.fillna(lado.map(part))
        adj = adj.fillna(0).to_numpy(float)
        dt = (q.days - q.days.min()).to_numpy(float)
        w = np.exp(-np.log(2) * dt / 14.0) * np.sqrt(q.n.to_numpy(float))
        w = w / q.pollster_key.map(q.pollster_key.value_counts()).to_numpy(float)
        if regla == 'medio_part':
            w = w * np.where(es_part, 0.5, 1.0)
        w = w / w.sum()
        Dm, Rm, Om = float(w @ q.cand1_pct), float(w @ q.cand2_pct), float(w @ q.cand3_pct)
        a = float(w @ adj)
        filas.append({'race': race, 'year': y, 'location': p.location.iloc[0], 'tipo': p.type_simple.iloc[0],
                      'runoff': bool(p.runoff.iloc[0]), 'D': Dm - a / 2, 'R': Rm + a / 2, 'O': Om,
                      'U': max(100 - Dm - Rm - Om, 0.0), 'k': int(q.pollster_key.nunique()),
                      'neff': 1 / float(np.sum(w ** 2)), 'frac_part': float(w[es_part.to_numpy()].sum()),
                      'actual': float(p.margin_actual.iloc[0]), 'D_real': float(p.cand1_actual.iloc[0]),
                      'R_real': float(p.cand2_actual.iloc[0]), 'O_real': float(p.otros_real.iloc[0])})
    return pd.DataFrame(filas)


VARIANTES = {   # nombre: (base, indecisos, sesgo, incertidumbre)
    'G  V11 + sesgo estatal contraído (Florida)': ('v11', 'u50', True, 'sig'),
    'H8 V11 sin sesgo estatal (Arizona)': ('v11', 'u50', False, 'sig'),
    'F1 V11 + sesgo estatal sin contraer': ('v11', 'u50', 'raw', 'sig'),
    'H3 V11 + cuota R de indecisos estimada': ('v11', 'ufit', True, 'sig'),
    'H2 V11 + indecisos proporcionales': ('v11', 'uprop', True, 'sig'),
    'P1 casa + patrocinador si la firma no tiene historia': ('casa_part', 'u50', True, 'sig'),
    'P2 sin encuestas partidistas (si hay no partidistas)': ('sin_part', 'u50', True, 'sig'),
    'P3 encuestas partidistas pesan la mitad': ('medio_part', 'u50', True, 'sig'),
    'P2s P2 sin sesgo estatal': ('sin_part', 'u50', False, 'sig'),
}
REF = 'G  V11 + sesgo estatal contraído (Florida)'


def main():
    pd.set_option('display.width', 230)
    d = RO.cargar()                                         # conserva si la encuesta reporta terceros
    d['partisan'] = d.partisan.fillna('').astype(str).str[:1].replace({'n': ''})
    years = sorted(d.year.unique())
    casa = {y: bt.efectos_casa(d[d.year != y]) for y in years}
    bases = {'v11': BA.construir(d, casa, 'v11')}
    for r in ('casa_part', 'sin_part', 'medio_part'):
        bases[r] = construir_part(d, casa, r)
    comunes = set.intersection(*[set(b.race) for b in bases.values()])
    bases = {m: b[b.race.isin(comunes)].reset_index(drop=True) for m, b in bases.items()}
    P = pd.concat([BA.evaluar(bases[me], nom, ui, se, inc) for nom, (me, ui, se, inc) in VARIANTES.items()],
                  ignore_index=True)
    R = BA.resumen(P)
    boot = []
    for amb, sel in [('Nacional', None), ('Nacional_Gob', P.tipo == 'Gov-G'), (f'{EST}_todas', P.location == EST)]:
        for v in VARIANTES:
            if v != REF:
                boot.append({'ambito': amb, 'variante': v, 'P(variante mejor que G)': BA.bootstrap_por_anio(P, v, REF, sel)})
    Bt = pd.DataFrame(boot)
    E = BF.errores_estado(bases['v11'], EST)
    nac = bases['v11'].assign(e=lambda x: (x.D - x.R) - x.actual).groupby('year').e.mean()
    rel = (E.groupby('year').error_pp.mean() - nac.reindex(E.year.unique())).dropna()
    ac = float(np.corrcoef(rel.values[:-1], rel.values[1:])[0, 1]) if len(rel) > 3 else np.nan
    pp = bases['v11'][['race', 'location', 'year']].merge(bases['casa_part'][['race', 'frac_part']], on='race')

    p_(f'Contiendas (H={BA.H}, ventana 12–21 días): {P.race.nunique()} · {EST}: {P[P.location == EST].race.nunique()}')
    for amb in R.ambito.unique():
        p_(f'\n== {amb}')
        p_(R[R.ambito == amb].drop(columns='ambito').sort_values('CRPS').round(3).to_string(index=False))
    p_('\n== Bootstrap por año: P(variante con menor CRPS que G)')
    p_(Bt.pivot(index='variante', columns='ambito', values='P(variante mejor que G)').round(3).to_string())
    p_(f'\n== Errores de las encuestas en {EST} (V11 sin sesgo; + = pro-D): {int((E.error_pp > 0).sum())} pro-D de {len(E)}')
    p_(E.round(2).to_string(index=False))
    p_(f'\nError relativo {EST} por año ({EST} − nacional): {rel.round(2).to_dict()} · autocorrelación {ac:.2f}')
    p_(f'Peso de encuestas partidistas en la ventana: media nacional {pp.frac_part.mean():.2f}; contiendas con > 50 %: '
       f'{int((pp.frac_part > .5).sum())}')

    # validación cronológica: con y sin sesgo
    bc = RO.base_cronologica(d)
    C = pd.concat([RO.evaluar_cronologico(bc, True).assign(modelo='G con sesgo'),
                   RO.evaluar_cronologico(bc, False).assign(modelo='H8 sin sesgo')], ignore_index=True)
    filas = []
    for amb, m in (('Nacional', C.index == C.index), ('Nacional_Gob', C.tipo == 'Gov-G'), (EST, C.location == EST),
                   (f'{EST}_Gob', (C.location == EST) & (C.tipo == 'Gov-G')), (f'{EST}_2016+', (C.location == EST) & (C.year >= 2016))):
        for mod, g in C[m].groupby('modelo'):
            filas.append({'ambito': amb, 'modelo': mod, 'n': len(g), 'CRPS': g.crps.mean(), 'sesgo': (g.mu - g.actual).mean()})
        filas.append({'ambito': amb, 'modelo': 'P(sin sesgo mejor)',
                      'CRPS': BA.bootstrap_por_anio(C, 'H8 sin sesgo', 'G con sesgo', pd.Series(np.asarray(m), index=C.index))})
    Cr = pd.DataFrame(filas)
    p_('\n== Validación estrictamente cronológica (2004–2024)')
    p_(Cr.round(3).to_string(index=False))

    # terceros (T0/T2/T4) en PA
    Pg = P[P.modelo == REF]
    orep = RO.otros_reportados(d, casa)
    T, _ = RO.comparar_terceros(bases['v11'], Pg, orep)
    p_('\n== Terceros')
    p_(T.round(3).to_string(index=False))

    # ---- E: escala del margen (¿las encuestas comprimen los márgenes grandes?), estimada sin el año evaluado
    from scipy.stats import t as st_t
    G = P[P.modelo == REF].copy()
    filas_e = []
    for y in sorted(G.year.unique()):
        tr, te = G[G.year != y], G[G.year == y].copy()
        A = np.c_[np.ones(len(tr)), tr.mu]
        a_, b_ = np.linalg.lstsq(A, tr.actual, rcond=None)[0]
        te['mu'] = a_ + b_ * te.mu
        te['escala_b'] = b_
        filas_e.append(te)
    E_ = pd.concat(filas_e, ignore_index=True)
    E_['modelo'] = 'E  G + escala del margen (LOYO)'
    E_['crps'] = BA.crps_t(E_.actual, E_.mu, E_.sd, E_.nu)
    sc = E_.sd * np.sqrt((E_.nu - 2) / E_.nu)
    E_['pD'] = st_t.cdf(E_.mu / sc, E_.nu)
    E_['c80'] = np.abs(E_.mu - E_.actual) <= st_t.ppf(.9, E_.nu) * sc
    E_['c95'] = np.abs(E_.mu - E_.actual) <= st_t.ppf(.975, E_.nu) * sc
    P = pd.concat([P, E_[P.columns]], ignore_index=True)
    p_(f"\n== Variante E: actual = a + b·μ_G; b medio fuera de muestra {E_.escala_b.mean():.3f} (b > 1: las encuestas comprimen)")
    grande = P.merge(G[['race']].assign(gran=(G.mu.abs() >= 15).values), on='race', how='left').gran.fillna(False)
    Rg = BA.resumen(P[grande.values].assign())
    Rg = Rg[Rg.ambito == 'Nacional'].assign(ambito='Ventaja ≥ 15 pp (nacional)')
    for amb, sel in [('Nacional', None), (f'{EST}_todas', P.location == EST), ('Ventaja ≥ 15 pp', grande)]:
        prob = BA.bootstrap_por_anio(P, 'E  G + escala del margen (LOYO)', REF, sel)
        p_(f'   P(E mejor que G) {amb}: {prob:.3f}')
    p_(Rg.drop(columns='ambito').sort_values('CRPS').round(3).to_string(index=False))
    Gg = G[G.mu.abs() >= 15]
    p_(f"   En contiendas con ventaja ≥ 15 pp (n = {len(Gg)}): error medio con signo del líder "
       f"{np.mean(np.sign(Gg.mu) * (Gg.mu - Gg.actual)):+.2f} pp (negativo = el líder ganó por más de lo pronosticado)")
    p_(BA.resumen(P[(P.location == EST)]).query("ambito == 'Nacional'").drop(columns='ambito').sort_values('CRPS').round(3)
       .rename(columns={'n': f'n_{EST}'}).to_string(index=False))
    Rg.to_csv(BA.SAL / 'metricas_ventaja_grande.csv', index=False)

    P.to_csv(BA.SAL / 'predicciones_LOYO.csv', index=False)
    R.to_csv(BA.SAL / 'metricas_margen.csv', index=False)
    Bt.to_csv(BA.SAL / 'bootstrap_vs_G.csv', index=False)
    E.to_csv(BA.SAL / f'errores_encuestas_{EST}.csv', index=False)
    Cr.to_csv(BA.SAL / 'cronologico.csv', index=False)
    T.to_csv(BA.SAL / 'terceros.csv', index=False)
    (BA.SAL / 'consola.txt').write_text('\n'.join(LOG), encoding='utf-8')


if __name__ == '__main__':
    main()
