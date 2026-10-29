"""Wikipedia (API MediaWiki): descarga de páginas y lectura de las tablas de resultados.

Las tablas de resultados de Wikipedia («Party | Candidate | Votes | %») cambian de forma entre páginas: unas traen la
fila «Democratic hold», otras «Majority/Turnout», otras solo «Candidate | Votes | Percent». Aquí se normalizan a
(partido, candidato, votos) quitando totales, sobrevotos y subvotos, para que el porcentaje sea sobre votos válidos
(como en los resultados certificados de la DCBOE).
"""
from __future__ import annotations

import logging
import re
from io import StringIO

import pandas as pd

from .red import get_json

log = logging.getLogger(__name__)

EXCLUIR = r'Total|Majority|Turnout|Registered|Over ?[Vv]otes|Under ?[Vv]otes|Overvotes|Undervotes|hold|gain|^Other$|Source:'


def pagina_html(cfg, titulo: str) -> str:
    """HTML de la página (lanza excepción si no hay red o la API responde error)."""
    d = get_json(cfg.fuentes.wikipedia_api, params={'action': 'parse', 'page': titulo, 'prop': 'text', 'format': 'json',
                                                    'formatversion': 2, 'redirects': 1},
                 offline=cfg.offline, timeout=cfg.fuentes.timeout_http_s)
    if 'error' in d:
        raise RuntimeError(f"Wikipedia: {d['error'].get('info', d['error'])}")
    return d['parse']['text']


def _num(x):
    try:
        return float(str(x).replace(',', '').replace('%', '').strip())
    except (TypeError, ValueError):
        return None


def tablas(html: str) -> list[pd.DataFrame]:
    try:
        ts = pd.read_html(StringIO(html))
    except ValueError:
        return []
    out = []
    for d in ts:
        d = d.copy()
        d.columns = [str(c[-1] if isinstance(c, tuple) else c) for c in d.columns]
        out.append(d)
    return out


def tablas_resultado(html: str) -> list[tuple[bool, pd.DataFrame]]:
    """[(tiene_fila_hold, DataFrame partido/cand/votos)] para cada tabla con columnas Candidate y Votes."""
    out = []
    for d in tablas(html):
        cc = [c for c in d.columns if c.startswith('Candidate')]
        if 'Votes' not in d.columns or not cc:
            continue
        pc = [c for c in d.columns if c.startswith('Party')]
        partido = (d[pc[-1]] if pc else pd.Series([''] * len(d), index=d.index)).astype(str)
        cand = d[cc[0]].astype(str)
        v = d['Votes'] if isinstance(d['Votes'], pd.Series) else d['Votes'].iloc[:, 0]
        v = v.map(_num)
        hold = bool(partido.str.contains('hold|gain', case=False).any())
        ok = v.notna() & ~cand.str.contains(EXCLUIR) & ~partido.str.contains(EXCLUIR)
        sub = pd.DataFrame({'partido': partido[ok].replace('nan', ''), 'cand': cand[ok].replace('nan', ''),
                            'votos': v[ok]}).reset_index(drop=True)
        if not sub.empty:
            out.append((hold, sub))
    return out


def es_escrito(s: pd.DataFrame) -> pd.Series:
    return s.cand.str.contains('Write', case=False) | s.partido.str.contains('Write', case=False)


def tabla_general(html: str) -> pd.DataFrame | None:
    """Tabla de la elección general: la última con fila «… hold/gain»; si no hay, la de más votos con algún partido
    distinto del demócrata (el formato «Majority/Turnout» de 2006)."""
    ts = tablas_resultado(html)
    con_hold = [s for h, s in ts if h]
    if con_hold:
        return con_hold[-1]
    multi = [s for _, s in ts if s.partido.str.contains('Republican|Independent|Statehood|Libertarian').any()]
    return max(multi, key=lambda s: s.votos.sum()) if multi else None


def tabla_primaria_d(html: str, apellido: str) -> pd.DataFrame | None:
    """Primaria demócrata: la tabla sin fila «hold» con el apellido del nominado, solo demócratas (o sin columna de
    partido) y al menos 3 filas. Se toma la primera (la de primera ronda si hubiera varias)."""
    for hold, s in tablas_resultado(html):
        if hold or len(s) < 3 or not s.cand.str.contains(apellido, regex=False).any():
            continue
        p = s.partido[~es_escrito(s)]
        if (p.str.contains('^Democratic', regex=True) | (p == '')).all():
            return s
    return None


def apellido(nombre: str) -> str:
    n = re.sub(r'\s*\(.*', '', str(nombre)).replace('"', '').strip()
    partes = [x for x in n.split() if x.rstrip('.') not in ('Jr', 'Sr', 'II', 'III')]
    return partes[-1] if partes else n
