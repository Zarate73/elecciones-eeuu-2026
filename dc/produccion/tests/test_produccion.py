"""Pruebas sin red del paquete dc_pronostico (respuestas reales del 28-oct-2026 en fixtures/)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from dc_pronostico import mercados, rcv
from dc_pronostico.historico import obtener_historico
from dc_pronostico.modelo import loyo


def test_historico_13_generales_en_vivo_y_cifras_certificadas(cfg):
    h = obtener_historico(cfg)
    t = h['tabla'].set_index('anio')
    assert h['estado'] == 'en_vivo (13/13 páginas)'
    assert len(t) == 13
    # contra los resultados certificados de la DCBOE (votos válidos, sin sobre/subvotos)
    assert t.loc[2022, 'pct_d'] == pytest.approx(74.62, abs=0.01)
    assert t.loc[2018, 'pct_d'] == pytest.approx(76.39, abs=0.01)
    assert t.loc[2014, 'pct_d'] == pytest.approx(55.30, abs=0.01)
    # 2010: la tabla de la general (Gray contra Fenty por escrito), no la primaria con más votos
    assert t.loc[2010, 'pct_d'] == pytest.approx(74.20, abs=0.01) and t.loc[2010, 'opositor'] == 'Write-in'
    # 2006: tabla de primaria sin columna de partido; 1974: sin tabla (respaldo del texto, 53 %)
    assert t.loc[2006, 'primaria_pct'] == pytest.approx(57.2, abs=0.05)
    assert t.loc[1974, 'primaria_pct'] == 53.0
    resp = pd.read_csv(cfg.ruta('historico_respaldo')).set_index('anio')
    assert np.allclose(t.pct_d, resp.pct_d, atol=0.01)
    assert t.fuerte.sum() == 6 and set(t.index[t.fuerte == 1]) == {1986, 1994, 1998, 2002, 2010, 2014}


def test_historico_cae_a_cache_y_respaldo(cfg, monkeypatch):
    obtener_historico(cfg)                                  # deja la caché
    from dc_pronostico import red
    original = red._get

    def falla_2010(url, **kw):
        if '2010_Washington' in str(kw.get('params', {}).get('page', '')):
            raise RuntimeError('HTTP 503')
        return original(url, **kw)
    monkeypatch.setattr(red, '_get', falla_2010)
    h = obtener_historico(cfg)
    assert h['estado'].startswith('parcial (12/13') and '2010 cache' in h['estado']
    cfg.offline = True
    (cfg.dir_cache / 'historico_alcaldias.csv').unlink()
    h = obtener_historico(cfg)
    assert h['estado'] == 'respaldo' and len(h['tabla']) == 13


def test_backtest_elige_m1(cfg):
    t = obtener_historico(cfg)['tabla']
    m1 = loyo(t, ['fuerte'])['crps']
    for v in ([], ['fuerte', 'titular'], ['fuerte', 'primaria'], ['fuerte', 'tendencia']):
        assert loyo(t, v)['crps'] > m1, v


def test_pagina_2026_boleta_primaria_y_sin_encuestas_de_la_general(cfg):
    from dc_pronostico.eleccion2026 import obtener_eleccion
    el = obtener_eleccion(cfg)
    b = el['boleta']
    assert el['estado'] == 'en_vivo' and b['ok'] and not b['avisos'] and not b['con_resultados']
    assert len(b['candidatos']) == 3
    assert el['primaria_pct'] == pytest.approx(54.13, abs=0.01)
    assert el['encuestas'].empty                            # WaPo/GMU y True Dot son de la primaria: no entran


def test_fechas_de_campo():
    from dc_pronostico.eleccion2026 import fechas_campo
    assert fechas_campo('May 27 – June 1, 2026') == (pd.Timestamp(2026, 5, 27), pd.Timestamp(2026, 6, 1))
    assert fechas_campo('October 20–22, 2026') == (pd.Timestamp(2026, 10, 20), pd.Timestamp(2026, 10, 22))
    assert fechas_campo('Oct 3, 2026') == (pd.Timestamp(2026, 10, 3), pd.Timestamp(2026, 10, 3))


def test_registro_dcboe(cfg):
    from dc_pronostico.registro import obtener_registro
    r = obtener_registro(cfg)
    assert r['estado'] == 'en_vivo' and r['total'] == 453471 and r['fecha_informe'] == 'September 30, 2026'
    assert r['pct']['D'] == pytest.approx(76.31, abs=0.01) and r['por_partido']['Sin partido'] == 78279


def test_mercados_sin_mercado_de_la_general(cfg):
    mk = mercados.obtener_mercados(cfg)
    assert mk['n_usables'] == 0
    assert mk['kalshi']['estado'].startswith('no_aplica') and mk['polymarket']['estado'].startswith('no_aplica')


def test_mercado_de_la_primaria_no_cuenta_y_uno_de_la_general_si(cfg, monkeypatch):
    from dc_pronostico import red
    from conftest import FIX, servidor
    prim = json.loads((FIX / 'poly_primaria_dc_cerrada.json').read_text())
    assert not mercados.es_mercado_general(prim['events'][0]['title'])
    gen = {'events': [{'id': '1', 'title': 'Washington, D.C. Mayoral Election Winner', 'slug': 'dc-mayor-2026', 'closed': False,
                       'markets': [{'question': 'Will Janeese Lewis George win the D.C. mayoral election?',
                                    'groupItemTitle': 'Janeese Lewis George', 'bestBid': 0.96, 'bestAsk': 0.98}]}]}
    monkeypatch.setattr(red, '_get', servidor({r'polymarket': gen}))
    mk = mercados.obtener_mercados(cfg)
    assert mk['polymarket']['p_D'] == pytest.approx(0.97) and mk['n_usables'] == 1
    for t in ('Who will win the 2026 Democratic D.C. Mayoral Primary?', 'Los Angeles mayoral election winner?',
              'Mayor of Johannesburg after municipal elections?'):
        assert not mercados.es_mercado_general(t)
    assert mercados.es_mercado_general('Washington DC mayoral election winner?')


@pytest.mark.parametrize('semilla', range(5))
def test_rcv_vectorizado_igual_al_conteo_de_la_primaria(semilla):
    """contar_rcv_vector = run_rcv (sin linaje) del modelo de la primaria, también con Lewis George < 50 %."""
    rng = np.random.default_rng(semilla)
    cands = ['Lewis George', 'Hamilton', 'Gross', 'escrito']
    tr = {'escrito': {'Lewis George': 0.35, 'Hamilton': 0.25, 'Gross': 0.05, 'agotada': 0.35},
          'Gross': {'Lewis George': 0.45, 'Hamilton': 0.20, 'agotada': 0.35}}
    V = rng.dirichlet([3, 2.5, 1, 1], 400)
    c = rcv.contar_rcv_vector(V, cands, tr)
    for i in range(len(V)):
        r = rcv.contar_rcv(dict(zip(cands, V[i])), tr)
        assert cands[c['ganador'][i]] == r['ganador']
        assert c['rondas'][i] == len(r['rondas'])
        assert c['cuota_final'][i] == pytest.approx(max(r['rondas'][-1].values()))
    assert (c['rondas'] > 1).any() and (c['ganador'] != 0).any()


def test_corrida_completa(cfg):
    from dc_pronostico.pipeline import ejecutar
    from dc_pronostico.reporte import json_estricto
    r = ejecutar(cfg)
    f = r['modelo']['final']
    assert not r['degradadas']
    assert 75 < f['pct_D'] < 85 and f['P_D'] > 0.99 and f['P_D'] == f['P_D_modelo']
    assert f['pct_D'] + f['pct_opositor'] + f['pct_verde'] + f['pct_escrito'] == pytest.approx(100, abs=1e-6)
    assert f['pct_opositor'] > f['pct_escrito'] > f['pct_verde'] > 0
    assert f['P_primera_ronda'] <= f['P_D']
    rep = json.loads((cfg.dir_salidas / 'ultimo' / 'reporte.json').read_text(encoding='utf-8'))
    assert rep['alcaldia']['P_D'] == pytest.approx(f['P_D'])
    assert 'NaN' not in json_estricto(rep)
    h = pd.read_csv(cfg.dir_salidas / 'historial_pronosticos.csv')
    assert len(h) == 1 and h.base[0] == 'fundamentales'
    esc = r['modelo']['escenarios']
    fuerte = esc[esc.escenario.str.startswith('Si surgiera')].iloc[0]
    assert fuerte.pct_D < f['pct_D'] - 10                    # el criterio del opositor es la variable que más pesa


def test_encuesta_de_la_general_mueve_el_pronostico(cfg):
    """Si aparece una encuesta (archivo complementario), entra combinada por precisión y respeta la reconstrucción."""
    from dc_pronostico.pipeline import ejecutar
    p = cfg.dir_salidas.parent / 'comp.csv'
    pd.DataFrame([{'pollster': 'Encuestadora X', 'inicio': '2026-10-20', 'fin': '2026-10-24', 'n': 600, 'pop': 'LV',
                   'lewis_george': 55, 'hamilton': 30, 'gross': 3, 'otros': 2, 'indecisos': 10, 'fuente': 'prueba',
                   'nota': ''}]).to_csv(p, index=False)
    cfg.rutas['encuestas_complementarias'] = str(p)
    r = ejecutar(cfg, escribir_salidas=False)
    f = r['modelo']['final']
    assert f['base'] == 'fundamentales + encuestas' and 0.3 < f['peso_fundamentales'] < 0.7
    assert f['encuestas']['pct_D'] == pytest.approx(100 * 55 / 88)
    assert 62.5 < f['pct_D'] < 79
    cfg.corte_manual = pd.Timestamp('2026-10-26').date()     # reconstrucción: publicada el 27 (cierre + 3)
    r = ejecutar(cfg, escribir_salidas=False)
    assert r['modelo']['final']['base'] == 'fundamentales'


def test_offline_usa_caches(cfg):
    from dc_pronostico.pipeline import ejecutar
    ejecutar(cfg, escribir_salidas=False)
    cfg.offline = True
    r = ejecutar(cfg, escribir_salidas=False)
    e = r['estados_fuentes']
    assert e['wikipedia_historico'] == 'cache' and e['wikipedia_2026'] == 'cache' and e['dcboe_registro'] == 'cache'
    assert r['modelo']['final']['P_D'] > 0.99


@pytest.mark.parametrize('patron', ['rcv_15_*', 'rcv_17_*', 'rcv_18_*'])
def test_conteo_reproduce_la_tabulacion_certificada_de_la_primaria(patron):
    """rcv.py, con las transferencias publicadas, reproduce ronda por ronda la tabulación certificada del 16-jun-2026
    (alcaldía 1 ronda, at-large 8, Ward 1 4; informes RCTab de la DCBOE)."""
    import importlib.util
    from conftest import FIX, PROD
    spec = importlib.util.spec_from_file_location('vp', PROD.parent / 'backtest' / 'validacion_primaria_2026.py')
    if spec is None or not Path(spec.origin).exists():
        pytest.skip('backtest no incluido en esta copia')
    vp = importlib.util.module_from_spec(spec); spec.loader.exec_module(vp)
    t = vp.leer_rctab(next(FIX.glob(patron + '.csv')))
    r = rcv.contar_rcv({c: x[0][0] for c, x in t['cand'].items()}, vp.matriz_publicada(t))
    assert r['ganador'] == t['ganador'] and len(r['rondas']) == t['rondas']
    for k, ronda in enumerate(r['rondas']):
        tot = sum(x[0][k] for x in t['cand'].values())
        for c, cuota in ronda.items():
            assert cuota * tot == pytest.approx(t['cand'][c][0][k], abs=1e-6)
