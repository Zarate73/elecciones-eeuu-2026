"""Backtest de modelos de pronóstico para Georgia (y generalización nacional).

Objetivo: margen D−R (pp del voto total) en contiendas estatales Gobernador/Senado/Presidente.
Validación: leave-one-year-out (LOYO). Todo parámetro (efectos de casa, sigma, pesos de mezcla)
se estima SIN el año evaluado. Los errores dentro de un año están correlacionados, por eso
la unidad de validación es el año y no la contienda.

Datos: FiveThirtyEight pollster-ratings 2023 raw-polls (encuestas de los últimos 21 días,
1998–2022) + encuestas GA Presidente 2024 (Wikipedia) + resultado certificado 2024.

Ejecutar: python backtest_georgia.py   -> escribe salida_backtest/
"""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
OUT = ROOT / 'salida_backtest'
OUT.mkdir(exist_ok=True)

# Margen presidencial nacional D−R (voto popular), para el 'lean' estatal
NAT_PRES = {1996: 8.5, 2000: 0.5, 2004: -2.4, 2008: 7.3, 2012: 3.9, 2016: 2.1, 2020: 4.5, 2024: -1.5}
GA_PRES2024 = {'cand1_actual': 48.53, 'cand2_actual': 50.73}
HOUSE_K = 8.0        # contracción de efectos de casa (pseudo-encuestas en 0)
HALF_LIFE = 14.0     # vida media (días) para el promedio ponderado


# ----------------------------------------------------------------------------- datos
def cargar_encuestas() -> pd.DataFrame:
    d = pd.read_csv(DATA / 'fte_raw_polls_2023.csv')
    d = d[d.type_simple.isin(['Gov-G', 'Sen-G', 'Pres-G']) & (d.location != 'US')]
    d = d[(d.cand1_party == 'DEM') & (d.cand2_party == 'REP')]
    d = d[(d.cand1_actual + d.cand2_actual) >= 85]          # excluye 'jungle' y multicandidato
    d = d.copy()
    d['runoff'] = d.race.str.contains('-GR_|-GSR_', regex=True)
    d['polldate'] = pd.to_datetime(d.polldate)
    d['electiondate'] = pd.to_datetime(d.electiondate)
    keep = ['race', 'year', 'location', 'type_simple', 'runoff', 'pollster', 'partisan', 'polldate',
            'electiondate', 'samplesize', 'cand1_pct', 'cand2_pct', 'cand3_pct', 'cand1_actual', 'cand2_actual']
    d = d[keep]
    g = pd.read_csv(DATA / 'ga_pres2024_polls.csv')
    g = g.assign(race='2024_Pres-G_GA', year=2024, location='GA', type_simple='Pres-G', runoff=False,
                 polldate=pd.to_datetime(g.polldate), electiondate=pd.Timestamp('2024-11-05'),
                 cand3_pct=np.nan, **GA_PRES2024)
    g['partisan'] = g.partisan.where(g.partisan.notna(), np.nan)
    d = pd.concat([d, g[keep]], ignore_index=True)
    d['days'] = (d.electiondate - d.polldate).dt.days
    d['margin_poll'] = d.cand1_pct - d.cand2_pct
    d['margin_actual'] = d.cand1_actual - d.cand2_actual
    d['major_poll'] = d.cand1_pct + d.cand2_pct
    d['n'] = pd.to_numeric(d.samplesize, errors='coerce').fillna(600).clip(100, 3000)
    d['pollster_key'] = d.pollster.str.lower().str.replace(r'[^a-z]', '', regex=True).str[:14]
    d['partisan'] = d.partisan.astype(str).str[:1].replace({'n': '', 'N': ''})
    return d


def lean_estatal(d: pd.DataFrame) -> dict:
    """Lean = margen presidencial estatal − nacional de la elección presidencial PREVIA."""
    p = d[d.type_simple == 'Pres-G'].groupby(['location', 'year']).margin_actual.first()
    out = {}
    for (loc, yr) in d[['location', 'year']].drop_duplicates().itertuples(index=False):
        prev = max([y for y in NAT_PRES if y < yr], default=None)
        if prev is not None and (loc, prev) in p.index:
            out[(loc, yr)] = float(p[(loc, prev)] - NAT_PRES[prev])
    return out


# ----------------------------------------------------------------------- componentes
def efectos_casa(train: pd.DataFrame) -> tuple[dict, dict]:
    """Efecto relativo: desviación de cada encuesta frente a la media de SU contienda.
    Se contrae hacia 0 con HOUSE_K. Devuelve efectos por encuestadora y por patrocinio partidista."""
    t = train.copy()
    t['dev'] = t.margin_poll - t.groupby('race').margin_poll.transform('mean')
    t['nr'] = t.groupby('race').margin_poll.transform('size')
    t = t[t.nr >= 3]
    hp = t.groupby('pollster_key').dev.agg(['sum', 'size'])
    house = (hp['sum'] / (hp['size'] + HOUSE_K)).to_dict()
    ps = t.groupby('partisan').dev.agg(['sum', 'size'])
    part = (ps['sum'] / (ps['size'] + HOUSE_K)).to_dict()
    return house, part


