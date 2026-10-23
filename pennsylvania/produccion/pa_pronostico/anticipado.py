"""Voto ya emitido, en vivo (civicAPI con datos del Departamento de Estado / condados).

Categorías: returned (boletas por correo devueltas), requested (solicitadas) e inperson (voto anticipado en persona,
opcional: Pennsylvania NO tiene voto anticipado en persona, solo correo). Por partido registrado (D, R, sin partido,
otros) y condado. SOLO DIAGNÓSTICO: no entra al pronóstico. En PA el correo es muy demócrata por hábito (D+43 por
registro al 23-oct) y los republicanos votan sobre todo el día de la elección: no indica el resultado.
Cada corrida agrega una fila a salidas/civicapi_historial_<estado>.csv.
"""
from __future__ import annotations

import json
import logging

import pandas as pd

from .red import get_json

log = logging.getLogger(__name__)
CATS = ('returned', 'inperson', 'requested')
OPCIONALES = ('inperson',)                             # Pennsylvania no tiene voto anticipado en persona
PARTIDOS = ('D', 'R', 'NPA', 'Otros')
MAPA = {'Democratic': 'D', 'Republican': 'R', 'No Party Affiliation': 'NPA', 'Nonpartisan': 'NPA', 'Non-Partisan': 'NPA'}
CONDADO_PRINCIPAL = ['Clark']                          # lo fija obtener_anticipado desde la configuración


def _tabla(js: dict, categoria: str) -> pd.DataFrame:
    filas = [{'condado': c, 'partido': p, 'categoria': categoria, 'votos': int(v.get('votes', 0) or 0)}
             for c, partidos in (js.get('regions') or {}).items() for p, v in partidos.items()]
    return pd.DataFrame(filas, columns=['condado', 'partido', 'categoria', 'votos'])


def resumir(js: dict) -> dict:
    t = pd.concat([_tabla(js[c], c) for c in CATS if c in js])
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
    md = cond[cond.condado == CONDADO_PRINCIPAL[0]]
    n_c, n_p = sum(corr.values()), sum(pers.values())
    return {'fecha': js['returned'].get('snapshot_date'), 'emitidos': n, 'por_correo': n_c, 'en_persona': n_p,
            'tiene_en_persona': 'inperson' in js,
            'correo_solicitado': sum(sol.values()),
            **{f'pct_{x}': 100 * emit[x] / n for x in PARTIDOS},
            'margen_DR_pp': 100 * (emit['D'] - emit['R']) / n,
            'margen_DR_correo_pp': 100 * (corr['D'] - corr['R']) / max(n_c, 1),
            'margen_DR_persona_pp': 100 * (pers['D'] - pers['R']) / max(n_p, 1),
            'condado_principal': CONDADO_PRINCIPAL[0],
            'condado_principal_pct': float(100 * md.emitidos.sum() / n) if len(md) else None,
            'condado_principal_margen_pp': float(md.margen_DR_pp.iloc[0]) if len(md) else None,
            'condados': cond}


def obtener_anticipado(cfg) -> dict:
    f = cfg.fuentes
    CONDADO_PRINCIPAL[0] = cfg.eleccion.get('condado_principal', CONDADO_PRINCIPAL[0])
    d = cfg.dir_cache / 'civicapi'
    d.mkdir(parents=True, exist_ok=True)
    js, estado = {}, 'en_vivo'
    try:
        for cat in CATS:
            try:
                js[cat] = get_json(f'{f.civicapi}/{f.civicapi_estado}/{cat}', offline=cfg.offline, timeout=f.timeout_http_s)
            except Exception:
                if cat not in OPCIONALES or cfg.offline:
                    raise
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
        if any(c not in js for c in CATS if c not in OPCIONALES):
            log.warning('civicAPI no disponible: %s', err)
            return {'disponible': False, 'estado': f'no_disponible ({err})'}
        res, estado = resumir(js), f'cache ({err})'
    res.update({'disponible': True, 'estado': estado, 'uso': 'diagnóstico; no entra al pronóstico',
                'fuente': f'civicAPI (civicapi.org), datos oficiales de {cfg.eleccion.estado}'})
    hist = cfg.dir_salidas / f'civicapi_historial_{f.civicapi_estado.lower()}.csv'
    h = pd.read_csv(hist) if hist.exists() else pd.DataFrame()
    fila = pd.DataFrame([{k: v for k, v in res.items() if not isinstance(v, (pd.DataFrame, dict))
                          and k not in ('disponible', 'estado', 'uso', 'fuente')}])
    if len(h):
        h = h[h.fecha.astype(str) != str(res['fecha'])]
    pd.concat([h, fila], ignore_index=True).sort_values('fecha').to_csv(hist, index=False)
    return res
