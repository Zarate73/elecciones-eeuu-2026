"""¿Cuánto deben pesar los mercados? Estimación por máxima verosimilitud con contiendas resueltas de 2024.

Datos (rama diagnostico-mercados, procesados en data/mercados_2024/):
  - Kalshi: velas diarias de PRESPARTY{ST}-24, SENATE{ST}-24, GOVPARTY{ST}-24 (punto medio bid/ask o cierre).
  - Polymarket: precio diario del mercado «Will a Democrat win…» (y el republicano para normalizar).
  - Wikipedia 2024: encuestas de cada contienda y resultado oficial.
Modelo de encuestas = producción de Arizona (V11 sin sesgo estatal): efectos de casa de FiveThirtyEight (≤ 2022),
√n, vida media 14 d, 1/firma; σ = √(τ² + s²/k + 0.25²·días extra) con τ, s, ν calibrados a h = 13; t de Student.
Horizonte: 13 días antes de la elección (23-oct-2024), igual que el pronóstico de Arizona del 21-oct-2026.
Mezcla: P_w = logit⁻¹((1−w)·logit P_enc + w·logit P_mercado); margen desplazado: μ_w = esc·t⁻¹(P_w).
Se maximiza en w:
  (a) la verosimilitud del margen real bajo t(μ_w, esc, ν)   -> usa la información del margen
  (b) el log score del ganador (log P_w del que ganó)       -> solo usa quién ganó
IC: razón de verosimilitud (caída de 1.92) y bootstrap por contienda. Advertencia: un solo año (2024), con error de
encuestas común a todos los estados; el bootstrap por contienda no captura esa correlación.
"""
from __future__ import annotations

import json
import re
import sys
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit
from scipy.stats import t as student_t

BASE = Path(__file__).resolve().parent
PROD = BASE.parent / 'produccion'
sys.path.insert(0, str(PROD))
from az_pronostico import encuestas_web as W          # noqa: E402
from az_pronostico.config import cargar_config         # noqa: E402
from az_pronostico.historico import calibrar, efectos_casa, obtener_raw_polls, preparar, promedio  # noqa: E402

DATOS = BASE / 'data' / 'mercados_2024'
SAL = BASE / 'salida'
ELECCION = pd.Timestamp('2024-11-05')
H = 13
CORTE = ELECCION - pd.Timedelta(days=H)
NOMBRES = {'AZ': 'Arizona', 'GA': 'Georgia', 'MI': 'Michigan', 'NV': 'Nevada', 'NC': 'North_Carolina',
           'PA': 'Pennsylvania', 'WI': 'Wisconsin', 'FL': 'Florida', 'TX': 'Texas', 'OH': 'Ohio', 'MN': 'Minnesota',
           'NH': 'New_Hampshire', 'VA': 'Virginia', 'IA': 'Iowa', 'NM': 'New_Mexico', 'ME': 'Maine', 'CO': 'Colorado',
           'NY': 'New_York', 'NJ': 'New_Jersey', 'MO': 'Missouri', 'MT': 'Montana', 'SC': 'South_Carolina',
           'MD': 'Maryland', 'WA': 'Washington', 'IN': 'Indiana'}
# contienda: (página de Wikipedia, candidato D, candidato R, evento Kalshi, slug de Polymarket)
SEN = {'AZ': ('Gallego', 'Lake'), 'MI': ('Slotkin', 'Rogers'), 'NV': ('Rosen', 'Brown'), 'PA': ('Casey', 'McCormick'),
       'WI': ('Baldwin', 'Hovde'), 'OH': ('Brown', 'Moreno'), 'MT': ('Tester', 'Sheehy'), 'TX': ('Allred', 'Cruz'),
       'FL': ('Mucarsel', 'Scott'), 'MD': ('Alsobrooks', 'Hogan'), 'MN': ('Klobuchar', 'White'),
       'NM': ('Heinrich', 'Domenici'), 'VA': ('Kaine', 'Cao'), 'NJ': ('Kim', 'Bashaw'), 'NY': ('Gillibrand', 'Sapraicone'),
       'MO': ('Kunce', 'Hawley'), 'WA': ('Cantwell', 'Garcia')}
