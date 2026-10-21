"""Modelo V11: promedio corregido por casa − sesgo GA, sigma(k) empírica, colas t, mezcla con Kalshi."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.special import expit, logit
from scipy.stats import norm, t as student_t

from .historico import promedio


class Dist:
    """Normal o Student-t con desviación estándar sd (escala t ajustada para var = sd²)."""

    def __init__(self, sd: float, nu: float | None):
        self.sd, self.nu = float(sd), (float(nu) if nu else None)
        self.sc = self.sd * np.sqrt((self.nu - 2) / self.nu) if self.nu else self.sd

    def cdf(self, x):
        return student_t.cdf(x / self.sc, self.nu) if self.nu else norm.cdf(x / self.sd)

    def ppf(self, p):
        return self.sc * student_t.ppf(p, self.nu) if self.nu else self.sd * norm.ppf(p)


def preparar_encuestas(df: pd.DataFrame, cfg, house: dict) -> pd.DataFrame:
    p = df.copy()
    p['fin'] = pd.to_datetime(p.fin)
    p['days'] = (pd.Timestamp(cfg.dia_eleccion) - p.fin).dt.days
    p['margin_poll'] = p.D - p.R
    p['n'] = p.n.clip(100, 3000)
    p['efecto_casa'] = p.clave_538.map(house).fillna(0.0)
    p['margen_corregido'] = p.margin_poll - p.efecto_casa
    return p


def ventana(p: pd.DataFrame, cfg) -> tuple[pd.DataFrame, dict]:
    lim = pd.Timestamp(cfg.dia_eleccion) - pd.Timedelta(days=cfg.modelo.ventana_dias_eleccion)
    q = p[p.fin >= lim]
    nota = {'desde': str(lim.date()), 'ampliada': False}
    if q.clave_538.nunique() < cfg.modelo.min_encuestadoras and len(p):
        ultima = p.groupby('clave_538').fin.max().sort_values(ascending=False)  # más reciente de cada firma
        desde = ultima.head(cfg.modelo.min_encuestadoras).min()
        q = p[p.fin >= desde]
        nota = {'desde': str(desde.date()), 'ampliada': True}
    return q, nota


def sigma(par, k) -> float:
    return float(np.sqrt(par['tau'] ** 2 + par['s'] ** 2 / max(k, 1)))


def tres_categorias(q: pd.DataFrame, cfg) -> dict:
    g = q[q.tipo_pregunta == 'general']
    if g.empty:
        return {'n_encuestas': 0}
    dt = (g.days - g.days.min()).to_numpy(float)
    w = np.exp(-np.log(2) * dt / cfg.modelo.vida_media_dias) * np.sqrt(g.n.to_numpy(float))
    w = w / g.clave_538.map(g.clave_538.value_counts()).to_numpy(float); w = w / w.sum()
    D, R = float(w @ g.D), float(w @ g.R)
    return {'n_encuestas': int(len(g)), 'D_encuesta': D, 'R_encuesta': R, 'otros_indecisos': 100 - D - R}


def estimar_carrera(df: pd.DataFrame, cfg, par: dict) -> dict:
    p = preparar_encuestas(df, cfg, par['efectos_casa'])
    q, nota = ventana(p, cfg)
    m_enc, k = promedio(q, par['efectos_casa'], cfg.modelo.vida_media_dias)
    mu = m_enc - par['sesgo_estado']
    D = Dist(sigma(par, k), par['nu'] if cfg.modelo.colas_t else None)
    return {'encuestas': p, 'ventana': q, 'nota_ventana': nota, 'margen_corregido': m_enc, 'mu': mu, 'k': k,
            'dist': D, 'p_D': float(D.cdf(mu)), 'tres_categorias': tres_categorias(q, cfg)}


def mezclar_kalshi(p_enc: float, kal: dict, w: float) -> float:
    if w <= 0 or not kal.get('usable_en_mezcla'):
        return p_enc
    return float(expit((1 - w) * logit(p_enc) + w * logit(kal['p_d_normalizada'])))


def resumir_sim(M: np.ndarray, W: np.ndarray) -> dict:
    B, J = (100 - W + M) / 2, (100 - W - M) / 2
    q = lambda x, a: float(np.quantile(x, a))
    return {'margen': float(M.mean()), 'sd': float(M.std()), 'IC80': (q(M, .1), q(M, .9)), 'IC95': (q(M, .025), q(M, .975)),
            'pct_D': float(B.mean()), 'pct_R': float(J.mean()),
            'pct_D_IC80': (q(B, .1), q(B, .9)), 'pct_R_IC80': (q(J, .1), q(J, .9)),
            'P_D': float((B > J).mean()), 'P_R': float((J > B).mean()),
            'P_segunda_vuelta': float(((B <= 50) & (J <= 50)).mean())}


def simular(mu, D: Dist, cfg, semilla_extra=0, n=None):
    rng = np.random.default_rng(cfg.modelo.semilla + semilla_extra)
    n = n or cfg.modelo.n_simulaciones
    if D.nu:
        M = mu + D.sc * rng.standard_t(D.nu, n)
    else:
        M = rng.normal(mu, D.sd, n)
    W = rng.uniform(cfg.eleccion.writein_pp_min, cfg.eleccion.writein_pp_max, n)
    return M, W


def pronosticar(gob: dict, kal: dict, cfg, par: dict) -> dict:
    w = cfg.modelo.w_kalshi
    p_fin = mezclar_kalshi(gob['p_D'], kal, w)
    D = gob['dist']
    mu_fin = float(D.ppf(p_fin))
    M, W = simular(mu_fin, D, cfg)
    final = resumir_sim(M, W)
    final.update({'p_D_encuestas': gob['p_D'], 'p_D_final': p_fin, 'mu_encuestas': gob['mu'], 'mu_final': mu_fin,
                  'peso_kalshi_aplicado': w if kal.get('usable_en_mezcla') else 0.0})
    esc = {'Solo encuestas (sin Kalshi)': (gob['mu'], D),
           'Sin sesgo estatal GA': (gob['margen_corregido'], D),
           'Distribución normal': (float(Dist(D.sd, None).ppf(mezclar_kalshi(float(norm.cdf(gob['mu'] / D.sd)), kal, w))),
                                   Dist(D.sd, None))}
    if kal.get('p_d_normalizada') is not None:
        esc['Kalshi solo'] = (float(D.ppf(kal['p_d_normalizada'])), D)
    p = gob['encuestas']
    for dias in (30, 45):
        qq = p[p.fin >= pd.Timestamp(cfg.corte) - pd.Timedelta(days=dias)]
        mm, kk = promedio(qq, par['efectos_casa'], cfg.modelo.vida_media_dias)
        if not np.isnan(mm):
            esc[f'Ventana {dias} días'] = (mm - par['sesgo_estado'], Dist(sigma(par, kk), D.nu))
    escenarios = [{'escenario': 'FINAL', **final}]
    for nombre, (m_, d_) in esc.items():
        escenarios.append({'escenario': nombre, **resumir_sim(*simular(m_, d_, cfg, n=min(cfg.modelo.n_simulaciones, 50_000)))})
    return {'final': final, 'escenarios': pd.DataFrame(escenarios), 'sim': (M, W)}


def senado_conjunto(gob_final_mu: float, Dg: Dist, sen: dict, cfg) -> dict:
    """t bivariada (normales correlacionadas con ρ y el mismo factor chi²)."""
    rng = np.random.default_rng(cfg.modelo.semilla + 7)
    n, rho = cfg.modelo.n_simulaciones, cfg.senado.rho_gob_sen
    z1 = rng.standard_normal(n)
    z2 = rho * z1 + np.sqrt(1 - rho ** 2) * rng.standard_normal(n)
    esc = np.sqrt(rng.chisquare(Dg.nu, n) / Dg.nu) if Dg.nu else np.ones(n)
    Mg = gob_final_mu + Dg.sc * z1 / esc
    Ms = sen['mu'] + sen['dist'].sc * z2 / esc
    B, O = Mg > 0, Ms > 0
    W = rng.uniform(cfg.eleccion.writein_pp_min, cfg.eleccion.writein_pp_max, n)
    sen_res = resumir_sim(Ms, W)
    return {'senado': sen_res,
            'conjunto': {'P_D_gob_y_D_sen': float((B & O).mean()), 'P_R_gob_y_D_sen': float((~B & O).mean()),
                         'P_D_gob_y_R_sen': float((B & ~O).mean()), 'P_R_gob_y_R_sen': float((~B & ~O).mean()),
                         'P_D_gob_si_gana_D_sen': float(B[O].mean()) if O.any() else np.nan,
                         'P_D_gob_si_gana_R_sen': float(B[~O].mean()) if (~O).any() else np.nan,
                         'P_voto_dividido': float((B != O).mean()), 'rho': rho,
                         'corr_simulada': float(np.corrcoef(Mg, Ms)[0, 1])}}
