"""Georgia Gobernador 2026 · MODELO FINAL (v11) = lo mejor de v5–v10, validado por backtest.

Modelo seleccionado por backtest (leave-one-year-out, 980 contiendas 1998–2024, ver ../BACKTEST_GEORGIA).
Componentes y versión de origen (solo se conservaron los que mejoran el CRPS fuera de muestra):
  - promedio con recencia y 1 voto por firma ........ V8-M1 / V9 (vida media 14 d validada; 5 d no generaliza)
  - efectos de casa + sesgo estatal + sigma(k) ....... V10 (backtest)
  - colas Student-t (ν estimado) ..................... V8-M3 (P(mejor) 0.86 nacional / 0.84 GA)
  - tres categorías en reporte de encuestas .......... V6–V8 (Other/None separado; dos-opciones excluidas)
  - comparador de voto anticipado al mismo día ....... V5/M4-E: SOLO diagnóstico (empeora el RMSE en GA)
  - Kalshi ........................................... v10 (peso 0.30, no validado)
  - Senado (Ossoff–Collins) con correlación de errores Gob–Sen ρ=0.42 calibrada (simulación conjunta)
Revisión externa (20-oct): prior estructural lean+entorno EMPEORA el CRPS en gobernadores (3.655→3.705 con β
LOYO; 3.971 con β=0.20) -> solo sensibilidad documentada; composición por edad y volumen de anticipado:
no validable (2 comparaciones por tipo de ciclo) -> diagnóstico; gasto/autofinanciamiento: sin datos -> fuera.
Descartados por backtest: pesos 1/var (V8/V9), Kalman nivel local (V8-M2), shocks Poisson (V9),
reparto Beta de indecisos (V9), reponderación territorial M4-H (V5–V9, no validable y sesgada).

  margen_encuestas = promedio ponderado de (margen D−R − efecto de casa)
                     pesos: recencia (vida media 14 d) × sqrt(n), cada encuestadora pesa como una
  mu               = margen_encuestas − sesgo_GA        (sesgo estatal: solo ciclos pasados, vida media 4 años,
                                                         contracción bayes empírica)
  sigma            = sqrt(tau² + s²/k)                   (tau, s por MLE sobre errores históricos al mismo
                                                         horizonte; k = encuestadoras distintas)
  distribución     = Student-t con ν estimado (desv. estándar = sigma)
  Kalshi           = mezcla logit de probabilidades con peso PESO_KALSHI (no validado: ver LEEME)
  Indecisos        = 50/50 (el backtest descarta repartos sesgados dentro de este modelo)
  Otros            = solo write-ins (no hay terceros en boleta); segunda vuelta si nadie > 50 %

Uso:  import georgia_modelo_final as gm ; r = gm.ejecutar()
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import date
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from scipy.stats import norm, t as student_t
from scipy.special import logit, expit

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'datos'


@dataclass
class Config:
    corte: date = date(2026, 10, 20)
    eleccion: date = date(2026, 11, 3)
    peso_kalshi: float = 0.30            # 0 = solo encuestas
    kalshi_en_vivo: bool = False         # True intenta la API pública; si falla usa la caché fechada
    kalshi_max_dias: int = 3             # antigüedad máxima aceptada del precio
    sobreprecio_kalshi: float = 0.01     # suma D+R−1 típica; solo si falta el precio R
    ventana_dias_eleccion: int = 21      # ventana de encuestas = la usada en el backtest (últimos 21 días)
    min_encuestadoras: int = 2           # si hay menos, se amplía la ventana y se marca
    vida_media_dias: float = 14.0
    vida_media_sesgo_anios: float = 4.0
    contraccion_casa: float = 8.0
    writein_pp: tuple = (0.001, 0.02)    # rango de write-ins (pp); histórico GA: 0.002 %
    colas_t: bool = True                 # Student-t (v8-M3, validado); False = normal (v10)
    senado: bool = True                  # modela también Ossoff–Collins y la probabilidad conjunta
    rho_gob_sen: float = 0.42            # corr. de errores Gob–Sen mismo estado-año (120 pares 1998–2024, IC95 0.23–0.58)
    n_sim: int = 100_000
    semilla: int = 20261019
    salida: Path = field(default_factory=lambda: ROOT / 'salida')

    @property
    def dias_a_eleccion(self) -> int:
        return (pd.Timestamp(self.eleccion) - pd.Timestamp(self.corte)).days


# =============================================================================== histórico
NAT_PRES = {1996: 8.5, 2000: 0.5, 2004: -2.4, 2008: 7.3, 2012: 3.9, 2016: 2.1, 2020: 4.5, 2024: -1.5}


def cargar_historico() -> pd.DataFrame:
    d = pd.read_csv(DATA / 'fte_raw_polls_2023.csv')
    d = d[d.type_simple.isin(['Gov-G', 'Sen-G', 'Pres-G']) & (d.location != 'US')]
    d = d[(d.cand1_party == 'DEM') & (d.cand2_party == 'REP') & ((d.cand1_actual + d.cand2_actual) >= 85)].copy()
    d['runoff'] = d.race.str.contains('-GR_|-GSR_', regex=True)
    keep = ['race', 'year', 'location', 'type_simple', 'runoff', 'pollster', 'polldate', 'electiondate',
            'samplesize', 'cand1_pct', 'cand2_pct', 'cand1_actual', 'cand2_actual']
    d = d[keep].copy()
    d['polldate'] = pd.to_datetime(d.polldate, format='%m/%d/%Y')
    d['electiondate'] = pd.to_datetime(d.electiondate, format='%m/%d/%Y')
    g = pd.read_csv(DATA / 'ga_pres2024_polls.csv')
    g = g.assign(race='2024_Pres-G_GA', year=2024, location='GA', type_simple='Pres-G', runoff=False,
                 electiondate=pd.Timestamp('2024-11-05'), polldate=pd.to_datetime(g.polldate),
                 cand1_actual=48.53, cand2_actual=50.73)
    d = pd.concat([d, g[keep]], ignore_index=True)
    d['days'] = (d.electiondate - d.polldate).dt.days
    d['margin_poll'] = d.cand1_pct - d.cand2_pct
    d['margin_actual'] = d.cand1_actual - d.cand2_actual
    d['n'] = pd.to_numeric(d.samplesize, errors='coerce').fillna(600).clip(100, 3000)
    d['pollster_key'] = d.pollster.str.lower().str.replace(r'[^a-z]', '', regex=True).str[:14]
    return d


def efectos_casa(train: pd.DataFrame, k: float) -> dict:
    t = train.copy()
    t['dev'] = t.margin_poll - t.groupby('race').margin_poll.transform('mean')
    t = t[t.groupby('race').margin_poll.transform('size') >= 3]
    hp = t.groupby('pollster_key').dev.agg(['sum', 'size'])
    return (hp['sum'] / (hp['size'] + k)).to_dict()


def promedio(p: pd.DataFrame, house: dict, vida_media: float) -> tuple[float, int]:
    """Promedio ponderado de márgenes corregidos por efecto de casa. Devuelve (margen, k encuestadoras)."""
    if p.empty:
        return np.nan, 0
    m = p.margin_poll.to_numpy(float) - p.pollster_key.map(house).fillna(0).to_numpy(float)
    dt = (p.days - p.days.min()).to_numpy(float)
    w = np.exp(-np.log(2) * dt / vida_media) * np.sqrt(p.n.to_numpy(float))
    w = w / p.pollster_key.map(p.pollster_key.value_counts()).to_numpy(float)
    return float(np.sum(w * m) / np.sum(w)), int(p.pollster_key.nunique())


def ajustar_sigma(err, k) -> tuple[float, float]:
    """MLE en malla de var = tau² + s²/k."""
    taus = np.linspace(1.0, 8.0, 141)[:, None, None]
    ss = np.linspace(0.0, 12.0, 121)[None, :, None]
    v = taus ** 2 + ss ** 2 / np.maximum(np.asarray(k, float), 1)[None, None, :]
    ll = -0.5 * np.sum(np.log(v) + np.asarray(err, float)[None, None, :] ** 2 / v, axis=2)
    i, j = np.unravel_index(np.argmax(ll), ll.shape)
    return float(taus[i, 0, 0]), float(ss[0, j, 0])


def calibrar(cfg: Config, estado: str = 'GA', usar_cache: bool = True) -> dict:
    """Parámetros históricos al horizonte del corte. Se guardan en caché (dependen solo de datos y horizonte)."""
    h = int(np.clip(cfg.dias_a_eleccion, 0, 21))
    firma = hashlib.md5((DATA / 'fte_raw_polls_2023.csv').read_bytes()[:200000] +
                        (DATA / 'ga_pres2024_polls.csv').read_bytes()).hexdigest()[:10]
    clave = f'v11_h{h}_k{cfg.contraccion_casa}_vm{cfg.vida_media_dias}_vs{cfg.vida_media_sesgo_anios}_{firma}'
    cache = cfg.salida / 'cache' / f'calibracion_{clave}.json'
    if usar_cache and cache.exists():
        return json.loads(cache.read_text(encoding='utf8'))
    d = cargar_historico()
    years = sorted(d.year.unique())
    rows = []
    for y in years:                                  # errores fuera de muestra (casa sin el año)
        house = efectos_casa(d[d.year != y], cfg.contraccion_casa)
        for race, p in d[d.year == y].groupby('race'):
            mu, k = promedio(p[p.days >= h], house, cfg.vida_media_dias)
            if not np.isnan(mu):
                rows.append({'race': race, 'year': y, 'location': p.location.iloc[0], 'k': k,
                             'e': mu - float(p.margin_actual.iloc[0])})
    b = pd.DataFrame(rows)
    tau, s = ajustar_sigma(b.e, b.k)
    z = b.e / np.sqrt(tau ** 2 + s ** 2 / np.maximum(b.k, 1))      # errores estandarizados -> ν por MLE
    nus = np.linspace(2.5, 60, 576)
    nu = float(nus[int(np.argmax([np.sum(student_t.logpdf(z, v_, scale=np.sqrt((v_ - 2) / v_))) for v_ in nus]))])
    yr_obj = pd.Timestamp(cfg.eleccion).year
    b['w'] = 0.5 ** ((yr_obj - b.year) / cfg.vida_media_sesgo_anios)
    st = b.groupby('location').apply(lambda g: pd.Series({
        'm': np.average(g.e, weights=g.w), 'neff': g.w.sum() ** 2 / (g.w ** 2).sum(),
        'v': g.e.var() if len(g) > 1 else np.nan}), include_groups=False)
    st = st[st.neff >= 1.5]
    var_estados = max(float(st.m.var()) - float(np.nanmean(st.v / st.neff)), 0.0)
    r = st.loc[estado]
    contr = var_estados / (var_estados + r.v / r.neff) if var_estados > 0 else 0.0
    par = {'horizonte_dias': h, 'horizonte_recortado': cfg.dias_a_eleccion > 21,
           'tau': tau, 's': s, 'nu': nu, 'n_contiendas': len(b), 'sesgo_estado_bruto': float(r.m),
           'contraccion_sesgo': float(contr), 'sesgo_estado': float(contr * r.m),
           'var_entre_estados': var_estados,
           'efectos_casa': efectos_casa(d, cfg.contraccion_casa),
           'errores_estado': b[b.location == estado].drop(columns='w').to_dict('records')}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(par, ensure_ascii=False), encoding='utf8')
    return par


# ================================================================================== 2026
COLUMNAS_ENCUESTAS = ['pollster', 'clave_538', 'inicio', 'fin', 'n', 'pop', 'D', 'R', 'tipo_pregunta', 'fuente']
TIPOS_PREGUNTA = {'general', 'dos_opciones', 'reasignacion'}


def validar_encuestas(p: pd.DataFrame) -> list[str]:
    """Revisa el CSV de encuestas antes de usarlo. Errores -> excepción; avisos -> lista devuelta."""
    err, avisos = [], []
    falt = [c for c in COLUMNAS_ENCUESTAS if c not in p.columns]
    if falt:
        raise ValueError(f'Faltan columnas en ga_gob2026_encuestas.csv: {falt}')
    for c in ['pollster', 'clave_538', 'inicio', 'fin', 'n', 'pop', 'D', 'R', 'tipo_pregunta', 'fuente']:
        vac = p[p[c].isna() | (p[c].astype(str).str.strip() == '')]
        if len(vac):
            err.append(f'{c} vacío en filas {list(vac.index)}')
    ini, fin = pd.to_datetime(p.inicio, errors='coerce'), pd.to_datetime(p.fin, errors='coerce')
    if ini.isna().any() or fin.isna().any():
        err.append('fechas inválidas (usar AAAA-MM-DD)')
    elif (fin < ini).any():
        err.append(f'fin anterior a inicio en filas {list(p.index[fin < ini])}')
    D, R, n = (pd.to_numeric(p[c], errors='coerce') for c in ('D', 'R', 'n'))
    if D.isna().any() or R.isna().any() or n.isna().any():
        err.append('D, R o n no numéricos')
    else:
        if ((D + R) > 100.5).any() or (D < 0).any() or (R < 0).any():
            err.append(f'D+R > 100 o negativos en filas {list(p.index[(D + R) > 100.5])}')
        if (n < 100).any():
            avisos.append(f'muestras < 100 en filas {list(p.index[n < 100])}')
        sin_u = p.index[((D + R) >= 99.5) & p.tipo_pregunta.eq('general')]
        if len(sin_u):
            avisos.append(f'filas {list(sin_u)} suman ~100 con tipo "general": ¿son de dos opciones o reasignadas?')
    malos = set(p.tipo_pregunta.astype(str)) - TIPOS_PREGUNTA
    if malos:
        err.append(f'tipo_pregunta no válido {malos}; usar {sorted(TIPOS_PREGUNTA)}')
    if not p.clave_538.astype(str).str.fullmatch(r'[a-z]{1,14}').all():
        err.append('clave_538 debe ser minúsculas sin espacios, máx. 14 letras (como en FiveThirtyEight)')
    if not p['pop'].isin(['LV', 'RV', 'A']).all():
        err.append('pop debe ser LV, RV o A')
    dup = p[p.duplicated(['clave_538', 'fin'], keep=False)]
    if len(dup):
        err.append(f'encuesta duplicada (misma firma y fecha) en filas {list(dup.index)}; deja una sola versión (preferir LV)')
    if err:
        raise ValueError('CSV de encuestas con errores:\n - ' + '\n - '.join(err))
    return avisos


def encuestas_actuales(cfg: Config, archivo: str = 'ga_gob2026_encuestas.csv') -> pd.DataFrame:
    crudo = pd.read_csv(DATA / archivo)
    avisos = validar_encuestas(crudo)
    p = crudo.assign(inicio=pd.to_datetime(crudo.inicio), fin=pd.to_datetime(crudo.fin))
    p.attrs['avisos_validacion'] = avisos
    futuras = p[p.fin > pd.Timestamp(cfg.corte)]
    p = p[p.fin <= pd.Timestamp(cfg.corte)].copy()
    p.attrs['excluidas_posteriores_al_corte'] = len(futuras)
    p.attrs['avisos_validacion'] = avisos
    p['days'] = (pd.Timestamp(cfg.eleccion) - p.fin).dt.days
    p['margin_poll'] = p.D - p.R
    p['n'] = p.n.clip(100, 3000)
    p['pollster_key'] = p.clave_538
    return p.sort_values('fin').reset_index(drop=True)


def seleccionar_ventana(p: pd.DataFrame, cfg: Config) -> tuple[pd.DataFrame, dict]:
    lim = pd.Timestamp(cfg.eleccion) - pd.Timedelta(days=cfg.ventana_dias_eleccion)
    q = p[p.fin >= lim]
    nota = {'ventana_desde': str(lim.date()), 'ampliada': False}
    if q.pollster_key.nunique() < cfg.min_encuestadoras:      # fallback explícito
        ultima = p.groupby('pollster_key').fin.max().sort_values(ascending=False)   # encuesta más reciente por firma
        desde = ultima.head(cfg.min_encuestadoras).min()
        q = p[p.fin >= desde]
        nota.update({'ventana_desde': str(desde.date()), 'ampliada': True})
    return q, nota


def kalshi(cfg: Config) -> dict:
    """Probabilidad normalizada de Bottoms (D). En vivo opcional; si no, caché fechada."""
    corte = pd.Timestamp(cfg.corte)
    if cfg.kalshi_en_vivo:
        try:
            import requests
            js = requests.get('https://api.elections.kalshi.com/trade-api/v2/markets',
                              params={'event_ticker': 'GOVPARTYGA-26'}, timeout=10).json()
            mk = {m['ticker']: m for m in js['markets']}
            mid = lambda m: (float(m['yes_bid_dollars']) + float(m['yes_ask_dollars'])) / 2
            d, r = mid(mk['GOVPARTYGA-26-D']), mid(mk['GOVPARTYGA-26-R'])
            hoy = pd.Timestamp.now(tz='UTC').normalize().tz_localize(None)
            fila = pd.DataFrame([{'date_utc': hoy.date(), 'yes_bid_close': mk['GOVPARTYGA-26-D']['yes_bid_dollars'],
                                  'yes_ask_close': mk['GOVPARTYGA-26-D']['yes_ask_dollars'], 'price_close': np.nan,
                                  'volume': np.nan, 'mid_R': r}])
            ruta = DATA / 'kalshi_GOVPARTYGA-26-D_diario.csv'
            h = pd.read_csv(ruta)
            pd.concat([h[h.date_utc != str(hoy.date())], fila]).to_csv(ruta, index=False)
            return {'p_D': d / (d + r), 'fecha': str(hoy.date()), 'fuente': 'API en vivo', 'mid_D': d, 'mid_R': r,
                    'usable': (hoy - corte).days <= 1}
        except Exception as ex:                           # nunca se finge un dato en vivo
            err = f'{type(ex).__name__}: {ex}'
    else:
        err = 'consulta en vivo desactivada'
    k = pd.read_csv(DATA / 'kalshi_GOVPARTYGA-26-D_diario.csv', parse_dates=['date_utc'])
    k = k[k.date_utc <= corte + pd.Timedelta(days=1)]          # tolera el día siguiente (UTC) al corte
    if k.empty:
        return {'usable': False, 'fuente': 'sin datos', 'nota': err}
    h = k.iloc[-1]
    d = (float(h.yes_bid_close) + float(h.yes_ask_close)) / 2
    r = float(h.mid_R) if 'mid_R' in k and pd.notna(h.get('mid_R')) else 1 - d + cfg.sobreprecio_kalshi
    edad = (corte - h.date_utc).days
    return {'p_D': d / (d + r), 'fecha': str(h.date_utc.date()), 'fuente': f'caché ({err})', 'mid_D': d,
            'mid_R': r, 'usable': -1 <= edad <= cfg.kalshi_max_dias, 'antiguedad_dias': edad}


class Dist:
    """Normal o Student-t con desviación estándar sd (la escala t se ajusta para que var = sd²)."""
    def __init__(self, sd: float, nu: float | None):
        self.sd, self.nu = sd, nu
        self.sc = sd * np.sqrt((nu - 2) / nu) if nu else sd
    def cdf(self, x): return student_t.cdf(x / self.sc, self.nu) if self.nu else norm.cdf(x / self.sd)
    def ppf(self, p): return self.sc * student_t.ppf(p, self.nu) if self.nu else self.sd * norm.ppf(p)
    def rvs(self, mu, n, rng): return mu + (self.sc * rng.standard_t(self.nu, n) if self.nu else rng.normal(0, self.sd, n))


def simular(mu: float, dist: 'Dist', cfg: Config, rng) -> pd.DataFrame:
    M = dist.rvs(mu, cfg.n_sim, rng)
    W = rng.uniform(*cfg.writein_pp, cfg.n_sim)
    B = (100 - W + M) / 2; J = (100 - W - M) / 2
    return pd.DataFrame({'Bottoms': B, 'Jackson': J, 'Writein': W, 'Margen_B_J': M,
                         'Gana_Bottoms': B > J, 'Segunda_vuelta': (B <= 50) & (J <= 50)})


def resumen(s: pd.DataFrame, nombre: str) -> dict:
    q = lambda c, x: float(s[c].quantile(x))
    return {'escenario': nombre, 'margen_media': float(s.Margen_B_J.mean()), 'sd': float(s.Margen_B_J.std()),
            'IC80': (q('Margen_B_J', .1), q('Margen_B_J', .9)), 'IC95': (q('Margen_B_J', .025), q('Margen_B_J', .975)),
            'Bottoms_media': float(s.Bottoms.mean()), 'Jackson_media': float(s.Jackson.mean()),
            'P_Bottoms': float(s.Gana_Bottoms.mean()), 'P_Jackson': float(1 - s.Gana_Bottoms.mean()),
            'P_segunda_vuelta': float(s.Segunda_vuelta.mean()),
            'P_Bottoms_>50': float((s.Bottoms > 50).mean()), 'P_Jackson_>50': float((s.Jackson > 50).mean())}


def tres_categorias(q: pd.DataFrame, cfg: Config) -> dict:
    """Reporte v6–v8: Bottoms / Jackson / Other-None EN ENCUESTAS (no voto). Las preguntas de dos opciones o con
    indecisos reasignados se excluyen del cálculo del residual (su 0 % no es evidencia de cero indecisos)."""
    g = q[q.tipo_pregunta.astype(str).str.lower().eq('general')]
    if g.empty:
        return {'n_encuestas': 0}
    dt = (g.days - g.days.min()).to_numpy(float)
    w = np.exp(-np.log(2) * dt / cfg.vida_media_dias) * np.sqrt(g.n.to_numpy(float))
    w = w / g.pollster_key.map(g.pollster_key.value_counts()).to_numpy(float); w = w / w.sum()
    D_, R_ = float(w @ g.D), float(w @ g.R)
    return {'n_encuestas': int(len(g)), 'Bottoms_encuesta': D_, 'Jackson_encuesta': R_, 'Otros_ninguno_indecisos': 100 - D_ - R_,
            'nota': 'Porcentajes de respuesta; el residual se reparte 50/50 en el pronóstico (validado) y no hay terceros en boleta.'}


def voto_anticipado_diagnostico(cfg: Config, en_vivo: bool = False) -> dict:
    """Comparador M4-E (v5) con Civic Forge: % negro de boletas aceptadas al mismo número de días antes de la
    elección. SOLO DIAGNÓSTICO: en el backtest GA 2018–2024 corregir con esta señal empeora el RMSE (2.94 vs 1.63)."""
    cf = pd.read_csv(DATA / 'civicforge_raza_T15.csv')
    nota = 'caché'
    if en_vivo:
        try:
            import requests
            js = requests.get('https://www.civicforge.solutions/api/ga-2026-general/crosstab',
                              params={'groupBy': 'race', 'compact': 1}, timeout=15).json()
            nota = 'API en vivo (revisa que las claves del JSON coincidan con la caché)'
            # Formato de la API: se guarda tal cual para auditoría; no se usa en el pronóstico.
            (cfg.salida / 'civicforge_crosstab_raza_vivo.json').write_text(json.dumps(js)[:200000], encoding='utf8')
        except Exception as ex:
            nota = f'caché ({type(ex).__name__})'
    cols = ['ASIAN', 'BLACK', 'HISPANIC', 'NA', 'OTHER', 'WHITE']
    cf['total'] = cf[cols].sum(axis=1)
    cf['negro_pct'] = 100 * cf.BLACK / cf.total
    cf['blanco_pct'] = 100 * cf.WHITE / cf.total
    ref = cf.set_index('anio')
    act = int(pd.Timestamp(cfg.eleccion).year)
    out = cf[['anio', 'fecha_matched', 'dias_eleccion', 'total', 'negro_pct', 'blanco_pct']].copy()
    if act in ref.index and 2022 in ref.index:
        out.attrs['delta_negro_vs_2022'] = float(ref.loc[act, 'negro_pct'] - ref.loc[2022, 'negro_pct'])
    out.attrs['nota'] = nota
    return {'tabla': out, 'delta_negro_vs_2022': out.attrs.get('delta_negro_vs_2022'), 'fuente': nota,
            'uso': 'diagnóstico; no entra al pronóstico'}


def senado_y_conjunto(cfg: Config, par: dict, mu_gob: float, D_gob: 'Dist') -> dict:
    """Ossoff (D) – Collins (R) con el mismo método (casa + sesgo GA + sigma(k) + t) y simulación conjunta con el
    gobernador: t bivariada (normales correlacionadas con ρ y el mismo factor chi² para ambas carreras)."""
    ps = encuestas_actuales(cfg, 'ga_sen2026_encuestas.csv')
    ps['efecto_casa'] = ps.pollster_key.map(par['efectos_casa']).fillna(0.0)
    ps['margen_corregido'] = ps.margin_poll - ps.efecto_casa
    qs, nota = seleccionar_ventana(ps, cfg)
    ms, ks = promedio(qs, par['efectos_casa'], cfg.vida_media_dias)
    mus = ms - par['sesgo_estado']
    Ds = Dist(float(np.sqrt(par['tau'] ** 2 + par['s'] ** 2 / max(ks, 1))), D_gob.nu)
    rng = np.random.default_rng(cfg.semilla + 7)
    n, rho = cfg.n_sim, cfg.rho_gob_sen
    z1 = rng.standard_normal(n); z2 = rho * z1 + np.sqrt(1 - rho ** 2) * rng.standard_normal(n)
    esc = np.sqrt(rng.chisquare(D_gob.nu, n) / D_gob.nu) if D_gob.nu else np.ones(n)
    Mg = mu_gob + D_gob.sc * z1 / esc
    Ms = mus + Ds.sc * z2 / esc
    B, O = Mg > 0, Ms > 0
    conj = {'P_Ossoff': float(O.mean()), 'P_Bottoms': float(B.mean()),
            'P_Bottoms_y_Ossoff': float((B & O).mean()), 'P_Jackson_y_Ossoff': float((~B & O).mean()),
            'P_Bottoms_y_Collins': float((B & ~O).mean()), 'P_Jackson_y_Collins': float((~B & ~O).mean()),
            'P_Bottoms_si_gana_Ossoff': float(B[O].mean()) if O.any() else np.nan,
            'P_Bottoms_si_gana_Collins': float(B[~O].mean()) if (~O).any() else np.nan,
            'P_Ossoff_si_gana_Bottoms': float(O[B].mean()) if B.any() else np.nan,
            'P_division_de_voto': float((B != O).mean()), 'rho': rho,
            'corr_simulada': float(np.corrcoef(Mg, Ms)[0, 1])}
    sen = {'margen_promedio_corregido': ms, 'mu': mus, 'sd': Ds.sd, 'k': ks, 'ventana': nota,
           'encuestas_en_ventana': int(len(qs)), 'P_Ossoff': float(Ds.cdf(mus)),
           'IC80': (float(mus + Ds.ppf(.1)), float(mus + Ds.ppf(.9))),
           'avisos_validacion': ps.attrs.get('avisos_validacion', [])}
    return {'senado': sen, 'conjunto': conj, 'encuestas_senado': ps}


def ejecutar(cfg: Config | None = None, guardar: bool = True) -> dict:
    cfg = cfg or Config()
    cfg.salida.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(cfg.semilla)
    par = calibrar(cfg)
    p = encuestas_actuales(cfg)
    p['efecto_casa'] = p.pollster_key.map(par['efectos_casa']).fillna(0.0)
    p['margen_corregido'] = p.margin_poll - p.efecto_casa
    q, nota_ventana = seleccionar_ventana(p, cfg)
    m_enc, k = promedio(q, par['efectos_casa'], cfg.vida_media_dias)
    mu_enc = m_enc - par['sesgo_estado']
    sd = float(np.sqrt(par['tau'] ** 2 + par['s'] ** 2 / max(k, 1)))
    nu = par['nu'] if cfg.colas_t else None
    D = Dist(sd, nu)
    p_enc = float(D.cdf(mu_enc))
    kal = kalshi(cfg)
    w = cfg.peso_kalshi if kal.get('usable') else 0.0
    p_fin = float(expit((1 - w) * logit(p_enc) + w * logit(kal['p_D']))) if w > 0 else p_enc
    mu_fin = float(D.ppf(p_fin))                   # margen equivalente con la misma incertidumbre
    sims = simular(mu_fin, D, cfg, rng)
    tabla = [resumen(sims, 'FINAL: encuestas + Kalshi' if w > 0 else 'FINAL: encuestas')]
    # sensibilidades (mismas reglas, una pieza distinta cada vez)
    sens = {'Solo encuestas (sin Kalshi)': (mu_enc, D),
            'Distribución normal (= v10)': (sd * norm.ppf(expit((1 - w) * logit(norm.cdf(mu_enc / sd)) + w * logit(kal['p_D'])))
                                            if w > 0 else mu_enc, Dist(sd, None)),
            'Sin sesgo estatal GA': (m_enc, D),
            'Sin efectos de casa': (promedio(q, {}, cfg.vida_media_dias)[0] - par['sesgo_estado'], D)}
    for dias in (30, 45):
        qq = p[p.fin >= pd.Timestamp(cfg.corte) - pd.Timedelta(days=dias)]
        mm, kk = promedio(qq, par['efectos_casa'], cfg.vida_media_dias)
        sens[f'Ventana {dias} días'] = (mm - par['sesgo_estado'], Dist(float(np.sqrt(par['tau'] ** 2 + par['s'] ** 2 / kk)), nu))
    if kal.get('p_D') is not None:
        sens['Kalshi solo'] = (float(D.ppf(kal['p_D'])), D)
    for nombre, (m_, s_) in sens.items():
        tabla.append(resumen(simular(m_, s_, cfg, np.random.default_rng(cfg.semilla)), nombre))
    T = pd.DataFrame(tabla)
    SC = senado_y_conjunto(cfg, par, mu_fin, D) if cfg.senado else None
    meta = {'config': {k_: (str(v) if isinstance(v, (date, Path)) else v) for k_, v in asdict(cfg).items()},
            'calibracion': {k_: v for k_, v in par.items() if k_ not in ('efectos_casa', 'errores_estado')},
            'ventana': nota_ventana, 'encuestas_en_ventana': int(len(q)), 'k_encuestadoras': k,
            'encuestas_excluidas_posteriores_al_corte': p.attrs.get('excluidas_posteriores_al_corte', 0),
            'avisos_validacion_encuestas': p.attrs.get('avisos_validacion', []),
            'margen_promedio_corregido': m_enc, 'mu_encuestas': mu_enc, 'sd': sd, 'nu': nu, 'p_encuestas': p_enc,
            'tres_categorias_encuestas': tres_categorias(q, cfg),
            'senado': (SC['senado'] if SC else None), 'conjunto_gob_sen': (SC['conjunto'] if SC else None),
            'kalshi': kal, 'peso_kalshi_aplicado': w, 'p_final': p_fin, 'mu_final': mu_fin,
            'nota': 'Pronóstico probabilístico calibrado con backtest LOYO; peso de Kalshi no validado.'}
    if guardar:
        o = cfg.salida
        T.to_csv(o / 'resumen_escenarios.csv', index=False)
        p.to_csv(o / 'encuestas_corregidas.csv', index=False)
        pd.DataFrame([meta['tres_categorias_encuestas']]).to_csv(o / 'tres_categorias_encuestas.csv', index=False)
        if SC:
            pd.DataFrame([{**{f'sen_{k_}': v for k_, v in SC['senado'].items() if k_ not in ('ventana', 'avisos_validacion')},
                           **SC['conjunto']}]).to_csv(o / 'senado_y_conjunto.csv', index=False)
            SC['encuestas_senado'].to_csv(o / 'encuestas_senado_corregidas.csv', index=False)
        sims.sample(min(20000, len(sims)), random_state=1).to_csv(o / 'simulaciones_muestra.csv', index=False)
        pd.DataFrame(par['errores_estado']).to_csv(o / 'errores_historicos_GA.csv', index=False)
        (o / 'metadatos.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2, default=str), encoding='utf8')
        hist = o / 'historial_pronosticos.csv'
        fila = pd.DataFrame([{'corte': str(cfg.corte), 'mu_final': mu_fin, 'sd': sd, 'nu': nu, 'p_final': p_fin,
                              'p_encuestas': p_enc, 'p_kalshi': kal.get('p_D'), 'peso_kalshi': w, 'k': k,
                              'ejecutado': pd.Timestamp.now().isoformat(timespec='seconds')}])
        if hist.exists():
            h = pd.read_csv(hist); fila = pd.concat([h[h.corte != str(cfg.corte)], fila])
        fila.to_csv(hist, index=False)
    return {'resumen': T, 'encuestas': p, 'ventana': q, 'simulaciones': sims, 'meta': meta, 'calibracion': par,
            'tres_categorias': meta['tres_categorias_encuestas'], 'senado': SC}


if __name__ == '__main__':
    r = ejecutar()
    pd.set_option('display.width', 200)
    print(r['resumen'][['escenario', 'margen_media', 'sd', 'P_Bottoms', 'P_segunda_vuelta']].round(3).to_string(index=False))
