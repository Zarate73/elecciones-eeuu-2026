"""Página de Wikipedia de la elección 2026: boleta de la general, primaria demócrata y encuestas de la general.

- Boleta: la tabla de la general (aún sin votos) debe traer a los tres candidatos de la configuración; si falta uno o
  aparece otro con partido, se avisa (p. ej., si un concejal lanzara una candidatura por escrito).
- Encuestas de la general: tablas con columna «Poll source» y una columna del opositor (Hamilton). Al 28-oct no hay
  ninguna; las únicas encuestas son de la primaria (WaPo/GMU, City Cast/True Dot) y no se usan.
"""
from __future__ import annotations

import logging
import re

import pandas as pd

from .wiki import _num, pagina_html, tabla_primaria_d, tablas

log = logging.getLogger(__name__)
MESES = {m: i for i, m in enumerate(('january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
                                      'september', 'october', 'november', 'december'), 1)}


def fechas_campo(txt: str, anio: int = 2026) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    """«May 27 – June 1, 2026» / «October 20–22, 2026» / «Oct 3, 2026» -> (inicio, fin)."""
    t = re.sub(r'\[.*?\]', '', str(txt)).replace('–', '-').replace('—', '-').strip()
    m = re.findall(r'([A-Za-z]+)\.?\s+(\d{1,2})', t)
    if not m:
        return None, None
    y = re.search(r'(20\d\d)', t)
    y = int(y.group(1)) if y else anio

    def ts(mes, dia):
        k = mes.lower()
        n = next((v for kk, v in MESES.items() if kk.startswith(k[:3])), None)
        return pd.Timestamp(y, n, int(dia)) if n else None
    ini = ts(*m[0])
    fin = ts(*m[-1])
    solo_dia = re.search(r'-\s*(\d{1,2})\s*,', t)          # «October 20-22, 2026»
    if len(m) == 1 and solo_dia and ini is not None:
        fin = ini.replace(day=int(solo_dia.group(1)))
    return ini, fin


def _pct(x):
    v = _num(re.sub(r'\[.*?\]', '', str(x)))
    return v


def encuestas_general(html: str, cfg) -> pd.DataFrame:
    e = cfg.eleccion
    filas = []
    for d in tablas(html):
        cols = list(d.columns)
        fuente = next((c for c in cols if 'Poll source' in c), None)
        c_op = next((c for c in cols if e.opositor in c), None)
        c_d = next((c for c in cols if e.candidato_d in c), None)
        if not (fuente and c_op and c_d):
            continue
        c_fecha = next((c for c in cols if 'Date' in c), None)
        c_n = next((c for c in cols if 'Sample' in c), None)
        c_v = next((c for c in cols if e.verde in c), None)
        c_ind = next((c for c in cols if 'Undecided' in c), None)
        for _, r in d.iterrows():
            ini, fin = fechas_campo(r.get(c_fecha, ''))
            dv, ov = _pct(r[c_d]), _pct(r[c_op])
            if fin is None or dv is None or ov is None:
                continue
            ntxt = str(r.get(c_n, ''))
            n = _num(re.sub(r'\(.*|\[.*', '', ntxt))
            pop = 'LV' if 'LV' in ntxt else 'RV' if 'RV' in ntxt else 'A' if re.search(r'\(A\)', ntxt) else ''
            gv = _pct(r[c_v]) if c_v else None
            ind = _pct(r[c_ind]) if c_ind else None
            filas.append({'pollster': re.sub(r'\[.*?\]', '', str(r[fuente])).strip(), 'inicio': ini, 'fin': fin, 'n': n,
                          'pop': pop, 'lewis_george': dv, 'hamilton': ov, 'gross': gv,
                          'indecisos': ind, 'origen': 'wikipedia'})
    return pd.DataFrame(filas, columns=['pollster', 'inicio', 'fin', 'n', 'pop', 'lewis_george', 'hamilton', 'gross',
                                        'indecisos', 'origen'])


