"""
ODISEO · California · Backtesting de M1–M4 + Kalshi
===================================================
Ejecutar:  python backtest_california.py  (desde la carpeta que contiene data/ y el Excel)

Bloques
  A. Elecciones generales estatales 2018–2025 (6 contiendas): error del agregado M1 y
     calibración de sigma (M1 vs M3 vs sigma empírica LOO) con CRPS, log-score y cobertura.
  B. Primaria top-two 2026 (y 2018 / Senado 2024 como entrenamiento): agregado multicandidato,
     probabilidad de avanzar, comparación con Kalshi; señal de participación M2 (proxy actual).
  C. Conteo post-electoral de la primaria 2026 ("espejismo rojo") y reacción de Kalshi.
  D. Kalshi en la general 2026: margen implícito / sigma implícita.

Ninguna cifra de este script está ajustada a mano al resultado: los parámetros que se
calibran (sigma) se estiman leave-one-out o con elecciones anteriores a la evaluada.
"""
from __future__ import annotations
import re, json, unicodedata
from pathlib import Path
from datetime import date, timedelta

import numpy as np
import pandas as pd
from scipy import stats

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
OUT = BASE / "salida_backtest"
OUT.mkdir(exist_ok=True)
EXCEL = next((p for p in (BASE / "CALIFORNIA_GOBERNADOR-v3.xlsx",
                          BASE.parent / "CALIFORNIA_2026_NOTEBOOK_COMPLETO" / "CALIFORNIA_GOBERNADOR-v3.xlsx")
              if p.exists()), BASE / "CALIFORNIA_GOBERNADOR-v3.xlsx")
RNG = np.random.default_rng(20261019)

# --------------------------------------------------------------------------------------
# Utilidades de agregación (misma lógica que el notebook + variante mejorada)
# --------------------------------------------------------------------------------------
PARTIDISTA = re.compile(r"\((?:D|R)\)|campa", re.I)


def familia(nombre: str) -> str:
    n = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode().lower()
    for k, v in [("berkeley", "Berkeley IGS"), ("ppic", "PPIC"), ("emerson", "Emerson"),
                 ("surveyusa", "SurveyUSA"), ("thomas partners", "Thomas Partners"),
                 ("activote", "ActiVote"), ("research co", "Research Co."),
                 ("evitarus", "Evitarus"), ("binder", "Binder"), ("kreate", "Kreate"),
                 ("gsg", "GSG"), ("gudelunas", "Gudelunas"), ("impact", "Impact"),
                 ("emc", "EMC"), ("ivp", "IVP"), ("tavern", "Tavern"), ("yougov", "YouGov"),
                 ("competitive edge", "Competitive Edge"), ("cepp", "CEPP"), ("ppp", "PPP")]:
        if k in n:
            return v
    return nombre.strip()


def pesos(df: pd.DataFrame, corte: pd.Timestamp, variante: str, vida_media=30.0) -> np.ndarray:
    medio = df["inicio"] + (df["fin"] - df["inicio"]) / 2
    dias = (corte - medio).dt.days.clip(lower=0).to_numpy(float)
    w = np.exp(-np.log(2) * dias / vida_media)
    if variante == "mejorado":
        nn = df["n"].fillna(600).clip(200, 3000).to_numpy(float)
        w *= np.sqrt(nn / 600.0)                                   # tamaño de muestra (acotado)
        w *= np.where(df["encuestadora"].str.contains(PARTIDISTA), 0.5, 1.0)  # partidistas
        fam = df["encuestadora"].map(familia)
        w /= np.sqrt(fam.map(fam.value_counts()).to_numpy(float))  # cada casa ≈ un voto
    return w / w.sum()


# --------------------------------------------------------------------------------------
# Métricas de pronóstico probabilístico
# --------------------------------------------------------------------------------------

def crps_normal(y, mu, s):
    z = (y - mu) / s
    return s * (z * (2 * stats.norm.cdf(z) - 1) + 2 * stats.norm.pdf(z) - 1 / np.sqrt(np.pi))


def logscore_normal(y, mu, s):
    return -stats.norm.logpdf(y, mu, s)


