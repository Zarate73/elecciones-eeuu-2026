"""Pruebas sin red: formatos reales de las fuentes oficiales (archivos 2026 publicados en cero el 31-oct y elecciones
2022/2024 con votos) y la comparación contra el pronóstico."""
import gzip
import json
import shutil
from datetime import datetime, timezone

import pytest

from conftest import FIX, RAIZ
from res_eeuu import fuentes as F
from res_eeuu.comparar import comparar, crps_t
from res_eeuu.pipeline import cargar_config, ejecutar

G = {'timeout_s': 5, 'dia_eleccion': '2026-11-03', 'wikipedia_api': 'https://en.wikipedia.org/w/api.php'}


def car(d, r, dp='DEM', rp='REP', wiki='x'):
    return {'estado': 'X', 'cargo': 'X', 'd': {'apellido': d, 'partido': dp}, 'r': {'apellido': r, 'partido': rp}, 'wikipedia': wiki}


def servir(monkeypatch, mapa):
    def js(url, params=None, **kw):
        for k, v in mapa.items():
            if k in url + str(params or ''):
                return json.loads((FIX / v).read_text()) if v.endswith('.json') else v
        raise AssertionError(url)

    def tx(url, **kw):
        for k, v in mapa.items():
            if k in url:
                return (FIX / v).read_text(encoding='utf-8')
        raise AssertionError(url)
    monkeypatch.setattr(F, 'get_json', js)
    monkeypatch.setattr(F, 'get_text', tx)


def test_carreras_cubren_los_14_estados_del_tablero():
    c = cargar_config()
    assert len(c['carreras']) == 14
    for k in c['carreras']:
        assert (RAIZ.parent / 'tablero' / 'datos' / f'{k}.json').exists(), k


def test_ncsbe_2026_en_cero_y_2024_con_votos(monkeypatch):
    servir(monkeypatch, {'20261103': 'ncsbe_2026.json', '20241105': 'ncsbe_2024.json'})
    assert F.ncsbe(car('Cooper', 'Whatley'), {'url': 'x/20261103/', 'contienda': 'US SENATE'}, G) is None
    c = F.ncsbe(car('Stein', 'Robinson'), {'url': 'x/20241105/', 'contienda': 'NC GOVERNOR'}, G)
    assert c.votos_D > c.votos_R > 0 and c.avance == pytest.approx(1.0) and c.votos_otros > 0
    assert 100 * c.votos_D / c.total == pytest.approx(54.9, abs=0.2)          # Stein 54.9 % (certificado)


def test_florida_2026_en_cero_y_2024_con_votos(monkeypatch):
    servir(monkeypatch, {'2026': 'florida_2026.txt', '2024': 'florida_2024.txt'})
    assert F.florida_dos(car('Jolly', 'Donalds'), {'url': '2026', 'carrera': 'GOV'}, G) is None
    c = F.florida_dos(car('Harris', 'Trump'), {'url': '2024', 'carrera': 'PRE'}, G)
    assert 100 * c.votos_R / c.total == pytest.approx(56.1, abs=0.2)           # Trump 56.1 % (2024)
    assert 0.95 < c.avance <= 1.0                                              # archivo final: 97 % de precintos


def test_california_en_cero_y_con_votos(monkeypatch, tmp_path):
    servir(monkeypatch, {'governor': 'california_2026.json'})
    cr = car('Becerra', 'Hilton', 'Dem', 'Rep')
    assert F.california_sos(cr, {'url': 'governor'}, G) is None
    d = json.loads((FIX / 'california_2026.json').read_text())
    d['candidates'][0]['Votes'], d['candidates'][1]['Votes'] = '1,200,000', '800,000'
    d['Reporting'] = '25.0% (5,965 of 23,860) precincts reporting'
    (FIX / 'tmp_ca.json').write_text(json.dumps(d))
    try:
        servir(monkeypatch, {'governor': 'tmp_ca.json'})
        c = F.california_sos(cr, {'url': 'governor'}, G)
        assert (c.votos_D, c.votos_R) == (1_200_000, 800_000) and c.avance == pytest.approx(0.25, abs=1e-3)
    finally:
        (FIX / 'tmp_ca.json').unlink()


def test_pennsylvania_2026_en_cero(monkeypatch):
    servir(monkeypatch, {'GetSummaryData': 'pa_resumen_2026.json', 'GetOfficeNames': 'pa_oficinas_2026.json'})
    assert F.pennsylvania_dos(car('Shapiro', 'Garrity'), {'oficina': 'Governor'}, G) is None


def test_georgia_espera_la_eleccion_y_lee_el_export(monkeypatch):
    servir(monkeypatch, {'jurisdictions': 'georgia_jurisdiccion_2026_10_31.json'})
    assert F.georgia_ev(car('Bottoms', 'Jackson'), {'contienda': 'Governor'}, G) is None    # 31-oct: aún no está el 3-nov
    j = json.loads((FIX / 'georgia_jurisdiccion_2026_10_31.json').read_text())
    j['elections'].insert(0, {'publicElectionId': '2026NovGen', 'electionDate': '2026-11-03'})
    (FIX / 'tmp_ga.json').write_text(json.dumps(j))
    try:
        servir(monkeypatch, {'jurisdictions': 'tmp_ga.json', 'export-2026NovGen': 'georgia_export_2022.json'})
        c = F.georgia_ev(car('Abrams', 'Kemp'), {'contienda': 'Governor'}, G)
        assert (c.votos_D, c.votos_R, c.votos_otros) == (1813673, 2111572, 28163) and c.avance == 1.0
    finally:
        (FIX / 'tmp_ga.json').unlink()


