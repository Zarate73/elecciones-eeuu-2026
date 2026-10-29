"""Pruebas sin red del modelo de Wisconsin · Gobernador (fixtures reales: captura del 29-oct 02:15 UTC, corte 28-oct)."""
import json
from datetime import date

import numpy as np
import pandas as pd
import pytest

from wi_pronostico import cli, encuestas, mercados
from wi_pronostico.anticipado import obtener_anticipado, resumir
from wi_pronostico.pipeline import ejecutar

FIX = __import__('pathlib').Path(__file__).parent / 'fixtures'


# ----------------------------------------------------------------------------------- encuestas
def test_fechas_excel():
    assert encuestas._fechas_es('01–05 oct 2026') == (date(2026, 10, 1), date(2026, 10, 5))
    assert encuestas._fechas_es('29 sep–05 oct 2026') == (date(2026, 9, 29), date(2026, 10, 5))


def test_base_verificada_csv():
    """CSV publicado = bloque 1 de la hoja «Histórico encuestas» de WISCONSIN_GOBERNADOR.xlsx: 9 encuestas generales."""
    from wi_pronostico.config import RAIZ
    b = encuestas.cargar_base(RAIZ / 'data' / 'encuestas_verificadas_wi.csv')
    assert len(b) == 9 and b.iloc[0].pollster == 'TIPP Insights (R)' and (b.iloc[0].D, b.iloc[0].R) == (42, 41)
    y = b[b.pollster.str.startswith('YouGov')].iloc[0]
    assert (y.D, y.R, y['pop']) == (46, 42, 'A')


def test_encuestas_en_vivo_sin_duplicados_y_alias(cfg, red_simulada):
    r = encuestas.obtener_encuestas(cfg)
    p = r['encuestas']
    assert r['estados']['wikipedia'] == 'en_vivo' and r['estados']['270towin'] == 'en_vivo'
    assert not p.duplicated(['pollster_key', 'inicio', 'fin']).any()
    assert len(p) == N_ENCUESTAS and (p.fin > '2026-03-01').all()
    # Marquette con tres nombres; «TIPP» = TIPP Insights; Badger Battleground = Platform Communications; RMG/Napolitan
    assert not p.pollster_key.isin(['marquettelawsc', 'tipp', 'badgerbattlegr', 'rmgresearchnap', 'yougovcityforw']).any()
    assert (p.pollster_key == 'marquetteunive').sum() == 3 and (p.pollster_key == 'tippinsights').sum() == 2


def test_fecha_de_publicacion_no_es_otra_encuesta(cfg, red_simulada):
    """270toWin fecha a Marquette de octubre el 28-oct (publicación; campo 14–22 oct): una sola encuesta, con su campo."""
    p = encuestas.obtener_encuestas(cfg)['encuestas']
    m = p[(p.pollster_key == 'marquetteunive') & (p.fin >= '2026-10-01')]
    assert len(m) == 1 and m.iloc[0].fin == pd.Timestamp('2026-10-22') and '270towin' in m.iloc[0].tambien_en
    assert (m.iloc[0].D, m.iloc[0].R, m.iloc[0]['pop']) == (51, 44, 'LV')


def test_sin_encuestas_aisladas(cfg, red_simulada):
    """Wisconsin no necesita aislar filas: data/encuestas_excluidas.csv solo trae el encabezado."""
    r = encuestas.obtener_encuestas(cfg)
    assert r['aisladas'].empty and not any('aisladas' in a for a in r['avisos'])


def test_partidistas(cfg, red_simulada):
    p = encuestas.obtener_encuestas(cfg)['encuestas']
    assert p[p.pollster_key.isin(['tippinsights', 'gbao', 'platformcommun', 'ztoaresearch', 'yougov', 'wick'])].partidista.all()
    assert not p[p.pollster_key.isin(['marquetteunive', 'rmgresearch'])].partidista.any()


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
    assert k['p_d'] == pytest.approx(0.835) and k['p_r'] == pytest.approx(0.165)
    assert p['p_d'] == pytest.approx(0.84) and p['p_r'] == pytest.approx(0.145)
    assert mk['kalshi_independiente'] is None


