"""Backtest para la general de Ohio (gobernador 2026, corte 26-oct → 8 días a la elección).

Base: Nueva York v1.1.0 / Illinois / Texas / Maine / Pennsylvania / Nevada / Florida (Georgia V11 + sesgo estatal
contraído + terceros con «no reportado» ≠ 0 + mercados) y la regla de Arizona (sin sesgo). Piezas específicas de Ohio:
  - sesgo estatal persistente pro-D (todas las contiendas desde 2014 sobreestimaron al demócrata);
  - tercero en la boleta (Don Kissick, Libertario): regla de terceros T4;
  - muchas encuestas de patrocinio partidista en ambos lados (co/efficient, Big Data, RedBox, Tulchin…).
Marco: leave-one-year-out con la ventana de producción (8 ≤ días ≤ 21), 1998–2024, más validación cronológica.
Uso: python backtest_ohio.py   → salida/*.csv y salida/consola.txt
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

EST = 'OH'
BA.H = 8
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

    # terceros (T0/T2/T4)
    Pg = P[P.modelo == REF]
    orep = RO.otros_reportados(d, casa)
    T, _ = RO.comparar_terceros(bases['v11'], Pg, orep)
    p_('\n== Terceros')
    p_(T.round(3).to_string(index=False))

    # ---- Independiente fuerte: ¿se desinfla?, ¿hacia quién?, ¿calibra T4? (contiendas con terceros ≥ 5 % reportados)
    _, Q = RO.comparar_terceros(bases['v11'], Pg, orep)
    Q4 = Q[Q.regla.str.startswith('T4')].copy()
    Q4['fuerte'] = Q4.O_rep >= 5
    Q4['err_margen'] = Q4.actual - Q4.mu                    # + = el demócrata rindió más que el pronóstico
    Q4['desinfle'] = Q4.O_real - Q4.O_rep                   # − = el tercero sacó menos de lo que daban las encuestas
    F = Q4[Q4.fuerte]
    p_(f'\n== Independiente fuerte: contiendas con terceros ≥ 5 % reportados en la ventana: {len(F)} '
       f'(de {Q4.O_rep.notna().sum()} con terceros reportados)')
    p_(f'   Desinfle medio (real − encuestas): {F.desinfle.mean():+.2f} pp (mediana {F.desinfle.median():+.2f}); '
       f'regla T4: sesgo de terceros {(F.Tp - F.O_real).mean():+.2f} pp, MAE {(F.Tp - F.O_real).abs().mean():.2f}')
    # ¿hacia dónde va el desinfle? error del margen contra el desinfle (pendiente > 0: si el tercero cae, gana el D)
    if len(F) > 5:
        A = np.c_[np.ones(len(F)), F.desinfle]
        co = np.linalg.lstsq(A, F.err_margen, rcond=None)[0]
        res = F.err_margen - A @ co
        se = float(np.sqrt(res.var(ddof=2) / ((F.desinfle - F.desinfle.mean()) ** 2).sum()))
        p_(f'   Error del margen vs desinfle: pendiente {co[1]:+.3f} (ee {se:.3f}); error medio del margen {F.err_margen.mean():+.2f} '
           f'(débil o nula ⇒ el voto que pierde el tercero se reparte parejo: indecisos/terceros 50/50)')
        boot = np.random.default_rng(1).choice(F.year.unique(), (2000, F.year.nunique()))
        pend = []
        for yy in boot:
            g = pd.concat([F[F.year == y] for y in yy])
            if g.desinfle.std() > 0:
                pend.append(np.polyfit(g.desinfle, g.err_margen, 1)[0])
        p_(f'   IC90 por bootstrap de años de la pendiente: [{np.percentile(pend, 5):+.3f}, {np.percentile(pend, 95):+.3f}]')
    # T5: regla por tramos (calibración separada para terceros fuertes), LOYO
    filas_t5 = []
    for y in sorted(Q4.year.unique()):
        tr, te = Q4[(Q4.year != y) & Q4.O_rep.notna()], Q4[Q4.year == y].copy()
        a_f, c_f = np.linalg.lstsq(np.c_[np.ones(tr.fuerte.sum()), tr[tr.fuerte].O_rep], tr[tr.fuerte].O_real, rcond=None)[0]
        a_d, c_d = np.linalg.lstsq(np.c_[np.ones((~tr.fuerte).sum()), tr[~tr.fuerte].O_rep], tr[~tr.fuerte].O_real, rcond=None)[0]
        t5 = np.where(te.O_rep.isna(), te.Tp, np.where(te.fuerte, a_f + c_f * te.O_rep.fillna(0), a_d + c_d * te.O_rep.fillna(0)))
        te['Tp5'] = np.clip(t5, 0, None)
        te['c_fuerte'] = c_f
        filas_t5.append(te)
    T5 = pd.concat(filas_t5)
    for amb, m in (('Nacional, terceros ≥ 5 %', T5.fuerte), (f'{EST}', T5.location == EST),
                   (f'{EST}, terceros ≥ 5 %', (T5.location == EST) & T5.fuerte)):
        g = T5[m]
        if len(g):
            p_(f'   {amb} (n = {len(g)}): MAE terceros T4 {(g.Tp - g.O_real).abs().mean():.2f} · T5 por tramos '
               f'{(g.Tp5 - g.O_real).abs().mean():.2f} · sesgo T4 {(g.Tp - g.O_real).mean():+.2f} · T5 {(g.Tp5 - g.O_real).mean():+.2f}')
    p_(f'   Pendiente media de T5 para terceros fuertes: {T5.c_fuerte.mean():.3f} (T4 global: {Q4.c4.mean():.3f})')
    cols = ['race', 'O_rep', 'O_real', 'desinfle', 'Tp', 'mu', 'actual', 'err_margen']
    p_(f'   Contiendas de {EST} con terceros reportados:')
    p_(Q4[(Q4.location == EST) & Q4.O_rep.notna()][cols].round(2).to_string(index=False))
    p_('   Las 12 contiendas con más terceros en las encuestas (nacional):')
    p_(F.sort_values('O_rep', ascending=False).head(12)[cols].round(2).to_string(index=False))
    F[cols + ['year', 'location']].to_csv(BA.SAL / 'terceros_fuertes.csv', index=False)

    # sesgo estatal del estado: con y sin contiendas de una sola encuestadora (k = 1)
    Gm = P[(P.modelo == REF) & (P.location == EST)]
    Hm = P[(P.modelo == 'H8 V11 sin sesgo estatal (Arizona)') & (P.location == EST)]
    for amb, mk in ((f'{EST}, todas', Gm.k >= 1), (f'{EST}, k ≥ 2', Gm.k >= 2), (f'{EST}, k = 1', Gm.k == 1)):
        g, h = Gm[mk.values], Hm[mk.values]
        p_(f'   Sesgo estatal {amb} (n = {len(g)}): CRPS con sesgo {g.crps.mean():.3f} · sin sesgo {h.crps.mean():.3f}')

    P.to_csv(BA.SAL / 'predicciones_LOYO.csv', index=False)
    R.to_csv(BA.SAL / 'metricas_margen.csv', index=False)
    Bt.to_csv(BA.SAL / 'bootstrap_vs_G.csv', index=False)
    E.to_csv(BA.SAL / f'errores_encuestas_{EST}.csv', index=False)
    Cr.to_csv(BA.SAL / 'cronologico.csv', index=False)
    T.to_csv(BA.SAL / 'terceros.csv', index=False)
    (BA.SAL / 'consola.txt').write_text('\n'.join(LOG), encoding='utf-8')


if __name__ == '__main__':
    main()