def brier(p, o):
    return float(np.mean((np.asarray(p) - np.asarray(o)) ** 2))


def logloss(p, o):
    p = np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4)
    o = np.asarray(o, float)
    return float(-np.mean(o * np.log(p) + (1 - o) * np.log(1 - p)))


# ======================================================================================
# A. GENERALES
# ======================================================================================

def bloque_a():
    enc = pd.read_csv(DATA / "generales_encuestas.csv", parse_dates=["inicio", "fin"])
    res = pd.read_csv(DATA / "generales_resultados.csv", parse_dates=["fecha_eleccion"])
    res["margen_real_2p"] = 100 * (res.d_pct - res.r_pct) / (res.d_pct + res.r_pct)
    enc["margen_2p"] = 100 * (enc.d_pct - enc.r_pct) / (enc.d_pct + enc.r_pct)

    filas = []
    for _, r in res.iterrows():
        e = enc[enc.eleccion == r.eleccion]
        for dias_antes in (21, 14, 7, 0):
            corte = r.fecha_eleccion - pd.Timedelta(days=dias_antes)
            sub = e[e.fin <= corte]
            if len(sub) < 2:
                continue
            for var in ("notebook", "mejorado"):
                w = pesos(sub, corte, var)
                mu = float(np.dot(w, sub.margen_2p))
                disp = float(np.sqrt(np.dot(w, (sub.margen_2p - mu) ** 2)))
                filas.append(dict(eleccion=r.eleccion, ciclo=r.ciclo, presidente=r.presidente_partido,
                                  dias_antes=dias_antes, variante=var, n_encuestas=len(sub),
                                  n_efectivo=1 / np.sum(w ** 2), margen_agregado=mu,
                                  dispersion=disp, margen_real=r.margen_real_2p,
                                  error=r.margen_real_2p - mu))
    t = pd.DataFrame(filas)
    t.to_csv(OUT / "A_generales_errores.csv", index=False, encoding="utf-8-sig")

    # --- calibración de sigma LOO sobre el corte T-14 (equivale a hoy: 15 días) ---
    base = t[(t.dias_antes == 14)].copy()
    puntajes = []
    for var in ("notebook", "mejorado"):
        b = base[base.variante == var].reset_index(drop=True)
        for i, r in b.iterrows():
            otros = b.drop(i)
            sigma_loo = float(np.sqrt(np.mean(otros.error ** 2)))       # RMSE de las demás
            lam = 0.15 * 14 / 7
            sig_m3 = np.sqrt(4.5 ** 2 + lam * 3.0 ** 2)                 # M3 del notebook
            sig_m4 = np.sqrt(4.5 ** 2 + 1.42 * lam * 3.0 ** 2)          # M4 con multiplicador 1.42
            for nombre, s in (("M1 sigma=4.5", 4.5), ("M3 shocks", sig_m3), ("M4 sentimiento", sig_m4),
                              ("sigma empirica LOO", sigma_loo)):
                puntajes.append(dict(variante=var, eleccion=r.eleccion, modelo=nombre, sigma=s,
                                     crps=crps_normal(r.margen_real, r.margen_agregado, s),
                                     logscore=logscore_normal(r.margen_real, r.margen_agregado, s),
                                     dentro_80=abs(r.error) <= 1.2816 * s,
                                     dentro_95=abs(r.error) <= 1.96 * s))
    p = pd.DataFrame(puntajes)
    resumen = (p.groupby(["variante", "modelo"])
                 .agg(sigma_media=("sigma", "mean"), CRPS=("crps", "mean"), LogScore=("logscore", "mean"),
                      cobertura_80=("dentro_80", "mean"), cobertura_95=("dentro_95", "mean"))
                 .reset_index().sort_values(["variante", "CRPS"]))
    resumen.to_csv(OUT / "A_calibracion_sigma.csv", index=False, encoding="utf-8-sig")
    return t, resumen


# ======================================================================================
# B. PRIMARIAS
# ======================================================================================
MESES = dict(ene=1, feb=2, mar=3, abr=4, may=5, jun=6, jul=7, ago=8, sep=9, oct=10, nov=11, dic=12)


