"""Pruebas sin red de la producción de Florida (fixtures reales del 22-oct-2026)."""
import json
from datetime import date

import numpy as np
import pandas as pd
import pytest

from fl_pronostico import cli, encuestas, mercados, modelo
from fl_pronostico.anticipado import obtener_anticipado, resumir
from fl_pronostico.pipeline import ejecutar

FIX = __import__('pathlib').Path(__file__).parent / 'fixtures'


# ----------------------------------------------------------------------------------- encuestas
def test_fechas_excel():
    assert encuestas._fechas_es('05–07 oct 2026') == (date(2026, 10, 5), date(2026, 10, 7))
    assert encuestas._fechas_es('28 sep–05 oct 2026') == (date(2026, 9, 28), date(2026, 10, 5))
    assert encuestas._fechas_es('15 mar–13 abr 2026') == (date(2026, 3, 15), date(2026, 4, 13))


def test_encuestas_en_vivo_sin_duplicados(cfg, red_simulada):
    r = encuestas.obtener_encuestas(cfg)
    p = r['encuestas']
    assert r['estados']['wikipedia'] == 'en_vivo' and r['estados']['270towin'] == 'en_vivo'
    assert r['estados']['base_verificada'].startswith('archivo')
    assert not p.duplicated(['pollster_key', 'fin']).any()
    assert len(p) == 16 and (p.fin > '2026-08-18').all()
    # Univision/YouGov (Wikipedia, 15-oct, 42/50) = «YouGov» de 270toWin (19-oct): una sola encuesta
    yg = p[p.pollster_key == 'yougov']
    assert ((yg.D == 42) & (yg.R == 50)).sum() == 1
    # Mason-Dixon del Excel («— NBC 6 / Telemundo») y de Wikipedia son una sola
    assert (p.pollster_key == 'masondixon').sum() == 1


def test_wikipedia_con_rowspan_mal_formado(cfg, red_simulada):
    """La página de FL trae atributos «rowspan="2;"»: sin normalizarlos se pierden encuestas."""
    cfg.rutas['encuestas_base'] = ''
    p = encuestas.obtener_encuestas(cfg)['encuestas']
    assert len(p) >= 14 and set(p.origen) <= {'wikipedia', '270towin'}
    assert {'activote', 'universityofno', 'coefficient'} <= set(p.pollster_key)


def test_fuente_caida_usa_cache(cfg, red_simulada):
    encuestas.obtener_encuestas(cfg)                            # deja caché
    red_simulada.caidas.add('wikipedia')
    r = encuestas.obtener_encuestas(cfg)
    assert r['estados']['wikipedia'].startswith('cache') and len(r['encuestas']) == 16


def test_excel_excluye_promedio():
    from fl_pronostico.config import RAIZ
    b = encuestas.cargar_base(RAIZ / 'data' / 'encuestas_verificadas_fl.csv')
    assert len(b) == 25 and not b.pollster.str.upper().str.contains('PROME').any()
    assert b.iloc[0].pollster == 'St. Pete Polls' and b.iloc[0].D == 44.6 and b.iloc[0].R == 44.7


# ----------------------------------------------------------------------------------- mercados
def test_kalshi_y_polymarket_en_vivo(cfg, red_simulada):
    mk = mercados.obtener_mercados(cfg)
    k, p = mk['kalshi'], mk['polymarket']
    assert k['estado'] == p['estado'] == 'en_vivo' and k['usable'] and p['usable']
    assert k['p_d'] == pytest.approx((0.22 + 0.23) / 2) and k['p_r'] == pytest.approx((0.78 + 0.79) / 2)
    assert p['p_d'] == pytest.approx(0.20) and p['p_D'] == pytest.approx(0.20)
    assert k['p_D'] == pytest.approx(0.225 / (0.225 + 0.785))
    assert mk['promedio_D'] == pytest.approx((k['p_D'] + p['p_D']) / 2)
    rg = mk['rangos']
    assert rg['estado'] == 'en_vivo' and len(rg['tabla']) == 10
    assert rg['margen_media'] == pytest.approx(-4.755, abs=0.01) and rg['P_D'] == pytest.approx(0.2128, abs=0.001)


