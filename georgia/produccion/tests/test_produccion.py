from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ga_pronostico import encuestas as enc
from ga_pronostico.pipeline import ErrorFatal, ejecutar
from ga_pronostico.historico import calibrar
from ga_pronostico.modelo import estimar_carrera, pronosticar
from tests.conftest import FIX


# ---------------------------------------------------------------- parsers
@pytest.mark.parametrize('txt,esperado', [
    ('October 12–13, 2026', (date(2026, 10, 12), date(2026, 10, 13))),
    ('July 29 – August 1, 2026', (date(2026, 7, 29), date(2026, 8, 1))),
    ('Sept. 14, 2026', (date(2026, 9, 14), date(2026, 9, 14))),
    ('10/14/2026', (date(2026, 10, 14), date(2026, 10, 14))),
    ('December 28 – January 3, 2027', (date(2026, 12, 28), date(2027, 1, 3))),
])
def test_fechas(txt, esperado):
    assert enc.parse_fechas(txt, 2026) == esperado


def test_muestra_y_numeros():
    assert enc.parse_muestra('1,200 (LV)') == (1200.0, 'LV')
    assert enc.parse_muestra('3,414 (RV)') == (3414.0, 'RV')
    assert enc.a_numero('49.5%') == 49.5 and enc.a_numero('<1%') == 0.5 and np.isnan(enc.a_numero('–'))


def test_wikipedia_gob_descarta_hipoteticas_y_agregadores():
    import json
    html = json.loads((FIX / 'wikipedia_gob.json').read_text())['parse']['text']
    df = enc.parse_tabla_wikipedia(html, 'Bottoms', 'Jackson', 2026)
    assert len(df) == 18                                     # filas del cuadro principal (con versiones)
    assert not df.pollster.str.contains('270toWin').any()     # agregador fuera
    assert set(df.clave_538) >= {'insideradvanta', 'yougov', 'bigdatapoll', 'rasmussenrepor'}
    yg = df[df.clave_538 == 'yougov']
    assert len(yg) == 3 and set(yg.fin) == {date(2026, 9, 18)}  # rowspan heredado


def test_versiones_lv_y_sin_leaners():
    import json
    html = json.loads((FIX / 'wikipedia_gob.json').read_text())['parse']['text']
    df = enc.elegir_versiones(enc.parse_tabla_wikipedia(html, 'Bottoms', 'Jackson', 2026))
    yg = df[df.clave_538 == 'yougov'].iloc[0]
    assert (yg['pop'], yg.n, yg.D, yg.R) == ('LV', 3299, 44, 46)
    sn = df[df.clave_538 == 'statenavigate'].iloc[0]
    assert (sn.D, sn.R) == (50, 43)                            # versión sin leaners (más indecisos)
    bd = df[df.clave_538 == 'bigdatapoll'].iloc[0]
    assert bd['pop'] == 'LV' and bd.tipo_pregunta == 'reasignacion'


@pytest.mark.skipif(not (FIX / 'gratings_georgia.xlsx').exists(), reason='Excel propio no publicado')
def test_gratings_excel(cfg):
    g = enc.parse_gratings(FIX / 'gratings_georgia.xlsx', cfg)
    assert (g['gob'].iloc[0].D, g['gob'].iloc[0].R) == (45.3, 47.5)
    assert (g['sen'].iloc[0].D, g['sen'].iloc[0].R) == (50.5, 41.4)
    assert g['gob'].iloc[0].fin == date(2026, 9, 29) and g['gob'].iloc[0]['pop'] == 'RV'


