"""Motor de backtest (copia del de Arizona, generalizado por estado). Original: backtest para la general de Arizona: modelo de Georgia (V11) vs enfoque de la primaria de Arizona vs híbridos.

Marco (igual que Georgia): leave-one-year-out (LOYO); todo parámetro se estima sin el año evaluado.
Datos: FiveThirtyEight raw-polls 2023 (Gob/Sen/Pres generales 1998–2022, todos los estados)
       + GA Presidente 2024 + AZ Presidente 2024 y AZ Senado 2024 (Wikipedia, una versión por encuesta).
Horizonte: encuestas con >= H días antes de la elección (H = 13, igual que hoy: 21-oct → 3-nov).

Piezas que se combinan:
  MEDIA   v11  = efecto de casa (contraído) + √n + vida media 14 d + cada firma pesa ~1   (Georgia)
          prim = recencia vida media 10 d × √n × 1/MOE (≡ ∝ n) sin casa ni control por firma  (primaria AZ)
  INDEC.  u50  = indecisos 50/50 (margen tal cual)                                      (Georgia)
          uprop= proporcional a D, R y terceros                                          (primaria: escenario 1)
          umix = mezcla de escenarios de la primaria (proporcional .25, temperatura .35,
                 consolidación R .28 [55/30/15], repunte D .12 [32/53/15])               (primaria)
  SESGO   est  = sesgo estatal pasado (vida media 4 años, Bayes empírico)                (Georgia)
  INCERT. sig  = σ = √(τ² + s²/k) calibrada + colas t (ν estimado)                       (Georgia)
          dir  = Dirichlet(N_ef = 750) + shocks N(0, 3.5 D / 4.0 R / 2.8 otros)          (primaria)

Métricas del margen: CRPS (principal), MAE, sesgo, cobertura 80/95, Brier de P(D gana).
Métricas de porcentajes: MAE del % D y del % R con distintas reglas para terceros.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm, t as student_t
from scipy.special import beta as Bfun

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
import base_georgia as bt  # noqa: E402

SAL = BASE / 'salida'
SAL.mkdir(exist_ok=True)
H = 13
RNG = np.random.default_rng(20261021)
NSIM = 4000
AZ24 = {'2024_Pres-G_AZ': (46.69, 52.22), '2024_Sen-G_AZ': (50.06, 47.65)}


# ----------------------------------------------------------------------------- datos
def cargar() -> pd.DataFrame:
    d = bt.cargar_encuestas()
    a = pd.read_csv(BASE / 'data' / 'az2024_encuestas_finales.csv', parse_dates=['polldate', 'electiondate'])
    a['rk'] = a['pop'].map({'LV': 0, 'RV': 1, 'A': 2}).fillna(3)
    a = a.sort_values('rk').drop_duplicates(['race', 'pollster', 'polldate'])        # una versión: LV > RV > A
    a = a.assign(runoff=False, samplesize=a.n, cand1_pct=a.D, cand2_pct=a.R,
                 cand3_pct=a.otros, cand1_actual=a.race.map(lambda r: AZ24[r][0]),
                 cand2_actual=a.race.map(lambda r: AZ24[r][1]))
    a['partisan'] = a.partisan.fillna('')
    keep = ['race', 'year', 'location', 'type_simple', 'runoff', 'pollster', 'partisan', 'polldate',
            'electiondate', 'samplesize', 'cand1_pct', 'cand2_pct', 'cand3_pct', 'cand1_actual', 'cand2_actual']
    a = a[keep]
    a['days'] = (a.electiondate - a.polldate).dt.days
    a['margin_poll'] = a.cand1_pct - a.cand2_pct
    a['margin_actual'] = a.cand1_actual - a.cand2_actual
    a['major_poll'] = a.cand1_pct + a.cand2_pct
    a['n'] = pd.to_numeric(a.samplesize, errors='coerce').fillna(600).clip(100, 3000)
    a['pollster_key'] = a.pollster.str.lower().str.replace(r'[^a-z]', '', regex=True).str[:14]
    d = pd.concat([d, a[d.columns]], ignore_index=True)
    d['cand3_pct'] = pd.to_numeric(d.cand3_pct, errors='coerce').fillna(0.0)
    d['otros_real'] = (100 - d.cand1_actual - d.cand2_actual).clip(lower=0)
    return d


# ------------------------------------------------------------------------- agregados
def agregar(p: pd.DataFrame, house: dict, metodo: str) -> dict | None:
    if p.empty:
        return None
    D, R, O = (p.cand1_pct.to_numpy(float), p.cand2_pct.to_numpy(float), p.cand3_pct.to_numpy(float))
    dt = (p.days - p.days.min()).to_numpy(float)
    n = p.n.to_numpy(float)
    if metodo == 'v11':
        adj = p.pollster_key.map(house).fillna(0).to_numpy(float)          # casa: se resta al margen
        w = np.exp(-np.log(2) * dt / 14.0) * np.sqrt(n)
        w = w / p.pollster_key.map(p.pollster_key.value_counts()).to_numpy(float)
    elif metodo == 'v11_hl10':
        adj = p.pollster_key.map(house).fillna(0).to_numpy(float)
        w = np.exp(-np.log(2) * dt / 10.0) * np.sqrt(n)
        w = w / p.pollster_key.map(p.pollster_key.value_counts()).to_numpy(float)
    elif metodo == 'v11_n':                                                  # pesos ∝ n con casa y firma
        adj = p.pollster_key.map(house).fillna(0).to_numpy(float)
        w = np.exp(-np.log(2) * dt / 14.0) * n
        w = w / p.pollster_key.map(p.pollster_key.value_counts()).to_numpy(float)
    elif metodo == 'prim':                                                   # primaria AZ
        adj = np.zeros(len(p))
        moe = 100 * 1.96 * np.sqrt(0.25 / n)                                 # MOE publicado ≈ 98/√n
        w = 0.5 ** (dt / 10.0) * np.sqrt(n) * (1 / moe)
    else:
        raise ValueError(metodo)
    w = w / w.sum()
    Dm, Rm, Om = float(w @ D), float(w @ R), float(w @ O)
    # la corrección de casa se reparte mitad y mitad entre D y R
    a = float(w @ adj)
    Dm, Rm = Dm - a / 2, Rm + a / 2
    return {'D': Dm, 'R': Rm, 'O': Om, 'U': max(100 - Dm - Rm - Om, 0.0), 'k': int(p.pollster_key.nunique()),
            'neff': 1 / float(np.sum(w ** 2))}


def margen_indecisos(a: dict, regla: str, s_r: float = 0.5) -> float:
    D, R, O, U = a['D'], a['R'], a['O'], a['U']
    if regla == 'u50':
        return D - R
    if regla == 'uprop':
        return (D - R) * (1 + U / max(D + R + O, 1e-9))
    if regla == 'ufit':
        return D - R + U * (1 - 2 * s_r)
    if regla == 'ufl':                                       # primaria FL (FIX v8): 40 % proporcional, 35 % fragmentado
        tot = max(D + R + O, 1e-9)                           # (reparto parejo entre D, R y terceros), 25 % consolidación
        sh = np.array([D, R, O]) / tot                       # hacia el líder (cuotas al cuadrado)
        frag = np.array([1, 1, 1]) / 3 if O > 0.5 else np.array([.5, .5, 0])
        con = sh ** 2 / np.sum(sh ** 2)
        mezcla = .40 * sh + .35 * frag + .25 * con
        return D - R + U * (mezcla[0] - mezcla[1])
    if regla == 'umix':
        tot = max(D + R + O, 1e-9)
        prop = (D - R) * (1 + U / tot)
        sh = np.array([D, R, O]) / tot
        tmp = sh ** 0.85; tmp /= tmp.sum()
        temp = D - R + U * (tmp[0] - tmp[1])
        cons_r = D - R + U * (0.30 - 0.55)
        surge_d = D - R + U * (0.53 - 0.32)
        return .25 * prop + .35 * temp + .28 * cons_r + .12 * surge_d
    raise ValueError(regla)


def construir(d: pd.DataFrame, casa: dict, metodo: str) -> pd.DataFrame:
    filas = []
    for race, p in d.groupby('race'):
        y = int(p.year.iloc[0])
        q = p[p.days >= H]
        a = agregar(q, casa[y][0], metodo)
        if a is None:
            continue
        filas.append({'race': race, 'year': y, 'location': p.location.iloc[0], 'tipo': p.type_simple.iloc[0],
                      'runoff': bool(p.runoff.iloc[0]), **a, 'actual': float(p.margin_actual.iloc[0]),
                      'D_real': float(p.cand1_actual.iloc[0]), 'R_real': float(p.cand2_actual.iloc[0]),
                      'O_real': float(p.otros_real.iloc[0])})
    return pd.DataFrame(filas)


# ----------------------------------------------------------------------- incertidumbre
def nu_entrenado(e, k, tau, s):
    z = e / np.sqrt(tau ** 2 + s ** 2 / np.maximum(k, 1))
    nus = np.linspace(2.5, 60, 116)
    ll = [np.sum(student_t.logpdf(z, nu, scale=np.sqrt((nu - 2) / nu))) for nu in nus]
    return float(nus[int(np.argmax(ll))])


def crps_t(y, mu, sd, nu):
    sc = sd * np.sqrt((nu - 2) / nu)
    z = (y - mu) / sc
    F, f = student_t.cdf(z, nu), student_t.pdf(z, nu)
    term = 2 * np.sqrt(nu) * Bfun(.5, nu - .5) / ((nu - 1) * Bfun(.5, nu / 2) ** 2)
    return sc * (z * (2 * F - 1) + 2 * f * (nu + z ** 2) / (nu - 1) - term)


def crps_muestras(x: np.ndarray, y: float) -> float:
    x = np.sort(x)
    n = len(x)
    return float(np.mean(np.abs(x - y)) - np.sum((2 * np.arange(1, n + 1) - n - 1) * x) / n ** 2)


def muestras_dirichlet(a: dict, mu_margen: float) -> np.ndarray:
    """Motor de la primaria: Dirichlet(N_ef 750) sobre (D, R, O, U) + reparto + shocks; se recentra en mu."""
    v = np.array([a['D'], a['R'], a['O'], a['U']]) / 100
    v = np.clip(v, 1e-4, None); v /= v.sum()
    x = RNG.dirichlet(v * 750 + 0.1, NSIM)
    c, u = x[:, :3], x[:, 3]
    c = c + u[:, None] * c / c.sum(axis=1, keepdims=True)                     # reparto proporcional
    c = c * 100 + RNG.normal(0, [3.5, 4.0, 2.8], (NSIM, 3))
    c = c - (c.mean(axis=1, keepdims=True) - c.mean())                      # shocks de media cero
    c = np.maximum(c, 0); c = c / c.sum(axis=1, keepdims=True) * 100
    m = c[:, 0] - c[:, 1]
    return m - m.mean() + mu_margen


# --------------------------------------------------------------------------- evaluar
def sesgo_pasado(tr: pd.DataFrame, y: int, contraer: bool = True) -> dict:
    tr = tr.assign(e=tr.mu0 - tr.actual)
    past = tr[tr.year < y].copy()
    if len(past) < 20:
        return {}
    past['w'] = 0.5 ** ((y - past.year) / 4.0)
    st = past.groupby('location').apply(lambda g: pd.Series({
        'm': np.average(g.e, weights=g.w), 'neff': g.w.sum() ** 2 / (g.w ** 2).sum(),
        'v': g.e.var() if len(g) > 1 else np.nan}), include_groups=False)
    st = st[st.neff >= 1.5]
    vs = max(float(st.m.var()) - float(np.nanmean(st.v / st.neff)), 0)
    if not contraer:
        return {l: float(r.m) for l, r in st.iterrows()}
    return {l: (vs / (vs + r.v / r.neff)) * r.m if vs > 0 and np.isfinite(r.v) else 0.0 for l, r in st.iterrows()}


def evaluar(b: pd.DataFrame, nombre: str, regla: str, sesgo: bool, incert: str) -> pd.DataFrame:
    b = b.copy()
    years = sorted(b.year.unique())
    preds = []
    for y in years:
        te, tr = b[b.year == y].copy(), b[b.year != y].copy()
        s_r = 0.5
        if regla == 'ufit':                                         # cuota R de indecisos estimada en entrenamiento
            g = np.linspace(0.3, 0.7, 41)
            sse = [np.sum((tr.D - tr.R + tr.U * (1 - 2 * s) - tr.actual) ** 2) for s in g]
            s_r = float(g[int(np.argmin(sse))])
        for t in (tr, te):
            t['mu0'] = [margen_indecisos(r, regla, s_r) for r in t[['D', 'R', 'O', 'U']].to_dict('records')]
        bias = sesgo_pasado(tr, y, contraer=(sesgo != 'raw')) if sesgo else {}
        te['mu'] = te.mu0 - te.location.map(bias).fillna(0.0)
        e = (tr.mu0 - tr.actual).to_numpy()
        tau, s = bt.ajustar_sigma(e, tr.k.to_numpy())
        nu = nu_entrenado(e, tr.k.to_numpy(), tau, s)
        te['sd'] = np.sqrt(tau ** 2 + s ** 2 / np.maximum(te.k, 1))
        te['nu'] = nu
        te['s_r'] = s_r
        preds.append(te)
    P = pd.concat(preds, ignore_index=True)
    if incert == 'sig':
        P['crps'] = crps_t(P.actual, P.mu, P.sd, P.nu)
        sc = P.sd * np.sqrt((P.nu - 2) / P.nu)
        P['pD'] = student_t.cdf(P.mu / sc, P.nu)
        P['c80'] = np.abs(P.mu - P.actual) <= student_t.ppf(.9, P.nu) * sc
        P['c95'] = np.abs(P.mu - P.actual) <= student_t.ppf(.975, P.nu) * sc
        P['sd_eff'] = P.sd
    else:
        cr, pd_, c80, c95, sde = [], [], [], [], []
        for r in P.itertuples():
            x = muestras_dirichlet({'D': r.D, 'R': r.R, 'O': r.O, 'U': r.U}, r.mu)
            cr.append(crps_muestras(x, r.actual)); pd_.append(float(np.mean(x > 0)))
            q = np.quantile(x, [.025, .1, .9, .975])
            c80.append(q[1] <= r.actual <= q[2]); c95.append(q[0] <= r.actual <= q[3]); sde.append(float(x.std()))
        P['crps'], P['pD'], P['c80'], P['c95'], P['sd_eff'] = cr, pd_, c80, c95, sde
    P['modelo'] = nombre
    return P


ESTADO = 'AZ'


def resumen(P: pd.DataFrame) -> pd.DataFrame:
    filas = []
    E = ESTADO
    for amb, m in [('Nacional', P.index == P.index), ('Nacional_Gob', P.tipo == 'Gov-G'),
                   (f'{E}_todas', P.location == E), (f'{E}_2016+', (P.location == E) & (P.year >= 2016)),
                   (f'{E}_Gob', (P.location == E) & (P.tipo == 'Gov-G'))]:
        for mod, g in P[m].groupby('modelo'):
            e = g.mu - g.actual
            filas.append({'ambito': amb, 'modelo': mod, 'n': len(g), 'CRPS': g.crps.mean(), 'MAE': e.abs().mean(),
                          'sesgo': e.mean(), 'Cob80': g.c80.mean(), 'Cob95': g.c95.mean(),
                          'Brier': ((g.pD - (g.actual > 0)) ** 2).mean(), 'sd_media': g.sd_eff.mean()})
    return pd.DataFrame(filas)


def bootstrap_por_anio(P: pd.DataFrame, a: str, b: str, sel=None, B=2000) -> float:
    """P(modelo a tiene menor CRPS que b) remuestreando años."""
    x = P[P.modelo.isin([a, b])] if sel is None else P[P.modelo.isin([a, b]) & sel]
    t = x.pivot_table(index=['race', 'year'], columns='modelo', values='crps').dropna().reset_index()
    yrs = t.year.unique()
    gana = 0
    for _ in range(B):
        ys = RNG.choice(yrs, len(yrs))
        s = pd.concat([t[t.year == y] for y in ys])
        gana += s[a].mean() < s[b].mean()
    return gana / B


# ---------------------------------------------------------------------- porcentajes
def porcentajes(b: pd.DataFrame, P: pd.DataFrame) -> pd.DataFrame:
    """% D y % R: margen del modelo + regla para terceros (otros reales = 100 − D − R)."""
    x = P.merge(b[['race', 'O']].rename(columns={'O': 'O_enc'}), on='race')
    filas = []
    for y in sorted(x.year.unique()):
        te, tr = x[x.year == y].copy(), x[x.year != y]
        # terceros: real ≈ a + c·(otros en encuestas)  (estimado sin el año)
        A = np.c_[np.ones(len(tr)), tr.O_enc]
        coef = np.linalg.lstsq(A, tr.O_real, rcond=None)[0]
        reglas = {
            'T0 terceros = 0 (Georgia)': np.zeros(len(te)),
            'T1 terceros = lo que dicen las encuestas (primaria)': te.O_enc.to_numpy(),
            'T2 terceros calibrados a + c·encuesta (LOYO)': np.clip(coef[0] + coef[1] * te.O_enc, 0, None).to_numpy(),
            'T3 terceros = media histórica del estado (pasado)': te.location.map(
                tr[tr.year < y].groupby('location').O_real.mean()).fillna(tr.O_real.mean()).to_numpy(),
        }
        for nom, T in reglas.items():
            Dp, Rp = (100 - T + te.mu) / 2, (100 - T - te.mu) / 2
            filas.append(te.assign(regla=nom, Dp=Dp, Rp=Rp, Tp=T, c=coef[1]))
    Q = pd.concat(filas)
    out = []
    for amb, m in [('Nacional', Q.index == Q.index), (f'{ESTADO}_todas', Q.location == ESTADO),
                   ('Con terceros > 3%', Q.O_real > 3)]:
        for (mod, r), g in Q[m].groupby(['modelo', 'regla']):
            out.append({'ambito': amb, 'modelo': mod, 'regla': r, 'n': len(g),
                        'MAE_%D': (g.Dp - g.D_real).abs().mean(), 'MAE_%R': (g.Rp - g.R_real).abs().mean(),
                        'MAE_terceros': (g.Tp - g.O_real).abs().mean(), 'sesgo_terceros': (g.Tp - g.O_real).mean()})
    return pd.DataFrame(out), Q


VARIANTES = {   # nombre: (media, indecisos, sesgo estatal, incertidumbre)
    'G  Georgia V11': ('v11', 'u50', True, 'sig'),
    'A  Primaria AZ (tal cual)': ('prim', 'umix', False, 'dir'),
    'H1 V11 + escenarios de indecisos de la primaria': ('v11', 'umix', True, 'sig'),
    'H2 V11 + indecisos proporcionales': ('v11', 'uprop', True, 'sig'),
    'H3 V11 + cuota R de indecisos estimada': ('v11', 'ufit', True, 'sig'),
    'H4 V11 + Dirichlet y shocks de la primaria': ('v11', 'u50', True, 'dir'),
    'H5 Pesos de la primaria + resto V11': ('prim', 'u50', True, 'sig'),
    'H6 V11 con vida media 10 d': ('v11_hl10', 'u50', True, 'sig'),
    'H7 V11 con pesos ∝ n': ('v11_n', 'u50', True, 'sig'),
    'H8 V11 sin sesgo estatal': ('v11', 'u50', False, 'sig'),
}


def main():
    d = cargar()
    years = sorted(d.year.unique())
    casa = {y: bt.efectos_casa(d[d.year != y]) for y in years}
    bases = {m: construir(d, casa, m) for m in ('v11', 'v11_hl10', 'v11_n', 'prim')}
    comunes = set.intersection(*[set(b.race) for b in bases.values()])
    bases = {m: b[b.race.isin(comunes)].reset_index(drop=True) for m, b in bases.items()}
    P = pd.concat([evaluar(bases[me], nom, ui, se, inc) for nom, (me, ui, se, inc) in VARIANTES.items()],
                  ignore_index=True)
    R = resumen(P)
    T, Q = porcentajes(bases['v11'], P[P.modelo.isin(['G  Georgia V11', 'H2 V11 + indecisos proporcionales'])])
    boot = []
    for amb, sel in [('Nacional', None), ('AZ_todas', P.location == 'AZ')]:
        for v in VARIANTES:
            if v.startswith('G'):
                continue
            boot.append({'ambito': amb, 'variante': v, 'P(variante mejor que V11)': bootstrap_por_anio(P, v, 'G  Georgia V11', sel)})
    Bt = pd.DataFrame(boot)
    P.to_csv(SAL / 'predicciones_LOYO.csv', index=False)
    R.to_csv(SAL / 'metricas_margen.csv', index=False)
    T.to_csv(SAL / 'metricas_porcentajes.csv', index=False)
    Bt.to_csv(SAL / 'bootstrap_vs_V11.csv', index=False)
    return d, bases, P, R, T, Q, Bt


if __name__ == '__main__':
    pd.set_option('display.width', 230)
    d, bases, P, R, T, Q, Bt = main()
    print(f'Contiendas evaluadas (H={H}): {P.race.nunique()} · AZ: {P[P.location == "AZ"].race.nunique()}')
    for amb in R.ambito.unique():
        print('\n==', amb)
        print(R[R.ambito == amb].drop(columns='ambito').sort_values('CRPS').round(3).to_string(index=False))
    print('\n== Bootstrap por año (P de que la variante tenga menor CRPS que V11)')
    print(Bt.pivot(index='variante', columns='ambito', values='P(variante mejor que V11)').round(3).to_string())
    print('\n== Porcentajes por candidato (reglas de terceros)')
    print(T.round(2).to_string(index=False))
