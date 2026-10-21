"""Pruebas complementarias al backtest:
 A) Asignación de indecisos: ¿proporcional (normalizar) o sesgada hacia R como en V9?
 B) Bootstrap por bloques de año de diferencias de CRPS (¿la mejora es real?).
 C) Sesgo estatal con decaimiento temporal (ciclos recientes pesan más).
Ejecutar después de backtest_georgia.py (usa salida_backtest/predicciones_h15.csv).
"""
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm
import backtest_georgia as bt

OUT = bt.OUT
rng = np.random.default_rng(20261019)


def indecisos():
    d = bt.cargar_encuestas()
    d = d[d.cand3_pct.notna() | (d.year == 2024)].copy()
    d['c3'] = d.cand3_pct.fillna(0)
    d['U'] = (100 - d.cand1_pct - d.cand2_pct - d.c3).clip(lower=0)
    d['major_act'] = d.cand1_actual + d.cand2_actual
    # Oráculo de terceros (en GA-2026 sabemos que casi no hay terceros en boleta)
    d['m_raw'] = d.margin_poll
    d['m_prop'] = d.margin_poll * d.major_act / (d.cand1_pct + d.cand2_pct)
    rows = []
    for s in [0.30, 0.40, 0.436, 0.50, 0.60]:
        # reparto de U con fracción s a R; el resto del voto no-mayor se resta proporcionalmente
        d[f'm_s{s}'] = d.margin_poll + d.U * (1 - 2 * s)
    grp = d.groupby('race').agg(actual=('margin_actual', 'first'), year=('year', 'first'), U=('U', 'mean'),
                                **{c: (c, 'mean') for c in d.columns if c.startswith('m_')})
    for c in [c for c in grp.columns if c.startswith('m_')]:
        e = grp[c] - grp.actual
        rows.append({'regla': c, 'n_contiendas': len(grp), 'sesgo': e.mean(), 'MAE': e.abs().mean(),
                     'RMSE': np.sqrt((e ** 2).mean())})
    # s óptimo por mínimos cuadrados con LOYO
    sh = []
    for y in grp.year.unique():
        tr = grp[grp.year != y]
        # actual - poll = U*(1-2s)  -> (1-2s) = sum(U*r)/sum(U^2)
        k = np.sum(tr.U * (tr.actual - tr.m_raw)) / np.sum(tr.U ** 2)
        sh.append((1 - k) / 2)
    out = pd.DataFrame(rows)
    out.attrs['s_LOYO_media'] = float(np.mean(sh))
    out.attrs['s_LOYO_rango'] = (float(np.min(sh)), float(np.max(sh)))
    out.attrs['U_medio'] = float(grp.U.mean())
    return out


def bootstrap_crps(P, ambito_mask, a, b, B=4000):
    g = P[ambito_mask & P.modelo.isin([a, b])].copy()
    g['crps'] = bt.crps_normal(g.actual, g.mu, g.sd)
    w = g.pivot_table(index=['race', 'year'], columns='modelo', values='crps').dropna().reset_index()
    w['diff'] = w[a] - w[b]
    yrs = w.year.unique()
    by = {y: w.loc[w.year == y, 'diff'].to_numpy() for y in yrs}
    stats = []
    for _ in range(B):
        s = rng.choice(yrs, len(yrs), replace=True)
        stats.append(np.concatenate([by[y] for y in s]).mean())
    stats = np.array(stats)
    return {'A': a, 'B': b, 'n': len(w), 'dif_media(A-B)': w['diff'].mean(),
            'IC95_bajo': np.quantile(stats, .025), 'IC95_alto': np.quantile(stats, .975),
            'P(A mejor)': (stats < 0).mean()}


def sesgo_estado_decaimiento(horizonte=15, vidas=(4, 8, 12, 1e9)):
    """Variante C: media ponderada por antigüedad del error estatal, contraída (EB)."""
    d = bt.cargar_encuestas()
    years = sorted(d.year.unique())
    casa = {y: bt.efectos_casa(d[d.year != y]) for y in years}
    b = bt.construir_contiendas(d, horizonte, 'casa', casa)
    b['e'] = b.poll - b.actual
    res = []
    for hl in vidas:
        preds = []
        for y in years:
            te = b.year == y
            if not te.any():
                continue
            tr = b[~te]
            tau, s = bt.ajustar_sigma(tr.e.to_numpy(), tr.k.to_numpy())
            t = b[te].copy()
            # usa SOLO años previos para el sesgo (más estricto que LOYO: no mira al futuro)
            past = tr[tr.year < y].copy()
            if len(past) < 20:
                t['mu'] = t.poll
            else:
                past['w'] = 0.5 ** ((y - past.year) / hl)
                st = past.groupby('location').apply(
                    lambda g: pd.Series({'m': np.average(g.e, weights=g.w), 'neff': g.w.sum() ** 2 / (g.w ** 2).sum(),
                                         'v': g.e.var() if len(g) > 1 else np.nan}), include_groups=False)
                st = st[st.neff >= 1.5]
                noise = float(np.nanmean(st.v / st.neff))
                vs = max(float(st.m.var()) - noise, 0)
                def bias(l):
                    if l not in st.index or vs == 0 or np.isnan(st.loc[l, 'v']):
                        return 0.0
                    return float(vs / (vs + st.loc[l, 'v'] / st.loc[l, 'neff']) * st.loc[l, 'm'])
                t['mu'] = t.poll - np.array([bias(l) for l in t.location])
            t['sd'] = np.sqrt(tau ** 2 + s ** 2 / np.maximum(t.k, 1))
            preds.append(t)
        Pp = pd.concat(preds)
        for amb, m in [('Nacional', Pp.index == Pp.index), ('GA_generales', (Pp.location == 'GA') & ~Pp.runoff),
                       ('GA_2014+', (Pp.location == 'GA') & (Pp.year >= 2014))]:
            r = bt.metricas(Pp[m]); r.update({'vida_media_anios': hl, 'ambito': amb}); res.append(r)
    return pd.DataFrame(res)


if __name__ == '__main__':
    pd.set_option('display.width', 200)
    A = indecisos()
    A.to_csv(OUT / 'A_indecisos.csv', index=False)
    print('A) Indecisos (U medio %.1f pp). s óptimo LOYO hacia R: %.3f, rango %s' %
          (A.attrs['U_medio'], A.attrs['s_LOYO_media'], A.attrs['s_LOYO_rango']))
    print(A.round(3).to_string(index=False))
    P = pd.read_csv(OUT / 'predicciones_h15.csv')
    best = 'casa_part|sesgo_estado+sd_emp'
    comps = []
    for amb, m in [('Nacional', P.index == P.index), ('GA', P.location == 'GA')]:
        for other in ['pond|sd_empirica', 'pond|sd_V9(2pp)', 'casa_part|fundamentales+sd_emp', 'casa_part|sd_empirica']:
            r = bootstrap_crps(P, m, best, other); r['ambito'] = amb; comps.append(r)
    Bc = pd.DataFrame(comps); Bc.to_csv(OUT / 'B_bootstrap_crps.csv', index=False)
    print('\nB) Bootstrap por año (CRPS, negativo = gana el modelo A)')
    print(Bc.round(3).to_string(index=False))
    C = sesgo_estado_decaimiento()
    C.to_csv(OUT / 'C_sesgo_estado_decaimiento.csv', index=False)
    print('\nC) Sesgo estatal sólo con pasado y decaimiento temporal')
    print(C[['ambito', 'vida_media_anios', 'n', 'sesgo', 'MAE', 'RMSE', 'CRPS', 'Cob80', 'Cob95']].round(3).to_string(index=False))
