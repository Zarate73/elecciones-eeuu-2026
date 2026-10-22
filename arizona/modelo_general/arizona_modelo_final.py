"""Arizona Gobernador 2026 · MODELO FINAL (general: Hobbs D vs Biggs R + terceros).

Selección por backtest (../backtest, leave-one-year-out, 782 contiendas 1998–2024, 22 de Arizona):
  - Base: modelo de Georgia V11 (promedio con efectos de casa, √n, vida media 14 d, cada firma pesa ~1;
    σ = √(τ² + s²/k) calibrada; colas Student-t). Ganó a nivel nacional (CRPS 3.495).
  - SIN sesgo estatal: en Arizona el error relativo no persiste entre ciclos (corr −0.11 vs +0.22 nacional)
    y quitarlo bajó el CRPS de AZ de 2.630 a 2.471 (P(mejor) 0.85 por bootstrap de años).
  - Terceros calibrados (de la primaria: candidatos nombrados, sin bucket genérico): real = a + c·encuestas
    (a ≈ 1.9, c ≈ 0.69, LOYO). Bajó el MAE del % D de 3.08 a 2.56 (nacional) y de 2.53 a 1.94 (AZ).
  - Indecisos 50/50 entre D y R: los escenarios de la primaria, el reparto proporcional y la cuota R
    estimada (≈0.55) empeoran el CRPS.
  - Descartado de la primaria: pesos ∝ n (√n·1/MOE), vida media 10 d, Dirichlet N_ef 750 + shocks por facción,
    escenarios por facción calibrados con Maricopa (todos peores o sin ganancia en el backtest).
  - Mercados: Kalshi y Polymarket (promedio) en mezcla logit con peso 0.30, como GA y CA (no validable:
    solo 2 contiendas AZ con historia en ambos).

  margen   = Σ w_i (margen_i − casa_i) / Σ w_i            ventana: últimos 21 días; si < 2 firmas, la más
                                                          reciente de cada firma (regla V11)
  σ, ν     calibrados a los días que faltan (13 al 21-oct) + deriva 0.25²·(días que las encuestas son más
           viejas que ese horizonte); ventana: 21 días, o los 21 días previos a la encuesta más reciente si
           hay menos de 2 encuestadoras (pasa hoy: la última encuesta terminó el 8-oct)
  terceros T ~ N(a + c·otros_encuestas, sd_resid), mínimo 0.1 pp
  Hobbs    = (100 − T + margen)/2 ;  Biggs = (100 − T − margen)/2
  recuento automático si |margen| ≤ 0.5 pp

Uso:  import arizona_modelo_final as am ; r = am.ejecutar()
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit
from scipy.stats import norm, t as student_t

import encuestas_web as W

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'datos'
AZ24 = {'2024_Pres-G_AZ': (46.69, 52.22), '2024_Sen-G_AZ': (50.06, 47.65)}
MESES_ES = {'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10,
            'nov': 11, 'dic': 12}
# misma encuestadora con nombres distintos entre fuentes (clave_538 de 14 letras)
ALIAS = {'aarp': 'fabrizioward', 'bspresearch': 'arizonastateun', 'bspresearchas': 'arizonastateun',
         'highgroundinc': 'highground', 'grayhouser': 'grayhouse', 'gqrd': 'gqr', 'equisresearchd': 'equisresearch',
         'noblepredictiv': 'noblepredictiv', 'ohpredictivein': 'noblepredictiv', 'thetarrancegro': 'tarrancegroup',
         'tarrancegroupr': 'tarrancegroup', 'nextgenpolling': 'nextgenpolling', 'nextgenp': 'nextgenpolling'}


@dataclass
class Config:
    corte: date = date(2026, 10, 21)
    eleccion: date = date(2026, 11, 3)
    ventana_dias_eleccion: int = 21
    min_encuestadoras: int = 2
    vida_media_dias: float = 14.0
    contraccion_casa: float = 8.0
    sesgo_estatal: bool = False            # backtest AZ: sin sesgo estatal
    peso_mercados: float = 0.30            # 0 = solo encuestas
    terceros_a: float | None = None        # None = calibrar con el histórico (LOYO completo)
    recuento_pp: float = 0.5               # recuento automático en AZ
    civicapi_en_vivo: bool = True          # voto anticipado de civicAPI; si falla, último snapshot guardado
    sigma_dia_pp: float = 0.25             # deriva diaria si las encuestas son más viejas que el horizonte calibrado
                                           # (supuesto de California M5; no validable con 538, que solo trae 21 días)
    n_sim: int = 200_000
    semilla: int = 20261021
    salida: Path = field(default_factory=lambda: ROOT / 'salida')

    @property
    def dias_a_eleccion(self) -> int:
        return (pd.Timestamp(self.eleccion) - pd.Timestamp(self.corte)).days


# =============================================================================== histórico
def cargar_historico() -> pd.DataFrame:
    d = pd.read_csv(DATA / 'fte_raw_polls_2023.csv', low_memory=False)
    d = d[d.type_simple.isin(['Gov-G', 'Sen-G', 'Pres-G']) & (d.location != 'US')]
    d = d[(d.cand1_party == 'DEM') & (d.cand2_party == 'REP') & ((d.cand1_actual + d.cand2_actual) >= 85)].copy()
    keep = ['race', 'year', 'location', 'type_simple', 'pollster', 'polldate', 'electiondate', 'samplesize',
            'cand1_pct', 'cand2_pct', 'cand3_pct', 'cand1_actual', 'cand2_actual', 'partisan']
    d = d[keep].copy()
    d['polldate'] = pd.to_datetime(d.polldate, format='%m/%d/%Y')
    d['electiondate'] = pd.to_datetime(d.electiondate, format='%m/%d/%Y')
    g = pd.read_csv(DATA / 'ga_pres2024_polls.csv')
    g = g.assign(partisan=g.get('partisan', np.nan), race='2024_Pres-G_GA', year=2024, location='GA', type_simple='Pres-G', cand3_pct=np.nan,
                 electiondate=pd.Timestamp('2024-11-05'), polldate=pd.to_datetime(g.polldate),
                 cand1_actual=48.53, cand2_actual=50.73)
    a = pd.read_csv(DATA / 'az2024_encuestas_finales.csv', parse_dates=['polldate', 'electiondate'])
    a['rk'] = a['pop'].map({'LV': 0, 'RV': 1, 'A': 2}).fillna(3)
    a = a.sort_values('rk').drop_duplicates(['race', 'pollster', 'polldate'])
    a = a.assign(partisan=a.get('partisan', np.nan), samplesize=a.n, cand1_pct=a.D, cand2_pct=a.R, cand3_pct=a.otros,
                 cand1_actual=a.race.map(lambda r: AZ24[r][0]), cand2_actual=a.race.map(lambda r: AZ24[r][1]))
    d = pd.concat([d, g[keep], a[keep]], ignore_index=True)
    d['days'] = (d.electiondate - d.polldate).dt.days
    d['margin_poll'] = d.cand1_pct - d.cand2_pct
    d['margin_actual'] = d.cand1_actual - d.cand2_actual
    d['n'] = pd.to_numeric(d.samplesize, errors='coerce').fillna(600).clip(100, 3000)
    d['pollster_key'] = d.pollster.str.lower().str.replace(r'[^a-z]', '', regex=True).str[:14]
    d['cand3_pct'] = pd.to_numeric(d.cand3_pct, errors='coerce').fillna(0.0)
    d['otros_real'] = (100 - d.cand1_actual - d.cand2_actual).clip(lower=0)
    return d


def efectos_casa(train: pd.DataFrame, k: float) -> dict:
    t = train.copy()
    t['dev'] = t.margin_poll - t.groupby('race').margin_poll.transform('mean')
    t = t[t.groupby('race').margin_poll.transform('size') >= 3]
    hp = t.groupby('pollster_key').dev.agg(['sum', 'size'])
    return (hp['sum'] / (hp['size'] + k)).to_dict()


def efectos_partidistas(k: float = 8.0) -> dict:
    """Desviación media (contraída) del margen de encuestas con patrocinador D o R frente al promedio de su contienda.
    Solo para el escenario de sensibilidad: en el backtest no mejora el CRPS nacional (3.579 vs 3.545 sin casa)."""
    t = cargar_historico()
    t['dev'] = t.margin_poll - t.groupby('race').margin_poll.transform('mean')
    t = t[(t.groupby('race').margin_poll.transform('size') >= 3) & t.partisan.isin(['D', 'R'])]
    g = t.groupby('partisan').dev.agg(['sum', 'size'])
    return (g['sum'] / (g['size'] + k)).to_dict()


def lado_partidista(pollster: str) -> str | None:
    """'D', 'R' o None. Una encuesta bipartidista (p. ej. Fabrizio Ward (R) / Impact Research (D)) no se ajusta."""
    lados = set(re.findall(r'\((D|R)\)', str(pollster)))
    return lados.pop() if len(lados) == 1 else None


def promedio(p: pd.DataFrame, house: dict, vida_media: float) -> tuple[float, float, int, pd.Series]:
    """(margen corregido por casa, % otros ponderado, k encuestadoras, pesos)."""
    m = p.margin_poll.to_numpy(float) - p.pollster_key.map(house).fillna(0).to_numpy(float)
    dt = (p.days - p.days.min()).to_numpy(float)
    w = np.exp(-np.log(2) * dt / vida_media) * np.sqrt(p.n.to_numpy(float))
    w = w / p.pollster_key.map(p.pollster_key.value_counts()).to_numpy(float)
    w = w / w.sum()
    return float(w @ m), float(w @ p.otros.fillna(0).to_numpy(float)), int(p.pollster_key.nunique()), pd.Series(w, p.index)


def ajustar_sigma(err, k) -> tuple[float, float]:
    taus = np.linspace(1.0, 8.0, 141)[:, None, None]
    ss = np.linspace(0.0, 12.0, 121)[None, :, None]
    v = taus ** 2 + ss ** 2 / np.maximum(np.asarray(k, float), 1)[None, None, :]
    ll = -0.5 * np.sum(np.log(v) + np.asarray(err, float)[None, None, :] ** 2 / v, axis=2)
    i, j = np.unravel_index(np.argmax(ll), ll.shape)
    return float(taus[i, 0, 0]), float(ss[0, j, 0])


def calibrar(cfg: Config, h: int, usar_cache: bool = True) -> dict:
    """τ, s, ν al horizonte h; efectos de casa; terceros a + c·encuesta; sesgo estatal AZ (informativo)."""
    firma = hashlib.md5(b''.join((DATA / f).read_bytes()[:300000] for f in
                                 ('fte_raw_polls_2023.csv', 'ga_pres2024_polls.csv', 'az2024_encuestas_finales.csv'))).hexdigest()[:10]
    cache = cfg.salida / 'cache' / f'calibracion_h{h}_k{cfg.contraccion_casa}_vm{cfg.vida_media_dias}_{firma}.json'
    if usar_cache and cache.exists():
        return json.loads(cache.read_text(encoding='utf8'))
    d = cargar_historico()
    filas = []
    for y in sorted(d.year.unique()):
        house = efectos_casa(d[d.year != y], cfg.contraccion_casa)
        for race, p in d[d.year == y].groupby('race'):
            q = p[p.days >= h].rename(columns={'cand3_pct': 'otros'})
            if q.empty:
                continue
            mu, o, k, _ = promedio(q, house, cfg.vida_media_dias)
            filas.append({'race': race, 'year': y, 'location': p.location.iloc[0], 'k': k, 'otros_enc': o,
                          'otros_real': float(p.otros_real.iloc[0]), 'e': mu - float(p.margin_actual.iloc[0])})
    b = pd.DataFrame(filas)
    tau, s = ajustar_sigma(b.e, b.k)
    z = b.e / np.sqrt(tau ** 2 + s ** 2 / np.maximum(b.k, 1))
    nus = np.linspace(2.5, 60, 576)
    nu = float(nus[int(np.argmax([np.sum(student_t.logpdf(z, v, scale=np.sqrt((v - 2) / v))) for v in nus]))])
    A = np.c_[np.ones(len(b)), b.otros_enc]
    coef = np.linalg.lstsq(A, b.otros_real, rcond=None)[0]
    sd_t = float(np.std(b.otros_real - A @ coef, ddof=2))
    # sesgo estatal AZ (V11, vida media 4 años, contracción) -> solo para el escenario de sensibilidad
    b['w'] = 0.5 ** ((pd.Timestamp(cfg.eleccion).year - b.year) / 4.0)
    st = b.groupby('location').apply(lambda g: pd.Series({
        'm': np.average(g.e, weights=g.w), 'neff': g.w.sum() ** 2 / (g.w ** 2).sum(),
        'v': g.e.var() if len(g) > 1 else np.nan}), include_groups=False)
    st = st[st.neff >= 1.5]
    vs = max(float(st.m.var()) - float(np.nanmean(st.v / st.neff)), 0.0)
    r = st.loc['AZ']
    contr = vs / (vs + r.v / r.neff) if vs > 0 else 0.0
    par = {'horizonte_dias': h, 'tau': tau, 's': s, 'nu': nu, 'n_contiendas': len(b),
           'terceros_a': float(coef[0]), 'terceros_c': float(coef[1]), 'terceros_sd': sd_t,
           'sesgo_az_bruto': float(r.m), 'sesgo_az_contraido': float(contr * r.m),
           'efectos_casa': efectos_casa(d, cfg.contraccion_casa),
           'errores_az': b[b.location == 'AZ'].drop(columns='w').round(3).to_dict('records')}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(par, ensure_ascii=False), encoding='utf8')
    return par


# ================================================================================== encuestas 2026
def _fechas_es(txt: str) -> tuple[date, date]:
    """'30 sep–05 oct 2026' · '01–09 sep 2026' · '18 ago–04 sep 2026'."""
    s = str(txt).strip().lower().replace('—', '–').replace('-', '–')
    anio = int(re.search(r'(\d{4})', s).group(1))
    s = re.sub(r'\s*\d{4}\s*$', '', s)
    ini, fin = [x.strip() for x in s.split('–')] if '–' in s else (s, s)
    mf = re.match(r'(\d{1,2})\s+([a-z]{3})', fin)
    df_, mes_f = int(mf.group(1)), MESES_ES[mf.group(2)]
    mi = re.match(r'(\d{1,2})(?:\s+([a-z]{3}))?', ini)
    di, mes_i = int(mi.group(1)), MESES_ES[mi.group(2)] if mi.group(2) else mes_f
    return date(anio - (mes_i > mes_f), mes_i, di), date(anio, mes_f, df_)


def encuestas_excel(ruta: Path) -> pd.DataFrame:
    """Bloque «Encuestas Individuales» de ARIZONA_GOBERNADOR-v1.xlsx (hoja Gobernador Arizona)."""
    m = pd.read_excel(ruta, sheet_name='Gobernador Arizona', header=None, dtype=object).values.tolist()
    fila = lambda pref: next(i for i, r in enumerate(m) if str(r[0]).lower().startswith(pref))
    i_n, i_f, i_d, i_r = fila('encuestadora'), fila('survey dates'), fila('katie hobbs'), fila('andy biggs')
    out = []
    for j in range(1, len(m[i_n])):
        nombre = m[i_n][j]
        if pd.isna(nombre) or not str(nombre).strip() or not re.search(r'\d{4}', str(m[i_f][j])):
            continue                                   # columnas sin encuesta (notas, celdas vacías)
        ini, fin = _fechas_es(m[i_f][j])
        out.append({'pollster': str(nombre).strip(), 'inicio': ini, 'fin': fin, 'n': np.nan, 'pop': None,
                    'D': float(m[i_d][j]), 'R': float(m[i_r][j]), 'otros': np.nan, 'indecisos': np.nan,
                    'origen': 'excel'})
    return pd.DataFrame(out)


def _clave(nombre: str) -> str:
    k = W.clave_firma(nombre)
    return ALIAS.get(k, k)


def combinar(*fuentes: pd.DataFrame) -> pd.DataFrame:
    """Prioridad en el orden recibido. Misma encuesta = misma firma (con ALIAS) y fin a ≤ 7 días, o misma firma
    con las mismas cifras (±0.5) a ≤ 60 días (270toWin fecha por publicación). Nunca se fusionan firmas distintas
    solo por coincidir en cifras: GQR y GrayHouse publicaron ambas 49/45 con n = 600."""
    base = []
    for f in fuentes:
        for r in f.to_dict('records'):
            dup = False
            for b in base:
                dias = abs((pd.Timestamp(r['fin']) - pd.Timestamp(b['fin'])).days)
                mismas = abs(r['D'] - b['D']) <= 0.51 and abs(r['R'] - b['R']) <= 0.51
                if r['clave'] == b['clave'] and (dias <= 7 or (mismas and dias <= 60)):
                    dup = True
                    for c in ('n', 'pop', 'otros', 'indecisos'):       # completa datos que falten
                        if pd.isna(b.get(c)) and pd.notna(r.get(c)):
                            b[c] = r[c]
                    b.setdefault('tambien_en', set()).add(r['origen'])
                    break
            if not dup:
                base.append(dict(r))
    out = pd.DataFrame(base)
    out['tambien_en'] = out.get('tambien_en', pd.Series([None] * len(out))).map(
        lambda s: ', '.join(sorted(s)) if isinstance(s, set) else '')
    return out


def encuestas_2026(cfg: Config) -> pd.DataFrame:
    tx = json.loads((DATA / 'wikipedia_az_gob_2026-10-21.json').read_text(encoding='utf8'))['parse']['text']
    wiki = W.elegir_versiones(W.parse_tabla_wikipedia(tx, 'Hobbs', 'Biggs', 2026))
    t270 = W.elegir_versiones(W.parse_tabla_270((DATA / 't270_az_gob_2026-10-21.html').read_text(encoding='utf8'),
                                                'Hobbs', 'Biggs', 2026))
    exc = encuestas_excel(DATA / 'ARIZONA_GOBERNADOR-v1.xlsx')
    fuentes = []
    for f in (wiki, exc, t270):
        f = f.copy()
        f['clave'] = f.pollster.map(_clave)
        f['fin'] = pd.to_datetime(f.fin).dt.date
        f['inicio'] = pd.to_datetime(f.inicio).dt.date
        fuentes.append(f[['pollster', 'clave', 'inicio', 'fin', 'n', 'pop', 'D', 'R', 'otros', 'indecisos', 'origen']])
    p = combinar(*fuentes)
    p = p[(pd.to_datetime(p.fin) >= '2026-07-22') & (pd.to_datetime(p.fin) <= pd.Timestamp(cfg.corte))].copy()
    p['partidista'] = p.pollster.str.contains(r'\((?:R|D)\)')
    p['n'] = pd.to_numeric(p.n, errors='coerce').fillna(600).clip(100, 3000)
    p['days'] = (pd.Timestamp(cfg.eleccion) - pd.to_datetime(p.fin)).dt.days
    p['margin_poll'] = p.D - p.R
    p['pollster_key'] = p.clave
    p['fin'] = pd.to_datetime(p.fin)
    if p.duplicated(['pollster_key', 'fin']).any():
        raise ValueError('encuestas duplicadas tras combinar: ' + str(p[p.duplicated(['pollster_key', 'fin'], keep=False)].pollster.tolist()))
    return p.sort_values('fin').reset_index(drop=True)


def seleccionar_ventana(p: pd.DataFrame, cfg: Config, dias: int | None = None,
                        regla: str = 'desplazada') -> tuple[pd.DataFrame, dict]:
    """Encuestas que terminan en los últimos `dias` antes de la elección (21 = backtest).
    Si hay < min_encuestadoras: 'desplazada' = los 21 días anteriores a la encuesta más reciente (misma
    estructura que el backtest); 'v11' = la encuesta más reciente de cada firma (regla literal de Georgia)."""
    dias = dias or cfg.ventana_dias_eleccion
    lim = pd.Timestamp(cfg.eleccion) - pd.Timedelta(days=dias)
    q = p[p.fin >= lim]
    nota = {'ventana_desde': str(lim.date()), 'ampliada': False, 'regla': 'normal'}
    if q.pollster_key.nunique() < cfg.min_encuestadoras:
        if regla == 'v11':
            desde = p.groupby('pollster_key').fin.max().sort_values(ascending=False).head(cfg.min_encuestadoras).min()
        else:
            desde = p.fin.max() - pd.Timedelta(days=cfg.ventana_dias_eleccion)
        q = p[p.fin >= desde]
        nota.update({'ventana_desde': str(desde.date()), 'ampliada': True, 'regla': regla})
    return q, nota


# ================================================================================== mercados
def mercados(cfg: Config) -> dict:
    m = pd.read_csv(DATA / 'mercados_az_gob2026_diario.csv', parse_dates=['fecha'])
    m = m[m.fecha <= pd.Timestamp(cfg.corte)].iloc[-1]
    r = pd.read_csv(DATA / 'polymarket_margen_rangos_2026-10-21.csv')
    medio = np.where(np.isinf(r.desde), r.hasta - 3, np.where(np.isinf(r.hasta), r.desde + 3, (r.desde + r.hasta) / 2))
    media = float(np.sum(r.p_norm * medio))
    return {'fecha': str(m.fecha.date()), 'kalshi_D': float(m.kalshi), 'polymarket_D': float(m.polymarket),
            'promedio_D': float((m.kalshi + m.polymarket) / 2), 'dif_pp': float(100 * (m.kalshi - m.polymarket)),
            'polymarket_rangos_margen_media': media,
            'polymarket_rangos_margen_sd': float(np.sqrt(np.sum(r.p_norm * (medio - media) ** 2))),
            'polymarket_rangos_P_D': float(r[r.desde >= 0].p_norm.sum())}


# ================================================================================== voto anticipado (civicAPI)
CIVICAPI = 'https://civicapi.org/api/v2/early-vote'
DIR_CIVIC = DATA / 'civicapi'


def _tabla_civic(js: dict, categoria: str) -> pd.DataFrame:
    filas = [{'condado': c, 'partido': p, 'categoria': categoria, 'votos': int(v.get('votes', 0))}
             for c, partidos in (js.get('regions') or {}).items() for p, v in partidos.items()]
    return pd.DataFrame(filas)


def voto_anticipado_civicapi(cfg: Config) -> dict:
    """Boletas anticipadas solicitadas y devueltas por partido y condado (civicAPI, datos de las autoridades
    electorales; gratis, sin clave, con atribución). Solo diagnóstico: no entra al pronóstico.
    En vivo si cfg.civicapi_en_vivo; si falla, último snapshot guardado en datos/civicapi/ (≤ corte)."""
    DIR_CIVIC.mkdir(parents=True, exist_ok=True)
    estado, js = 'snapshot guardado', {}
    if cfg.civicapi_en_vivo:
        try:
            import requests
            for cat in ('returned', 'requested'):
                r = requests.get(f'{CIVICAPI}/AZ/{cat}', timeout=30, headers={'User-Agent': 'pronostico-elecciones/1.0'})
                r.raise_for_status()
                js[cat] = r.json()
                (DIR_CIVIC / f"AZ_{cat}_{js[cat]['snapshot_date']}.json").write_text(json.dumps(js[cat]), encoding='utf8')
            estado = 'en_vivo'
        except Exception as ex:                                    # nunca se finge un dato en vivo
            js, estado = {}, f'snapshot guardado ({type(ex).__name__}: {str(ex)[:80]})'
    if not js:
        for cat in ('returned', 'requested'):
            arch = sorted(f for f in DIR_CIVIC.glob(f'AZ_{cat}_*.json') if f.stem.split('_')[-1] <= str(cfg.corte))
            if not arch:
                return {'disponible': False, 'estado': 'sin datos de civicAPI'}
            js[cat] = json.loads(arch[-1].read_text(encoding='utf8'))
    t = pd.concat([_tabla_civic(js[c], c) for c in ('returned', 'requested')])
    t['partido'] = t.partido.where(t.partido.isin(['Democratic', 'Republican']), 'Otros')
    cond = t.pivot_table(index='condado', columns=['categoria', 'partido'], values='votos', aggfunc='sum', fill_value=0)
    cond.columns = [f'{c}_{p}' for c, p in cond.columns]
    tot = cond.sum()
    dev = {p: int(tot.get(f'returned_{p}', 0)) for p in ('Democratic', 'Republican', 'Otros')}
    sol = {p: int(tot.get(f'requested_{p}', 0)) for p in ('Democratic', 'Republican', 'Otros')}
    n_dev, n_sol = sum(dev.values()), sum(sol.values())
    res = {'disponible': True, 'estado': estado, 'fuente': 'civicAPI (civicapi.org), autoridades electorales de AZ',
           'fecha': js['returned']['snapshot_date'], 'devueltas': n_dev, 'solicitadas': n_sol,
           'pct_dev_D': 100 * dev['Democratic'] / n_dev, 'pct_dev_R': 100 * dev['Republican'] / n_dev,
           'pct_dev_otros': 100 * dev['Otros'] / n_dev,
           'margen_dev_DR_pp': 100 * (dev['Democratic'] - dev['Republican']) / n_dev,
           'tasa_dev_D': 100 * dev['Democratic'] / max(sol['Democratic'], 1),
           'tasa_dev_R': 100 * dev['Republican'] / max(sol['Republican'], 1),
           'tasa_dev_otros': 100 * dev['Otros'] / max(sol['Otros'], 1),
           'maricopa_pct_dev': float(100 * cond.filter(like='returned_').loc['Maricopa'].sum() / n_dev)}
    hist = DIR_CIVIC / 'historial_az.csv'                     # serie propia día a día (para comparar en 2028)
    h = pd.read_csv(hist) if hist.exists() else pd.DataFrame()
    fila = pd.DataFrame([{k: v for k, v in res.items() if k not in ('disponible', 'estado', 'fuente')}])
    h = pd.concat([h[h.get('fecha', pd.Series(dtype=str)) != res['fecha']] if len(h) else h, fila], ignore_index=True)
    h.sort_values('fecha').to_csv(hist, index=False)
    cond['devueltas'] = cond.filter(like='returned_').sum(axis=1)
    cond['margen_dev_DR_pp'] = 100 * (cond.get('returned_Democratic', 0) - cond.get('returned_Republican', 0)) / cond.devueltas.clip(lower=1)
    res['condados'] = cond.sort_values('devueltas', ascending=False).reset_index()
    res['historial'] = h
    return res


# ================================================================================== simulación
class Dist:
    def __init__(self, sd: float, nu: float | None):
        self.sd, self.nu = sd, nu
        self.sc = sd * np.sqrt((nu - 2) / nu) if nu else sd

    def cdf(self, x):
        return student_t.cdf(x / self.sc, self.nu) if self.nu else norm.cdf(x / self.sd)

    def rvs(self, mu, n, rng):
        return mu + (self.sc * rng.standard_t(self.nu, n) if self.nu else rng.normal(0, self.sd, n))


def simular(mu: float, dist: Dist, t_media: float, t_sd: float, cfg: Config, rng) -> pd.DataFrame:
    M = dist.rvs(mu, cfg.n_sim, rng)
    T = np.maximum(rng.normal(t_media, t_sd, cfg.n_sim), 0.1)
    return pd.DataFrame({'Hobbs': (100 - T + M) / 2, 'Biggs': (100 - T - M) / 2, 'Terceros': T, 'Margen': M})


def resumen(s: pd.DataFrame, nombre: str, p_final: float | None = None) -> dict:
    q = lambda c, x: float(s[c].quantile(x))
    p_mod = float((s.Margen > 0).mean())
    return {'escenario': nombre, 'margen_media': float(s.Margen.mean()), 'sd': float(s.Margen.std()),
            'IC80_margen': (q('Margen', .1), q('Margen', .9)), 'IC95_margen': (q('Margen', .025), q('Margen', .975)),
            'Hobbs': float(s.Hobbs.mean()), 'Hobbs_IC80': (q('Hobbs', .1), q('Hobbs', .9)),
            'Biggs': float(s.Biggs.mean()), 'Biggs_IC80': (q('Biggs', .1), q('Biggs', .9)),
            'Terceros': float(s.Terceros.mean()), 'Terceros_IC80': (q('Terceros', .1), q('Terceros', .9)),
            'P_Hobbs_modelo': p_mod, 'P_Hobbs': p_final if p_final is not None else p_mod,
            'P_recuento': float((s.Margen.abs() <= 0.5).mean()), 'P_Hobbs_>50': float((s.Hobbs > 50).mean())}


def ejecutar(cfg: Config | None = None, guardar: bool = True) -> dict:
    cfg = cfg or Config()
    rng = np.random.default_rng(cfg.semilla)
    p = encuestas_2026(cfg)
    q, nota = seleccionar_ventana(p, cfg)
    h_ef = int(np.clip(cfg.dias_a_eleccion, 0, 21))                 # horizonte calibrado (días a la elección)
    edad_extra = max((pd.Timestamp(cfg.eleccion) - q.fin.max()).days - h_ef, 0)   # encuestas más viejas que h
    var_deriva = cfg.sigma_dia_pp ** 2 * edad_extra
    par = calibrar(cfg, h_ef)
    house = par['efectos_casa']
    mu_enc, otros_enc, k, w = promedio(q, house, cfg.vida_media_dias)
    sesgo = par['sesgo_az_contraido'] if cfg.sesgo_estatal else 0.0
    mu = mu_enc - sesgo
    sd = float(np.sqrt(par['tau'] ** 2 + par['s'] ** 2 / max(k, 1) + var_deriva))
    dist = Dist(sd, par['nu'])
    a = par['terceros_a'] if cfg.terceros_a is None else cfg.terceros_a
    t_media = max(a + par['terceros_c'] * otros_enc, 0.1)
    mk = mercados(cfg)
    base = simular(mu, dist, t_media, par['terceros_sd'], cfg, rng)
    p_mod = float((base.Margen > 0).mean())
    p_final = p_mod if cfg.peso_mercados == 0 else float(expit(
        (1 - cfg.peso_mercados) * logit(np.clip(p_mod, 1e-4, 1 - 1e-4)) + cfg.peso_mercados * logit(mk['promedio_D'])))
    # la probabilidad mezclada se traslada a la distribución: se desplaza el margen simulado para que
    # P(margen > 0) = p_final; así margen, intervalos, % de voto y recuento son coherentes con la probabilidad
    desplaz = 0.0 if cfg.peso_mercados == 0 else float(-np.quantile(base.Margen, 1 - p_final))
    M_f = base.Margen + desplaz
    sim_final = pd.DataFrame({'Hobbs': (100 - base.Terceros + M_f) / 2, 'Biggs': (100 - base.Terceros - M_f) / 2,
                              'Terceros': base.Terceros, 'Margen': M_f})
    final = resumen(sim_final, 'FINAL: encuestas + mercados (Kalshi y Polymarket)')
    final.update({'P_Hobbs_modelo': p_mod, 'P_Hobbs_mezcla_objetivo': p_final, 'desplazamiento_mercados_pp': desplaz})

    esc = [final, resumen(base, 'Solo encuestas (sin mercados)')]
    sb = par['sesgo_az_contraido']
    esc.append(resumen(simular(mu_enc - sb, dist, t_media, par['terceros_sd'], cfg, rng),
                       f'Con sesgo estatal AZ (V11, {sb:+.2f} pp)'))
    esc.append(resumen(simular(mu, Dist(sd, None), t_media, par['terceros_sd'], cfg, rng), 'Distribución normal'))
    esc.append(resumen(simular(mu, dist, 0.1, 0.0, cfg, rng), 'Sin terceros (como Georgia)'))
    esc.append(resumen(simular(mu, Dist(float(np.sqrt(sd ** 2 - var_deriva)), par['nu']), t_media,
                               par['terceros_sd'], cfg, rng), 'Sin deriva por encuestas viejas'))
    for nom_v, kw in (('Regla literal V11 (última encuesta de cada firma)', {'regla': 'v11'}),
                      ('Ventana 45 días', {'dias': 45}), ('Ventana 60 días', {'dias': 60})):
        qq, _ = seleccionar_ventana(p, cfg, **kw)
        m2, o2, k2, _ = promedio(qq, house, cfg.vida_media_dias)
        ed2 = max((pd.Timestamp(cfg.eleccion) - qq.fin.max()).days - h_ef, 0)
        s2 = float(np.sqrt(par['tau'] ** 2 + par['s'] ** 2 / max(k2, 1) + cfg.sigma_dia_pp ** 2 * ed2))
        esc.append(resumen(simular(m2 - sesgo, Dist(s2, par['nu']), max(a + par['terceros_c'] * o2, .1),
                                   par['terceros_sd'], cfg, rng), f'{nom_v} ({k2} encuestadoras)'))
    sin_casa, *_ = promedio(q, {}, cfg.vida_media_dias)
    esc.append(resumen(simular(sin_casa - sesgo, dist, t_media, par['terceros_sd'], cfg, rng), 'Sin efectos de casa'))
    ep = efectos_partidistas(cfg.contraccion_casa)
    lado = q.pollster.map(lado_partidista)
    # firma con historia: su efecto de casa; sin historia: el efecto medio de su patrocinador (D o R)
    casa_part = {kk: house.get(kk, ep.get(ll, 0.0) if ll else 0.0) for kk, ll in zip(q.pollster_key, lado)}
    casa_solo = {kk: (ep.get(ll, 0.0) if ll else 0.0) for kk, ll in zip(q.pollster_key, lado)}
    for nom_p, mp in (('Ajuste partidista (patrocinador D/R)', casa_solo),
                      ('Efecto de casa + partidista si la firma no tiene historia', casa_part)):
        m_p, *_ = promedio(q, mp, cfg.vida_media_dias)
        esc.append(resumen(simular(m_p - sesgo, dist, t_media, par['terceros_sd'], cfg, rng),
                           f"{nom_p} [D {ep.get('D', 0):+.1f}, R {ep.get('R', 0):+.1f}]"))
    for nom, pm in (('Kalshi', mk['kalshi_D']), ('Polymarket', mk['polymarket_D'])):
        esc.append({'escenario': f'Solo {nom} (probabilidad)', 'P_Hobbs': pm,
                    'margen_media': float(dist.sc * student_t.ppf(pm, par['nu']))})
    esc.append({'escenario': 'Polymarket por rangos de margen', 'P_Hobbs': mk['polymarket_rangos_P_D'],
                'margen_media': mk['polymarket_rangos_margen_media'], 'sd': mk['polymarket_rangos_margen_sd']})

    tabla = q.assign(efecto_casa=q.pollster_key.map(house).fillna(0.0), peso=w.values,
                     patrocinador=lado.fillna('—'), efecto_partidista=lado.map(ep).fillna(0.0))
    tabla['margen_corregido'] = tabla.margin_poll - tabla.efecto_casa
    todas = p.assign(en_ventana=p.index.isin(q.index))
    diag = pd.read_csv(DATA / 'diagnostico_electorado_2026.csv')
    anticipado = voto_anticipado_civicapi(cfg)
    r = {'config': {k_: str(v) for k_, v in cfg.__dict__.items()}, 'ventana': nota, 'horizonte_calibrado': h_ef,
         'dias_extra_encuestas': edad_extra, 'var_deriva': var_deriva,
         'parametros': {k_: v for k_, v in par.items() if k_ not in ('efectos_casa', 'errores_az')},
         'margen_encuestas': mu_enc, 'otros_encuestas': otros_enc, 'k': k, 'mu': mu, 'sd': sd, 'nu': par['nu'],
         'terceros_media': t_media, 'mercados': mk, 'resultado': final,
         'escenarios': pd.DataFrame(esc), 'encuestas_ventana': tabla, 'encuestas_todas': todas,
         'errores_az': pd.DataFrame(par['errores_az']), 'diagnostico': diag, 'voto_anticipado': anticipado, 'simulacion': sim_final}
    if guardar:
        guardar_salidas(r, cfg)
    return r


def guardar_salidas(r: dict, cfg: Config) -> None:
    o = cfg.salida
    o.mkdir(parents=True, exist_ok=True)
    r['escenarios'].to_csv(o / 'resumen_escenarios.csv', index=False)
    r['encuestas_todas'].drop(columns=['pollster_key']).to_csv(o / 'encuestas_2026_combinadas.csv', index=False)
    r['encuestas_ventana'].to_csv(o / 'encuestas_ventana_pesos.csv', index=False)
    r['errores_az'].to_csv(o / 'errores_historicos_AZ.csv', index=False)
    va = r['voto_anticipado']
    if va.get('disponible'):
        va['condados'].to_csv(o / 'voto_anticipado_condados_civicapi.csv', index=False)
    f = r['resultado']
    pd.DataFrame([{'candidato': 'Katie Hobbs (D)', 'pct': f['Hobbs'], 'IC80': f['Hobbs_IC80'], 'P_ganar': f['P_Hobbs']},
                  {'candidato': 'Andy Biggs (R)', 'pct': f['Biggs'], 'IC80': f['Biggs_IC80'], 'P_ganar': 1 - f['P_Hobbs']},
                  {'candidato': 'Terceros (Hourihan, Lombardo, otros)', 'pct': f['Terceros'], 'IC80': f['Terceros_IC80'],
                   'P_ganar': 0.0}]).to_csv(o / 'pronostico_gobernador.csv', index=False)
    meta = {k: v for k, v in r.items() if k not in ('escenarios', 'encuestas_ventana', 'encuestas_todas',
                                                     'errores_az', 'diagnostico', 'simulacion', 'voto_anticipado')}
    meta['voto_anticipado'] = {k: v for k, v in r['voto_anticipado'].items() if k not in ('condados', 'historial')}
    (o / 'metadatos.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2, default=str), encoding='utf8')
