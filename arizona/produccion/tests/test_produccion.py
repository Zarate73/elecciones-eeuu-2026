"""Pruebas sin red de la producción de Arizona (fixtures reales del 21-oct-2026)."""
import json
from datetime import date

import numpy as np
import pandas as pd
import pytest

from az_pronostico import cli, encuestas, mercados, modelo
from az_pronostico.anticipado import obtener_anticipado, resumir
from az_pronostico.pipeline import ejecutar

FIX = __import__('pathlib').Path(__file__).parent / 'fixtures'


# ----------------------------------------------------------------------------------- encuestas
def test_fechas_excel():
    assert encuestas._fechas_es('30 sep–05 oct 2026') == (date(2026, 9, 30), date(2026, 10, 5))
    assert encuestas._fechas_es('01–09 sep 2026') == (date(2026, 9, 1), date(2026, 9, 9))
    assert encuestas._fechas_es('18 ago–04 sep 2026') == (date(2026, 8, 18), date(2026, 9, 4))


def test_encuestas_en_vivo_sin_duplicados_ni_falsos_duplicados(cfg, red_simulada):
    r = encuestas.obtener_encuestas(cfg)
    p = r['encuestas']
    assert r['estados']['wikipedia'] == 'en_vivo' and r['estados']['270towin'] == 'en_vivo'
    assert r['estados']['base_verificada'].startswith('archivo')
    assert not p.duplicated(['pollster_key', 'fin']).any()
    assert {'gqr', 'grayhouse'} <= set(p.pollster_key)          # 49/45 con n=600 en ambas: NO son la misma
    assert (p.pollster_key == 'grayhouse').sum() == 2
    assert (p.pollster_key == 'fabrizioward').sum() == 1 and (p.pollster_key == 'arizonastateun').sum() == 1
    assert len(p) == 15 and (p.fin > '2026-07-21').all()


def test_sin_base_verificada_bastan_las_fuentes_web(cfg, red_simulada):
    cfg.rutas['encuestas_base'] = ''
    p = encuestas.obtener_encuestas(cfg)['encuestas']
    assert len(p) >= 12 and set(p.origen) <= {'wikipedia', '270towin'}


def test_fuente_caida_usa_cache(cfg, red_simulada):
    encuestas.obtener_encuestas(cfg)                            # deja caché
    red_simulada.caidas.add('wikipedia')
    r = encuestas.obtener_encuestas(cfg)
    assert r['estados']['wikipedia'].startswith('cache') and len(r['encuestas']) == 15


# ----------------------------------------------------------------------------------- mercados
def test_kalshi_y_polymarket_en_vivo(cfg, red_simulada):
    mk = mercados.obtener_mercados(cfg)
    k, p = mk['kalshi'], mk['polymarket']
    assert k['estado'] == p['estado'] == 'en_vivo' and k['usable'] and p['usable']
    assert k['p_d'] == pytest.approx((0.908 + 0.913) / 2) and k['p_r'] == pytest.approx((0.088 + 0.095) / 2)
    assert p['p_d'] == pytest.approx(0.935) and 0.88 < k['p_D'] < 0.95
    assert mk['promedio_D'] == pytest.approx((k['p_D'] + p['p_D']) / 2)
    rg = mk['rangos']
    assert rg['estado'] == 'en_vivo' and len(rg['tabla']) == 10
    assert rg['margen_media'] == pytest.approx(8.98, abs=0.05) and rg['P_D'] == pytest.approx(0.925, abs=0.005)


def test_rangos_polymarket_signo_y_extremos():
    ev = json.loads((FIX / 'polymarket_arizona-governor-margin-of-victory-2026.json').read_text())[0]
    t = mercados.rangos_poly(ev)
    assert t.desde.min() == -30 and t.hasta.max() == 30
    assert ((t.desde == -6) & (t.hasta == -3)).sum() == 1 and ((t.desde == 15) & (t.hasta == 18)).sum() == 1


def test_mercado_caido_queda_fuera_y_cache_vieja_no_se_usa(cfg, red_simulada):
    red_simulada.caidas.add('kalshi')
    mk = mercados.obtener_mercados(cfg)
    assert not mk['kalshi']['usable'] and mk['n_usables'] == 1
    assert mk['promedio_D'] == pytest.approx(mk['polymarket']['p_D'])
    # caché de hace 5 días: se informa pero no entra a la mezcla
    pd.DataFrame([{'consulta': '2026-10-16T08:00:00', 'fecha': '2026-10-16', 'p_d': 0.8, 'p_r': 0.2}]) \
        .to_csv(cfg.dir_cache / 'mercado_kalshi.csv', index=False)
    mk = mercados.obtener_mercados(cfg)
    assert mk['kalshi']['estado'].startswith('cache') and not mk['kalshi']['usable'] and mk['n_usables'] == 1


# ----------------------------------------------------------------------------------- civicAPI
def test_civicapi_en_vivo_y_cache(cfg, red_simulada):
    a = obtener_anticipado(cfg)
    assert a['estado'] == 'en_vivo' and a['fecha'] == '2026-10-21' and a['devueltas'] == 642253
    assert abs(a['pct_dev_D'] + a['pct_dev_R'] + a['pct_dev_otros'] - 100) < 1e-9
    assert a['condados'].iloc[0].condado == 'Maricopa' and a['condados'].devueltas.sum() == a['devueltas']
    assert (cfg.dir_salidas / 'civicapi_historial_az.csv').exists()
    red_simulada.caidas.add('civicapi')
    b = obtener_anticipado(cfg)
    assert b['estado'].startswith('cache') and b['devueltas'] == a['devueltas']


