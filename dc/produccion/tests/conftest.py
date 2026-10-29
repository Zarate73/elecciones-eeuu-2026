"""Pruebas sin red: las respuestas reales del 28-oct-2026 (Wikipedia, DCBOE, Polymarket) se sirven desde fixtures/."""
import gzip
import json
import re
import shutil
import sys
from pathlib import Path

import pytest

PROD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROD))
FIX = Path(__file__).resolve().parent / 'fixtures'


class Resp:
    def __init__(self, cuerpo: bytes, status=200):
        self.content, self.status_code, self.headers, self.encoding = cuerpo, status, {}, 'utf-8'

    @property
    def text(self):
        return self.content.decode('utf-8')

    def json(self):
        return json.loads(self.content)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f'HTTP {self.status_code}')


def servidor(extra=None):
    """Devuelve un _get falso: Wikipedia por título, DCBOE registro, Kalshi vacío y Polymarket real del 28-oct."""
    indice = json.loads((FIX / 'wiki_indice.json').read_text())
    extra = extra or {}

    def _get(url, *, params=None, offline=False, **kw):
        from dc_pronostico.red import SinRed
        if offline:
            raise SinRed('modo sin red')
        params = params or {}
        for patron, cuerpo in extra.items():
            if re.search(patron, url + ' ' + json.dumps(params, sort_keys=True)):
                return cuerpo if isinstance(cuerpo, Resp) else Resp(json.dumps(cuerpo).encode())
        if 'wikipedia.org' in url:
            t = params.get('page', '').replace(' ', '_')
            if t not in indice:
                return Resp(json.dumps({'error': {'info': f"The page you specified doesn't exist: {t}"}}).encode())
            with gzip.open(FIX / indice[t], 'rb') as g:
                return Resp(g.read())
        if 'voter-registration-statistics' in url:
            with gzip.open(FIX / 'dcboe_registro.html.gz', 'rb') as g:
                return Resp(g.read())
        if url.endswith('.pdf') or 'Data-Statistics-Report-9_2026' in url:
            return Resp((FIX / 'dcboe_registro_2026_09.pdf').read_bytes())
        if 'kalshi.com' in url:
            return Resp(json.dumps({'series': []} if url.endswith('/series') else {'events': [], 'cursor': ''}).encode())
        if 'polymarket.com' in url:
            return Resp((FIX / 'poly2_DC_mayoral_election.json').read_bytes())
        raise AssertionError(f'URL no prevista en las pruebas: {url}')
    return _get


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    from dc_pronostico import red, registro
    from dc_pronostico.config import cargar_config
    monkeypatch.setattr(red, '_get', servidor())
    monkeypatch.setattr(registro, '_get', red._get)
    c = cargar_config()
    c.rutas['salidas'] = str(tmp_path / 'salidas')
    c.rutas['logs'] = str(tmp_path / 'logs')
    c.modelo['n_simulaciones'] = 40000
    c.fuentes['pausa_wikipedia_s'] = 0
    c.ejecucion['graficas'] = False
    c.corte_manual = __import__('datetime').date(2026, 10, 28)
    monkeypatch.setattr(type(c), 'hoy', property(lambda self: __import__('datetime').date(2026, 10, 28)))
    return c
