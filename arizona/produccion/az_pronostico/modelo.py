"""Modelo general de Arizona (selección por backtest, ver arizona/docs):

  margen   = Σ w_i (margen_i − casa_i) / Σ w_i    (V11 de Georgia: casa contraída, √n, vida media 14 d, 1/firma)
  ventana  últimos 21 días; si hay < 2 encuestadoras, los 21 días previos a la encuesta más reciente
  σ        = √(τ² + s²/k + 0.25²·días que las encuestas son más viejas que el horizonte calibrado); t de Student
  terceros T ~ N(a + c·otros_encuestas, sd), mínimo 0.1 pp;   indecisos 50/50
  Hobbs    = (100 − T + margen)/2 ;  Biggs = (100 − T − margen)/2 ;  recuento si |margen| ≤ 0.5
  final    = logit⁻¹((1 − w)·logit(P_encuestas) + w·logit(promedio Kalshi/Polymarket)),  w = 0.30
  SIN sesgo estatal (en AZ el error no persiste entre ciclos: CRPS 2.471 vs 2.630).
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
from scipy.special import expit, logit
from scipy.stats import norm, t as student_t

from .historico import promedio


class Dist:
    def __init__(self, sd: float, nu: float | None):
        self.sd, self.nu = sd, nu
        self.sc = sd * np.sqrt((nu - 2) / nu) if nu else sd

    def rvs(self, mu, n, rng):
        return mu + (self.sc * rng.standard_t(self.nu, n) if self.nu else rng.normal(0, self.sd, n))


def seleccionar_ventana(p: pd.DataFrame, cfg, dias: int | None = None, regla: str = 'desplazada'):
    m = cfg.modelo
    dias = dias or m.ventana_dias_eleccion
    lim = pd.Timestamp(cfg.dia_eleccion) - pd.Timedelta(days=dias)
    q = p[p.fin >= lim]
    nota = {'desde': str(lim.date()), 'ampliada': False, 'regla': 'normal'}
    if q.pollster_key.nunique() < m.min_encuestadoras:
        if regla == 'v11':
            desde = p.groupby('pollster_key').fin.max().sort_values(ascending=False).head(m.min_encuestadoras).min()
        else:
            desde = p.fin.max() - pd.Timedelta(days=m.ventana_dias_eleccion)
        q = p[p.fin >= desde]
        nota.update({'desde': str(desde.date()), 'ampliada': True, 'regla': regla})
    return q, nota


def simular(mu, dist: Dist, t_media, t_sd, n, rng) -> pd.DataFrame:
    M = dist.rvs(mu, n, rng)
    T = np.maximum(rng.normal(t_media, t_sd, n), 0.1)
    return pd.DataFrame({'D': (100 - T + M) / 2, 'R': (100 - T - M) / 2, 'T': T, 'M': M})


def resumen(s: pd.DataFrame, nombre: str, recuento: float, p_final: float | None = None) -> dict:
    q = lambda c, x: float(s[c].quantile(x))
    p_mod = float((s.M > 0).mean())
    return {'escenario': nombre, 'margen': float(s.M.mean()), 'sd': float(s.M.std()),
            'IC80': (q('M', .1), q('M', .9)), 'IC95': (q('M', .025), q('M', .975)),
            'pct_D': float(s.D.mean()), 'pct_D_IC80': (q('D', .1), q('D', .9)),
            'pct_R': float(s.R.mean()), 'pct_R_IC80': (q('R', .1), q('R', .9)),
            'pct_terceros': float(s['T'].mean()), 'pct_terceros_IC80': (q('T', .1), q('T', .9)),
            'P_D_encuestas': p_mod, 'P_D': p_final if p_final is not None else p_mod,
            'P_recuento': float((s.M.abs() <= recuento).mean()), 'P_D_mas_50': float((s.D > 50).mean())}


def lado_partidista(pollster: str) -> str | None:
    """'D', 'R' o None. Una encuesta bipartidista (Fabrizio Ward (R) / Impact Research (D)) no se ajusta."""
    lados = set(re.findall(r'\((D|R)\)', str(pollster)))
    return lados.pop() if len(lados) == 1 else None


def pronosticar(p: pd.DataFrame, par: dict, mk: dict, cfg) -> dict:
    m = cfg.modelo
    rng = np.random.default_rng(m.semilla)
    n = int(m.n_simulaciones)
    rec = float(cfg.eleccion.recuento_pp)
    q, nota = seleccionar_ventana(p, cfg)
    h = int(par['horizonte_dias'])
    edad_extra = max((pd.Timestamp(cfg.dia_eleccion) - q.fin.max()).days - h, 0)
    var_deriva = m.sigma_dia_pp ** 2 * edad_extra
    house = par['efectos_casa']
    mu_enc, otros_enc, k, w = promedio(q, house, m.vida_media_dias)
    sesgo = par['sesgo_az_contraido'] if m.sesgo_estatal else 0.0
    mu = mu_enc - sesgo
    sd = float(np.sqrt(par['tau'] ** 2 + par['s'] ** 2 / max(k, 1) + var_deriva))
    dist = Dist(sd, par['nu'])
    a, c, tsd = par['terceros_a'], par['terceros_c'], par['terceros_sd']
    t_media = max(a + c * otros_enc, 0.1)
    base = simular(mu, dist, t_media, tsd, n, rng)
    p_mod = float((base.M > 0).mean())
    w_m = m.peso_mercados if mk.get('promedio_D') is not None else 0.0
    p_final = p_mod if w_m == 0 else float(expit((1 - w_m) * logit(np.clip(p_mod, 1e-4, 1 - 1e-4))
                                                 + w_m * logit(np.clip(mk['promedio_D'], 1e-4, 1 - 1e-4))))
    final = resumen(base, 'FINAL: encuestas + mercados (Kalshi y Polymarket)', rec, p_final)
    final.update({'peso_mercados_aplicado': w_m, 'margen_encuestas': mu_enc, 'k': k, 'ventana': nota,
                  'dias_extra_encuestas': edad_extra, 'terceros_media': t_media})

    esc = [final, resumen(base, 'Solo encuestas (sin mercados)', rec)]
    sim = lambda mu_, d_=dist, tm=t_media, ts=tsd: simular(mu_, d_, tm, ts, n, rng)
    sb = par['sesgo_az_contraido']
    esc.append(resumen(sim(mu_enc - sb), f'Con sesgo estatal AZ (V11, {sb:+.2f} pp)', rec))
    esc.append(resumen(sim(mu, Dist(sd, None)), 'Distribución normal', rec))
    esc.append(resumen(sim(mu, dist, 0.1, 0.0), 'Sin terceros', rec))
    esc.append(resumen(sim(mu, Dist(float(np.sqrt(sd ** 2 - var_deriva)), par['nu'])), 'Sin deriva por encuestas viejas', rec))
    for nom, kw in (('Regla literal V11 (última encuesta de cada firma)', {'regla': 'v11'}),
                    ('Ventana 45 días', {'dias': 45}), ('Ventana 60 días', {'dias': 60})):
        qq, _ = seleccionar_ventana(p, cfg, **kw)
        m2, o2, k2, _ = promedio(qq, house, m.vida_media_dias)
        ed2 = max((pd.Timestamp(cfg.dia_eleccion) - qq.fin.max()).days - h, 0)
        s2 = float(np.sqrt(par['tau'] ** 2 + par['s'] ** 2 / max(k2, 1) + m.sigma_dia_pp ** 2 * ed2))
        esc.append(resumen(sim(m2 - sesgo, Dist(s2, par['nu']), max(a + c * o2, .1)), f'{nom} ({k2} encuestadoras)', rec))
    sin_casa, *_ = promedio(q, {}, m.vida_media_dias)
    esc.append(resumen(sim(sin_casa - sesgo), 'Sin efectos de casa', rec))
    ep = par.get('efectos_partidistas', {})
    lado = q.pollster.map(lado_partidista)
    casa_solo = {kk: (ep.get(ll, 0.0) if ll else 0.0) for kk, ll in zip(q.pollster_key, lado)}
    casa_mix = {kk: house.get(kk, ep.get(ll, 0.0) if ll else 0.0) for kk, ll in zip(q.pollster_key, lado)}
    for nom, mp in (('Ajuste partidista (patrocinador D/R)', casa_solo),
                    ('Efecto de casa + partidista si la firma no tiene historia', casa_mix)):
        m_p, *_ = promedio(q, mp, m.vida_media_dias)
        esc.append(resumen(sim(m_p - sesgo), f"{nom} [D {ep.get('D', 0):+.1f}, R {ep.get('R', 0):+.1f}]", rec))
    for nom in ('kalshi', 'polymarket'):
        x = mk.get(nom, {})
        if x.get('usable'):
            esc.append({'escenario': f'Solo {nom.capitalize()} (probabilidad)', 'P_D': x['p_D'],
                        'margen': float(dist.sc * student_t.ppf(x['p_D'], par['nu']))})
    rg = mk.get('rangos', {})
    if 'P_D' in rg:
        esc.append({'escenario': 'Polymarket por rangos de margen', 'P_D': rg['P_D'], 'margen': rg['margen_media'],
                    'sd': rg['margen_sd']})

    tabla = q.assign(efecto_casa=q.pollster_key.map(house).fillna(0.0), peso=w.values,
                     patrocinador=lado.fillna('—'), efecto_partidista=lado.map(ep).fillna(0.0))
    tabla['margen_corregido'] = tabla.margin_poll - tabla.efecto_casa
    p = p.assign(en_ventana=p.index.isin(q.index),
                 efecto_casa=p.pollster_key.map(house).fillna(0.0))
    p['margen_corregido'] = p.margin_poll - p.efecto_casa
    return {'final': final, 'escenarios': pd.DataFrame(esc), 'ventana': tabla, 'encuestas': p, 'mu': mu,
            'sd': sd, 'nu': par['nu'], 'sim': base}
