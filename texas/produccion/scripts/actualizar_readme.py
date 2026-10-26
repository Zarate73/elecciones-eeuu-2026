"""Actualiza el bloque de pronóstico de los README con la última corrida (salidas/ultimo/reporte.json).

Uso:  python scripts/actualizar_readme.py   (desde texas/produccion; lo llama GitHub Actions)
Escribe entre los marcadores <!-- PRONOSTICO:INICIO --> y <!-- PRONOSTICO:FIN --> de texas/README.md,
reemplaza (o agrega) la fila de Texas en la tabla del README raíz y genera salidas/evolucion.png.
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
    ax.plot(d.corte, 100 * d.P_D, marker='o', color='#2563eb', label='P(gana Hinojosa), final')
    ax.plot(d.corte, 100 * d.P_D_encuestas, marker='.', ls=':', color='#9aa5b1', label='Solo encuestas')
    for col, color, nom in (('P_D_kalshi', '#d97706', 'Kalshi'), ('P_D_polymarket', '#7c3aed', 'Polymarket')):
        if d[col].notna().any():
            ax.plot(d.corte, 100 * d[col], marker='.', ls='--', color=color, label=nom)
    ax.axhline(50, color='#1f2933', lw=.8)
    ax.set_ylim(0, 100); ax.set_ylabel('%'); ax.legend(frameon=False, fontsize=8, loc='lower left')
    ax.set_title('Evolución del pronóstico · Texas Gobernador', loc='left', fontsize=10)
    ax.spines[['top', 'right']].set_visible(False)
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=10))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
    if len(d) == 1:
        ax.set_xlim(d.corte.iloc[0] - pd.Timedelta(days=2), d.corte.iloc[0] + pd.Timedelta(days=2))
    fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(SAL / 'evolucion.png', dpi=130); plt.close(fig)
    return True


def _ventaja(x: float) -> str:
    return f"D+{x:.1f}" if x >= 0 else f"R+{-x:.1f}"


def _p(x) -> str:
    """Probabilidad redondeada sin mostrar 0 % ni 100 % cuando no lo son (99.7 % → «>99%», 0.3 % → «<1%»)."""
    if x is None:
        return '—'
    if 0.995 <= x < 1:
        return '>99%'
    if 0 < x < 0.005:
        return '<1%'
    return f'{x:.0%}'


def main() -> int:
    rep = json.loads((SAL / 'ultimo' / 'reporte.json').read_text(encoding='utf-8'))
    g, mk, a = rep['gobernador'], rep['mercados'], rep.get('anticipado', {})
    ahora = datetime.now(ZoneInfo('America/Chicago')).strftime('%Y-%m-%d %H:%M CT')   # hora del centro
    vivas = sum(1 for v in rep['estados_fuentes'].values() if str(v).startswith(('en_vivo', 'archivo')))
    total = len(rep['estados_fuentes'])
    lineas = [
        f"**Pronóstico al {rep['corte']}** ({rep['dias_a_eleccion']} días a la elección) · actualizado automáticamente "
        f"{ahora} · fuentes en vivo {vivas}/{total}",
        '',
        '| Gobernador | % de voto (IC80) | Probabilidad de ganar |',
        '|---|---|---|',
        f"| Gina **Hinojosa** (D) | **{g['pct_D']:.1f}%** ({g['pct_D_IC80'][0]:.1f}–{g['pct_D_IC80'][1]:.1f}) | **{_p(g['P_D'])}** |",
        f"| Greg **Abbott** (R, gobernador) | **{g['pct_R']:.1f}%** ({g['pct_R_IC80'][0]:.1f}–{g['pct_R_IC80'][1]:.1f}) | **{_p(1 - g['P_D'])}** |",
        f"| Terceros (Pat Dixon, L; otros) | {g['pct_terceros']:.1f}% ({g['pct_terceros_IC80'][0]:.1f}–{g['pct_terceros_IC80'][1]:.1f}) | — |",
        '',
        f"Margen D−R {g['margen']:+.1f} pp (σ {g['sd']:.1f}) · solo encuestas: P(Hinojosa) {_p(g['P_D_encuestas'])} · "
        f"Kalshi {_p(mk['kalshi'].get('p_D'))} · Polymarket {_p(mk['polymarket'].get('p_D'))} "
        f"(peso de mercados {g['peso_mercados_aplicado']}) · resultado muy estrecho (|margen| ≤ 0.5) {g['P_recuento']:.1%} · "
        f"{g['n_encuestas']} encuestas, {g['k']} encuestadoras en la ventana",
    ]
    if g.get('sesgo_estatal_aplicado'):
        lineas += ['', f"Cómo se llega: promedio de encuestas {g['margen_encuestas']:+.1f} · sesgo estatal de Texas "
                       f"{-g['sesgo_estatal_aplicado']:+.1f} · "
                       f"mercados {g['desplazamiento_mercados_pp']:+.1f}"]
    pi = mk.get('rangos', {}).get('P_independiente')
    if 'P_D_gana_3' in g and (mk.get('kalshi_independiente') is not None or pi is not None):   # solo con independiente
        lineas += ['', f"**Con independiente** (mayoría simple): P(Hinojosa gana) {_p(g['P_D_gana_3'])} · P(un tercero gana) "
                       f"en el modelo {_p(g['P_tercero_gana_cota'])} · en los mercados Kalshi {_p(mk.get('kalshi_independiente'))} "
                       f"y Polymarket {_p(pi)}."]
    u = rep.get('ultima_encuesta')
    if u:
        lineas += ['', f"**Encuesta más reciente:** {u['encuestadora']}, terminó el {u['fin']} "
                       f"(**{u['dias_desde_fin']} días** antes del corte). Las fuentes se consultan en vivo, pero el promedio "
                       f"solo puede ser tan reciente como la última encuesta publicada."]
    if a.get('disponible'):
        lineas += ['', f"**Voto anticipado ya emitido** (civicAPI, diagnóstico, al {a['fecha']}): {a['emitidos']:,} "
                       f"({a['en_persona']:,} en persona, {a['por_correo']:,} por correo)"
                       + (f" · {a['pct_del_total_previo']:.0f} % del total de votos de 2022" if a.get('pct_del_total_previo') else '')
                       + f". Texas no tiene registro partidario: es solo volumen, no indica el resultado y no entra al pronóstico."]
    lineas += ['', '![Pronóstico](produccion/salidas/ultimo/pronostico.png)']
    if evolucion():
        lineas += ['', '![Evolución](produccion/salidas/evolucion.png)']
    lineas += ['', "Detalle: [`resumen.txt`](produccion/salidas/ultimo/resumen.txt) · "
                   "[encuestas usadas](produccion/salidas/ultimo/encuestas_gobernador.csv) · "
                   "[escenarios](produccion/salidas/ultimo/escenarios_gobernador.csv) · "
                   "[voto anticipado por condado](produccion/salidas/ultimo/voto_anticipado_condados.csv) · "
                   "[historial](produccion/salidas/historial_pronosticos.csv)"]
    README_EST.write_text(_reemplazar(README_EST.read_text(encoding='utf-8'), '\n'.join(lineas)), encoding='utf-8')
    fila = (f"| Texas | Gobernador: Hinojosa {g['pct_D']:.1f}% · Abbott {g['pct_R']:.1f}% · P(Hinojosa) {_p(g['P_D'])} "
            f"(corte {rep['corte']}) | **Producción (general)**, actualización automática | [`texas/`](texas/) |")
    raiz = README_RAIZ.read_text(encoding='utf-8')
    if re.search(r'^\| Texas \|', raiz, re.M):
        raiz = re.sub(r'^\| Texas \|.*$', lambda _: fila, raiz, count=1, flags=re.M)
    else:                                                   # primera vez: antes de la fila «…»
        raiz = re.sub(r'^\| … \|', lambda m_: fila + '\n' + m_.group(0), raiz, count=1, flags=re.M)
    README_RAIZ.write_text(raiz, encoding='utf-8')
    print('README actualizados:', rep['corte'], f"P(Hinojosa)={g['P_D']:.3f}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
