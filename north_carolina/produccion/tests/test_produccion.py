"""Pruebas sin red del modelo de North Carolina · Senado (fixtures reales: captura del 27-oct 20:35 UTC, corte 27-oct)."""
import json
from datetime import date

import numpy as np
import pandas as pd
import pytest

from nc_pronostico import cli, encuestas, mercados
from nc_pronostico.anticipado import obtener_anticipado, resumir
from nc_pronostico.pipeline import ejecutar

FIX = __import__('pathlib').Path(__file__).parent / 'fixtures'


# ----------------------------------------------------------------------------------- encuestas
def test_fechas_excel():
    assert encuestas._fechas_es('01–05 oct 2026') == (date(2026, 10, 1), date(2026, 10, 5))
    assert encuestas._fechas_es('29 sep–05 oct 2026') == (date(2026, 9, 29), date(2026, 10, 5))


def test_base_verificada_csv():
    """CSV publicado = bloque 1 de la hoja «Histórico encuestas» de NORTH_CAROLINA_SENADO.xlsx: 46 encuestas generales."""
    from nc_pronostico.config import RAIZ
    b = encuestas.cargar_base(RAIZ / 'data' / 'encuestas_verificadas_nc.csv')
    assert len(b) == 46 and b.iloc[0].pollster == 'Victory Insights (R)' and (b.iloc[0].D, b.iloc[0].R) == (43, 40)
    a = b[b.pollster == 'ActiVote'].iloc[0]
    assert (a.D, a.R) == (56.9, 43.1)


def test_encuestas_en_vivo_sin_duplicados_y_alias(cfg, red_simulada):
    r = encuestas.obtener_encuestas(cfg)
    p = r['encuestas']
    assert r['estados']['wikipedia'] == 'en_vivo' and r['estados']['270towin'] == 'en_vivo'
    assert not p.duplicated(['pollster_key', 'inicio', 'fin']).any()
    assert len(p) == N_ENCUESTAS and (p.fin > '2025-07-27').all()
    # «Harper Polling (R) — Carolina Journal» (Excel) = Harper Polling; «The Trafalgar Group» = Trafalgar Group; AARP = Fabrizio
    assert not p.pollster_key.isin(['harperpollingc', 'thetrafalgargr', 'aarp', 'fabrizioward']).any()
    assert (p.pollster_key == 'harperpolling').sum() == 8 and (p.pollster_key == 'trafalgargroup').sum() == 2


def test_fecha_de_publicacion_no_es_otra_encuesta(cfg, red_simulada):
    """El Excel y 270toWin fechan a Harper el 22-oct (publicación; campo 18–20 oct): una sola encuesta, con su campo."""
    p = encuestas.obtener_encuestas(cfg)['encuestas']
    m = p[(p.pollster_key == 'harperpolling') & (p.fin >= '2026-10-01')]
    assert len(m) == 1 and m.iloc[0].fin == pd.Timestamp('2026-10-20')
    assert '270towin' in m.iloc[0].tambien_en and 'base' in m.iloc[0].tambien_en


def test_encuestas_aisladas(cfg, red_simulada):
    """«YouGov» 20-oct de 270toWin = Elon/YouGov 29 sep–8 oct; Catawba 30-sep (270toWin y Excel) = Catawba/YouGov 4–15 sep."""
    r = encuestas.obtener_encuestas(cfg)
    p, a = r['encuestas'], r['aisladas']
    assert sorted(zip(a.origen, a.clave_538)) == [('270towin', 'catawbacollege'), ('270towin', 'yougov')]
    assert not ((p.pollster_key == 'yougov') & (p.fin == '2026-10-20')).any()
    assert ((p.pollster_key == 'elonuniversity') & (p.fin == '2026-10-08')).sum() == 1
    c = p[(p.pollster_key == 'catawbacollege') & (p.fin >= '2026-09-01')]
    assert len(c) == 1 and c.iloc[0].fin == pd.Timestamp('2026-09-15')
    assert any(x.startswith('filas de la base verificada aisladas: Catawba') for x in r['avisos'])


