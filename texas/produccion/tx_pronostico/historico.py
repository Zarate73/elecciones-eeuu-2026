"""Histórico para calibrar: FiveThirtyEight raw-polls (descarga en vivo desde GitHub) + 2024: GA Pres, AZ Pres/Sen y
contiendas con encuestas finales de Wikipedia (data/encuestas_2024_wiki.csv; sin Axis Research, oct-2024, que era una
encuesta del distrito 2 de Maine y no estatal).

Calibra al horizonte del corte (días a la elección, tope 21), leave-one-year-out:
  - efectos de casa por encuestadora (contraídos, k = 8);
  - errores fuera de muestra -> τ, s de σ(k) = √(τ² + s²/k) y ν de la t de Student;
  - terceros: real = a + c·(otros en las encuestas que los REPORTAN); si ninguna los reporta, media histórica de las
    contiendas sin reporte (no reportado ≠ 0 %; revisión del 22-oct). Cada régimen con su desviación residual;
  - sesgo estatal del estado: regla «todas» (contiendas del estado; la de Texas) o «k2» (sin contiendas de una sola
    encuestadora; la de Maine). El sesgo con solo contiendas de gobernador se calcula como escenario.
"""
from __future__ import annotations

import hashlib
import json
import logging

import numpy as np
import pandas as pd
from scipy.stats import t as student_t

from .red import get_text

log = logging.getLogger(__name__)
AZ24 = {'2024_Pres-G_AZ': (46.69, 52.22), '2024_Sen-G_AZ': (50.06, 47.65)}
KEEP = ['race', 'year', 'location', 'type_simple', 'pollster', 'partisan', 'polldate', 'electiondate', 'samplesize',
        'cand1_pct', 'cand2_pct', 'cand3_pct', 'cand1_actual', 'cand2_actual']


def obtener_raw_polls(cfg) -> tuple[pd.DataFrame, str, str]:
    """(datos, estado, firma del contenido). En vivo desde GitHub; si falla, caché; si no, copia del paquete."""
    ruta = cfg.dir_cache / 'fte_raw_polls_2023.csv'
    try:
        txt = get_text(cfg.fuentes.fte_raw_polls_url, offline=cfg.offline, timeout=cfg.fuentes.timeout_http_s)
        if 'race_id' not in txt[:500]:
            raise ValueError('formato inesperado')
        ruta.write_text(txt, encoding='utf-8')
        estado = 'en_vivo'
    except Exception as exc:
        err = f'{type(exc).__name__}: {str(exc)[:120]}'
        if ruta.exists():
            estado = f'cache ({err})'
        else:
            ruta = cfg.dir_datos / 'fte_raw_polls_2023.csv'      # copia de respaldo del paquete
            estado = f'paquete ({err})'
    b = ruta.read_bytes()
    return pd.read_csv(ruta, low_memory=False), estado, hashlib.md5(b).hexdigest()[:10]


def preparar(raw: pd.DataFrame, cfg) -> pd.DataFrame:
    d = raw[raw.type_simple.isin(['Gov-G', 'Sen-G', 'Pres-G']) & (raw.location != 'US')]
    d = d[(d.cand1_party == 'DEM') & (d.cand2_party == 'REP') & ((d.cand1_actual + d.cand2_actual) >= 85)].copy()
    d = d.reindex(columns=KEEP)
    d['polldate'] = pd.to_datetime(d.polldate, format='%m/%d/%Y')
    d['electiondate'] = pd.to_datetime(d.electiondate, format='%m/%d/%Y')
    g = pd.read_csv(cfg.dir_datos / 'ga_pres2024_polls.csv')
    g = g.assign(partisan=np.nan, race='2024_Pres-G_GA', year=2024, location='GA', type_simple='Pres-G',
                 cand3_pct=np.nan, electiondate=pd.Timestamp('2024-11-05'), polldate=pd.to_datetime(g.polldate),
                 cand1_actual=48.53, cand2_actual=50.73)
    a = pd.read_csv(cfg.dir_datos / 'az2024_encuestas_finales.csv', parse_dates=['polldate', 'electiondate'])
    a['rk'] = a['pop'].map({'LV': 0, 'RV': 1, 'A': 2}).fillna(3)
    a = a.sort_values('rk').drop_duplicates(['race', 'pollster', 'polldate'])
    # capturas de Wikipedia 2024: el analizador anterior escribía 0 para «—» (no reportado) → se trata como faltante
    a = a.assign(samplesize=a.n, cand1_pct=a.D, cand2_pct=a.R, cand3_pct=a.otros.where(a.otros > 0),
                 cand1_actual=a.race.map(lambda r: AZ24[r][0]), cand2_actual=a.race.map(lambda r: AZ24[r][1]))
    w = pd.read_csv(cfg.dir_datos / 'encuestas_2024_wiki.csv', parse_dates=['polldate', 'electiondate'])
    w['rk'] = w['pop'].map({'LV': 0, 'RV': 1, 'A': 2}).fillna(3)
    w = w.sort_values('rk').drop_duplicates(['race', 'pollster', 'polldate'])
    w = w.assign(samplesize=w.n, cand1_pct=w.D, cand2_pct=w.R, cand3_pct=w.otros.where(w.otros > 0))
    d = pd.concat([d, g.reindex(columns=KEEP), a.reindex(columns=KEEP), w.reindex(columns=KEEP)], ignore_index=True)
    d['days'] = (d.electiondate - d.polldate).dt.days
    d['margin_poll'] = d.cand1_pct - d.cand2_pct
    d['margin_actual'] = d.cand1_actual - d.cand2_actual
    d['n'] = pd.to_numeric(d.samplesize, errors='coerce').fillna(600).clip(100, 3000)
    d['pollster_key'] = d.pollster.str.lower().str.replace(r'[^a-z]', '', regex=True).str[:14]
    d['cand3_pct'] = pd.to_numeric(d.cand3_pct, errors='coerce')        # NaN = la encuesta no reporta terceros
    d['otros_real'] = (100 - d.cand1_actual - d.cand2_actual).clip(lower=0)
    return d


