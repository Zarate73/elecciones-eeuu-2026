"""Revisión externa del 22-oct (Nevada): pruebas que pide cada observación.

A. Régimen de hoy (pocas firmas y encuesta interna dominante): CRPS y cobertura de G frente a P1/P2/P3 solo en las
   contiendas históricas que se le parecen (k ≤ 2 encuestadoras y > 50 % del peso en encuestas partidistas).
B. Sesgo estatal de NV: comparaciones excluyendo 2014 (una sola encuestadora, error +22.8) y separando contiendas con
   k = 1 de k ≥ 2, en LOYO y en validación cronológica; valor actual del sesgo con esos filtros; variante nacional
   que estima el sesgo sin contiendas de una sola encuestadora.
D. Peso de mercados en régimen de escasez: máxima verosimilitud de w en las contiendas de 2024 con k ≤ 2 y k ≤ 3.

Uso: python revision_nevada.py  (requiere haber corrido backtest_nevada.py) → salida/revision_*.csv, revision_resumen.txt
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
import backtest_nevada as BN           # noqa: E402
import base_georgia as bt              # noqa: E402
import motor_backtest as BA            # noqa: E402
import revision_observaciones as RO    # noqa: E402

EST = 'NV'
SAL = BASE / 'salida'
LOG: list[str] = []


def p_(*x):
    s = ' '.join(str(v) for v in x)
    print(s)
    LOG.append(s)


def tabla(P: pd.DataFrame, modelos: list[str], filtros: dict) -> pd.DataFrame:
    filas = []
    for amb, m in filtros.items():
        g0 = P[m & P.modelo.isin(modelos)]
        for mod, g in g0.groupby('modelo'):
            filas.append({'ambito': amb, 'modelo': mod, 'n': len(g), 'CRPS': g.crps.mean(),
                          'MAE': (g.mu - g.actual).abs().mean(), 'Cob80': g.c80.mean()})
    return pd.DataFrame(filas)


# ------------------------------------------------------------------------------------- sesgo sin contiendas k = 1
def sesgo_pasado_k2(tr: pd.DataFrame, y: int, contraer: bool = True) -> dict:
    return BA_sesgo_original(tr[tr.k >= 2], y, contraer)


BA_sesgo_original = BA.sesgo_pasado


def main():
    pd.set_option('display.width', 220)
    P = pd.read_csv(SAL / 'predicciones_LOYO.csv')
    G, H8 = BN.REF, 'H8 V11 sin sesgo estatal (Arizona)'
    nv = P.location == EST

    # ---------------------------------------------------------------- A. régimen de hoy
    part = P[P.modelo == 'P1 casa + patrocinador si la firma no tiene historia'][['race', 'frac_part']]
    kG = P[P.modelo == G][['race', 'k']].rename(columns={'k': 'k_G'})
    P = P.drop(columns='frac_part', errors='ignore').merge(part, on='race', how='left').merge(kG, on='race', how='left')
    reg = (P.k_G <= 2) & (P.frac_part > 0.5)                 # mismo conjunto de contiendas para todas las variantes
    mods = [G, H8, 'P1 casa + patrocinador si la firma no tiene historia',
            'P2 sin encuestas partidistas (si hay no partidistas)', 'P3 encuestas partidistas pesan la mitad']
    TA = tabla(P, mods, {'k ≤ 2 y encuestas partidistas > 50 %': reg, 'k ≤ 2 (todas)': P.k_G <= 2, 'k ≥ 3': P.k_G >= 3})
    p_(f'[A] Régimen parecido al de hoy en NV: {P[reg & (P.modelo == G)].shape[0]} contiendas con k ≤ 2 y > 50 % del peso '
       f'en encuestas partidistas')
    p_(TA.round(3).to_string(index=False))
    TA.to_csv(SAL / 'revision_A_regimen.csv', index=False)

    # ---------------------------------------------------------------- B. sesgo estatal
    filtros = {'NV (23)': nv, 'NV sin 2014': nv & (P.race != '2014_Gov-G_NV'), 'NV k ≥ 2': nv & (P.k >= 2),
               'NV k = 1': nv & (P.k == 1), 'NV gobernador sin 2014': nv & (P.tipo == 'Gov-G') & (P.race != '2014_Gov-G_NV'),
               'NV gobernador k ≥ 2': nv & (P.tipo == 'Gov-G') & (P.k >= 2)}
    TB = tabla(P, [G, H8], filtros)
    TB['P(sin sesgo mejor)'] = np.nan
    for amb, m in filtros.items():
        if (P[m & (P.modelo == G)].year.nunique()) > 2:
            TB.loc[(TB.ambito == amb) & (TB.modelo == H8), 'P(sin sesgo mejor)'] = BA.bootstrap_por_anio(P, H8, G, m)
    p_('\n[B1] LOYO: con sesgo (G) frente a sin sesgo (H8)')
    p_(TB.round(3).to_string(index=False))

    # cronológico
    d = RO.cargar()
    d['partisan'] = d.partisan.fillna('').astype(str).str[:1].replace({'n': ''})
    bc = RO.base_cronologica(d)
    C = pd.concat([RO.evaluar_cronologico(bc, True).assign(modelo='con sesgo'),
                   RO.evaluar_cronologico(bc, False).assign(modelo='sin sesgo')], ignore_index=True)
    nvc = C.location == EST
    fc = {'NV': nvc, 'NV sin 2014': nvc & (C.race != '2014_Gov-G_NV'), 'NV k ≥ 2': nvc & (C.k >= 2),
          'NV gobernador sin 2014': nvc & (C.tipo == 'Gov-G') & (C.race != '2014_Gov-G_NV')}
    TC = tabla(C, ['con sesgo', 'sin sesgo'], fc)
    for amb, m in fc.items():
        TC.loc[(TC.ambito == amb) & (TC.modelo == 'sin sesgo'), 'P(sin sesgo mejor)'] = \
            BA.bootstrap_por_anio(C, 'sin sesgo', 'con sesgo', m)
    p_('\n[B2] Validación cronológica (2004–2024)')
    p_(TC.round(3).to_string(index=False))

    # sesgo estimado sin contiendas k = 1: variante nacional (LOYO)
    years = sorted(d.year.unique())
    casa = {y: bt.efectos_casa(d[d.year != y]) for y in years}
    b = BA.construir(d, casa, 'v11')
    PG = BA.evaluar(b, 'G', 'u50', True, 'sig')
    BA.sesgo_pasado = sesgo_pasado_k2
    PK = BA.evaluar(b, 'G2 sesgo estimado solo con k ≥ 2', 'u50', True, 'sig')
    BA.sesgo_pasado = BA_sesgo_original
    PP = pd.concat([PG, PK], ignore_index=True)
    TD = tabla(PP, ['G', 'G2 sesgo estimado solo con k ≥ 2'],
               {'Nacional': PP.index == PP.index, 'Nacional gobernador': PP.tipo == 'Gov-G', 'NV': PP.location == EST})
    for amb, m in (('Nacional', PP.index == PP.index), ('NV', PP.location == EST)):
        TD.loc[(TD.ambito == amb) & (TD.modelo != 'G'), 'P(G2 mejor)'] = BA.bootstrap_por_anio(
            PP, 'G2 sesgo estimado solo con k ≥ 2', 'G', pd.Series(np.asarray(m), index=PP.index))
    p_('\n[B3] ¿Estimar el sesgo sin contiendas de una sola encuestadora?')
    p_(TD.round(3).to_string(index=False))

    # valor actual del sesgo de NV con filtros (mismo cálculo que producción: errores a h = 12, vida media 4 años)
    sys.path.insert(0, str(BASE.parent / 'produccion'))
    from nv_pronostico import historico as PH
    from nv_pronostico.config import cargar_config
    cfg = cargar_config(corte='2026-10-22')
    raw = pd.read_csv(BASE / 'data' / 'fte_raw_polls_2023.csv', low_memory=False)
    dd = PH.preparar(raw, cfg)
    filas = []
    for y in sorted(dd.year.unique()):
        house = PH.efectos_casa(dd[dd.year != y], 8.0)
        for race, p in dd[dd.year == y].groupby('race'):
            q = p[(p.days >= 12) & (p.days <= 21)].rename(columns={'cand3_pct': 'otros'})
            if len(q):
                mu, _, k, _ = PH.promedio(q, house, 14.0)
                filas.append({'race': race, 'year': int(y), 'location': p.location.iloc[0], 'k': k,
                              'e': mu - float(p.margin_actual.iloc[0])})
    E = pd.DataFrame(filas)

    def sesgo(e: pd.DataFrame) -> tuple[float, float, float]:
        e = e.assign(w=0.5 ** ((2026 - e.year) / 4.0))
        st = e.groupby('location').apply(lambda g: pd.Series({
            'm': np.average(g.e, weights=g.w), 'neff': g.w.sum() ** 2 / (g.w ** 2).sum(),
            'v': g.e.var() if len(g) > 1 else np.nan}), include_groups=False)
        st = st[st.neff >= 1.5]
        vs = max(float(st.m.var()) - float(np.nanmean(st.v / st.neff)), 0.0)
        r = st.loc[EST]
        c = vs / (vs + r.v / r.neff) if vs > 0 else 0.0
        return float(r.m), float(c), float(c * r.m)

    SV = pd.DataFrame([{'version': nom, **dict(zip(('bruto', 'contraccion', 'contraido'), sesgo(e)))} for nom, e in (
        ('Producción (todas)', E), ('Sin 2014 Gob NV', E[E.race != '2014_Gov-G_NV']),
        ('Solo contiendas con k ≥ 2 (todos los estados)', E[E.k >= 2]))])
    p_('\n[B4] Sesgo estatal de NV que usaría el pronóstico de hoy (+ = encuestas pro-D; se resta al margen)')
    p_(SV.round(3).to_string(index=False))
    p_(f"    Peso del año 2014 en el promedio de NV con vida media de 4 años: 0.5^(12/4) = {0.5 ** 3:.3f}")

    # ---------------------------------------------------------------- D. peso de mercados con pocas encuestas
    sys.path.insert(0, str(BASE.parent.parent / 'arizona' / 'backtest'))
    import importlib
    PMk = importlib.import_module('peso_mercados')
    x = pd.read_csv(BASE.parent.parent / 'arizona' / 'backtest' / 'data' / 'mercados_2024' / 'predicciones_h13_2024.csv')
    filas = []
    for amb, sel in (('Todas', x.k > 0), ('k ≤ 3', x.k <= 3), ('k ≤ 2', x.k <= 2), ('k ≥ 4', x.k >= 4)):
        xx = x[sel].reset_index(drop=True)
        gg = PMk.perfil(xx)
        w_ml, lo, hi = PMk.ic_lr(gg['ll_margen'])
        filas.append({'ambito': amb, 'n': len(xx), 'w_ML': w_ml, 'IC95_LR': f'{lo:.2f}–{hi:.2f}',
                      'ΔLL w=0.30': float(gg.loc[0.3, 'll_margen'] - gg['ll_margen'].max()),
                      'ΔLL w=0': float(gg.loc[0.0, 'll_margen'] - gg['ll_margen'].max())})
    TM = pd.DataFrame(filas)
    p_('\n[D] Peso de mercados por máxima verosimilitud según cuántas encuestadoras hay (40 contiendas 2024, h = 13)')
    p_(TM.round(3).to_string(index=False))

    for nom, t in (('B_loyo', TB), ('B_cronologico', TC), ('B_sesgo_k2', TD), ('B_valor_sesgo', SV), ('D_peso_mercados', TM)):
        t.to_csv(SAL / f'revision_{nom}.csv', index=False)
    (SAL / 'revision_resumen.txt').write_text('\n'.join(LOG), encoding='utf-8')


if __name__ == '__main__':
    main()