def test_partidistas(cfg, red_simulada):
    p = encuestas.obtener_encuestas(cfg)['encuestas']
    assert p[p.pollster_key.isin(['harperpolling', 'trafalgargroup', 'quantusinsight', 'insideradvanta',
                                  'changeresearch', 'publicpolicypo', 'tippinsights'])].partidista.all()
    # bipartidistas (Beacon/Shaw, Fabrizio/Impact) y no partidistas
    assert not p[p.pollster_key.isin(['beaconresearch', 'fabrizioleeass', 'elonuniversity', 'highpointunive',
                                      'surveyusa', 'activote', 'eastcarolinaun', 'thenewyorktime'])].partidista.any()


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
    assert k['p_d'] == pytest.approx(0.9645) and k['p_r'] == pytest.approx(0.0355)
    assert p['p_d'] == pytest.approx(0.97) and p['p_r'] == pytest.approx(0.025)
    assert mk['kalshi_independiente'] is None


def test_rangos_particion_completa_sin_contratos_inactivos(cfg, red_simulada):
    """Margen de Polymarket: 5 rangos de cada lado (partición completa); «Person A» y «Other» (inactivos, 0.50 sin
    volumen) no cuentan."""
    rg = mercados.obtener_mercados(cfg)['rangos']
    assert rg['completo'] and rg['n_contratos'] == 10
    assert rg['suma_precios'] == pytest.approx(1.0155)
    assert rg['P_D'] == pytest.approx(0.9956, abs=1e-4)
    assert rg['margen_media'] == pytest.approx(13.72, abs=0.05) and rg['margen_cond_D'] == pytest.approx(14.21, abs=0.05)


def test_rangos_incompletos_no_dan_probabilidad():
    """Sin el contrato del lado perdedor no hay P(D) ni margen incondicional: solo E[M | D]."""
    t = pd.DataFrame({'desde': [0, 5, 10, 15, 20, 25, 30], 'hasta': [5, 10, 15, 20, 25, 30, np.inf],
                      'p': [.09, .0465, .1505, .26, .245, .115, .24], 'contrato': ['rango'] * 6 + ['abierto']})
    r = mercados.resumen_rangos(t)
    assert not r['completo'] and 'P_D' not in r and 'margen_media' not in r
    assert r['suma_precios'] == pytest.approx(1.147) and r['margen_cond_D'] == pytest.approx(20.99, abs=0.05)


# ----------------------------------------------------------------------------------- civicAPI
def test_civicapi_por_partido(cfg, red_simulada):
    """NC tiene registro partidario: civicAPI publica el voto emitido por partido y condado (100)."""
    a = obtener_anticipado(cfg)
    assert a['disponible'] and a['fecha'] == '2026-10-27' and 'por_partido' not in a
    assert (a['emitidos'], a['por_correo'], a['en_persona']) == (1_773_889, 65_841, 1_708_048)
    assert a['condado_principal'] == 'Wake' and len(a['condados']) == 100
    assert a['pct_D'] == pytest.approx(40.963, abs=0.01) and a['margen_DR_pp'] == pytest.approx(16.72, abs=0.01)


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
    assert f['k'] == 3 and len(r['modelo']['ventana']) == 3 and not f['ventana']['ampliada'] and f['peso_mercados_aplicado'] == 0.30
    assert f['terceros_regimen'] == 'reportado en encuestas' and 2 < f['pct_terceros'] < 4.5
    lo, hi = sorted([f['P_D_encuestas'], r['mercados']['promedio_D']])
    assert lo - 1e-9 <= f['P_D'] <= hi + 1e-9
    assert 'P(recuento, |margen| ≤ 0.26 pp)' in r['resumen_texto']


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
    assert e.escenario.str.startswith('Sin Quantus Insights (R)').any() and e.escenario.str.startswith('Sin ActiVote').any()
    assert e.escenario.str.startswith('Ventana 45 días').any()
    assert e.escenario.str.startswith('Terceros: reducción').sum() == 2
    assert {'Peso de mercados 0.15 (base 0.30)', 'Peso de mercados 0.50 (base 0.30)'} <= set(e.escenario)
    assert e.escenario.str.startswith('Polymarket por rangos').any()
    assert e.escenario.str.startswith('Sesgo estimado sin contiendas de una sola encuestadora').any()
    assert e.escenario.str.startswith('Sesgo estimado solo con contiendas de Senado').any()
    assert e.escenario.str.startswith('Fechas por el punto medio del campo').any()
    assert e.escenario.str.startswith('Sesgo sin la contienda').sum() == 2
    assert e.escenario.str.startswith('Sin encuestas de patrocinio partidista').any()
    sin = e[e.escenario == 'Sin sesgo estatal, sin mercados'].iloc[0]
    con = e[e.escenario == 'Con sesgo estatal, sin mercados (solo encuestas)'].iloc[0]
    assert SIGNO_SESGO * (con.margen - sin.margen) > 0                  # dirección del sesgo de NC


