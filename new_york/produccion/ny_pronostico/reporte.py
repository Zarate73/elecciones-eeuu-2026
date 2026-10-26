"""Escritura de salidas: resumen.txt, reporte.json, CSV, gráfica, historial."""
from __future__ import annotations

import json
import math
import shutil
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd


def _pct(x) -> str:
    return '—' if x is None else f'{x:.1%}'


def texto_resumen(r: dict, cfg) -> str:
    m, e, mk = r['modelo'], cfg.eleccion, r['mercados']
    f = m['final']
    v = f['ventana']
    lin = [f"{e.estado} {e.cargo} {cfg.dia_eleccion.year} · corte {cfg.corte} ({cfg.dias_a_eleccion} días a la elección)",
           '=' * 78,
           f"  {e.nombre_d} (D): {f['pct_D']:.1f}%   [IC80 {f['pct_D_IC80'][0]:.1f}–{f['pct_D_IC80'][1]:.1f}]",
           f"  {e.nombre_r} (R): {f['pct_R']:.1f}%   [IC80 {f['pct_R_IC80'][0]:.1f}–{f['pct_R_IC80'][1]:.1f}]",
           f"  Terceros: {f['pct_terceros']:.1f}%   [IC80 {f['pct_terceros_IC80'][0]:.1f}–{f['pct_terceros_IC80'][1]:.1f}]"
           + (f"   ({f['terceros_regimen']})" if f.get('terceros_regimen') else ''),
           f"  Margen D−R: {f['margen']:+.1f} pp (σ {f['sd']:.1f}) · IC95 [{f['IC95'][0]:+.1f}, {f['IC95'][1]:+.1f}]",
           f"  P(gana {e.candidato_d}) = {f['P_D']:.1%}   P(gana {e.candidato_r}) = {1 - f['P_D']:.1%}   "
           f"P(recuento, |margen| ≤ {cfg.eleccion.recuento_pp} pp) = {f['P_recuento']:.1%}",
           f"  Solo encuestas: {f['P_D_encuestas']:.1%} · Kalshi {_pct(mk['kalshi'].get('p_D'))} ({mk['kalshi']['estado'][:30]}) · "
           f"Polymarket {_pct(mk['polymarket'].get('p_D'))} ({mk['polymarket']['estado'][:30]}) · peso mercados {f['peso_mercados_aplicado']}",
           f"  Ventana: {len(m['ventana'])} encuestas de {f['k']} encuestadoras desde {v['desde']}"
           + (f" (AMPLIADA, regla {v['regla']})" if v['ampliada'] else '')
           + (f" · deriva por {f['dias_extra_encuestas']} días de antigüedad" if f['dias_extra_encuestas'] else ''),
           f"  Última encuesta: {r['ultima_encuesta']['encuestadora']}, terminó el {r['ultima_encuesta']['fin']} "
           f"({r['ultima_encuesta']['dias_desde_fin']} días antes del corte). Fuentes en vivo ≠ encuestas recientes."]
    if f.get('sesgo_estatal_aplicado'):
        lin.insert(9, f"  Sesgo estatal: {-f['sesgo_estatal_aplicado']:+.2f} pp (bruto {-f['sesgo_estatal_bruto']:+.2f}, "
                      f"contracción {f['contraccion_sesgo']:.2f}) · promedio de encuestas {f['margen_encuestas']:+.2f} · "
                      f"mercados desplazan {f['desplazamiento_mercados_pp']:+.2f} pp")
    rg0 = mk.get('rangos', {})
    if mk.get('kalshi_independiente') is not None or rg0.get('P_independiente') is not None:   # solo con independiente
        lin.append(f"  Con independiente (mayoría simple): P(gana {e.candidato_d}) = {f['P_D_gana_3']:.1%} · "
                   f"P(supera a {e.candidato_r}) = {f['P_D']:.1%} · P(un tercero gana), cota del modelo = "
                   f"{f['P_tercero_gana_cota']:.2%} · mercados: Kalshi {_pct(mk.get('kalshi_independiente'))}, "
                   f"Polymarket «gana un independiente» {_pct(rg0.get('P_independiente'))}")
    imp = m['ventana'][m['ventana'].get('n_imputado', pd.Series(False, index=m['ventana'].index)).astype(bool)]
    if len(imp):
        lin.append('  n imputado en 600 (la fuente no lo publica): ' + ', '.join(imp.pollster.astype(str)))
    rg = mk.get('rangos', {})
    if 'suma_precios' in rg:            # diagnóstico: no entra a la distribución publicada
        lin += ['', f"POLYMARKET POR RANGOS (diagnóstico, {rg['estado'][:30]}): {rg['n_contratos']} contratos, "
                    f"suma de precios {rg['suma_precios']:.3f} antes de normalizar · "
                    + (f"P(D) {rg['P_D']:.1%} (partición completa) · margen ajustado {rg['margen_media']:+.1f} "
                       f"(σ {rg['margen_sd']:.1f}; condicional a que gane un partido principal) · " if rg.get('completo') else 'partición INCOMPLETA: sin P(D) ni margen incondicional · ')
                    + (f"E[margen | gana D] {rg['margen_cond_D']:+.1f}" if 'margen_cond_D' in rg else '')]
    a = r.get('anticipado', {})
    if a.get('disponible') and a.get('tipo') == 'nyc_checkins':
        lin += ['', f"VOTO ANTICIPADO EN NYC (Junta Electoral de NYC, check-ins no oficiales, diagnóstico, {a['estado'][:30]}, "
                    f"día {a['dia']}, al {a['fecha']}): {a['emitidos']:,} en persona · "
                    + ' · '.join(f"{x.condado} {x.emitidos:,}" for x in a['condados'].itertuples())
                    + " · solo la ciudad y solo en persona; sin partido"]
    elif a.get('disponible') and a.get('por_partido') is False:
        lin += ['', f"VOTO YA EMITIDO (civicAPI, diagnóstico, {a['estado'][:30]}, al {a['fecha']}): {a['emitidos']:,} "
                    f"({a['por_correo']:,} correo · {a['en_persona']:,} en persona)"
                    + (f" · {a['pct_del_total_previo']:.0f} % del total de votos de 2022" if a.get('pct_del_total_previo') else '')
                    + f" · {a['condado_principal']} {a['condado_principal_pct']:.1f} % · sin registro partidario: "
                      f"solo volumen, sin desglose por partido"]
    elif a.get('disponible'):
        lin += ['', f"VOTO YA EMITIDO (civicAPI, diagnóstico, {a['estado'][:30]}, al {a['fecha']}): {a['emitidos']:,} "
                    f"({a['por_correo']:,} correo · {a['en_persona']:,} en persona) · D {a['pct_D']:.1f}% · R {a['pct_R']:.1f}% · "
                    + (f"NPA {a['pct_NPA']:.1f}% · " if a['pct_NPA'] > 0 else f"otros e independientes {a['pct_Otros']:.1f}% · ")
                    + f"margen D−R {a['margen_DR_pp']:+.1f} (correo {a['margen_DR_correo_pp']:+.1f}, "
                    + (f"en persona {a['margen_DR_persona_pp']:+.1f})" if a.get('tiene_en_persona', True) else "sin voto anticipado en persona en el estado)")
                    + " · registro de partido, no intención de voto"]
    lin += ['', 'FUENTES: ' + ' · '.join(f'{k}={str(x)[:40]}' for k, x in r['estados_fuentes'].items())]
    if r['avisos']:
        lin += ['AVISOS: ' + ' | '.join(r['avisos'])]
    return '\n'.join(lin)