def parse_rango_es(txt: str):
    """'27–28 may 2026' | '26 mar–03 abr 2026' | '30 nov–07 dic 2025'."""
    t = str(txt).lower().replace("–", "-").replace("—", "-").strip()
    anio = int(re.search(r"(20\d\d)", t).group(1))
    t = re.sub(r"\s*20\d\d", "", t)
    a, b = [x.strip() for x in t.split("-")]
    db, mb = b.split()
    da = a.split()
    ma = da[1] if len(da) > 1 else mb
    fin = date(anio, MESES[mb[:3]], int(db))
    ini = date(anio if MESES[ma[:3]] <= MESES[mb[:3]] else anio - 1, MESES[ma[:3]], int(da[0]))
    return pd.Timestamp(ini), pd.Timestamp(fin)


def valor(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return np.nan
    s = str(x).strip()
    if s in ("n.d.", "—", "nan", ""):
        return np.nan
    if s.startswith("<"):
        return np.nan                   # '<1%' o '<10%': no se imputa
    v = float(s.replace("%", ""))
    return 100 * v if v <= 1 else v


def encuestas_primaria_2026() -> pd.DataFrame:
    m = pd.read_excel(EXCEL, sheet_name="Gobernador California", header=None, dtype=object)
    cand = {24: "Becerra", 25: "Hilton", 26: "Steyer", 27: "Bianco", 28: "Porter", 29: "Mahan",
            30: "Swalwell", 31: "Villaraigosa", 32: "Yee", 33: "Thurmond", 34: "Indecisos"}
    filas = []
    for j in range(5, m.shape[1]):
        fecha, nombre = m.iat[22, j], m.iat[23, j]
        if pd.isna(fecha) or pd.isna(nombre):
            continue
        ini, fin = parse_rango_es(fecha)
        row = dict(eleccion="PRIM2026", encuestadora=str(nombre).replace("\n", " "), inicio=ini, fin=fin, n=np.nan)
        for i, c in cand.items():
            row[c] = valor(m.iat[i, j])
        filas.append(row)
    return pd.DataFrame(filas)


def encuestas_primarias_previas() -> pd.DataFrame:
    p = pd.read_csv(DATA / "primarias_encuestas_previas.csv", parse_dates=["inicio", "fin"])
    filas = []
    for _, r in p.iterrows():
        d = dict(eleccion=r.eleccion, encuestadora=r.encuestadora, inicio=r.inicio, fin=r.fin, n=r.n,
                 Indecisos=r.indecisos)
        for k in (1, 2, 3, 4):
            d[r[f"c{k}"]] = r[f"c{k}_pct"]
        filas.append(d)
    return pd.DataFrame(filas)


def agregado_multicandidato(df, candidatos, corte, variante):
    sub = df[df.fin <= corte].copy()
    sub = sub.dropna(subset=candidatos[:2])
    w = pesos(sub, corte, variante, vida_media=14.0)   # primarias: más volátiles → vida media 14 d
    out = {}
    for c in candidatos:
        v = sub[c].to_numpy(float)
        ok = ~np.isnan(v)
        out[c] = float(np.dot(w[ok], v[ok]) / w[ok].sum()) if ok.any() else np.nan
    return out, len(sub)


def prob_avanzar(medias: dict, sigma_ind: float, sigma_bloque: float, partidos: dict, nsim=200_000):
    """Normal multivariada: ruido individual + choque común por partido (consolidación)."""
    cands = list(medias)
    mu = np.array([medias[c] for c in cands])
    z_ind = RNG.normal(0, sigma_ind, (nsim, len(cands)))
    choque = {p: RNG.normal(0, sigma_bloque, nsim) for p in set(partidos.values())}
    sim = mu + z_ind + np.column_stack([choque[partidos[c]] for c in cands])
    orden = np.argsort(-sim, axis=1)[:, :2]
    return {c: float(np.mean((orden == k).any(axis=1))) for k, c in enumerate(cands)}


def bloque_b():
    prev = encuestas_primarias_previas()
    res = pd.read_csv(DATA / "primarias_resultados.csv", parse_dates=["fecha_eleccion"])
    p26 = encuestas_primaria_2026()
    p26.to_csv(OUT / "B_encuestas_primaria_2026_parseadas.csv", index=False, encoding="utf-8-sig")

    config = {
        "PRIM2018": (["Newsom", "Cox", "Villaraigosa", "Allen"], prev[prev.eleccion == "PRIM2018"]),
        "PRIMSEN2024": (["Schiff", "Garvey", "Porter", "Lee"], prev[prev.eleccion == "PRIMSEN2024"]),
        "PRIM2026": (["Becerra", "Hilton", "Steyer", "Bianco"], p26),
    }
    partidos = dict(res[["candidato", "partido"]].drop_duplicates().values)

    filas = []
    for el, (cands, df) in config.items():
        r = res[res.eleccion == el]
        real = dict(zip(r.candidato, r.pct))
        fe = r.fecha_eleccion.iloc[0]
        for dias_antes in (28, 14, 7, 1):
            corte = fe - pd.Timedelta(days=dias_antes)
            for var in ("notebook", "mejorado"):
                ag, n = agregado_multicandidato(df, cands, corte, var)
                if n == 0:
                    continue
                for c in cands:
                    filas.append(dict(eleccion=el, dias_antes=dias_antes, variante=var, n_encuestas=n,
                                      candidato=c, partido=partidos[c], encuestas=ag[c], real=real[c],
                                      error=real[c] - ag[c]))
    t = pd.DataFrame(filas)
    # Líder de partido según las ENCUESTAS en ese corte (no según el resultado)
    t["lider_partido"] = (t.groupby(["eleccion", "dias_antes", "variante", "partido"]).encuestas
                           .transform("max").eq(t.encuestas))
    t.to_csv(OUT / "B_primarias_errores.csv", index=False, encoding="utf-8-sig")

    # Calibración con 2018 y 2024 (anteriores) -> evaluación fuera de muestra en 2026
    train = t[(t.eleccion != "PRIM2026") & (t.dias_antes == 1) & (t.variante == "mejorado")]
    # Descomposición: choque común por partido (media de error por partido y elección) + residuo
    bloque = train.groupby(["eleccion", "partido"]).error.transform("mean")
    sigma_bloque = float(np.sqrt(np.mean(train.groupby(["eleccion", "partido"]).error.mean() ** 2)))
    sigma_ind = float(np.sqrt(np.mean((train.error - bloque) ** 2)))
    sesgo_por_partido = train.groupby("partido").error.mean().to_dict()
    # Prima de consolidación top-two: el líder de cada partido en encuestas capta indecisos
    prima = train.groupby("lider_partido").error.mean().to_dict()
    resid_lider = train.error - train.lider_partido.map(prima)
    sigma_ind_lider = float(np.sqrt(np.mean(resid_lider ** 2)))

    ev, ev_medias = [], {}
    for var in ("notebook", "mejorado"):
        t26 = t[(t.eleccion == "PRIM2026") & (t.dias_antes == 1) & (t.variante == var)]
        medias = dict(zip(t26.candidato, t26.encuestas))
        lider = dict(zip(t26.candidato, t26.lider_partido))
        for nombre, sb, si, sesgo in (
            ("M1 notebook (sigma 4.5 indiv, sin bloque)", 0.0, 4.5, None),
            ("M1 + choque de bloque calibrado 2018/2024", sigma_bloque, sigma_ind, None),
            ("M1 + bloque + sesgo por partido 2018/2024", sigma_bloque, sigma_ind, "partido"),
            ("M1 + bloque + prima de líder top-two 2018/2024", sigma_bloque, sigma_ind_lider, "lider"),
        ):
            if sesgo == "partido":
                mu = {c: medias[c] + sesgo_por_partido.get(partidos[c], 0) for c in medias}
            elif sesgo == "lider":
                mu = {c: medias[c] + prima[bool(lider[c])] for c in medias}
            else:
                mu = dict(medias)
            if var == "mejorado":
                ev_medias[nombre] = {c: round(v, 2) for c, v in mu.items()}
            pa = prob_avanzar(mu, si, sb, {c: partidos[c] for c in mu})
            for c, pr in pa.items():
                ev.append(dict(variante=var, modelo=nombre, candidato=c, p_avanza=pr,
                               avanzo=int(c in ("Becerra", "Hilton"))))
    ev = pd.DataFrame(ev)

    # Kalshi: cierre del 1-jun (vela que termina 2-jun 04:00 UTC)
    k = pd.read_csv(DATA / "kalshi_primaria_avanza.csv")
    k["mid"] = np.where((k.yes_bid_close > 0) & (k.yes_ask_close < 1),
                        (k.yes_bid_close + k.yes_ask_close) / 2, k.price_close)
    k["fecha_et"] = (pd.to_datetime(k.end_period_ts, unit="s") - pd.Timedelta(hours=4)).dt.date - timedelta(days=1)
    k["candidato"] = k.ticker.str.split("-").str[-1].map({"XBEC": "Becerra", "SHIL": "Hilton", "TSTE": "Steyer"})
    k.to_csv(OUT / "C_kalshi_primaria_diaria.csv", index=False, encoding="utf-8-sig")
    kal = k[k.fecha_et == date(2026, 6, 1)][["candidato", "mid"]]
    for _, r in kal.iterrows():
        ev = pd.concat([ev, pd.DataFrame([dict(variante="mercado", modelo="Kalshi (cierre 1-jun)",
                                               candidato=r.candidato, p_avanza=r.mid,
                                               avanzo=int(r.candidato in ("Becerra", "Hilton")))])])
    # Ensamble 50/50 en logit (peso NO ajustado: con una sola primaria no es estimable)
    lg = lambda p: np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4)))
    mod = ev[(ev.variante == "mejorado") & (ev.modelo.str.contains("prima de líder"))].set_index("candidato").p_avanza
    kk = kal.set_index("candidato").mid
    for c in kk.index:
        pe = 1 / (1 + np.exp(-(0.5 * lg(mod[c]) + 0.5 * lg(kk[c]))))
        ev = pd.concat([ev, pd.DataFrame([dict(variante="ensamble", modelo="50% prima de líder + 50% Kalshi",
                                               candidato=c, p_avanza=pe, avanzo=int(c in ("Becerra", "Hilton")))])])
    tres = ev[ev.candidato.isin(["Becerra", "Hilton", "Steyer"])]
    score = (tres.groupby(["variante", "modelo"])
                 .apply(lambda g: pd.Series(dict(Brier=brier(g.p_avanza, g.avanzo),
                                                 LogLoss=logloss(g.p_avanza, g.avanzo),
                                                 P_Becerra=g.set_index("candidato").p_avanza.get("Becerra"),
                                                 P_Hilton=g.set_index("candidato").p_avanza.get("Hilton"),
                                                 P_Steyer=g.set_index("candidato").p_avanza.get("Steyer"))),
                        include_groups=False)
                 .reset_index().sort_values("Brier"))
    score.to_csv(OUT / "B_primaria2026_prob_avanzar.csv", index=False, encoding="utf-8-sig")

    # --- M2 (proxy de registro del notebook) aplicado a datos tempranos de la primaria ---
    reg_d, reg_r, reg_tot = 10_397_692, 5_779_786, 23_155_447     # SOV primaria 2026
    m2 = []
    for etiqueta, dev_tot, d_sh, r_sh in (("17-may (PDI)", 905_889, .41, .37),
                                          ("31-may (PDI, tasas D15%/R19%)", .151 * reg_tot,
                                           .15 * reg_d / (.151 * reg_tot), .19 * reg_r / (.151 * reg_tot))):
        margen_dev = 100 * (d_sh - r_sh)
        margen_reg = 100 * (reg_d - reg_r) / reg_tot
        cobertura = min(1, dev_tot / (reg_tot * 0.60))
        delta = 2.0 * 0.5 * np.sqrt(cobertura) * np.tanh((margen_dev - margen_reg) / 15.0)
        m2.append(dict(corte=etiqueta, devueltas=int(dev_tot), margen_DR_devueltas=margen_dev,
                       margen_DR_registro=margen_reg, desviacion=margen_dev - margen_reg,
                       delta_margen_M2_pp=delta))
    m2 = pd.DataFrame(m2)
    m2.to_csv(OUT / "B_M2_proxy_en_primaria.csv", index=False, encoding="utf-8-sig")
    calib = dict(sigma_bloque=sigma_bloque, sigma_individual=sigma_ind, sesgo_por_partido=sesgo_por_partido,
                 prima_lider=prima[True], prima_no_lider=prima[False], sigma_individual_tras_prima=sigma_ind_lider,
                 medias_2026_por_modelo=ev_medias)
    return t, score, m2, calib


