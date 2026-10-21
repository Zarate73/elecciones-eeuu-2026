"""Voto anticipado (Civiq): API pública primero, navegador de respaldo, caché al final.
También guarda la historia diaria de 7 elecciones y el desglose por condado, y calcula
los diagnósticos de participación (M2 corregido por edad, comparación histórica y
composición -> resultado)."""
from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import date, datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from .red import get_json
from .tipos import FuenteNoDisponible, VotoTemprano

log = logging.getLogger(__name__)
EDADES = ('18-29', '30-45', '46-64', '65+')
PARTIDOS_API = {'D': 'dem', 'R': 'rep', 'O': 'otro'}


# ======================================================================================
# API
# ======================================================================================
def _api(cfg, endpoint: str):
    d = quote(cfg.fuentes.civiq_distrito)
    return get_json(f"{cfg.fuentes.civiq_api}/{endpoint.format(d=d)}", offline=cfg.offline,
                    timeout=cfg.fuentes.timeout_http_s)


def voto_temprano_desde_api(cfg) -> VotoTemprano:
    cruz = _api(cfg, 'crosstabs/{d}?row=party&column=age')
    br = _api(cfg, 'ballot-returns/{d}')
    cols = sorted(cruz['columnValues'], key=lambda x: int(x))
    if len(cols) != 4:
        raise FuenteNoDisponible(f'Civiq API: se esperaban 4 grupos de edad, llegaron {cols}')
    pe = {}
    for fila in cruz['matrix']:
        k = PARTIDOS_API.get(fila['party'])
        if k:
            pe[k] = [[int(fila[c]['registered']), int(fila[c]['returned'])] for c in cols]
    if set(pe) != {'dem', 'rep', 'otro'}:
        raise FuenteNoDisponible(f'Civiq API: partidos incompletos {sorted(pe)}')
    reg = {k: sum(r for r, _ in v) for k, v in pe.items()}
    dev = {k: sum(x for _, x in v) for k, v in pe.items()}
    filas = br.get('ballotReturns', [])
    fechas = [f['returnDate'] for f in filas if f.get('returnDate')]
    if not fechas:
        raise FuenteNoDisponible('Civiq API: sin fechas de devolución')
    fecha = max(fechas)
    total_br = sum(int(f['voters']) for f in filas if f.get('returnDate'))   # filas sin fecha = no devueltas
    total = sum(dev.values())
    if total_br and abs(total_br - total) / total > 0.005:
        log.warning('Civiq API: crosstab (%s) y ballot-returns (%s) difieren >0.5%%', total, total_br)
    if not (15_000_000 <= sum(reg.values()) <= 30_000_000) or not 0 < total <= sum(reg.values()):
        raise FuenteNoDisponible('Civiq API: totales fuera de rango')
    if not (cfg.inicio_voto <= date.fromisoformat(fecha) <= cfg.dia_eleccion):
        raise FuenteNoDisponible(f'Civiq API: fecha {fecha} fuera del periodo de votación')
    edad_reg = {e: sum(pe[k][i][0] for k in pe) for i, e in enumerate(EDADES)}
    edad_dev = {e: sum(pe[k][i][1] for k in pe) for i, e in enumerate(EDADES)}
    return VotoTemprano(
        fuente='Civiq / Optiq Data (API)', url=f"{cfg.fuentes.civiq_api}/crosstabs",
        fecha_datos=fecha, fecha_consulta=datetime.now(ZoneInfo(cfg.eleccion.zona_horaria)).isoformat(timespec='seconds'),
        registrados=sum(reg.values()), devueltas=total,
        registro_dem=reg['dem'], registro_rep=reg['rep'], registro_otro=reg['otro'],
        devueltas_dem=dev['dem'], devueltas_rep=dev['rep'], devueltas_otro=dev['otro'],
        registro_edad=edad_reg, devueltas_edad=edad_dev, partido_edad=pe, origen='api')