def test_rangos_particion_completa_sin_contratos_inactivos(cfg, red_simulada):
    """Margen de Polymarket: 5 rangos de cada lado (partición completa); «Person A» y «Other» (inactivos, 0.50 sin
    volumen) no cuentan."""
    rg = mercados.obtener_mercados(cfg)['rangos']
    assert rg['completo'] and rg['n_contratos'] == 10
    assert rg['suma_precios'] == pytest.approx(1.004)
    assert rg['P_D'] == pytest.approx(0.8685, abs=1e-4)
    assert rg['margen_media'] == pytest.approx(4.94, abs=0.05) and rg['margen_cond_D'] == pytest.approx(6.18, abs=0.05)


def test_rangos_incompletos_no_dan_probabilidad():
    """Sin el contrato del lado perdedor no hay P(D) ni margen incondicional: solo E[M | D]."""
    t = pd.DataFrame({'desde': [0, 5, 10, 15, 20, 25, 30], 'hasta': [5, 10, 15, 20, 25, 30, np.inf],
                      'p': [.09, .0465, .1505, .26, .245, .115, .24], 'contrato': ['rango'] * 6 + ['abierto']})
    r = mercados.resumen_rangos(t)
    assert not r['completo'] and 'P_D' not in r and 'margen_media' not in r
    assert r['suma_precios'] == pytest.approx(1.147) and r['margen_cond_D'] == pytest.approx(20.99, abs=0.05)


# ----------------------------------------------------------------------------------- civicAPI
def test_civicapi_solo_participacion(cfg, red_simulada):
    """Wisconsin no tiene registro partidario: civicAPI publica volumen por condado (72), sin partido."""
    a = obtener_anticipado(cfg)
    assert a['disponible'] and a['por_partido'] is False and a['fecha'] == '2026-10-28'
    assert (a['emitidos'], a['por_correo'], a['en_persona']) == (873_458, 574_433, 299_025)
    assert a['condado_principal'] == 'Milwaukee' and len(a['condados']) == 72
    assert a['pct_del_total_previo'] == pytest.approx(100 * 873_458 / 2_656_490)


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
    assert f['k'] == 2 and len(r['modelo']['ventana']) == 2 and not f['ventana']['ampliada'] and f['peso_mercados_aplicado'] == 0.30
    assert f['terceros_regimen'].startswith('solo dos candidatos') and f['pct_terceros'] < 0.3
    assert f['sesgo_estatal_aplicado'] == 0
    lo, hi = sorted([f['P_D_encuestas'], r['mercados']['promedio_D']])
    assert lo - 1e-9 <= f['P_D'] <= hi + 1e-9
    assert 'P(recuento, |margen| ≤ 1.0 pp)' in r['resumen_texto']


def test_cifras_de_referencia(cfg, red_simulada):
    """Mismas cifras que el notebook (200 000 simulaciones, semilla fija)."""
    cfg.modelo['n_simulaciones'] = 200_000
    r = ejecutar(cfg, escribir_salidas=False)
    f, par = r['modelo']['final'], r['calibracion']
    assert par['sesgo_regla'] == 'todas'
    assert f['margen_encuestas'] == pytest.approx(MARGEN_ENC, abs=0.01)
    assert par['sesgo_contraido'] == pytest.approx(SESGO, abs=0.002) and f['sesgo_estatal_aplicado'] == 0   # solo escenario
    assert f['margen'] == pytest.approx(MARGEN, abs=0.03) and f['P_D'] == pytest.approx(P_D, abs=0.002)
    assert f['pct_terceros'] == pytest.approx(TERCEROS, abs=0.05)