# ======================================================================================
# C. CONTEO DE LA PRIMARIA ("espejismo rojo")
# ======================================================================================

def bloque_c():
    c = pd.read_csv(DATA / "conteo_primaria_2026.csv")
    cand = ["becerra", "hilton", "steyer", "bianco"]
    total_final_votos_gob = 9_255_000      # aprox. votos válidos gobernador (suma de candidatos SOV)
    filas = []
    prev = None
    for _, r in c.iterrows():
        tot_est = r.hilton / {0.55: .276, 0.94: .248, 1.0: .2459}[r.pct_contado_aprox]
        cur = {k: r[k] for k in cand}
        fila = dict(corte=r.corte, votos_validos_est=tot_est,
                    **{f"{k}_pct": 100 * cur[k] / tot_est for k in cand})
        fila["bloque_R_pct"] = fila["hilton_pct"] + fila["bianco_pct"]
        fila["becerra_menos_hilton_pp"] = fila["becerra_pct"] - fila["hilton_pct"]
        fila["hilton_menos_steyer_pp"] = fila["hilton_pct"] - fila["steyer_pct"]
        if prev is not None:
            dv = tot_est - prev[0]
            for k in cand:
                fila[f"{k}_pct_tramo"] = 100 * (cur[k] - prev[1][k]) / dv
        filas.append(fila)
        prev = (tot_est, cur)
    t = pd.DataFrame(filas)
    t.to_csv(OUT / "C_conteo_primaria_2026.csv", index=False, encoding="utf-8-sig")
    return t


