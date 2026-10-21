"""D) Indecisos dentro del modelo ganador (T−15, LOYO): ¿el reparto hacia R aporta algo además del sesgo estatal?
E) Kalshi GOVPARTYGA-26: margen implícito y mezcla con el modelo.
"""
import numpy as np, pandas as pd
from scipy.stats import norm
from scipy.special import logit, expit
import backtest_georgia as bt

OUT = bt.OUT

def contiendas_con_U(h=15):
    d = bt.cargar_encuestas()
    d['U'] = (100 - d.cand1_pct - d.cand2_pct - d.cand3_pct.fillna(0)).clip(lower=0)
    years = sorted(d.year.unique())
    casa = {y: bt.efectos_casa(d[d.year != y]) for y in years}
    b = bt.construir_contiendas(d, h, 'casa', casa)
    U = d[d.days >= h].groupby('race').U.mean()
    b['U'] = b.race.map(U)
    b['e'] = b.poll - b.actual
    return b, years

def sesgo_pasado(tr, y, hl=4.0):
    past = tr[tr.year < y].copy()
    if len(past) < 20: return {}
    past['w'] = 0.5 ** ((y - past.year) / hl)
    st = past.groupby('location').apply(lambda g: pd.Series({'m': np.average(g.e2, weights=g.w),
        'neff': g.w.sum()**2/(g.w**2).sum(), 'v': g.e2.var() if len(g)>1 else np.nan}), include_groups=False)
    st = st[st.neff >= 1.5]
    vs = max(float(st.m.var()) - float(np.nanmean(st.v/st.neff)), 0)
    return {l: (vs/(vs + r.v/r.neff))*r.m if vs > 0 and not np.isnan(r.v) else 0.0 for l, r in st.iterrows()}

def prueba_indecisos():
    b, years = contiendas_con_U()
    res = []
    for regla in ['50/50', 's_LOYO', 's=0.436 (V9)']:
        preds = []
        for y in years:
            te = b.year == y
            if not te.any(): continue
            tr = b[~te].copy()
            if regla == '50/50': s = 0.5
            elif regla == 's=0.436 (V9)': s = 0.436
            else:
                k = np.sum(tr.U * (tr.actual - tr.poll)) / np.sum(tr.U ** 2); s = (1 - k) / 2
            tr['mu0'] = tr.poll + tr.U * (1 - 2 * s)
            tr['e2'] = tr.mu0 - tr.actual
            tau, sg = bt.ajustar_sigma(tr.e2.to_numpy(), tr.k.to_numpy())
            bias = sesgo_pasado(tr, y)
            t = b[te].copy()
            t['mu'] = t.poll + t.U * (1 - 2 * s) - t.location.map(bias).fillna(0)
            t['sd'] = np.sqrt(tau**2 + sg**2 / np.maximum(t.k, 1)); t['s'] = s
            preds.append(t)
        P = pd.concat(preds)
        for amb, m in [('Nacional', P.index == P.index), ('GA_generales', (P.location == 'GA') & ~P.runoff),
                       ('GA_2014+', (P.location == 'GA') & (P.year >= 2014))]:
            r = bt.metricas(P[m]); r.update({'regla_indecisos': regla, 'ambito': amb, 's_media': P.s.mean()}); res.append(r)
    return pd.DataFrame(res)

def kalshi(mu_modelo, sd_modelo):
    k = pd.read_csv(bt.DATA / 'kalshi_GOVPARTYGA-26-D_diario.csv', parse_dates=['date_utc'])
    k['mid'] = (k.yes_bid_close + k.yes_ask_close) / 2
    hoy = k.iloc[-1]
    # precio R del mismo día (API markets 20-oct): bid 0.51-0.52, ask 0.52-0.53 -> normalizamos D/(D+R)
    p_d = float(hoy.mid) / (float(hoy.mid) + 0.515)
    m_implicito = sd_modelo * norm.ppf(p_d)               # margen que haría coincidir al modelo con el mercado
    sd_implicito = -mu_modelo / norm.ppf(p_d) if abs(norm.ppf(p_d)) > 1e-6 else np.inf  # sigma que haría coincidir el centro
    p_mod = norm.cdf(mu_modelo / sd_modelo)
    filas = []
    for w in [0, 0.15, 0.30, 0.50, 1.0]:
        pm = expit((1 - w) * logit(p_mod) + w * logit(p_d))
        filas.append({'peso_kalshi': w, 'P_Bottoms': pm, 'margen_equivalente': sd_modelo * norm.ppf(pm)})
    return k, {'fecha': str(hoy.date_utc.date()), 'mid_D': float(hoy.mid), 'p_D_normalizado': p_d,
               'margen_implicito_con_sd_modelo': m_implicito, 'sd_implicita_con_mu_modelo': sd_implicito,
               'p_modelo': p_mod}, pd.DataFrame(filas)

if __name__ == '__main__':
    pd.set_option('display.width', 200)
    D = prueba_indecisos(); D.to_csv(OUT / 'D_indecisos_en_modelo_ganador.csv', index=False)
    print(D[['ambito','regla_indecisos','s_media','n','sesgo','MAE','RMSE','CRPS','Cob80','Cob95']].round(3).to_string(index=False))