def test_reporte_json_estricto(cfg, red_simulada):
    ejecutar(cfg)
    txt = (cfg.dir_salidas / 'ultimo' / 'reporte.json').read_text(encoding='utf-8')
    rep = json.loads(txt, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    assert rep['ultima_encuesta']['fin'] == '2026-10-25'
    assert rep['anticipado']['emitidos'] == 1_773_889 and rep['senado']['n_encuestas'] == N_ENCUESTAS
    assert (cfg.dir_salidas / 'ultimo' / 'voto_anticipado_condados.csv').exists()
    assert [x['encuestadora'] for x in rep['encuestas_aisladas']] == ['Catawba College', 'YouGov']
    assert len(pd.read_csv(cfg.dir_salidas / 'ultimo' / 'encuestas_aisladas.csv', encoding='utf-8-sig')) == 2


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
    from nc_pronostico import __version__
    ejecutar(cfg)
    h = pd.read_csv(cfg.dir_salidas / 'historial_pronosticos.csv')
    assert h.version_modelo.iloc[-1] == __version__.split()[0]


def test_excel_verificado_contiene_al_csv_publicado():
    from nc_pronostico.config import RAIZ, cargar_config
    ruta = cargar_config().ruta_encuestas_base
    if ruta is None or ruta.suffix.lower() != '.xlsx' or not ruta.exists():
        pytest.skip('la configuración no apunta a un Excel local')
    clave = lambda d: set(zip(d.pollster, pd.to_datetime(d.fin).dt.date, d.D.astype(float), d.R.astype(float)))
    assert clave(encuestas.cargar_base(RAIZ / 'data' / 'encuestas_verificadas_nc.csv')) <= clave(encuestas.cargar_base(ruta))


def test_n_imputado_marcado(cfg, red_simulada):
    """Todas las encuestas traen n en alguna fuente: ninguna se imputa (la Harper «¹» del Excel se funde con Wikipedia)."""
    p = encuestas.obtener_encuestas(cfg)['encuestas']
    assert not p.n_imputado.any() and (p.n_fuente != 'imputado (600)').all()


def test_k_efectivo_por_firma(cfg, red_simulada):
    """k efectivo agrupa los pesos por firma (W_f = Σ w de sus encuestas): nunca supera al número de firmas."""
    import re
    e = ejecutar(cfg, escribir_salidas=False)['modelo']['escenarios']
    nom = e[e.escenario.str.startswith('Incertidumbre con k efectivo')].escenario.iloc[0]
    k_ef, k = map(float, re.search(r'k efectivo ([\d.]+) \(no (\d+) firmas\)', nom).groups())
    assert 1 <= k_ef <= k


# valores fijados con la corrida de referencia del 27-oct (ver notebook)
N_ENCUESTAS = 47
MARGEN_ENC, SESGO, MARGEN, P_D, TERCEROS = 10.677, 2.102, 9.23, 0.948, 3.20   # sesgo «todas» (+2.10 pp pro-D, se resta)
SIGNO_SESGO = -1                                    # en NC el sesgo RESTA al demócrata


def test_readme_bloque_automatico(cfg, red_simulada, tmp_path, monkeypatch):
    """El bloque del README (en copias temporales) incluye el pronóstico, el voto ya emitido y la fila del README raíz."""
    import importlib.util
    from nc_pronostico.config import RAIZ
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
    assert 'Roy **Cooper**' in t and 'Michael **Whatley**' in t and '1,773,889' in t
    assert '| North Carolina |' in raiz.read_text(encoding='utf-8')


# ----------------------------------------------------------------------------------- revisión OH-05: reconstrucción de cortes
def _con_encuestas_artificiales(monkeypatch, filas):
    """Agrega encuestas a la respuesta de Wikipedia (como si la fuente descargada hoy las trajera)."""
    from nc_pronostico import encuestas_web as W
    original = W.parse_tabla_wikipedia

    def parse(*a, **k):
        d = original(*a, **k)
        base = d.iloc[0].to_dict()
        extra = [{**base, 'pollster': nom, 'clave_538': W.clave_firma(nom), 'inicio': date.fromisoformat(i),
                  'fin': date.fromisoformat(f), 'n': 800.0, 'pop': 'LV', 'D': D, 'R': R} for nom, i, f, D, R in filas]
        return pd.concat([d, pd.DataFrame(extra)], ignore_index=True)
    monkeypatch.setattr(W, 'parse_tabla_wikipedia', parse)


def test_es_reconstruccion_solo_si_el_corte_es_anterior_a_hoy(cfg, red_simulada):
    assert cfg.hoy == date(2026, 10, 27) and not cfg.es_reconstruccion          # reloj fijo de los fixtures
    cfg.corte_manual = date(2026, 10, 22)
    assert cfg.es_reconstruccion


def test_fecha_de_publicacion_desde_270towin(cfg, red_simulada):
    """270toWin fecha por publicación: Harper (campo 18–20 oct) se publicó el 22-oct; SurveyUSA (7–11 oct), el 13-oct.
    Sin fecha de publicación (Elon 29 sep–8 oct, no está en 270toWin con su nombre): cierre de campo + 3 días."""
    m = encuestas.obtener_encuestas(cfg)['encuestas']
    har = m[(m.pollster_key == 'harperpolling') & (m.fin == '2026-10-20')].iloc[0]
    sus = m[m.pollster_key == 'surveyusa'].iloc[0]
    elo = m[(m.pollster_key == 'elonuniversity') & (m.fin == '2026-10-08')].iloc[0]
    assert (har.publicacion, har.tipo_fecha) == (pd.Timestamp('2026-10-22'), 'publicacion (270toWin)')
    assert sus.disponible_desde == pd.Timestamp('2026-10-13')
    assert elo.tipo_fecha == 'estimada: fin + 3 días' and elo.disponible_desde == pd.Timestamp('2026-10-11')
    assert (m.disponible_desde >= m.fin).all()


def test_reconstruccion_excluye_encuestas_no_publicadas(cfg, red_simulada):
    """Corte del 20-oct con las fuentes de hoy: Harper (publicada el 22-oct) y Quantus (campo 24–25 oct) no entran; con
    una sola encuestadora en la ventana (ActiVote, publicada el 20-oct) la ventana se amplía."""
    cfg.corte_manual = date(2026, 10, 20)
    r = ejecutar(cfg, escribir_salidas=False)
    v = set(r['modelo']['ventana'].pollster_key)
    assert v == {'activote', 'bigdatapoll', 'changeresearch', 'eastcarolinaun', 'elonuniversity', 'surveyusa', 'trafalgargroup'}
    assert r['modelo']['final']['ventana']['ampliada']
    assert not ((r['modelo']['encuestas'].pollster_key == 'quantusinsight') & (r['modelo']['encuestas'].fin > '2026-10-20')).any()
    rec = r['reconstruccion']
    assert rec['activa'] and [x['encuestadora'] for x in rec['no_disponibles_al_corte']] == ['Harper Polling (R)']
    assert r['avisos'][0].startswith('RECONSTRUCCIÓN del corte 2026-10-20') and 'RECONSTRUCCIÓN' in r['resumen_texto']


def test_encuesta_futura_artificial_nunca_entra(cfg, red_simulada, monkeypatch):
    """Aunque la fuente descargada la traiga: (a) campo posterior al corte → nunca; (b) campo cerrado antes del corte pero
    sin publicación conocida y fin + 3 > corte → fuera en una reconstrucción; (c) en la corrida diaria lo descargado hoy ya
    está publicado → entra."""
    _con_encuestas_artificiales(monkeypatch, [('Futura A', '2026-10-22', '2026-10-23', 60, 30),
                                              ('Reciente B', '2026-10-19', '2026-10-21', 30, 60),
                                              ('Hoy C', '2026-10-25', '2026-10-26', 49, 49)])
    cfg.corte_manual = date(2026, 10, 22)
    r = ejecutar(cfg, escribir_salidas=False)
    nombres = set(r['modelo']['encuestas'].pollster)
    assert 'Futura A' not in nombres and 'Reciente B' not in nombres and 'Hoy C' not in nombres
    assert 'Reciente B' in {x['encuestadora'] for x in r['reconstruccion']['no_disponibles_al_corte']}
    cfg.corte_manual = date(2026, 10, 27)                                   # corrida diaria
    r2 = ejecutar(cfg, escribir_salidas=False)
    assert {'Futura A', 'Reciente B', 'Hoy C'} <= set(r2['modelo']['encuestas'].pollster)
    assert not r2['reconstruccion']['activa'] and r2['reconstruccion']['no_disponibles_al_corte'] == []


def test_reconstruccion_usa_precios_al_cierre_del_corte(cfg, red_simulada):
    """Mercados del 20-oct al cierre de ese día (Kalshi 0.961/0.043, Polymarket 0.966/0.036), no los de hoy; los rangos
    también. No se escribe en la caché de consultas en vivo."""
    cfg.corte_manual = date(2026, 10, 20)
    mk = mercados.obtener_mercados(cfg)
    k, p = mk['kalshi'], mk['polymarket']
    assert k['estado'] == p['estado'] == 'historico (cierre 2026-10-20)' and k['usable'] and p['usable']
    assert (k['p_d'], k['p_r']) == pytest.approx((0.961, 0.043)) and (p['p_d'], p['p_r']) == pytest.approx((0.966, 0.036))
    assert mk['rangos']['estado'].startswith('historico') and mk['rangos']['n_contratos'] == 10
    assert not (cfg.dir_cache / 'mercado_kalshi.csv').exists()


def test_reconstruccion_no_usa_el_voto_anticipado_de_hoy(cfg, red_simulada):
    """civicAPI publica hoy el acumulado al 27-oct: en una reconstrucción del 22-oct solo vale un snapshot ≤ 22-oct.
    Sin él, «no aplica» (diagnóstico; no cuenta como fuente degradada)."""
    ejecutar(cfg)                                                           # corrida diaria: guarda el snapshot del 27-oct
    cfg.corte_manual = date(2026, 10, 22)
    r = ejecutar(cfg, escribir_salidas=False)
    assert not r['anticipado']['disponible'] and r['estados_fuentes']['civicapi'].startswith('no_aplica')
    assert r['degradadas'] == []


def test_csv_de_encuestas_trae_fechas_de_disponibilidad(cfg, red_simulada):
    ejecutar(cfg)
    e = pd.read_csv(cfg.dir_salidas / 'ultimo' / 'encuestas_senado.csv', encoding='utf-8-sig')
    assert {'publicacion', 'tipo_fecha', 'disponible_desde'} <= set(e.columns)
    assert e[(e.pollster == 'Harper Polling (R)') & (e.fin == '2026-10-20')].disponible_desde.iloc[0].startswith('2026-10-22')


# ----------------------------------------------------------------------------------- sin tercero principal (NC)
def test_sin_tercero_principal_no_se_reporta(cfg, red_simulada):
    """NC tiene dos candidatos menores (Bray, L; Dublin, Verde): los terceros van en bloque y no hay «tercero principal»."""
    assert 'tercero_principal' not in cfg.modelo
    r = ejecutar(cfg, escribir_salidas=False)
    assert 'tercero_principal' not in r['modelo']['final'] and 'conserva el registro' not in r['resumen_texto']


def test_reconstruccion_sin_red_usa_caches_al_corte(cfg, red_simulada):
    """Notebook: reconstrucción sin red del corte del 27-oct con las cachés de esa corrida → mercados y rangos de caché."""
    ejecutar(cfg)                                                          # corrida diaria del 27-oct (guarda cachés)
    red_simulada.caidas.update({'kalshi', 'polymarket', 'civicapi'})
    import nc_pronostico.config as C
    class Manana(C.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 28, 12, 0, tzinfo=tz)
    import pytest as _pt
    mp = _pt.MonkeyPatch(); mp.setattr('nc_pronostico.config.datetime', Manana)
    try:
        cfg.corte_manual = date(2026, 10, 27)
        r = ejecutar(cfg, escribir_salidas=False)
    finally:
        mp.undo()
    assert r['reconstruccion']['activa']
    assert r['mercados']['kalshi']['estado'].startswith('cache') and r['mercados']['rangos']['estado'].startswith('cache')
    assert 'margen_media' in r['mercados']['rangos'] and r['anticipado']['disponible']


# ----------------------------------------------------------------------------------- cliente HTTP (27-oct, límite de Wikimedia)
def test_wikimedia_ua_propio_y_respeta_retry_after(monkeypatch):
    """A Wikipedia se le envía el UA identificado (política de Wikimedia), no el de navegador; ante 503 con Retry-After
    se espera lo que pide (+1 s) y se reintenta hasta 5 veces. A 270toWin se le sigue enviando el UA de navegador."""
    import requests
    from nc_pronostico import red

    class Resp:
        def __init__(self, code, ra=None):
            self.status_code, self.headers = code, ({'Retry-After': ra} if ra else {})
            self.text, self.encoding = 'ok', 'utf-8'

        def raise_for_status(self):
            pass

        def json(self):
            return {'ok': 1}

    llamadas, esperas = [], []
    seq = iter([Resp(503, '12'), Resp(503, '14'), Resp(429, '200'), Resp(200)])
    monkeypatch.setattr(requests, 'get', lambda url, **kw: (llamadas.append((url, kw['headers']['User-Agent'])), next(seq))[1])
    monkeypatch.setattr(red.time, 'sleep', esperas.append)
    assert red.get_json('https://en.wikipedia.org/w/api.php', params={'a': 1}) == {'ok': 1}
    assert esperas == [13.0, 15.0, 60.0] and len(llamadas) == 4
    assert all(ua == red.UA_WIKIMEDIA and 'Mozilla' not in ua for _, ua in llamadas)
    llamadas.clear()
    monkeypatch.setattr(requests, 'get', lambda url, **kw: (llamadas.append((url, kw['headers']['User-Agent'])), Resp(200))[1])
    red.get_text('https://www.270towin.com/2026-senate-polls/north-carolina')
    assert llamadas[0][1] == red.UA
    seq2 = iter([Resp(503, '1')] * 5)
    monkeypatch.setattr(requests, 'get', lambda url, **kw: next(seq2))
    with pytest.raises(RuntimeError, match='tras 5 intentos'):
        red.get_json('https://en.wikipedia.org/w/api.php')