GOB = {'NC': ('Stein', 'Robinson'), 'NH': ('Craig', 'Ayotte'), 'WA': ('Ferguson', 'Reichert'),
       'IN': ('McCormick', 'Braun'), 'MO': ('Quade', 'Kehoe'), 'MT': ('Busse', 'Gianforte')}
PRES = ['AZ', 'GA', 'MI', 'NV', 'NC', 'PA', 'WI', 'FL', 'TX', 'OH', 'MN', 'NH', 'VA', 'IA', 'NM', 'ME', 'CO', 'NY',
        'NJ', 'MO', 'MT', 'SC']


def contiendas() -> list[dict]:
    out = []
    for s in PRES:
        out.append({'id': f'Pres-{s}', 'cargo': 'Pres', 'estado': s, 'd': 'Harris', 'r': 'Trump',
                    'wiki': f'2024_United_States_presidential_election_in_{NOMBRES[s]}', 'kalshi': f'PRESPARTY{s}-24',
                    'poly': f"{NOMBRES[s].lower().replace('_', '-')}-presidential-election-winner"})
    for s, (d, r) in SEN.items():
        out.append({'id': f'Sen-{s}', 'cargo': 'Sen', 'estado': s, 'd': d, 'r': r,
                    'wiki': f'2024_United_States_Senate_election_in_{NOMBRES[s]}', 'kalshi': f'SENATE{s}-24',
                    'poly': f"{NOMBRES[s].lower().replace('_', '-')}-us-senate-election-winner"})
    for s, (d, r) in GOB.items():
        out.append({'id': f'Gob-{s}', 'cargo': 'Gob', 'estado': s, 'd': d, 'r': r,
                    'wiki': f'2024_{NOMBRES[s]}_gubernatorial_election', 'kalshi': f'GOVPARTY{s}-24',
                    'poly': f"{NOMBRES[s].lower().replace('_', '-')}-governor-election-winner"})
    return out


# ------------------------------------------------------------------------------------ lectura de crudos
def _limpio(h: str) -> str:
    return re.sub(r'(rowspan|colspan)="\s*(\d+)[^"]*"', r'\1="\2"', h)


def resultado(html: str, cd: str, cr: str):
    """% del candidato D y R en la tabla de resultados de la GENERAL (la de mayor D+R: descarta primarias top-two).
    Con voto de fusión (NY) suma las líneas del candidato; si hay fila de total no la cuenta doble."""
    def total(x: pd.Series) -> float:
        x = x.dropna()
        if len(x) > 1 and abs(x.max() - (x.sum() - x.max())) < 0.6:   # una fila es el total de las demás
            return float(x.max())
        return float(x.sum())
    mejor = None
    for t in pd.read_html(StringIO(_limpio(html))):
        cols = [' '.join(map(str, c)) if isinstance(c, tuple) else str(c) for c in t.columns]
        t.columns = cols
        cc = [c for c in cols if 'Candidate' in c]
        cp = [c for c in cols if c.split()[-1] == '%']
        if not (cc and cp and any('Votes' in c for c in cols)):
            continue
        txt = t[cc[0]].astype(str)
        num = pd.to_numeric(t[cp[0]].astype(str).str.replace('%', '').str.strip(), errors='coerce')
        a = num[txt.str.contains(cd, case=False, regex=False)]
        b = num[txt.str.contains(cr, case=False, regex=False)]
        if len(a.dropna()) and len(b.dropna()):
            par = (total(a), total(b))
            if par[0] + par[1] <= 100.5 and (mejor is None or sum(par) > sum(mejor)):
                mejor = par
    return mejor


def encuestas(html: str, cd: str, cr: str) -> pd.DataFrame:
    p = W.elegir_versiones(W.parse_tabla_wikipedia(_limpio(html), cd, cr, 2024))
    if p.empty:
        return p
    p['fin'] = pd.to_datetime(p.fin)
    return p[p.fin <= CORTE].copy()


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return np.nan