def test_civicapi_sin_partidos_es_error():
    vacio = {'snapshot_date': '2026-10-21', 'regions': {'Statewide': {'Unspecified': {'votes': 10}}}}
    with pytest.raises(ValueError):
        resumir({'returned': vacio, 'requested': vacio})


# ----------------------------------------------------------------------------------- pipeline
def test_corrida_completa_en_vivo(cfg, red_simulada):
    r = ejecutar(cfg)
    assert r['degradadas'] == [] and all(v.startswith(('en_vivo', 'archivo')) for v in r['estados_fuentes'].values())
    f = r['modelo']['final']
    assert abs(f['pct_D'] + f['pct_R'] + f['pct_terceros'] - 100) < 1e-6
    assert 6.5 < f['margen'] < 9.5 and 0.85 < f['P_D'] < 0.99 and 0 < f['P_recuento'] < 0.1
    assert f['ventana']['ampliada'] and f['k'] == 4 and f['peso_mercados_aplicado'] == 0.30
    lo, hi = sorted([f['P_D_encuestas'], r['mercados']['promedio_D']])
    assert lo - 1e-9 <= f['P_D'] <= hi + 1e-9
    for a in ('pronostico_gobernador.csv', 'escenarios_gobernador.csv', 'encuestas_gobernador.csv',
              'encuestas_ventana_pesos.csv', 'voto_anticipado_condados.csv', 'polymarket_rangos_margen.csv',
              'resumen.txt', 'reporte.json'):
        assert (cfg.dir_salidas / 'ultimo' / a).exists(), a
    rep = json.loads((cfg.dir_salidas / 'ultimo' / 'reporte.json').read_text(encoding='utf-8'))
    assert rep['gobernador']['P_D'] == pytest.approx(f['P_D'])
    assert len(pd.read_csv(cfg.dir_salidas / 'historial_pronosticos.csv')) == 1


def test_igual_al_modelo_del_notebook(cfg, red_simulada):
    """Mismas encuestas y semilla que ARIZONA_2026_MODELO_FINAL.ipynb (21-oct): promedio +7.854, simulado +7.835."""
    cfg.modelo['n_simulaciones'] = 200_000
    f = ejecutar(cfg, escribir_salidas=False)['modelo']['final']
    assert f['margen_encuestas'] == pytest.approx(7.854, abs=0.001)
    assert f['margen'] == pytest.approx(7.835, abs=0.001) and f['pct_D'] == pytest.approx(51.878, abs=0.001)
    assert f['P_D_encuestas'] == pytest.approx(0.940715, abs=1e-6)


def test_escenario_partidista_no_toca_el_final(cfg, red_simulada):
    r = ejecutar(cfg, escribir_salidas=False)['modelo']
    e = r['escenarios'].set_index('escenario')
    fila = [i for i in e.index if i.startswith('Ajuste partidista')]
    assert len(fila) == 1 and e.loc[fila[0], 'margen'] > r['mu']
    assert e.iloc[0]['margen'] == r['final']['margen']
    assert modelo.lado_partidista('Fabrizio Ward (R)/ Impact Research (D)') is None


def test_sin_mercados_el_final_es_solo_encuestas(cfg, red_simulada):
    red_simulada.caidas.update({'kalshi', 'polymarket'})
    r = ejecutar(cfg, escribir_salidas=False)
    f = r['modelo']['final']
    assert f['peso_mercados_aplicado'] == 0 and f['P_D'] == f['P_D_encuestas']
    assert {'kalshi', 'polymarket', 'polymarket_rangos'} <= set(r['degradadas'])


def test_offline_usa_caches_y_estricto_da_codigo_2(cfg, red_simulada, monkeypatch):
    ejecutar(cfg)                                              # deja cachés
    cfg.offline = True
    r = ejecutar(cfg)
    assert set(r['degradadas']) >= {'wikipedia', '270towin', 'kalshi', 'polymarket', 'civicapi', 'historico_538'}
    assert r['modelo']['final']['peso_mercados_aplicado'] == 0.30          # caché del mismo día: usable
    monkeypatch.setattr(cli, 'cargar_config', lambda *a, **k: cfg)
    assert cli.main(['correr', '--offline', '--estricto', '--sin-graficas']) == 2
    assert cli.main(['correr', '--offline', '--sin-graficas']) == 0


def test_excel_verificado_contiene_al_csv_publicado():
    """En la copia local la base es tu Excel: debe contener todas las encuestas del CSV publicado (puede tener más)."""
    from az_pronostico.config import RAIZ, cargar_config
    ruta = cargar_config().ruta_encuestas_base
    if ruta is None or ruta.suffix.lower() != '.xlsx' or not ruta.exists():
        pytest.skip('la configuración no apunta a un Excel local')
    clave = lambda d: set(zip(d.pollster, pd.to_datetime(d.fin).dt.date, d.D.astype(float), d.R.astype(float)))
    assert clave(encuestas.cargar_base(RAIZ / 'data' / 'encuestas_verificadas_az.csv')) <= clave(encuestas.cargar_base(ruta))
