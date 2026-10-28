"""Cliente HTTP común: User-Agent, timeout, reintentos ante 429/5xx y modo sin red.

Wikimedia (revisión del 27-oct): la API de Wikipedia limita el ritmo por cliente y trata peor a los programas que se
presentan como navegador. Con el User-Agent de Chrome respondió 503/429 desde la primera petición (Retry-After 32–44 s);
identificado según su política (nombre/versión + URL de contacto, sin imitar a un navegador) admite ráfagas cortas y, si
limita, pide 12–15 s. Por eso:
  - a los dominios de Wikimedia se les envía UA_WIKIMEDIA; al resto (270toWin, mercados, civicAPI) el UA de navegador;
  - Retry-After se respeta (hasta espera_max) y Wikimedia tiene más reintentos (RETRY_WIKIMEDIA).
"""
from __future__ import annotations

import logging
import time
from urllib.parse import urlsplit

log = logging.getLogger(__name__)

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/131.0 Safari/537.36 pronostico-elecciones/1.0')
UA_WIKIMEDIA = 'pronostico-elecciones/1.1 (https://github.com/Zarate73/elecciones-eeuu-2026) python-requests'
RETRY_WIKIMEDIA = 5


class SinRed(ConnectionError):
    """Se lanza en modo offline para que cada fuente use su caché."""


def es_wikimedia(url: str) -> bool:
    h = (urlsplit(url).hostname or '').lower()
    return h.endswith(('wikipedia.org', 'wikimedia.org', 'mediawiki.org'))


def _get(url, *, params=None, offline=False, timeout=30, reintentos=3, pausa_base=5.0, espera_max=60.0):
    if offline:
        raise SinRed('modo sin red')
    import requests
    wm = es_wikimedia(url)
    ua = UA_WIKIMEDIA if wm else UA
    if wm:
        reintentos = max(reintentos, RETRY_WIKIMEDIA)
    ultimo = None
    for intento in range(reintentos):
        try:
            r = requests.get(url, params=params, timeout=timeout, headers={'User-Agent': ua})
        except requests.RequestException as exc:
            ultimo = exc
            if intento < reintentos - 1:
                time.sleep(min(pausa_base * 2 ** intento, espera_max))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            ra = (r.headers.get('Retry-After') or '').strip()
            espera = float(ra) + 1 if ra.isdigit() else pausa_base * 2 ** intento
            espera = min(espera, espera_max)
            ultimo = RuntimeError(f'HTTP {r.status_code}')
            if intento < reintentos - 1:
                log.warning('%s -> HTTP %s; reintento %d/%d en %.0f s', url.split('?')[0], r.status_code, intento + 1,
                            reintentos - 1, espera)
                time.sleep(espera)
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