def boleta(html: str, cfg) -> dict:
    """Candidatos de la tabla de la general (la última con los tres apellidos o con «Write-in»)."""
    e = cfg.eleccion
    cands = None
    for d in tablas(html):
        cc = [c for c in d.columns if c.startswith('Candidate')]
        if not cc:
            continue
        txt = ' '.join(d[cc[0]].astype(str))
        if e.opositor in txt and e.candidato_d in txt:
            cands = d
    if cands is None:
        return {'ok': False, 'candidatos': [], 'avisos': ['Wikipedia: no se encontró la tabla de la general']}
    pc = [c for c in cands.columns if c.startswith('Party')]
    cc = [c for c in cands.columns if c.startswith('Candidate')][0]
    lista = []
    for _, r in cands.iterrows():
        nom = str(r[cc])
        if re.search(r'Total|Write-in|nan|Over|Under', nom, re.I):
            continue
        lista.append({'candidato': nom, 'partido': str(r[pc[-1]]) if pc else '', 'votos': _num(r.get('Votes'))})
    faltan = [x for x in (e.candidato_d, e.opositor, e.verde) if not any(x in c['candidato'] for c in lista)]
    extra = [c['candidato'] for c in lista if not any(x in c['candidato'] for x in (e.candidato_d, e.opositor, e.verde))]
    avisos = []
    if faltan:
        avisos.append(f"Wikipedia: falta en la boleta {', '.join(faltan)}")
    if extra:
        avisos.append(f"Wikipedia: candidato no previsto en la general: {', '.join(extra)} (revisar opositor_fuerte)")
    con_votos = any(c['votos'] is not None and c['votos'] == c['votos'] and c['votos'] > 0 for c in lista)   # NaN ≠ NaN
    return {'ok': not faltan, 'candidatos': lista, 'avisos': avisos, 'con_resultados': bool(con_votos)}


def primaria(html: str, cfg) -> float | None:
    """% de primera ronda del nominado demócrata en la primaria de junio (solo para el escenario M3 y el reporte)."""
    p = tabla_primaria_d(html, cfg.eleccion.candidato_d)
    if p is None:
        return None
    return float(100 * p[p.cand.str.contains(cfg.eleccion.candidato_d, regex=False)].votos.max() / p.votos.sum())


def obtener_eleccion(cfg) -> dict:
    cache = cfg.dir_cache / 'eleccion_2026.json'
    import json
    try:
        html = pagina_html(cfg, cfg.fuentes.wikipedia_pagina)
        b = boleta(html, cfg)
        enc = encuestas_general(html, cfg)
        pr = primaria(html, cfg)
        r = {'estado': 'en_vivo', 'boleta': b, 'encuestas': enc, 'primaria_pct': pr}
        cache.write_text(json.dumps({'boleta': b, 'primaria_pct': pr,
                                     'encuestas': enc.astype({'inicio': str, 'fin': str}).to_dict('records')},
                                    ensure_ascii=False, default=str), encoding='utf-8')
        return r
    except Exception as exc:                                        # noqa: BLE001
        log.warning('Wikipedia 2026: %s', exc)
        if cache.exists():
            c = json.loads(cache.read_text(encoding='utf-8'))
            enc = pd.DataFrame(c['encuestas'], columns=['pollster', 'inicio', 'fin', 'n', 'pop', 'lewis_george', 'hamilton',
                                                        'gross', 'indecisos', 'origen'])
            for k in ('inicio', 'fin'):
                enc[k] = pd.to_datetime(enc[k], errors='coerce')
            return {'estado': 'cache', 'boleta': c['boleta'], 'encuestas': enc, 'primaria_pct': c.get('primaria_pct')}
        return {'estado': f'error: {str(exc)[:80]}', 'boleta': {'ok': False, 'candidatos': [], 'avisos': []},
                'encuestas': encuestas_general('', cfg)}
