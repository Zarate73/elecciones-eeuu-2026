"""Modelo general de Maine (selección por backtest, ver maine/backtest y maine/docs).
Base: Pennsylvania v1.1.0 / Nevada v1.1.0 / Florida v1.1.0.

  margen   = Σ w_i (margen_i − casa_i) / Σ w_i − sesgo_ME   (V11 de Georgia: casa contraída, √n, vida media 14 d,
             1/firma; sesgo estatal con vida media de 4 años, contraído por Bayes empírico, estimado SIN contiendas
             de una sola encuestadora: hoy +2.43 pp pro-D, se resta)
  ventana  últimos 21 días; si hay < 2 encuestadoras, los 21 días previos a la encuesta más reciente
  σ        = √(τ² + s²/k + 0.25²·días que las encuestas son más viejas que el horizonte calibrado); t de Student
  terceros T ~ N(a + c·otros, sd) con «otros» promediado solo entre encuestas que reportan terceros (Bennett);
           si ninguna los reporta, media histórica sin reporte;   indecisos 50/50
  Pingree  = (100 − T + margen)/2 ;  Charles = (100 − T − margen)/2 ;  mayoría simple (sin voto preferencial en la
           general de gobernador); P(|margen| ≤ 0.5) se reporta (Maine no tiene recuento automático)
  final    = logit⁻¹((1 − w)·logit(P_encuestas) + w·logit(promedio Kalshi/Polymarket)),  w = 0.30; la distribución
             se desplaza para que P(margen > 0) = final. Kalshi tiene un tercer contrato (Bennett): se usa D/(D + R).
  Sesgo estatal: en ME las encuestas sobreestimaron al demócrata en 8 de 13 contiendas (sobre todo las de Collins).
  Con sesgo 3.32 vs sin sesgo 3.52 (cronológico P = 0.014). Estimarlo sin contiendas k = 1 mejora en ME (P = 0.99) y a
  nivel nacional (P = 0.74); estimarlo solo con el mismo cargo empeora a nivel nacional.
  Independiente fuerte: en 139 contiendas con terceros ≥ 5 % el tercero se desinfla 1.1 pp en promedio y la regla T4
  ya lo corrige (sesgo −0.07); el voto que pierde no va claramente a ningún lado (pendiente +0.28, IC90 −0.17 a +0.72):
  indecisos/terceros 50/50.
  Escenarios: cada uno con su probabilidad sin y con mercados; influencia de cada encuesta; sesgo con todas las
  contiendas; terceros con reducción; peso de mercados 0.15/0.50.
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


def resumen(s: pd.DataFrame, nombre: str, recuento: float) -> dict:
    """Todo sale de la misma simulación: P_D es siempre la fracción de simulaciones con margen > 0."""
    q = lambda c, x: float(s[c].quantile(x))
    return {'escenario': nombre, 'margen': float(s.M.mean()), 'sd': float(s.M.std()),
            'IC80': (q('M', .1), q('M', .9)), 'IC95': (q('M', .025), q('M', .975)),
            'pct_D': float(s.D.mean()), 'pct_D_IC80': (q('D', .1), q('D', .9)),
            'pct_R': float(s.R.mean()), 'pct_R_IC80': (q('R', .1), q('R', .9)),
            'pct_terceros': float(s['T'].mean()), 'pct_terceros_IC80': (q('T', .1), q('T', .9)),
            'P_D': float((s.M > 0).mean()),
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
    sesgo = par['sesgo_contraido'] if m.sesgo_estatal else 0.0
    mu = mu_enc - sesgo
    sd = float(np.sqrt(par['tau'] ** 2 + par['s'] ** 2 / max(k, 1) + var_deriva))
    dist = Dist(sd, par['nu'])
    def terceros(o: float) -> tuple[float, float]:
        """«No reportado» ≠ 0 %: con encuestas que reportan terceros, a + c·o; si ninguna, media histórica sin reporte."""
        if np.isfinite(o):
            return max(par['terceros_a'] + par['terceros_c'] * o, 0.1), par['terceros_sd']
        return max(par['terceros_sin_reporte'], 0.1), par['terceros_sin_reporte_sd']

    t_media, tsd = terceros(otros_enc)
    base = simular(mu, dist, t_media, tsd, n, rng)
    p_mod = float((base.M > 0).mean())
    w_m = m.peso_mercados if mk.get('promedio_D') is not None else 0.0

    def mezclar(s_: pd.DataFrame, w: float | None = None) -> tuple[float, float]:
        """Mismo ajuste por mercados que el final: (probabilidad mezclada, desplazamiento del margen simulado)."""
        w = w_m if w is None else w
        p0 = float((s_.M > 0).mean())
        if w == 0 or mk.get('promedio_D') is None:
            return p0, 0.0
        pf = float(expit((1 - w) * logit(np.clip(p0, 1e-4, 1 - 1e-4))
                         + w * logit(np.clip(mk['promedio_D'], 1e-4, 1 - 1e-4))))
        return pf, float(-np.quantile(s_.M, 1 - pf))

    # La probabilidad mezclada se traslada a la distribución: se desplaza el margen simulado lo justo para que
    # P(margen > 0) = p_final (mismo tratamiento que Georgia, con el cuantil empírico de la propia simulación).
    # Así margen, intervalos, % de voto y recuento son coherentes con la probabilidad publicada.
    p_final, desplaz = mezclar(base)

    def desplazar(s_: pd.DataFrame, dz: float) -> pd.DataFrame:
        M_ = s_.M + dz
        return pd.DataFrame({'D': (100 - s_['T'] + M_) / 2, 'R': (100 - s_['T'] - M_) / 2, 'T': s_['T'], 'M': M_})

    sim_final = desplazar(base, desplaz)
    final = resumen(sim_final, 'FINAL: encuestas + mercados (Kalshi y Polymarket)', rec)
    final.update({'P_D_encuestas': p_mod, 'P_D_mezcla_objetivo': p_final, 'desplazamiento_mercados_pp': desplaz,
                  'peso_mercados_aplicado': w_m, 'margen_encuestas': mu_enc, 'k': k, 'ventana': nota,
                  'dias_extra_encuestas': edad_extra, 'terceros_media': t_media,
                  'terceros_reportados_encuestas': otros_enc if np.isfinite(otros_enc) else None,
                  'terceros_regimen': 'reportado en encuestas' if np.isfinite(otros_enc) else 'ninguna encuesta de la ventana los reporta',
                  'sesgo_estatal_aplicado': sesgo,
                  'sesgo_estatal_bruto': par['sesgo_bruto'], 'contraccion_sesgo': par.get('contraccion'),
                  'P_D_con_mercados': p_final, 'margen_con_mercados': float(sim_final.M.mean())})

    def fila(s_: pd.DataFrame, nombre: str) -> dict:
        """Escenario sin mercados + la misma mezcla con mercados del final (columnas *_con_mercados)."""
        r_ = resumen(s_, nombre, rec)
        pf, dz = mezclar(s_)
        r_.update({'P_D_con_mercados': pf, 'margen_con_mercados': float(s_.M.mean() + dz)})
        return r_

    sim = lambda mu_, d_=dist, tm=t_media, ts=tsd: simular(mu_, d_, tm, ts, n, rng)
    sb, sr = par['sesgo_contraido'], par['sesgo_bruto']
    # 2 × 2 sesgo × mercados: cada efecto se aísla manteniendo fijo el otro
    esc = [final, fila(base, 'Con sesgo estatal, sin mercados (solo encuestas)')]
    s_alt = sim(mu_enc - sb) if not m.sesgo_estatal else sim(mu_enc)
    nom_alt = 'Con sesgo estatal' if not m.sesgo_estatal else 'Sin sesgo estatal'
    esc.append(fila(s_alt, f'{nom_alt}, sin mercados'))
    pf_alt, dz_alt = mezclar(s_alt)
    r_alt = resumen(desplazar(s_alt, dz_alt), f'{nom_alt}, con mercados (mismo ajuste que el final)', rec)
    r_alt.update({'P_D_con_mercados': r_alt['P_D'], 'margen_con_mercados': r_alt['margen']})
    esc.append(r_alt)
    # sensibilidad (cada fila trae también su probabilidad con mercados)
    esc.append(fila(sim(mu_enc - sr), f'Sesgo estatal sin contraer ({-sr:+.2f} pp)'))
    esc.append(fila(sim(mu_enc - 0.5 * sb), f'Sesgo estatal a la mitad ({-0.5 * sb:+.2f} pp)'))
    if par.get('sesgo_regla') == 'k2' and 'sesgo_contraido_todas' in par:      # Maine: la alternativa es «todas»
        st_ = par['sesgo_contraido_todas']
        esc.append(fila(sim(mu_enc - st_), f'Sesgo estimado con todas las contiendas, incluidas las de una sola '
                                           f'encuestadora ({-st_:+.2f} pp)'))
    elif 'sesgo_contraido_k2' in par:                       # sin contiendas de una sola encuestadora (revisión NV)
        sk2 = par['sesgo_contraido_k2']
        esc.append(fila(sim(mu_enc - sk2), f'Sesgo estimado sin contiendas de una sola encuestadora ({-sk2:+.2f} pp)'))
    esc.append(fila(sim(mu, Dist(sd, None)), 'Distribución normal'))
    esc.append(fila(sim(mu, dist, 0.1, 0.0), 'Sin terceros'))
    esc.append(fila(sim(mu, Dist(float(np.sqrt(sd ** 2 - var_deriva)), par['nu'])), 'Sin deriva por encuestas viejas'))
    esc.append(fila(sim(mu, Dist(float(np.sqrt(sd ** 2 - var_deriva + 3 * var_deriva)), par['nu'])),
                    f'Deriva al doble (0.50 pp/día, {edad_extra} días)'))
    for nom, kw in (('Regla literal V11 (última encuesta de cada firma)', {'regla': 'v11'}),
                    ('Ventana 45 días', {'dias': 45}), ('Ventana 60 días', {'dias': 60})):
        qq, _ = seleccionar_ventana(p, cfg, **kw)
        m2, o2, k2, _ = promedio(qq, house, m.vida_media_dias)
        ed2 = max((pd.Timestamp(cfg.dia_eleccion) - qq.fin.max()).days - h, 0)
        s2 = float(np.sqrt(par['tau'] ** 2 + par['s'] ** 2 / max(k2, 1) + m.sigma_dia_pp ** 2 * ed2))
        esc.append(fila(sim(m2 - sesgo, Dist(s2, par['nu']), *terceros(o2)), f'{nom} ({k2} encuestadoras)'))
    sin_casa, *_ = promedio(q, {}, m.vida_media_dias)
    esc.append(fila(sim(sin_casa - sesgo), 'Sin efectos de casa'))
    for kk in (4, 16):
        m_k, *_ = promedio(q, par.get(f'efectos_casa_k{kk}', house), m.vida_media_dias)
        esc.append(fila(sim(m_k - sesgo), f'Efectos de casa con contracción k = {kk} (base 8)'))
    ep = par.get('efectos_partidistas', {})
    lado = q.pollster.map(lado_partidista)
    casa_solo = {kk: (ep.get(ll, 0.0) if ll else 0.0) for kk, ll in zip(q.pollster_key, lado)}
    casa_mix = {kk: house.get(kk, ep.get(ll, 0.0) if ll else 0.0) for kk, ll in zip(q.pollster_key, lado)}
    for nom, mp in (('Ajuste partidista (patrocinador D/R)', casa_solo),
                    ('Efecto de casa + partidista si la firma no tiene historia', casa_mix)):
        m_p, *_ = promedio(q, mp, m.vida_media_dias)
        esc.append(fila(sim(m_p - sesgo), f"{nom} [D {ep.get('D', 0):+.1f}, R {ep.get('R', 0):+.1f}]"))
    # --- dependencia de una sola encuesta, terceros y peso de mercados (revisión de Nevada del 22-oct)
    def con_encuestas(pp: pd.DataFrame, nombre: str) -> None:
        """Reconstruye el promedio con otro conjunto de encuestas, con la misma regla de ventana (y ampliación)."""
        if pp.empty:
            return
        q2, nt = seleccionar_ventana(pp, cfg)
        m2, o2, k2, _ = promedio(q2, house, m.vida_media_dias)
        ed2 = max((pd.Timestamp(cfg.dia_eleccion) - q2.fin.max()).days - h, 0)
        s2 = float(np.sqrt(par['tau'] ** 2 + par['s'] ** 2 / max(k2, 1) + m.sigma_dia_pp ** 2 * ed2))
        firmas = ', '.join(q2.sort_values('fin').pollster.str.split(r' [\(—]').str[0].unique())
        esc.append(fila(sim(m2 - sesgo, Dist(s2, par['nu']), *terceros(o2)),
                        f'{nombre} → ventana desde {nt["desde"]}: {firmas}'))

    pesos = w.sort_values(ascending=False)
    for idx in pesos.index[:3]:                              # influencia de cada una de las encuestas con más peso
        fila_q = q.loc[idx]
        con_encuestas(p[p.pollster_key != fila_q.pollster_key],
                      f'Sin {fila_q.pollster} (pesa {pesos[idx]:.0%})')
    lado_p = p.pollster.map(lado_partidista)
    if lado_p.notna().any():
        con_encuestas(p[lado_p.isna()], 'Sin encuestas de patrocinio partidista')
    t_rep = otros_enc if np.isfinite(otros_enc) else None
    for f_, nom_f in ((0.6, 'reducción moderada'), (0.3, 'reducción pronunciada')):
        tm, ts = terceros(otros_enc * f_) if t_rep is not None else (max(t_media * f_, 0.1), tsd)
        esc.append(fila(sim(mu, dist, tm, ts), f'Terceros: {nom_f} (apoyo × {f_:.1f}; media {tm:.1f} %)'))
    for w_alt in (0.15, 0.50):
        if w_m > 0:
            pf, dz = mezclar(base, w_alt)
            r_w = resumen(desplazar(base, dz), f'Peso de mercados {w_alt:.2f} (base {w_m:.2f})', rec)
            r_w.update({'P_D_con_mercados': r_w['P_D'], 'margen_con_mercados': r_w['margen']})
            esc.append(r_w)
    for nom in ('kalshi', 'polymarket'):
        x = mk.get(nom, {})
        if x.get('usable'):
            esc.append({'escenario': f'Solo {nom.capitalize()} (probabilidad)', 'P_D': x['p_D'],
                        'margen': float(dist.sc * student_t.ppf(x['p_D'], par['nu']))})
    rg = mk.get('rangos', {})
    if 'P_D' in rg:                     # solo con partición completa (incluye el contrato del lado perdedor)
        esc.append({'escenario': 'Polymarket por rangos de margen (normal ajustada a la partición completa; '
                                 'P de los contratos)', 'P_D': rg['P_D'], 'margen': rg['margen_media'], 'sd': rg['margen_sd']})

    tabla = q.assign(efecto_casa=q.pollster_key.map(house).fillna(0.0), peso=w.values,
                     patrocinador=lado.fillna('—'), efecto_partidista=lado.map(ep).fillna(0.0))
    tabla['margen_corregido'] = tabla.margin_poll - tabla.efecto_casa
    p = p.assign(en_ventana=p.index.isin(q.index),
                 efecto_casa=p.pollster_key.map(house).fillna(0.0))
    p['margen_corregido'] = p.margin_poll - p.efecto_casa
    return {'final': final, 'escenarios': pd.DataFrame(esc), 'ventana': tabla, 'encuestas': p, 'mu': mu,
            'mu_final': mu + desplaz, 'sd': sd, 'nu': par['nu'], 'sim': sim_final}
