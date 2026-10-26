"""Pruebas sin red del modelo de Ohio (fixtures reales: captura del 26-oct 21:20 UTC, corte 26-oct)."""
import json
from datetime import date

import numpy as np
import pandas as pd
import pytest

from oh_pronostico import cli, encuestas, mercados
from oh_pronostico.anticipado import obtener_anticipado, resumir
from oh_pronostico.pipeline import ejecutar

FIX = __import__('pathlib').Path(__file__).parent / 'fixtures'


# ----------------------------------------------------------------------------------- encuestas
def test_fechas_excel():
    assert encuestas._fechas_es('01–05 oct 2026') == (date(2026, 10, 1), date(2026, 10, 5))
    assert encuestas._fechas_es('29 sep–05 oct 2026') == (date(2026, 9, 29), date(2026, 10, 5))


def test_base_verificada_csv():
    """CSV publicado = bloque 1 de la hoja «Histórico encuestas» de OHIO_GOBERNADOR-v1.xlsx: 27 encuestas generales."""
    from oh_pronostico.config import RAIZ
    b = encuestas.cargar_base(RAIZ / 'data' / 'encuestas_verificadas_oh.csv')
    assert len(b) == 27 and b.iloc[0].pollster == 'Public Policy Polling (D)' and (b.iloc[0].D, b.iloc[0].R) == (45, 44)
    bd = b[b.pollster == 'Big Data Poll (R)'].iloc[0]
    assert (bd.D, bd.R) == (46.8, 47.9)


def test_encuestas_en_vivo_sin_duplicados_y_alias(cfg, red_simulada):
    r = encuestas.obtener_encuestas(cfg)
    p = r['encuestas']
    assert r['estados']['wikipedia'] == 'en_vivo' and r['estados']['270towin'] == 'en_vivo'
    assert not p.duplicated(['pollster_key', 'inicio', 'fin']).any()
    assert len(p) == N_ENCUESTAS and (p.fin > '2025-11-22').all()
    # «Siena College» (270toWin) = NYT/Siena; BGSU/YouGov con tres nombres; CNN/SSRS = SSRS; Fox News = Beacon/Shaw
    assert (p.pollster_key == 'thenewyorktime').sum() == 2 and not (p.pollster_key == 'sienacollege').any()
    assert (p.pollster_key == 'bowlinggreenst').sum() == 3 and (p.pollster_key == 'beaconresearch').sum() == 3
    assert (p.pollster_key == 'ssrs').sum() == 1 and not p.pollster_key.isin(['cnn', 'foxnews', 'bowlinggreenun']).any()


def test_fecha_de_publicacion_no_es_otra_encuesta(cfg, red_simulada):
    """270toWin fecha a Marist el 20-oct (publicación; campo 15–18 oct): una sola encuesta, con su periodo de campo."""
    p = encuestas.obtener_encuestas(cfg)['encuestas']
    m = p[(p.pollster_key == 'maristcollege') & (p.fin >= '2026-10-01')]
    assert len(m) == 1 and m.iloc[0].fin == pd.Timestamp('2026-10-18') and '270towin' in m.iloc[0].tambien_en


def test_cifras_y_n_de_la_publicacion_original(cfg, red_simulada):
    """Marist LV 50–43 (Wikipedia: 51–43), n = 883; ActiVote 48.6–51.4 (Wikipedia y 270toWin: 49–51)."""
    p = encuestas.obtener_encuestas(cfg)['encuestas']
    m = p[(p.pollster_key == 'maristcollege') & (p.fin == '2026-10-18')].iloc[0]
    a = p[p.pollster_key == 'activote'].iloc[0]
    assert (m.D, m.R, m.n, m['pop']) == (50, 43, 883, 'LV') and m.n_fuente.startswith('corregido')
    assert (a.D, a.R) == (48.6, 51.4)


def test_partidistas(cfg, red_simulada):
    p = encuestas.obtener_encuestas(cfg)['encuestas']
    assert p[p.pollster_key.isin(['co', 'bigdatapoll', 'echeloninsight', 'quantusinsight', 'datatargeting',
                                  'redboxresearch', 'tulchinresearc', 'emcresearch'])].partidista.all()
    # bipartidistas (Beacon/Shaw, Fabrizio/Impact, GS/New River) y no partidistas
    assert not p[p.pollster_key.isin(['beaconresearch', 'fabrizioleeass', 'gsstrategygrou', 'maristcollege',
                                      'thenewyorktime', 'activote', 'verasight'])].partidista.any()


def test_fuente_caida_usa_cache(cfg, red_simulada):
    encuestas.obtener_encuestas(cfg)
    red_simulada.caidas.add('wikipedia')
    r = encuestas.obtener_encuestas(cfg)
    assert r['estados']['wikipedia'].startswith('cache') and len(r['encuestas']) == N_ENCUESTAS


