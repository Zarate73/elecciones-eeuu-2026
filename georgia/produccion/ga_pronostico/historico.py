"""Histórico para calibrar: FiveThirtyEight raw-polls (descarga en vivo desde GitHub) + GA Presidente 2024.

Calibra al horizonte del corte (días a la elección, tope 21):
  - efectos de casa por encuestadora (contraídos), con todo el histórico;
  - errores fuera de muestra (casa estimada sin el año) -> tau, s de sigma(k) = sqrt(tau² + s²/k) y ν de la t;
  - sesgo del estado: media ponderada (vida media 4 años) contraída por bayes empírico.
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


def obtener_raw_polls(cfg) -> tuple[pd.DataFrame, str]:
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
    return pd.read_csv(ruta), estado


def preparar(raw: pd.DataFrame, cfg) -> pd.DataFrame:
    d = raw[raw.type_simple.isin(['Gov-G', 'Sen-G', 'Pres-G']) & (raw.location != 'US')]
    d = d[(d.cand1_party == 'DEM') & (d.cand2_party == 'REP') & ((d.cand1_actual + d.cand2_actual) >= 85)].copy()
    keep = ['race', 'year', 'location', 'type_simple', 'pollster', 'polldate', 'electiondate', 'samplesize',
            'cand1_pct', 'cand2_pct', 'cand1_actual', 'cand2_actual']
    d = d[keep].copy()
    d['polldate'] = pd.to_datetime(d.polldate, format='%m/%d/%Y')
    d['electiondate'] = pd.to_datetime(d.electiondate, format='%m/%d/%Y')
    g = pd.read_csv(cfg.dir_datos / 'ga_pres2024_polls.csv')
    g = g.assign(race='2024_Pres-G_GA', year=2024, location='GA', type_simple='Pres-G',
                 electiondate=pd.Timestamp('2024-11-05'), polldate=pd.to_datetime(g.polldate),
                 cand1_actual=48.53, cand2_actual=50.73)
    d = pd.concat([d, g[keep]], ignore_index=True)
    d['days'] = (d.electiondate - d.polldate).dt.days
    d['margin_poll'] = d.cand1_pct - d.cand2_pct
    d['margin_actual'] = d.cand1_actual - d.cand2_actual
    d['n'] = pd.to_numeric(d.samplesize, errors='coerce').fillna(600).clip(100, 3000)
    d['clave_538'] = d.pollster.str.lower().str.replace(r'[^a-z]', '', regex=True).str[:14]
    return d


def efectos_casa(train: pd.DataFrame, k: float) -> dict:
    t = train.copy()
    t['dev'] = t.margin_poll - t.groupby('race').margin_poll.transform('mean')
    t = t[t.groupby('race').margin_poll.transform('size') >= 3]
    hp = t.groupby('clave_538').dev.agg(['sum', 'size'])
    return (hp['sum'] / (hp['size'] + k)).to_dict()


def promedio(p: pd.DataFrame, house: dict, vida_media: float, fin_col='days') -> tuple[float, int]:
    """Margen ponderado corregido por casa. p: columnas margin_poll, n, clave_538, days (días a la elección)."""
    if p.empty:
        return np.nan, 0
    m = p.margin_poll.to_numpy(float) - p.clave_538.map(house).fillna(0).to_numpy(float)
    dt = (p[fin_col] - p[fin_col].min()).to_numpy(float)
    w = np.exp(-np.log(2) * dt / vida_media) * np.sqrt(p.n.to_numpy(float))
    w = w / p.clave_538.map(p.clave_538.value_counts()).to_numpy(float)
    return float(np.sum(w * m) / np.sum(w)), int(p.clave_538.nunique())


def ajustar_sigma(err, k) -> tuple[float, float]:
    taus = np.linspace(1.0, 8.0, 141)[:, None, None]
    ss = np.linspace(0.0, 12.0, 121)[None, :, None]
    v = taus ** 2 + ss ** 2 / np.maximum(np.asarray(k, float), 1)[None, None, :]
    ll = -0.5 * np.sum(np.log(v) + np.asarray(err, float)[None, None, :] ** 2 / v, axis=2)
    i, j = np.unravel_index(np.argmax(ll), ll.shape)
    return float(taus[i, 0, 0]), float(ss[0, j, 0])


def calibrar(cfg, estado: str = 'GA') -> dict:
    raw, est_fuente = obtener_raw_polls(cfg)
    m = cfg.modelo
    h = int(np.clip(cfg.dias_a_eleccion, 0, 21))
    firma = hashlib.md5(pd.util.hash_pandas_object(raw, index=False).values.tobytes()).hexdigest()[:10]
    clave = f'h{h}_k{m.contraccion_casa}_vm{m.vida_media_dias}_vs{m.vida_media_sesgo_anios}_{estado}_{firma}'
    cache = cfg.dir_cache / f'calibracion_{clave}.json'
    if cache.exists():
        par = json.loads(cache.read_text(encoding='utf-8'))
        par['estado_fuente'] = est_fuente
        return par
    d = preparar(raw, cfg)
    rows = []
    for y in sorted(d.year.unique()):
        house = efectos_casa(d[d.year != y], m.contraccion_casa)
        for race, p in d[d.year == y].groupby('race'):
            mu, k = promedio(p[p.days >= h], house, m.vida_media_dias)
            if not np.isnan(mu):
                rows.append({'race': race, 'year': int(y), 'location': p.location.iloc[0], 'k': k,
                             'e': mu - float(p.margin_actual.iloc[0])})
    b = pd.DataFrame(rows)
    tau, s = ajustar_sigma(b.e, b.k)
    z = b.e / np.sqrt(tau ** 2 + s ** 2 / np.maximum(b.k, 1))
    nus = np.linspace(2.5, 60, 576)
    nu = float(nus[int(np.argmax([np.sum(student_t.logpdf(z, v, scale=np.sqrt((v - 2) / v))) for v in nus]))])
    b['w'] = 0.5 ** ((cfg.dia_eleccion.year - b.year) / m.vida_media_sesgo_anios)
    st = b.groupby('location').apply(lambda g: pd.Series({
        'm': np.average(g.e, weights=g.w), 'neff': g.w.sum() ** 2 / (g.w ** 2).sum(),
        'v': g.e.var() if len(g) > 1 else np.nan}), include_groups=False)
    st = st[st.neff >= 1.5]
    var_est = max(float(st.m.var()) - float(np.nanmean(st.v / st.neff)), 0.0)
    r = st.loc[estado]
    contr = var_est / (var_est + r.v / r.neff) if var_est > 0 else 0.0
    par = {'horizonte_dias': h, 'horizonte_recortado': cfg.dias_a_eleccion > 21, 'tau': tau, 's': s, 'nu': nu,
           'n_contiendas': int(len(b)), 'sesgo_estado_bruto': float(r.m), 'contraccion_sesgo': float(contr),
           'sesgo_estado': float(contr * r.m), 'var_entre_estados': var_est,
           'efectos_casa': efectos_casa(d, m.contraccion_casa),
           'errores_estado': b[b.location == estado].drop(columns='w').to_dict('records')}
    cache.write_text(json.dumps(par, ensure_ascii=False), encoding='utf-8')
    par['estado_fuente'] = est_fuente
    log.info('Calibración h=%d: tau=%.2f s=%.2f nu=%.1f sesgo_GA=%+.2f (%d contiendas)', h, tau, s, nu,
             par['sesgo_estado'], len(b))
    return par
