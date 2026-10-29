"""Kalshi y Polymarket: búsqueda en vivo de un mercado de la general de la alcaldía de D.C.

Al 28-oct-2026 no existe ninguno (Kalshi: 0 de los ~15,300 eventos abiertos; Polymarket: solo la primaria demócrata,
ya resuelta). En cada corrida se vuelve a buscar; si aparece un mercado, su probabilidad para Lewis George entra a la
mezcla logit con el mismo peso que en los demás estados (0.30). «no_aplica» = la búsqueda funcionó y no hay mercado.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone

from .red import get_json

log = logging.getLogger(__name__)
PATRON_DC = re.compile(r'(\bD\.?\s?C\.?\b|Washington,? D\.?C|District of Columbia)', re.I)


def es_mercado_general(titulo: str) -> bool:
    t = str(titulo)
    return bool(re.search(r'mayor', t, re.I) and PATRON_DC.search(t) and not re.search(r'primary|nominee|nomination', t, re.I))


def _p_kalshi(m: dict) -> float | None:
    for a, b in (('yes_bid_dollars', 'yes_ask_dollars'), ('yes_bid', 'yes_ask')):
        x, y = m.get(a), m.get(b)
        try:
            x, y = float(x), float(y)
        except (TypeError, ValueError):
            continue
        if a == 'yes_bid':
            x, y = x / 100, y / 100
        if 0 < x <= y < 1:
            return (x + y) / 2
    for k, esc in (('last_price_dollars', 1), ('last_price', 100)):
        try:
            v = float(m.get(k)) / esc
        except (TypeError, ValueError):
            continue
        if 0 < v < 1:
            return v
    return None


def kalshi(cfg) -> dict:
    f, nom = cfg.fuentes, cfg.eleccion.candidato_d
    series, err = list(f.kalshi_series), []
    try:                                                    # lista de series de elecciones (una sola llamada)
        d = get_json(f'{f.kalshi_api}/series', params={'category': 'Elections'}, offline=cfg.offline,
                     timeout=f.timeout_http_s, reintentos=2)
        series += [s['ticker'] for s in d.get('series') or [] if es_mercado_general(s.get('title', ''))]
    except Exception as exc:                                # noqa: BLE001
        err.append(f'series: {str(exc)[:60]}')
    for s in dict.fromkeys(series):
        try:
            d = get_json(f'{f.kalshi_api}/events', params={'series_ticker': s, 'status': 'open', 'with_nested_markets': 'true'},
                         offline=cfg.offline, timeout=f.timeout_http_s, reintentos=2)
        except Exception as exc:                            # noqa: BLE001
            err.append(f'{s}: {str(exc)[:40]}')
            continue
        for ev in d.get('events') or []:
            if not es_mercado_general(ev.get('title', '')) and s not in f.kalshi_series:
                continue
            for m in ev.get('markets') or []:
                txt = ' '.join(str(m.get(k, '')) for k in ('yes_sub_title', 'subtitle', 'title', 'ticker'))
                if nom.lower() in txt.lower() or re.search(r'democrat', txt, re.I):
                    p = _p_kalshi(m)
                    if p is not None:
                        return {'estado': 'en_vivo', 'p_D': p, 'ticker': m.get('ticker'), 'evento': ev.get('title'),
                                'fecha': datetime.now(timezone.utc).date().isoformat(), 'usable': True}
    if len(err) > len(series):                              # todo falló: no se sabe si hay mercado
        return {'estado': 'error: ' + '; '.join(err)[:100], 'usable': False}
    return {'estado': 'no_aplica (sin mercado de la general)', 'usable': False,
            **({'avisos_busqueda': err} if err else {})}


def polymarket(cfg) -> dict:
    f, nom = cfg.fuentes, cfg.eleccion.candidato_d
    errores, vistos = 0, set()
    for q in f.polymarket_busquedas:
        try:
            d = get_json(f'{f.polymarket_api}/public-search', params={'q': q, 'limit_per_type': 30, 'events_status': 'active'},
                         offline=cfg.offline, timeout=f.timeout_http_s, reintentos=2)
        except Exception:                                   # noqa: BLE001
            errores += 1
            continue
        for ev in d.get('events') or []:
            if ev.get('id') in vistos or ev.get('closed') or not es_mercado_general(ev.get('title', '')):
                continue
            vistos.add(ev.get('id'))
            for m in ev.get('markets') or []:
                txt = f"{m.get('groupItemTitle', '')} {m.get('question', '')}"
                if nom.lower() not in txt.lower() and not re.search(r'democrat', txt, re.I):
                    continue
                p = None
                try:
                    b, a = float(m.get('bestBid')), float(m.get('bestAsk'))
                    if 0 < b <= a < 1:
                        p = (a + b) / 2
                except (TypeError, ValueError):
                    pass
                if p is None:
                    try:
                        p = float(json.loads(m.get('outcomePrices') or '[]')[0])
                    except (ValueError, IndexError, TypeError):
                        p = None
                if p is not None and 0 < p < 1:
                    return {'estado': 'en_vivo', 'p_D': p, 'evento': ev.get('slug'), 'mercado': m.get('question'),
                            'fecha': datetime.now(timezone.utc).date().isoformat(), 'usable': True}
    if errores == len(f.polymarket_busquedas):
        return {'estado': 'error: sin respuesta de la búsqueda', 'usable': False}
    return {'estado': 'no_aplica (sin mercado de la general)', 'usable': False}


def obtener_mercados(cfg) -> dict:
    if cfg.es_reconstruccion:                               # no hubo mercados: nada que reconstruir
        k = {'estado': 'no_aplica (reconstrucción; no hubo mercado de la general)', 'usable': False}
        return {'kalshi': k, 'polymarket': dict(k), 'n_usables': 0, 'promedio_D': None}
    k, p = kalshi(cfg), polymarket(cfg)
    us = [x['p_D'] for x in (k, p) if x.get('usable')]
    return {'kalshi': k, 'polymarket': p, 'n_usables': len(us), 'promedio_D': sum(us) / len(us) if us else None}
