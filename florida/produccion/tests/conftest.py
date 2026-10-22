"""Fixtures sin red: respuestas reales (22-oct-2026) de Wikipedia, 270toWin, Kalshi, Polymarket, civicAPI y GitHub."""
import json
from pathlib import Path

import pytest

from fl_pronostico import config as cfgmod
from fl_pronostico import red

FIX = Path(__file__).parent / 'fixtures'
RAIZ = Path(__file__).parent.parent
MODULOS_JSON = ('fl_pronostico.encuestas', 'fl_pronostico.mercados', 'fl_pronostico.anticipado')


def _archivo_json(url: str, params: dict) -> str:
    if 'wikipedia' in url:
        return 'wikipedia_fl_gob.json'
    if 'kalshi' in url:
        return 'kalshi_markets.json'
    if 'polymarket' in url:
        return f"polymarket_{params['slug']}.json"
    if 'civicapi' in url:
        return f"civicapi_FL_{url.rstrip('/').split('/')[-1]}.json"
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
            return (FIX / 't270_fl_gob.html').read_text(encoding='utf-8')
        raise AssertionError(f'URL no esperada: {url}')


@pytest.fixture
def red_simulada(monkeypatch):
    r = RedSimulada()
    for mod in MODULOS_JSON:
        monkeypatch.setattr(f'{mod}.get_json', r.get_json)
    monkeypatch.setattr('fl_pronostico.encuestas.get_text', r.get_text)
    monkeypatch.setattr('fl_pronostico.historico.get_text', r.get_text)
    monkeypatch.setattr('time.sleep', lambda s: None)
    return r


@pytest.fixture
def cfg(tmp_path):
    c = cfgmod.cargar_config(corte='2026-10-22')
    c.rutas['salidas'] = str(tmp_path / 'salidas')
    c.rutas['logs'] = str(tmp_path / 'logs')
    c.rutas['encuestas_base'] = str(RAIZ / 'data' / 'encuestas_verificadas_fl.csv')
    c.modelo['n_simulaciones'] = 60_000
    c.ejecucion['graficas'] = False
    return c