def test_combinacion_y_ajustes(cfg, red_simulada):
    r = enc.obtener_encuestas(cfg, 'gob')
    e = r['encuestas']
    assert e.fin.min() >= cfg.fecha_nominacion and e.fin.max() <= cfg.corte
    assert not e.duplicated(['clave_538', 'fin']).any()
    bd = e[e.clave_538 == 'bigdatapoll'].iloc[0]
    assert (bd.D, bd.R) == (46.7, 48.8) and bd.origen == 'ajuste:reemplazar'
    uga = e[e.clave_538 == 'universityofge'].iloc[0]                 # 270toWin -> versión verificada
    assert uga.fin == date(2026, 10, 15) and uga.origen == 'ajuste:agregar'
    qu = e[(e.clave_538 == 'quantusinsight') & (e.fin > date(2026, 10, 1))].iloc[0]
    assert (qu.D, qu.R) == (46.6, 48.2)
    assert 'gratings' in set(e.clave_538)
    assert len(e) == 15                                               # mismas 15 encuestas que V11
    assert all(str(v).startswith(('en_vivo', 'archivo')) for v in r['estados'].values())


def test_validacion_rechaza_errores():
    base = pd.DataFrame([{'pollster': 'X', 'clave_538': 'x', 'inicio': date(2026, 10, 1), 'fin': date(2026, 10, 2),
                          'n': 800, 'pop': 'LV', 'D': 60, 'R': 50, 'tipo_pregunta': 'general'}])
    with pytest.raises(ValueError):
        enc.validar(base)


def test_equivalencia_v11(cfg, red_simulada):
    """Con las encuestas del CSV de V11 y Kalshi 0.495/0.515, el pronóstico coincide con V11 (−1.42, 0.389)."""
    par = calibrar(cfg)
    df = pd.read_csv(FIX / 'v11_gob2026.csv', parse_dates=['inicio', 'fin'])
    df['fin'] = df.fin.dt.date; df['inicio'] = df.inicio.dt.date
    gob = estimar_carrera(df, cfg, par)
    kal = {'p_d_normalizada': 0.495 / (0.495 + 0.515), 'usable_en_mezcla': True}
    pr = pronosticar(gob, kal, cfg, par)
    assert abs(gob['mu'] - (-1.956)) < 0.02 and gob['k'] == 3
    assert abs(pr['final']['mu_final'] - (-1.42)) < 0.02
    assert abs(pr['final']['p_D_final'] - 0.389) < 0.003
    assert abs(par['tau'] - 3.25) < 0.06 and abs(par['s'] - 7.5) < 0.15 and abs(par['nu'] - 11.8) < 0.3


def test_corrida_completa(cfg, red_simulada):
    r = ejecutar(cfg)
    f = r['gobernador']['final']
    assert abs(f['pct_D'] + f['pct_R'] - 100) < 0.05
    assert 0.33 < f['P_D'] < 0.45 and f['P_segunda_vuelta'] < 0.01
    assert r['senado']['senado']['P_D'] > 0.8
    c = r['senado']['conjunto']
    assert abs(sum(c[k] for k in c if k.startswith('P_') and '_y_' in k) - 1) < 1e-9
    assert r['degradadas'] == []
    for arch in ('resumen.txt', 'reporte.json', 'pronostico_gobernador.csv', 'encuestas_gobernador.csv',
                 'senado_y_conjunto.csv', 'voto_anticipado_diagnostico.csv'):
        assert (cfg.dir_salidas / 'ultimo' / arch).exists()
    ant = r['anticipado']
    assert abs(ant['delta_vs_2022']['pct_negro'] - 2.6) < 0.1
    import json
    def prohibido(c):
        raise ValueError(f'constante no estándar en JSON: {c}')
    rep = json.loads((cfg.dir_salidas / 'ultimo' / 'reporte.json').read_text(encoding='utf-8'), parse_constant=prohibido)
    u = rep['ultima_encuesta']
    assert u['fin'] <= rep['corte'] and u['dias_desde_fin'] >= 0
    # la probabilidad publicada sale de la misma simulación que margen e intervalos (margen equivalente con Kalshi)
    M = r['gobernador']['sim'][0]
    assert f['P_D'] == pytest.approx(float(np.mean(M > 0)), abs=1e-3)
    assert f['P_D'] == pytest.approx(f['p_D_final'], abs=0.01)


