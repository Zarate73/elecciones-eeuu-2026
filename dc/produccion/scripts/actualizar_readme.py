"""Actualiza el bloque de pronóstico de los README con la última corrida (salidas/ultimo/reporte.json).

Uso:  python scripts/actualizar_readme.py   (desde dc/produccion; lo llama GitHub Actions)
Escribe entre los marcadores <!-- PRONOSTICO:INICIO --> y <!-- PRONOSTICO:FIN --> de dc/README.md,
reemplaza (o agrega) la fila de Washington D.C. en la tabla del README raíz y genera salidas/evolucion.png.
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
README_EST = PROD.parent / 'README.md'
README_RAIZ = PROD.parent.parent / 'README.md'
INI, FIN = '<!-- PRONOSTICO:INICIO -->', '<!-- PRONOSTICO:FIN -->'


def _reemplazar(texto: str, bloque: str) -> str:
    patron = re.compile(re.escape(INI) + r'.*?' + re.escape(FIN), re.S)
    return patron.sub(lambda _: f'{INI}\n{bloque.strip()}\n{FIN}', texto)


def evolucion() -> bool:
    h = SAL / 'historial_pronosticos.csv'
    if not h.exists():
        return False
    d = pd.read_csv(h)
    d['corte'] = pd.to_datetime(d.corte)
    d = d.sort_values('ejecutado').groupby('corte').tail(1).sort_values('corte')
    if d.empty:
        return False
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 3.4))
    ax.plot(d.corte, d.pct_D, marker='o', color='#2563eb', label='% Lewis George (1.ª ronda)')
    ax.plot(d.corte, d.pct_opositor, marker='.', color='#d97706', label='% Hamilton')
    ax.axhline(50, color='#1f2933', lw=.8)
    ax.set_ylim(0, 100); ax.set_ylabel('%'); ax.legend(frameon=False, fontsize=8, loc='center left')
    ax.set_title('Evolución del pronóstico · Washington D.C. Alcaldía', loc='left', fontsize=10)
    ax.spines[['top', 'right']].set_visible(False)
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=10))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
    if len(d) == 1:
        ax.set_xlim(d.corte.iloc[0] - pd.Timedelta(days=2), d.corte.iloc[0] + pd.Timedelta(days=2))
    fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(SAL / 'evolucion.png', dpi=130); plt.close(fig)
    return True


def _p(x) -> str:
    """Probabilidad sin mostrar 0 % ni 100 % cuando no lo son (99.8 % → «>99%», 0.2 % → «<1%»)."""
    if x is None:
        return '—'
    if 0.995 <= x < 1:
        return '>99%'
    if 0 < x < 0.005:
        return '<1%'
    return f'{x:.0%}'


def main() -> int:
    rep = json.loads((SAL / 'ultimo' / 'reporte.json').read_text(encoding='utf-8'))
    g, mk, reg = rep['alcaldia'], rep['mercados'], rep.get('registro') or {}
    ahora = datetime.now(ZoneInfo('America/New_York')).strftime('%Y-%m-%d %H:%M ET')
    vivas = sum(1 for v in rep['estados_fuentes'].values() if str(v).startswith(('en_vivo', 'no_aplica')))
    total = len(rep['estados_fuentes'])
    pu = g['P_umbral']
    lineas = [
        f"**Pronóstico al {rep['corte']}** ({rep['dias_a_eleccion']} días a la elección) · actualizado automáticamente "
        f"{ahora} · fuentes en vivo {vivas}/{total}",
        '',
        '| Alcaldía (1.ª ronda RCV) | % de voto (IC80) | Probabilidad de ganar |',
        '|---|---|---|',
        f"| Janeese **Lewis George** (D) | **{g['pct_D']:.1f}%** ({g['pct_D_IC80'][0]:.1f}–{g['pct_D_IC80'][1]:.1f}) | **{_p(g['P_D'])}** |",
        f"| Rhonda **Hamilton** (I) | **{g['pct_opositor']:.1f}%** ({g['pct_opositor_IC80'][0]:.1f}–{g['pct_opositor_IC80'][1]:.1f}) | **{_p(g['P_opositor'])}** |",
        f"| Robert L. **Gross** (Statehood Green) | {g['pct_verde']:.1f}% ({g['pct_verde_IC80'][0]:.1f}–{g['pct_verde_IC80'][1]:.1f}) | — |",
        f"| Votos por escrito | {g['pct_escrito']:.1f}% ({g['pct_escrito_IC80'][0]:.1f}–{g['pct_escrito_IC80'][1]:.1f}) | — |",
        '',
        f"P(Lewis George gana en la primera ronda, > 50 %) **{_p(g['P_primera_ronda'])}** · P(≥ 70 %) {_p(pu.get('70'))} · "
        f"P(≥ 80 %) {_p(pu.get('80'))} · margen sobre Hamilton {g['margen']:+.1f} pp · base: **{g['base']}** "
        f"({g['n_elecciones']} generales 1974–2022; LOYO CRPS {g['crps_loyo']:.1f} pp, cobertura IC80 {g['cobertura80_loyo']:.0%})",
        '',
        f"**Sin encuestas ni mercados de la general.** No hay ninguna encuesta Lewis George–Hamilton publicada y ni Kalshi "
        f"({mk['kalshi']['estado'].split(' (')[0]}) ni Polymarket ({mk['polymarket']['estado'].split(' (')[0]}) tienen mercado "
        f"de esta elección; ambos se buscan en cada corrida y entran solos si aparecen (peso de mercados "
        f"{g['peso_mercados_aplicado']}).",
    ]
    if reg.get('total'):
        pc = reg['pct']
        lineas += ['', f"**Registro** (DCBOE, {reg.get('fecha_informe')}): {reg['total']:,} votantes · demócratas {pc['D']:.1f} %, "
                       f"sin partido {pc.get('Sin partido', 0):.1f} %, republicanos {pc.get('R', 0):.1f} %. Contexto: D.C. no "
                       f"publica voto anticipado por partido y el registro no entra al pronóstico."]
    lineas += ['', '![Pronóstico](produccion/salidas/ultimo/pronostico.png)']
    if evolucion():
        lineas += ['', '![Evolución](produccion/salidas/evolucion.png)']
    lineas += ['', "Detalle: [`resumen.txt`](produccion/salidas/ultimo/resumen.txt) · "
                   "[generales 1974–2022](produccion/salidas/ultimo/historico_alcaldias.csv) · "
                   "[escenarios](produccion/salidas/ultimo/escenarios_alcaldia.csv) · "
                   "[validación LOYO](produccion/salidas/ultimo/validacion_loyo.csv) · "
                   "[historial](produccion/salidas/historial_pronosticos.csv)"]
    README_EST.write_text(_reemplazar(README_EST.read_text(encoding='utf-8'), '\n'.join(lineas)), encoding='utf-8')
    fila = (f"| Washington D.C. | Alcaldía: Lewis George {g['pct_D']:.1f}% · Hamilton {g['pct_opositor']:.1f}% · "
            f"P(Lewis George) {_p(g['P_D'])} (corte {rep['corte']}) | **Producción (general)**, actualización automática | [`dc/`](dc/) |")
    raiz = README_RAIZ.read_text(encoding='utf-8')
    if re.search(r'^\| Washington D\.C\. \|', raiz, re.M):
        raiz = re.sub(r'^\| Washington D\.C\. \|.*$', lambda _: fila, raiz, count=1, flags=re.M)
    elif re.search(r'^\| … \|.*$', raiz, re.M):           # D.C. es el estado 14 de 14: ocupa la fila «pendiente»
        raiz = re.sub(r'^\| … \|.*$', lambda _: fila, raiz, count=1, flags=re.M)
    else:                                                   # sin fila «…»: después de la última fila de estado
        raiz = re.sub(r'(^\| Wisconsin \|.*$)', lambda m_: m_.group(1) + '\n' + fila, raiz, count=1, flags=re.M)
    README_RAIZ.write_text(raiz, encoding='utf-8')
    print('README actualizados:', rep['corte'], f"P(Lewis George)={g['P_D']:.4f}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
