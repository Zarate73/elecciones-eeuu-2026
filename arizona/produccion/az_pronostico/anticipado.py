"""Voto anticipado de Arizona en vivo (civicAPI: boletas solicitadas y devueltas por partido y condado).

Fuente: civicapi.org (datos de las autoridades electorales de AZ; gratis, sin clave, con atribución).
Solo diagnóstico: no entra al pronóstico (no hay histórico comparable al mismo día para validarlo).
Cada corrida agrega una fila a salidas/civicapi_historial_az.csv: serie propia para comparar en 2028.
"""
from __future__ import annotations

import json
import logging

import pandas as pd

from .red import get_json

log = logging.getLogger(__name__)
PARTIDOS = ('Democratic', 'Republican', 'Otros')


def _tabla(js: dict, categoria: str) -> pd.DataFrame:
    filas = [{'condado': c, 'partido': p, 'categoria': categoria, 'votos': int(v.get('votes', 0) or 0)}
             for c, partidos in (js.get('regions') or {}).items() for p, v in partidos.items()]
    return pd.DataFrame(filas, columns=['condado', 'partido', 'categoria', 'votos'])


def resumir(js: dict) -> dict:
    t = pd.concat([_tabla(js[c], c) for c in ('returned', 'requested')])
    if t.empty:
        raise ValueError('civicAPI sin regiones')
    t['partido'] = t.partido.where(t.partido.isin(['Democratic', 'Republican']), 'Otros')
    cond = t.pivot_table(index='condado', columns=['categoria', 'partido'], values='votos', aggfunc='sum', fill_value=0)
    cond.columns = [f'{c}_{p}' for c, p in cond.columns]
    tot = cond.sum()
    dev = {p: int(tot.get(f'returned_{p}', 0)) for p in PARTIDOS}
    sol = {p: int(tot.get(f'requested_{p}', 0)) for p in PARTIDOS}
    n_dev, n_sol = sum(dev.values()), sum(sol.values())
    if n_dev == 0 or dev['Democratic'] + dev['Republican'] == 0:
        raise ValueError('civicAPI sin desglose por partido')
    cond['devueltas'] = cond.filter(like='returned_').sum(axis=1)
    cond['margen_dev_DR_pp'] = 100 * (cond.get('returned_Democratic', 0) - cond.get('returned_Republican', 0)) \
        / cond.devueltas.clip(lower=1)
    cond = cond.sort_values('devueltas', ascending=False).reset_index()
    mar = cond[cond.condado == 'Maricopa']
    return {'fecha': js['returned'].get('snapshot_date'), 'devueltas': n_dev, 'solicitadas': n_sol,
            'pct_dev_D': 100 * dev['Democratic'] / n_dev, 'pct_dev_R': 100 * dev['Republican'] / n_dev,
            'pct_dev_otros': 100 * dev['Otros'] / n_dev,
            'margen_dev_DR_pp': 100 * (dev['Democratic'] - dev['Republican']) / n_dev,
            'tasa_dev_D': 100 * dev['Democratic'] / max(sol['Democratic'], 1),
            'tasa_dev_R': 100 * dev['Republican'] / max(sol['Republican'], 1),
            'tasa_dev_otros': 100 * dev['Otros'] / max(sol['Otros'], 1),
            'maricopa_pct_dev': float(100 * mar.devueltas.sum() / n_dev) if len(mar) else None,
            'maricopa_margen_dev_pp': float(mar.margen_dev_DR_pp.iloc[0]) if len(mar) else None,
            'condados': cond}


def obtener_anticipado(cfg) -> dict:
    f = cfg.fuentes
    d = cfg.dir_cache / 'civicapi'
    d.mkdir(parents=True, exist_ok=True)
    js, estado = {}, 'en_vivo'
    try:
        for cat in ('returned', 'requested'):
            js[cat] = get_json(f'{f.civicapi}/{f.civicapi_estado}/{cat}', offline=cfg.offline, timeout=f.timeout_http_s)
        res = resumir(js)
        for cat in js:
            (d / f"{f.civicapi_estado}_{cat}_{js[cat].get('snapshot_date')}.json").write_text(json.dumps(js[cat]), encoding='utf-8')
    except Exception as exc:                           # nunca se presenta un dato guardado como si fuera en vivo
        err = f'{type(exc).__name__}: {str(exc)[:120]}'
        js = {}
        for cat in ('returned', 'requested'):
            arch = sorted(x for x in d.glob(f'{f.civicapi_estado}_{cat}_*.json') if x.stem.split('_')[-1] <= str(cfg.corte))
            if arch:
                js[cat] = json.loads(arch[-1].read_text(encoding='utf-8'))
        if len(js) < 2:
            log.warning('civicAPI no disponible: %s', err)
            return {'disponible': False, 'estado': f'no_disponible ({err})'}
        res, estado = resumir(js), f'cache ({err})'
    res.update({'disponible': True, 'estado': estado, 'uso': 'diagnóstico; no entra al pronóstico',
                'fuente': 'civicAPI (civicapi.org), autoridades electorales de AZ'})
    hist = cfg.dir_salidas / 'civicapi_historial_az.csv'
    h = pd.read_csv(hist) if hist.exists() else pd.DataFrame()
    fila = pd.DataFrame([{k: v for k, v in res.items() if not isinstance(v, (pd.DataFrame, dict))
                          and k not in ('disponible', 'estado', 'uso', 'fuente')}])
    if len(h):
        h = h[h.fecha.astype(str) != str(res['fecha'])]
    pd.concat([h, fila], ignore_index=True).sort_values('fecha').to_csv(hist, index=False)
    return res
