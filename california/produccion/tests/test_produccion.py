import json
import numpy as np
import pandas as pd
import pytest

from ca_pronostico import civiq, externas, modelo
from ca_pronostico.config import cargar_config
from ca_pronostico.pipeline import ejecutar


# ------------------------------------------------------------------ configuración
def test_config_valida():
    c = cargar_config()
    assert c.dia_eleccion.isoformat() == '2026-11-03'
    assert 0 <= c.modelo.w_kalshi <= 1


def test_config_invalida(tmp_path):
    txt = (cargar_config().archivo).read_text(encoding='utf-8').replace('w_kalshi = 0.30', 'w_kalshi = 1.7')
    p = tmp_path / 'malo.toml'
    p.write_text(txt, encoding='utf-8')
    with pytest.raises(ValueError, match='w_kalshi'):
        cargar_config(p)


# ------------------------------------------------------------------ Civiq API
def test_civiq_api_construye_voto_temprano(cfg, red_simulada):
    d = civiq.voto_temprano_desde_api(cfg)
    assert d.origen == 'api'
    assert d.registrados == d.registro_dem + d.registro_rep + d.registro_otro
    assert d.devueltas == d.devueltas_dem + d.devueltas_rep + d.devueltas_otro
    assert sum(d.devueltas_edad.values()) == d.devueltas
    assert d.registro_dem == 10_395_709          # coincide con el tablero
    assert d.fecha_datos == '2026-10-19'


def test_civiq_historia_siete_elecciones(cfg, red_simulada):
    import json
    from tests.conftest import FIX
    h = civiq.historia_desde_api(json.loads((FIX / 'civiq_historical_elections.json').read_text()))
    assert h.eleccion.nunique() == 7
    fin22 = h[(h.eleccion == '2022 General') & (h.dias_antes_eleccion == -1)].iloc[0]
    assert abs(fin22.dem_pct - 49.0) < 0.1 and abs(fin22.rep_pct - 28.8) < 0.1   # tabla de finales del tablero


def test_civiq_sin_red_usa_cache(cfg, red_simulada):
    d, _ = civiq.obtener_voto_temprano(cfg, pd.Timestamp('2026-10-19').date())
    assert d.estado == 'actualizado'
    cfg.offline = True
    d2, estado = civiq.obtener_voto_temprano(cfg, pd.Timestamp('2026-10-19').date())
    assert d2.estado == 'cache_desactualizado' and 'caché' in estado


def test_m2_por_edad_signo(cfg, red_simulada):
    d = civiq.voto_temprano_desde_api(cfg)
    m = civiq.m2_por_edad(d)
    assert m['disponible']
    # 57% de devoluciones de +65 (más R que el promedio): el esperado por edad es menor que el registro
    assert m['margen_dr_esperado_por_edad_pp'] < m['margen_dr_registro_pp']


# ------------------------------------------------------------------ modelo
def _agregado(m=18.7):
    return {'margen': m, 'dispersion_encuestas': 7.7, 'n_efectivo': 7.0}


def test_m5_varianza_y_identidades(cfg):
    r = modelo.pronostico_m5(cfg, _agregado(), 15, 6.0)
    assert abs(r['sigma_pp'] ** 2 - sum(r['componentes_varianza_pp2'].values())) < 1e-9
    assert r['media_pp'] == 18.7                       # w_m2 = 0 => media = encuestas
    assert abs(np.std(r['simulacion']) / r['sigma_pp'] - 1) < 0.03
    assert r['p_final'] == r['p_modelo']               # sin Kalshi
    r2 = modelo.pronostico_m5(cfg, _agregado(), 15, 6.0, k_sent=9)
    assert r2['k_sent_aplicado'] == cfg.modelo.k_sent_max


def test_kalshi_mueve_hacia_el_mercado(cfg):
    a = modelo.pronostico_m5(cfg, _agregado(), 15, 6.0)
    b = modelo.pronostico_m5(cfg, _agregado(), 15, 6.0, p_kalshi=0.90)
    assert b['p_final'] < a['p_modelo']