def efectos_casa(train: pd.DataFrame, k: float) -> dict:
    t = train.copy()
    t['dev'] = t.margin_poll - t.groupby('race').margin_poll.transform('mean')
    t = t[t.groupby('race').margin_poll.transform('size') >= 3]
    hp = t.groupby('pollster_key').dev.agg(['sum', 'size'])
    return (hp['sum'] / (hp['size'] + k)).to_dict()


def efectos_partidistas(d: pd.DataFrame, k: float) -> dict:
    """Desviación media (contraída) de encuestas con patrocinador D o R frente al promedio de su contienda.
    Solo escenario: en el backtest no mejora el CRPS nacional (3.579 vs 3.545 sin efectos de casa)."""
    t = d.copy()
    t['dev'] = t.margin_poll - t.groupby('race').margin_poll.transform('mean')
    t = t[(t.groupby('race').margin_poll.transform('size') >= 3) & t.partisan.isin(['D', 'R'])]
    g = t.groupby('partisan').dev.agg(['sum', 'size'])
    return (g['sum'] / (g['size'] + k)).to_dict()


def promedio(p: pd.DataFrame, house: dict, vida_media: float) -> tuple[float, float, int, pd.Series]:
    """(margen corregido por casa, % otros, k encuestadoras, pesos).
    Peso = 2^(−Δdías/vida_media) · √n / (encuestas de la misma firma en la ventana).
    % otros = promedio con esos pesos SOLO entre las encuestas que reportan terceros; NaN si ninguna los reporta."""
    m = p.margin_poll.to_numpy(float) - p.pollster_key.map(house).fillna(0).to_numpy(float)
    dt = (p.days - p.days.min()).to_numpy(float)
    w = np.exp(-np.log(2) * dt / vida_media) * np.sqrt(p.n.to_numpy(float))
    w = w / p.pollster_key.map(p.pollster_key.value_counts()).to_numpy(float)
    w = w / w.sum()
    o = p.otros.to_numpy(float)
    rep = np.isfinite(o)
    otros = float(np.average(o[rep], weights=w[rep])) if rep.any() and w[rep].sum() > 0 else float('nan')
    return float(w @ m), otros, int(p.pollster_key.nunique()), pd.Series(w, p.index)


def ajustar_sigma(err, k) -> tuple[float, float]:
    taus = np.linspace(1.0, 8.0, 141)[:, None, None]
    ss = np.linspace(0.0, 12.0, 121)[None, :, None]
    v = taus ** 2 + ss ** 2 / np.maximum(np.asarray(k, float), 1)[None, None, :]
    ll = -0.5 * np.sum(np.log(v) + np.asarray(err, float)[None, None, :] ** 2 / v, axis=2)
    i, j = np.unravel_index(np.argmax(ll), ll.shape)
    return float(taus[i, 0, 0]), float(ss[0, j, 0])


