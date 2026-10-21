"""Escritura de salidas: resumen.txt, reporte.json, CSV y gráfica."""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


def texto_resumen(r: dict, cfg) -> str:
    f, e = r['gobernador']['final'], cfg.eleccion
    lin = [f"ODISEO · {e.estado} {e.cargo} {cfg.dia_eleccion.year} · corte {cfg.corte} ({cfg.dias_a_eleccion} días a la elección)",
           '=' * 78,
           f"GOBERNADOR (pronóstico principal)",
           f"  {e.nombre_d} (D): {f['pct_D']:.1f}%   [IC80 {f['pct_D_IC80'][0]:.1f}–{f['pct_D_IC80'][1]:.1f}]",
           f"  {e.nombre_r} (R): {f['pct_R']:.1f}%   [IC80 {f['pct_R_IC80'][0]:.1f}–{f['pct_R_IC80'][1]:.1f}]",
           f"  Margen D−R: {f['margen']:+.1f} pp (σ {f['sd']:.1f}) · IC95 [{f['IC95'][0]:+.1f}, {f['IC95'][1]:+.1f}]",
           f"  P(gana {e.candidato_d}) = {f['P_D']:.1%}   P(gana {e.candidato_r}) = {f['P_R']:.1%}   P(segunda vuelta) = {f['P_segunda_vuelta']:.2%}",
           f"  Solo encuestas: P({e.candidato_d}) = {f['p_D_encuestas']:.1%} · Kalshi: "
           + (f"{r['kalshi']['p_d_normalizada']:.1%} ({r['kalshi']['estado']}, peso {f['peso_kalshi_aplicado']})" if 'p_d_normalizada' in r['kalshi'] else r['kalshi']['estado']),
           f"  Encuestas en ventana: {len(r['gobernador']['ventana'])} de {r['gobernador']['k']} encuestadoras desde {r['gobernador']['nota_ventana']['desde']}"
           + (' (AMPLIADA)' if r['gobernador']['nota_ventana']['ampliada'] else '')]
    if r.get('senado'):
        s, c = r['senado']['senado'], r['senado']['conjunto']
        lin += ['', f"SENADO (adicional, no altera el pronóstico de gobernador)",
                f"  {cfg.senado.candidato_d}: {s['pct_D']:.1f}% · {cfg.senado.candidato_r}: {s['pct_R']:.1f}% · margen {s['margen']:+.1f} · P({cfg.senado.candidato_d}) = {s['P_D']:.1%}",
                f"  Conjunto: {e.candidato_r}+{cfg.senado.candidato_d} {c['P_R_gob_y_D_sen']:.1%} · {e.candidato_d}+{cfg.senado.candidato_d} {c['P_D_gob_y_D_sen']:.1%} · "
                f"{e.candidato_r}+{cfg.senado.candidato_r} {c['P_R_gob_y_R_sen']:.1%} · {e.candidato_d}+{cfg.senado.candidato_r} {c['P_D_gob_y_R_sen']:.1%}"]
    a = r.get('anticipado', {})
    if a.get('delta_vs_2022'):
        d = a['delta_vs_2022']
        lin += ['', f"VOTO ANTICIPADO (diagnóstico, {a['estado']}): vs 2022 al mismo día · % negro {d.get('pct_negro', np.nan):+.1f} pp · "
                    f"% 65+ {d.get('pct_65mas', np.nan):+.1f} pp · boletas {d.get('boletas', np.nan):+,.0f}"]
    lin += ['', 'FUENTES: ' + ' · '.join(f'{k}={str(v)[:40]}' for k, v in r['estados_fuentes'].items())]
    if r['avisos']:
        lin += ['AVISOS: ' + ' | '.join(r['avisos'])]
    return '\n'.join(lin)


def _serializable(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, (pd.Timestamp, datetime)):
        return o.isoformat()
    if isinstance(o, pd.DataFrame):
        return o.to_dict('records')
    return str(o)


