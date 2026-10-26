"""Pruebas sin red del modelo de Texas (fixtures reales del 25-oct-2026)."""
import json
from datetime import date

import numpy as np
import pandas as pd
import pytest

from tx_pronostico import cli, encuestas, mercados
from tx_pronostico.anticipado import obtener_anticipado, resumir
from tx_pronostico.pipeline import ejecutar

FIX = __import__('pathlib').Path(__file__).parent / 'fixtures'


# ----------------------------------------------------------------------------------- encuestas
def test_fechas_excel():
    assert encuestas._fechas_es('01–05 oct 2026') == (date(2026, 10, 1), date(2026, 10, 5))
    assert encuestas._fechas_es('28 sep–01 oct 2026') == (date(2026, 9, 28), date(2026, 10, 1))


def test_base_verificada_csv():
    """CSV publicado = bloque 1 de la hoja «Histórico encuestas» de TEXAS_GOBERNADOR.xlsx: 50 encuestas generales."""
    from tx_pronostico.config import RAIZ
    b = encuestas.cargar_base(RAIZ / 'data' / 'encuestas_verificadas_tx.csv')
    assert len(b) == 50 and b.iloc[0].D == 42 and b.iloc[0].R == 50 and b.iloc[0].indecisos == 8
    assert ((b[['D', 'R']] * 10).round(6) % 1 == 0).all().all()             # sin residuos de punto flotante del Excel


def test_encuestas_en_vivo_sin_duplicados_y_alias(cfg, red_simulada):
    r = encuestas.obtener_encuestas(cfg)
    p = r['encuestas']
    assert r['estados']['wikipedia'] == 'en_vivo' and r['estados']['270towin'] == 'en_vivo'
    assert not p.duplicated(['pollster_key', 'fin']).any()
    assert len(p) == N_ENCUESTAS and (p.fin > '2026-03-03').all()
    # alias hacia la clave del histórico de FiveThirtyEight (conservan su efecto de casa)
    assert not p.pollster_key.isin(['texasamunivers', 'univofhouston', 'maristuniversi', 'cookpoliticalr',
                                    'newriver', 'uttyler']).any()
    assert (p.pollster_key == 'reconmr').sum() == 4


def test_misma_firma_mismas_cifras_en_fechas_distintas(cfg, red_simulada):
    """Beacon/Shaw (Fox) publicó 47–52 LV el 28-sep y otra vez el 19-oct: son dos encuestas, no una."""
    p = encuestas.obtener_encuestas(cfg)['encuestas']
    b = p[p.pollster_key == 'beaconresearch']
    assert {'2026-09-28', '2026-10-19'} <= set(b.fin.dt.strftime('%Y-%m-%d'))
    assert b[b.fin == '2026-10-19'].iloc[0].n == 1398                   # versión LV, no la RV (2,011)


def test_misma_firma_periodos_distintos_son_dos_encuestas(cfg, red_simulada):
    """ActiVote levantó del 30 sep al 14 oct y del 17 al 21 oct: dos encuestas, aunque sus fechas de fin estén a 7 días.
    Las cifras de la segunda son las de ActiVote (47.5–52.5), no las redondeadas de Wikipedia (48–53, suma 101)."""
    p = encuestas.obtener_encuestas(cfg)['encuestas']
    a = p[p.pollster_key == 'activote']
    a = a.set_index(a.fin.dt.strftime('%Y-%m-%d'))
    assert {'2026-10-14', '2026-10-21'} <= set(a.index)
    assert a.loc['2026-10-21', 'D'] == 47.5 and a.loc['2026-10-21', 'R'] == 52.5
    assert 'wikipedia' not in a.loc['2026-10-14', 'tambien_en']          # ya no se funde con la segunda


def test_fecha_de_publicacion_no_es_otra_encuesta(cfg, red_simulada):
    """270toWin fecha a Verasight/VoteHub el 23-oct (publicación); el campo fue del 1 al 20 de octubre: una sola
    encuesta, con el periodo de campo."""
    p = encuestas.obtener_encuestas(cfg)['encuestas']
    v = p[p.pollster_key == 'verasight']
    assert len(v[v.fin >= '2026-10-15']) == 1
    assert v.iloc[-1].fin == pd.Timestamp('2026-10-20') and '270towin' in v.iloc[-1].tambien_en


