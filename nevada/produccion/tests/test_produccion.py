"""Pruebas sin red del modelo de Nevada (fixtures reales del 22-oct-2026)."""
import json
from datetime import date

import numpy as np
import pandas as pd
import pytest

from nv_pronostico import cli, encuestas, mercados, modelo
from nv_pronostico.anticipado import obtener_anticipado, resumir
from nv_pronostico.pipeline import ejecutar

FIX = __import__('pathlib').Path(__file__).parent / 'fixtures'


# ----------------------------------------------------------------------------------- encuestas
def test_fechas_excel_ingles_y_espanol():
    assert encuestas._fechas_es('Sep 22–26') == (date(2026, 9, 22), date(2026, 9, 26))
    assert encuestas._fechas_es('Nov 16–18, 2025') == (date(2025, 11, 16), date(2025, 11, 18))
    assert encuestas._fechas_es('Dic 11–18, 2025') == (date(2025, 12, 11), date(2025, 12, 18))
    assert encuestas._fechas_es('Jun 27–Jul 2') == (date(2026, 6, 27), date(2026, 7, 2))
    assert encuestas._fechas_es('28 sep–05 oct 2026') == (date(2026, 9, 28), date(2026, 10, 5))


def test_excel_solo_encuestas_generales():
    """Se excluyen el promedio, las preguntas de primaria, los careos hipotéticos y la versión RV repetida."""
    from nv_pronostico.config import RAIZ
    b = encuestas.cargar_base(RAIZ / 'data' / 'encuestas_verificadas_nv.csv')
    assert len(b) == 12 and not b.pollster.str.upper().str.contains('PROME|PRIMARIA| VS\\.|MISMA').any()
    assert b.iloc[0].pollster == 'Noble Predictive Insights' and b.iloc[0].D == 40 and b.iloc[0].R == 42


def test_encuestas_en_vivo_sin_duplicados(cfg, red_simulada):
    r = encuestas.obtener_encuestas(cfg)
    p = r['encuestas']
    assert r['estados']['wikipedia'] == 'en_vivo' and r['estados']['270towin'] == 'en_vivo'
    assert not p.duplicated(['pollster_key', 'fin']).any()
    assert len(p) == 8 and (p.fin > '2026-06-09').all()
    npi = p[p.pollster_key == 'noblepredictiv'].iloc[0]
    assert npi.D == 40 and npi.R == 42 and npi.otros == 10        # versión LV; Danielle Ford (I) cuenta como tercero
    assert 'wedgewoodpolls' in set(p.pollster_key)                 # solo está en tu Excel


def test_columna_de_aaron_ford_no_la_de_danielle(cfg, red_simulada):
    cfg.rutas['encuestas_base'] = ''
    p = encuestas.obtener_encuestas(cfg)['encuestas']
    assert set(p.origen) <= {'wikipedia', '270towin'} and len(p) >= 6
    assert (p.D >= 35).all()                                       # Danielle Ford ronda el 7 %


def test_fuente_caida_usa_cache(cfg, red_simulada):
    encuestas.obtener_encuestas(cfg)
    red_simulada.caidas.add('wikipedia')
    r = encuestas.obtener_encuestas(cfg)
    assert r['estados']['wikipedia'].startswith('cache') and len(r['encuestas']) == 8


# ----------------------------------------------------------------------------------- mercados
def test_kalshi_y_polymarket_en_vivo(cfg, red_simulada):
    mk = mercados.obtener_mercados(cfg)
    k, p = mk['kalshi'], mk['polymarket']
    assert k['estado'] == p['estado'] == 'en_vivo' and k['usable'] and p['usable']
    assert k['p_d'] == pytest.approx(0.665) and k['p_r'] == pytest.approx(0.335)
    assert p['p_D'] == pytest.approx(0.665)
    rg = mk['rangos']
    assert rg['estado'] == 'en_vivo' and len(rg['tabla']) == 10
    assert rg['margen_media'] == pytest.approx(0.915, abs=0.01) and rg['P_D'] == pytest.approx(0.530, abs=0.002)


def test_mercado_caido_queda_fuera(cfg, red_simulada):
    red_simulada.caidas.add('kalshi')
    mk = mercados.obtener_mercados(cfg)
    assert not mk['kalshi']['usable'] and mk['n_usables'] == 1 and mk['promedio_D'] == pytest.approx(mk['polymarket']['p_D'])