def _limpio(o):
    """Convierte a tipos JSON estándar: NaN/±inf -> null, numpy -> nativos, fechas -> ISO, tablas -> registros."""
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
    """JSON válido según el estándar (RFC 8259): sin NaN ni Infinity; falla si quedara alguno."""
    return json.dumps(_limpio(obj), ensure_ascii=False, indent=2, allow_nan=False)


def reporte_json(r: dict, cfg) -> dict:
    m, mk, a = r['modelo'], r['mercados'], r['anticipado']
    from . import __version__
    return {'version_modelo': __version__, 'corte': str(cfg.corte), 'dias_a_eleccion': cfg.dias_a_eleccion, 'estados_fuentes': r['estados_fuentes'],
            'avisos': r['avisos'], 'conteos_encuestas': r['conteos'], 'ultima_encuesta': r['ultima_encuesta'],
            'gobernador': {**m['final'], 'n_encuestas': len(m['encuestas'])},
            'escenarios': m['escenarios'],
            'mercados': {'kalshi': mk['kalshi'], 'polymarket': mk['polymarket'], 'promedio_D': mk['promedio_D'],
                         'kalshi_independiente': mk.get('kalshi_independiente'),
                         'dif_pp': mk['dif_pp'], 'rangos': {k: v for k, v in mk['rangos'].items() if k != 'tabla'}},
            'anticipado': {k: v for k, v in a.items() if k != 'condados'},
            'calibracion': {k: v for k, v in r['calibracion'].items() if not k.startswith('efectos_casa')}}


