"""Exporta los resultados de cada estado a un formato común para el tablero (tablero/datos/*.json).

Uso:  python scripts/exportar_tablero.py            (desde la raíz; lo llama cada flujo de pronóstico)
Lee <estado>/produccion/salidas/ultimo/{reporte.json, encuestas…csv} y salidas/historial_pronosticos.csv.
Escribe JSON estricto (sin NaN): tablero/datos/<estado>.json e tablero/datos/indice.json.
Si un estado no tiene salidas todavía, se omite sin error.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / 'tablero' / 'datos'


def _num(x, nd=4):
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return round(f, nd) if math.isfinite(f) else None


def _limpio(o):
    if isinstance(o, dict):
        return {k: _limpio(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_limpio(v) for v in o]
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    return o


def _vivo(v) -> bool:
    return str(v).startswith(('en_vivo', 'archivo', 'api_en_vivo', 'Datos de Civiq'))


def _fuentes(est: dict) -> list:
    return [{'nombre': k, 'estado': str(v)[:120], 'en_vivo': _vivo(v)} for k, v in est.items()]


def _historial(ruta: Path, col_corte, cols: dict) -> list:
    if not ruta.exists():
        return []
    h = pd.read_csv(ruta, encoding='utf-8-sig')
    orden = 'ejecutado' if 'ejecutado' in h else 'generado'
    h = h.sort_values(orden).groupby(col_corte).tail(1).sort_values(col_corte)
    return [{'corte': str(r[col_corte])[:10], **{k: _num(r.get(v)) for k, v in cols.items()}} for _, r in h.iterrows()]


def _encuestas(df: pd.DataFrame, fin, firma, d, r, ventana, origen, peso=None, n=200) -> list:
    df = df.copy()
    df['_fin'] = pd.to_datetime(df[fin].astype(str).str[:10], errors='coerce')
    df = df.sort_values('_fin', ascending=False).head(n)
    out = []
    for _, x in df.iterrows():
        out.append({'fin': x._fin.date().isoformat() if pd.notna(x._fin) else None, 'encuestadora': str(x[firma]),
                    'D': _num(x[d], 2), 'R': _num(x[r], 2), 'margen': _num(float(x[d]) - float(x[r]), 2),
                    'en_ventana': bool(x[ventana]) if ventana in x and pd.notna(x[ventana]) else None,
                    'origen': str(x[origen]) if origen in x else None,
                    'peso': _num(x[peso], 4) if peso and peso in x else None})
    return out


def _escenarios(lista, nombre='escenario', margen='margen', p='P_D') -> list:
    return [{'escenario': e.get(nombre), 'margen': _num(e.get(margen), 3), 'P_D': _num(e.get(p), 4)} for e in lista
            if e.get(p) is not None]


# ------------------------------------------------------------------------------------ Georgia
def georgia() -> dict | None:
    s = RAIZ / 'georgia/produccion/salidas'
    if not (s / 'ultimo/reporte.json').exists():
        return None
    r = json.loads((s / 'ultimo/reporte.json').read_text(encoding='utf-8'))
    g, k = r['gobernador'], r['kalshi']
    enc = pd.read_csv(s / 'ultimo/encuestas_gobernador.csv', encoding='utf-8-sig')
    a = r.get('anticipado') or {}
    dv = a.get('delta_vs_2022') or {}
    sen = r.get('senado')
    return {
        'clave': 'georgia', 'estado': 'Georgia', 'cargo': 'Gobernador', 'modelo': 'V11',
        'candidatos': {'D': 'Keisha Lance Bottoms', 'R': 'Rick Jackson'}, 'corte': r['corte'],
        'dias_a_eleccion': r['dias_a_eleccion'],
        'pronostico': {'P_D': _num(g['P_D']), 'pct_D': _num(g['pct_D'], 2), 'pct_D_IC80': [_num(x, 2) for x in g['pct_D_IC80']],
                       'pct_R': _num(g['pct_R'], 2), 'pct_R_IC80': [_num(x, 2) for x in g['pct_R_IC80']],
                       'pct_terceros': None, 'margen': _num(g['margen'], 3), 'margen_IC80': [_num(x, 2) for x in g['IC80']],
                       'margen_IC95': [_num(x, 2) for x in g['IC95']], 'sd': _num(g['sd'], 3),
                       'nu': _num(r['calibracion'].get('nu'), 2), 'P_D_encuestas': _num(g['p_D_encuestas']),
                       'peso_mercados': _num(g['peso_kalshi_aplicado'], 2),
                       'mercado_en_distribucion': True,
                       'extra': [{'etiqueta': 'Segunda vuelta (ninguno > 50 %)', 'valor': _num(g['P_segunda_vuelta'])}]},
        'mercados': [{'nombre': 'Kalshi', 'P_D': _num(k.get('p_d_normalizada')), 'estado': k.get('estado')}],
        'ultima_encuesta': r.get('ultima_encuesta'),
        'encuestas': _encuestas(enc, 'fin', 'pollster', 'D', 'R', 'en_ventana', 'origen'),
        'n_encuestas_ventana': g.get('k'),
        'historial': _historial(s / 'historial_pronosticos.csv', 'corte',
                                {'P_D': 'P_D', 'P_D_encuestas': 'P_D_encuestas', 'P_kalshi': 'P_D_kalshi',
                                 'pct_D': 'pct_D', 'margen': 'margen'}),
        'escenarios': _escenarios(r.get('escenarios', [])),
        'anticipado': ({'fuente': 'Civic Forge', 'fecha': a.get('fecha_datos'), 'estado': a.get('estado'),
                        'metricas': [{'etiqueta': 'Boletas vs 2022 (mismo día)', 'valor': _num(dv.get('boletas'), 0), 'formato': 'entero_signo'},
                                     {'etiqueta': '% votantes negros vs 2022', 'valor': _num(dv.get('pct_negro'), 2), 'formato': 'pp'},
                                     {'etiqueta': '% 65+ vs 2022', 'valor': _num(dv.get('pct_65mas'), 2), 'formato': 'pp'}]}
                       if dv else None),
        'adicional': ({'titulo': 'Senado (Ossoff vs Collins)', 'P_D': _num(sen['P_D']), 'pct_D': _num(sen['pct_D'], 2),
                       'pct_R': _num(sen['pct_R'], 2), 'margen': _num(sen['margen'], 2),
                       'nota': f"Voto dividido (gobernador R + senado D): {sen['conjunto']['P_R_gob_y_D_sen']:.0%}"}
                      if sen else None),
        'fuentes': _fuentes(r['estados_fuentes']), 'avisos': r.get('avisos', []),
        'carpeta': 'georgia',
    }


# ------------------------------------------------------------------------------------ California
def california() -> dict | None:
    s = RAIZ / 'california/produccion/salidas'
    if not (s / 'ultimo/reporte.json').exists():
        return None
    r = json.loads((s / 'ultimo/reporte.json').read_text(encoding='utf-8'))
    p, m5, k = r['pronostico'], r['m5'], r['kalshi']
    q = m5.get('cuantiles_margen_pp', {})
    enc = pd.read_csv(s / 'ultimo/encuestas_pesos.csv', encoding='utf-8-sig')
    enc = enc[enc.Incluida.astype(str).str.lower() == 'true'] if 'Incluida' in enc else enc
    enc['fin'] = enc['Fecha de campo'].astype(str).str.split('–').str[-1]
    enc['en_ventana'] = pd.to_numeric(enc['Peso M5'], errors='coerce') > 0
    hi = (r.get('participacion_m2') or {}).get('historico') or {}
    refs = hi.get('margen_referencias_mismo_dia_pp') or {}
    desplazado = bool(abs(m5.get('desplazamiento_kalshi_pp') or 0) > 1e-9)
    return {
        'clave': 'california', 'estado': 'California', 'cargo': 'Gobernador', 'modelo': 'M5',
        'candidatos': {'D': 'Xavier Becerra', 'R': 'Steve Hilton'}, 'corte': r['fecha_corte'],
        'dias_a_eleccion': r['dias_a_eleccion'],
        'pronostico': {'P_D': _num(p['p_d_gana_final']), 'pct_D': _num(p['pct_d'], 2), 'pct_D_IC80': [_num(x, 2) for x in p['ic80_pct_d']],
                       'pct_R': _num(p['pct_r'], 2), 'pct_R_IC80': [_num(100 - p['ic80_pct_d'][1], 2), _num(100 - p['ic80_pct_d'][0], 2)],
                       'pct_terceros': None, 'margen': _num(p['margen_pp'], 3),
                       'margen_IC80': [_num(q.get('10'), 2), _num(q.get('90'), 2)],
                       'margen_IC95': [_num(q.get('2.5'), 2), _num(q.get('97.5'), 2)], 'sd': _num(m5['sigma_pp'], 3),
                       'nu': 5.0, 'P_D_encuestas': _num(p['p_d_gana_modelo']), 'peso_mercados': _num(m5.get('w_kalshi'), 2),
                       'mercado_en_distribucion': desplazado, 'extra': []},
        'mercados': [{'nombre': 'Kalshi', 'P_D': _num(k.get('p_d_normalizada')), 'estado': k.get('estado')}],
        'ultima_encuesta': r.get('ultima_encuesta'),
        'encuestas': _encuestas(enc, 'fin', 'Encuestadora', 'Becerra original %', 'Hilton original %', 'en_ventana',
                                'Origen', 'Peso M5'),
        'n_encuestas_ventana': int(enc.en_ventana.sum()),
        'historial': _historial(s / 'historial_pronosticos.csv', 'fecha_corte',
                                {'P_D': 'p_d_final', 'P_D_encuestas': 'p_d_modelo', 'P_kalshi': 'p_kalshi',
                                 'pct_D': 'pct_becerra', 'margen': 'margen_pp'}),
        'escenarios': [],
        'anticipado': ({'fuente': 'Civiq', 'fecha': (r.get('voto_temprano') or {}).get('fecha_datos'), 'estado': 'diagnóstico',
                        'metricas': [{'etiqueta': 'Boletas devueltas', 'valor': _num((r.get('voto_temprano') or {}).get('devueltas'), 0), 'formato': 'entero'},
                                     {'etiqueta': 'Margen D−R de devueltas', 'valor': _num(hi.get('margen_actual_pp'), 2), 'formato': 'pp'}]
                        + [{'etiqueta': f'{k_} al mismo día', 'valor': _num(v, 2), 'formato': 'pp'} for k_, v in refs.items()]}
                       if hi.get('disponible') else None),
        'adicional': None,
        'fuentes': _fuentes(r['estados_fuentes']), 'avisos': r.get('avisos', []),
        'carpeta': 'california',
    }


# ------------------------------------------------------------------------------------ Arizona
def arizona() -> dict | None:
    s = RAIZ / 'arizona/produccion/salidas'
    if not (s / 'ultimo/reporte.json').exists():
        return None
    r = json.loads((s / 'ultimo/reporte.json').read_text(encoding='utf-8'))
    g, mk, a = r['gobernador'], r['mercados'], r.get('anticipado') or {}
    enc = pd.read_csv(s / 'ultimo/encuestas_gobernador.csv', encoding='utf-8-sig')
    pesos = s / 'ultimo/encuestas_ventana_pesos.csv'
    if pesos.exists():
        w = pd.read_csv(pesos, encoding='utf-8-sig')[['fin', 'pollster', 'peso']]
        enc = enc.merge(w, on=['fin', 'pollster'], how='left')
    rg = mk.get('rangos') or {}
    return {
        'clave': 'arizona', 'estado': 'Arizona', 'cargo': 'Gobernador', 'modelo': 'General (V11 sin sesgo estatal)',
        'candidatos': {'D': 'Katie Hobbs', 'R': 'Andy Biggs'}, 'corte': r['corte'], 'dias_a_eleccion': r['dias_a_eleccion'],
        'pronostico': {'P_D': _num(g['P_D']), 'pct_D': _num(g['pct_D'], 2), 'pct_D_IC80': [_num(x, 2) for x in g['pct_D_IC80']],
                       'pct_R': _num(g['pct_R'], 2), 'pct_R_IC80': [_num(x, 2) for x in g['pct_R_IC80']],
                       'pct_terceros': _num(g.get('pct_terceros'), 2),
                       'pct_terceros_IC80': [_num(x, 2) for x in g.get('pct_terceros_IC80', [None, None])],
                       'margen': _num(g['margen'], 3), 'margen_IC80': [_num(x, 2) for x in g['IC80']],
                       'margen_IC95': [_num(x, 2) for x in g['IC95']], 'sd': _num(g['sd'], 3),
                       'nu': _num(r['calibracion'].get('nu'), 2), 'P_D_encuestas': _num(g['P_D_encuestas']),
                       'peso_mercados': _num(g['peso_mercados_aplicado'], 2), 'mercado_en_distribucion': True,
                       'extra': [{'etiqueta': 'Recuento automático (|margen| ≤ 0.5)', 'valor': _num(g['P_recuento'])}]},
        'mercados': [{'nombre': 'Kalshi', 'P_D': _num(mk['kalshi'].get('p_D')), 'estado': mk['kalshi'].get('estado')},
                     {'nombre': 'Polymarket', 'P_D': _num(mk['polymarket'].get('p_D')), 'estado': mk['polymarket'].get('estado')}],
        'ultima_encuesta': r.get('ultima_encuesta'),
        'encuestas': _encuestas(enc, 'fin', 'pollster', 'D', 'R', 'en_ventana', 'origen', 'peso' if 'peso' in enc else None),
        'n_encuestas_ventana': g.get('k'),
        'historial': _historial(s / 'historial_pronosticos.csv', 'corte',
                                {'P_D': 'P_D', 'P_D_encuestas': 'P_D_encuestas', 'P_kalshi': 'P_D_kalshi',
                                 'P_polymarket': 'P_D_polymarket', 'pct_D': 'pct_D', 'margen': 'margen'}),
        'escenarios': _escenarios(r.get('escenarios', [])),
        'anticipado': ({'fuente': 'civicAPI', 'fecha': a.get('fecha'), 'estado': a.get('estado'),
                        'metricas': [{'etiqueta': 'Boletas devueltas', 'valor': _num(a.get('devueltas'), 0), 'formato': 'entero'},
                                     {'etiqueta': 'Devueltas por demócratas registrados', 'valor': _num(a.get('pct_dev_D'), 2), 'formato': 'pct'},
                                     {'etiqueta': 'Devueltas por republicanos registrados', 'valor': _num(a.get('pct_dev_R'), 2), 'formato': 'pct'},
                                     {'etiqueta': 'Devueltas por otros e independientes', 'valor': _num(a.get('pct_dev_otros'), 2), 'formato': 'pct'},
                                     {'etiqueta': 'Maricopa, % del total', 'valor': _num(a.get('maricopa_pct_dev'), 2), 'formato': 'pct'}]}
                       if a.get('disponible') else None),
        'adicional': ({'titulo': 'Polymarket por rangos de margen', 'P_D': _num(rg.get('P_D')), 'margen': _num(rg.get('margen_media'), 2),
                       'nota': f"Margen implícito {rg['margen_media']:+.1f} pp (σ {rg['margen_sd']:.1f})"}
                      if rg.get('margen_media') is not None else None),
        'fuentes': _fuentes(r['estados_fuentes']), 'avisos': r.get('avisos', []),
        'carpeta': 'arizona',
    }


# ------------------------------------------------------------------------------------ Florida
def florida() -> dict | None:
    s = RAIZ / 'florida/produccion/salidas'
    if not (s / 'ultimo/reporte.json').exists():
        return None
    r = json.loads((s / 'ultimo/reporte.json').read_text(encoding='utf-8'))
    g, mk, a = r['gobernador'], r['mercados'], r.get('anticipado') or {}
    enc = pd.read_csv(s / 'ultimo/encuestas_gobernador.csv', encoding='utf-8-sig')
    pesos = s / 'ultimo/encuestas_ventana_pesos.csv'
    if pesos.exists():
        w = pd.read_csv(pesos, encoding='utf-8-sig')[['fin', 'pollster', 'peso']]
        enc = enc.merge(w, on=['fin', 'pollster'], how='left')
    rg = mk.get('rangos') or {}
    sesgo = g.get('sesgo_estatal_aplicado')
    return {
        'clave': 'florida', 'estado': 'Florida', 'cargo': 'Gobernador', 'modelo': 'General (V11 con sesgo estatal)',
        'candidatos': {'D': 'David Jolly', 'R': 'Byron Donalds'}, 'corte': r['corte'], 'dias_a_eleccion': r['dias_a_eleccion'],
        'pronostico': {'P_D': _num(g['P_D']), 'pct_D': _num(g['pct_D'], 2), 'pct_D_IC80': [_num(x, 2) for x in g['pct_D_IC80']],
                       'pct_R': _num(g['pct_R'], 2), 'pct_R_IC80': [_num(x, 2) for x in g['pct_R_IC80']],
                       'pct_terceros': _num(g.get('pct_terceros'), 2),
                       'pct_terceros_IC80': [_num(x, 2) for x in g.get('pct_terceros_IC80', [None, None])],
                       'margen': _num(g['margen'], 3), 'margen_IC80': [_num(x, 2) for x in g['IC80']],
                       'margen_IC95': [_num(x, 2) for x in g['IC95']], 'sd': _num(g['sd'], 3),
                       'nu': _num(r['calibracion'].get('nu'), 2), 'P_D_encuestas': _num(g['P_D_encuestas']),
                       'peso_mercados': _num(g['peso_mercados_aplicado'], 2), 'mercado_en_distribucion': True,
                       'extra': [{'etiqueta': 'Recuento por máquina (|margen| ≤ 0.5)', 'valor': _num(g['P_recuento'])}]},
        'mercados': [{'nombre': 'Kalshi', 'P_D': _num(mk['kalshi'].get('p_D')), 'estado': mk['kalshi'].get('estado')},
                     {'nombre': 'Polymarket', 'P_D': _num(mk['polymarket'].get('p_D')), 'estado': mk['polymarket'].get('estado')}],
        'ultima_encuesta': r.get('ultima_encuesta'),
        'encuestas': _encuestas(enc, 'fin', 'pollster', 'D', 'R', 'en_ventana', 'origen', 'peso' if 'peso' in enc else None),
        'n_encuestas_ventana': g.get('k'),
        'historial': _historial(s / 'historial_pronosticos.csv', 'corte',
                                {'P_D': 'P_D', 'P_D_encuestas': 'P_D_encuestas', 'P_kalshi': 'P_D_kalshi',
                                 'P_polymarket': 'P_D_polymarket', 'pct_D': 'pct_D', 'margen': 'margen'}),
        'escenarios': _escenarios(r.get('escenarios', [])),
        'anticipado': ({'fuente': 'civicAPI', 'fecha': a.get('fecha'), 'estado': a.get('estado'),
                        'metricas': [{'etiqueta': 'Votos ya emitidos (correo + en persona)', 'valor': _num(a.get('emitidos'), 0), 'formato': 'entero'},
                                     {'etiqueta': 'Emitidos por demócratas registrados', 'valor': _num(a.get('pct_D'), 2), 'formato': 'pct'},
                                     {'etiqueta': 'Emitidos por republicanos registrados', 'valor': _num(a.get('pct_R'), 2), 'formato': 'pct'},
                                     {'etiqueta': 'Emitidos por sin partido (NPA)', 'valor': _num(a.get('pct_NPA'), 2), 'formato': 'pct'},
                                     {'etiqueta': 'Margen D−R por correo', 'valor': _num(a.get('margen_DR_correo_pp'), 2), 'formato': 'pp'},
                                     {'etiqueta': 'Margen D−R en persona', 'valor': _num(a.get('margen_DR_persona_pp'), 2), 'formato': 'pp'}]}
                       if a.get('disponible') else None),
        'rangos_poly': ({'P_D': _num(rg.get('P_D')), 'margen': _num(rg.get('margen_media'), 2)}
                        if rg.get('margen_media') is not None else None),
        'adicional': ({'titulo': 'Sesgo estatal de Florida', 'P_D': None, 'margen': _num(-sesgo, 2),
                       'etiqueta_margen': 'corrección al margen D−R',
                       'nota': (f"Las encuestas de FL han sobreestimado al demócrata: el modelo corrige {-sesgo:+.1f} pp "
                                f"(promedio de encuestas {g['margen_encuestas']:+.1f}). "
                                + (f"Polymarket por rangos: margen implícito {rg['margen_media']:+.1f} pp."
                                   if rg.get('margen_media') is not None else ''))}
                      if sesgo else None),
        'fuentes': _fuentes(r['estados_fuentes']), 'avisos': r.get('avisos', []),
        'carpeta': 'florida',
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    indice = []
    for f in (georgia, california, arizona, florida):
        try:
            d = f()
        except Exception as exc:                       # un estado roto no tumba a los demás
            print(f'{f.__name__}: error {type(exc).__name__}: {exc}')
            continue
        if d is None:
            continue
        (OUT / f"{d['clave']}.json").write_text(json.dumps(_limpio(d), ensure_ascii=False, allow_nan=False, indent=1),
                                               encoding='utf-8')
        p = d['pronostico']
        indice.append({'clave': d['clave'], 'estado': d['estado'], 'cargo': d['cargo'], 'candidatos': d['candidatos'],
                       'corte': d['corte'], 'P_D': p['P_D'], 'pct_D': p['pct_D'], 'pct_R': p['pct_R'], 'margen': p['margen']})
        print(f"{d['estado']}: corte {d['corte']} · P(D) {p['P_D']:.3f}")
    meta = {'generado': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'estados_totales': 14,
            'estados': indice}
    (OUT / 'indice.json').write_text(json.dumps(_limpio(meta), ensure_ascii=False, allow_nan=False, indent=1), encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