def test_fuentes_caidas_usan_cache(cfg, red_simulada):
    ejecutar(cfg)                                    # llena cachés
    cfg.offline = True
    r = ejecutar(cfg)
    # sin red: todo sale de caché; Kalshi puede quedar fuera si su copia es posterior al corte fijo de la prueba
    assert r['degradadas'] and all(str(r['estados_fuentes'][k]).startswith(('cache', 'no_disponible')) for k in r['degradadas'])
    assert all(str(r['estados_fuentes'][k]).startswith('cache') for k in r['degradadas'] if k != 'kalshi')
    assert len(r['gobernador']['encuestas']) == 15


def test_sin_nada_es_error_fatal(cfg):
    cfg.offline = True
    cfg.rutas['encuestas_propias'] = ''
    with pytest.raises(ErrorFatal):
        ejecutar(cfg)


def test_270towin_real_lee_firma_de_source_colspan():
    """Página real (21-oct-2026): 'Source' tiene colspan=2 (logo vacío + nombre). Antes salía NaN -> 'desconocida'."""
    from ga_pronostico import encuestas as E
    al = pd.read_csv(Path(__file__).parents[1] / 'data' / 'alias_encuestadoras.csv')
    for k, (d, r) in {'gob': ('Bottoms', 'Jackson'), 'sen': ('Ossoff', 'Collins')}.items():
        html = (Path(__file__).parent / 'fixtures' / 'reales' / f't270_{k}_2026-10-21.html').read_text(encoding='utf-8')
        df = E.parse_tabla_270(html, d, r, 2026, al)
        assert len(df) >= 8
        assert df.pollster.str.len().gt(0).all()
        assert not (df.clave_538 == 'desconocida').any()
        assert not df.pollster.str.contains('Average', case=False).any()
    uga = E.parse_tabla_270((Path(__file__).parent / 'fixtures' / 'reales' / 't270_gob_2026-10-21.html').read_text(encoding='utf-8'),
                            'Bottoms', 'Jackson', 2026, al)
    assert (uga.clave_538 == 'universityofge').sum() >= 1


def test_combinar_mismas_cifras_con_fecha_de_publicacion():
    from ga_pronostico import encuestas as E
    from datetime import date
    base = dict(inicio=date(2026, 7, 29), n=815.0, pop='LV', otros=0.0, indecisos=9.0, tipo_pregunta='', fuente='', nota='')
    w = pd.DataFrame([dict(base, pollster='Quantus Insights (R)', clave_538='quantusinsight', fin=date(2026, 8, 1), D=46.0, R=45.0, origen='wikipedia')])
    t = pd.DataFrame([dict(base, pollster='Quantus Insights', clave_538='quantusinsight', fin=date(2026, 8, 10), D=46.0, R=45.0, origen='270towin'),
                      dict(base, pollster='Quantus Insights', clave_538='quantusinsight', fin=date(2026, 8, 20), D=44.0, R=47.0, origen='270towin')])
    out = E.combinar(w, t)
    assert len(out) == 2                                   # la de mismas cifras a 9 días se descarta; la distinta a 19 días no
    assert set(out.origen) == {'wikipedia', '270towin'}


def test_cache_vieja_sin_firma_no_tumba_la_corrida(tmp_path):
    from types import SimpleNamespace
    from ga_pronostico import encuestas as E
    cfg = SimpleNamespace(dir_cache=tmp_path)
    pd.DataFrame({'pollster': [np.nan, 'UGA'], 'clave_538': ['desconocida', 'universityofge'],
                  'inicio': ['2026-10-07'] * 2, 'fin': ['2026-10-15'] * 2, 'n': [1000, 1000], 'pop': ['LV'] * 2,
                  'D': [45, 45], 'R': [46, 46]}).to_csv(tmp_path / 'encuestas_gob_270towin.csv', index=False)
    def falla():
        raise ConnectionError('sin red')
    df, estado = E._con_cache(cfg, 'gob_270towin', falla)
    assert estado.startswith('cache') and list(df.pollster) == ['UGA']
