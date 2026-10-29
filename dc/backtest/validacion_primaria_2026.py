"""Validación del modelo elegido contra la primaria demócrata del 16-jun-2026 (resultados RCV certificados, 17-jul-2026).

La primaria no tiene nominado partidista ni «opositor fuerte», así que el núcleo de M1 (logit del % demócrata en la
general) no se puede evaluar con ella. Lo que sí se valida con la primaria es todo lo que el modelo de la general
comparte con una elección RCV de D.C.:
  1. El CONTEO RCV (rcv.py): con las transferencias publicadas, ¿reproduce ronda por ronda las 4 contiendas certificadas
     de la primaria (alcaldía 1 ronda; at-large 8; Ward 1 4; Ward 5, Ward 6, Delegado 1)?
  2. La tasa de AGOTAMIENTO que supone config/dc.toml (35 % de las boletas de un eliminado): ¿cuánto se agotó de verdad?
  3. El reparto de INDECISOS de las encuestas (proporcional, encuestas.py) frente al 55/30/15 del modelo de la primaria,
     con las dos encuestas publicadas (WaPo/GMU, City Cast/True Dot).
  4. La comparación «ronda final» del modelo de la primaria (51.85 %) contra la tabulación certificada.
Datos: datos/rcv_primaria_2026/*.csv (informes RCTab de la DCBOE, descargados con scripts/capturar_dc4.py).
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / 'produccion'))
from dc_pronostico.rcv import contar_rcv   # noqa: E402

D = AQUI / 'datos/rcv_primaria_2026'
RES = AQUI / 'resultados'
RES.mkdir(exist_ok=True)
INACTIVAS = ('Inactive Ballots by Overvotes', 'Inactive Ballots by Skipped Rankings', 'Inactive Ballots by Exhausted Choices',
             'Inactive Ballots by Repeated Rankings')


def leer_rctab(p: Path) -> dict:
    filas = list(csv.reader(p.open(encoding='utf-8-sig')))
    i = next(k for k, f in enumerate(filas) if f and f[0] == 'Rounds')
    nr = sum(1 for c in filas[i] if c.startswith('Round '))
    elim = filas[i + 1][1::3][:nr]
    cand, inact = {}, {}
    for f in filas[i + 3:]:
        if not f or not f[0]:
            continue
        if f[0].startswith(('Active Ballots', 'Current Round', 'Inactive Ballots Total')):
            continue
        votos = [float(f[1 + 3 * r]) for r in range(nr)]
        trans = [float(f[3 + 3 * r] or 0) for r in range(nr)]
        (inact if f[0] in INACTIVAS else cand)[f[0]] = (votos, trans)
    return {'rondas': nr, 'eliminados': elim, 'cand': cand, 'inact': inact,
            'ganador': next(f[1] for f in filas if f and f[0] == 'Winner(s)')}


def matriz_publicada(t: dict) -> dict:
    """Fracciones de transferencia que implican las columnas «transfer» del informe certificado."""
    tr = {}
    for r, e in enumerate(t['eliminados']):
        if not e:
            continue
        v = t['cand'][e][0][r]
        fila = {c: x[1][r] / v for c, x in t['cand'].items() if c != e and x[1][r] > 0}
        fila['agotada'] = sum(x[1][r] for x in t['inact'].values()) / v
        tr[e] = fila
    return tr


def main() -> int:
    filas_conteo, filas_ag = [], []
    for p in sorted(D.glob('rcv_*.csv')):
        t = leer_rctab(p)
        primeras = {c: x[0][0] for c, x in t['cand'].items()}
        r = contar_rcv(primeras, matriz_publicada(t))
        oficial = [{c: x[0][k] for c, x in t['cand'].items() if x[0][k] > 0} for k in range(t['rondas'])]
        dif = max(abs(r['rondas'][k][c] * sum(oficial[k].values()) - oficial[k][c]) for k in range(t['rondas']) for c in oficial[k]) \
            if len(r['rondas']) == t['rondas'] else np.nan
        filas_conteo.append({'contienda': p.stem.split('_', 2)[2], 'rondas_oficiales': t['rondas'], 'rondas_rcv_py': len(r['rondas']),
                             'ganador_oficial': t['ganador'], 'ganador_rcv_py': r['ganador'], 'max_dif_votos': dif})
        for k, e in enumerate(t['eliminados']):
            if e:
                v = t['cand'][e][0][k]
                ag = sum(x[1][k] for x in t['inact'].values())
                filas_ag.append({'contienda': p.stem.split('_', 2)[2], 'ronda': k + 1, 'eliminado': e, 'votos': v,
                                 'agotadas': ag, 'tasa_agotamiento': ag / v, 'es_write_in': e == 'Write-in'})
    C = pd.DataFrame(filas_conteo); A = pd.DataFrame(filas_ag)
    pd.set_option('display.width', 200)
    print('1. CONTEO RCV: rcv.py contra la tabulación certificada')
    print(C.to_string(index=False))
    print('\n2. AGOTAMIENTO por eliminación (certificado)')
    print(A.round(3).to_string(index=False))
    ponder = A.groupby('es_write_in').apply(lambda g: g.agotadas.sum() / g.votos.sum(), include_groups=False)
    print(f"Tasa ponderada: write-in {ponder.get(True, np.nan):.1%} · candidatos {ponder.get(False, np.nan):.1%} · "
          f"supuesto del modelo: 35 % (escrito y Gross)")
    # 3. indecisos
    enc = [('WaPo/GMU/Braun', 836, 36, 25, 25), ('City Cast/True Dot', 487, 39, 34, None)]
    real = {'jlg': 54.12, 'mcd': 35.06}
    filas_ind = []
    for nom, n, j, m, ind in enc:
        prop_j = 100 * j / (100 - (ind or 0)) if ind else np.nan
        filas_ind.append({'encuesta': nom, 'n': n, 'JLG_bruto': j, 'McDuffie_bruto': m, 'indecisos': ind,
                          'JLG_proporcional': prop_j, 'McDuffie_proporcional': 100 * m / (100 - ind) if ind else np.nan})
    I = pd.DataFrame(filas_ind)
    print('\n3. INDECISOS (real 1.ª ronda certificada: Lewis George 54.12 %, McDuffie 35.06 %)')
    print(I.round(1).to_string(index=False))
    print('   Modelo de la primaria (55/30/15): Lewis George 42.2 %, McDuffie 31.6 %')
    # 4. ronda final
    t = leer_rctab(next(D.glob('rcv_15_*MAYOR*.csv')))
    jlg, mcd = t['cand']['Janeese Lewis George'][0][0], t['cand']['Kenyan R. McDuffie'][0][0]
    act = sum(x[0][0] for x in t['cand'].values())
    menores = act - jlg - mcd
    print(f"\n4. RONDA FINAL. Certificado: {t['rondas']} ronda (Lewis George {100 * jlg / act:.2f} % de {act:,.0f} activas).")
    print(f"   Un cara a cara hipotético (sin los menores) quedaría en Lewis George ∈ [{100 * jlg / act:.1f}, {100 * (jlg + menores) / act:.1f}] %,"
          f" McDuffie ∈ [{100 * mcd / act:.1f}, {100 * (mcd + menores) / act:.1f}] %")
    print('   Modelo de la primaria, «final_share_active»: Lewis George 51.85 %, McDuffie 42.06 %')
    C.to_csv(RES / 'validacion_primaria_conteo.csv', index=False)
    A.round(4).to_csv(RES / 'validacion_primaria_agotamiento.csv', index=False)
    I.round(2).to_csv(RES / 'validacion_primaria_indecisos.csv', index=False)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