def test_kalshi_ajusta_solo_la_probabilidad_y_desplazamiento_opcional(cfg):
    """California: por defecto Kalshi ajusta solo la probabilidad publicada (la simulación no se mueve);
    con trasladar_mercado_a_distribucion = true la simulación se desplaza y queda coherente con p_final."""
    b = modelo.pronostico_m5(cfg, _agregado(), 15, 6.0, p_kalshi=0.90)
    assert b['desplazamiento_kalshi_pp'] == 0 and np.array_equal(b['simulacion'], b['simulacion_modelo'])
    assert b['p_final'] == b['p_mezcla_objetivo'] < b['p_modelo'] == float(np.mean(b['simulacion'] > 0))
    cfg.modelo['trasladar_mercado_a_distribucion'] = True
    c = modelo.pronostico_m5(cfg, _agregado(), 15, 6.0, p_kalshi=0.90)
    assert c['p_final'] == float(np.mean(c['simulacion'] > 0))
    assert c['p_final'] == pytest.approx(c['p_mezcla_objetivo'], abs=2 / len(c['simulacion']))
    assert c['desplazamiento_kalshi_pp'] < 0

def test_porcentajes_suman_100(cfg):
    sim = modelo.pronostico_m5(cfg, _agregado(), 15, 6.0)['simulacion']
    t = modelo.porcentajes(cfg, {'M5': sim})
    assert abs(t.pronostico_pct.sum() - 100) < 1e-6
    assert abs(t.p_ganar.sum() - 1) < 1e-6


def test_calibracion_sigma(cfg):
    c = modelo.calibrar_sigma(cfg)
    assert c['n_elecciones'] >= 4 and 5 < c['rmse_historico_pp'] < 9
    assert c['sigma_sis_pp'] >= cfg.modelo.sigma_sis_min_pp


def test_conteo_corrimiento_primaria(cfg):
    assert modelo.corrimiento_tardio_primaria(cfg) < 0             # tardías menos R
    r = modelo.proyectar_conteo(cfg, 3_000_000, 2_400_000, 5_000_000)
    assert r['margen_proyectado_mediana_pp'] > r['margen_actual_pp']


# ------------------------------------------------------------------ fuentes externas
def test_kalshi_en_vivo_y_respaldo(cfg, red_simulada):
    hoy = pd.Timestamp('2026-10-19').date()
    k = externas.obtener_kalshi(cfg, hoy)
    assert k['estado'] == 'en_vivo' and 0.95 < k['p_d_normalizada'] < 0.96
    cfg.offline = True
    k2 = externas.obtener_kalshi(cfg, hoy)
    assert k2['estado'].startswith('cache_snapshot')


def test_kalshi_apagado_en_conteo(cfg, red_simulada):
    cfg.ejecucion['modo_conteo'] = True
    assert not externas.obtener_kalshi(cfg, pd.Timestamp('2026-10-19').date())['usable_en_mezcla']


def test_gdelt_cache_y_senal(cfg, red_simulada):
    df, estado = externas.actualizar_gdelt(cfg)
    assert estado == 'en_vivo' and set(df.candidato) == {'BECERRA', 'HILTON'}
    n = len(red_simulada)
    _, estado2 = externas.actualizar_gdelt(cfg)
    assert estado2.startswith('cache') and len(red_simulada) == n       # no reconsulta
    s = externas.senal_gdelt(cfg, df, pd.Timestamp('2026-10-19').date())
    assert s['disponible'] and 1 <= s['k_sent_candidato'] <= cfg.modelo.k_sent_max


# ------------------------------------------------------------------ punta a punta
def test_corrida_completa(cfg, red_simulada):
    cfg.fuentes['encuestas_en_vivo'] = False            # solo la base verificada = notebook M5
    r = ejecutar(cfg)
    p = r['reporte']['pronostico']
    assert abs(p['pct_d'] + p['pct_r'] - 100) < 1e-6
    assert 55 < p['pct_d'] < 65                                       # sanidad con datos del 19-oct
    assert r['reporte']['encuestas']['margen_m5_pp'] == pytest.approx(18.73, abs=0.05)   # = notebook M5
    assert r['reporte']['estados_fuentes']['kalshi'] == 'en_vivo'
    assert (cfg.dir_salidas / 'ultimo' / 'reporte.json').exists()
    assert (cfg.dir_salidas / 'historial_pronosticos.csv').exists()
    assert r['reporte']['participacion_m2']['historico']['disponible']
    txt = (cfg.dir_salidas / 'ultimo' / 'reporte.json').read_text(encoding='utf-8')
    def prohibido(c):
        raise ValueError(f'constante no estándar en JSON: {c}')
    rep = json.loads(txt, parse_constant=prohibido)                 # JSON estricto: sin NaN ni Infinity
    assert rep['ultima_encuesta']['dias_desde_fin'] >= 0 and rep['ultima_encuesta']['fin'] <= rep['fecha_corte']
    tm = r['tabla_modelos'].set_index('modelo')                    # la fila M5 es la del modelo (sin Kalshi)
    assert tm.loc['M5 · híbrido', 'p_d_gana'] == pytest.approx(p['p_d_gana_modelo'], abs=1e-12)


