"""Escritura de salidas: resumen.txt, reporte.json, CSV, gráfica, historial."""
from __future__ import annotations

import json
import math
import shutil
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

CLAVE = 'alcaldia'


def _p(x) -> str:
    if x is None:
        return '—'
    if 0.999 <= x < 1:
        return '>99.9%'
    if 0 < x < 0.001:
        return '<0.1%'
    return f'{x:.1%}'


def texto_resumen(r: dict, cfg) -> str:
    m, e, mk = r['modelo'], cfg.eleccion, r['mercados']
    f = m['final']
    reg = r.get('registro') or {}
    lin = [f"{e.estado} {e.cargo} {cfg.dia_eleccion.year} · corte {cfg.corte} ({cfg.dias_a_eleccion} días a la elección)"
           + (f" · RECONSTRUCCIÓN (corrida del {cfg.hoy})" if cfg.es_reconstruccion else ''),
           '=' * 78,
           'Primera ronda (RCV, Iniciativa 83):',
           *[f"  {nom:32s} {v:5.1f}%   [IC80 {ic[0]:.1f}–{ic[1]:.1f}]" for nom, v, ic in (
               (f'{e.nombre_d} (D):', f['pct_D'], f['pct_D_IC80']),
               (f'{e.nombre_opositor} (I):', f['pct_opositor'], f['pct_opositor_IC80']),
               (f'{e.nombre_verde} (Verde):', f['pct_verde'], f['pct_verde_IC80']),
               ('Votos por escrito:', f['pct_escrito'], f['pct_escrito_IC80']))],
           f"  Margen {e.candidato_d} − {e.opositor}: {f['margen']:+.1f} pp · IC95 [{f['IC95'][0]:+.1f}, {f['IC95'][1]:+.1f}]",
           f"  P(gana {e.candidato_d}) = {_p(f['P_D'])} · P(gana en la 1.ª ronda, > 50 %) = {_p(f['P_primera_ronda'])} · "
           + ' · '.join(f"P(≥ {k} %) = {_p(v)}" for k, v in f['P_umbral'].items() if k != '50'),
           f"  Base: {f['base']} · M1 logit(%D) = {f['coeficientes']['const']:.3f} {f['coeficientes'].get('fuerte', 0):+.3f}·fuerte "
           f"(σ {f['sigma_logit']:.3f}, {f['n_elecciones']} elecciones, gl {f['gl']}) · LOYO: CRPS {f['crps_loyo']:.2f} pp, "
           f"cobertura IC80 {f['cobertura80_loyo']:.0%}",
           f"  Mercados: Kalshi {_p(mk['kalshi'].get('p_D'))} ({mk['kalshi']['estado'][:40]}) · Polymarket "
           f"{_p(mk['polymarket'].get('p_D'))} ({mk['polymarket']['estado'][:40]}) · peso aplicado {f['peso_mercados_aplicado']}"]
    pe = r.get('promedio_encuestas')
    lin.append(f"  Encuestas de la general: {pe['n_encuestas']} ({pe['k_firmas']} firmas; última {pe['ultima_fin']}) · "
               f"promedio {pe['pct_D']:.1f} % · peso de los fundamentales {f['peso_fundamentales']:.2f}" if pe else
               '  Encuestas de la general: ninguna publicada (las de la primaria no se usan)')
    if reg.get('total'):
        pc = reg['pct']
        lin.append(f"  Registro DCBOE ({reg.get('fecha_informe')}): {reg['total']:,} votantes · D {pc.get('D', 0):.1f} % · "
                   f"sin partido {pc.get('Sin partido', 0):.1f} % · R {pc.get('R', 0):.1f} % · verde {pc.get('Verde', 0):.1f} % "
                   f"(contexto; no entra al pronóstico)")
    lin += ['', 'ESCENARIOS (no cambian el pronóstico):']
    for x in m['escenarios'].itertuples():
        lin.append(f"  {x.escenario[:78]:78s} D {x.pct_D:5.1f}% [{x.pct_D_IC80_bajo:.0f}–{x.pct_D_IC80_alto:.0f}] · "
                   f"P {_p(x.P_D)} · 1.ª ronda {_p(x.P_primera_ronda)}")
    lin += ['', 'FUENTES: ' + ' · '.join(f'{k}={str(x)[:45]}' for k, x in r['estados_fuentes'].items())]
    if r['avisos']:
        lin += ['AVISOS: ' + ' | '.join(r['avisos'])]
    return '\n'.join(lin)