def kalshi_precio(crudo: Path, ticker: str) -> float:
    f = crudo / 'kalshi' / f'velas_{ticker}.json'
    if not f.exists():
        return np.nan
    filas = []
    for v in json.loads(f.read_text()).get('candlesticks', []):
        p, b, a = v.get('price', {}), v.get('yes_bid', {}), v.get('yes_ask', {})
        bid, ask = _f(b.get('close_dollars', b.get('close'))), _f(a.get('close_dollars', a.get('close')))
        if np.isfinite(bid) and bid > 1:                 # centavos
            bid, ask = bid / 100, ask / 100
        cierre = _f(p.get('close_dollars', p.get('close')))
        if np.isfinite(cierre) and cierre > 1:
            cierre /= 100
        medio = (bid + ask) / 2 if np.isfinite(bid) and np.isfinite(ask) and 0 < ask - bid <= 0.10 else cierre
        filas.append((pd.to_datetime(v['end_period_ts'], unit='s').normalize(), medio))
    if not filas:
        return np.nan
    s = pd.Series(dict(filas)).dropna()
    s = s[s.index <= CORTE + pd.Timedelta(days=1)]          # vela que cierra el 24-oct 00:00 UTC = 23-oct
    return float(s.iloc[-1]) if len(s) else np.nan


def poly_precio(crudo: Path, slug: str):
    f = next(iter(sorted((crudo / 'poly').glob(f'evento_{slug}*.json'))), None)
    if f is None:
        return np.nan
    ev = json.loads(f.read_text())
    pr = {}
    for m in ev.get('markets', []):
        q = (m.get('question') or '').lower()
        lado = 'D' if 'democrat' in q else 'R' if 'republican' in q else None
        h = crudo / 'poly' / f"hist_{m.get('id')}.json"
        if lado and h.exists():
            s = pd.DataFrame(json.loads(h.read_text()).get('history', []))
            if len(s):
                s['fecha'] = pd.to_datetime(s.t, unit='s').dt.normalize()
                s = s[s.fecha <= CORTE + pd.Timedelta(days=1)]
                if len(s):
                    pr[lado] = float(s.p.iloc[-1])
    if 'D' in pr and 'R' in pr and pr['D'] + pr['R'] > 0:
        return pr['D'] / (pr['D'] + pr['R'])
    return pr.get('D', np.nan)


def construir(crudo: Path) -> pd.DataFrame:
    filas, enc = [], []
    for c in contiendas():
        k_d, k_r = kalshi_precio(crudo, f"{c['kalshi']}-D"), kalshi_precio(crudo, f"{c['kalshi']}-R")
        k = k_d / (k_d + k_r) if np.isfinite(k_d) and np.isfinite(k_r) and k_d + k_r > 0 else k_d
        pm = poly_precio(crudo, c['poly'])
        f = crudo / 'wiki' / f"{c['wiki']}.json"
        res, n_enc = None, 0
        if f.exists():
            html = json.loads(f.read_text())['parse']['text']
            res = resultado(html, c['d'], c['r'])
            e = encuestas(html, c['d'], c['r'])
            n_enc = len(e)
            if len(e):
                enc.append(e.assign(contienda=c['id']))
        filas.append({**{k_: c[k_] for k_ in ('id', 'cargo', 'estado', 'd', 'r')}, 'kalshi_D': k, 'poly_D': pm,
                      'D_real': res[0] if res else np.nan, 'R_real': res[1] if res else np.nan,
                      'n_encuestas_hasta_corte': n_enc})
    t = pd.DataFrame(filas)
    t['margen_real'] = t.D_real - t.R_real
    DATOS.mkdir(parents=True, exist_ok=True)
    t.to_csv(DATOS / 'contiendas_2024.csv', index=False)
    if enc:
        pd.concat(enc).to_csv(DATOS / 'encuestas_2024_hasta_corte.csv', index=False)
    return t


# ------------------------------------------------------------------------------------ predicción de encuestas
def k_firmas(q: pd.DataFrame) -> int:
    return int(q.pollster_key.nunique())


