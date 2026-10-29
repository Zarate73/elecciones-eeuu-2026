"""Modelo general de D.C.: fundamentales históricos (M1) + reparto del voto no demócrata + conteo RCV.

1. % del demócrata en la primera ronda: logit(%D) = a + b·opositor_fuerte (+ las variables de config), ajustado con las
   13 generales 1974–2022; predictiva t de Student con la incertidumbre de los coeficientes (elegido por LOYO, docs/01).
2. Si hay encuestas de la general: se combinan por precisión en escala logit (hoy no hay).
3. Voto no demócrata = verde (lognormal) + escrito (lognormal) + opositor principal (el resto, con un mínimo).
4. RCV: conteo de la Iniciativa 83 en cada simulación (rcv.py).
5. Mercados (si existen): mezcla logit de la probabilidad con peso 0.30.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.special import expit, logit

from .rcv import contar_rcv_vector


def _col(h: pd.DataFrame, v: str) -> np.ndarray:
    return {'fuerte': lambda: h.fuerte.values, 'titular': lambda: h.titular.values,
            'primaria': lambda: h.primaria_pct.values, 'tendencia': lambda: (h.anio.values - 2000) / 10}[v]().astype(float)


def x_2026(cfg, variables, primaria_pct=None) -> np.ndarray:
    e = cfg.eleccion
    val = {'fuerte': float(bool(e.opositor_fuerte)), 'titular': float(bool(e.titular_compite)),
           'primaria': float(primaria_pct) if primaria_pct is not None else np.nan, 'tendencia': 2.6}
    return np.r_[1.0, [val[v] for v in variables]]


def ajustar(h: pd.DataFrame, variables) -> dict:
    A = np.column_stack([np.ones(len(h))] + [_col(h, v) for v in variables])
    b, *_ = np.linalg.lstsq(A, h.y.values, rcond=None)
    r = h.y.values - A @ b
    gl = max(len(h) - A.shape[1], 1)
    return {'b': b, 's2': float(r @ r / gl), 'gl': gl, 'XtXi': np.linalg.pinv(A.T @ A), 'variables': list(variables)}


def predictiva(fit: dict, x: np.ndarray) -> tuple[float, float, int]:
    mu = float(x @ fit['b'])
    sc = float(np.sqrt(fit['s2'] * (1 + x @ fit['XtXi'] @ x)))
    return mu, sc, fit['gl']


def crps_muestras(p: np.ndarray, obs: float, rng) -> float:
    return float(np.mean(np.abs(p - obs)) - 0.5 * np.mean(np.abs(p - rng.permutation(p))))


def loyo(h: pd.DataFrame, variables, n=4000, semilla=7) -> dict:
    """Validación dejando fuera una elección: CRPS y cobertura del IC80 del % demócrata (pp)."""
    rng = np.random.default_rng(semilla)
    cr, cub, err = [], [], []
    for i in range(len(h)):
        tr, te = h.drop(h.index[i]), h.iloc[i]
        f = ajustar(tr, variables)
        x = np.r_[1.0, [_col(h.iloc[[i]], v)[0] for v in variables]]
        mu, sc, gl = predictiva(f, x)
        p = 100 * expit(mu + sc * rng.standard_t(gl, n))
        cr.append(crps_muestras(p, te.pct_d, rng))
        lo, hi = np.percentile(p, [10, 90])
        cub.append(lo <= te.pct_d <= hi)
        err.append(np.median(p) - te.pct_d)
    return {'crps': float(np.mean(cr)), 'cobertura80': float(np.mean(cub)), 'mae': float(np.mean(np.abs(err))),
            'por_eleccion': [{'anio': int(a), 'crps': float(c), 'error_mediana_pp': float(e)}
                             for a, c, e in zip(h.anio, cr, err)]}


def reparto(pct_d: np.ndarray, m, rng) -> dict:
    """Divide el voto no demócrata entre el opositor principal, el verde y los votos por escrito."""
    n = len(pct_d)
    resto = 100 - pct_d
    g = np.exp(np.log(m.verde_mediana_pct) + m.verde_sd_log * rng.standard_normal(n))
    w = np.exp(np.log(m.escrito_mediana_pct) + m.escrito_sd_log * rng.standard_normal(n))
    tope = (1 - m.opositor_min_frac) * resto              # el opositor principal conserva al menos esa fracción
    esc = np.minimum(1.0, tope / np.maximum(g + w, 1e-9))
    g, w = g * esc, w * esc
    return {'D': pct_d, 'O': resto - g - w, 'V': g, 'W': w}


def simular(mu, sc, gl, cfg, rng, n, encuestas=None, transferencias=None) -> dict:
    m = cfg.modelo
    z = mu + sc * rng.standard_t(gl, n)
    peso_f = 1.0
    if encuestas is not None:
        p = np.clip(encuestas['pct_D'] / 100, 0.02, 0.98)
        zp, sp = logit(p), m.encuesta_sd_pp / (100 * p * (1 - p))
        peso_f = sp ** 2 / (sc ** 2 + sp ** 2)
        z = peso_f * z + (1 - peso_f) * (zp + sp * rng.standard_normal(n))
    r = reparto(100 * expit(z), m, rng)
    V = np.column_stack([r['D'], r['O'], r['V'], r['W']])
    c = contar_rcv_vector(V, cfg.candidatos, transferencias if transferencias is not None else m.transferencias)
    return {**r, 'ganador': c['ganador'], 'rondas': c['rondas'], 'cuota_final': c['cuota_final'], 'peso_fundamentales': peso_f}


def mezcla_mercados(p_modelo: float, mk: dict | None, w: float) -> tuple[float, float]:
    if not mk or not mk.get('n_usables'):
        return p_modelo, 0.0
    pm = float(np.clip(mk['promedio_D'], 1e-4, 1 - 1e-4))
    pmod = float(np.clip(p_modelo, 1e-5, 1 - 1e-5))
    return float(expit((1 - w) * logit(pmod) + w * logit(pm))), w


def _ic(x, a=80):
    q = (100 - a) / 2
    return [float(np.percentile(x, q)), float(np.percentile(x, 100 - q))]


def resumir(s: dict, cfg) -> dict:
    um = cfg.modelo.umbrales_pct
    d, o = s['D'], s['O']
    marg = d - o
    return {'pct_D': float(d.mean()), 'pct_D_IC80': _ic(d), 'pct_D_IC95': _ic(d, 95),
            'pct_opositor': float(o.mean()), 'pct_opositor_IC80': _ic(o),
            'pct_verde': float(s['V'].mean()), 'pct_verde_IC80': _ic(s['V']),
            'pct_escrito': float(s['W'].mean()), 'pct_escrito_IC80': _ic(s['W']),
            'pct_terceros': float((s['V'] + s['W']).mean()), 'pct_terceros_IC80': _ic(s['V'] + s['W']),
            'margen': float(marg.mean()), 'IC80': _ic(marg), 'IC95': _ic(marg, 95), 'sd': float(marg.std()),
            'P_D_modelo': float((s['ganador'] == 0).mean()), 'P_opositor': float((s['ganador'] == 1).mean()),
            'P_primera_ronda': float((d > 50).mean()),
            'P_umbral': {f'{u:g}': float((d >= u).mean()) for u in um},
            'rondas': {str(k): float((s['rondas'] == k).mean()) for k in (1, 2, 3, 4)}}


def pronosticar(hist: dict, eleccion: dict, enc_prom: dict | None, mk: dict, cfg) -> dict:
    m = cfg.modelo
    h = hist['tabla']
    rng = np.random.default_rng(int(m.semilla))
    variables = list(m.variables)
    prim = eleccion.get('primaria_pct')
    fit = ajustar(h, variables)
    mu, sc, gl = predictiva(fit, x_2026(cfg, variables, prim))
    n = int(m.n_simulaciones)
    s = simular(mu, sc, gl, cfg, rng, n, encuestas=enc_prom)
    f = resumir(s, cfg)
    s0 = simular(mu, sc, gl, cfg, np.random.default_rng(int(m.semilla) + 1), n // 4) if enc_prom else s
    f['P_D_fundamentales'] = float((s0['ganador'] == 0).mean())
    f['P_D'], f['peso_mercados_aplicado'] = mezcla_mercados(f['P_D_modelo'], mk, float(m.peso_mercados))
    val = loyo(h, variables)
    f.update({'base': 'fundamentales + encuestas' if enc_prom else 'fundamentales', 'peso_fundamentales': s['peso_fundamentales'],
              'mu_logit': mu, 'escala_logit': sc, 'gl': gl, 'coeficientes': dict(zip(['const'] + variables, map(float, fit['b']))),
              'sigma_logit': float(np.sqrt(fit['s2'])), 'n_elecciones': int(len(h)), 'crps_loyo': val['crps'],
              'cobertura80_loyo': val['cobertura80'], 'mae_loyo': val['mae'],
              'pct_D_fundamentales_centro': float(100 * expit(mu)), 'encuestas': None if not enc_prom else
              {k: v for k, v in enc_prom.items() if k != 'tabla'}})
    esc = escenarios(h, mu, sc, gl, cfg, prim, enc_prom)
    sim = pd.DataFrame({'D': s['D'][:20000], 'O': s['O'][:20000], 'V': s['V'][:20000], 'W': s['W'][:20000],
                        'ganador': s['ganador'][:20000], 'rondas': s['rondas'][:20000]})
    return {'final': f, 'escenarios': esc, 'loyo': val, 'sim': sim, 'ajuste': fit}


def escenarios(h, mu, sc, gl, cfg, prim, enc_prom) -> pd.DataFrame:
    m = cfg.modelo
    n = max(20000, int(m.n_simulaciones) // 5)
    debil = h[h.fuerte == 0]
    recientes = debil[debil.anio >= 2018]
    filas = []

    def fila(nombre, mu_, sc_, gl_, tr=None, nota=''):
        s = simular(mu_, sc_, gl_, cfg, np.random.default_rng(int(m.semilla) + len(filas) + 10), n, encuestas=enc_prom,
                    transferencias=tr)
        r = resumir(s, cfg)
        filas.append({'escenario': nombre, 'pct_D': r['pct_D'], 'pct_D_IC80_bajo': r['pct_D_IC80'][0],
                      'pct_D_IC80_alto': r['pct_D_IC80'][1], 'margen': r['margen'], 'P_D': r['P_D_modelo'],
                      'P_primera_ronda': r['P_primera_ronda'], 'nota': nota})
    fila('Base (M1: opositor débil, 13 elecciones)', mu, sc, gl, nota='pronóstico publicado (antes de mercados)')
    sc5 = float(np.sqrt(debil.y.var(ddof=1) * (1 + 1 / len(debil))))
    fila(f'Solo las {len(debil)} elecciones con opositor débil (σ propia)', float(debil.y.mean()), sc5, len(debil) - 1,
         nota='M5 del backtest')
    if len(recientes):
        c = float(recientes.pct_d.mean())
        fila(f'Nivel reciente: {"–".join(map(str, recientes.anio))} con opositor débil ({c:.1f} %)', float(logit(c / 100)), sc, gl,
             nota='Bowser 3.er y 2.º mandato; misma incertidumbre')
    mn = debil.loc[debil.pct_d.idxmin()]
    fila(f'Protesta moderada: centro en el mínimo con opositor débil ({int(mn.anio)}, {mn.pct_d:.1f} %)',
         float(logit(mn.pct_d / 100)), sc, gl, nota='sin respaldo de Bowser; voto antisocialista hacia Hamilton')
    f1 = ajustar(h, ['fuerte'])
    x = np.r_[1.0, 1.0]
    mu1, sc1, gl1 = predictiva(f1, x)
    fila('Si surgiera un opositor fuerte (concejal o alcalde, p. ej. por escrito)', mu1, sc1, gl1,
         nota='como 1986–2002, 2010 y 2014')
    if prim is not None:
        f3 = ajustar(h, ['fuerte', 'primaria'])
        mu3, sc3, gl3 = predictiva(f3, np.r_[1.0, float(bool(cfg.eleccion.opositor_fuerte)), float(prim)])
        fila(f'Con el % de la primaria ({prim:.1f} %) como variable (M3)', mu3, sc3, gl3, nota='peor en el backtest')
    e = cfg.eleccion
    tr = {'escrito': {e.candidato_d: 0.20, e.opositor: 0.60, 'agotada': 0.20},
          e.verde: {e.candidato_d: 0.30, e.opositor: 0.50, 'agotada': 0.20}}
    fila('Transferencias RCV desfavorables (verde y escrito → opositor 50–60 %)', mu, sc, gl, tr=tr,
         nota='solo cambia algo si Lewis George < 50 % en la 1.ª ronda')
    return pd.DataFrame(filas)