# ======================================================================================
# D. KALSHI GENERAL 2026
# ======================================================================================

def bloque_d(sigma_emp: float, margen_encuestas: float):
    k = pd.read_csv(DATA / "kalshi_general_ganador.csv")
    k["mid"] = np.where(k.yes_bid_close.notna() & (k.yes_bid_close > 0),
                        (k.yes_bid_close + k.yes_ask_close) / 2, k.price_close)
    k["fecha_et"] = (pd.to_datetime(k.end_period_ts, unit="s") - pd.Timedelta(hours=4)).dt.date - timedelta(days=1)
    k["cand"] = k.ticker.str[-4:]
    w = k.pivot_table(index="fecha_et", columns="cand", values="mid").dropna()
    w["p_becerra_norm"] = w.XBEC / (w.XBEC + w.SHIL)        # quita el overround
    w.to_csv(OUT / "D_kalshi_general_diaria.csv", encoding="utf-8-sig")
    ult = w.iloc[-1]
    p = float(ult.p_becerra_norm)
    zq = stats.norm.ppf(p)
    d = dict(fecha=str(w.index[-1]), p_becerra_kalshi=float(ult.XBEC), p_hilton_kalshi=float(ult.SHIL),
             p_becerra_normalizada=p,
             margen_implicito_sigma_4_5=4.5 * zq,
             margen_implicito_sigma_empirica=sigma_emp * zq,
             sigma_implicita_dado_margen_encuestas=margen_encuestas / zq,
             p_modelo_sigma_4_5=float(stats.norm.cdf(margen_encuestas / 4.5)),
             p_modelo_sigma_empirica=float(stats.norm.cdf(margen_encuestas / sigma_emp)))
    return w, d