def test_polymarket_ignora_opciones_genericas():
    ev = json.loads((FIX / 'polymarket_florida-governor-winner-2026.json').read_text())[0]
    assert any('Option A' in m['question'] for m in ev['markets'])
    d, r = mercados.ganador_poly(ev)
    assert d == pytest.approx(0.20) and r == pytest.approx(0.80)


def test_mercado_caido_queda_fuera_y_cache_vieja_no_se_usa(cfg, red_simulada):
    red_simulada.caidas.add('kalshi')
    mk = mercados.obtener_mercados(cfg)
    assert not mk['kalshi']['usable'] and mk['n_usables'] == 1
    assert mk['promedio_D'] == pytest.approx(mk['polymarket']['p_D'])
    pd.DataFrame([{'consulta': '2026-10-17T08:00:00', 'fecha': '2026-10-17', 'p_d': 0.3, 'p_r': 0.7}]) \
        .to_csv(cfg.dir_cache / 'mercado_kalshi.csv', index=False)
    mk = mercados.obtener_mercados(cfg)
    assert mk['kalshi']['estado'].startswith('cache') and not mk['kalshi']['usable'] and mk['n_usables'] == 1


# ----------------------------------------------------------------------------------- civicAPI
def test_civicapi_en_vivo_y_cache(cfg, red_simulada):
    a = obtener_anticipado(cfg)
    assert a['estado'] == 'en_vivo' and a['fecha'] == '2026-10-22'
    assert a['emitidos'] == a['por_correo'] + a['en_persona'] == 1_676_291
    assert abs(a['pct_D'] + a['pct_R'] + a['pct_NPA'] + a['pct_Otros'] - 100) < 1e-9
    assert a['margen_DR_correo_pp'] > 0 > a['margen_DR_persona_pp']      # D vota por correo, R en persona
    assert len(a['condados']) == 67 and a['condados'].emitidos.sum() == a['emitidos']
    assert (cfg.dir_salidas / 'civicapi_historial_fl.csv').exists()
    red_simulada.caidas.add('civicapi')
    b = obtener_anticipado(cfg)
    assert b['estado'].startswith('cache') and b['emitidos'] == a['emitidos']


def test_civicapi_sin_partidos_es_error():
    vacio = {'snapshot_date': '2026-10-22', 'regions': {'Statewide': {'Unspecified': {'votes': 10}}}}
    with pytest.raises(ValueError):
        resumir({'returned': vacio, 'inperson': vacio, 'requested': vacio})


# ----------------------------------------------------------------------------------- pipeline
def test_corrida_completa_en_vivo(cfg, red_simulada):
    r = ejecutar(cfg)
    assert r['degradadas'] == [] and all(v.startswith(('en_vivo', 'archivo')) for v in r['estados_fuentes'].values())
    f = r['modelo']['final']
    assert abs(f['pct_D'] + f['pct_R'] + f['pct_terceros'] - 100) < 1e-6
    assert -10 < f['margen'] < -6.5 and 0.02 < f['P_D'] < 0.10 and 0 < f['P_recuento'] < 0.05
    assert f['k'] == 4 and not f['ventana']['ampliada'] and f['peso_mercados_aplicado'] == 0.30
    lo, hi = sorted([f['P_D_encuestas'], r['mercados']['promedio_D']])
    assert lo - 1e-9 <= f['P_D'] <= hi + 1e-9
    for a in ('pronostico_gobernador.csv', 'escenarios_gobernador.csv', 'encuestas_gobernador.csv',
              'encuestas_ventana_pesos.csv', 'voto_anticipado_condados.csv', 'polymarket_rangos_margen.csv',
              'resumen.txt', 'reporte.json'):
        assert (cfg.dir_salidas / 'ultimo' / a).exists(), a
    rep = json.loads((cfg.dir_salidas / 'ultimo' / 'reporte.json').read_text(encoding='utf-8'))
    assert rep['gobernador']['P_D'] == pytest.approx(f['P_D'])
    assert len(pd.read_csv(cfg.dir_salidas / 'historial_pronosticos.csv')) == 1


