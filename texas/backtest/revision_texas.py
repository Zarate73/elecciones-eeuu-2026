"""Pruebas de Texas (25-oct), heredadas de la revisión de Maine: pruebas que piden las observaciones.

1. Validación ESTRICTAMENTE cronológica de la regla del sesgo estatal: todas las contiendas vs sin contiendas de una
   sola encuestadora (k ≥ 2) vs sin sesgo (antes solo había cronológico de «todas» vs «sin sesgo»).
2. Régimen de ventana ampliada. Producción amplía la ventana a los 21 días previos a la encuesta más reciente cuando hay
   menos de 2 encuestadoras en los últimos 21 días (en Maine el 24-oct: 65 % del peso tenía más de 21 días; en Texas hoy hay 10 firmas y no se amplía).
   FiveThirtyEight solo publica encuestas de los últimos 21 días, así que el régimen no se puede reproducir a escala
   real. Se emula a escala 9/21: ventana nominal de 3 a 9 días antes de la elección; si hay < 2 encuestadoras, se
   amplía a las encuestas de los 9 días previos a la más reciente (≤ 18 días). En las contiendas ampliadas se comparan:
     A0 solo la ventana nominal (sin ampliar)
     A1 producción: ampliada, k = número de encuestadoras, deriva por la antigüedad de la MÁS RECIENTE
     A2 ampliada con k efectivo POR FIRMA = 1/Σ_f W_f², W_f = suma de los pesos de las encuestas de la firma f
        (revisión: la versión por encuesta, 1/Σw², contaba como independientes las encuestas repetidas de una firma
        y podía superar a k)
     A3 ampliada con deriva por la antigüedad PONDERADA de todas las encuestas
     A4 A2 + A3
   τ, s y ν se ajustan fuera del año evaluado (LOYO) con los errores de cada variante.
Uso: python revision_maine.py → salida/revision_*.csv y salida/revision_resumen.txt
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as st_t

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
import backtest_texas as BM            # noqa: E402,F401  (fija H y ESTADO)
import base_georgia as bt              # noqa: E402
import motor_backtest as BA            # noqa: E402
import revision_observaciones as RO    # noqa: E402

EST = 'TX'
SAL = BASE / 'salida'
LOG: list[str] = []
ORIG = BA.sesgo_pasado


def p_(*x):
    s = ' '.join(str(v) for v in x)
    print(s)
    LOG.append(s)


def sesgo_k2(tr, y, contraer=True):
    return ORIG(tr[tr.k >= 2], y, contraer)


# ------------------------------------------------------------------------------------- 1. cronológico
def cronologico(d):
    bc = RO.base_cronologica(d)
    C = [RO.evaluar_cronologico(bc, True).assign(modelo='G todas'),
         RO.evaluar_cronologico(bc, False).assign(modelo='sin sesgo')]
    BA.sesgo_pasado = sesgo_k2
    C.append(RO.evaluar_cronologico(bc, True).assign(modelo='G k≥2'))
    BA.sesgo_pasado = ORIG
    C = pd.concat(C, ignore_index=True)
    filas = []
    for amb, m in (('Nacional', C.index == C.index), ('Nacional_Gob', C.tipo == 'Gov-G'), (EST, C.location == EST),
                   (f'{EST}_Gob', (C.location == EST) & (C.tipo == 'Gov-G'))):
        for mod, g in C[m].groupby('modelo'):
            fila = {'ambito': amb, 'modelo': mod, 'n': len(g), 'CRPS': g.crps.mean(),
                    'MAE': (g.mu - g.actual).abs().mean(), 'Cob80': g.c80.mean()}
            if mod != 'G todas' and C[m].year.nunique() > 2:
                fila['P(mejor que G todas)'] = BA.bootstrap_por_anio(C, mod, 'G todas', pd.Series(np.asarray(m), index=C.index))
            filas.append(fila)
    return pd.DataFrame(filas), C


# ------------------------------------------------------------------------------------- 2. ventana ampliada
HN, WN = 3, 9                 # horizonte y ventana nominal emulados (escala 9/21)


def base_ventana(d, casa):
    filas = []
    for race, p in d.groupby('race'):
        y = int(p.year.iloc[0])
        q = p[p.days >= HN]
        if q.empty:
            continue
        nom = q[q.days <= WN]
        k_nom = nom.pollster_key.nunique()
        d_rec = int(q.days.min())
        amp = q[q.days <= d_rec + WN] if k_nom < 2 else nom
        ampliada = k_nom < 2 and amp.pollster_key.nunique() > max(k_nom, 0)
        for var, sel in (('nominal', nom), ('ampliada', amp)):
            if sel.empty:
                continue
            a = BA.agregar(sel, casa[y][0], 'v11')
            dt = (sel.days - sel.days.min()).to_numpy(float)
            w = np.exp(-np.log(2) * dt / 14.0) * np.sqrt(sel.n.to_numpy(float))
            w = w / sel.pollster_key.map(sel.pollster_key.value_counts()).to_numpy(float)
            w = w / w.sum()
            W_f = pd.Series(w, index=sel.index).groupby(sel.pollster_key).sum()       # peso total de cada firma
            a = {**a, 'neff_encuestas': a['neff'], 'neff': 1.0 / float(np.sum(W_f.to_numpy() ** 2))}   # 1 ≤ k_ef ≤ k
            filas.append({'race': race, 'year': y, 'location': p.location.iloc[0], 'tipo': p.type_simple.iloc[0],
                          'var': var, 'regimen_ampliado': ampliada, **a,
                          'edad_reciente': float(sel.days.min() - HN), 'edad_ponderada': float(w @ sel.days.to_numpy(float) - HN),
                          'actual': float(p.margin_actual.iloc[0])})
    return pd.DataFrame(filas)


def evaluar_variante(b, k_col, deriva_col, nombre):
    b = b.copy()
    b['k_mod'] = b[k_col]
    preds = []
    for y in sorted(b.year.unique()):
        te, tr = b[b.year == y].copy(), b[b.year != y].copy()
        for t in (tr, te):
            t['mu0'] = t.D - t.R
        bias = sesgo_k2(tr.assign(k=tr.k), y)
        te['mu'] = te.mu0 - te.location.map(bias).fillna(0.0)
        e = (tr.mu0 - tr.actual).to_numpy()
        # σ² = τ² + s²/k + 0.25²·deriva  (deriva en días; τ, s ajustados sin la deriva, como producción)
        tau, s = bt.ajustar_sigma(e, np.maximum(tr.k_mod.to_numpy(float), 1))
        nu = BA.nu_entrenado(e, np.maximum(tr.k_mod.to_numpy(float), 1), tau, s)
        der = te[deriva_col].to_numpy(float) if deriva_col else 0.0
        te['sd'] = np.sqrt(tau ** 2 + s ** 2 / np.maximum(te.k_mod, 1) + 0.25 ** 2 * der)
        te['nu'] = nu
        preds.append(te)
    P = pd.concat(preds, ignore_index=True)
    P['crps'] = BA.crps_t(P.actual, P.mu, P.sd, P.nu)
    sc = P.sd * np.sqrt((P.nu - 2) / P.nu)
    P['c80'] = np.abs(P.mu - P.actual) <= st_t.ppf(.9, P.nu) * sc
    P['c95'] = np.abs(P.mu - P.actual) <= st_t.ppf(.975, P.nu) * sc
    P['modelo'] = nombre
    return P


def ventana(d):
    years = sorted(d.year.unique())
    casa = {y: bt.efectos_casa(d[d.year != y]) for y in years}
    B = base_ventana(d, casa)
    amp_races = set(B[B.regimen_ampliado & (B['var'] == 'ampliada')].race)
    nom_races = set(B[B['var'] == 'nominal'].race)
    # base de producción: ampliada donde corresponde, nominal en el resto
    prod = pd.concat([B[(B['var'] == 'ampliada') & B.race.isin(amp_races)], B[(B['var'] == 'nominal') & ~B.race.isin(amp_races)]])
    nomb = B[(B['var'] == 'nominal')]
    P = pd.concat([
        evaluar_variante(nomb, 'k', 'edad_reciente', 'A0 solo ventana nominal'),
        evaluar_variante(prod, 'k', 'edad_reciente', 'A1 producción: k = firmas, deriva de la más reciente'),
        evaluar_variante(prod, 'neff', 'edad_reciente', 'A2 k efectivo por firma 1/Σ W_f²'),
        evaluar_variante(prod, 'k', 'edad_ponderada', 'A3 deriva por antigüedad ponderada'),
        evaluar_variante(prod, 'neff', 'edad_ponderada', 'A4 k efectivo + deriva ponderada'),
    ], ignore_index=True)
    sel_amp = P.race.isin(amp_races & nom_races)                  # mismas contiendas en todas las variantes
    filas = []
    for amb, m in (('Contiendas con ventana ampliada (y con encuesta nominal)', sel_amp),
                   ('Contiendas sin ampliar', ~P.race.isin(amp_races)), ('Todas', P.race.isin(nom_races))):
        for mod, g in P[m].groupby('modelo'):
            fila = {'ambito': amb, 'modelo': mod, 'n': len(g), 'CRPS': g.crps.mean(), 'MAE': (g.mu - g.actual).abs().mean(),
                    'Cob80': g.c80.mean(), 'Cob95': g.c95.mean(), 'sd_media': g.sd.mean(), 'k_medio': g.k_mod.mean()}
            if not mod.startswith('A1') and P[m].year.nunique() > 2:
                fila['P(mejor que A1)'] = BA.bootstrap_por_anio(P, mod, 'A1 producción: k = firmas, deriva de la más reciente',
                                                                pd.Series(np.asarray(m), index=P.index))
            filas.append(fila)
    T = pd.DataFrame(filas)
    a = B[B.race.isin(amp_races) & (B['var'] == 'ampliada')]
    info = (f'{len(amp_races)} contiendas ampliadas de {B.race.nunique()}; en ellas k medio {a.k.mean():.2f} '
            f'(k efectivo por firma {a.neff.mean():.2f}; por encuesta {a.neff_encuestas.mean():.2f}), antigüedad de la más reciente {a.edad_reciente.mean():.1f} d y '
            f'ponderada {a.edad_ponderada.mean():.1f} d sobre el horizonte')
    return T, info


def main():
    pd.set_option('display.width', 230)
    d = RO.cargar()
    d['partisan'] = d.partisan.fillna('').astype(str).str[:1].replace({'n': ''})
    T1, _ = cronologico(d)
    p_('[1] Validación estrictamente cronológica (2004–2024) de la regla del sesgo estatal')
    p_(T1.round(3).to_string(index=False))
    T2, info = ventana(d)
    p_(f'\n[2] Régimen de ventana ampliada (emulación a escala 9/21: nominal 3–9 días; ampliada ≤ 18 días). {info}')
    p_(T2.round(3).to_string(index=False))
    T1.to_csv(SAL / 'revision_cronologico_sesgo.csv', index=False)
    T2.to_csv(SAL / 'revision_ventana_ampliada.csv', index=False)
    (SAL / 'revision_resumen.txt').write_text('\n'.join(LOG), encoding='utf-8')


if __name__ == '__main__':
    main()
