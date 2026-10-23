"""Pruebas sin red del modelo de Pennsylvania (fixtures reales del 23-oct-2026)."""
import json
from datetime import date

import numpy as np
import pandas as pd
import pytest

from pa_pronostico import cli, encuestas, mercados
from pa_pronostico.anticipado import obtener_anticipado, resumir
from pa_pronostico.pipeline import ejecutar

FIX = __import__('pathlib').Path(__file__).parent / 'fixtures'


# ----------------------------------------------------------------------------------- encuestas
def test_fechas_excel():
    assert encuestas._fechas_es('01–05 oct 2026') == (date(2026, 10, 1), date(2026, 10, 5))
    assert encuestas._fechas_es('28 sep–01 oct 2026') == (date(2026, 9, 28), date(2026, 10, 1))


def test_excel_solo_encuestas_generales():
    from pa_pronostico.config import RAIZ
    b = encuestas.cargar_base(RAIZ / 'data' / 'encuestas_verificadas_pa.csv')
    assert len(b) == 20 and not b.pollster.str.upper().str.contains('PROME').any()
    assert b.iloc[0].pollster == 'Quinnipiac University' and b.iloc[0].D == 59 and b.iloc[0].R == 34


def test_encuestas_en_vivo_sin_duplicados_y_alias(cfg, red_simulada):
    r = encuestas.obtener_encuestas(cfg)
    p = r['encuestas']
    assert r['estados']['wikipedia'] == 'en_vivo' and r['estados']['270towin'] == 'en_vivo'
    assert not p.duplicated(['pollster_key', 'fin']).any()
    assert len(p) == 18 and (p.fin > '2026-05-19').all()
    # PennLive = Bravo Group = «Bravo Group — PennLive»; NYT/Inquirer/Siena = Siena College = «New York Times / Siena»
    assert not p.pollster_key.isin(['pennlive', 'bravogrouppenn', 'thenewyorktime', 'newyorktimes']).any()
    assert (p.pollster_key == 'sienacollege').sum() == 2 and (p.pollster_key == 'bravogroup').sum() == 6


def test_version_lv_de_otra_fuente_reemplaza_a_la_rv(cfg, red_simulada):
    """Franklin & Marshall (7–18 oct): Wikipedia trae RV 52/30 y 270toWin la versión LV 59/36 → se usa la LV."""
    p = encuestas.obtener_encuestas(cfg)['encuestas']
    fm = p[(p.pollster_key == 'franklinmarsha') & (p.fin == '2026-10-18')].iloc[0]
    assert fm['pop'] == 'LV' and fm.D == 59 and fm.R == 36 and 'LV de 270towin' in fm.nota_version


def test_fuente_caida_usa_cache(cfg, red_simulada):
    encuestas.obtener_encuestas(cfg)
    red_simulada.caidas.add('wikipedia')
    r = encuestas.obtener_encuestas(cfg)
    assert r['estados']['wikipedia'].startswith('cache') and len(r['encuestas']) == 18


# ----------------------------------------------------------------------------------- mercados
def test_kalshi_y_polymarket_en_vivo(cfg, red_simulada):
    mk = mercados.obtener_mercados(cfg)
    k, p = mk['kalshi'], mk['polymarket']
    assert k['estado'] == p['estado'] == 'en_vivo' and k['usable'] and p['usable']
    assert k['p_d'] == pytest.approx(0.973) and p['p_d'] == pytest.approx(0.9765)
    rg = mk['rangos']
    assert len(rg['tabla']) == 7 and rg['tabla'].hasta.max() == 40      # «30 % o más» → 30–40, no 30–30
    assert rg['margen_media'] == pytest.approx(24.33, abs=0.05)


# ----------------------------------------------------------------------------------- civicAPI
def test_civicapi_solo_correo(cfg, red_simulada):
    """Pennsylvania no tiene voto anticipado en persona: civicAPI responde 404 en «inperson» y no es error."""
    a = obtener_anticipado(cfg)
    assert a['estado'] == 'en_vivo' and not a['tiene_en_persona']
    assert a['emitidos'] == a['por_correo'] == 720_664 and a['en_persona'] == 0
    assert a['condado_principal'] == 'Philadelphia' and len(a['condados']) == 67
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
    assert f['k'] == 2 and not f['ventana']['ampliada'] and f['peso_mercados_aplicado'] == 0.30
    lo, hi = sorted([f['P_D_encuestas'], r['mercados']['promedio_D']])
    assert lo - 1e-9 <= f['P_D'] <= hi + 1e-9
    assert 'sin voto anticipado en persona' in r['resumen_texto']


def test_cifras_del_23_oct(cfg, red_simulada):
    """Mismas cifras que el notebook (200 000 simulaciones, semilla fija)."""
    cfg.modelo['n_simulaciones'] = 200_000
    r = ejecutar(cfg, escribir_salidas=False)
    f, par = r['modelo']['final'], r['calibracion']
    assert f['margen_encuestas'] == pytest.approx(22.30, abs=0.01)
    assert par['sesgo_contraido'] == pytest.approx(1.049, abs=0.002)
    assert f['margen'] == pytest.approx(18.80, abs=0.03) and f['P_D'] == pytest.approx(0.997, abs=0.002)
    assert f['desplazamiento_mercados_pp'] == pytest.approx(-2.44, abs=0.05)   # mercados (97 %) por debajo del modelo


def test_escenarios_de_revision(cfg, red_simulada):
    e = ejecutar(cfg, escribir_salidas=False)['modelo']['escenarios']
    assert e.escenario.str.startswith('Sin Franklin & Marshall College').any()
    assert e.escenario.str.startswith('Sin ActiVote').any()
    assert e.escenario.str.startswith('Terceros: reducción').sum() == 2
    assert {'Peso de mercados 0.15 (base 0.30)', 'Peso de mercados 0.50 (base 0.30)'} <= set(e.escenario)


def test_reporte_json_estricto(cfg, red_simulada):
    ejecutar(cfg)
    txt = (cfg.dir_salidas / 'ultimo' / 'reporte.json').read_text(encoding='utf-8')
    rep = json.loads(txt, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    assert rep['ultima_encuesta']['fin'] == '2026-10-21'


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
    from pa_pronostico import __version__
    ejecutar(cfg)
    h = pd.read_csv(cfg.dir_salidas / 'historial_pronosticos.csv')
    assert h.version_modelo.iloc[-1] == __version__.split()[0]


def test_excel_verificado_contiene_al_csv_publicado():
    from pa_pronostico.config import RAIZ, cargar_config
    ruta = cargar_config().ruta_encuestas_base
    if ruta is None or ruta.suffix.lower() != '.xlsx' or not ruta.exists():
        pytest.skip('la configuración no apunta a un Excel local')
    clave = lambda d: set(zip(d.pollster, pd.to_datetime(d.fin).dt.date, d.D.astype(float), d.R.astype(float)))
    assert clave(encuestas.cargar_base(RAIZ / 'data' / 'encuestas_verificadas_pa.csv')) <= clave(encuestas.cargar_base(ruta))