def promedio(polls: pd.DataFrame, metodo: str, house=None, part=None, horizonte: int = 0) -> tuple[float, int]:
    p = polls[polls.days >= horizonte]
    if p.empty:
        return np.nan, 0
    m = p.margin_poll.to_numpy(float)
    if metodo in ('casa', 'casa_part'):
        adj = p.pollster_key.map(house or {}).fillna(0).to_numpy(float)
        if metodo == 'casa_part':
            # patrocinio partidista solo si la encuestadora no tiene efecto propio estimado
            sin = ~p.pollster_key.isin((house or {}).keys()).to_numpy()
            adj = adj + sin * p.partisan.map(part or {}).fillna(0).to_numpy(float)
        m = m - adj
    if metodo == 'simple':
        return float(m.mean()), int(p.pollster_key.nunique())
    dt = (p.days - p.days.min()).to_numpy(float)
    w = np.exp(-np.log(2) * dt / HALF_LIFE) * np.sqrt(p.n.to_numpy(float))
    w = w / p.pollster_key.map(p.pollster_key.value_counts()).to_numpy(float)   # cada firma pesa ~1
    return float(np.sum(w * m) / np.sum(w)), int(p.pollster_key.nunique())


def construir_contiendas(d: pd.DataFrame, horizonte: int, metodo: str, casa_por_anio: dict) -> pd.DataFrame:
    rows = []
    for race, p in d.groupby('race'):
        yr = int(p.year.iloc[0])
        h, pt = casa_por_anio.get(yr, ({}, {}))
        mu, k = promedio(p, metodo, h, pt, horizonte)
        if np.isnan(mu):
            continue
        rows.append({'race': race, 'year': yr, 'location': p.location.iloc[0], 'tipo': p.type_simple.iloc[0],
                     'runoff': bool(p.runoff.iloc[0]), 'poll': mu, 'k': k, 'actual': float(p.margin_actual.iloc[0]),
                     'major_poll': float(p[p.days >= horizonte].major_poll.mean())})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- sigma
def ajustar_sigma(err: np.ndarray, k: np.ndarray) -> tuple[float, float]:
    """MLE de var = tau² + s²/k (error común + ruido que se promedia con k encuestadoras)."""
    best = None
    for tau in np.linspace(1.0, 8.0, 71):
        for s in np.linspace(0.0, 12.0, 61):
            v = tau ** 2 + s ** 2 / np.maximum(k, 1)
            ll = -0.5 * np.sum(np.log(v) + err ** 2 / v)
            if best is None or ll > best[0]:
                best = (ll, tau, s)
    return best[1], best[2]


def crps_normal(y, mu, sd):
    z = (y - mu) / sd
    return sd * (z * (2 * norm.cdf(z) - 1) + 2 * norm.pdf(z) - 1 / np.sqrt(np.pi))


def metricas(df: pd.DataFrame, col_mu='mu', col_sd='sd') -> dict:
    e = df[col_mu] - df.actual
    sd = df[col_sd]
    p = norm.cdf(df[col_mu] / sd)
    win = (df.actual > 0).astype(float)
    return {'n': len(df), 'sesgo': e.mean(), 'MAE': e.abs().mean(), 'RMSE': np.sqrt((e ** 2).mean()),
            'CRPS': crps_normal(df.actual, df[col_mu], sd).mean(),
            'LogScore': (-norm.logpdf(df.actual, df[col_mu], sd)).mean(),
            'Cob80': (np.abs(e) <= 1.2816 * sd).mean(), 'Cob95': (np.abs(e) <= 1.96 * sd).mean(),
            'Brier': ((p - win) ** 2).mean(), 'sd_media': sd.mean()}


