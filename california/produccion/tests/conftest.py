"""Fixtures: respuestas reales de Civiq (19-oct-2026), Wikipedia y 270toWin (21-oct-2026); Kalshi y GDELT simulados; sin red."""
import json
import shutil
from pathlib import Path

import pytest

from ca_pronostico import config as cfgmod
from ca_pronostico import red

FIX = Path(__file__).parent / 'fixtures'


def _fixture_para(url: str):
    if 'historical-elections' in url:
        return 'civiq_historical_elections.json'
    if 'crosstabs' in url:
        return 'civiq_crosstab_party_age.json'
    if 'ballot-returns' in url:
        return 'civiq_ballot_returns.json'
    if 'geography-breakdown' in url:
        return 'civiq_condados.json'
    if 'kalshi' in url:
        return 'kalshi_markets.json'
    if 'gdelt' in url:
        return 'gdelt_tono.json'
    if 'wikipedia' in url:
        return 'wikipedia_ca_gob_2026-10-21.json'
    raise AssertionError(f'URL no esperada en pruebas: {url}')


@pytest.fixture
def red_simulada(monkeypatch):
    llamadas = []

    def falso(url, *, params=None, offline=False, **kw):
        if offline:
            raise red.SinRed('modo sin red')
        llamadas.append(url)
        return json.loads((FIX / _fixture_para(url)).read_text(encoding='utf-8'))

    def falso_texto(url, *, offline=False, **kw):
        if offline:
            raise red.SinRed('modo sin red')
        llamadas.append(url)
        assert '270towin' in url, url
        return (FIX / 't270_ca_gob_2026-10-21.html').read_text(encoding='utf-8')

    for mod in ('ca_pronostico.civiq', 'ca_pronostico.externas', 'ca_pronostico.encuestas_web'):
        monkeypatch.setattr(f'{mod}.get_json', falso)
    monkeypatch.setattr('ca_pronostico.encuestas_web.get_text', falso_texto)
    monkeypatch.setattr('time.sleep', lambda s: None)
    return llamadas


@pytest.fixture
def cfg(tmp_path):
    """Config real, con salidas en una carpeta temporal y corte fijo (19-oct-2026)."""
    c = cfgmod.cargar_config(corte='2026-10-19')
    c.rutas['salidas'] = str(tmp_path / 'salidas')
    c.rutas['logs'] = str(tmp_path / 'logs')
    c.modelo['n_simulaciones'] = 50_000
    c.ejecucion['graficas'] = False
    return c


EXCEL = cfgmod.RAIZ.parent / 'CALIFORNIA_2026_NOTEBOOK_COMPLETO' / 'CALIFORNIA_GOBERNADOR-v3.xlsx'