# ----------------------------------------------------------------------------------- mercados
def test_kalshi_y_polymarket_en_vivo(cfg, red_simulada):
    mk = mercados.obtener_mercados(cfg)
    k, p = mk['kalshi'], mk['polymarket']
    assert k['estado'] == p['estado'] == 'en_vivo' and k['usable'] and p['usable']
    assert k['p_d'] == pytest.approx(0.825) and k['p_r'] == pytest.approx(0.185)
    assert p['p_d'] == pytest.approx(0.825) and p['p_r'] == pytest.approx(0.17)
    assert mk['kalshi_independiente'] is None


def test_rangos_particion_completa_sin_contratos_inactivos(cfg, red_simulada):
    """Margen de Polymarket: 5 rangos de cada lado (partición completa); «Person A» y «Other» (inactivos, 0.50 sin
    volumen) no cuentan."""
    rg = mercados.obtener_mercados(cfg)['rangos']
    assert rg['completo'] and rg['n_contratos'] == 10
    assert rg['suma_precios'] == pytest.approx(1.1195)
    assert rg['P_D'] == pytest.approx(0.7749, abs=1e-4)
    assert rg['margen_media'] == pytest.approx(3.89, abs=0.05) and rg['margen_cond_D'] == pytest.approx(6.82, abs=0.05)


def test_rangos_incompletos_no_dan_probabilidad():
    """Sin el contrato del lado perdedor no hay P(D) ni margen incondicional: solo E[M | D]."""
    t = pd.DataFrame({'desde': [0, 5, 10, 15, 20, 25, 30], 'hasta': [5, 10, 15, 20, 25, 30, np.inf],
                      'p': [.09, .0465, .1505, .26, .245, .115, .24], 'contrato': ['rango'] * 6 + ['abierto']})
    r = mercados.resumen_rangos(t)
    assert not r['completo'] and 'P_D' not in r and 'margen_media' not in r
    assert r['suma_precios'] == pytest.approx(1.147) and r['margen_cond_D'] == pytest.approx(20.99, abs=0.05)


# ----------------------------------------------------------------------------------- civicAPI
def test_civicapi_solo_participacion(cfg, red_simulada):
    """Ohio no tiene registro partidario: civicAPI publica volumen por condado (88), sin partido."""
    a = obtener_anticipado(cfg)
    assert a['disponible'] and a['por_partido'] is False and a['fecha'] == '2026-10-26'
    assert (a['emitidos'], a['por_correo'], a['en_persona']) == (1_084_305, 452_169, 632_136)
    assert a['condado_principal'] == 'Franklin' and len(a['condados']) == 88
    assert a['pct_del_total_previo'] == pytest.approx(100 * 1_084_305 / 4_134_877)


def test_civicapi_sin_partidos_es_error_si_se_pide_partido():
    vacio = {'snapshot_date': '2026-10-23', 'regions': {'Statewide': {'Unspecified': {'votes': 10}}}}
    with pytest.raises(ValueError):
        resumir({'returned': vacio, 'requested': vacio})


# ----------------------------------------------------------------------------------- pipeline
def test_corrida_completa_en_vivo(cfg, red_simulada):
    r = ejecutar(cfg)
    assert r['degradadas'] == []
    f = r['modelo']['final']
    assert abs(f['pct_D'] + f['pct_R'] + f['pct_terceros'] - 100) < 1e-6
    assert f['k'] == 6 and len(r['modelo']['ventana']) == 6 and not f['ventana']['ampliada'] and f['peso_mercados_aplicado'] == 0.30
    assert f['terceros_regimen'] == 'reportado en encuestas' and 2 < f['pct_terceros'] < 4.5
    lo, hi = sorted([f['P_D_encuestas'], r['mercados']['promedio_D']])
    assert lo - 1e-9 <= f['P_D'] <= hi + 1e-9
    assert 'P(recuento, |margen| ≤ 0.25 pp)' in r['resumen_texto']


def test_cifras_de_referencia(cfg, red_simulada):
    """Mismas cifras que el notebook (200 000 simulaciones, semilla fija)."""
    cfg.modelo['n_simulaciones'] = 200_000
    r = ejecutar(cfg, escribir_salidas=False)
    f, par = r['modelo']['final'], r['calibracion']
    assert par['sesgo_regla'] == 'todas'
    assert f['margen_encuestas'] == pytest.approx(MARGEN_ENC, abs=0.01)
    assert par['sesgo_contraido'] == pytest.approx(SESGO, abs=0.002)
    assert f['margen'] == pytest.approx(MARGEN, abs=0.03) and f['P_D'] == pytest.approx(P_D, abs=0.002)
    assert f['pct_terceros'] == pytest.approx(TERCEROS, abs=0.05)