def graficos(tA, kal_prim: pd.DataFrame):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    # 1) Error de encuestas en generales
    e = tA[(tA.variante == "mejorado") & (tA.dias_antes == 7)].sort_values("eleccion")
    fig, ax = plt.subplots(figsize=(8, 4))
    col = ["#c0392b" if p == "R" else "#2e86c1" for p in e.presidente]
    ax.bar(e.eleccion, e.error, color=col)
    ax.axhline(0, color="gray", lw=1)
    for s in (4.5, 6.6):
        ax.axhspan(-1.96 * s, 1.96 * s, alpha=.06 if s == 6.6 else .12, color="k")
    ax.set(title="Error real − encuestas (margen D−R, T−7). Rojo: presidente R; azul: presidente D",
           ylabel="pp")
    ax.text(0.01, 0.02, "Bandas: ±1.96σ con σ=4.5 (oscura) y σ=6.6 empírica (clara)", transform=ax.transAxes, fontsize=8)
    plt.tight_layout(); plt.savefig(OUT / "A_error_generales.png", dpi=150); plt.close()
    # 2) Kalshi primaria alrededor de la elección y el conteo
    k = kal_prim[(kal_prim.fecha_et >= date(2026, 5, 15)) & (kal_prim.fecha_et <= date(2026, 6, 9))]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    for c, g in k.groupby("candidato"):
        ax.plot(g.fecha_et, g.mid, marker="o", ms=3, label=c)
    for d, t in ((date(2026, 6, 2), "Elección"), (date(2026, 6, 5), "Becerra rebasa / AP")):
        ax.axvline(d, color="gray", ls=":"); ax.text(d, 1.02, t, fontsize=8, ha="center")
    ax.set(ylim=(0, 1.08), title="Kalshi: probabilidad de avanzar a noviembre (cierre diario ET)", ylabel="precio")
    ax.legend(); fig.autofmt_xdate(); plt.tight_layout(); plt.savefig(OUT / "C_kalshi_primaria_conteo.png", dpi=150); plt.close()