def historia_desde_api(js: dict) -> pd.DataFrame:
    filas = []
    for e in js.get('elections', []):
        reg = e.get('registeredVoters') or np.nan
        puntos = [(s['daysBeforeElection'], s['returns'], s['partyReturns']) for s in e.get('snapshots', [])]
        if e.get('finalStatus') == 'available' and e.get('final'):
            puntos.append((-1, e['final']['returns'], e['final']['partyReturns']))      # -1 = final
        for dias, tot, p in puntos:
            d, r, o = p.get('Dem', 0), p.get('Rep', 0), p.get('NPP/Oth', 0)
            if not tot or d + r + o != tot:
                continue
            filas.append({'dias_antes_eleccion': int(dias), 'eleccion': e['election'], 'total': int(tot),
                          'dem_pct': 100 * d / tot, 'rep_pct': 100 * r / tot, 'otro_pct': 100 * o / tot,
                          'margen_dr_pp': 100 * (d - r) / tot, 'turnout_pct': 100 * tot / reg})
    return pd.DataFrame(filas)


def _acumular(df: pd.DataFrame, ruta, llave) -> pd.DataFrame:
    if df.empty:
        return pd.read_csv(ruta) if ruta.exists() else df
    if ruta.exists():
        df = pd.concat([pd.read_csv(ruta), df], ignore_index=True)
    df = df.drop_duplicates(llave, keep='last')
    df.to_csv(ruta, index=False, encoding='utf-8-sig')
    return df


def actualizar_historia_y_condados(cfg) -> dict:
    """Historia diaria (7 elecciones) y condados. Errores no fatales: se usa la caché."""
    estado = {}
    ruta_h = cfg.dir_cache / 'civiq_historia_diaria.csv'
    try:
        h = historia_desde_api(_api(cfg, 'historical-elections/{d}'))
        _acumular(h, ruta_h, ['dias_antes_eleccion', 'eleccion'])
        estado['historia'] = f'api_en_vivo ({len(h)} filas)'
    except Exception as exc:
        estado['historia'] = f'cache ({type(exc).__name__}: {exc})'
    ruta_c = cfg.dir_cache / 'civiq_condados.csv'
    try:
        c = pd.DataFrame(_api(cfg, 'geography-breakdown/{d}?level=county_name'))
        c.to_csv(ruta_c, index=False, encoding='utf-8-sig')
        estado['condados'] = f'api_en_vivo ({len(c)} condados)'
    except Exception as exc:
        estado['condados'] = f'cache ({type(exc).__name__}: {exc})'
    return estado


def cargar_historia(cfg) -> pd.DataFrame:
    p = cfg.dir_cache / 'civiq_historia_diaria.csv'
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


# ======================================================================================
# Orquestación: API -> navegador -> caché
# ======================================================================================
def _ruta_ultimo(cfg):
    return cfg.dir_cache / 'voto_temprano_ultimo.json'