# ----------------------------------------------------------------------------------- civicAPI
def test_civicapi_en_vivo_y_cache(cfg, red_simulada):
    a = obtener_anticipado(cfg)
    assert a['estado'] == 'en_vivo' and a['emitidos'] == a['por_correo'] + a['en_persona'] == 230_976
    assert a['pct_NPA'] == 0 and abs(a['pct_D'] + a['pct_R'] + a['pct_Otros'] - 100) < 1e-9   # NV: no partidistas en «Otros»
    assert a['margen_DR_correo_pp'] > 0 > a['margen_DR_persona_pp']
    assert a['condado_principal'] == 'Clark' and len(a['condados']) == 17
    red_simulada.caidas.add('civicapi')
    assert obtener_anticipado(cfg)['estado'].startswith('cache')


def test_civicapi_sin_partidos_es_error():
    vacio = {'snapshot_date': '2026-10-22', 'regions': {'Statewide': {'Unspecified': {'votes': 10}}}}
    with pytest.raises(ValueError):
        resumir({'returned': vacio, 'inperson': vacio, 'requested': vacio})


# ----------------------------------------------------------------------------------- pipeline
def test_corrida_completa_en_vivo(cfg, red_simulada):
    r = ejecutar(cfg)
    assert r['degradadas'] == []
    f = r['modelo']['final']
    assert abs(f['pct_D'] + f['pct_R'] + f['pct_terceros'] - 100) < 1e-6
    assert f['ventana']['ampliada'] and f['k'] == 2 and f['peso_mercados_aplicado'] == 0.30
    lo, hi = sorted([f['P_D_encuestas'], r['mercados']['promedio_D']])
    assert lo - 1e-9 <= f['P_D'] <= hi + 1e-9
    for a in ('pronostico_gobernador.csv', 'escenarios_gobernador.csv', 'encuestas_gobernador.csv', 'resumen.txt', 'reporte.json'):
        assert (cfg.dir_salidas / 'ultimo' / a).exists(), a


def test_cifras_del_22_oct(cfg, red_simulada):
    """Mismas cifras que el notebook (200 000 simulaciones, semilla fija)."""
    cfg.modelo['n_simulaciones'] = 200_000
    r = ejecutar(cfg, escribir_salidas=False)
    f, par = r['modelo']['final'], r['calibracion']
    assert f['margen_encuestas'] == pytest.approx(-2.25, abs=0.01)
    assert par['sesgo_contraido'] == pytest.approx(0.563, abs=0.002)   # 0.583 antes de quitar Axis Research (ME-02) del histórico 2024
    assert f['P_D_encuestas'] == pytest.approx(0.318, abs=0.003) and f['P_D'] == pytest.approx(0.419, abs=0.003)
    assert f['margen'] == pytest.approx(-1.22, abs=0.02)


def test_probabilidad_coherente_y_2x2(cfg, red_simulada):
    r = ejecutar(cfg, escribir_salidas=False)['modelo']
    f, sim, e = r['final'], r['sim'], r['escenarios'].set_index('escenario')
    assert f['P_D'] == pytest.approx(float((sim.M > 0).mean()), abs=1e-12)
    assert f['desplazamiento_mercados_pp'] > 0                     # mercados más favorables a Ford que las encuestas
    sin_cm = e.loc['Sin sesgo estatal, con mercados (mismo ajuste que el final)']
    assert e.loc['Sin sesgo estatal, sin mercados', 'P_D'] < sin_cm['P_D']
    assert f['P_D'] < sin_cm['P_D']                                # el sesgo de NV es pro-D: quitarlo ayuda a Ford