def escribir(r: dict, cfg) -> Path:
    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    base = cfg.dir_salidas / 'corridas' / ts
    base.mkdir(parents=True, exist_ok=True)
    g = r['gobernador']
    f = g['final']
    pd.DataFrame([{'corte': str(cfg.corte), 'candidato': cfg.eleccion.nombre_d, 'partido': 'D', 'pct': f['pct_D'],
                   'pct_IC80_bajo': f['pct_D_IC80'][0], 'pct_IC80_alto': f['pct_D_IC80'][1], 'P_ganar': f['P_D']},
                  {'corte': str(cfg.corte), 'candidato': cfg.eleccion.nombre_r, 'partido': 'R', 'pct': f['pct_R'],
                   'pct_IC80_bajo': f['pct_R_IC80'][0], 'pct_IC80_alto': f['pct_R_IC80'][1], 'P_ganar': f['P_R']}]
                 ).to_csv(base / 'pronostico_gobernador.csv', index=False, encoding='utf-8-sig')
    g['escenarios'].to_csv(base / 'escenarios_gobernador.csv', index=False, encoding='utf-8-sig')
    cols = ['fin', 'inicio', 'pollster', 'clave_538', 'pop', 'n', 'D', 'R', 'tipo_pregunta', 'margin_poll',
            'efecto_casa', 'margen_corregido', 'origen', 'fuente', 'nota']
    g['encuestas'].assign(en_ventana=g['encuestas'].index.isin(g['ventana'].index))[cols + ['en_ventana']] \
        .sort_values('fin', ascending=False).to_csv(base / 'encuestas_gobernador.csv', index=False, encoding='utf-8-sig')
    if r.get('senado'):
        s = r['senado']
        pd.DataFrame([{**{f'sen_{k}': v for k, v in s['senado'].items()}, **s['conjunto']}]).to_csv(
            base / 'senado_y_conjunto.csv', index=False, encoding='utf-8-sig')
        s['carrera']['encuestas'][cols].sort_values('fin', ascending=False).to_csv(
            base / 'encuestas_senado.csv', index=False, encoding='utf-8-sig')
    if len(r.get('anticipado', {}).get('tabla', [])):
        r['anticipado']['tabla'].to_csv(base / 'voto_anticipado_diagnostico.csv', index=False, encoding='utf-8-sig')
    (base / 'resumen.txt').write_text(r['resumen_texto'], encoding='utf-8')
    rep = {k: v for k, v in r['reporte'].items()}
    (base / 'reporte.json').write_text(json.dumps(rep, ensure_ascii=False, indent=2, default=_serializable), encoding='utf-8')
    if cfg.ejecucion.graficas:
        grafica(r, cfg, base / 'pronostico.png')
    ult = cfg.dir_salidas / 'ultimo'
    if ult.exists():
        shutil.rmtree(ult)
    shutil.copytree(base, ult)
    hist = cfg.dir_salidas / 'historial_pronosticos.csv'
    fila = pd.DataFrame([{'ejecutado': datetime.now().isoformat(timespec='seconds'), 'corte': str(cfg.corte),
                          'dias': cfg.dias_a_eleccion, 'pct_D': f['pct_D'], 'pct_R': f['pct_R'], 'margen': f['margen'],
                          'sd': f['sd'], 'P_D': f['P_D'], 'P_D_encuestas': f['p_D_encuestas'],
                          'P_D_kalshi': r['kalshi'].get('p_d_normalizada'), 'peso_kalshi': f['peso_kalshi_aplicado'],
                          'n_encuestas': len(g['encuestas']), 'k_ventana': g['k'],
                          'P_D_senado': r['senado']['senado']['P_D'] if r.get('senado') else None,
                          'fuentes_degradadas': ';'.join(r['degradadas'])}])
    fila.to_csv(hist, mode='a', header=not hist.exists(), index=False, encoding='utf-8-sig')
    corr = sorted((cfg.dir_salidas / 'corridas').iterdir())
    for viejo in corr[:-int(cfg.ejecucion.conservar_corridas)]:
        shutil.rmtree(viejo, ignore_errors=True)
    return base


def grafica(r: dict, cfg, ruta: Path) -> None:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    ink, acc, mute, warm = '#1f2933', '#2563eb', '#9aa5b1', '#d97706'
    g, f = r['gobernador'], r['gobernador']['final']
    M = r['gobernador']['sim'][0]
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.6))
    a = ax[0]
    a.hist(M, bins=120, range=(-25, 20), color=acc, alpha=.75, density=True)
    a.axvline(0, color=ink, lw=.8)
    a.set_title(f"Margen {cfg.eleccion.candidato_d} − {cfg.eleccion.candidato_r} · P({cfg.eleccion.candidato_d}) = {f['P_D']:.0%}",
                loc='left', color=ink)
    a.set_yticks([]); a.spines[['top', 'right', 'left']].set_visible(False); a.set_xlabel('pp')
    b = ax[1]
    e = g['encuestas']
    b.scatter(e.fin, e.margen_corregido, s=np.sqrt(e.n) * 1.6, color=acc, alpha=.75, label='Encuestas (corregidas por casa)')
    b.axhline(0, color=ink, lw=.8)
    b.axhline(g['mu'], color=acc, ls=':', lw=1, label=f"Modelo encuestas: {g['mu']:+.1f}")
    b.axhline(f['mu_final'], color=warm, ls='--', lw=1, label=f"Final con Kalshi: {f['mu_final']:+.1f}")
    b.legend(frameon=False, fontsize=8.5, loc='upper right'); b.spines[['top', 'right']].set_visible(False)
    b.set_title('Encuestas y pronóstico', loc='left', color=ink); b.set_ylabel('margen D−R (pp)')
    fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(ruta, dpi=140); plt.close(fig)