def test_texas_descubre_la_eleccion(monkeypatch):
    servir(monkeypatch, {'static/data/Version.json': 'tx_version.json', 'ElectionConstants_': 'tx_constantes.json',
                         '49664/Version.json': 'tx_version_eleccion.json', 'OfficeSummary': 'tx_resumen.json', 'Home.json': 'tx_home.json'})
    assert F.texas_sos(car('Hinojosa', 'Abbott'), {'anio': '2026', 'oficina': 'GOVERNOR'}, G) is None   # 2026 aún no publicada
    c = F.texas_sos(car('Allred', 'Cruz'), {'anio': '2024', 'oficina': 'U. S. SENATOR'}, G)
    assert (c.votos_D, c.votos_R) == (5031249, 5990741) and c.avance == 1.0


def test_dcboe_formato_2024(monkeypatch):
    servir(monkeypatch, {'getCityWide': 'dcboe_2024.json'})
    c = F.dcboe(car('Norton', 'Freeman', 'DEM', 'STG'), {'eleccion': '2024-General-Election', 'contienda': 'DELEGATE'}, G)
    assert (c.votos_D, c.votos_R) == (251540, 21873) and c.votos_otros == 19765 + 19033 + 1858   # sin sobre/subvotos


def test_wikipedia_respaldo(monkeypatch):
    texto = json.loads(gzip.open(FIX / 'wiki_2022_Washington_D_C_mayoral_election.json.gz').read())
    monkeypatch.setattr(F, 'get_json', lambda *a, **k: texto)
    c = F.wikipedia(car('Bowser', 'Grant', wiki='2022'), {}, G)
    assert 100 * c.votos_D / c.total == pytest.approx(74.62, abs=0.01) and c.avance is None


def test_crps_y_comparacion():
    p = {'P_D': 0.8, 'pct_D': 52, 'pct_R': 46, 'margen': 6.0, 'sd': 4.0, 'nu': 8, 'margen_IC80': [1, 11], 'margen_IC95': [-3, 15],
         'pct_D_IC80': [49, 55], 'pct_R_IC80': [43, 49]}
    r = comparar(p, {'votos_D': 49, 'votos_R': 51, 'votos_otros': 0, 'total': 100, 'avance': 0.5, 'fuente': 'x'})
    assert r['estado'] == 'parcial' and r['margen'] == pytest.approx(-2) and r['error_margen'] == pytest.approx(-8)
    assert not r['en_IC80'] and r['en_IC95'] and not r['acierto_lider'] and r['brier'] == pytest.approx(0.64)
    assert 0.02 < r['percentil'] < 0.1
    assert crps_t(6, 6, 4, 8) < crps_t(-2, 6, 4, 8)
    assert comparar(p, None)['estado'] == 'sin_datos'


def test_corrida_congela_y_escribe(tmp_path):
    tab = tmp_path / 'tablero'
    shutil.copytree(RAIZ.parent / 'tablero' / 'datos', tab)
    res = tmp_path / 'res'
    (res / 'data').mkdir(parents=True)
    (res / 'data' / 'manuales.csv').write_text('clave,hora_utc,votos_D,votos_R,votos_otros,avance,fuente,url\n'
                                               'ohio,2026-11-04T02:00:00Z,1000,1100,20,0.4,AP,\n')
    sin = {k: (lambda *a, **kw: None) for k in F.ADAPTADORES}
    antes = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)
    r = ejecutar(ahora=antes, dir_tablero=tab, dir_res=res, adaptadores=sin)
    assert not r['congelado'] and not (res / 'pronosticos_finales' / 'ohio.json').exists()
    despues = datetime(2026, 11, 4, 2, tzinfo=timezone.utc)
    r = ejecutar(ahora=despues, dir_tablero=tab, dir_res=res, adaptadores=sin)
    assert r['congelado'] and len(r['estados']) == 14
    o = r['estados']['ohio']
    assert o['estado'] == 'parcial' and o['fuente'] == 'Manual: AP' and o['pronostico_congelado']
    assert r['agregado']['con_datos']['n'] == 1 and r['agregado']['casi_completos'] is None
    # el pronóstico congelado no cambia aunque el tablero cambie después
    d = json.loads((tab / 'ohio.json').read_text()); d['pronostico']['margen'] = 99.0
    (tab / 'ohio.json').write_text(json.dumps(d))
    r2 = ejecutar(ahora=despues, dir_tablero=tab, dir_res=res, adaptadores=sin)
    assert r2['estados']['ohio']['pronostico']['margen'] != 99.0
    assert len(r2['estados']['ohio']['serie']) == 1                      # sin cambios en los votos: no se repite en el historial
    json.loads((tab / 'resultados.json').read_text())                     # JSON estricto


def test_votos_vacios_no_son_nan():
    assert F._n('nan') == 0 and F._n('') == 0 and F._n('1,234') == 1234


def test_wikipedia_infobox_noche_electoral(monkeypatch):
    """3-nov 22:45 ET: la tabla de resultados de Ohio sigue vacía, pero el infobox ya trae el conteo parcial."""
    texto = json.loads(gzip.open(FIX / 'wiki_ohio_noche_2026.json.gz').read())
    monkeypatch.setattr(F, 'get_json', lambda *a, **k: texto)
    c = F.wikipedia(car('Acton', 'Ramaswamy', wiki='x'), {}, G)
    assert (c.votos_D, c.votos_R) == (1658024, 1519697)
    assert 100 * c.votos_D / c.total == pytest.approx(50.4, abs=0.1) and c.votos_otros > 0
    assert c.avance == pytest.approx(0.70) and 'as of 9:58 PM EST' in c.avance_txt
