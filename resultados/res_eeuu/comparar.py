"""Conteo preliminar frente al pronóstico final: error, posición en la distribución y métricas agregadas.

El pronóstico final de cada estado es la distribución del margen D−R que publicó el tablero en su última corrida
(t de Student con media `margen`, sd `sd` y `nu` grados de libertad; es la misma aproximación que dibuja el tablero)
y sus intervalos del 80/95 % publicados. El «real» es el conteo de ese momento: con avance parcial, el error es
PROVISIONAL (el voto temprano, el del día y el de correo llegan en orden distinto en cada estado).
"""
from __future__ import annotations

import math

import numpy as np
from scipy import stats

ESTADOS = ('sin_datos', 'parcial', 'casi_completo')


def _escala_t(sd: float, nu: float) -> float:
    return sd * math.sqrt((nu - 2) / nu) if nu and nu > 2 else sd


def crps_t(obs: float, mu: float, sd: float, nu: float) -> float:
    """CRPS de una t de Student escalada (forma cerrada; Jordan et al. 2019, scoringRules)."""
    s = _escala_t(sd, nu)
    z = (obs - mu) / s
    if not nu or nu > 1e6:
        return s * (z * (2 * stats.norm.cdf(z) - 1) + 2 * stats.norm.pdf(z) - 1 / math.sqrt(math.pi))
    from scipy.special import beta
    bfrac = beta(0.5, nu - 0.5) / beta(0.5, nu / 2) ** 2
    return s * (z * (2 * stats.t.cdf(z, nu) - 1) + 2 * stats.t.pdf(z, nu) * (nu + z * z) / (nu - 1)
                - 2 * math.sqrt(nu) / (nu - 1) * bfrac)


def comparar(p: dict, conteo: dict | None, avance_completo: float = 0.95) -> dict:
    """p: bloque «pronostico» del tablero congelado; conteo: Conteo.dict() o None."""
    out = {'pronostico': {k: p.get(k) for k in ('P_D', 'pct_D', 'pct_R', 'pct_D_IC80', 'pct_R_IC80', 'margen', 'margen_IC80',
                                                 'margen_IC95', 'sd', 'nu')}}
    if not conteo or conteo.get('total', 0) <= 0:
        return {**out, 'estado': 'sin_datos'}
    tot = conteo['total']
    pd_, pr_ = 100 * conteo['votos_D'] / tot, 100 * conteo['votos_R'] / tot
    m = pd_ - pr_
    av = conteo.get('avance')
    estado = 'casi_completo' if av is not None and av >= avance_completo else 'parcial'
    mu, sd, nu = float(p['margen']), float(p['sd']), float(p.get('nu') or 30)
    pct = float(stats.t.cdf((m - mu) / _escala_t(sd, nu), nu))
    lider = 'D' if m > 0 else 'R' if m < 0 else 'empate'
    fav = 'D' if p['P_D'] >= 0.5 else 'R'
    ic80, ic95 = p.get('margen_IC80') or [None, None], p.get('margen_IC95') or [None, None]
    return {**out, 'estado': estado, 'avance': av, 'avance_txt': conteo.get('avance_txt', ''), 'fuente': conteo['fuente'],
            'url': conteo.get('url', ''), 'actualizado': conteo.get('actualizado'), 'consultado': conteo.get('consultado'),
            'votos': {'D': conteo['votos_D'], 'R': conteo['votos_R'], 'otros': conteo['votos_otros'], 'total': tot},
            'pct_D': pd_, 'pct_R': pr_, 'pct_otros': 100 - pd_ - pr_, 'margen': m,
            'error_margen': m - mu,                                  # > 0: el demócrata va mejor que el pronóstico
            'error_pct_D': pd_ - p['pct_D'], 'error_pct_R': pr_ - p['pct_R'],
            'percentil': pct, 'en_IC80': bool(ic80[0] is not None and ic80[0] <= m <= ic80[1]),
            'en_IC95': bool(ic95[0] is not None and ic95[0] <= m <= ic95[1]),
            'lider': lider, 'favorito': fav, 'acierto_lider': lider == fav,
            'brier': float((p['P_D'] - (1.0 if m > 0 else 0.0)) ** 2), 'crps': float(crps_t(m, mu, sd, nu))}


def agregado(filas: list[dict], solo_completos: bool = False) -> dict | None:
    """Métricas de todos los estados con datos (o solo los casi completos)."""
    f = [x for x in filas if x['estado'] == 'casi_completo' or (not solo_completos and x['estado'] == 'parcial')]
    if not f:
        return None
    e = np.array([x['error_margen'] for x in f])
    return {'n': len(f), 'estados': [x['clave'] for x in f], 'MAE_margen': float(np.abs(e).mean()),
            'RMSE_margen': float(np.sqrt((e ** 2).mean())), 'sesgo_margen': float(e.mean()),
            'cobertura_IC80': float(np.mean([x['en_IC80'] for x in f])), 'cobertura_IC95': float(np.mean([x['en_IC95'] for x in f])),
            'aciertos_lider': int(sum(x['acierto_lider'] for x in f)), 'brier': float(np.mean([x['brier'] for x in f])),
            'crps': float(np.mean([x['crps'] for x in f]))}
