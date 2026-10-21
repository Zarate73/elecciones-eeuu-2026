"""Fixtures sin red: respuestas con el formato de Wikipedia (API MediaWiki), 270toWin, Kalshi, Civic Forge y GitHub."""
import json
from pathlib import Path

import pytest

from ga_pronostico import config as cfgmod
from ga_pronostico import red

FIX = Path(__file__).parent / 'fixtures'
RAIZ = Path(__file__).parent.parent


def _json(url, params):
    if 'wikipedia' in url:
        return 'wikipedia_gob.json' if 'gubernatorial' in params['page'] else 'wikipedia_sen.json'
    if 'kalshi' in url:
        return 'kalshi_markets.json'
    if 'civicforge' in url:
        anio = url.split('/history/')[1].split('/')[0] if '/history/' in url else '2026'
        return f"civicforge_{params['groupBy']}_{anio}.json"
    raise AssertionError(f'URL no esperada: {url}')


@pytest.fixture
def red_simulada(monkeypatch):
    llamadas = []

    def fjson(url, *, params=None, offline=False, **kw):
        if offline:
            raise red.SinRed('modo sin red')
        llamadas.append(url)
        return json.loads((FIX / _json(url, params or {})).read_text(encoding='utf-8'))

    def ftext(url, *, params=None, offline=False, **kw):
        if offline:
            raise red.SinRed('modo sin red')
        llamadas.append(url)
        if 'githubusercontent' in url:
            return (RAIZ / 'data' / 'fte_raw_polls_2023.csv').read_text(encoding='utf-8')
        if '270towin' in url:
            return (FIX / ('t270_gob.html' if 'governor' in url else 't270_sen.html')).read_text(encoding='utf-8')
        raise AssertionError(f'URL no esperada: {url}')

    for mod in ('ga_pronostico.encuestas', 'ga_pronostico.externas'):
        monkeypatch.setattr(f'{mod}.get_json', fjson)
    monkeypatch.setattr('ga_pronostico.encuestas.get_text', ftext)
    monkeypatch.setattr('ga_pronostico.historico.get_text', ftext)
    monkeypatch.setattr('time.sleep', lambda s: None)
    return llamadas


@pytest.fixture
def cfg(tmp_path):
    c = cfgmod.cargar_config(corte='2026-10-20')
    c.rutas['salidas'] = str(tmp_path / 'salidas')
    c.rutas['logs'] = str(tmp_path / 'logs')
    x = FIX / 'gratings_georgia.xlsx'          # el Excel propio no se publica; si existe localmente se prueba
    c.rutas['encuestas_propias'] = str(x) if x.exists() else ''
    c.modelo['n_simulaciones'] = 60_000
    c.ejecucion['graficas'] = False
    return c