def test_yougov_generico_es_la_de_cbs(cfg, red_simulada):
    """270toWin rotula «YouGov» (18-oct, n 1,460) la encuesta de CBS News/YouGov (16-oct, n 1,492 en Wikipedia)."""
    p = encuestas.obtener_encuestas(cfg)['encuestas']
    assert not ((p.pollster_key == 'yougov') & (p.fin >= '2026-10-10')).any()
    assert '270towin' in p[p.pollster_key == 'cbsnews'].iloc[-1].tambien_en


def test_cook_es_gs_strategy(cfg, red_simulada):
    """La encuesta de Cook Political Report del Excel es la de GS Strategy/New River (13-oct, 46–48)."""
    p = encuestas.obtener_encuestas(cfg)['encuestas']
    g = p[(p.pollster_key == 'gsstrategygrou') & (p.fin == '2026-10-13')]
    assert len(g) == 1 and 'base' in g.iloc[0].tambien_en


def test_partidistas_y_bipartidistas(cfg, red_simulada):
    p = encuestas.obtener_encuestas(cfg)['encuestas']
    assert not p[p.pollster_key.isin(['beaconresearch', 'gsstrategygrou'])].partidista.any()   # (D)+(R) = bipartidista
    assert p[p.pollster_key.isin(['gbao', 'stratusintelli'])].partidista.all()


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
    assert k['p_d'] == pytest.approx(0.335) and k['p_r'] == pytest.approx(0.675)
    assert p['p_d'] == pytest.approx(0.315) and p['p_r'] == pytest.approx(0.6865)
    assert mk['kalshi_independiente'] is None                           # Texas no tiene contrato de independiente


def test_rangos_particion_completa(cfg, red_simulada):
    """Margen de Polymarket: 10 contratos D/R (partición completa, sin independiente)."""
    rg = mercados.obtener_mercados(cfg)['rangos']
    t = rg['tabla']
    assert rg['completo'] and rg['n_contratos'] == 10 and not (t.contrato == 'independiente').any()
    assert rg['suma_precios'] == pytest.approx(1.005)
    assert rg['P_D'] == pytest.approx((0.163 + 0.0805 + 0.0475) / 1.005)
    assert rg['margen_media'] == pytest.approx(-3.01, abs=0.05) and rg['margen_cond_D'] == pytest.approx(3.88, abs=0.05)


def test_rangos_incompletos_no_dan_probabilidad():
    """Sin el contrato del lado perdedor no hay P(D) ni margen incondicional: solo E[M | D]."""
    t = pd.DataFrame({'desde': [0, 5, 10, 15, 20, 25, 30], 'hasta': [5, 10, 15, 20, 25, 30, np.inf],
                      'p': [.09, .0465, .1505, .26, .245, .115, .24], 'contrato': ['rango'] * 6 + ['abierto']})
    r = mercados.resumen_rangos(t)
    assert not r['completo'] and 'P_D' not in r and 'margen_media' not in r
    assert r['suma_precios'] == pytest.approx(1.147) and r['margen_cond_D'] == pytest.approx(20.99, abs=0.05)