# ---------------------------------------------------------------------------- main
def main(horizonte: int = 0):
    d = cargar_encuestas()
    years = sorted(d.year.unique())
    # efectos de casa LOYO (entrenados solo con otros años)
    casa = {y: efectos_casa(d[d.year != y]) for y in years}
    leans = lean_estatal(d)
    bases = {m: construir_contiendas(d, horizonte, m, casa) for m in ['simple', 'pond', 'casa', 'casa_part']}
    races = bases['simple'][['race']].merge(bases['casa_part'][['race']])
    for m in bases:
        bases[m] = bases[m][bases[m].race.isin(races.race)].reset_index(drop=True)

    resultados = []
    preds_all = []
    for m, b in bases.items():
        b = b.copy()
        b['lean'] = [leans.get((l, y), np.nan) for l, y in zip(b.location, b.year)]
        # entorno nacional EN EL AÑO a partir de encuestas de OTRAS contiendas (sin resultados)
        b['env'] = np.nan
        for i, r in b.iterrows():
            o = b[(b.year == r.year) & (b.race != r.race) & b.lean.notna() & ~b.runoff]
            if len(o) >= 5:
                b.at[i, 'env'] = float((o.poll - o.lean).median())
        b['fund'] = b.lean + b.env
        for y in years:
            te = b.year == y
            tr = ~te
            if te.sum() == 0:
                continue
            etr = (b.poll - b.actual)[tr].to_numpy()
            tau, s = ajustar_sigma(etr, b.k[tr].to_numpy())
            sd_emp = np.sqrt(tau ** 2 + s ** 2 / np.maximum(b.k[te], 1))
            # sesgo histórico (media de errores de años previos, sólo pasado)
            past = b[b.year < y]
            bias_hist = float((past.poll - past.actual).mean()) if len(past) > 20 else 0.0
            # mezcla con fundamentales: actual - poll = beta*(fund - poll)
            f = b[tr & b.fund.notna()]
            beta = float(np.clip(np.sum((f.fund - f.poll) * (f.actual - f.poll)) / np.sum((f.fund - f.poll) ** 2), 0, 1))
            # sesgo específico de estado (contracción empírica bayesiana): media de errores del estado
            # en años de entrenamiento, contraída según varianza entre estados estimada en entrenamiento.
            trd = b[tr].assign(e=b.poll - b.actual)
            st = trd.groupby('location').e.agg(['mean', 'var', 'size'])
            st = st[st['size'] >= 3]
            noise = float(np.nanmean(st['var'] / st['size']))
            var_state = max(float(st['mean'].var()) - noise, 0.0)
            def bias_estado(loc):
                if loc not in st.index or var_state == 0:
                    return 0.0
                r_ = st.loc[loc]
                w_ = var_state / (var_state + r_['var'] / r_['size'])
                return float(w_ * r_['mean'])
            t = b[te].copy()
            bias_st = np.array([bias_estado(l) for l in t.location])
            bias_ga = bias_estado('GA')
            # sigma estilo V9: varianza muestral (~12/k para n≈800) + piso común de 2pp
            sd_v9 = np.sqrt(12.0 / np.maximum(t.k, 1) + 2.0 ** 2)
            # sigma propia para la mezcla con fundamentales (residuos de entrenamiento)
            ftr = f.actual - (f.poll + beta * (f.fund - f.poll))
            tau_f, s_f = ajustar_sigma(ftr.to_numpy(), f.k.to_numpy())
            sd_f = np.sqrt(tau_f ** 2 + s_f ** 2 / np.maximum(t.k, 1))
            fundmu = np.where(t.fund.notna(), t.poll + beta * (t.fund - t.poll), t.poll)
            sd_fund = np.where(t.fund.notna(), sd_f, sd_emp)
            variants = {
                f'{m}|sd_V9(2pp)': (t.poll, sd_v9),
                f'{m}|sd_empirica': (t.poll, sd_emp),
                f'{m}|sesgo_hist+sd_emp': (t.poll - bias_hist, sd_emp),
                f'{m}|fundamentales+sd_emp': (pd.Series(fundmu, index=t.index), sd_fund),
                f'{m}|sesgo_estado+sd_emp': (t.poll - bias_st, sd_emp),
            }
            for name, (mu, sd) in variants.items():
                tt = t.assign(mu=np.asarray(mu, float), sd=np.asarray(sd, float), modelo=name,
                              tau=tau, s=s, beta=beta, bias_hist=bias_hist, bias_ga=bias_ga)
                preds_all.append(tt)
    P = pd.concat(preds_all, ignore_index=True)
    P['agregado'] = P.modelo.str.split('|').str[0]
    # recalibración de 'fundamentales': la sd se escala por año entrenado; simplificación documentada
    for scope, sel in [('Nacional_todas', P.index == P.index), ('Nacional_Gob', P.tipo == 'Gov-G'),
                       ('GA_todas', P.location == 'GA'), ('GA_generales', (P.location == 'GA') & ~P.runoff),
                       ('GA_2014+', (P.location == 'GA') & (P.year >= 2014))]:
        for mod, g in P[sel].groupby('modelo'):
            r = metricas(g)
            r.update({'ambito': scope, 'modelo': mod})
            resultados.append(r)
    R = pd.DataFrame(resultados)
    R = R[['ambito', 'modelo', 'n', 'sesgo', 'MAE', 'RMSE', 'CRPS', 'LogScore', 'Cob80', 'Cob95', 'Brier', 'sd_media']]
    return d, bases, P, R


if __name__ == '__main__':
    pd.set_option('display.width', 220)
    for h in [0, 15]:
        d, bases, P, R = main(h)
        R.to_csv(OUT / f'metricas_h{h}.csv', index=False)
        P.to_csv(OUT / f'predicciones_h{h}.csv', index=False)
        print(f'\n===== HORIZONTE: encuestas con >= {h} días antes =====')
        for amb in R.ambito.unique():
            print('\n--', amb)
            print(R[R.ambito == amb].sort_values('CRPS').drop(columns='ambito').round(3).to_string(index=False))