def test_corrida_offline_sin_cache_no_falla(cfg):
    cfg.offline = True
    r = ejecutar(cfg)
    assert r['reporte']['voto_temprano'] is None
    assert r['reporte']['kalshi']['estado'].startswith('cache_historico')


# ------------------------------------------------------------------ encuestas en vivo
def test_base_csv_igual_al_excel(cfg):
    from tests.conftest import EXCEL
    from ca_pronostico.encuestas import cargar_encuestas_base
    if not EXCEL.exists():
        pytest.skip('Excel local no disponible (repositorio público: solo el CSV exportado)')
    a, _ = cargar_encuestas_base(cfg.ruta('encuestas_base'), cfg.corte_manual, cfg.rutas.hoja_encuestas, cfg.fecha_primaria)
    b, _ = cargar_encuestas_base(EXCEL, cfg.corte_manual, cfg.rutas.hoja_encuestas, cfg.fecha_primaria)
    assert [(x.encuestadora, x.fin, x.becerra, x.hilton) for x in a] == [(x.encuestadora, x.fin, x.becerra, x.hilton) for x in b]


def test_paginas_reales_y_combinacion(cfg, red_simulada):
    from ca_pronostico import encuestas_web as W
    from ca_pronostico.encuestas import cargar_encuestas_base
    web, est = W.obtener_web(cfg)
    assert est == {'encuestas_wikipedia': 'en_vivo', 'encuestas_270towin': 'en_vivo'}
    assert len(web['wikipedia']) >= 12 and len(web['270towin']) >= 15
    assert all(e.encuestadora for e in web['270towin'])                  # Source con colspan=2
    base, _ = cargar_encuestas_base(cfg.ruta('encuestas_base'), cfg.dia_eleccion, cfg.rutas.hoja_encuestas, cfg.fecha_primaria)
    todas = [e for e in W.combinar(web['wikipedia'], base, web['270towin']) if not e.preprimaria]
    claves = [(e.familia, e.fin) for e in todas]
    assert len(claves) == len(set(claves))
    # nada se repite: misma familia a <= 7 días
    for i, a in enumerate(todas):
        for b in todas[i + 1:]:
            assert not (a.familia == b.familia and abs((a.fin - b.fin).days) <= 7), (a.encuestadora, b.encuestadora)
    nombres = ' | '.join(e.encuestadora for e in todas)
    assert 'Manhattan Institute' in nombres and 'ActiVote' in nombres     # nuevas, solo en vivo
    assert 'Wolfson' in nombres                                           # solo en la base verificada
    assert not any(e.becerra < 40 for e in todas)                         # sin encuestas de primaria
    mi = next(e for e in todas if 'Manhattan' in e.encuestadora)
    assert mi.encargada_campania and mi.origen == 'wikipedia'             # (R) => peso interno


def test_corrida_con_encuestas_en_vivo(cfg, red_simulada):
    r = ejecutar(cfg)
    enc = r['reporte']['encuestas']
    assert enc['por_origen'].get('wikipedia', 0) >= 8 and enc['por_origen'].get('base', 0) >= 1
    assert r['reporte']['estados_fuentes']['encuestas_wikipedia'] == 'en_vivo'
    assert 10 < enc['margen_m5_pp'] < 25


def test_encuesta_de_primaria_aislada(cfg, red_simulada):
    """Berkeley IGS 29-may 25–21 (270toWin) es la primaria del 2-jun: se aísla antes de combinar y queda registrada aparte;
    la general de Berkeley IGS del 19–24 may (52–31) se conserva (revisión del 26-oct)."""
    from ca_pronostico import encuestas_web as W
    web, _ = W.obtener_web(cfg)
    bk = [(e.origen, str(e.fin), e.becerra, e.hilton) for e in web['wikipedia'] + web['270towin'] if e.familia.startswith('Berkeley IGS')]
    assert ('270towin', '2026-05-29', 25.0, 21.0) not in bk and ('wikipedia', '2026-05-24', 52.0, 31.0) in bk
    x = pd.read_csv(cfg.dir_salidas / 'encuestas_excluidas.csv')
    assert len(x) == 1 and x.clave_538.iloc[0] == 'berkeleyigs' and x.razon.iloc[0].startswith('Primaria')
