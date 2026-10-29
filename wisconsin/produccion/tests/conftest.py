"""Fixtures sin red: respuestas reales (29-oct-2026, 02:15 UTC (28-oct, 21:15 CT), captura de GitHub Actions) de Wikipedia, 270toWin, Kalshi, Polymarket, civicAPI y GitHub."""
import datetime as _dt
import json
from pathlib import Path

import pytest

from wi_pronostico import config as cfgmod
from wi_pronostico import red

FIX = Path(__file__).parent / 'fixtures'
RAIZ = Path(__file__).parent.parent
MODULOS_JSON = ('wi_pronostico.encuestas', 'wi_pronostico.mercados', 'wi_pronostico.anticipado')
CORTE = '2026-10-28'                       # fecha de los fixtures: las pruebas no dependen del día en que corren


class RelojFijo(_dt.datetime):
    """«Ahora» = mediodía del corte de los fixtures (los mercados fechan sus snapshots con la hora real)."""

    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 28, 22, 0, tzinfo=tz)


def _archivo_json(url: str, params: dict) -> str:
    if 'wikipedia' in url:
        return 'wikipedia_wi_gob.json'
    if 'kalshi' in url and '/candlesticks' in url:            # reconstrucción: velas diarias (revisión OH-05)
        return f"kalshi_velas_{url.split('/markets/')[1].split('/')[0]}.json"
    if 'kalshi' in url:
        return 'kalshi_markets.json'
    if 'prices-history' in url:                               # reconstrucción: historial de Polymarket por token
        return f"polymarket_historial_{params['market'][:16]}.json"
    if 'polymarket' in url:
        return f"polymarket_{params['slug']}.json"
    if 'civicapi' in url:
        return f"civicapi_WI_{url.rstrip('/').split('/')[-1]}.json"
    raise AssertionError(f'URL no esperada: {url}')


class RedSimulada:
    """Sirve los fixtures; `caidas` = fragmentos de URL que deben fallar (simula una API caída)."""

    def __init__(self):
        self.llamadas, self.caidas = [], set()

    def _revisar(self, url, offline):
        if offline:
            raise red.SinRed('modo sin red')
        self.llamadas.append(url)
        if any(c in url for c in self.caidas):
            raise RuntimeError(f'HTTP 503 simulado en {url}')

    def get_json(self, url, *, params=None, offline=False, **kw):
        self._revisar(url, offline)
        return json.loads((FIX / _archivo_json(url, params or {})).read_text(encoding='utf-8'))

    def get_text(self, url, *, params=None, offline=False, **kw):
        self._revisar(url, offline)
        if 'githubusercontent' in url:
            return (RAIZ / 'data' / 'fte_raw_polls_2023.csv').read_text(encoding='utf-8')
        if '270towin' in url:
            return (FIX / 't270_wi_gob.html').read_text(encoding='utf-8')
        raise AssertionError(f'URL no esperada: {url}')


@pytest.fixture
def red_simulada(monkeypatch):
    r = RedSimulada()
    for mod in MODULOS_JSON:
        monkeypatch.setattr(f'{mod}.get_json', r.get_json)
    monkeypatch.setattr('wi_pronostico.encuestas.get_text', r.get_text)
    monkeypatch.setattr('wi_pronostico.historico.get_text', r.get_text)
    monkeypatch.setattr('time.sleep', lambda s: None)
    monkeypatch.setattr('wi_pronostico.mercados.datetime', RelojFijo)
    monkeypatch.setattr('wi_pronostico.config.datetime', RelojFijo)
    return r


@pytest.fixture
def cfg(tmp_path):
    c = cfgmod.cargar_config(corte=CORTE)
    c.rutas['salidas'] = str(tmp_path / 'salidas')
    c.rutas['logs'] = str(tmp_path / 'logs')
    c.rutas['encuestas_base'] = str(RAIZ / 'data' / 'encuestas_verificadas_wi.csv')
    c.modelo['n_simulaciones'] = 60_000
    c.ejecucion['graficas'] = False
    return c
