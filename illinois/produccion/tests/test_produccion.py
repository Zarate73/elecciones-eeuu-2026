"""Pruebas sin red del modelo de Illinois (fixtures reales del 25-oct-2026)."""
import json
from datetime import date

import numpy as np
import pandas as pd
import pytest

from il_pronostico import cli, encuestas, mercados
from il_pronostico.anticipado import obtener_anticipado, resumir
from il_pronostico.pipeline import ejecutar

FIX = __import__('pathlib').Path(__file__).parent / 'fixtures'


# ----------------------------------------------------------------------------------- encuestas
def test_fechas_excel():
    assert encuestas._fechas_es('01–05 oct 2026') == (date(2026, 10, 1), date(2026, 10, 5))
    assert encuestas._fechas_es('28 sep–01 oct 2026') == (date(2026, 9, 28), date(2026, 10, 1))


def test_base_verificada_csv():
    """CSV publicado = bloque 1 de la hoja «Histórico encuestas» de ILLINOIS_GOBERNADOR-v1.xlsx: 2 encuestas generales."""
    from il_pronostico.config import RAIZ
    b = encuestas.cargar_base(RAIZ / 'data' / 'encuestas_verificadas_il.csv')
    assert len(b) == 2 and b.iloc[0].pollster == 'Victory Research' and b.iloc[0].D == 54.3 and b.iloc[0].R == 34
    assert b.otros.isna().all()                                         # el Excel no separa terceros de indecisos


def test_encuestas_en_vivo_sin_duplicados_y_alias(cfg, red_simulada):
    """Solo hay dos encuestas generales después de la primaria del 17-mar: PPP (30 sep–1 oct) y ActiVote (2–22 oct).
    Victory Research (nov-2025) es anterior a la primaria y no entra."""
    r = encuestas.obtener_encuestas(cfg)
    p = r['encuestas']
    assert r['estados']['wikipedia'] == 'en_vivo' and r['estados']['270towin'] == 'en_vivo'
    assert not p.duplicated(['pollster_key', 'fin']).any()
    assert len(p) == N_ENCUESTAS and (p.fin > '2026-03-17').all()
    assert set(p.pollster_key) == {'publicpolicypo', 'activote'}
    ppp = p[p.pollster_key == 'publicpolicypo'].iloc[0]
    assert {'base', '270towin'} <= set(ppp.tambien_en.split(', '))      # Excel «PPP — Chicago News Weekly» = misma encuesta
    assert ppp.otros == 6 and ppp['pop'] == 'LV'                          # Corbett 6 % (Wikipedia), no «12 % indecisos/otros»


def test_fecha_de_publicacion_no_es_otra_encuesta(cfg, red_simulada):
    """270toWin fecha a PPP el 6-oct (publicación; campo 30 sep–1 oct) y a ActiVote el 22-oct: una encuesta cada una."""
    p = encuestas.obtener_encuestas(cfg)['encuestas']
    assert p[p.pollster_key == 'publicpolicypo'].iloc[0].fin == pd.Timestamp('2026-10-01')
    assert len(p[p.pollster_key == 'activote']) == 1


def test_firma_partidista_no_es_patrocinio(cfg, red_simulada):
    """Wikipedia rotula a PPP «(D)» por la firma, pero la encuesta la pagó Chicago News Weekly: no es patrocinio
    partidista (config firmas_sin_patrocinio_partidista), como la columna partisan de FiveThirtyEight."""
    p = encuestas.obtener_encuestas(cfg)['encuestas']
    assert not p.partidista.any()
    e = ejecutar(cfg, escribir_salidas=False)['modelo']
    assert not e['escenarios'].escenario.str.startswith('Sin encuestas de patrocinio partidista').any()
    assert set(e['ventana'].patrocinador) == {'—'}


def test_cifras_originales_de_activote(cfg, red_simulada):
    """ActiVote publica 58.7–41.3 (Wikipedia y 270toWin redondean 59–41): margen +17.4, no +18."""
    p = encuestas.obtener_encuestas(cfg)['encuestas']
    a = p[p.pollster_key == 'activote'].iloc[0]
    assert a.D == 58.7 and a.R == 41.3 and a.margin_poll == pytest.approx(17.4)
    v = ejecutar(cfg, escribir_salidas=False)['modelo']['ventana']
    assert v[v.pollster_key == 'activote'].iloc[0].D == 58.7


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
    assert k['p_d'] == pytest.approx(0.968) and k['p_r'] == pytest.approx(0.0355)
    assert p['p_d'] == pytest.approx(0.9695) and p['p_r'] == pytest.approx(0.0265)
    assert mk['kalshi_independiente'] is None                           # Kalshi no lista a Corbett


def test_rangos_particion_completa(cfg, red_simulada):
    """Margen de Polymarket: «Republican Wins» + 7 rangos del demócrata (partición completa)."""
    rg = mercados.obtener_mercados(cfg)['rangos']
    assert rg['completo'] and rg['n_contratos'] == 8
    assert rg['suma_precios'] == pytest.approx(1.0125)
    assert rg['P_D'] == pytest.approx(1 - 0.0275 / 1.0125)
    assert rg['margen_media'] == pytest.approx(20.23, abs=0.05) and rg['margen_cond_D'] == pytest.approx(20.87, abs=0.05)


