"""Utilidades de la revisión externa de Florida (22-oct), reutilizadas en Nevada: ventana de producción, validación
cronológica y terceros con «no reportado» ≠ 0.

1. Ventana: ¿el backtest (q = days >= H) reproduce la ventana de producción (21 días + regla de ampliación)?
   Se recalcula cada contienda histórica con las funciones de producción (fl_pronostico.modelo.seleccionar_ventana y
   fl_pronostico.historico.promedio) y se compara con el promedio del backtest.
2. Validación estrictamente cronológica: efectos de casa, τ, s, ν y sesgo estatal estimados SOLO con años anteriores
   al evaluado (el LOYO usa también años posteriores para casa y σ). G (con sesgo) frente a H8 (sin sesgo).
3. Terceros: «no reportado» ≠ 0 %. Variante T4: promedio de terceros solo con encuestas que lo reportan; si ninguna
   lo reporta, media histórica de contiendas sin reporte. Frente a T2 (actual: faltante = 0, real = a + c·O).
4. Conteo de signos de los errores de Florida.

Uso: python revision_observaciones.py   (escribe salida/revision_*.csv y salida/revision_resumen.txt)
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
for _c in ('produccion', 'MODELO_NUEVA_YORK_GENERAL'):                       # repositorio o carpeta local
    sys.path.insert(0, str(BASE.parent / _c))
import base_florida as BF          # noqa: E402
import base_georgia as bt              # noqa: E402
import motor_backtest as BA            # noqa: E402
from ny_pronostico import historico as PH, modelo as PM   # noqa: E402

H = 12
VENTANA = 21
ESTADO = 'FL'          # backtest_new_york.py lo cambia a 'NY'
SAL = BASE / 'salida'
LOG: list[str] = []


def p_(*x):
    s = ' '.join(str(v) for v in x)
    print(s)
    LOG.append(s)


# ------------------------------------------------------------------------------------- datos con «reportado»
def cargar() -> pd.DataFrame:
    """Igual que el backtest, pero conserva si la encuesta reporta terceros. En 538 «no reportado» es NaN; en las
    capturas de Wikipedia 2024 (AZ y resto) el analizador escribía 0 para «—», así que ahí 0 se trata como faltante."""
    d = BF.cargar()
    raw = pd.read_csv(BASE / 'data' / 'fte_raw_polls_2023.csv', low_memory=False,
                      usecols=['race', 'pollster', 'polldate', 'samplesize', 'cand1_pct', 'cand2_pct', 'cand3_pct'])
    raw['polldate'] = pd.to_datetime(raw.polldate)
    raw['rep'] = raw.cand3_pct.notna()
    raw = raw.drop_duplicates(['race', 'pollster', 'polldate', 'cand1_pct', 'cand2_pct'])
    d = d.merge(raw[['race', 'pollster', 'polldate', 'cand1_pct', 'cand2_pct', 'rep']],
                on=['race', 'pollster', 'polldate', 'cand1_pct', 'cand2_pct'], how='left')
    d['rep'] = d.rep.fillna(d.cand3_pct > 0).astype(bool)         # 2024 (Wikipedia): 0 = no reportado
    return d


# ------------------------------------------------------------------------------------- 1. ventana
def ventana_produccion(p: pd.DataFrame, house: dict) -> dict:
    """Promedio de una contienda histórica con el código de producción, como si el corte fuera H días antes."""
    elec = p.electiondate.iloc[0]
    cfg = SimpleNamespace(dia_eleccion=elec.date(),
                          modelo=SimpleNamespace(ventana_dias_eleccion=VENTANA, min_encuestadoras=2))
    q = p[p.days >= H].assign(fin=lambda x: x.polldate, otros=lambda x: x.cand3_pct)   # ≤ corte
    if q.empty:
        return {}
    w_q, nota = PM.seleccionar_ventana(q, cfg)
    mu, o, k, _ = PH.promedio(w_q, house, 14.0)
    return {'mu_prod': mu, 'k_prod': k, 'n_prod': len(w_q), 'ampliada': nota['ampliada'],
            'n_fuera_21': int((q.days > VENTANA).sum())}


def revisar_ventana(d: pd.DataFrame, casa: dict) -> pd.DataFrame:
    b = BA.construir(d, casa, 'v11')
    filas = []
    for race, p in d.groupby('race'):
        r = ventana_produccion(p, casa[int(p.year.iloc[0])][0])
        if r:
            filas.append({'race': race, **r})
    x = b.merge(pd.DataFrame(filas), on='race')
    x['mu_bt'] = x.D - x.R
    x['dif'] = x.mu_prod - x.mu_bt
    return x


# ------------------------------------------------------------------------------------- 2. cronológico
def base_cronologica(d: pd.DataFrame) -> pd.DataFrame:
    """Cada contienda del año y usa efectos de casa estimados solo con años < y."""
    years = sorted(d.year.unique())
    casa = {y: bt.efectos_casa(d[d.year < y]) if (d.year < y).any() else ({}, {}) for y in years}
    return BA.construir(d, casa, 'v11')


def evaluar_cronologico(b: pd.DataFrame, sesgo: bool, desde: int = 2004) -> pd.DataFrame:
    preds = []
    for y in sorted(b.year.unique()):
        if y < desde:
            continue
        te, tr = b[b.year == y].copy(), b[b.year < y].copy()
        for t in (tr, te):
            t['mu0'] = t.D - t.R
        bias = BA.sesgo_pasado(tr, y) if sesgo else {}
        te['mu'] = te.mu0 - te.location.map(bias).fillna(0.0)
        e = (tr.mu0 - tr.actual).to_numpy()
        tau, s = bt.ajustar_sigma(e, tr.k.to_numpy())
        te['sd'] = np.sqrt(tau ** 2 + s ** 2 / np.maximum(te.k, 1))
        te['nu'] = BA.nu_entrenado(e, tr.k.to_numpy(), tau, s)
        preds.append(te)
    P = pd.concat(preds, ignore_index=True)
    P['crps'] = BA.crps_t(P.actual, P.mu, P.sd, P.nu)
    sc = P.sd * np.sqrt((P.nu - 2) / P.nu)
    from scipy.stats import t as st
    P['c80'] = np.abs(P.mu - P.actual) <= st.ppf(.9, P.nu) * sc
    P['pD'] = st.cdf(P.mu / sc, P.nu)
    P['sd_eff'] = P.sd
    P['c95'] = np.abs(P.mu - P.actual) <= st.ppf(.975, P.nu) * sc
    return P


# ------------------------------------------------------------------------------------- 3. terceros
def otros_reportados(d: pd.DataFrame, casa: dict) -> pd.DataFrame:
    """Por contienda (H = 12, pesos V11): % de terceros promediado SOLO con encuestas que lo reportan, y la fracción
    del peso que lo reporta."""
    filas = []
    for race, p in d.groupby('race'):
        q = p[p.days >= H]
        if q.empty:
            continue
        dt = (q.days - q.days.min()).to_numpy(float)
        w = np.exp(-np.log(2) * dt / 14.0) * np.sqrt(q.n.to_numpy(float))
        w = w / q.pollster_key.map(q.pollster_key.value_counts()).to_numpy(float)
        w = w / w.sum()
        rep = q.rep.to_numpy(bool)
        o_rep = float(np.average(q.cand3_pct.to_numpy(float)[rep], weights=w[rep])) if rep.any() else np.nan
        filas.append({'race': race, 'O_rep': o_rep, 'frac_rep': float(w[rep].sum())})
    return pd.DataFrame(filas)


def comparar_terceros(b: pd.DataFrame, P: pd.DataFrame, orep: pd.DataFrame) -> pd.DataFrame:
    x = P.merge(b[['race', 'O']].rename(columns={'O': 'O_enc'}), on='race').merge(orep, on='race', how='left')
    out = []
    for y in sorted(x.year.unique()):
        te, tr = x[x.year == y].copy(), x[x.year != y]
        c2 = np.linalg.lstsq(np.c_[np.ones(len(tr)), tr.O_enc], tr.O_real, rcond=None)[0]
        con = tr[tr.O_rep.notna()]
        c4 = np.linalg.lstsq(np.c_[np.ones(len(con)), con.O_rep], con.O_real, rcond=None)[0]
        sin = float(tr[tr.O_rep.isna()].O_real.mean())
        t2 = np.clip(c2[0] + c2[1] * te.O_enc, 0, None)
        t4 = np.where(te.O_rep.notna(), np.clip(c4[0] + c4[1] * te.O_rep.fillna(0), 0, None), sin)
        for nom, T in (('T0 terceros = 0', np.zeros(len(te))), ('T2 actual (faltante = 0)', t2.to_numpy()),
                       ('T4 faltante ≠ 0 (solo encuestas que reportan)', t4)):
            out.append(te.assign(regla=nom, Tp=T, Dp=(100 - T + te.mu) / 2, Rp=(100 - T - te.mu) / 2,
                                 a4=c4[0], c4=c4[1], sin_rep=sin))
    Q = pd.concat(out)
    filas = []
    for amb, m in (('Nacional', Q.index == Q.index), (ESTADO, Q.location == ESTADO),
                   ('Nacional, sin reporte en la ventana', Q.O_rep.isna())):
        for r, g in Q[m].groupby('regla'):
            eD, eR = (g.Dp - g.D_real).abs(), (g.Rp - g.R_real).abs()
            filas.append({'ambito': amb, 'regla': r, 'n': len(g), 'MAE_%D': eD.mean(), 'MAE_%R': eR.mean(),
                          'MAE_conjunto': (eD.mean() + eR.mean()) / 2, 'MAE_terceros': (g.Tp - g.O_real).abs().mean(),
                          'sesgo_terceros': (g.Tp - g.O_real).mean()})
    return pd.DataFrame(filas), Q


def main():
    pd.set_option('display.width', 220)
    d = cargar()
    years = sorted(d.year.unique())
    casa = {y: bt.efectos_casa(d[d.year != y]) for y in years}

    # 4. signos
    e = pd.read_csv(SAL / 'errores_encuestas_FL.csv')
    p_(f'[4] Errores de FL: {int((e.error_pp > 0).sum())} pro-D de {len(e)} (no 19 de 23).')

    # 1. ventana
    x = revisar_ventana(d, casa)
    x.to_csv(SAL / 'revision_ventana.csv', index=False)
    p_(f'\n[1] Ventana. Encuestas del histórico con > 21 días a la elección: {int((d.days > VENTANA).sum())} '
       f'(de {len(d)}; FiveThirtyEight solo publica los últimos 21 días).')
    p_(f'    Contiendas: {len(x)} · |dif| máx {x.dif.abs().max():.4f} pp · contiendas con dif > 0.01: '
       f'{int((x.dif.abs() > 0.01).sum())} · k distinto: {int((x.k != x.k_prod).sum())} · ampliadas: {int(x.ampliada.sum())}')
    p_(x[x.dif.abs() > 0.01][['race', 'mu_bt', 'mu_prod', 'dif', 'k', 'k_prod', 'n_fuera_21']].round(3).to_string(index=False))

    # 2. cronológico
    bc = base_cronologica(d)
    G = evaluar_cronologico(bc, True).assign(modelo='G con sesgo')
    S = evaluar_cronologico(bc, False).assign(modelo='H8 sin sesgo')
    C = pd.concat([G, S], ignore_index=True)
    C.to_csv(SAL / 'revision_cronologico_predicciones.csv', index=False)
    filas = []
    for amb, m in (('Nacional', C.index == C.index), ('Nacional_Gob', C.tipo == 'Gov-G'), ('FL', C.location == 'FL'),
                   ('FL_Gob', (C.location == 'FL') & (C.tipo == 'Gov-G')), ('FL_2016+', (C.location == 'FL') & (C.year >= 2016))):
        for mod, g in C[m].groupby('modelo'):
            filas.append({'ambito': amb, 'modelo': mod, 'n': len(g), 'CRPS': g.crps.mean(), 'MAE': (g.mu - g.actual).abs().mean(),
                          'sesgo': (g.mu - g.actual).mean(), 'Cob80': g.c80.mean()})
        sel = pd.Series(np.asarray(m), index=C.index)
        prob = BA.bootstrap_por_anio(C, 'H8 sin sesgo', 'G con sesgo', sel)
        filas.append({'ambito': amb, 'modelo': 'P(sin sesgo mejor), bootstrap por año', 'CRPS': prob})
    R = pd.DataFrame(filas)
    R.to_csv(SAL / 'revision_cronologico.csv', index=False)
    p_('\n[2] Validación estrictamente cronológica (evaluación 2004–2024; todo se estima con años anteriores):')
    p_(R.round(3).to_string(index=False))

    # 3. terceros (sobre las predicciones LOYO de G)
    b = BA.construir(d, casa, 'v11')
    P = BA.evaluar(b, 'G', 'u50', True, 'sig')
    orep = otros_reportados(d, casa)
    T, Q = comparar_terceros(b, P, orep)
    T.to_csv(SAL / 'revision_terceros.csv', index=False)
    fl = orep.merge(b[['race', 'location']], on='race')
    p_(f'\n[3] Terceros. Contiendas sin ninguna encuesta que reporte terceros: {int(orep.O_rep.isna().sum())} de {len(orep)} '
       f'(FL: {int(fl[fl.location == "FL"].O_rep.isna().sum())} de {int((fl.location == "FL").sum())}).')
    p_(T.round(3).to_string(index=False))
    q4 = Q[Q.regla.str.startswith('T4')]
    p_(f'    T4 (todas las contiendas): real = {q4.a4.mean():.2f} + {q4.c4.mean():.2f}·reportado; sin reporte → {q4.sin_rep.mean():.2f}')
    (SAL / 'revision_resumen.txt').write_text('\n'.join(LOG), encoding='utf-8')
    return x, R, T


if __name__ == '__main__':
    main()
