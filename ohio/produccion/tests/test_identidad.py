"""Pruebas sintéticas de identidad de encuestas (auditoría T3, 26-oct-2026). Idénticas en los diez paquetes."""
import hashlib
import importlib
from pathlib import Path

import pandas as pd

PKG = 'oh_pronostico'
I = importlib.import_module(f'{PKG}.identidad')
COLS = ['pollster', 'clave', 'inicio', 'fin', 'n', 'pop', 'D', 'R', 'otros', 'indecisos', 'origen']
HUELLA = 'f3b1c60409286168e5f3a6104e773d3f'          # md5 de identidad.py: el módulo debe ser el mismo en los diez paquetes


def fila(pollster, clave, inicio, fin, D, R, origen='wikipedia', n=1000.0, pop='LV'):
    return dict(pollster=pollster, clave=clave, inicio=pd.Timestamp(inicio).date(), fin=pd.Timestamp(fin).date(),
                n=n, pop=pop, D=D, R=R, otros=float('nan'), indecisos=float('nan'), origen=origen)


def comb(*fuentes):
    return I.combinar_df(*[pd.DataFrame(f, columns=COLS) for f in fuentes], cols=COLS)


def estudios(out):
    return sorted(zip(out.clave, out.inicio.astype(str), out.fin.astype(str)))


def test_modulo_identico_en_los_diez_paquetes():
    assert hashlib.md5(Path(I.__file__).read_bytes()).hexdigest() == HUELLA


def test_dos_olas_a_pocos_dias_con_mismas_cifras_son_dos():
    w = [fila('Emerson', 'emerson', '2026-10-20', '2026-10-22', 48, 50), fila('Emerson', 'emerson', '2026-10-25', '2026-10-27', 48, 50)]
    assert len(comb(w)) == 2


def test_dos_olas_a_semanas_con_mismas_cifras_son_dos():
    w = [fila('Emerson', 'emerson', '2026-09-01', '2026-09-03', 48, 50)]
    t = [fila('Emerson', 'emerson', '2026-10-10', '2026-10-12', 48, 50, origen='base')]
    assert len(comb(w, t)) == 2


def test_misma_ola_en_wikipedia_y_270towin_es_una_y_conserva_el_campo():
    w = [fila('Emerson College', 'emerson', '2026-10-17', '2026-10-19', 45, 49)]
    t = [fila('Emerson College', 'emerson', '2026-10-22', '2026-10-22', 47, 51, origen='270towin')]   # con indecisos asignados
    out = comb(w, t)
    assert estudios(out) == [('emerson', '2026-10-17', '2026-10-19')] and out.tambien_en.iloc[0] == '270towin'


def test_version_lv_y_rv_de_la_misma_muestra_es_una_y_gana_lv():
    w = [fila('F&M', 'fm', '2026-10-07', '2026-10-18', 52, 30, pop='RV', n=808.0)]
    t = [fila('F&M', 'fm', '2026-10-22', '2026-10-22', 54, 31, origen='270towin', pop='LV', n=433.0)]
    out = comb(w, t)
    assert len(out) == 1 and out['pop'].iloc[0] == 'LV' and out.D.iloc[0] == 54
    assert estudios(out) == [('fm', '2026-10-07', '2026-10-18')]


def test_base_sin_poblacion_no_cede_sus_decimales():
    b = [dict(fila('HighGround', 'highground', '2026-08-15', '2026-08-18', 49.5, 34.3, origen='base'), pop=float('nan'))]
    t = [fila('HighGround', 'highground', '2026-08-25', '2026-08-25', 50, 34, origen='270towin')]
    out = comb(b, t)
    assert len(out) == 1 and (out.D.iloc[0], out.R.iloc[0]) == (49.5, 34.3)


def test_periodos_solapados_en_la_misma_fuente_con_margenes_distintos_no_se_funden():
    w = [fila('X', 'x', '2026-10-01', '2026-10-05', 50, 40), fila('X', 'x', '2026-10-03', '2026-10-06', 44, 48)]
    out = comb(w)
    assert len(out) == 2 and any(d['razon'].startswith('ambigua') for d in out.attrs['decisiones'])