def test_escenarios(cfg, red_simulada):
    e = ejecutar(cfg, escribir_salidas=False)['modelo']['escenarios']
    assert e.escenario.str.startswith('Sin Wick (R)').any() and e.escenario.str.startswith('Sin Marquette University').any()
    assert e.escenario.str.startswith('Ventana 45 días').any()
    assert e.escenario.str.startswith('Terceros: reducción').sum() == 2
    assert {'Peso de mercados 0.15 (base 0.30)', 'Peso de mercados 0.50 (base 0.30)'} <= set(e.escenario)
    assert e.escenario.str.startswith('Polymarket por rangos').any()
    assert e.escenario.str.startswith('Sesgo estimado sin contiendas de una sola encuestadora').any()
    assert e.escenario.str.startswith('Sesgo estimado solo con contiendas de gobernador').any()
    assert e.escenario.str.startswith('Fechas por el punto medio del campo').any()
    assert e.escenario.str.startswith('Sesgo sin la contienda').sum() == 2
    assert e.escenario.str.startswith('Sin encuestas de patrocinio partidista').any()
    sin = e[e.escenario == 'Sin sesgo estatal, sin mercados (solo encuestas)'].iloc[0]   # producción (regla de Arizona)
    con = e[e.escenario == 'Con sesgo estatal, sin mercados'].iloc[0]
    assert SIGNO_SESGO * (con.margen - sin.margen) > 0                  # el escenario con sesgo resta al demócrata


