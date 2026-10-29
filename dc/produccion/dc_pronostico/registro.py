"""Registro de votantes de la DCBOE (informe mensual en PDF): contexto, no entra al pronóstico.

D.C. no publica voto anticipado por partido (civicAPI devuelve ceros para DC), así que lo único partidista que hay en
vivo es el registro: demócratas 76 %, sin partido 17 %, republicanos 5 % (30-sep-2026).
"""
from __future__ import annotations

import io
import json
import logging
import re
from urllib.parse import urljoin

from .red import _get, get_text

log = logging.getLogger(__name__)
PARTIDOS = {'DEM': 'D', 'REP': 'R', 'STG': 'Verde', 'N-P': 'Sin partido', 'LIB': 'Libertario', 'OTH': 'Otros'}


def leer_pdf(b: bytes) -> dict:
    from pypdf import PdfReader
    t = PdfReader(io.BytesIO(b)).pages[0].extract_text()
    fecha = re.search(r'AS OF ([A-Z]+ \d{1,2}, \d{4})', t)
    cab = re.search(r'WARD\s+(.*?)\s+TOTALS', t, re.S)
    cols = [c for c in re.split(r'\s+', cab.group(1).strip()) if c in PARTIDOS]
    tot = re.search(r'\nTOTALS[ \t]+(\d[\d,]*,\d{3}(?:[ \t]+[\d,]+)+)', t)     # la fila de totales, no la cabecera
    nums = [int(x.replace(',', '')) for x in tot.group(1).split()][:len(cols) + 1]
    if len(nums) != len(cols) + 1 or sum(nums[:-1]) != nums[-1]:
        raise ValueError('registro: la fila TOTALS no cuadra')
    por = {PARTIDOS[c]: n for c, n in zip(cols, nums)}
    return {'fecha_informe': fecha.group(1).title() if fecha else None, 'total': nums[-1], 'por_partido': por,
            'pct': {k: 100 * v / nums[-1] for k, v in por.items()}}


def obtener_registro(cfg) -> dict:
    cache = cfg.dir_cache / 'registro.json'
    try:
        url = cfg.fuentes.dcboe_registro
        html = get_text(url, offline=cfg.offline, timeout=cfg.fuentes.timeout_http_s)
        m = re.search(r'href="([^"]+)"[^>]*>\s*Monthly report for the period ending ([^<]+)<', html, re.I)
        if not m:
            raise ValueError('registro: no se encontró el informe mensual')
        pdf = urljoin(url, m.group(1).replace('&amp;', '&'))
        r = leer_pdf(_get(pdf, offline=cfg.offline, timeout=60).content)
        r.update({'estado': 'en_vivo', 'url': pdf})
        cache.write_text(json.dumps(r, ensure_ascii=False), encoding='utf-8')
        return r
    except Exception as exc:                                        # noqa: BLE001
        log.warning('DCBOE registro: %s', exc)
        if cache.exists():
            r = json.loads(cache.read_text(encoding='utf-8'))
            r['estado'] = 'cache'
            return r
        return {'estado': f'error: {str(exc)[:80]}'}