def test_complementaria_verificada_conserva_identidad_y_decimales():
    # OnMessage NY: 1–6 oct 50–46 (Wikipedia) y 12–14 oct 50.3–45.9 (complementaria), ambas n = 1,000 LV
    w = [fila('OnMessage', 'onmessage', '2026-10-01', '2026-10-06', 50, 46)]
    c = [fila('OnMessage', 'onmessage', '2026-10-12', '2026-10-14', 50.3, 45.9, origen='complementaria')]
    t = [fila('OnMessage', 'onmessage', '2026-10-16', '2026-10-16', 50, 46, origen='270towin')]
    out = comb(w, c, t)
    assert estudios(out) == [('onmessage', '2026-10-01', '2026-10-06'), ('onmessage', '2026-10-12', '2026-10-14')]
    oct12 = out[out.inicio.astype(str) == '2026-10-12'].iloc[0]
    assert (oct12.D, oct12.R) == (50.3, 45.9) and oct12.tambien_en == '270towin'    # la más cercana


def test_decimales_de_la_base_verificada_mandan_sobre_el_redondeo():
    w = [fila('St. Pete Polls', 'stpete', '2026-10-05', '2026-10-07', 45, 45)]
    b = [dict(fila('St. Pete Polls', 'stpete', '2026-10-05', '2026-10-07', 44.6, 44.7, origen='base'), pop=float('nan'))]
    out = comb(w, b)
    assert len(out) == 1 and (out.D.iloc[0], out.R.iloc[0]) == (44.6, 44.7)


def test_yougov_generico_es_el_patrocinador_pero_dos_firmas_reales_no():
    w = [fila('CBS/YouGov', 'cbsnews', '2026-10-13', '2026-10-16', 47, 50, n=1492.0)]
    t = [fila('YouGov', 'yougov', '2026-10-18', '2026-10-18', 47, 50, origen='270towin', n=1460.0)]
    assert len(comb(w, t)) == 1
    g = [fila('GQR (D)', 'gqr', '2026-09-30', '2026-10-05', 49, 45, n=600.0),
         fila('GrayHouse (R)', 'grayhouse', '2026-10-01', '2026-10-05', 49, 45, n=600.0, origen='base')]
    assert len(comb(g[:1], g[1:])) == 2                  # mismas cifras y mismo n, pero firmas distintas


def test_resultado_independiente_del_orden_de_las_fuentes():
    w = [fila('ActiVote', 'activote', '2026-09-30', '2026-10-14', 49, 51, n=400.0),
         fila('ActiVote', 'activote', '2026-10-17', '2026-10-21', 48, 53, n=400.0),
         fila('Quantus', 'quantus', '2026-10-15', '2026-10-17', 47, 48, n=755.0)]
    t = [fila('ActiVote', 'activote', '2026-10-15', '2026-10-15', 49, 51, origen='270towin', n=400.0),
         fila('ActiVote', 'activote', '2026-10-21', '2026-10-21', 48, 53, origen='270towin', n=400.0),
         fila('Quantus', 'quantus', '2026-10-19', '2026-10-19', 48, 49, origen='270towin', n=755.0)]
    a, b = comb(w, t), comb(t, w)
    assert estudios(a) == estudios(b) == [('activote', '2026-09-30', '2026-10-14'), ('activote', '2026-10-17', '2026-10-21'),
                                          ('quantus', '2026-10-15', '2026-10-17')]


def test_publicacion_en_ventana_con_cifras_incompatibles_se_conserva_y_se_registra():
    w = [fila('X', 'x', '2026-10-01', '2026-10-05', 50, 40)]
    t = [fila('X', 'x', '2026-10-08', '2026-10-08', 44, 48, origen='270towin', n=700.0)]
    out = comb(w, t)
    assert len(out) == 2 and any(d['razon'].startswith('ambigua') for d in out.attrs['decisiones'])