def predicciones(t: pd.DataFrame) -> pd.DataFrame:
    cfg = cargar_config(corte='2026-10-21')                # solo para leer el histórico y los parámetros
    cfg.offline = True
    raw, _, _ = obtener_raw_polls(cfg)
    d = preparar(raw, cfg)
    d = d[d.year <= 2022]                                  # fuera de muestra para 2024
    house = efectos_casa(d, cfg.modelo.contraccion_casa)
    par = calibrar(cfg, H)                                 # τ, s, ν a 13 días (histórico 1998–2024 sin estas contiendas)
    enc = pd.read_csv(DATOS / 'encuestas_2024_hasta_corte.csv', parse_dates=['fin'])
    out = []
    for r in t.itertuples():
        p = enc[enc.contienda == r.id].copy()
        if p.empty or not np.isfinite(r.margen_real):
            continue
        p['pollster_key'] = p.clave_538
        p['days'] = (ELECCION - p.fin).dt.days
        p['margin_poll'] = p.D - p.R
        p['n'] = pd.to_numeric(p.n, errors='coerce').fillna(600).clip(100, 3000)
        q = p[p.days <= 21]                                # ventana de producción: últimos 21 días (aquí 13–21)
        regla = 'normal'
        if q.pollster_key.nunique() < 2:                    # regla desplazada de producción
            q = p[p.fin >= p.fin.max() - pd.Timedelta(days=21)]
            regla = 'desplazada'
        if (CORTE - q.fin.max()).days > 45 or k_firmas(q) < 2:
            continue                                       # sin al menos 2 encuestadoras recientes no hay promedio
        mu, _, k, _ = promedio(q, house, 14.0)
        extra = max(int(q.days.min()) - H, 0)
        sd = float(np.sqrt(par['tau'] ** 2 + par['s'] ** 2 / max(k, 1) + 0.25 ** 2 * extra))
        out.append({'id': r.id, 'cargo': r.cargo, 'mu': mu, 'sd': sd, 'nu': par['nu'], 'k': k, 'regla': regla,
                    'dias_extra': extra, 'kalshi_D': r.kalshi_D, 'poly_D': r.poly_D, 'margen_real': r.margen_real})
    x = pd.DataFrame(out)
    x['mercado_D'] = x[['kalshi_D', 'poly_D']].mean(axis=1)
    return x[x.mercado_D.notna()].reset_index(drop=True)


# ------------------------------------------------------------------------------------ estimación de w
def evaluar(x: pd.DataFrame, w: float) -> pd.DataFrame:
    sc = x.sd * np.sqrt((x.nu - 2) / x.nu)
    p0 = student_t.cdf(x.mu / sc, x.nu)
    pm = x.mercado_D.clip(1e-3, 1 - 1e-3)
    pw = expit((1 - w) * logit(np.clip(p0, 1e-4, 1 - 1e-4)) + w * logit(pm))
    mu_w = sc * student_t.ppf(pw, x.nu)
    z = (x.margen_real - mu_w) / sc
    gano = x.margen_real > 0
    # CRPS de la t escalada (fórmula cerrada)
    nu = x.nu
    from scipy.special import beta as B
    crps = sc * (z * (2 * student_t.cdf(z, nu) - 1) + 2 * student_t.pdf(z, nu) * (nu + z ** 2) / (nu - 1)
                 - 2 * np.sqrt(nu) * B(0.5, nu - 0.5) / ((nu - 1) * B(0.5, nu / 2) ** 2))
    return pd.DataFrame({'id': x.id, 'cargo': x.cargo, 'w': w, 'P': pw, 'mu_w': mu_w,
                         'll_margen': student_t.logpdf(z, nu) - np.log(sc),
                         'log_score': np.log(np.where(gano, pw, 1 - pw)), 'brier': (pw - gano) ** 2,
                         'error': mu_w - x.margen_real, 'crps': crps})


def perfil(x: pd.DataFrame, grid=np.round(np.arange(0, 1.0001, 0.05), 2)) -> pd.DataFrame:
    e = pd.concat([evaluar(x, w) for w in grid])
    g = e.groupby('w').agg(ll_margen=('ll_margen', 'sum'), log_score=('log_score', 'sum'), brier=('brier', 'mean'),
                           crps=('crps', 'mean'), mae=('error', lambda s: s.abs().mean()), sesgo=('error', 'mean'))
    return g


def ic_lr(g: pd.Series) -> tuple[float, float, float]:
    w_ml = float(g.idxmax())
    ok = g[g >= g.max() - 1.92].index
    return w_ml, float(ok.min()), float(ok.max())


