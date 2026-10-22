"""Voto ya emitido en Florida, en vivo (civicAPI con datos de la División de Elecciones de FL).

Categorías: returned (boletas por correo devueltas), inperson (voto anticipado en persona) y requested (boletas por
correo solicitadas), por partido registrado (D, R, NPA, otros) y condado. Emitidos = returned + inperson.
Fuente gratuita, sin clave, con atribución. SOLO DIAGNÓSTICO: no entra al pronóstico. Mide registro de partido, no
intención de voto, y la brecha entre el voto anticipado y el resultado cambia de un ciclo a otro (FL 2022: R+3.5 al
31-oct y DeSantis +19; 2024: D adelante en correo al 21-oct y Trump +13); no hay serie del mismo día para calibrarla.
Cada corrida agrega una fila a salidas/civicapi_historial_fl.csv: serie propia para validar en 2028.
"""
from __future__ import annotations

import json
import logging

import pandas as pd

from .red import get_json

log = logging.getLogger(__name__)
CATS = ('returned', 'inperson', 'requested')
PARTIDOS = ('D', 'R', 'NPA', 'Otros')
MAPA = {'Democratic': 'D', 'Republican': 'R', 'No Party Affiliation': 'NPA'}


def _tabla(js: dict, categoria: str) -> pd.DataFrame:
    filas = [{'condado': c, 'partido': p, 'categoria': categoria, 'votos': int(v.get('votes', 0) or 0)}
             for c, partidos in (js.get('regions') or {}).items() for p, v in partidos.items()]
    return pd.DataFrame(filas, columns=['condado', 'partido', 'categoria', 'votos'])


def resumir(js: dict) -> dict:
    t = pd.concat([_tabla(js[c], c) for c in CATS])
    if t.empty:
        raise ValueError('civicAPI sin regiones')
    t['partido'] = t.partido.map(MAPA).fillna('Otros')
    cond = t.pivot_table(index='condado', columns=['categoria', 'partido'], values='votos', aggfunc='sum', fill_value=0)
    cond.columns = [f'{c}_{p}' for c, p in cond.columns]
    tot = cond.sum()
    corr = {p: int(tot.get(f'returned_{p}', 0)) for p in PARTIDOS}
    pers = {p: int(tot.get(f'inperson_{p}', 0)) for p in PARTIDOS}
    sol = {p: int(tot.get(f'requested_{p}', 0)) for p in PARTIDOS}
    emit = {p: corr[p] + pers[p] for p in PARTIDOS}
    n = sum(emit.values())
    if n == 0 or emit['D'] + emit['R'] == 0:
        raise ValueError('civicAPI sin desglose por partido')
    for x in PARTIDOS:
        cond[f'emitidos_{x}'] = cond.get(f'returned_{x}', 0) + cond.get(f'inperson_{x}', 0)
    cond['emitidos'] = cond.filter(like='emitidos_').sum(axis=1)
    cond['margen_DR_pp'] = 100 * (cond.emitidos_D - cond.emitidos_R) / cond.emitidos.clip(lower=1)
    cond = cond.sort_values('emitidos', ascending=False).reset_index()
    md = cond[cond.condado == 'Miami-Dade']
    n_c, n_p = sum(corr.values()), sum(pers.values())
    return {'fecha': js['returned'].get('snapshot_date'), 'emitidos': n, 'por_correo': n_c, 'en_persona': n_p,
            'correo_solicitado': sum(sol.values()),
            **{f'pct_{x}': 100 * emit[x] / n for x in PARTIDOS},
            'margen_DR_pp': 100 * (emit['D'] - emit['R']) / n,
            'margen_DR_correo_pp': 100 * (corr['D'] - corr['R']) / max(n_c, 1),
            'margen_DR_persona_pp': 100 * (pers['D'] - pers['R']) / max(n_p, 1),
            'miami_dade_pct': float(100 * md.emitidos.sum() / n) if len(md) else None,
            'miami_dade_margen_pp': float(md.margen_DR_pp.iloc[0]) if len(md) else None,
            'condados': cond}


def obtener_anticipado(cfg) -> dict:
    f = cfg.fuentes
    d = cfg.dir_cache / 'civicapi'
    d.mkdir(parents=True, exist_ok=True)
    js, estado = {}, 'en_vivo'
    try:
        for cat in CATS:
            js[cat] = get_json(f'{f.civicapi}/{f.civicapi_estado}/{cat}', offline=cfg.offline, timeout=f.timeout_http_s)
        res = resumir(js)
        for cat in js:
            (d / f"{f.civicapi_estado}_{cat}_{js[cat].get('snapshot_date')}.json").write_text(json.dumps(js[cat]), encoding='utf-8')
    except Exception as exc:                           # nunca se presenta un dato guardado como si fuera en vivo
        err = f'{type(exc).__name__}: {str(exc)[:120]}'
        js = {}
        for cat in CATS:
            arch = sorted(x for x in d.glob(f'{f.civicapi_estado}_{cat}_*.json') if x.stem.split('_')[-1] <= str(cfg.corte))
            if arch:
                js[cat] = json.loads(arch[-1].read_text(encoding='utf-8'))
        if len(js) < len(CATS):
            log.warning('civicAPI no disponible: %s', err)
            return {'disponible': False, 'estado': f'no_disponible ({err})'}
        res, estado = resumir(js), f'cache ({err})'
    res.update({'disponible': True, 'estado': estado, 'uso': 'diagnóstico; no entra al pronóstico',
                'fuente': 'civicAPI (civicapi.org), División de Elecciones de Florida'})
    hist = cfg.dir_salidas / 'civicapi_historial_fl.csv'
    h = pd.read_csv(hist) if hist.exists() else pd.DataFrame()
    fila = pd.DataFrame([{k: v for k, v in res.items() if not isinstance(v, (pd.DataFrame, dict))
                          and k not in ('disponible', 'estado', 'uso', 'fuente')}])
    if len(h):
        h = h[h.fecha.astype(str) != str(res['fecha'])]
    pd.concat([h, fila], ignore_index=True).sort_values('fecha').to_csv(hist, index=False)
    return res