def test_publicacion_fuera_de_ventana_es_otra_ola():
    w = [fila('Quantus', 'quantus', '2026-07-29', '2026-08-01', 46, 45, n=815.0)]
    t = [fila('Quantus', 'quantus', '2026-08-20', '2026-08-20', 44, 47, origen='270towin', n=815.0)]
    assert len(comb(w, t)) == 2


def test_fecha_mal_capturada_solo_con_mismas_cifras_y_mismo_n():
    w = [fila('Arizona State University', 'asu', '2026-08-18', '2026-09-04', 47, 34, pop='RV', n=1300.0)]
    t_mismo = [fila('BSP Research', 'asu', '2026-10-19', '2026-10-19', 47, 34, origen='270towin', pop='RV', n=1300.0)]
    t_otro = [fila('BSP Research', 'asu', '2026-10-19', '2026-10-19', 47, 34, origen='270towin', pop='RV', n=900.0)]
    assert estudios(comb(w, t_mismo)) == [('asu', '2026-08-18', '2026-09-04')]
    assert len(comb(w, t_otro)) == 2


def test_periodo_invertido_por_error_de_captura():
    w = [fila('Grassroots', 'grassroots', '2026-07-08', '2026-07-06', 40, 52, n=600.0)]
    b = [fila('Grassroots', 'grassroots', '2026-07-08', '2026-07-16', 40, 52, origen='base', n=600.0)]
    assert len(comb(w, b)) == 1


def test_elige_la_ola_mas_cercana_no_la_primera():
    w = [fila('Beacon/Shaw', 'beacon', '2026-09-24', '2026-09-28', 47, 52, n=1005.0),
         fila('Beacon/Shaw', 'beacon', '2026-10-15', '2026-10-19', 47, 52, n=1398.0)]
    t = [fila('Fox News', 'beacon', '2026-10-21', '2026-10-21', 47, 52, origen='270towin', n=1398.0)]
    out = comb(w, t)
    assert len(out) == 2
    assert out.set_index(out.inicio.astype(str)).loc['2026-10-15', 'tambien_en'] == '270towin'


def test_metadatos_insuficientes_no_pierden_la_observacion():
    w = [fila('Y', 'y', '2026-10-10', '2026-10-12', 50, 45)]
    t = [dict(fila('Y', 'y', '2026-10-30', '2026-10-30', 51, 44, origen='270towin'), n=float('nan'), pop=float('nan'))]
    assert len(comb(w, t)) == 2                            # 18 días después del cierre: otra encuesta, no se descarta


def test_mismo_periodo_en_la_misma_fuente_es_un_estudio_aunque_difiera_el_margen():
    # revisión del 26-oct: Marist RV 53–42 y LV 52–45 del mismo campo (Δ margen 4 pp) en la misma fuente; antes quedaban
    # dos filas con la misma llave (firma, inicio, fin) y la validación de duplicados detenía la corrida
    w = [fila('Marist', 'marist', '2026-10-01', '2026-10-04', 53, 42, pop='RV', n=1361.0),
         fila('Marist', 'marist', '2026-10-01', '2026-10-04', 52, 45, pop='LV', n=1100.0)]
    out = comb(w)
    assert len(out) == 1 and out['pop'].iloc[0] == 'LV' and (out.D.iloc[0], out.R.iloc[0]) == (52, 45)
    assert not out.duplicated(['clave', 'inicio', 'fin']).any()
    assert any('mismo periodo' in d['razon'] for d in out.attrs['decisiones'])


def test_mismo_periodo_desde_base_verificada_no_detiene_la_corrida():
    b = [fila('Siena', 'siena', '2026-09-11', '2026-09-17', 50, 41, origen='base', pop='RV'),
         fila('Siena', 'siena', '2026-09-11', '2026-09-17', 51, 37, origen='base', pop='LV')]
    out = comb(b)
    assert len(out) == 1 and out['pop'].iloc[0] == 'LV'
