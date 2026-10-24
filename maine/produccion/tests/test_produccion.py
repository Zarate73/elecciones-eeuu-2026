"""Pruebas sin red del modelo de Maine (fixtures reales del 24-oct-2026, 04:06 UTC)."""
import json
from datetime import date

import numpy as np
import pandas as pd
import pytest

from me_pronostico import cli, encuestas, mercados
from me_pronostico.anticipado import obtener_anticipado, resumir
from me_pronostico.pipeline import ejecutar

FIX = __import__('pathlib').Path(__file__).parent / 'fixtures'


# ----------------------------------------------------------------------------------- encuestas
def test_fechas_excel():
    assert encuestas._fechas_es('01–05 oct 2026') == (date(2026, 10, 1), date(2026, 10, 5))
    assert encuestas._fechas_es('28 sep–01 oct 2026') == (date(2026, 9, 28), date(2026, 10, 1))


def test_base_verificada_csv():
    """CSV publicado = bloque 1 de la hoja «Histórico encuestas»: 14 encuestas generales, con Bennett como tercero."""
    from me_pronostico.config import RAIZ
    b = encuestas.cargar_base(RAIZ / 'data' / 'encuestas_verificadas_me.csv')
    assert len(b) == 14 and b.iloc[0].D == 50 and b.iloc[0].R == 36 and b.iloc[0].otros == 8
    cbs = b[b.pollster.str.startswith('CBS')].iloc[0]
    assert cbs.D + cbs.R == 100 and np.isnan(cbs.otros)                  # careo forzado: Bennett no preguntado ≠ 0


def test_encuestas_en_vivo_sin_duplicados_y_alias(cfg, red_simulada):
    r = encuestas.obtener_encuestas(cfg)
    p = r['encuestas']
    assert r['estados']['wikipedia'] == 'en_vivo' and r['estados']['270towin'] == 'en_vivo'
    assert not p.duplicated(['pollster_key', 'fin']).any()
    assert len(p) == 16 and (p.fin > '2026-06-09').all()
    # alias hacia la clave del histórico de FiveThirtyEight (conservan su efecto de casa)
    assert not p.pollster_key.isin(['foxnews', 'aarp', 'cnn', 'nyt', 'sienacollege', 'maristpoll', 'maristuniversi',
                                    'umasslowell', 'univofnewhamps', 'washpostschars']).any()
    assert (p.pollster_key == 'beaconresearch').sum() == 3 and (p.pollster_key == 'thenewyorktime').sum() == 2


def test_siena_version_con_bennett(cfg, red_simulada):
    """NYT/PPH/Siena publica la boleta completa (47–34–8) y un careo sin Bennett (53–39): se usa la boleta completa."""
    p = encuestas.obtener_encuestas(cfg)['encuestas']
    s = p[(p.pollster_key == 'thenewyorktime') & (p.fin == '2026-09-22')].iloc[0]
    assert s.D == 47 and s.R == 34 and s.otros == 8


def test_bipartidistas_no_son_partidistas(cfg, red_simulada):
    p = encuestas.obtener_encuestas(cfg)['encuestas']
    assert not p[p.pollster_key.isin(['beaconresearch', 'fabrizioleeass'])].partidista.any()
    assert p[p.pollster_key == 'co'].partidista.all()                   # co/efficient (R)


def test_fuente_caida_usa_cache(cfg, red_simulada):
    encuestas.obtener_encuestas(cfg)
    red_simulada.caidas.add('wikipedia')
    r = encuestas.obtener_encuestas(cfg)
    assert r['estados']['wikipedia'].startswith('cache') and len(r['encuestas']) == 16


# ----------------------------------------------------------------------------------- mercados
def test_kalshi_y_polymarket_en_vivo(cfg, red_simulada):
    """Kalshi tiene tres contratos (D, R y Bennett): la probabilidad del modelo es D / (D + R)."""
    mk = mercados.obtener_mercados(cfg)
    k, p = mk['kalshi'], mk['polymarket']
    assert k['estado'] == p['estado'] == 'en_vivo' and k['usable'] and p['usable']
    assert k['p_d'] == pytest.approx(0.954) and k['p_r'] == pytest.approx(0.043)
    assert p['p_d'] == pytest.approx(0.9545) and p['p_r'] == pytest.approx(0.0355)


def test_rangos_con_contrato_independiente(cfg, red_simulada):
    """Margen de Polymarket: 8 rangos D/R (partición completa) + «Will an Independent win» fuera del eje D−R,
    que cuenta en el denominador de P(D)."""
    rg = mercados.obtener_mercados(cfg)['rangos']
    t = rg['tabla']
    assert (t.contrato == 'independiente').sum() == 1 and rg['completo'] and rg['n_contratos'] == 9
    assert rg['suma_precios'] == pytest.approx(1.2235)
    assert rg['P_independiente'] == pytest.approx(0.035 / 1.2235)
    assert rg['P_D'] == pytest.approx((0.12 + 0.25 + 0.335 + 0.215 + 0.0985 + 0.094) / 1.2235)
    assert rg['margen_media'] == pytest.approx(12.34, abs=0.05) and rg['margen_cond_D'] == pytest.approx(13.63, abs=0.05)