# ----------------------------------------------------------------------------------- civicAPI
def test_civicapi_solo_participacion(cfg, red_simulada):
    """Texas no tiene registro partidario: civicAPI da volumen (correo + en persona) por condado, sin partido."""
    a = obtener_anticipado(cfg)
    assert a['estado'] == 'en_vivo' and a['por_partido'] is False and a['tiene_en_persona']
    assert a['emitidos'] == 4_132_879 and a['por_correo'] == 198_692 and a['en_persona'] == 3_934_187
    assert a['condado_principal'] == 'Harris' and a['pct_del_total_previo'] == pytest.approx(51.0, abs=0.1)
    assert len(a['condados']) == 254
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
    assert f['k'] == 9 and len(r['modelo']['ventana']) == 10 and not f['ventana']['ampliada'] and f['peso_mercados_aplicado'] == 0.30
    assert f['terceros_regimen'] == 'reportado en encuestas'
    lo, hi = sorted([f['P_D_encuestas'], r['mercados']['promedio_D']])
    assert lo - 1e-9 <= f['P_D'] <= hi + 1e-9
    assert 'Con independiente' not in r['resumen_texto'] and 'Texas no tiene registro partidario' in r['resumen_texto']


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
    assert e.escenario.str.startswith('Sin Beacon Research').any()
    assert e.escenario.str.startswith('Terceros: reducción').sum() == 2
    assert {'Peso de mercados 0.15 (base 0.30)', 'Peso de mercados 0.50 (base 0.30)'} <= set(e.escenario)
    assert e.escenario.str.startswith('Polymarket por rangos').any()
    assert e.escenario.str.startswith('Sesgo estimado sin contiendas de una sola encuestadora').any()
    assert e.escenario.str.startswith('Sesgo estimado solo con contiendas de gobernador').any()
    assert e.escenario.str.startswith('Sin encuestas de patrocinio partidista').any()
    sin = e[e.escenario == 'Sin sesgo estatal, sin mercados'].iloc[0]
    con = e[e.escenario == 'Con sesgo estatal, sin mercados (solo encuestas)'].iloc[0]
    assert sin.P_D > con.P_D                                            # el sesgo de TX es pro-D: quitarlo sube a Hinojosa


def test_reporte_json_estricto(cfg, red_simulada):
    ejecutar(cfg)
    txt = (cfg.dir_salidas / 'ultimo' / 'reporte.json').read_text(encoding='utf-8')
    rep = json.loads(txt, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    assert rep['ultima_encuesta']['fin'] == '2026-10-21'
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
    from tx_pronostico import __version__
    ejecutar(cfg)
    h = pd.read_csv(cfg.dir_salidas / 'historial_pronosticos.csv')
    assert h.version_modelo.iloc[-1] == __version__.split()[0]


def test_excel_verificado_contiene_al_csv_publicado():
    from tx_pronostico.config import RAIZ, cargar_config
    ruta = cargar_config().ruta_encuestas_base
    if ruta is None or ruta.suffix.lower() != '.xlsx' or not ruta.exists():
        pytest.skip('la configuración no apunta a un Excel local')
    clave = lambda d: set(zip(d.pollster, pd.to_datetime(d.fin).dt.date, d.D.astype(float), d.R.astype(float)))
    assert clave(encuestas.cargar_base(RAIZ / 'data' / 'encuestas_verificadas_tx.csv')) <= clave(encuestas.cargar_base(ruta))


def test_n_imputado_marcado(cfg, red_simulada):
    """Sin n en ninguna fuente se imputa 600 y queda marcado: Marist 8–11 oct LV publica «TBA»."""
    p = encuestas.obtener_encuestas(cfg)['encuestas']
    imp = p[(p.fin >= '2026-10-01') & p.n_imputado]
    assert set(imp.pollster_key) == {'maristcollege'} and (imp.n == 600).all()
    assert set(p.n_fuente) <= {'reportado', 'imputado (600)'} or p.n_fuente.str.startswith('corregido').any()


def test_k_efectivo_por_firma(cfg, red_simulada):
    """k efectivo agrupa los pesos por firma (W_f = Σ w de sus encuestas): nunca supera al número de firmas."""
    import re
    e = ejecutar(cfg, escribir_salidas=False)['modelo']['escenarios']
    nom = e[e.escenario.str.startswith('Incertidumbre con k efectivo')].escenario.iloc[0]
    k_ef, k = map(float, re.search(r'k efectivo ([\d.]+) \(no (\d+) firmas\)', nom).groups())
    assert 1 <= k_ef <= k


# valores fijados con la corrida de referencia del 25-oct (ver notebook)
N_ENCUESTAS = 51
MARGEN_ENC, SESGO, MARGEN, P_D, TERCEROS = -3.226, 2.495, -4.634, 0.1417, 2.21   # sesgo «todas» (+2.50 pp pro-D)
