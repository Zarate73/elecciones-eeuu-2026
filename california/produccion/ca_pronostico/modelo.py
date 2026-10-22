"""M5: calibración de sigma con backtest, simulación integrada, porcentajes por candidato
y proyección del conteo para la noche electoral."""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from .encuestas import PATRON_PARTIDISTA, identificar_familia, pesos_m5, simplificar


# ======================================================================================
# Calibración (data/generales_*.csv: 6 contiendas estatales CA 2018–2025)
# ======================================================================================
def calibrar_sigma(cfg, dias_ref: int | None = None) -> dict:
    m = cfg.modelo
    dias_ref = m.dias_calibracion if dias_ref is None else dias_ref
    enc = pd.read_csv(cfg.dir_datos / 'generales_encuestas.csv', parse_dates=['inicio', 'fin'])
    res = pd.read_csv(cfg.dir_datos / 'generales_resultados.csv', parse_dates=['fecha_eleccion'])
    enc['margen'] = 100 * (enc.d_pct - enc.r_pct) / (enc.d_pct + enc.r_pct)
    filas = []
    for _, r in res.iterrows():
        corte = (r.fecha_eleccion - pd.Timedelta(days=dias_ref)).date()
        sub = enc[(enc.eleccion == r.eleccion) & (enc.fin.dt.date <= corte)]
        if len(sub) < 2:
            continue
        medias = [(a + (b - a) / 2).date() for a, b in zip(sub.inicio, sub.fin)]
        partid = sub.encuestadora.map(lambda s: bool(PATRON_PARTIDISTA.search(simplificar(s))))
        w = pesos_m5(medias, corte, partid, sub.encuestadora.map(identificar_familia),
                     m.vida_media_dias, m.penal_interna)
        mu = float(np.dot(w, sub.margen))
        disp2 = float(np.dot(w, (sub.margen - mu) ** 2) / (1 - np.dot(w, w)))
        real = 100 * (r.d_pct - r.r_pct) / (r.d_pct + r.r_pct)
        filas.append({'eleccion': r.eleccion, 'agregado': mu, 'real': real, 'error': real - mu,
                      'muestreo_var': disp2 * float(np.dot(w, w))})
    t = pd.DataFrame(filas)
    rmse = float(np.sqrt(np.mean(t.error ** 2)))
    resto = rmse ** 2 - t.muestreo_var.mean() - m.sigma_dia_pp ** 2 * dias_ref
    sigma_sis = float(np.sqrt(max(resto, m.sigma_sis_min_pp ** 2)))
    if cfg.sigma_sis_fijo is not None:
        sigma_sis = cfg.sigma_sis_fijo
    return {'dias_ref': dias_ref, 'n_elecciones': int(len(t)), 'rmse_historico_pp': rmse,
            'sesgo_medio_pp': float(t.error.mean()), 'sigma_sis_pp': sigma_sis,
            'errores': {k: round(float(v), 2) for k, v in zip(t.eleccion, t.error)}}