def test_reporte_json_estricto(cfg, red_simulada):
    ejecutar(cfg)
    txt = (cfg.dir_salidas / 'ultimo' / 'reporte.json').read_text(encoding='utf-8')
    rep = json.loads(txt, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    assert rep['ultima_encuesta']['fin'] == '2026-10-23'
    assert rep['anticipado']['emitidos'] == 873_458 and rep['gobernador']['n_encuestas'] == N_ENCUESTAS
    assert (cfg.dir_salidas / 'ultimo' / 'voto_anticipado_condados.csv').exists()
    assert rep['encuestas_aisladas'] == [] and not (cfg.dir_salidas / 'ultimo' / 'encuestas_aisladas.csv').exists()


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
    from wi_pronostico import __version__
    ejecutar(cfg)
    h = pd.read_csv(cfg.dir_salidas / 'historial_pronosticos.csv')
    assert h.version_modelo.iloc[-1] == __version__.split()[0]


def test_excel_verificado_contiene_al_csv_publicado():
    from wi_pronostico.config import RAIZ, cargar_config
    ruta = cargar_config().ruta_encuestas_base
    if ruta is None or ruta.suffix.lower() != '.xlsx' or not ruta.exists():
        pytest.skip('la configuración no apunta a un Excel local')
    clave = lambda d: set(zip(d.pollster, pd.to_datetime(d.fin).dt.date, d.D.astype(float), d.R.astype(float)))
    assert clave(encuestas.cargar_base(RAIZ / 'data' / 'encuestas_verificadas_wi.csv')) <= clave(encuestas.cargar_base(ruta))


def test_n_imputado_marcado(cfg, red_simulada):
    """Todas las encuestas traen n en Wikipedia o 270toWin: ninguna se imputa."""
    p = encuestas.obtener_encuestas(cfg)['encuestas']
    assert not p.n_imputado.any() and (p.n_fuente != 'imputado (600)').all()


def test_k_efectivo_por_firma(cfg, red_simulada):
    """k efectivo agrupa los pesos por firma (W_f = Σ w de sus encuestas): nunca supera al número de firmas."""
    import re
    e = ejecutar(cfg, escribir_salidas=False)['modelo']['escenarios']
    nom = e[e.escenario.str.startswith('Incertidumbre con k efectivo')].escenario.iloc[0]
    k_ef, k = map(float, re.search(r'k efectivo ([\d.]+) \(no (\d+) firmas\)', nom).groups())
    assert 1 <= k_ef <= k


# valores fijados con la corrida de referencia del 28-oct (ver notebook)
N_ENCUESTAS = 11
MARGEN_ENC, SESGO, MARGEN, P_D, TERCEROS = 5.483, 0.505, 5.76, 0.819, 0.12   # sin sesgo estatal (el sesgo +0.50 es escenario)
SIGNO_SESGO = -1                                    # el escenario con sesgo RESTA al demócrata


def test_readme_bloque_automatico(cfg, red_simulada, tmp_path, monkeypatch):
    """El bloque del README (en copias temporales) incluye el pronóstico, el voto ya emitido y la fila del README raíz."""
    import importlib.util
    from wi_pronostico.config import RAIZ
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
    assert 'David **Crowley**' in t and 'Tom **Tiffany**' in t and '873,458' in t
    assert '| Wisconsin |' in raiz.read_text(encoding='utf-8')


# ----------------------------------------------------------------------------------- revisión OH-05: reconstrucción de cortes
def _con_encuestas_artificiales(monkeypatch, filas):
    """Agrega encuestas a la respuesta de Wikipedia (como si la fuente descargada hoy las trajera)."""
    from wi_pronostico import encuestas_web as W
    original = W.parse_tabla_wikipedia

    def parse(*a, **k):
        d = original(*a, **k)
        base = d.iloc[0].to_dict()
        extra = [{**base, 'pollster': nom, 'clave_538': W.clave_firma(nom), 'inicio': date.fromisoformat(i),
                  'fin': date.fromisoformat(f), 'n': 800.0, 'pop': 'LV', 'D': D, 'R': R} for nom, i, f, D, R in filas]
        return pd.concat([d, pd.DataFrame(extra)], ignore_index=True)
    monkeypatch.setattr(W, 'parse_tabla_wikipedia', parse)


def test_es_reconstruccion_solo_si_el_corte_es_anterior_a_hoy(cfg, red_simulada):
    assert cfg.hoy == date(2026, 10, 28) and not cfg.es_reconstruccion          # reloj fijo de los fixtures
    cfg.corte_manual = date(2026, 10, 24)
    assert cfg.es_reconstruccion


def test_fecha_de_publicacion_desde_270towin(cfg, red_simulada):
    """270toWin fecha por publicación: Marquette (campo 14–22 oct) se publicó el 28-oct; YouGov (22 sep–9 oct), el 16-oct.
    Sin fecha de publicación (Wick, solo en Wikipedia): cierre de campo + 3 días."""
    m = encuestas.obtener_encuestas(cfg)['encuestas']
    mar = m[(m.pollster_key == 'marquetteunive') & (m.fin == '2026-10-22')].iloc[0]
    you = m[m.pollster_key == 'yougov'].iloc[0]
    wic = m[m.pollster_key == 'wick'].iloc[0]
    assert (mar.publicacion, mar.tipo_fecha) == (pd.Timestamp('2026-10-28'), 'publicacion (270toWin)')
    assert you.disponible_desde == pd.Timestamp('2026-10-16')
    assert wic.tipo_fecha == 'estimada: fin + 3 días' and wic.disponible_desde == pd.Timestamp('2026-10-26')
    assert (m.disponible_desde >= m.fin).all()


def test_reconstruccion_excluye_encuestas_no_publicadas(cfg, red_simulada):
    """Corte del 24-oct con las fuentes de hoy: Marquette (publicada el 28-oct) y Wick (fin + 3 = 26-oct) no entran;
    sin encuestadoras en los últimos 21 días la ventana se amplía (Marquette sep, Z to A, YouGov)."""
    cfg.corte_manual = date(2026, 10, 24)
    r = ejecutar(cfg, escribir_salidas=False)
    assert set(r['modelo']['ventana'].pollster_key) == {'marquetteunive', 'ztoaresearch', 'yougov'}
    assert r['modelo']['final']['ventana']['ampliada']
    rec = r['reconstruccion']
    assert rec['activa'] and [x['encuestadora'] for x in rec['no_disponibles_al_corte']] == ['Marquette University', 'Wick (R)']
    assert r['avisos'][0].startswith('RECONSTRUCCIÓN del corte 2026-10-24') and 'RECONSTRUCCIÓN' in r['resumen_texto']


def test_encuesta_futura_artificial_nunca_entra(cfg, red_simulada, monkeypatch):
    """Aunque la fuente descargada la traiga: (a) campo posterior al corte → nunca; (b) campo cerrado antes del corte pero
    sin publicación conocida y fin + 3 > corte → fuera en una reconstrucción; (c) en la corrida diaria lo descargado hoy ya
    está publicado → entra."""
    _con_encuestas_artificiales(monkeypatch, [('Futura A', '2026-10-23', '2026-10-24', 60, 30),
                                              ('Reciente B', '2026-10-20', '2026-10-22', 30, 60),
                                              ('Hoy C', '2026-10-26', '2026-10-27', 49, 49)])
    cfg.corte_manual = date(2026, 10, 23)
    r = ejecutar(cfg, escribir_salidas=False)
    nombres = set(r['modelo']['encuestas'].pollster)
    assert 'Futura A' not in nombres and 'Reciente B' not in nombres and 'Hoy C' not in nombres
    assert 'Reciente B' in {x['encuestadora'] for x in r['reconstruccion']['no_disponibles_al_corte']}
    cfg.corte_manual = date(2026, 10, 28)                                   # corrida diaria
    r2 = ejecutar(cfg, escribir_salidas=False)
    assert {'Futura A', 'Reciente B', 'Hoy C'} <= set(r2['modelo']['encuestas'].pollster)
    assert not r2['reconstruccion']['activa'] and r2['reconstruccion']['no_disponibles_al_corte'] == []


def test_reconstruccion_usa_precios_al_cierre_del_corte(cfg, red_simulada):
    """Mercados del 24-oct al cierre de ese día (Kalshi 0.80/0.21, Polymarket 0.805/0.195), no los de hoy (~0.84); los
    rangos también. No se escribe en la caché de consultas en vivo."""
    cfg.corte_manual = date(2026, 10, 24)
    mk = mercados.obtener_mercados(cfg)
    k, p = mk['kalshi'], mk['polymarket']
    assert k['estado'] == p['estado'] == 'historico (cierre 2026-10-24)' and k['usable'] and p['usable']
    assert (k['p_d'], k['p_r']) == pytest.approx((0.80, 0.21)) and (p['p_d'], p['p_r']) == pytest.approx((0.805, 0.195))
    assert mk['rangos']['estado'].startswith('historico') and mk['rangos']['n_contratos'] == 10
    assert not (cfg.dir_cache / 'mercado_kalshi.csv').exists()


def test_reconstruccion_no_usa_el_voto_anticipado_de_hoy(cfg, red_simulada):
    """civicAPI publica hoy el acumulado al 28-oct: en una reconstrucción del 24-oct solo vale un snapshot ≤ 24-oct.
    Sin él, «no aplica» (diagnóstico; no cuenta como fuente degradada)."""
    ejecutar(cfg)                                                           # corrida diaria: guarda el snapshot del 28-oct
    cfg.corte_manual = date(2026, 10, 24)
    r = ejecutar(cfg, escribir_salidas=False)
    assert not r['anticipado']['disponible'] and r['estados_fuentes']['civicapi'].startswith('no_aplica')
    assert r['degradadas'] == []


def test_csv_de_encuestas_trae_fechas_de_disponibilidad(cfg, red_simulada):
    ejecutar(cfg)
    e = pd.read_csv(cfg.dir_salidas / 'ultimo' / 'encuestas_gobernador.csv', encoding='utf-8-sig')
    assert {'publicacion', 'tipo_fecha', 'disponible_desde'} <= set(e.columns)
    assert e[(e.pollster == 'Marquette University') & (e.fin == '2026-10-22')].disponible_desde.iloc[0].startswith('2026-10-28')


# ----------------------------------------------------------------------------------- solo dos candidatos (WI)
def test_solo_dos_candidatos_terceros_fijos(cfg, red_simulada):
    """Solo Crowley y Tiffany en la boleta: terceros = votos por escrito fijos (0.10 ± 0.05), sin tercero principal."""
    assert cfg.modelo['terceros_fijos'] == [0.10, 0.05] and 'tercero_principal' not in cfg.modelo
    r = ejecutar(cfg, escribir_salidas=False)
    f = r['modelo']['final']
    assert 'tercero_principal' not in f and 0.05 < f['pct_terceros'] < 0.2


def test_reconstruccion_sin_red_usa_caches_al_corte(cfg, red_simulada):
    """Notebook: reconstrucción sin red del corte del 28-oct con las cachés de esa corrida → mercados y rangos de caché."""
    ejecutar(cfg)                                                          # corrida diaria del 28-oct (guarda cachés)
    red_simulada.caidas.update({'kalshi', 'polymarket', 'civicapi'})
    import wi_pronostico.config as C
    class Manana(C.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 29, 12, 0, tzinfo=tz)
    import pytest as _pt
    mp = _pt.MonkeyPatch(); mp.setattr('wi_pronostico.config.datetime', Manana)
    try:
        cfg.corte_manual = date(2026, 10, 28)
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
    from wi_pronostico import red

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