def _limpio(o):
    if isinstance(o, dict):
        return {str(k): _limpio(v) for k, v in o.items()}
    if isinstance(o, (list, tuple, set)):
        return [_limpio(x) for x in o]
    if isinstance(o, pd.DataFrame):
        return _limpio(o.to_dict('records'))
    if isinstance(o, pd.Series):
        return _limpio(o.to_dict())
    if o is None or isinstance(o, (bool, np.bool_)):
        return None if o is None else bool(o)
    if isinstance(o, (int, np.integer)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        return float(o) if math.isfinite(o) else None
    if isinstance(o, (pd.Timestamp, datetime, date)):
        return None if pd.isna(o) else o.isoformat()
    if isinstance(o, str):
        return o
    try:
        if pd.isna(o):
            return None
    except (TypeError, ValueError):
        pass
    return str(o)


def json_estricto(obj) -> str:
    return json.dumps(_limpio(obj), ensure_ascii=False, indent=2, allow_nan=False)


def reporte_json(r: dict, cfg) -> dict:
    from . import __version__
    m, e = r['modelo'], cfg.eleccion
    reg = {k: v for k, v in (r.get('registro') or {}).items()}
    return {'version_modelo': __version__, 'corte': str(cfg.corte), 'dias_a_eleccion': cfg.dias_a_eleccion,
            'estados_fuentes': r['estados_fuentes'], 'avisos': r['avisos'],
            'candidatos': {'D': e.nombre_d, 'opositor': e.nombre_opositor, 'verde': e.nombre_verde},
            CLAVE: m['final'], 'escenarios': m['escenarios'], 'loyo': m['loyo'],
            'boleta': r['eleccion']['boleta'], 'primaria_pct_nominado': r['eleccion'].get('primaria_pct'),
            'mercados': r['mercados'], 'registro': reg,
            'reconstruccion': {'activa': cfg.es_reconstruccion, 'corte': str(cfg.corte), 'corrida': str(cfg.hoy)}}


def escribir(r: dict, cfg) -> Path:
    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    base = cfg.dir_salidas / 'corridas' / ts
    base.mkdir(parents=True, exist_ok=True)
    m, e = r['modelo'], cfg.eleccion
    f = m['final']
    pd.DataFrame([
        {'corte': str(cfg.corte), 'candidato': e.nombre_d, 'partido': 'D', 'pct': f['pct_D'], 'pct_IC80_bajo': f['pct_D_IC80'][0],
         'pct_IC80_alto': f['pct_D_IC80'][1], 'P_ganar': f['P_D']},
        {'corte': str(cfg.corte), 'candidato': e.nombre_opositor, 'partido': 'I', 'pct': f['pct_opositor'],
         'pct_IC80_bajo': f['pct_opositor_IC80'][0], 'pct_IC80_alto': f['pct_opositor_IC80'][1], 'P_ganar': 1 - f['P_D']},
        {'corte': str(cfg.corte), 'candidato': e.nombre_verde, 'partido': 'Verde', 'pct': f['pct_verde'],
         'pct_IC80_bajo': f['pct_verde_IC80'][0], 'pct_IC80_alto': f['pct_verde_IC80'][1], 'P_ganar': 0.0},
        {'corte': str(cfg.corte), 'candidato': 'Votos por escrito', 'partido': '', 'pct': f['pct_escrito'],
         'pct_IC80_bajo': f['pct_escrito_IC80'][0], 'pct_IC80_alto': f['pct_escrito_IC80'][1], 'P_ganar': 0.0}]
    ).to_csv(base / f'pronostico_{CLAVE}.csv', index=False, encoding='utf-8-sig')
    m['escenarios'].to_csv(base / f'escenarios_{CLAVE}.csv', index=False, encoding='utf-8-sig')
    h = r['historico'].drop(columns=['y', 'primaria_pct_respaldo'], errors='ignore')
    h.to_csv(base / 'historico_alcaldias.csv', index=False, encoding='utf-8-sig')
    pd.DataFrame(m['loyo']['por_eleccion']).to_csv(base / 'validacion_loyo.csv', index=False, encoding='utf-8-sig')
    enc = r['encuestas']
    enc.to_csv(base / f'encuestas_{CLAVE}.csv', index=False, encoding='utf-8-sig')
    (base / 'resumen.txt').write_text(r['resumen_texto'], encoding='utf-8')
    (base / 'reporte.json').write_text(json_estricto(reporte_json(r, cfg)), encoding='utf-8')
    if cfg.ejecucion.graficas:
        grafica(r, cfg, base / 'pronostico.png')
    ult = cfg.dir_salidas / 'ultimo'
    if ult.exists():
        shutil.rmtree(ult)
    shutil.copytree(base, ult)
    hist = cfg.dir_salidas / 'historial_pronosticos.csv'
    from . import __version__
    mk = r['mercados']
    fila = pd.DataFrame([{'ejecutado': datetime.now().isoformat(timespec='seconds'), 'version_modelo': __version__,
                          'corte': str(cfg.corte), 'dias': cfg.dias_a_eleccion, 'pct_D': f['pct_D'],
                          'pct_opositor': f['pct_opositor'], 'pct_verde': f['pct_verde'], 'pct_escrito': f['pct_escrito'],
                          'margen': f['margen'], 'sd': f['sd'], 'P_D': f['P_D'], 'P_D_modelo': f['P_D_modelo'],
                          'P_D_fundamentales': f['P_D_fundamentales'], 'P_primera_ronda': f['P_primera_ronda'],
                          'P_D_kalshi': mk['kalshi'].get('p_D'), 'P_D_polymarket': mk['polymarket'].get('p_D'),
                          'peso_mercados': f['peso_mercados_aplicado'], 'n_encuestas': len(r['encuestas']),
                          'base': f['base'], 'fuentes_degradadas': ';'.join(r['degradadas']),
                          'reconstruccion': bool(cfg.es_reconstruccion)}])
    if hist.exists():
        fila = pd.concat([pd.read_csv(hist), fila], ignore_index=True)
    fila.to_csv(hist, index=False, encoding='utf-8-sig')
    corr = sorted((cfg.dir_salidas / 'corridas').iterdir())
    for viejo in corr[:-int(cfg.ejecucion.conservar_corridas)]:
        shutil.rmtree(viejo, ignore_errors=True)
    return base


def grafica(r: dict, cfg, ruta: Path) -> None:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    ink, acc, warm, gris = '#1f2933', '#2563eb', '#d97706', '#9aa5b1'
    m, e = r['modelo'], cfg.eleccion
    f, s, h = m['final'], m['sim'], r['historico']
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.6))
    a = ax[0]
    a.hist(s.D, bins=100, range=(40, 100), color=acc, alpha=.75, density=True, label=e.candidato_d)
    a.hist(s.O, bins=100, range=(0, 60), color=warm, alpha=.6, density=True, label=e.opositor)
    a.axvline(50, color=ink, lw=.8)
    a.set_title(f"Primera ronda · {e.candidato_d} {f['pct_D']:.0f} % · P(gana) {_p(f['P_D'])}", loc='left', color=ink)
    a.set_yticks([]); a.spines[['top', 'right', 'left']].set_visible(False); a.set_xlabel('% de las boletas')
    a.legend(frameon=False, fontsize=9)
    b = ax[1]
    col = np.where(h.fuerte == 1, warm, acc)
    b.scatter(h.anio, h.pct_d, c=col, s=40, zorder=3)
    for x in h.itertuples():
        b.annotate(str(x.anio)[2:], (x.anio, x.pct_d), textcoords='offset points', xytext=(0, 6), ha='center', fontsize=7, color=gris)
    b.errorbar([2026], [f['pct_D']], yerr=[[f['pct_D'] - f['pct_D_IC80'][0]], [f['pct_D_IC80'][1] - f['pct_D']]],
               fmt='s', color=ink, capsize=4, label=f"2026 (IC80): {f['pct_D']:.1f} %")
    b.axhline(50, color=ink, lw=.6)
    b.scatter([], [], c=acc, label='opositor débil'); b.scatter([], [], c=warm, label='opositor fuerte (concejal/alcalde)')
    b.set_ylim(30, 95); b.set_ylabel('% del demócrata'); b.legend(frameon=False, fontsize=8.5, loc='lower left', ncol=2)
    b.set_title('Generales de alcaldía de D.C. 1974–2022', loc='left', color=ink); b.spines[['top', 'right']].set_visible(False)
    fig.tight_layout(); fig.savefig(ruta, dpi=140); plt.close(fig)
