"""Pruebas del modelo final de Arizona (sin red). Uso: python pruebas.py  (o python -m pytest pruebas.py)"""
from datetime import date
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

import arizona_modelo_final as am


def _cfg(**kw):
    return am.Config(salida=Path(tempfile.mkdtemp()), n_sim=40_000, **kw)


def test_fechas_excel():
    assert am._fechas_es('30 sep–05 oct 2026') == (date(2026, 9, 30), date(2026, 10, 5))
    assert am._fechas_es('01–09 sep 2026') == (date(2026, 9, 1), date(2026, 9, 9))
    assert am._fechas_es('18 ago–04 sep 2026') == (date(2026, 8, 18), date(2026, 9, 4))


def test_excel_lee_las_23_encuestas_generales():
    e = am.encuestas_excel(am.DATA / 'ARIZONA_GOBERNADOR-v1.xlsx')
    assert len(e) == 23 and (pd.to_datetime(e.fin) >= '2026-07-22').sum() == 12 and e.D.between(35, 60).all() and e.R.between(30, 55).all()
    assert e.iloc[0].pollster.startswith('GQR') and e.iloc[0].D == 49 and e.iloc[0].R == 45


def test_combinar_sin_duplicados_ni_falsos_duplicados():
    p = am.encuestas_2026(_cfg())
    assert not p.duplicated(['pollster_key', 'fin']).any()
    # GQR (sep–oct) y GrayHouse (ago) coinciden en 49/45 y n=600: NO son la misma encuesta
    assert {'gqr', 'grayhouse'} <= set(p.pollster_key)
    assert (p.pollster_key == 'grayhouse').sum() == 2
    # AARP = Fabrizio/Impact; BSP = ASU: una sola fila cada una
    assert (p.pollster_key == 'fabrizioward').sum() == 1 and (p.pollster_key == 'arizonastateun').sum() == 1
    # todas las del Excel quedaron emparejadas o incorporadas
    assert len(p) == 15


def test_ventana_desplazada_y_literal():
    cfg = _cfg()
    p = am.encuestas_2026(cfg)
    q, nota = am.seleccionar_ventana(p, cfg)
    assert nota['ampliada'] and nota['regla'] == 'desplazada' and q.pollster_key.nunique() == 4
    q2, n2 = am.seleccionar_ventana(p, cfg, regla='v11')
    assert q2.pollster_key.nunique() == 2


def test_calibracion_razonable():
    par = am.calibrar(_cfg(), 13, usar_cache=False)
    assert par['n_contiendas'] >= 750
    assert 2 < par['tau'] < 5 and 5 < par['s'] < 10 and par['nu'] > 5
    assert 1 < par['terceros_a'] < 3 and 0.4 < par['terceros_c'] < 0.9


def test_resultado_consistente():
    r = am.ejecutar(_cfg(), guardar=False)
    f, s = r['resultado'], r['simulacion']
    assert np.allclose(s.Hobbs + s.Biggs + s.Terceros, 100)
    assert (s.Terceros >= 0.1 - 1e-9).all()
    assert 0 < f['P_recuento'] < 0.1
    # la mezcla con mercados queda entre el modelo y el promedio de mercados
    lo, hi = sorted([f['P_Hobbs_modelo'], r['mercados']['promedio_D']])
    assert lo - 1e-9 <= f['P_Hobbs'] <= hi + 1e-9
    assert abs(f['margen_media'] - f['desplazamiento_mercados_pp'] - r['mu']) < 0.15
    # P publicada = fracción de simulaciones con margen > 0 (distribución coherente con la mezcla de mercados)
    assert f['P_Hobbs'] == float((s.Margen > 0).mean())
    assert abs(f['P_Hobbs'] - f['P_Hobbs_mezcla_objetivo']) < 2 / len(s)


def test_sin_mercados_y_sesgo_estatal():
    a = am.ejecutar(_cfg(peso_mercados=0.0), guardar=False)['resultado']
    assert a['P_Hobbs'] == a['P_Hobbs_modelo']
    b = am.ejecutar(_cfg(sesgo_estatal=True), guardar=False)
    assert b['mu'] < b['margen_encuestas']          # el sesgo AZ histórico es pro-D: corrige hacia Biggs


def test_voto_anticipado_civicapi_snapshot():
    va = am.voto_anticipado_civicapi(_cfg(civicapi_en_vivo=False))
    assert va['disponible'] and va['fecha'] == '2026-10-21' and va['devueltas'] == 642253
    assert abs(va['pct_dev_D'] + va['pct_dev_R'] + va['pct_dev_otros'] - 100) < 1e-9
    assert len(va['condados']) == 15 and va['condados'].iloc[0].condado == 'Maricopa'
    assert va['condados'].devueltas.sum() == va['devueltas']


def test_escenario_partidista_no_toca_el_pronostico():
    assert am.lado_partidista('Wick (R)') == 'R' and am.lado_partidista('GQR (D)') == 'D'
    assert am.lado_partidista('Fabrizio Ward (R)/ Impact Research (D)') is None and am.lado_partidista('HighGround') is None
    ep = am.efectos_partidistas()
    assert ep['D'] > 0 > ep['R']                       # patrocinio D infla el margen D; patrocinio R lo reduce
    r = am.ejecutar(_cfg(), guardar=False)
    e = r['escenarios'].set_index('escenario')
    fila = [i for i in e.index if i.startswith('Ajuste partidista')]
    assert len(fila) == 1 and e.loc[fila[0], 'margen_media'] > r['mu']   # en la ventana actual dominan patrocinios R
    assert r['resultado']['margen_media'] == e.iloc[0]['margen_media']    # el FINAL no usa el ajuste


def test_salidas_se_escriben():
    cfg = _cfg()
    am.ejecutar(cfg, guardar=True)
    for f in ('voto_anticipado_condados_civicapi.csv', 'resumen_escenarios.csv', 'encuestas_2026_combinadas.csv', 'encuestas_ventana_pesos.csv',
              'pronostico_gobernador.csv', 'metadatos.json', 'errores_historicos_AZ.csv'):
        assert (cfg.salida / f).exists(), f
    t = pd.read_csv(cfg.salida / 'pronostico_gobernador.csv')
    assert abs(t.pct.sum() - 100) < 0.05


if __name__ == '__main__':
    import sys
    fallos = 0
    for nombre, fn in list(globals().items()):
        if nombre.startswith('test_'):
            try:
                fn(); print('OK  ', nombre)
            except Exception as ex:                        # noqa: BLE001
                fallos += 1; print('FALLA', nombre, type(ex).__name__, ex)
    print('PRUEBAS OK' if not fallos else f'{fallos} FALLAS'); sys.exit(1 if fallos else 0)