def escribir(r: dict, cfg) -> Path:
    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    base = cfg.dir_salidas / 'corridas' / ts
    base.mkdir(parents=True, exist_ok=True)
    m, e = r['modelo'], cfg.eleccion
    f = m['final']
    pd.DataFrame([
        {'corte': str(cfg.corte), 'candidato': e.nombre_d, 'partido': 'D', 'pct': f['pct_D'],
         'pct_IC80_bajo': f['pct_D_IC80'][0], 'pct_IC80_alto': f['pct_D_IC80'][1], 'P_ganar': f['P_D']},
        {'corte': str(cfg.corte), 'candidato': e.nombre_r, 'partido': 'R', 'pct': f['pct_R'],
         'pct_IC80_bajo': f['pct_R_IC80'][0], 'pct_IC80_alto': f['pct_R_IC80'][1], 'P_ganar': 1 - f['P_D']},
        {'corte': str(cfg.corte), 'candidato': e.get('terceros', 'Terceros'), 'partido': 'otros',
         'pct': f['pct_terceros'], 'pct_IC80_bajo': f['pct_terceros_IC80'][0],
         'pct_IC80_alto': f['pct_terceros_IC80'][1], 'P_ganar': 0.0}]
    ).to_csv(base / 'pronostico_gobernador.csv', index=False, encoding='utf-8-sig')
    m['escenarios'].to_csv(base / 'escenarios_gobernador.csv', index=False, encoding='utf-8-sig')
    cols = ['fin', 'inicio', 'pollster', 'clave', 'pop', 'n', 'n_fuente', 'D', 'R', 'otros', 'indecisos', 'margin_poll',
            'efecto_casa', 'margen_corregido', 'partidista', 'origen', 'tambien_en', 'en_ventana']
    m['encuestas'][cols].sort_values('fin', ascending=False).to_csv(base / 'encuestas_gobernador.csv', index=False,
                                                                     encoding='utf-8-sig')
    m['ventana'][['fin', 'pollster', 'n', 'n_fuente', 'D', 'R', 'margin_poll', 'efecto_casa', 'margen_corregido', 'patrocinador',
                  'efecto_partidista', 'peso']].to_csv(base / 'encuestas_ventana_pesos.csv', index=False, encoding='utf-8-sig')
    if r['anticipado'].get('disponible'):
        r['anticipado']['condados'].to_csv(base / 'voto_anticipado_condados.csv', index=False, encoding='utf-8-sig')
    if 'tabla' in r['mercados']['rangos']:
        r['mercados']['rangos']['tabla'].to_csv(base / 'polymarket_rangos_margen.csv', index=False, encoding='utf-8-sig')
    (base / 'resumen.txt').write_text(r['resumen_texto'], encoding='utf-8')
    (base / 'reporte.json').write_text(json_estricto(reporte_json(r, cfg)), encoding='utf-8')
    if cfg.ejecucion.graficas:
        grafica(r, cfg, base / 'pronostico.png')
    ult = cfg.dir_salidas / 'ultimo'
    if ult.exists():
        shutil.rmtree(ult)
    shutil.copytree(base, ult)
    mk = r['mercados']
    hist = cfg.dir_salidas / 'historial_pronosticos.csv'
    from . import __version__
    fila = pd.DataFrame([{'ejecutado': datetime.now().isoformat(timespec='seconds'), 'version_modelo': __version__.split()[0], 'corte': str(cfg.corte),
                   'dias': cfg.dias_a_eleccion, 'pct_D': f['pct_D'], 'pct_R': f['pct_R'], 'pct_terceros': f['pct_terceros'],
                   'margen': f['margen'], 'sd': f['sd'], 'P_D': f['P_D'], 'P_D_encuestas': f['P_D_encuestas'],
                   'P_D_kalshi': mk['kalshi'].get('p_D'), 'P_D_polymarket': mk['polymarket'].get('p_D'),
                   'peso_mercados': f['peso_mercados_aplicado'], 'P_recuento': f['P_recuento'],
                   'n_encuestas': len(m['encuestas']), 'k_ventana': f['k'],
                   'ultima_encuesta_fin': r['ultima_encuesta']['fin'], 'dias_desde_ultima_encuesta': r['ultima_encuesta']['dias_desde_fin'],
                   'sesgo_estatal': f.get('sesgo_estatal_aplicado'), 'desplazamiento_mercados': f['desplazamiento_mercados_pp'],
                   'emitidos_anticipado': r['anticipado'].get('emitidos'), 'margen_DR_anticipado': r['anticipado'].get('margen_DR_pp'),
                   'fuentes_degradadas': ';'.join(r['degradadas'])}])
    # se reescribe completo: si cambian las columnas (versión nueva) el CSV sigue siendo rectangular
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
    ink, acc, warm = '#1f2933', '#2563eb', '#d97706'
    m, e = r['modelo'], cfg.eleccion
    f = m['final']
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.6))
    a = ax[0]
    a.hist(m['sim'].M, bins=120, range=(-30, 20), color=acc, alpha=.75, density=True)
    a.axvline(0, color=ink, lw=.8)
    a.set_title(f"Margen {e.candidato_d} − {e.candidato_r} · P({e.candidato_d}) = {f['P_D']:.0%}", loc='left', color=ink)
    a.set_yticks([]); a.spines[['top', 'right', 'left']].set_visible(False); a.set_xlabel('pp')
    b = ax[1]
    p = m['encuestas']
    b.scatter(p.fin, p.margen_corregido, s=np.sqrt(p.n) * 1.6, color=np.where(p.en_ventana, acc, '#9aa5b1'),
              alpha=.8, label='Encuestas (corregidas por casa; azul = en la ventana)')
    b.axhline(0, color=ink, lw=.8)
    b.axhline(f['margen'], color=warm, ls='--', lw=1, label=f"Pronóstico: {f['margen']:+.1f}")
    b.legend(frameon=False, fontsize=8.5, loc='upper left'); b.spines[['top', 'right']].set_visible(False)
    b.set_title('Encuestas desde la primaria', loc='left', color=ink); b.set_ylabel('margen D−R (pp)')
    fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(ruta, dpi=140); plt.close(fig)
