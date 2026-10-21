"""Actualiza el bloque de pronóstico de los README con la última corrida (salidas/ultimo/reporte.json).

Uso:  python scripts/actualizar_readme.py   (desde california/produccion; lo llama GitHub Actions)
Escribe entre los marcadores <!-- PRONOSTICO:INICIO --> y <!-- PRONOSTICO:FIN --> de california/README.md,
reemplaza la fila de California en la tabla del README raíz y genera salidas/evolucion.png.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

PROD = Path(__file__).resolve().parent.parent
SAL = PROD / 'salidas'
README_CA = PROD.parent / 'README.md'
README_RAIZ = PROD.parent.parent / 'README.md'
INI, FIN = '<!-- PRONOSTICO:INICIO -->', '<!-- PRONOSTICO:FIN -->'
VIVO = ('en_vivo', 'api_en_vivo', 'Datos de Civiq')


def _reemplazar(texto: str, bloque: str) -> str:
    patron = re.compile(re.escape(INI) + r'.*?' + re.escape(FIN), re.S)
    return patron.sub(lambda _: f'{INI}\n{bloque.strip()}\n{FIN}', texto)


def evolucion() -> bool:
    h = SAL / 'historial_pronosticos.csv'
    if not h.exists():
        return False
    d = pd.read_csv(h)
    d['corte'] = pd.to_datetime(d.fecha_corte)
    d = d.sort_values('generado').groupby('corte').tail(1).sort_values('corte')
    if d.empty:
        return False
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.4))
    a1.plot(d.corte, d.pct_becerra, marker='o', color='#2563eb', label='Becerra (D)')
    a1.plot(d.corte, d.pct_hilton, marker='o', color='#dc2626', label='Hilton (R)')
    a1.set_ylabel('% de voto'); a1.set_title('Voto pronosticado', loc='left', fontsize=10)
    a2.plot(d.corte, 100 * d.p_d_final, marker='o', color='#2563eb', label='P(Becerra), final')
    a2.plot(d.corte, 100 * pd.to_numeric(d.p_kalshi, errors='coerce'), marker='.', ls='--', color='#d97706', label='Kalshi')
    a2.set_ylim(min(80, 100 * d.p_d_final.min() - 5), 100.5)
    a2.set_ylabel('%'); a2.set_title('Probabilidad de ganar', loc='left', fontsize=10)
    for a in (a1, a2):
        a.legend(frameon=False, fontsize=8)
        a.spines[['top', 'right']].set_visible(False)
        a.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=8))
        a.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
        if len(d) == 1:
            a.set_xlim(d.corte.iloc[0] - pd.Timedelta(days=2), d.corte.iloc[0] + pd.Timedelta(days=2))
    fig.suptitle('Evolución del pronóstico · California Gobernador', x=0.01, ha='left', fontsize=11)
    fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(SAL / 'evolucion.png', dpi=130); plt.close(fig)
    return True


def main() -> int:
    rep = json.loads((SAL / 'ultimo' / 'reporte.json').read_text(encoding='utf-8'))
    p, m5, enc, kal = rep['pronostico'], rep['m5'], rep['encuestas'], rep['kalshi']
    est = rep['estados_fuentes']
    vivas = sum(1 for v in est.values() if str(v).startswith(VIVO))
    ahora = datetime.now(ZoneInfo('America/Los_Angeles')).strftime('%Y-%m-%d %H:%M PT')
    pr = 1 - p['p_d_gana_final']
    ic80r = (100 - p['ic80_pct_d'][1], 100 - p['ic80_pct_d'][0])
    origen = ', '.join(f'{v} {k}' for k, v in enc.get('por_origen', {}).items())
    lineas = [
        f"**Pronóstico al {rep['fecha_corte']}** ({rep['dias_a_eleccion']} días a la elección) · actualizado automáticamente {ahora} · fuentes en vivo {vivas}/{len(est)}",
        '',
        '| Gobernador | % de voto (IC80) | Probabilidad de ganar |',
        '|---|---|---|',
        f"| Xavier **Becerra** (D) | **{p['pct_d']:.1f}%** ({p['ic80_pct_d'][0]:.1f}–{p['ic80_pct_d'][1]:.1f}) | **{p['p_d_gana_final']:.1%}** |",
        f"| Steve **Hilton** (R) | **{p['pct_r']:.1f}%** ({ic80r[0]:.1f}–{ic80r[1]:.1f}) | **{pr:.1%}** |",
        '',
        f"Margen D−R {p['margen_pp']:+.1f} pp (σ {m5['sigma_pp']:.1f}) · solo modelo: P(Becerra) {p['p_d_gana_modelo']:.1%} · "
        f"Kalshi {kal['p_d_normalizada']:.1%} (peso {m5.get('w_kalshi', 0.3):.2f}) · "
        f"{enc['n']} encuestas ({origen}) · promedio M5 {enc['margen_m5_pp']:+.1f}",
    ]
    hi = rep['participacion_m2']['historico']
    if hi.get('disponible'):
        refs = ', '.join(f'{k} {v:+.1f}' for k, v in hi['margen_referencias_mismo_dia_pp'].items())
        lineas += ['', f"**Voto anticipado (Civiq, diagnóstico):** boletas devueltas D−R {hi['margen_actual_pp']:+.1f} "
                       f"a T−{hi['dias_comparados']} contra {refs} al mismo día."]
    lineas += ['', '![Pronóstico](produccion/salidas/ultimo/pronostico_porcentajes.png)']
    if evolucion():
        lineas += ['', '![Evolución](produccion/salidas/evolucion.png)']
    lineas += ['', "Detalle: [`resumen.txt`](produccion/salidas/ultimo/resumen.txt) · "
                   "[encuestas y pesos](produccion/salidas/ultimo/encuestas_pesos.csv) · "
                   "[M5 frente a M1–M4](produccion/salidas/ultimo/comparacion_modelos.csv) · "
                   "[historial](produccion/salidas/historial_pronosticos.csv)"]
    README_CA.write_text(_reemplazar(README_CA.read_text(encoding='utf-8'), '\n'.join(lineas)), encoding='utf-8')
    fila = (f"| California | Gobernador: Becerra {p['pct_d']:.1f}% · Hilton {p['pct_r']:.1f}% · P(Becerra) {p['p_d_gana_final']:.0%} "
            f"(corte {rep['fecha_corte']}) | **Producción (M5)**, actualización automática | [`california/`](california/) |")
    raiz = README_RAIZ.read_text(encoding='utf-8')
    README_RAIZ.write_text(re.sub(r'^\| California \|.*$', lambda _: fila, raiz, count=1, flags=re.M), encoding='utf-8')
    print('README actualizados:', rep['fecha_corte'], f"P(Becerra)={p['p_d_gana_final']:.3f}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