def test_reporte_json_estricto(cfg, red_simulada):
    ejecutar(cfg)
    txt = (cfg.dir_salidas / 'ultimo' / 'reporte.json').read_text(encoding='utf-8')
    rep = json.loads(txt, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    u = rep['ultima_encuesta']
    assert u['fin'] == '2026-10-13' and u['dias_antes_eleccion'] == 21
    assert any('encuesta más reciente' in a for a in rep['avisos'])


def test_sin_mercados_el_final_es_solo_encuestas(cfg, red_simulada):
    red_simulada.caidas.update({'kalshi', 'polymarket'})
    f = ejecutar(cfg, escribir_salidas=False)['modelo']['final']
    assert f['peso_mercados_aplicado'] == 0 and f['P_D'] == f['P_D_encuestas']


def test_offline_usa_caches_y_estricto_da_codigo_2(cfg, red_simulada, monkeypatch):
    ejecutar(cfg)
    cfg.offline = True
    r = ejecutar(cfg)
    assert {'wikipedia', '270towin', 'kalshi', 'polymarket', 'civicapi'} <= set(r['degradadas'])
    monkeypatch.setattr(cli, 'cargar_config', lambda *a, **k: cfg)
    assert cli.main(['correr', '--offline', '--estricto', '--sin-graficas']) == 2


def test_historial_registra_version(cfg, red_simulada):
    from nv_pronostico import __version__
    ejecutar(cfg)
    h = pd.read_csv(cfg.dir_salidas / 'historial_pronosticos.csv')
    assert h.version_modelo.iloc[-1] == __version__.split()[0]


def test_excel_verificado_contiene_al_csv_publicado():
    from nv_pronostico.config import RAIZ, cargar_config
    ruta = cargar_config().ruta_encuestas_base
    if ruta is None or ruta.suffix.lower() != '.xlsx' or not ruta.exists():
        pytest.skip('la configuración no apunta a un Excel local')
    clave = lambda d: set(zip(d.pollster, pd.to_datetime(d.fin).dt.date, d.D.astype(float), d.R.astype(float)))
    assert clave(encuestas.cargar_base(RAIZ / 'data' / 'encuestas_verificadas_nv.csv')) <= clave(encuestas.cargar_base(ruta))


# ----------------------------------------------------------------------------------- revisión del 22-oct (v1.1.0)
def test_influencia_de_cada_encuesta(cfg, red_simulada):
    """Quitar la encuesta interna (GSG, ~70 % del peso) reconstruye la ventana con NPI y Emerson; no es el escenario base."""
    r = ejecutar(cfg, escribir_salidas=False)['modelo']
    e, f = r['escenarios'], r['final']
    sin_gsg = e[e.escenario.str.startswith('Sin Global Strategy Group')].iloc[0]
    assert '(pesa 70%)' in sin_gsg.escenario and 'Emerson College' in sin_gsg.escenario
    assert sin_gsg.margen > e.iloc[1].margen                       # sin la interna, el promedio es MÁS favorable a Ford
    sin_part = e[e.escenario.str.startswith('Sin encuestas de patrocinio partidista')].iloc[0]
    assert np.isfinite(sin_part.P_D_con_mercados) and 'Emerson College' in sin_part.escenario and f['k'] == 2


def test_sesgo_sin_contiendas_de_una_encuestadora(cfg, red_simulada):
    par = ejecutar(cfg, escribir_salidas=False)['calibracion']
    assert 0 < par['sesgo_contraido_k2'] < par['sesgo_contraido']       # sin NV 2014 el sesgo casi desaparece
    assert par['sesgo_contraido_k2'] == pytest.approx(0.108, abs=0.01)


def test_escenarios_de_terceros_no_mueven_el_margen(cfg, red_simulada):
    r = ejecutar(cfg, escribir_salidas=False)['modelo']
    e = r['escenarios'].set_index('escenario')
    base = e.iloc[1]
    ter = e[e.index.str.startswith('Terceros:')]
    assert len(ter) == 2 and (ter.pct_terceros < base.pct_terceros).all()
    assert np.allclose(ter.margen, base.margen, atol=0.1) and (ter.pct_D > base.pct_D).all() and (ter.pct_R > base.pct_R).all()


def test_peso_de_mercados_monotono(cfg, red_simulada):
    e = ejecutar(cfg, escribir_salidas=False)['modelo']['escenarios'].set_index('escenario')
    p15, p50 = e.loc['Peso de mercados 0.15 (base 0.30)', 'P_D'], e.loc['Peso de mercados 0.50 (base 0.30)', 'P_D']
    assert e.iloc[1].P_D < p15 < e.iloc[0].P_D < p50 < 0.665                # encuestas < 0.15 < final (0.30) < 0.50 < mercados
