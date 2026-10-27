"""Modelo general de Ohio (selección por backtest, ver ohio/backtest y ohio/docs).
Base: Nueva York v1.1.0 / Illinois v1.1.0 / Texas / Maine / Pennsylvania / Nevada / Florida (Georgia V11).

  margen   = Σ w_i (margen_i − casa_i) / Σ w_i − sesgo_OH   (V11 de Georgia: casa contraída, √n, vida media 14 d,
             1/firma; sesgo estatal con vida media de 4 años, contraído por Bayes empírico, con todas las contiendas
             del estado: hoy +4.04 pp pro-D, se resta)
  ventana  últimos 21 días; si hay < 2 encuestadoras, los 21 días previos a la encuesta más reciente
  σ        = √(τ² + s²/k + σ_d²·d), σ_d = 0.25, d = días que las encuestas son más viejas que el horizonte calibrado;
           t de Student. La deriva es un PASEO ALEATORIO: la VARIANZA crece linealmente con d y la desviación estándar
           adicional con √d (0.25 pp por √día; 3 días → 0.43 pp), no 0.25 pp por día (revisión OH-04).
  terceros real = a + c·(otros en las encuestas que los reportan) (Don Kissick, Libertario, y votos por escrito);
           indecisos 50/50
  Acton    = (100 − T + margen)/2 ;  Ramaswamy = (100 − T − margen)/2 ;  P(|margen| ≤ 0.25) = recuento automático
  final    = logit⁻¹((1 − w)·logit(P_encuestas) + w·logit(promedio Kalshi/Polymarket)),  w = 0.30; la distribución
             se desplaza para que P(margen > 0) = final.
  Sesgo estatal (backtest de OH, 957 contiendas, 24 de OH): las encuestas sobreestimaron al demócrata en 16 de 24
  contiendas y en todas desde 2014 (+2.9 a +8.1 pp; gobernador 2018 +5.4, 2022 +8.1). LOYO 2.066 vs 2.478 sin sesgo
  (P = 0.05), cronológico 1.802 vs 2.464 (P = 0.002); «k2» empata y «por cargo» es peor (P = 0.010).
  Escenarios: cada uno con su probabilidad sin y con mercados; influencia de cada encuesta; sesgo k2, por cargo
  (gobernador), sin sesgo y sin cada contienda del estado (extremos); fechas por el punto medio del campo (como el
  histórico de FiveThirtyEight); ventana de 45 y 60 días; sin encuestas partidistas; peso de mercados 0.15/0.50.
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


def tercero_principal(s: pd.DataFrame, m) -> dict | None:
    """Voto del único tercero en la boleta (Ohio: Don Kissick, Libertario) = terceros simulados − votos por escrito.

    Es un cálculo POSTERIOR a la simulación, con su propio generador aleatorio: no cambia el margen, los porcentajes de
    D y R ni P(D). Votos por escrito ~ N(votos_escritos) recortados a [0, T] (Ohio 2018: 0.00 %; 2022: 0.22 %).
    `umbral_tercero_pct`: en Ohio un partido menor conserva su reconocimiento si su candidato a gobernador saca ≥ 3 %."""
    nombre = m.get('tercero_principal')
    if not nombre:
        return None
    w_m, w_sd = m.get('votos_escritos', [0.1, 0.1])
    rng = np.random.default_rng(int(m.semilla) + 1)
    T = s['T'].to_numpy()
    W = np.clip(rng.normal(w_m, w_sd, len(T)), 0, T)
    K = T - W
    u = float(m.get('umbral_tercero_pct', 3.0))
    return {'nombre': str(nombre), 'pct': float(K.mean()), 'pct_IC80': (float(np.quantile(K, .1)), float(np.quantile(K, .9))),
            'umbral_pct': u, 'P_umbral': float((K >= u).mean()),
            'P_gana': float((K > np.maximum(s.D.to_numpy(), s.R.to_numpy())).mean()),
            'votos_escritos_pct': float(W.mean())}


def resumen(s: pd.DataFrame, nombre: str, recuento: float) -> dict:
    """Todo sale de la misma simulación: P_D es siempre la fracción de simulaciones con margen > 0."""
    q = lambda c, x: float(s[c].quantile(x))
    return {'escenario': nombre, 'margen': float(s.M.mean()), 'sd': float(s.M.std()),
            'IC80': (q('M', .1), q('M', .9)), 'IC95': (q('M', .025), q('M', .975)),
            'pct_D': float(s.D.mean()), 'pct_D_IC80': (q('D', .1), q('D', .9)),
            'pct_R': float(s.R.mean()), 'pct_R_IC80': (q('R', .1), q('R', .9)),
            'pct_terceros': float(s['T'].mean()), 'pct_terceros_IC80': (q('T', .1), q('T', .9)),
            'P_D': float((s.M > 0).mean()),
            # mayoría simple: con independiente fuerte (Maine): P_D es P(D > R). Para ganar, D también debe superar a T.
            # T es TODO el voto de terceros (independiente + otros), así que P(T > max(D, R)) es una cota superior de
            # P(gana el independiente) en el espacio que simula el modelo (no modela a Bennett por separado).
            'P_D_gana_3': float(((s.D > s.R) & (s.D > s['T'])).mean()),
            'P_tercero_gana_cota': float((s['T'] > np.maximum(s.D, s.R)).mean()),
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
    var_deriva = m.sigma_dia_pp ** 2 * edad_extra      # paseo aleatorio: varianza σ_d²·d → sd adicional σ_d·√d
    house = par['efectos_casa']
    mu_enc, otros_enc, k, w = promedio(q, house, m.vida_media_dias)
    sesgo = par['sesgo_contraido'] if m.sesgo_estatal else 0.0
    mu = mu_enc - sesgo
    sd = float(np.sqrt(par['tau'] ** 2 + par['s'] ** 2 / max(k, 1) + var_deriva))
    dist = Dist(sd, par['nu'])
    fijos = m.get('terceros_fijos')                 # solo si la boleta tiene únicamente a D y R (Nueva York); Ohio no

    def terceros(o: float) -> tuple[float, float]:
        """«No reportado» ≠ 0 %: con encuestas que reportan terceros, a + c·o; si ninguna, media histórica sin reporte.
        Si la boleta solo tiene a los dos candidatos (terceros_fijos en la configuración), el «otro» de las encuestas no
        tiene a quién ir: terceros = votos por escrito, fijos (media, sd)."""
        if fijos:
            return float(fijos[0]), float(fijos[1])
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
                  'terceros_regimen': ('solo dos candidatos en la boleta (votos por escrito)' if fijos else
                                       'reportado en encuestas' if np.isfinite(otros_enc) else 'ninguna encuesta de la ventana los reporta'),
                  'sesgo_estatal_aplicado': sesgo,
                  'sesgo_estatal_bruto': par['sesgo_bruto'], 'contraccion_sesgo': par.get('contraccion'),
                  'P_D_con_mercados': p_final, 'margen_con_mercados': float(sim_final.M.mean())})
    tp = tercero_principal(sim_final, m)
    if tp:
        final['tercero_principal'] = tp

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
    if par.get('sesgo_regla') == 'k2' and 'sesgo_contraido_todas' in par:      # la alternativa es «todas»
        st_ = par['sesgo_contraido_todas']
        esc.append(fila(sim(mu_enc - st_), f'Sesgo estimado con todas las contiendas, incluidas las de una sola '
                                           f'encuestadora ({-st_:+.2f} pp)'))
    elif 'sesgo_contraido_k2' in par:                       # sin contiendas de una sola encuestadora (revisión NV)
        sk2 = par['sesgo_contraido_k2']
        esc.append(fila(sim(mu_enc - sk2), f'Sesgo estimado sin contiendas de una sola encuestadora ({-sk2:+.2f} pp)'))
    loco = par.get('sesgo_loco') or []                       # revisión de Illinois: sin cada contienda del estado
    if loco:
        a_, b_ = min(loco, key=lambda z: z['sesgo_contraido']), max(loco, key=lambda z: z['sesgo_contraido'])
        for x in (a_, b_):                                  # extremos de la corrección al quitar UNA contienda
            esc.append(fila(sim(mu_enc - x['sesgo_contraido']),
                            f"Sesgo sin la contienda {x['race']} ({-x['sesgo_contraido']:+.2f} pp; rango al quitar una de "
                            f"{len(loco)}: {-b_['sesgo_contraido']:+.2f} a {-a_['sesgo_contraido']:+.2f})"))
    if np.isfinite(par.get('sesgo_contraido_gob', np.nan)):  # solo contiendas de gobernador del estado (revisión de Texas)
        sg = par['sesgo_contraido_gob']
        esc.append(fila(sim(mu_enc - sg), f'Sesgo estimado solo con contiendas de gobernador ({-sg:+.2f} pp)'))
    esc.append(fila(sim(mu, Dist(sd, None)), 'Distribución normal'))
    # revisión del 24-oct: ventana ampliada (la mayor parte del peso tiene > 21 días). Escenario, no regla: en la emulación
    # del backtest k efectivo + deriva ponderada mejora apenas (CRPS 3.391 vs 3.397, P = 0.73) y no es significativo.
    wn = np.asarray(w, float) / float(np.sum(w))
    W_f = pd.Series(wn, index=q.index).groupby(q.pollster_key).sum()      # peso total de cada firma (no por encuesta)
    k_ef = 1.0 / float(np.sum(W_f.to_numpy() ** 2))                      # 1 ≤ k_ef ≤ k firmas
    edad_pond = float(np.sum(wn * (pd.Timestamp(cfg.dia_eleccion) - q.fin).dt.days.to_numpy(float))) - h
    sd_ef = float(np.sqrt(par['tau'] ** 2 + par['s'] ** 2 / max(k_ef, 1) + m.sigma_dia_pp ** 2 * max(edad_pond, 0)))
    esc.append(fila(sim(mu, Dist(sd_ef, par['nu'])), f'Incertidumbre con k efectivo {k_ef:.1f} (no {k} firmas) y deriva por '
                                                      f'antigüedad ponderada ({max(edad_pond, 0):.0f} días)'))
    esc.append(fila(sim(mu, dist, 0.1, 0.0), 'Sin terceros'))
    esc.append(fila(sim(mu, Dist(float(np.sqrt(sd ** 2 - var_deriva)), par['nu'])), 'Sin deriva por encuestas viejas'))
    esc.append(fila(sim(mu, Dist(float(np.sqrt(sd ** 2 - var_deriva + 3 * var_deriva)), par['nu'])),
                    f'Deriva al doble (σ_d = 0.50 pp por √día, {edad_extra} días)'))
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
    lado = q.pollster.map(lado_partidista).where(q.get('partidista', True), None)   # firma de un partido ≠ patrocinio
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
    lado_p = p.pollster.map(lado_partidista).where(p.get('partidista', True), None)
    if lado_p.notna().any():
        con_encuestas(p[lado_p.isna()], 'Sin encuestas de patrocinio partidista')
    # revisión de Illinois: el histórico de FiveThirtyEight fecha cada encuesta en el PUNTO MEDIO del campo; producción
    # usa el fin. Con campos largos (ActiVote 2–22 oct) la diferencia importa: escenario con las fechas del punto medio
    ini = pd.to_datetime(p['inicio']) if 'inicio' in p else p.fin
    medio = ini.fillna(p.fin) + (p.fin - ini.fillna(p.fin)) / 2
    p_med = p.assign(fin=medio.dt.normalize(), days=(pd.Timestamp(cfg.dia_eleccion) - medio.dt.normalize()).dt.days)
    con_encuestas(p_med, 'Fechas por el punto medio del campo (como el histórico de FiveThirtyEight)')
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
        esc.append({'escenario': 'Polymarket por rangos de margen (normal ajustada a los rangos D/R: condicional a que gane '
                                 'un partido principal; P de los contratos, con el independiente en el denominador)', 'P_D': rg['P_D'], 'margen': rg['margen_media'], 'sd': rg['margen_sd']})

    tabla = q.assign(efecto_casa=q.pollster_key.map(house).fillna(0.0), peso=w.values,
                     patrocinador=lado.fillna('—'), efecto_partidista=lado.map(ep).fillna(0.0))
    tabla['margen_corregido'] = tabla.margin_poll - tabla.efecto_casa
    p = p.assign(en_ventana=p.index.isin(q.index),
                 efecto_casa=p.pollster_key.map(house).fillna(0.0))
    p['margen_corregido'] = p.margin_poll - p.efecto_casa
    return {'final': final, 'escenarios': pd.DataFrame(esc), 'ventana': tabla, 'encuestas': p, 'mu': mu,
            'mu_final': mu + desplaz, 'sd': sd, 'nu': par['nu'], 'sim': sim_final}