def _guardar_snapshot(cfg, dato: VotoTemprano) -> None:
    p = _ruta_ultimo(cfg)
    if p.exists():
        try:
            previo = VotoTemprano(**json.loads(p.read_text(encoding='utf-8')))
            if date.fromisoformat(dato.fecha_datos) < date.fromisoformat(previo.fecha_datos):
                raise FuenteNoDisponible('Civiq regresó a una fecha anterior al último snapshot válido')
        except (TypeError, ValueError, KeyError):
            pass
    tmp = p.with_suffix('.tmp')
    tmp.write_text(json.dumps(asdict(dato), ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(p)
    fila = {k: getattr(dato, k) for k in ('fecha_datos', 'fecha_consulta', 'registrados', 'devueltas',
                                          'registro_dem', 'registro_rep', 'registro_otro',
                                          'devueltas_dem', 'devueltas_rep', 'devueltas_otro', 'origen')}
    _acumular(pd.DataFrame([fila]), cfg.dir_cache / 'voto_temprano_historico.csv', ['fecha_datos'])


def obtener_voto_temprano(cfg, corte: date) -> tuple[VotoTemprano | None, str]:
    errores = []
    dato = None
    try:
        dato = voto_temprano_desde_api(cfg)
    except Exception as exc:
        errores.append(f'API: {type(exc).__name__}: {exc}')
        if cfg.fuentes.civiq_usar_navegador_respaldo and not cfg.offline:
            try:
                from . import civiq_navegador
                civiq_navegador.configurar(cfg)
                dato = civiq_navegador.capturar_y_extraer()
            except Exception as exc2:
                errores.append(f'navegador: {type(exc2).__name__}: {str(exc2)[:300]}')
    if dato is not None:
        fd = date.fromisoformat(dato.fecha_datos)
        if fd > corte:
            errores.append('datos posteriores al corte (backtesting): no se usan')
            dato = None
        else:
            rezago = (min(corte, cfg.dia_eleccion) - fd).days
            if rezago > cfg.fuentes.civiq_max_dias_rezago:
                dato.estado = 'fuente_rezagada'
                return dato, f'ADVERTENCIA: Civiq ({dato.origen}) con {rezago} días de rezago'
            dato.estado = 'actualizado'
            try:
                _guardar_snapshot(cfg, dato)
            except FuenteNoDisponible as exc:
                return None, str(exc)
            return dato, f'Datos de Civiq vía {dato.origen}, validados ({dato.fecha_datos})'
    p = _ruta_ultimo(cfg)
    if p.exists():
        try:
            g = VotoTemprano(**json.loads(p.read_text(encoding='utf-8')))
            if date.fromisoformat(g.fecha_datos) <= corte:
                g.estado, g.origen = 'cache_desactualizado', 'cache'
                dias = (corte - date.fromisoformat(g.fecha_datos)).days
                return g, f'ATENCIÓN: caché de hace {dias} días. Causa: {"; ".join(errores)}'
        except Exception as exc:
            errores.append(f'caché corrupta: {exc}')
    return None, f'Sin datos de voto temprano. Causa: {"; ".join(errores)}'


def resumen_participacion(d: VotoTemprano) -> dict:
    n, t = d.registrados, d.devueltas
    partidos = {}
    for k, nombre in (('dem', 'Democratas'), ('rep', 'Republicanos'), ('otro', 'Otros/NPP')):
        reg, ret = getattr(d, f'registro_{k}'), getattr(d, f'devueltas_{k}')
        partidos[nombre] = {'registrados': reg, 'devueltas': ret, 'cuota_registro_pct': 100 * reg / n,
                            'cuota_devoluciones_pct': 100 * ret / t if t else 0.,
                            'tasa_devolucion_pct': 100 * ret / reg if reg else 0.}
    return {'fecha_datos': d.fecha_datos, 'estado': d.estado, 'origen': d.origen, 'registrados': n,
            'devueltas': t, 'tasa_devolucion_total_pct': 100 * t / n, 'partidos': partidos,
            'margen_dr_devueltas_pp': 100 * (d.devueltas_dem - d.devueltas_rep) / t if t else 0.,
            'margen_dr_registro_pp': 100 * (d.registro_dem - d.registro_rep) / n,
            'edades': {x: {'registrados': d.registro_edad.get(x), 'devueltas': c,
                           'porcentaje_de_devoluciones': 100 * c / t if t else 0.}
                       for x, c in d.devueltas_edad.items()}}


# ======================================================================================
# Diagnósticos de participación (M2). Ninguno entra a la media salvo con modelo.w_m2 > 0.
# ======================================================================================
def m2_por_edad(dato: VotoTemprano | None) -> dict:
    """Margen D-R de devoluciones frente al esperado si cada grupo de edad devolviera con la
    composición partidista de SU registro."""
    if dato is None or dato.devueltas <= 0:
        return {'disponible': False, 'nota': 'sin datos de voto temprano'}
    actual = 100 * (dato.devueltas_dem - dato.devueltas_rep) / dato.devueltas
    out = {'disponible': False, 'margen_dr_devueltas_pp': actual,
           'margen_dr_registro_pp': 100 * (dato.registro_dem - dato.registro_rep) / dato.registrados}
    pe = dato.partido_edad or {}
    if set(pe) == {'dem', 'rep', 'otro'} and all(len(v) == 4 for v in pe.values()):
        esperado = 0.0
        for i in range(4):
            reg_a = sum(pe[k][i][0] for k in pe)
            dev_a = sum(pe[k][i][1] for k in pe)
            if reg_a:
                esperado += (dev_a / dato.devueltas) * (pe['dem'][i][0] - pe['rep'][i][0]) / reg_a
        out.update(disponible=True, margen_dr_esperado_por_edad_pp=100 * esperado,
                   delta_m2_pp=actual - 100 * esperado)
    else:
        out['nota'] = 'sin tabla partido×edad'
    return out


def m2_composicion(cfg, margen_dr_final: float) -> dict:
    """Margen del resultado ~ a + b·(D-R de devoluciones FINALES), ajustado con generales y
    especiales 2021–2025 (data/civiq_finales_resultados.csv), con error LOO."""
    p = cfg.dir_datos / 'civiq_finales_resultados.csv'
    if not p.exists():
        return {'disponible': False}
    d = pd.read_csv(p)
    d['x'] = d.dem_pct_devueltas - d.rep_pct_devueltas
    tr = d[d.tipo != 'primaria'].reset_index(drop=True)
    b, a = np.polyfit(tr.x, tr.margen_resultado_2p_pp, 1)
    loo = []
    for i in range(len(tr)):
        o = tr.drop(i)
        bi, ai = np.polyfit(o.x, o.margen_resultado_2p_pp, 1)
        loo.append(tr.margen_resultado_2p_pp[i] - (ai + bi * tr.x[i]))
    prim = d[d.tipo == 'primaria']
    return {'disponible': True, 'pendiente': float(b), 'intercepto': float(a), 'n': int(len(tr)),
            'rmse_loo_pp': float(np.sqrt(np.mean(np.square(loo)))),
            'error_primaria_2026_pp': float(prim.margen_resultado_2p_pp.iloc[0] - (a + b * prim.x.iloc[0])) if len(prim) else None,
            'margen_resultado_implicito_pp': float(a + b * margen_dr_final)}


def m2_historico(cfg, margen_actual: float, dte: int, historia: pd.DataFrame, errores_encuestas: dict) -> dict:
    """Δ frente a elecciones comparables al mismo día, composición final proyectada y
    diagnóstico retrospectivo (¿el Δ temprano anticipó el error de las encuestas?)."""
    if historia.empty:
        return {'disponible': False, 'nota': 'sin historia de Civiq'}
    piv = historia.pivot_table(index='dias_antes_eleccion', columns='eleccion', values='margen_dr_pp')
    validos = piv.index[piv.index >= 0]
    if dte not in piv.index:
        dte = int(validos[np.argmin(np.abs(validos - dte))])
    refs = [e for e in cfg.modelo.m2_referencias if e in piv.columns and pd.notna(piv.loc[dte, e])]
    out = {'disponible': bool(refs), 'dias_comparados': int(dte), 'referencias': refs,
           'margen_actual_pp': margen_actual,
           'margen_referencias_mismo_dia_pp': {e: float(piv.loc[dte, e]) for e in refs}}
    if refs:
        out['delta_vs_referencias_pp'] = margen_actual - float(np.mean([piv.loc[dte, e] for e in refs]))
        if -1 in piv.index:
            corr = {e: float(piv.loc[-1, e] - piv.loc[dte, e]) for e in refs}
            out['corrimiento_dia_a_final_pp'] = corr
            out['composicion_final_proyectada_pp'] = margen_actual + float(np.mean(list(corr.values())))
            comp = m2_composicion(cfg, out['composicion_final_proyectada_pp'])
            if comp.get('disponible'):
                out['composicion_a_resultado'] = comp
    mapa = {'2021 Special': 'REV2021', '2022 General': 'GOB2022', '2024 General': 'PRES2024', '2025 Special': 'PROP2025'}
    filas = []
    for e, clave in mapa.items():
        if e in piv.columns and clave in errores_encuestas and pd.notna(piv.loc[dte, e]):
            otras = [piv.loc[dte, o] for o in mapa if o != e and o in piv.columns and pd.notna(piv.loc[dte, o])]
            filas.append({'eleccion': e, 'delta_vs_otras_pp': round(float(piv.loc[dte, e] - np.mean(otras)), 2),
                          'error_encuestas_pp': round(float(errores_encuestas[clave]), 2)})
    if len(filas) >= 3:
        t = pd.DataFrame(filas)
        out['diagnostico_retrospectivo'] = filas
        out['correlacion_delta_error'] = float(np.corrcoef(t.delta_vs_otras_pp, t.error_encuestas_pp)[0, 1])
    return out
