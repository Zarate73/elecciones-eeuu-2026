"""Elecciones generales de alcaldía de D.C. 1974–2022 (Wikipedia, en vivo) + criterio fuerte/titular (data/).

Cada corrida vuelve a leer las 13 páginas. Si una falla, se usa la fila de la última caché buena y, si tampoco hay
caché, la del respaldo versionado (data/historico_alcaldias_respaldo.csv, extraído de Wikipedia el 28-oct-2026 y
contrastado con los resultados certificados de la DCBOE 2014/2018/2022).
"""
from __future__ import annotations

import logging
import time

import numpy as np
import pandas as pd

from .wiki import apellido, es_escrito, pagina_html, tabla_general, tabla_primaria_d

log = logging.getLogger(__name__)
COLUMNAS = ['anio', 'nominado', 'pct_d', 'opositor', 'partido_op', 'pct_op', 'pct_verde', 'pct_escrito', 'votos',
            'primaria_pct']


def extraer_anio(html: str, anio: int) -> dict:
    g = tabla_general(html)
    if g is None:
        raise ValueError(f'{anio}: sin tabla de la general')
    tot = g.votos.sum()
    d = g[g.partido.str.contains('^Democratic', regex=True)].sort_values('votos', ascending=False)
    if d.empty:
        raise ValueError(f'{anio}: sin candidato demócrata en la general')
    nom = d.iloc[0]
    resto = g.drop(nom.name).sort_values('votos', ascending=False)
    op = resto.iloc[0]
    p = tabla_primaria_d(html, apellido(nom.cand))
    pp = None
    if p is not None:
        fila = p[p.cand.str.contains(apellido(nom.cand), regex=False)]
        pp = 100 * fila.votos.max() / p.votos.sum()
    return {'anio': anio, 'nominado': nom.cand, 'pct_d': 100 * nom.votos / tot,
            'opositor': op.cand if op.cand else 'Write-in', 'partido_op': op.partido, 'pct_op': 100 * op.votos / tot,
            'pct_verde': 100 * g[g.partido.str.contains('Statehood')].votos.sum() / tot,
            'pct_escrito': 100 * g[es_escrito(g)].votos.sum() / tot, 'votos': tot, 'primaria_pct': pp}


def _validar(fila: dict) -> None:
    if not 40 <= fila['pct_d'] <= 99 or fila['votos'] < 50_000:
        raise ValueError(f"{fila['anio']}: valores fuera de rango (D {fila['pct_d']:.1f} %, {fila['votos']:.0f} votos)")


def obtener_historico(cfg) -> dict:
    f = cfg.fuentes
    cache = cfg.dir_cache / 'historico_alcaldias.csv'
    previo = pd.read_csv(cache) if cache.exists() else pd.DataFrame(columns=COLUMNAS)
    respaldo = pd.read_csv(cfg.ruta('historico_respaldo'))
    filas, origen = [], {}
    for i, a in enumerate(f.anios_historicos):
        try:
            if i and not cfg.offline:
                time.sleep(float(f.get('pausa_wikipedia_s', 1.0)))
            fila = extraer_anio(pagina_html(cfg, f.wikipedia_historico.format(anio=a)), a)
            _validar(fila)
            origen[a] = 'en_vivo'
        except Exception as exc:                                   # noqa: BLE001 - cada año cae a su caché
            log.warning('Wikipedia %s: %s', a, exc)
            for nom, tabla in (('cache', previo), ('respaldo', respaldo)):
                x = tabla[tabla.anio == a]
                if len(x):
                    fila = x.iloc[0][COLUMNAS].to_dict()
                    origen[a] = nom
                    break
            else:
                raise RuntimeError(f'Elección {a}: sin Wikipedia, caché ni respaldo') from exc
        filas.append(fila)
    h = pd.DataFrame(filas)[COLUMNAS]
    ctx = pd.read_csv(cfg.ruta('contexto_historico'))
    h = h.merge(ctx, on='anio', how='left', validate='1:1')
    if h.fuerte.isna().any():
        raise ValueError(f"Falta el criterio fuerte/titular para {h.anio[h.fuerte.isna()].tolist()} en contexto_alcaldias.csv")
    h['primaria_pct'] = h.primaria_pct.fillna(h.primaria_pct_respaldo)
    h['origen'] = h.anio.map(origen)
    vivos = int((h.origen == 'en_vivo').sum())
    if vivos:
        h[COLUMNAS].to_csv(cache, index=False)
    n = len(h)
    if vivos == n:
        estado = f'en_vivo ({n}/{n} páginas)'
    elif vivos:
        estado = f'parcial ({vivos}/{n} en vivo; ' + ', '.join(f'{a} {o}' for a, o in origen.items() if o != 'en_vivo') + ')'
    else:
        estado = 'cache' if (h.origen == 'cache').all() else 'respaldo'
    h['y'] = np.log(h.pct_d / (100 - h.pct_d))
    return {'tabla': h, 'estado': estado}