def bootstrap(x: pd.DataFrame, col: str, B: int = 2000, semilla: int = 1) -> np.ndarray:
    grid = np.round(np.arange(0, 1.0001, 0.05), 2)
    E = np.stack([evaluar(x, w)[col].to_numpy() for w in grid])          # (w, contienda)
    rng = np.random.default_rng(semilla)
    idx = rng.integers(0, E.shape[1], (B, E.shape[1]))
    tot = E[:, idx].sum(axis=2)                                             # (w, B)
    return grid[np.argmax(tot, axis=0)]


def perfil_con_sesgo_comun(x: pd.DataFrame) -> pd.DataFrame:
    """Perfil en w dejando libre un sesgo común b (error compartido de las encuestas en el año).
    Separa lo que el mercado aporta por contienda de lo que solo refleja el error de 2024 en todos los estados."""
    from scipy.optimize import minimize_scalar
    sc = x.sd * np.sqrt((x.nu - 2) / x.nu)

    def ll(w, b):
        p0 = student_t.cdf((x.mu + b) / sc, x.nu)
        pw = expit((1 - w) * logit(np.clip(p0, 1e-4, 1 - 1e-4)) + w * logit(x.mercado_D.clip(1e-3, 1 - 1e-3)))
        return float(np.sum(student_t.logpdf((x.margen_real - sc * student_t.ppf(pw, x.nu)) / sc, x.nu) - np.log(sc)))
    filas = []
    for w in np.round(np.arange(0, 1.0001, 0.05), 2):
        r = minimize_scalar(lambda b: -ll(w, b), bounds=(-8, 8), method='bounded')
        filas.append({'w': w, 'll_margen_sin_sesgo_comun': ll(w, 0.0), 'll_margen_con_sesgo_comun': -r.fun, 'sesgo_comun_b': r.x})
    return pd.DataFrame(filas).set_index('w')


def main(crudo: str | None = None):
    if crudo:
        t = construir(Path(crudo))
    else:
        t = pd.read_csv(DATOS / 'contiendas_2024.csv')
    x = predicciones(t)
    x.to_csv(DATOS / 'predicciones_h13_2024.csv', index=False)
    g = perfil(x)
    g.to_csv(SAL / 'peso_mercados_perfil.csv')
    filas = []
    for amb, sel in (('Todas', x.index == x.index), ('Presidente', x.cargo == 'Pres'), ('Senado y gobernador', x.cargo != 'Pres')):
        xx = x[sel].reset_index(drop=True)
        gg = perfil(xx)
        for col in ('ll_margen', 'log_score'):
            w_ml, lo, hi = ic_lr(gg[col])
            bs = bootstrap(xx, col)
            filas.append({'ambito': amb, 'n': len(xx), 'criterio': col, 'w_ML': w_ml, 'IC95_LR': f'{lo:.2f}–{hi:.2f}',
                          'IC90_bootstrap': f'{np.quantile(bs, .05):.2f}–{np.quantile(bs, .95):.2f}',
                          'delta_LL_w0.30': float(gg.loc[0.3, col] - gg[col].max()),
                          'delta_LL_w0': float(gg.loc[0.0, col] - gg[col].max())})
    gc = perfil_con_sesgo_comun(x)
    gc.to_csv(SAL / 'peso_mercados_perfil_sesgo_comun.csv')
    w_ml, lo, hi = ic_lr(gc.ll_margen_con_sesgo_comun)
    filas.append({'ambito': 'Todas, con sesgo común libre', 'n': len(x), 'criterio': 'll_margen', 'w_ML': w_ml,
                  'IC95_LR': f'{lo:.2f}–{hi:.2f}', 'IC90_bootstrap': '',
                  'delta_LL_w0.30': float(gc.loc[0.3, 'll_margen_con_sesgo_comun'] - gc.ll_margen_con_sesgo_comun.max()),
                  'delta_LL_w0': float(gc.loc[0.0, 'll_margen_con_sesgo_comun'] - gc.ll_margen_con_sesgo_comun.max())})
    R = pd.DataFrame(filas)
    R.to_csv(SAL / 'peso_mercados_estimacion.csv', index=False)
    return t, x, g, R


if __name__ == '__main__':
    pd.set_option('display.width', 200)
    t, x, g, R = main(sys.argv[1] if len(sys.argv) > 1 else None)
    print(t.round(3).to_string(index=False))
    print(x.round(3).to_string(index=False))
    print(g.round(3).to_string())
    print(R.round(3).to_string(index=False))
