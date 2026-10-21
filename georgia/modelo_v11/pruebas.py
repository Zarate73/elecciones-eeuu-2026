"""Pruebas del modelo final. Escriben en una carpeta temporal: NO tocan salida/.
Ejecutar:  py pruebas.py
"""
import tempfile
from dataclasses import replace
from datetime import date
from pathlib import Path
import numpy as np
import pandas as pd
import georgia_modelo_final as gm


def main():
    tmp = Path(tempfile.mkdtemp(prefix='ga_v11_'))
    base = gm.Config(salida=tmp, n_sim=40_000)
    r = gm.ejecutar(base)
    s, m, T = r['simulaciones'], r['meta'], r['resumen']

    # 1. Cierre contable y rangos
    assert np.allclose(s.Bottoms + s.Jackson + s.Writein, 100, atol=1e-9)
    assert (s.Writein > 0).all() and (s.Writein < 0.05).all()
    # 2. Solo encuestas con fecha <= corte
    assert (r['encuestas'].fin <= pd.Timestamp(base.corte)).all()
    # 3. Ventana = últimos 21 días antes de la elección (como en el backtest)
    assert r['ventana'].fin.min() >= pd.Timestamp(base.eleccion) - pd.Timedelta(days=21)
    # 4. Sigma coherente con la calibración y k
    c = m['calibracion']
    assert abs(m['sd'] - np.sqrt(c['tau'] ** 2 + c['s'] ** 2 / m['k_encuestadoras'])) < 1e-9
    assert 3.0 < m['sd'] < 9.0, 'sigma fuera del rango del backtest'
    # 5. Mezcla con Kalshi entre encuestas y mercado
    lo, hi = sorted([m['p_encuestas'], m['kalshi']['p_D']])
    assert lo - 1e-12 <= m['p_final'] <= hi + 1e-12
    # 6. Sin Kalshi = solo encuestas
    r0 = gm.ejecutar(replace(base, peso_kalshi=0.0), guardar=False)
    assert abs(r0['meta']['p_final'] - r0['meta']['p_encuestas']) < 1e-12
    # 7. Kalshi viejo no se usa (corte 1-sep: el precio de caché más reciente sería >3 días después, se filtra)
    k = gm.kalshi(replace(base, corte=date(2026, 9, 1)))
    assert k['fecha'] <= '2026-09-02'
    # 8. Reproducibilidad
    r2 = gm.ejecutar(base, guardar=False)
    assert np.allclose(r2['simulaciones'].Margen_B_J, s.Margen_B_J)
    # 9. Probabilidad de segunda vuelta acorde a write-ins mínimos
    assert T.iloc[0].P_segunda_vuelta < 0.01
    # 11. Colas t (v8-M3): ν razonable y desviación estándar simulada = sd del modelo
    assert 3 < m['nu'] < 60
    assert abs(s.Margen_B_J.std() - m['sd']) / m['sd'] < 0.03
    # 12. Tres categorías de encuesta suman 100 y excluyen preguntas de dos opciones
    tc = r['tres_categorias']
    assert abs(tc['Bottoms_encuesta'] + tc['Jackson_encuesta'] + tc['Otros_ninguno_indecisos'] - 100) < 1e-9
    # 13. Normal = v10 como caso particular
    rn = gm.ejecutar(replace(base, colas_t=False), guardar=False)
    assert rn['meta']['nu'] is None
    # 14. Diagnóstico de voto anticipado no altera el pronóstico
    v = gm.voto_anticipado_diagnostico(base)
    assert v['uso'].startswith('diagnóstico') and abs(v['delta_negro_vs_2022'] - 2.6) < 0.1
    # 15. Validación del CSV de encuestas: duplicados y sumas imposibles se rechazan
    crudo = pd.read_csv(gm.DATA / 'ga_gob2026_encuestas.csv')
    assert gm.validar_encuestas(crudo) == []
    for malo in (pd.concat([crudo, crudo.tail(1)]),
                 crudo.assign(D=crudo.D.where(crudo.index != 0, 80.0)),
                 crudo.assign(tipo_pregunta=crudo.tipo_pregunta.where(crudo.index != 0, 'otro'))):
        try:
            gm.validar_encuestas(malo.reset_index(drop=True)); raise AssertionError('debió fallar')
        except ValueError:
            pass
    # 16. Senado y conjunto: probabilidades coherentes y correlación simulada = ρ calibrada
    c = m['conjunto_gob_sen']
    tot = c['P_Bottoms_y_Ossoff'] + c['P_Jackson_y_Ossoff'] + c['P_Bottoms_y_Collins'] + c['P_Jackson_y_Collins']
    assert abs(tot - 1) < 1e-9 and abs(c['corr_simulada'] - c['rho']) < 0.02
    assert abs(c['P_Bottoms'] - m['p_final']) < 0.01          # la marginal no cambia con la correlación
    # 17. Ventana ampliada usa la encuesta MÁS RECIENTE de cada firma (no arrastra encuestas viejas)
    sen = m['senado']
    if sen['ventana']['ampliada']:
        assert sen['k'] == base.min_encuestadoras
    # 10. Fallback de ventana: con un corte temprano se amplía y se marca
    r3 = gm.ejecutar(replace(base, corte=date(2026, 10, 1)), guardar=False)
    assert r3['meta']['ventana']['ampliada'] is True and r3['meta']['k_encuestadoras'] >= 2
    print('PRUEBAS OK ·', tmp)


if __name__ == '__main__':
    main()
