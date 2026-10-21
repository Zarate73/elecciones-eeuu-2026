"""Cliente HTTP común: User-Agent de navegador, timeout, reintentos ante 429/5xx y modo sin red."""
from __future__ import annotations

import logging
import time

log = logging.getLogger(__name__)

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/131.0 Safari/537.36')


class SinRed(ConnectionError):
    """Se lanza en modo offline para que cada fuente use su caché."""


def get_json(url: str, *, params: dict | None = None, offline: bool = False, timeout: float = 30,
             reintentos: int = 3, pausa_base: float = 5.0, espera_max: float = 60.0):
    if offline:
        raise SinRed('modo sin red')
    import requests
    ultimo = None
    for intento in range(reintentos):
        try:
            r = requests.get(url, params=params, timeout=timeout, headers={'User-Agent': UA})
        except requests.RequestException as exc:          # red caída, DNS, timeout
            ultimo = exc
            time.sleep(min(pausa_base * 2 ** intento, espera_max))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            ra = r.headers.get('Retry-After')
            espera = float(ra) if ra and ra.isdigit() else pausa_base * 2 ** intento
            log.warning('%s -> HTTP %s; reintento %d/%d en %.0f s', url.split('?')[0], r.status_code,
                        intento + 1, reintentos, min(espera, espera_max))
            ultimo = RuntimeError(f'HTTP {r.status_code}')
            time.sleep(min(espera, espera_max))
            continue
        r.raise_for_status()
        try:
            return r.json()
        except ValueError as exc:
            raise ValueError(f'Respuesta no JSON de {url}: {r.text[:200]}') from exc
    raise RuntimeError(f'{url.split("?")[0]} sin respuesta válida tras {reintentos} intentos: {ultimo}')


def get_text(url: str, *, offline: bool = False, timeout: float = 30, reintentos: int = 3,
             pausa_base: float = 5.0, espera_max: float = 60.0) -> str:
    """Igual que get_json, para páginas HTML (270toWin)."""
    if offline:
        raise SinRed('modo sin red')
    import requests
    ultimo = None
    for intento in range(reintentos):
        try:
            r = requests.get(url, timeout=timeout, headers={'User-Agent': UA})
        except requests.RequestException as exc:
            ultimo = exc
            time.sleep(min(pausa_base * 2 ** intento, espera_max))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            ultimo = RuntimeError(f'HTTP {r.status_code}')
            time.sleep(min(pausa_base * 2 ** intento, espera_max))
            continue
        r.raise_for_status()
        r.encoding = r.encoding or 'utf-8'
        return r.text
    raise RuntimeError(f'{url.split("?")[0]} sin respuesta válida tras {reintentos} intentos: {ultimo}')