# ======================================================================================
if __name__ == "__main__":
    pd.set_option("display.width", 200, "display.max_columns", 30)
    tA, calA = bloque_a()
    print("\n=== A. Generales: error del agregado (real - encuestas) ===")
    print(tA.pivot_table(index=["eleccion", "presidente"], columns=["variante", "dias_antes"], values="error").round(1))
    print(tA.groupby(["variante", "dias_antes"]).error.agg(n="count", sesgo="mean",
          RMSE=lambda e: float(np.sqrt(np.mean(e ** 2)))).round(2))
    print("\n=== A. Calibración de sigma (T-14) ===")
    print(calA.round(3).to_string(index=False))

    tB, scB, m2, calib = bloque_b()
    print("\n=== B. Primarias: error por candidato a T-1 (variante mejorado) ===")
    print(tB[(tB.dias_antes == 1) & (tB.variante == "mejorado")]
          [["eleccion", "candidato", "partido", "encuestas", "real", "error"]].round(2).to_string(index=False))
    print("\nCalibración de primarias (2018+2024):", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in calib.items()})
    print("\n=== B. Primaria 2026: probabilidad de avanzar ===")
    print(scB.round(3).to_string(index=False))
    print("\n=== B. M2 (proxy del notebook) con datos de devolución de la primaria ===")
    print(m2.round(3).to_string(index=False))

    tC = bloque_c()
    print("\n=== C. Conteo primaria 2026 ===")
    print(tC.round(2).T)

    sig_emp = float(calA[(calA.variante == "mejorado") & (calA.modelo == "sigma empirica LOO")].sigma_media.iloc[0])
    w, d = bloque_d(sig_emp, margen_encuestas=17.41)
    print("\n=== D. Kalshi general ===")
    print(json.dumps(d, indent=2, default=float))
    graficos(tA, pd.read_csv(OUT / "C_kalshi_primaria_diaria.csv", parse_dates=["fecha_et"]).assign(
        fecha_et=lambda x: x.fecha_et.dt.date))
    json.dump(dict(calibracion_primarias=calib, kalshi_general=d), open(OUT / "resumen.json", "w"),
              indent=2, default=float, ensure_ascii=False)
