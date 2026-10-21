"""Cliente HTTP común: User-Agent de navegador, timeout, reintentos ante 429/5xx y modo sin red."""
from __future__ import annotations

import logging
import time

log = logging.getLogger(__name__)

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/131.0 Safari/537.36 ODISEO-pronostico/1.0')


class SinRed(ConnectionError):
    """Se lanza en modo offline para que cada fuente use su caché."""


def _get(url, *, params=None, offline=False, timeout=30, reintentos=3, pausa_base=5.0, espera_max=60.0):
    if offline:
        raise SinRed('modo sin red')
    import requests
    ultimo = None
    for intento in range(reintentos):
        try:
            r = requests.get(url, params=params, timeout=timeout, headers={'User-Agent': UA})
        except requests.RequestException as exc:
            ultimo = exc
            time.sleep(min(pausa_base * 2 ** intento, espera_max))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            ra = r.headers.get('Retry-After')
            espera = float(ra) if ra and ra.isdigit() else pausa_base * 2 ** intento
            log.warning('%s -> HTTP %s; reintento %d/%d', url.split('?')[0], r.status_code, intento + 1, reintentos)
            ultimo = RuntimeError(f'HTTP {r.status_code}')
            time.sleep(min(espera, espera_max))
            continue
        r.raise_for_status()
        return r
    raise RuntimeError(f'{url.split("?")[0]} sin respuesta válida tras {reintentos} intentos: {ultimo}')


def get_json(url: str, **kw):
    r = _get(url, **kw)
    try:
        return r.json()
    except ValueError as exc:
        raise ValueError(f'Respuesta no JSON de {url}: {r.text[:200]}') from exc


def get_text(url: str, **kw) -> str:
    r = _get(url, **kw)
    r.encoding = r.encoding or 'utf-8'
    return r.text