def test_sesgo_estatal_de_florida(cfg, red_simulada):
    """Las encuestas de FL han sobreestimado al demócrata: el sesgo (contraído) corrige hacia Donalds."""
    r = ejecutar(cfg, escribir_salidas=False)
    par, f = r['calibracion'], r['modelo']['final']
    assert par['n_contiendas'] == 847 and any(e['race'] == '2024_Pres-G_FL' for e in par['errores_estado'])
    assert 3 < par['sesgo_contraido'] <= par['sesgo_bruto'] < 8 and par['contraccion'] > 0.6
    assert f['sesgo_estatal_aplicado'] == pytest.approx(par['sesgo_contraido'])
    assert r['modelo']['mu'] == pytest.approx(f['margen_encuestas'] - par['sesgo_contraido'])
    e = r['modelo']['escenarios'].set_index('escenario')
    assert e.loc['Sin sesgo estatal, sin mercados', 'P_D'] > f['P_D_encuestas']
    cfg.modelo['sesgo_estatal'] = False
    g = ejecutar(cfg, escribir_salidas=False)['modelo']
    assert g['mu'] == g['final']['margen_encuestas'] and g['final']['P_D'] > f['P_D']


def test_igual_al_modelo_del_notebook(cfg, red_simulada):
    """Mismas encuestas y semilla que FLORIDA_2026_MODELO_FINAL.ipynb (22-oct): promedio −5.25, final −8.31, P 5.0 %.
    Desde la versión 1.1.0 los terceros distinguen «no reportado» de 0 % (2.0 → 2.1 %); margen y probabilidad no cambian.
    24-oct: se quitó del histórico 2024 la encuesta Axis Research (distrito 2 de Maine, no estatal): recalibración nacional;
    final −8.311 → −8.266 y P 5.00 → 5.09 %."""
    cfg.modelo['n_simulaciones'] = 200_000
    r = ejecutar(cfg, escribir_salidas=False)['modelo']
    f, solo = r['final'], r['escenarios'].iloc[1]
    assert f['margen_encuestas'] == pytest.approx(-5.253, abs=0.001)
    assert 'solo encuestas' in solo['escenario'] and solo['margen'] == pytest.approx(-10.024, abs=0.001)
    assert f['margen'] == pytest.approx(-8.266, abs=0.001) and f['P_D'] == pytest.approx(0.0509, abs=0.0005)
    assert f['pct_R'] == pytest.approx(53.1, abs=0.05) and f['pct_D'] == pytest.approx(44.8, abs=0.05)


def test_probabilidad_coherente_con_la_distribucion(cfg, red_simulada):
    r = ejecutar(cfg, escribir_salidas=False)['modelo']
    f, sim = r['final'], r['sim']
    assert f['P_D'] == pytest.approx(float((sim.M > 0).mean()), abs=1e-12)
    assert f['P_D'] == pytest.approx(f['P_D_mezcla_objetivo'], abs=2 / len(sim))
    assert f['P_recuento'] == pytest.approx(float((sim.M.abs() <= 0.5).mean()), abs=1e-12)
    assert np.allclose(sim.D + sim.R + sim['T'], 100)
    assert f['desplazamiento_mercados_pp'] > 0                       # mercados más favorables a Jolly que el modelo
    cfg.modelo['peso_mercados'] = 0.0
    g = ejecutar(cfg, escribir_salidas=False)['modelo']
    assert g['final']['desplazamiento_mercados_pp'] == 0 and g['final']['margen'] == g['escenarios'].iloc[1]['margen']


def test_reporte_es_json_estricto_y_trae_antiguedad(cfg, red_simulada):
    ejecutar(cfg)
    txt = (cfg.dir_salidas / 'ultimo' / 'reporte.json').read_text(encoding='utf-8')

    def prohibido(c):
        raise ValueError(f'constante no estándar en JSON: {c}')
    rep = json.loads(txt, parse_constant=prohibido)
    u = rep['ultima_encuesta']
    assert u['fin'] == '2026-10-20' and u['dias_desde_fin'] == 2 and u['dias_antes_eleccion'] == 14
    assert rep['anticipado']['emitidos'] == 1_676_291 and 'condados' not in rep['anticipado']
    t = (cfg.dir_salidas / 'ultimo' / 'resumen.txt').read_text(encoding='utf-8')
    assert 'Sesgo estatal' in t and 'VOTO YA EMITIDO' in t


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


def test_partidista_bipartidista():
    assert modelo.lado_partidista('co/efficient (R)') == 'R'
    assert modelo.lado_partidista('Fabrizio Ward (R)/ Impact Research (D)') is None


