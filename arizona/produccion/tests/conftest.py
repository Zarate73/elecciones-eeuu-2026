"""Fixtures sin red: respuestas reales (21-oct-2026) de Wikipedia, 270toWin, Kalshi, Polymarket, civicAPI y GitHub."""
import datetime as _dt
import json
from pathlib import Path

import pytest

from az_pronostico import config as cfgmod
from az_pronostico import red

FIX = Path(__file__).parent / 'fixtures'
RAIZ = Path(__file__).parent.parent
MODULOS_JSON = ('az_pronostico.encuestas', 'az_pronostico.mercados', 'az_pronostico.anticipado')
CORTE = '2026-10-21'                       # fecha de los fixtures: las pruebas no dependen del día en que corren


class RelojFijo(_dt.datetime):
    """«Ahora» = mediodía del corte de los fixtures (los mercados fechan sus snapshots con la hora real)."""

    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 21, 12, 0, tzinfo=tz)


def _archivo_json(url: str, params: dict) -> str:
    if 'wikipedia' in url:
        return 'wikipedia_az_gob.json'
    if 'kalshi' in url:
        return 'kalshi_markets.json'
    if 'polymarket' in url:
        return f"polymarket_{params['slug']}.json"
    if 'civicapi' in url:
        return f"civicapi_AZ_{url.rstrip('/').split('/')[-1]}.json"
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
            return (FIX / 't270_az_gob.html').read_text(encoding='utf-8')
        raise AssertionError(f'URL no esperada: {url}')


@pytest.fixture
def red_simulada(monkeypatch):
    r = RedSimulada()
    for mod in MODULOS_JSON:
        monkeypatch.setattr(f'{mod}.get_json', r.get_json)
    monkeypatch.setattr('az_pronostico.encuestas.get_text', r.get_text)
    monkeypatch.setattr('az_pronostico.historico.get_text', r.get_text)
    monkeypatch.setattr('time.sleep', lambda s: None)
    monkeypatch.setattr('az_pronostico.mercados.datetime', RelojFijo)
    return r


@pytest.fixture
def cfg(tmp_path):
    c = cfgmod.cargar_config(corte=CORTE)
    c.rutas['salidas'] = str(tmp_path / 'salidas')
    c.rutas['logs'] = str(tmp_path / 'logs')
    c.rutas['encuestas_base'] = str(RAIZ / 'data' / 'encuestas_verificadas_az.csv')
    c.modelo['n_simulaciones'] = 60_000
    c.ejecucion['graficas'] = False
    return c