def calibrar(cfg, h: int) -> dict:
    m = cfg.modelo
    raw, estado, firma = obtener_raw_polls(cfg)
    # la caché también depende de los históricos 2024 del paquete (si se corrigen, se recalibra)
    firma += hashlib.md5(b''.join((cfg.dir_datos / x).read_bytes() for x in
                                  ('ga_pres2024_polls.csv', 'az2024_encuestas_finales.csv', 'encuestas_2024_wiki.csv'))).hexdigest()[:6]
    regla = str(getattr(m, 'sesgo_regla', 'todas') or 'todas')
    cache = cfg.dir_cache / f'calibracion_v14_h{h}_k{m.contraccion_casa}_vm{m.vida_media_dias}_s{regla}_{firma}.json'
    if cache.exists():
        par = json.loads(cache.read_text(encoding='utf-8'))
        par['estado_fuente'] = estado
        return par
    d = preparar(raw, cfg)
    filas = []
    for y in sorted(d.year.unique()):
        house = efectos_casa(d[d.year != y], m.contraccion_casa)
        for race, p in d[d.year == y].groupby('race'):
            q = p[(p.days >= h) & (p.days <= m.ventana_dias_eleccion)].rename(columns={'cand3_pct': 'otros'})   # = ventana de producción
            if q.empty:
                continue
            mu, o, k, _ = promedio(q, house, m.vida_media_dias)
            filas.append({'race': race, 'year': int(y), 'location': p.location.iloc[0], 'tipo': p.type_simple.iloc[0], 'k': k, 'otros_enc': o,
                          'otros_real': float(p.otros_real.iloc[0]), 'e': mu - float(p.margin_actual.iloc[0])})
    b = pd.DataFrame(filas)
    tau, s = ajustar_sigma(b.e, b.k)
    z = b.e / np.sqrt(tau ** 2 + s ** 2 / np.maximum(b.k, 1))
    nus = np.linspace(2.5, 60, 576)
    nu = float(nus[int(np.argmax([np.sum(student_t.logpdf(z, v, scale=np.sqrt((v - 2) / v))) for v in nus]))])
    con = b[b.otros_enc.notna()]
    A = np.c_[np.ones(len(con)), con.otros_enc]
    coef = np.linalg.lstsq(A, con.otros_real, rcond=None)[0]
    sd_t = float(np.std(con.otros_real - A @ coef, ddof=2))
    sin = b[b.otros_enc.isna()].otros_real

    def sesgo_estado(bb: pd.DataFrame, clave_estado: str | None = None) -> tuple[float, float]:
        """(bruto, contracción) del sesgo del estado: vida media de 4 años y Bayes empírico entre estados."""
        bb = bb.assign(w=0.5 ** ((cfg.dia_eleccion.year - bb.year) / 4.0))
        st = bb.groupby('location').apply(lambda g: pd.Series({
            'm': np.average(g.e, weights=g.w), 'neff': g.w.sum() ** 2 / (g.w ** 2).sum(),
            'v': g.e.var() if len(g) > 1 else np.nan}), include_groups=False)
        st = st[st.neff >= 1.5]
        vs = max(float(st.m.var()) - float(np.nanmean(st.v / st.neff)), 0.0)
        r_ = st.loc[clave_estado or cfg.eleccion.abrev]
        return float(r_.m), (vs / (vs + r_.v / r_.neff) if vs > 0 else 0.0)

    est = cfg.eleccion.abrev
    bruto_t, contr_t = sesgo_estado(b)                  # todas las contiendas del estado
    bruto_k2, contr_k2 = sesgo_estado(b[b.k >= 2])     # sin contiendas de una sola encuestadora
    # por cargo (solo contiendas de gobernador del estado): escenario. En el cronológico de Texas gana un poco
    # (2.230 vs 2.306, P = 0.82, n = 16) pero a nivel nacional pierde con claridad (3.259 vs 3.132, P = 0.004)
    try:
        bruto_g, contr_g = sesgo_estado(b.assign(location=b.location + '_' + b.tipo), f'{est}_Gov-G')
    except KeyError:
        bruto_g, contr_g = np.nan, np.nan
    # regla «todas» en Texas (cronológico: 2.306 vs 2.562 con k2, P = 0.07); «k2» en Maine; la otra queda de escenario
    bruto, contr = (bruto_k2, contr_k2) if regla == 'k2' else (bruto_t, contr_t)
    par = {'horizonte_dias': h, 'tau': tau, 's': s, 'nu': nu, 'n_contiendas': len(b),
           'terceros_a': float(coef[0]), 'terceros_c': float(coef[1]), 'terceros_sd': sd_t,
           'terceros_sin_reporte': float(sin.mean()), 'terceros_sin_reporte_sd': float(sin.std(ddof=1)),
           'n_con_reporte': len(con), 'n_sin_reporte': len(sin),
           'sesgo_bruto': bruto, 'sesgo_contraido': float(contr * bruto), 'contraccion': float(contr),
           'sesgo_regla': regla,
           'sesgo_bruto_k2': bruto_k2, 'sesgo_contraido_k2': float(contr_k2 * bruto_k2),
           'sesgo_bruto_todas': bruto_t, 'sesgo_contraido_todas': float(contr_t * bruto_t),
           'sesgo_bruto_gob': bruto_g, 'sesgo_contraido_gob': float(contr_g * bruto_g),
           'efectos_casa': efectos_casa(d, m.contraccion_casa),
           'efectos_casa_k4': efectos_casa(d, 4.0), 'efectos_casa_k16': efectos_casa(d, 16.0),   # sensibilidad
           'efectos_partidistas': efectos_partidistas(d, m.contraccion_casa),
           'errores_estado': b[b.location == est].round(3).to_dict('records')}
    cache.write_text(json.dumps(par, ensure_ascii=False), encoding='utf-8')
    par['estado_fuente'] = estado
    log.info('Calibración h=%d: τ=%.2f s=%.2f ν=%.1f · terceros %.2f + %.2f·enc · sesgo %s %+.2f (bruto %+.2f) · %d contiendas',
             h, tau, s, nu, coef[0], coef[1], est, contr * bruto, bruto, len(b))
    return par