def test_excel_verificado_contiene_al_csv_publicado():
    """En la copia local la base es tu Excel: debe contener todas las encuestas del CSV publicado (puede tener más)."""
    from fl_pronostico.config import RAIZ, cargar_config
    ruta = cargar_config().ruta_encuestas_base
    if ruta is None or ruta.suffix.lower() != '.xlsx' or not ruta.exists():
        pytest.skip('la configuración no apunta a un Excel local')
    clave = lambda d: set(zip(d.pollster, pd.to_datetime(d.fin).dt.date, d.D.astype(float), d.R.astype(float)))
    assert clave(encuestas.cargar_base(RAIZ / 'data' / 'encuestas_verificadas_fl.csv')) <= clave(encuestas.cargar_base(ruta))


# ----------------------------------------------------------------------------------- revisión del 22-oct (v1.1.0)
def test_terceros_no_reportado_no_es_cero(cfg, red_simulada):
    """«—» en Wikipedia = la encuesta no pregunta/reporta terceros: NaN, no 0 %."""
    p = encuestas.obtener_encuestas(cfg)['encuestas'].set_index('pollster_key')
    assert np.isnan(p.loc['activote', 'otros']) and np.isnan(p.loc['coefficient', 'otros'])
    assert p.loc['stetsonunivers'].otros.max() == 5.0                     # sí reporta terceros
    r = ejecutar(cfg, escribir_salidas=False)
    f, par = r['modelo']['final'], r['calibracion']
    assert f['terceros_reportados_encuestas'] is None                      # ninguna de las 4 de la ventana los reporta
    assert f['terceros_media'] == pytest.approx(par['terceros_sin_reporte'])
    assert par['n_con_reporte'] + par['n_sin_reporte'] == par['n_contiendas'] and par['n_sin_reporte'] > 300


def test_escenarios_cruzados_sesgo_por_mercados(cfg, red_simulada):
    """2 × 2: el efecto del sesgo se compara con el mismo tratamiento de mercados."""
    r = ejecutar(cfg, escribir_salidas=False)['modelo']
    e, f = r['escenarios'].set_index('escenario'), r['final']
    con_sm = e.loc['Con sesgo estatal, sin mercados (solo encuestas)']
    sin_sm = e.loc['Sin sesgo estatal, sin mercados']
    sin_cm = e.loc['Sin sesgo estatal, con mercados (mismo ajuste que el final)']
    assert con_sm['P_D_con_mercados'] == pytest.approx(f['P_D'], abs=1e-4)          # objetivo vs fracción simulada
    assert sin_sm['P_D_con_mercados'] == pytest.approx(sin_cm['P_D'], abs=1e-4)
    assert con_sm['P_D'] < f['P_D'] < sin_cm['P_D'] and sin_sm['P_D'] < sin_cm['P_D']
    assert sin_cm['P_D'] == pytest.approx(0.162, abs=0.006)   # revisión externa: 16.2 % (200 000 sim.; aquí 60 000)
    simulados = e[e.pct_D.notna()]
    assert simulados.P_D_con_mercados.notna().all()


def test_sensibilidad_contraccion_y_deriva(cfg, red_simulada):
    r = ejecutar(cfg, escribir_salidas=False)['modelo']
    e = r['escenarios'].set_index('escenario')
    fila = lambda pref: e.loc[[i for i in e.index if i.startswith(pref)][0]]
    mitad, crudo = fila('Sesgo estatal a la mitad'), fila('Sesgo estatal sin contraer')
    con, sin = fila('Con sesgo estatal, sin mercados'), fila('Sin sesgo estatal, sin mercados')
    assert crudo['P_D'] <= con['P_D'] <= mitad['P_D'] <= sin['P_D']        # monótono en el tamaño del sesgo
    assert fila('Deriva al doble')['sd'] >= fila('Sin deriva')['sd']
    assert {'Efectos de casa con contracción k = 4 (base 8)', 'Efectos de casa con contracción k = 16 (base 8)'} <= set(e.index)


def test_historial_registra_version(cfg, red_simulada):
    from fl_pronostico import __version__
    ejecutar(cfg)
    h = pd.read_csv(cfg.dir_salidas / 'historial_pronosticos.csv')
    assert h.version_modelo.iloc[-1] == __version__.split()[0] == '1.1.0'
    rep = json.loads((cfg.dir_salidas / 'ultimo' / 'reporte.json').read_text(encoding='utf-8'))
    assert rep['version_modelo'] == __version__
