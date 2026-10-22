"""Actualiza el bloque de pronóstico de los README con la última corrida (salidas/ultimo/reporte.json).

Uso:  python scripts/actualizar_readme.py   (desde georgia/produccion; lo llama GitHub Actions)
Escribe entre los marcadores <!-- PRONOSTICO:INICIO --> y <!-- PRONOSTICO:FIN -->:
  - georgia/README.md: tabla de gobernador y senado, gráficas, fuentes
  - README.md (raíz): fila de Georgia en la tabla de estados
Genera además salidas/evolucion.png con la serie de historial_pronosticos.csv.
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
README_GA = PROD.parent / 'README.md'
README_RAIZ = PROD.parent.parent / 'README.md'
INI, FIN = '<!-- PRONOSTICO:INICIO -->', '<!-- PRONOSTICO:FIN -->'


def _reemplazar(texto: str, bloque: str) -> str:
    patron = re.compile(re.escape(INI) + r'.*?' + re.escape(FIN), re.S)
    nuevo = f'{INI}\n{bloque.strip()}\n{FIN}'
    if patron.search(texto):
        return patron.sub(lambda _: nuevo, texto)
    return texto


def evolucion() -> bool:
    h = SAL / 'historial_pronosticos.csv'
    if not h.exists():
        return False
    d = pd.read_csv(h)
    d['corte'] = pd.to_datetime(d.corte)
    d = d.sort_values('ejecutado').groupby('corte').tail(1).sort_values('corte')
    if len(d) < 1:
        return False
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 3.4))
    ax.plot(d.corte, 100 * d.P_D, marker='o', color='#2563eb', label='P(gana Bottoms), final')
    ax.plot(d.corte, 100 * d.P_D_encuestas, marker='.', ls=':', color='#9aa5b1', label='Solo encuestas')
    if d.P_D_kalshi.notna().any():
        ax.plot(d.corte, 100 * d.P_D_kalshi, marker='.', ls='--', color='#d97706', label='Kalshi')
    ax.axhline(50, color='#1f2933', lw=.8)
    ax.set_ylim(0, 100); ax.set_ylabel('%'); ax.legend(frameon=False, fontsize=8, loc='upper left')
    ax.set_title('Evolución del pronóstico · Georgia Gobernador', loc='left', fontsize=10)
    ax.spines[['top', 'right']].set_visible(False)
    import matplotlib.dates as mdates
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=10))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
    if len(d) == 1:
        ax.set_xlim(d.corte.iloc[0] - pd.Timedelta(days=2), d.corte.iloc[0] + pd.Timedelta(days=2))
    fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(SAL / 'evolucion.png', dpi=130); plt.close(fig)
    return True


def main() -> int:
    rep = json.loads((SAL / 'ultimo' / 'reporte.json').read_text(encoding='utf-8'))
    g, s = rep['gobernador'], rep.get('senado')
    ahora = datetime.now(ZoneInfo('America/New_York')).strftime('%Y-%m-%d %H:%M ET')
    vivas = sum(1 for v in rep['estados_fuentes'].values() if str(v).startswith(('en_vivo', 'archivo')))
    total = len(rep['estados_fuentes'])
    tiene_evol = evolucion()
    lineas = [
        f"**Pronóstico al {rep['corte']}** ({rep['dias_a_eleccion']} días a la elección) · actualizado automáticamente {ahora} · fuentes en vivo {vivas}/{total}",
        '',
        '| Gobernador | % de voto (IC80) | Probabilidad de ganar |',
        '|---|---|---|',
        f"| Keisha Lance **Bottoms** (D) | **{g['pct_D']:.1f}%** ({g['pct_D_IC80'][0]:.1f}–{g['pct_D_IC80'][1]:.1f}) | **{g['P_D']:.0%}** |",
        f"| Rick **Jackson** (R) | **{g['pct_R']:.1f}%** ({g['pct_R_IC80'][0]:.1f}–{g['pct_R_IC80'][1]:.1f}) | **{g['P_R']:.0%}** |",
        '',
        f"Margen D−R {g['margen']:+.1f} pp (σ {g['sd']:.1f}) · solo encuestas: P(Bottoms) {g['p_D_encuestas']:.0%} · "
        f"con Kalshi (peso {g['peso_kalshi_aplicado']}) · segunda vuelta {g['P_segunda_vuelta']:.1%} · "
        f"{g['n_encuestas']} encuestas, {g['k']} encuestadoras en la ventana",
    ]
    u = rep.get('ultima_encuesta')
    if u:
        lineas += ['', f"**Encuesta más reciente:** {u['encuestadora']}, terminó el {u['fin']} "
                       f"(**{u['dias_desde_fin']} días** antes del corte). Las fuentes se consultan en vivo, pero el promedio "
                       f"solo puede ser tan reciente como la última encuesta publicada."]
    if s:
        c = s['conjunto']
        lineas += ['', f"**Senado:** Ossoff {s['pct_D']:.1f}% · Collins {s['pct_R']:.1f}% · P(Ossoff) {s['P_D']:.0%} · "
                       f"Jackson+Ossoff {c['P_R_gob_y_D_sen']:.0%} · Bottoms+Ossoff {c['P_D_gob_y_D_sen']:.0%}"]
    lineas += ['', '![Pronóstico](produccion/salidas/ultimo/pronostico.png)']
    if tiene_evol:
        lineas += ['', '![Evolución](produccion/salidas/evolucion.png)']
    lineas += ['', f"Detalle: [`resumen.txt`](produccion/salidas/ultimo/resumen.txt) · "
                   f"[encuestas usadas](produccion/salidas/ultimo/encuestas_gobernador.csv) · "
                   f"[escenarios](produccion/salidas/ultimo/escenarios_gobernador.csv) · "
                   f"[historial](produccion/salidas/historial_pronosticos.csv)"]
    README_GA.write_text(_reemplazar(README_GA.read_text(encoding='utf-8'), '\n'.join(lineas)), encoding='utf-8')
    fila = (f"| Georgia | Gobernador: Bottoms {g['pct_D']:.1f}% · Jackson {g['pct_R']:.1f}% · P(Bottoms) {g['P_D']:.0%} "
            f"(corte {rep['corte']}) | **Producción (V11)**, actualización automática | [`georgia/`](georgia/) |")
    raiz = README_RAIZ.read_text(encoding='utf-8')          # la fila de la tabla se reemplaza completa
    README_RAIZ.write_text(re.sub(r'^\| Georgia \|.*$', lambda _: fila, raiz, count=1, flags=re.M), encoding='utf-8')
    print('README actualizados:', rep['corte'], f"P(Bottoms)={g['P_D']:.3f}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
