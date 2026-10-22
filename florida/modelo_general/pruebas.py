"""Pruebas del modelo final de Florida (sin red). Uso: python pruebas.py  (o python -m pytest pruebas.py)"""
from datetime import date
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

import florida_modelo_final as fm


def _cfg(**kw):
    return fm.Config(salida=Path(tempfile.mkdtemp()), n_sim=40_000, civicapi_en_vivo=False, **kw)


def test_fechas_excel():
    assert fm._fechas_es('05–07 oct 2026') == (date(2026, 10, 5), date(2026, 10, 7))
    assert fm._fechas_es('28 sep–05 oct 2026') == (date(2026, 9, 28), date(2026, 10, 5))
    assert fm._fechas_es('15 mar–13 abr 2026') == (date(2026, 3, 15), date(2026, 4, 13))


def test_excel_lee_las_25_encuestas_sin_el_promedio():
    e = fm.encuestas_excel(fm.DATA / 'FLORIDA_GOBERNADOR-v2.xlsx')
    assert len(e) == 25 and not e.pollster.str.contains('PROME').any()
    assert e.iloc[0].pollster == 'St. Pete Polls' and e.iloc[0].D == 44.6 and e.iloc[0].R == 44.7
    assert e.D.between(30, 60).all() and e.R.between(30, 60).all()


def test_combinar_sin_duplicados():
    p = fm.encuestas_2026(_cfg())
    assert not p.duplicated(['pollster_key', 'fin']).any()
    assert (p.fin > fm.PRIMARIA).all()                         # solo encuestas posteriores a la primaria
    # Univision/YouGov (15-oct, 42/50) es la misma que 270toWin publica como «YouGov» el 19-oct
    yg = p[p.pollster_key == 'yougov']
    assert ((yg.D == 42) & (yg.R == 50)).sum() == 1
    # Mason-Dixon del Excel («— NBC 6 / Telemundo») y de Wikipedia son una sola
    assert (p.pollster_key == 'masondixon').sum() == 1


def test_calibracion_y_sesgo_de_florida():
    par = fm.calibrar(_cfg(), 12, usar_cache=False)
    assert par['n_contiendas'] >= 800 and 2 < par['tau'] < 5 and par['nu'] > 5
    # las encuestas de Florida han sobreestimado al demócrata: sesgo estatal positivo y poco contraído
    assert 3 < par['sesgo_contraido'] <= par['sesgo_bruto'] < 8 and par['contraccion'] > 0.6
    assert any(e['race'] == '2024_Pres-G_FL' for e in par['errores_estado'])


def test_resultado_coherente():
    r = fm.ejecutar(_cfg(), guardar=False)
    f, s = r['resultado'], r['simulacion']
    assert np.allclose(s.Jolly + s.Donalds + s.Terceros, 100)
    assert f['P_Jolly'] == float((s.Margen > 0).mean())                     # probabilidad = fracción simulada
    assert abs(f['P_Jolly'] - f['P_Jolly_mezcla_objetivo']) < 2 / len(s)
    lo, hi = sorted([f['P_Jolly_modelo'], r['mercados']['promedio_D']])
    assert lo - 1e-9 <= f['P_Jolly'] <= hi + 1e-9
    assert r['mu'] < r['margen_encuestas']                                   # el sesgo estatal corrige hacia Donalds


def test_escenarios_sin_sesgo_y_sin_mercados():
    a = fm.ejecutar(_cfg(peso_mercados=0.0), guardar=False)
    assert a['resultado']['desplazamiento_mercados_pp'] == 0
    b = fm.ejecutar(_cfg(sesgo_estatal=False), guardar=False)
    assert b['mu'] == b['margen_encuestas'] and b['resultado']['P_Jolly'] > a['resultado']['P_Jolly']


def test_voto_anticipado_snapshot():
    va = fm.voto_anticipado_civicapi(_cfg())
    assert va['disponible'] and va['fecha'] == '2026-10-22' and va['emitidos'] == va['por_correo'] + va['en_persona']
    assert abs(va['pct_D'] + va['pct_R'] + va['pct_NPA'] + va['pct_Otros'] - 100) < 1e-9
    assert va['margen_DR_correo_pp'] > 0 > va['margen_DR_persona_pp']      # D vota por correo, R en persona
    assert len(va['condados']) == 67


def test_salidas_se_escriben():
    cfg = _cfg()
    fm.ejecutar(cfg, guardar=True)
    for f in ('pronostico_gobernador.csv', 'resumen_escenarios.csv', 'encuestas_2026_combinadas.csv',
              'encuestas_ventana_pesos.csv', 'metadatos.json', 'errores_historicos_FL.csv',
              'voto_anticipado_condados_civicapi.csv'):
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