def test_rangos_incompletos_no_dan_probabilidad():
    """Sin el contrato del lado perdedor no hay P(D) ni margen incondicional: solo E[M | D]."""
    t = pd.DataFrame({'desde': [0, 5, 10, 15, 20, 25, 30], 'hasta': [5, 10, 15, 20, 25, 30, np.inf],
                      'p': [.09, .0465, .1505, .26, .245, .115, .24], 'contrato': ['rango'] * 6 + ['abierto']})
    r = mercados.resumen_rangos(t)
    assert not r['completo'] and 'P_D' not in r and 'margen_media' not in r
    assert r['suma_precios'] == pytest.approx(1.147) and r['margen_cond_D'] == pytest.approx(20.99, abs=0.05)


# ----------------------------------------------------------------------------------- civicAPI
def test_civicapi_solo_participacion(cfg, red_simulada):
    """Illinois no tiene registro partidario: civicAPI da volumen (correo + en persona) por condado y por ciudad con
    junta electoral propia (Chicago, Rockford, Bloomington…), sin partido."""
    a = obtener_anticipado(cfg)
    assert a['estado'] == 'en_vivo' and a['por_partido'] is False and a['tiene_en_persona']
    assert a['emitidos'] == 786_257 and a['por_correo'] == 443_833 and a['en_persona'] == 342_424
    assert a['condado_principal'] == 'Cook' and a['pct_del_total_previo'] == pytest.approx(19.16, abs=0.05)
    assert len(a['condados']) == 108
    red_simulada.caidas.add('civicapi')
    assert obtener_anticipado(cfg)['estado'].startswith('cache')


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
    assert f['k'] == 2 and len(r['modelo']['ventana']) == 2 and f['ventana']['ampliada'] and f['peso_mercados_aplicado'] == 0.30
    assert f['terceros_regimen'] == 'reportado en encuestas'
    lo, hi = sorted([f['P_D_encuestas'], r['mercados']['promedio_D']])
    assert lo - 1e-9 <= f['P_D'] <= hi + 1e-9
    assert 'Con independiente' not in r['resumen_texto'] and 'sin registro partidario' in r['resumen_texto']


def test_cifras_del_25_oct(cfg, red_simulada):
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
    assert e.escenario.str.startswith('Sin ActiVote').any() and e.escenario.str.startswith('Sin Public Policy Polling').any()
    assert e.escenario.str.startswith('Terceros: reducción').sum() == 2
    assert {'Peso de mercados 0.15 (base 0.30)', 'Peso de mercados 0.50 (base 0.30)'} <= set(e.escenario)
    assert e.escenario.str.startswith('Polymarket por rangos').any()
    assert e.escenario.str.startswith('Sesgo estimado sin contiendas de una sola encuestadora').any()
    assert e.escenario.str.startswith('Sesgo estimado solo con contiendas de gobernador').any()
    assert e.escenario.str.startswith('Fechas por el punto medio del campo').any()
    assert e.escenario.str.startswith('Sesgo sin la contienda').sum() == 2
    sin = e[e.escenario == 'Sin sesgo estatal, sin mercados'].iloc[0]
    con = e[e.escenario == 'Con sesgo estatal, sin mercados (solo encuestas)'].iloc[0]
    assert SIGNO_SESGO * (con.margen - sin.margen) > 0                  # dirección del sesgo de IL


def test_reporte_json_estricto(cfg, red_simulada):
    ejecutar(cfg)
    txt = (cfg.dir_salidas / 'ultimo' / 'reporte.json').read_text(encoding='utf-8')
    rep = json.loads(txt, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    assert rep['ultima_encuesta']['fin'] == '2026-10-22'
    assert rep['anticipado']['por_partido'] is False


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
    from il_pronostico import __version__
    ejecutar(cfg)
    h = pd.read_csv(cfg.dir_salidas / 'historial_pronosticos.csv')
    assert h.version_modelo.iloc[-1] == __version__.split()[0]


def test_excel_verificado_contiene_al_csv_publicado():
    from il_pronostico.config import RAIZ, cargar_config
    ruta = cargar_config().ruta_encuestas_base
    if ruta is None or ruta.suffix.lower() != '.xlsx' or not ruta.exists():
        pytest.skip('la configuración no apunta a un Excel local')
    clave = lambda d: set(zip(d.pollster, pd.to_datetime(d.fin).dt.date, d.D.astype(float), d.R.astype(float)))
    assert clave(encuestas.cargar_base(RAIZ / 'data' / 'encuestas_verificadas_il.csv')) <= clave(encuestas.cargar_base(ruta))


def test_n_imputado_marcado(cfg, red_simulada):
    """Las dos encuestas traen n (PPP 569, ActiVote 400): no hay imputación."""
    p = encuestas.obtener_encuestas(cfg)['encuestas']
    assert not p.n_imputado.any() and set(p.n) == {569, 400}
    assert set(p.n_fuente) <= {'reportado', 'imputado (600)'} or p.n_fuente.str.startswith('corregido').any()


def test_k_efectivo_por_firma(cfg, red_simulada):
    """k efectivo agrupa los pesos por firma (W_f = Σ w de sus encuestas): nunca supera al número de firmas."""
    import re
    e = ejecutar(cfg, escribir_salidas=False)['modelo']['escenarios']
    nom = e[e.escenario.str.startswith('Incertidumbre con k efectivo')].escenario.iloc[0]
    k_ef, k = map(float, re.search(r'k efectivo ([\d.]+) \(no (\d+) firmas\)', nom).groups())
    assert 1 <= k_ef <= k


# valores fijados con la corrida de referencia del 25-oct (ver notebook)
N_ENCUESTAS = 2
MARGEN_ENC, SESGO, MARGEN, P_D, TERCEROS = 18.239, -1.201, 17.32, 0.9940, 5.18   # sesgo «todas» (−1.20: encuestas pro-R)
SIGNO_SESGO = +1                                    # en IL el sesgo SUMA al demócrata
