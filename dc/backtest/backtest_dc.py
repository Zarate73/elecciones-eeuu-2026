"""Backtest del modelo general de D.C. (alcaldía): selección por validación dejando fuera una elección (LOYO).

Datos: las 13 generales de alcaldía 1974–2022 (Wikipedia, extraídas por dc_pronostico.historico; copia en datos/) y el
criterio del opositor principal (datos/contexto_alcaldias.csv: fuerte = concejal o alcalde, actual o anterior).
Uso:  python backtest_dc.py            (desde dc/backtest; usa datos/)
      python backtest_dc.py --en-vivo  (vuelve a leer Wikipedia con el paquete de producción)
Salidas: resultados/variantes_loyo.csv, resultados/predicciones_loyo.csv, resultados/reparto_no_democrata.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / 'produccion'))
from dc_pronostico.modelo import ajustar, crps_muestras, predictiva, _col   # noqa: E402

RES = AQUI / 'resultados'
RES.mkdir(exist_ok=True)


def datos(en_vivo: bool) -> pd.DataFrame:
    if en_vivo:
        from dc_pronostico.config import cargar_config
        from dc_pronostico.historico import obtener_historico
        return obtener_historico(cargar_config())['tabla']
    h = pd.read_csv(AQUI / 'datos/generales_alcaldia_1974_2022.csv').merge(pd.read_csv(AQUI / 'datos/contexto_alcaldias.csv'), on='anio')
    h['primaria_pct'] = h.primaria_pct.fillna(h.primaria_pct_respaldo)
    h['y'] = np.log(h.pct_d / (100 - h.pct_d))
    return h


def ajustar_ponderado(h, variables, w):
    A = np.column_stack([np.ones(len(h))] + [_col(h, v) for v in variables])
    W = np.diag(w / w.mean())
    XtWX = A.T @ W @ A
    b = np.linalg.solve(XtWX, A.T @ W @ h.y.values)
    r = h.y.values - A @ b
    gl = max(len(h) - A.shape[1], 1)
    return {'b': b, 's2': float(r @ W @ r / gl), 'gl': gl, 'XtXi': np.linalg.inv(XtWX)}


VARIANTES = {
    'M0 media': ([], None),
    'M1 fuerte (elegido)': (['fuerte'], None),
    'M2 fuerte + titular': (['fuerte', 'titular'], None),
    'M3 fuerte + % primaria': (['fuerte', 'primaria'], None),
    'M4 fuerte + tendencia': (['fuerte', 'tendencia'], None),
    'M5 fuerte, σ por grupo': (['fuerte'], 'grupo'),
    'M6 fuerte, vida media 12 años': (['fuerte'], 12),
    'M6 fuerte, vida media 20 años': (['fuerte'], 20),
    'M6 fuerte, vida media 32 años': (['fuerte'], 32),
}


def loyo(h, variables, modo, rng, n=8000):
    out = []
    for i in range(len(h)):
        tr, te = h.drop(h.index[i]), h.iloc[i]
        if modo == 'grupo':
            g = tr[tr.fuerte == te.fuerte]
            mu, sc, gl = g.y.mean(), np.sqrt(g.y.var(ddof=1) * (1 + 1 / len(g))), len(g) - 1
        else:
            x = np.r_[1.0, [_col(h.iloc[[i]], v)[0] for v in variables]]
            if isinstance(modo, (int, float)):
                f = ajustar_ponderado(tr, variables, 0.5 ** (np.abs(tr.anio.values - te.anio) / modo))
            else:
                f = ajustar(tr, variables)
            mu, sc, gl = predictiva(f, x)
        p = 100 * expit(mu + sc * rng.standard_t(gl, n))
        lo, hi = np.percentile(p, [10, 90])
        out.append({'anio': int(te.anio), 'real': te.pct_d, 'mediana': float(np.median(p)), 'ic80_bajo': lo, 'ic80_alto': hi,
                    'crps': crps_muestras(p, te.pct_d, rng), 'en_ic80': lo <= te.pct_d <= hi, 'P_menos_50': float((p < 50).mean())})
    return pd.DataFrame(out)


def main(en_vivo=False) -> int:
    h = datos(en_vivo).sort_values('anio').reset_index(drop=True)
    rng = np.random.default_rng(20261103)
    preds, filas = [], []
    for nom, (v, modo) in VARIANTES.items():
        d = loyo(h, v, modo, rng)
        d['variante'] = nom
        preds.append(d)
    P = pd.concat(preds)
    base = P[P.variante.str.startswith('M1')].set_index('anio').crps
    for nom, d in P.groupby('variante', sort=False):
        dif = d.set_index('anio').crps - base
        bs = np.array([rng.choice(dif.values, len(dif)).mean() for _ in range(10000)])
        filas.append({'variante': nom, 'CRPS': d.crps.mean(), 'MAE_mediana': (d.mediana - d.real).abs().mean(),
                      'cobertura_IC80': d.en_ic80.mean(), 'dCRPS_vs_M1': dif.mean(),
                      'P_mejor_que_M1': float((bs < 0).mean()) if dif.abs().sum() else np.nan})
    V = pd.DataFrame(filas)
    pd.set_option('display.width', 200)
    print(V.round(3).to_string(index=False))
    V.round(4).to_csv(RES / 'variantes_loyo.csv', index=False)
    P.round(4).to_csv(RES / 'predicciones_loyo.csv', index=False)
    print('\nM1 por elección:')
    print(P[P.variante.str.startswith('M1')][['anio', 'real', 'mediana', 'ic80_bajo', 'ic80_alto', 'crps', 'P_menos_50']].round(2).to_string(index=False))
    # reparto del voto no demócrata en las elecciones con opositor débil y en las de verde no principal
    r = h.assign(no_d=100 - h.pct_d, frac_opositor=h.pct_op / (100 - h.pct_d))
    r[['anio', 'fuerte', 'pct_d', 'opositor', 'pct_op', 'frac_opositor', 'pct_verde', 'pct_escrito']].round(3).to_csv(
        RES / 'reparto_no_democrata.csv', index=False)
    debil = r[r.fuerte == 0]
    verde = r[(r.pct_verde > 0) & ~r.partido_op.str.contains('Statehood')]
    esc = r[(r.pct_escrito > 0) & (r.anio != 2010)]
    print(f"\nOpositor principal / voto no D (débil): mín {debil.frac_opositor.min():.2f}, mediana {debil.frac_opositor.median():.2f}")
    print(f"Verde no principal: n={len(verde)}, mediana geométrica {np.exp(np.log(verde.pct_verde).mean()):.2f} %, sd log {np.log(verde.pct_verde).std(ddof=1):.2f}")
    print(f"Por escrito (sin 2010): n={len(esc)}, recientes {esc[esc.anio >= 2014].pct_escrito.round(2).tolist()}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main('--en-vivo' in sys.argv))