# ======================================================================================
# M5
# ======================================================================================
def _logit(p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def pronostico_m5(cfg, agregado: dict, dias: int, sigma_sis: float, delta_m2: float = 0.0,
                  k_sent: float = 1.0, p_kalshi: float | None = None) -> dict:
    m = cfg.modelo
    k = float(np.clip(k_sent, 1.0, m.k_sent_max))
    d2 = delta_m2 if (delta_m2 is not None and np.isfinite(delta_m2) and m.w_m2 > 0) else 0.0
    mu = agregado['margen'] + m.w_m2 * d2
    disp = agregado['dispersion_encuestas'] if np.isfinite(agregado['dispersion_encuestas']) else 0.0
    comp = {'sistematico': sigma_sis ** 2,
            'muestreo_encuestas': disp ** 2 / agregado['n_efectivo'],
            'deriva_hasta_eleccion': m.sigma_dia_pp ** 2 * dias * k,
            'participacion_m2': (m.w_m2 * m.sigma_m2_pp) ** 2 if m.w_m2 > 0 else 0.0}
    sigma = float(np.sqrt(sum(comp.values())))
    escala = sigma * np.sqrt((m.nu_colas - 2) / m.nu_colas)
    sim = mu + escala * np.random.default_rng(m.semilla).standard_t(m.nu_colas, m.n_simulaciones)
    p_mod = float(np.mean(sim > 0))
    p_obj, desplaz = p_mod, 0.0
    if p_kalshi is not None and np.isfinite(p_kalshi):
        p_obj = float(1 / (1 + np.exp(-((1 - m.w_kalshi) * _logit(p_mod) + m.w_kalshi * _logit(p_kalshi)))))
        # la probabilidad mezclada se traslada a la distribución (como Georgia): se desplaza el margen simulado
        # para que P(margen > 0) = p_obj; así margen, intervalos y % de voto son coherentes con la probabilidad
        desplaz = float(-np.quantile(sim, 1 - p_obj))
    sim_modelo, sim = sim, sim + desplaz
    p_fin = float(np.mean(sim > 0))
    q = np.quantile(sim, [.025, .1, .5, .9, .975])
    return {'simulacion': sim, 'simulacion_modelo': sim_modelo, 'media_pp': float(mu), 'media_final_pp': float(mu + desplaz),
            'desplazamiento_kalshi_pp': desplaz, 'p_mezcla_objetivo': p_obj, 'sigma_pp': sigma, 'k_sent_aplicado': k,
            'delta_m2_aplicado_pp': float(m.w_m2 * d2), 'p_modelo': p_mod, 'p_final': p_fin,
            'p_kalshi_usada': p_kalshi, 'w_kalshi': m.w_kalshi if p_kalshi is not None else 0.0,
            'cuantiles_margen_pp': dict(zip(['2.5', '10', '50', '90', '97.5'], [float(x) for x in q])),
            'componentes_varianza_pp2': comp}


def porcentajes(cfg, simulaciones: dict[str, np.ndarray]) -> pd.DataFrame:
    """% del voto válido para gobernador: %D = 50 + margen/2 (top-two, sin candidatos por escrito)."""
    e = cfg.eleccion
    filas = []
    for modelo, margen in simulaciones.items():
        for cand, signo in ((f'{e.candidato_d} (D)', 1), (f'{e.candidato_r} (R)', -1)):
            pct = 50 + signo * margen / 2
            q = np.quantile(pct, [.025, .10, .50, .90, .975])
            filas.append({'modelo': modelo, 'candidato': cand, 'pronostico_pct': float(q[2]),
                          'media_pct': float(pct.mean()), 'ic80_inf': float(q[1]), 'ic80_sup': float(q[3]),
                          'ic95_inf': float(q[0]), 'ic95_sup': float(q[4]),
                          'p_ganar': float(np.mean(signo * margen > 0))})
    return pd.DataFrame(filas)


# ======================================================================================
# Noche electoral
# ======================================================================================
def corrimiento_tardio_primaria(cfg) -> float:
    c = pd.read_csv(cfg.dir_datos / 'conteo_primaria_2026.csv')
    a, f = c.iloc[0], c.iloc[-1]
    r_temp = (a.hilton + a.bianco) / (a.becerra + a.hilton + a.steyer + a.bianco)
    dv = {k: f[k] - a[k] for k in ('becerra', 'hilton', 'steyer', 'bianco')}
    return float(100 * ((dv['hilton'] + dv['bianco']) / sum(dv.values()) - r_temp))


def proyectar_conteo(cfg, votos_d: int, votos_r: int, boletas_restantes: int,
                     corrimiento_r_pp: float | None = None, n_sim: int = 100_000) -> dict:
    """Corrimiento tardío con incertidumbre = 50% de su magnitud (HIPÓTESIS, 1 elección)."""
    cr = corrimiento_tardio_primaria(cfg) if corrimiento_r_pp is None else corrimiento_r_pp
    r_act = votos_r / (votos_d + votos_r)
    rng = np.random.default_rng(cfg.modelo.semilla)
    r_tard = np.clip(r_act + rng.normal(cr, abs(cr) * 0.5, n_sim) / 100, 0, 1)
    d_fin = votos_d + boletas_restantes * (1 - r_tard)
    r_fin = votos_r + boletas_restantes * r_tard
    margen = 100 * (d_fin - r_fin) / (d_fin + r_fin)
    return {'corrimiento_r_pp': cr, 'margen_actual_pp': 100 * (votos_d - votos_r) / (votos_d + votos_r),
            'margen_proyectado_mediana_pp': float(np.median(margen)),
            'intervalo_90_pp': [float(x) for x in np.quantile(margen, [.05, .95])],
            'pct_d_proyectado': float(50 + np.median(margen) / 2),
            'p_d_gana': float(np.mean(margen > 0))}
