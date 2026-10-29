"""Encuestas de la general (Wikipedia + data/encuestas_complementarias_dc.csv). Al 28-oct-2026 no hay ninguna.

Si aparecen: identidad = firma + periodo de campo (identidad.py, común a los paquetes) para no contar dos veces la
misma encuesta; promedio ponderado por √n y vida media de 14 días, 1/firma; indecisos repartidos en proporción
(la lección de la primaria: el reparto 55/30/15 del modelo de la primaria subestimó a Lewis George por 12 pp).
"""
from __future__ import annotations

import logging
import re

import numpy as np
import pandas as pd

from . import identidad

log = logging.getLogger(__name__)
COLS = ['pollster', 'inicio', 'fin', 'n', 'pop', 'lewis_george', 'hamilton', 'gross', 'indecisos', 'origen']


def clave_firma(nombre) -> str:
    """Clave de 14 letras de la firma (misma regla que encuestas_web.clave_firma de los demás paquetes)."""
    n = re.sub(r'\s+', ' ', re.sub(r'\[[^\]]*\]', '', '' if nombre is None else str(nombre))).strip()
    n = re.sub(r'\([^)]*\)', '', n).split('/')[0]
    return re.sub(r'[^a-z]', '', n.lower())[:14] or 'desconocida'


def complementarias(cfg) -> pd.DataFrame:
    p = cfg.ruta('encuestas_complementarias')
    if not p.exists():
        return pd.DataFrame(columns=COLS)
    d = pd.read_csv(p)
    if d.empty:
        return pd.DataFrame(columns=COLS)
    d['origen'] = 'complementaria'
    for k in ('inicio', 'fin'):
        d[k] = pd.to_datetime(d[k], errors='coerce')
    return d.reindex(columns=COLS)


def combinar(web: pd.DataFrame, comp: pd.DataFrame) -> pd.DataFrame:
    """Une Wikipedia y las complementarias con la identidad común (D = Lewis George, R = Hamilton)."""
    fuentes = []
    for x in (comp, web):                                   # prioridad: verificada primero
        if x is None or not len(x):
            continue
        y = x.copy()
        y['clave'] = y.pollster.map(clave_firma)
        y['D'], y['R'] = y.lewis_george, y.hamilton
        y['otros'] = y.gross
        y['inicio'] = pd.to_datetime(y.inicio).dt.date
        y['fin'] = pd.to_datetime(y.fin).dt.date
        fuentes.append(y)
    cols = ['pollster', 'clave', 'inicio', 'fin', 'n', 'pop', 'D', 'R', 'otros', 'indecisos', 'origen']
    if not fuentes:
        return pd.DataFrame(columns=COLS + ['clave'])
    out = identidad.combinar_df(*[f[cols] for f in fuentes], cols=cols)
    out = out.rename(columns={'D': 'lewis_george', 'R': 'hamilton', 'otros': 'gross'})
    for k in ('inicio', 'fin'):
        out[k] = pd.to_datetime(out[k])
    return out


def promedio(d: pd.DataFrame, cfg) -> dict | None:
    """% de Lewis George entre los que eligen candidato (indecisos proporcionales)."""
    if d is None or d.empty:
        return None
    d = d.copy()
    corte = pd.Timestamp(cfg.corte)
    if cfg.es_reconstruccion:                                # publicadas al corte (cierre + 3 días)
        d = d[d.fin + pd.Timedelta(days=3) <= corte]
    d = d[(d.fin <= corte) & (d.fin >= pd.Timestamp(cfg.fecha_nominacion))]
    if d.empty:
        return None
    dec = d[['lewis_george', 'hamilton']].sum(axis=1) + d.gross.fillna(0)
    d['p'] = 100 * d.lewis_george / dec.where(dec > 0)
    d = d.dropna(subset=['p'])
    if d.empty:
        return None
    n = d.n.fillna(400).clip(100, 3000)
    edad = (corte - d.fin).dt.days.clip(lower=0)
    w = np.sqrt(n) * 0.5 ** (edad / float(cfg.modelo.vida_media_dias))
    w = w / d.groupby('clave').p.transform('size')            # cada firma pesa ~1
    p = float(np.average(d.p, weights=w))
    return {'pct_D': p, 'n_encuestas': int(len(d)), 'k_firmas': int(d.clave.nunique()), 'ultima_fin': str(d.fin.max().date()),
            'tabla': d.assign(peso=w / w.sum())}