def test_rangos_incompletos_no_dan_probabilidad():
    """Sin el contrato del lado perdedor no hay P(D) ni margen incondicional: solo E[M | D]."""
    t = pd.DataFrame({'desde': [0, 5, 10, 15, 20, 25, 30], 'hasta': [5, 10, 15, 20, 25, 30, np.inf],
                      'p': [.09, .0465, .1505, .26, .245, .115, .24], 'contrato': ['rango'] * 6 + ['abierto']})
    r = mercados.resumen_rangos(t)
    assert not r['completo'] and 'P_D' not in r and 'margen_media' not in r
    assert r['suma_precios'] == pytest.approx(1.147) and r['margen_cond_D'] == pytest.approx(20.99, abs=0.05)


# ----------------------------------------------------------------------------------- civicAPI
def test_civicapi_voto_ausente(cfg, red_simulada):
    """Maine: voto ausente por correo y en persona, por municipio."""
    a = obtener_anticipado(cfg)
    assert a['estado'] == 'en_vivo' and a['tiene_en_persona']
    assert a['emitidos'] == 179_532 and a['por_correo'] == 87_036 and a['en_persona'] == 92_496
    assert a['condado_principal'] == 'Portland' and len(a['condados']) > 400
    red_simulada.caidas.add('civicapi')
    assert obtener_anticipado(cfg)['estado'].startswith('cache')


def test_civicapi_sin_partidos_es_error():
    vacio = {'snapshot_date': '2026-10-23', 'regions': {'Statewide': {'Unspecified': {'votes': 10}}}}
    with pytest.raises(ValueError):
        resumir({'returned': vacio, 'requested': vacio})


# ----------------------------------------------------------------------------------- pipeline
def test_corrida_completa_en_vivo(cfg, red_simulada):
    r = ejecutar(cfg)
    assert r['degradadas'] == []
    f = r['modelo']['final']
    assert abs(f['pct_D'] + f['pct_R'] + f['pct_terceros'] - 100) < 1e-6
    assert f['k'] == 6 and f['ventana']['ampliada'] and f['peso_mercados_aplicado'] == 0.30
    assert f['terceros_regimen'] == 'reportado en encuestas'
    lo, hi = sorted([f['P_D_encuestas'], r['mercados']['promedio_D']])
    assert lo - 1e-9 <= f['P_D'] <= hi + 1e-9


def test_cifras_del_24_oct(cfg, red_simulada):
    """Mismas cifras que el notebook (200 000 simulaciones, semilla fija)."""
    cfg.modelo['n_simulaciones'] = 200_000
    r = ejecutar(cfg, escribir_salidas=False)
    f, par = r['modelo']['final'], r['calibracion']
    assert f['margen_encuestas'] == pytest.approx(MARGEN_ENC, abs=0.01)
    assert par['sesgo_contraido'] == pytest.approx(SESGO, abs=0.002)
    assert f['margen'] == pytest.approx(MARGEN, abs=0.03) and f['P_D'] == pytest.approx(P_D, abs=0.002)
    assert f['pct_terceros'] == pytest.approx(TERCEROS, abs=0.05)


def test_escenarios(cfg, red_simulada):
    e = ejecutar(cfg, escribir_salidas=False)['modelo']['escenarios']
    assert e.escenario.str.startswith('Sin Beacon Research').any()
    assert e.escenario.str.startswith('Terceros: reducción').sum() == 2
    assert {'Peso de mercados 0.15 (base 0.30)', 'Peso de mercados 0.50 (base 0.30)'} <= set(e.escenario)
    assert e.escenario.str.startswith('Polymarket por rangos').any()
    assert e.escenario.str.startswith('Sesgo estimado con todas las contiendas').any()    # regla k ≥ 2: la otra es escenario


def test_reporte_json_estricto(cfg, red_simulada):
    ejecutar(cfg)
    txt = (cfg.dir_salidas / 'ultimo' / 'reporte.json').read_text(encoding='utf-8')
    rep = json.loads(txt, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    assert rep['ultima_encuesta']['fin'] == '2026-10-20'
    assert rep['mercados']['rangos']['P_independiente'] > 0


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
    from me_pronostico import __version__
    ejecutar(cfg)
    h = pd.read_csv(cfg.dir_salidas / 'historial_pronosticos.csv')
    assert h.version_modelo.iloc[-1] == __version__.split()[0]


def test_excel_verificado_contiene_al_csv_publicado():
    from me_pronostico.config import RAIZ, cargar_config
    ruta = cargar_config().ruta_encuestas_base
    if ruta is None or ruta.suffix.lower() != '.xlsx' or not ruta.exists():
        pytest.skip('la configuración no apunta a un Excel local')
    clave = lambda d: set(zip(d.pollster, pd.to_datetime(d.fin).dt.date, d.D.astype(float), d.R.astype(float)))
    assert clave(encuestas.cargar_base(RAIZ / 'data' / 'encuestas_verificadas_me.csv')) <= clave(encuestas.cargar_base(ruta))


def test_n_imputado_marcado(cfg, red_simulada):
    """Sin n en ninguna fuente, se imputa 600 y queda marcado (en Maine todas las encuestas de la ventana traen n)."""
    p = encuestas.obtener_encuestas(cfg)['encuestas']
    assert not p[p.fin >= '2026-09-29'].n_imputado.any()
    assert set(p.n_fuente) <= {'reportado', 'imputado (600)'} or p.n_fuente.str.startswith('corregido').any()


# valores fijados con la corrida de referencia del 24-oct (ver notebook)
MARGEN_ENC, SESGO, MARGEN, P_D, TERCEROS = 10.30, 2.427, 8.05, 0.9535, 6.80   # sesgo regla k ≥ 2 (+2.43 pp pro-D)