def test_escenarios(cfg, red_simulada):
    e = ejecutar(cfg, escribir_salidas=False)['modelo']['escenarios']
    assert e.escenario.str.startswith('Sin RedBox Research (D)').any() and e.escenario.str.startswith('Sin Beacon Research').any()
    assert e.escenario.str.startswith('Ventana 45 días').any()
    assert e.escenario.str.startswith('Terceros: reducción').sum() == 2
    assert {'Peso de mercados 0.15 (base 0.30)', 'Peso de mercados 0.50 (base 0.30)'} <= set(e.escenario)
    assert e.escenario.str.startswith('Polymarket por rangos').any()
    assert e.escenario.str.startswith('Sesgo estimado sin contiendas de una sola encuestadora').any()
    assert e.escenario.str.startswith('Sesgo estimado solo con contiendas de gobernador').any()
    assert e.escenario.str.startswith('Fechas por el punto medio del campo').any()
    assert e.escenario.str.startswith('Sesgo sin la contienda').sum() == 2
    assert e.escenario.str.startswith('Sin encuestas de patrocinio partidista').any()
    sin = e[e.escenario == 'Sin sesgo estatal, sin mercados'].iloc[0]
    con = e[e.escenario == 'Con sesgo estatal, sin mercados (solo encuestas)'].iloc[0]
    assert SIGNO_SESGO * (con.margen - sin.margen) > 0                  # dirección del sesgo de OH


def test_reporte_json_estricto(cfg, red_simulada):
    ejecutar(cfg)
    txt = (cfg.dir_salidas / 'ultimo' / 'reporte.json').read_text(encoding='utf-8')
    rep = json.loads(txt, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    assert rep['ultima_encuesta']['fin'] == '2026-10-23'
    assert rep['anticipado']['emitidos'] == 1_084_305
    assert (cfg.dir_salidas / 'ultimo' / 'voto_anticipado_condados.csv').exists()


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
    from oh_pronostico import __version__
    ejecutar(cfg)
    h = pd.read_csv(cfg.dir_salidas / 'historial_pronosticos.csv')
    assert h.version_modelo.iloc[-1] == __version__.split()[0]


def test_excel_verificado_contiene_al_csv_publicado():
    from oh_pronostico.config import RAIZ, cargar_config
    ruta = cargar_config().ruta_encuestas_base
    if ruta is None or ruta.suffix.lower() != '.xlsx' or not ruta.exists():
        pytest.skip('la configuración no apunta a un Excel local')
    clave = lambda d: set(zip(d.pollster, pd.to_datetime(d.fin).dt.date, d.D.astype(float), d.R.astype(float)))
    assert clave(encuestas.cargar_base(RAIZ / 'data' / 'encuestas_verificadas_oh.csv')) <= clave(encuestas.cargar_base(ruta))


def test_n_imputado_marcado(cfg, red_simulada):
    """Solo Wedgewood (11–13 ago, solo en el Excel) no trae n: se imputa en 600 y queda marcada."""
    p = encuestas.obtener_encuestas(cfg)['encuestas']
    assert p[p.n_imputado].pollster.tolist() == ['Wedgewood Polls']
    assert (p[p.n_imputado].n == 600).all()


def test_k_efectivo_por_firma(cfg, red_simulada):
    """k efectivo agrupa los pesos por firma (W_f = Σ w de sus encuestas): nunca supera al número de firmas."""
    import re
    e = ejecutar(cfg, escribir_salidas=False)['modelo']['escenarios']
    nom = e[e.escenario.str.startswith('Incertidumbre con k efectivo')].escenario.iloc[0]
    k_ef, k = map(float, re.search(r'k efectivo ([\d.]+) \(no (\d+) firmas\)', nom).groups())
    assert 1 <= k_ef <= k


# valores fijados con la corrida de referencia del 26-oct (ver notebook)
N_ENCUESTAS = 28
MARGEN_ENC, SESGO, MARGEN, P_D, TERCEROS = 2.972, 4.038, 0.59, 0.550, 3.14   # sesgo «todas» (+4.04 pp pro-D, se resta)
SIGNO_SESGO = -1                                    # en OH el sesgo RESTA al demócrata


def test_readme_bloque_automatico(cfg, red_simulada, tmp_path, monkeypatch):
    """El bloque del README (en copias temporales) incluye el pronóstico, el voto ya emitido y la fila del README raíz."""
    import importlib.util
    from oh_pronostico.config import RAIZ
    if not (RAIZ / 'scripts' / 'actualizar_readme.py').exists():
        pytest.skip('paquete local: sin actualizar_readme.py (solo se usa en GitHub)')
    ejecutar(cfg)
    spec = importlib.util.spec_from_file_location('actualizar_readme', RAIZ / 'scripts' / 'actualizar_readme.py')
    ar = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ar)
    est, raiz = tmp_path / 'README_est.md', tmp_path / 'README_raiz.md'
    est.write_text(f'x\n{ar.INI}\n{ar.FIN}\n', encoding='utf-8')
    raiz.write_text('| Estado | a | b | c |\n|---|---|---|---|\n| … | | | |\n', encoding='utf-8')
    monkeypatch.setattr(ar, 'SAL', cfg.dir_salidas)
    monkeypatch.setattr(ar, 'README_EST', est)
    monkeypatch.setattr(ar, 'README_RAIZ', raiz)
    monkeypatch.setattr(ar, 'evolucion', lambda: False)
    assert ar.main() == 0
    t = est.read_text(encoding='utf-8')
    assert 'Amy **Acton**' in t and 'Vivek **Ramaswamy**' in t and '1,084,305' in t
    assert '| Ohio |' in raiz.read_text(encoding='utf-8')
