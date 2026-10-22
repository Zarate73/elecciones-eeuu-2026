"""Corrida completa del pronóstico M5 (y comparación con M1–M4 legados)."""
from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from datetime import date, datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from . import civiq, externas, legado, modelo, reporte, sentimiento_propio
from . import encuestas_web
from .encuestas import cargar_encuestas_base, resumir, resumir_mejorado, tabla_encuestas

log = logging.getLogger(__name__)
__version__ = '1.0.0'


class ErrorFatal(RuntimeError):
    """Error que impide producir un pronóstico (p. ej. ninguna encuesta disponible)."""


@contextmanager
def candado(cfg, max_min: int = 30):
    """Evita dos corridas simultáneas (p. ej. tarea programada + manual)."""
    p = cfg.dir_salidas / '.corriendo.lock'
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists() and (time.time() - p.stat().st_mtime) < max_min * 60:
        raise ErrorFatal(f'Hay otra corrida en curso ({p}). Si no es así, borra el archivo.')
    p.write_text(str(os.getpid()))
    try:
        yield
    finally:
        p.unlink(missing_ok=True)


def fecha_corte(cfg) -> date:
    return cfg.corte_manual or datetime.now(ZoneInfo(cfg.eleccion.zona_horaria)).date()


def ejecutar(cfg) -> dict:
    with candado(cfg):
        return _ejecutar(cfg)


def _ejecutar(cfg) -> dict:
    t0 = time.monotonic()
    corte = fecha_corte(cfg)
    dias = max((cfg.dia_eleccion - corte).days, 0)
    m, e = cfg.modelo, cfg.eleccion
    estados, avisos = {}, []
    log.info('Corte %s · %d días a la elección · offline=%s', corte, dias, cfg.offline)

    # 1) Encuestas: base verificada (Excel local o CSV) + Wikipedia y 270toWin en vivo ----------
    base, ruta_base = [], cfg.ruta('encuestas_base')
    if ruta_base.exists():
        try:
            base, av = cargar_encuestas_base(ruta_base, corte, cfg.rutas.hoja_encuestas, cfg.fecha_primaria)
            avisos += av
        except Exception as exc:
            avisos.append(f'No se pudo leer la base verificada {ruta_base.name}: {exc}')
    else:
        avisos.append(f'No existe la base verificada de encuestas: {ruta_base}')
    web = {'wikipedia': [], '270towin': []}
    if cfg.fuentes.get('encuestas_en_vivo', True):
        web, est = encuestas_web.obtener_web(cfg)
        estados.update(est)
    todas = encuestas_web.combinar(web['wikipedia'], base, web['270towin'])
    posteriores = [x for x in todas if x.fin > corte]
    todas = [x for x in todas if x.fin <= corte]
    if not todas:
        raise ErrorFatal('No hay encuestas (ni base verificada, ni en vivo, ni caché)')
    incluidas = [x for x in todas if m.usar_encuestas_preprimaria or not x.preprimaria]
    if not incluidas:
        raise ErrorFatal('No hay encuestas de elección general antes del corte')
    origenes = pd.Series([x.origen for x in incluidas]).value_counts().to_dict()
    log.info('Encuestas incluidas por origen: %s (posteriores al corte: %d)', origenes, len(posteriores))
    ag_leg = resumir(incluidas, corte, m.vida_media_dias)
    ag = resumir_mejorado(incluidas, corte, m.vida_media_dias, m.penal_interna, m.dias_campo_default)
    tabla_enc = tabla_encuestas(todas, incluidas, ag['pesos']).rename(columns={'Peso': 'Peso M5'})
    tabla_enc['Peso legado'] = tabla_encuestas(todas, incluidas, ag_leg['pesos'])['Peso'].to_numpy()
    log.info('Encuestas: %d · margen legado %+.2f · M5 %+.2f', len(incluidas), ag_leg['margen'], ag['margen'])
    u = max(incluidas, key=lambda x: x.fin)            # fuentes en vivo ≠ encuestas recientes: se reporta su antigüedad
    ultima = {'encuestadora': u.encuestadora, 'fin': u.fin.isoformat(), 'dias_desde_fin': (corte - u.fin).days,
              'dias_antes_eleccion': (cfg.dia_eleccion - u.fin).days, 'origen': u.origen}
    if ultima['dias_desde_fin'] > 7:
        avisos.append(f"la encuesta más reciente terminó hace {ultima['dias_desde_fin']} días ({ultima['fin']})")

    # 2) Voto anticipado ----------------------------------------------------------------
    dato, estados['civiq'] = civiq.obtener_voto_temprano(cfg, corte)
    estados.update({f'civiq_{k}': v for k, v in civiq.actualizar_historia_y_condados(cfg).items()})
    log.info('Civiq: %s', estados['civiq'])
    m2e = civiq.m2_por_edad(dato)
    cal = modelo.calibrar_sigma(cfg)
    cal7 = modelo.calibrar_sigma(cfg, 7)
    m2h = (civiq.m2_historico(cfg, m2e['margen_dr_devueltas_pp'],
                              (cfg.dia_eleccion - date.fromisoformat(dato.fecha_datos)).days,
                              civiq.cargar_historia(cfg), cal7['errores'])
           if dato is not None else {'disponible': False})
    pdi = externas.cargar_pdi(cfg)

    # 3) Sentimiento ---------------------------------------------------------------------
    sentimiento_propio.configurar(cfg)
    sent, _, _ = sentimiento_propio.calcular_senal_sentimiento(cfg.ruta('carpeta_sentimiento'), corte,
                                                              cfg.legado.tasa_shocks_semanal)
    gd_df, estados['gdelt'] = externas.actualizar_gdelt(cfg)
    gd = externas.senal_gdelt(cfg, gd_df, corte)
    k_cand = max(sent.multiplicador_lambda if sent.activa else 1.0,
                 gd.get('k_sent_candidato', 1.0) if gd.get('disponible') else 1.0)
    k_sent = k_cand if m.validado_sentimiento else 1.0

    # 4) Kalshi --------------------------------------------------------------------------
    kal = externas.obtener_kalshi(cfg, corte)
    estados['kalshi'] = kal['estado']

    # 5) M5 ------------------------------------------------------------------------------
    m5 = modelo.pronostico_m5(cfg, ag, dias, cal['sigma_sis_pp'], delta_m2=m2e.get('delta_m2_pp', 0.0),
                              k_sent=k_sent, p_kalshi=kal['p_d_normalizada'] if kal['usable_en_mezcla'] else None)
    sims = {'M5 · híbrido': m5['simulacion']}            # sin desplazamiento por Kalshi (p_final es un ajuste externo)

    # 6) Legado M1–M4 (comparación) -------------------------------------------------------
    if cfg.legado.comparar:
        L = cfg.legado
        senal = (legado.calcular_senal(dato, corte, cfg.dia_eleccion, max_ajuste_margen_pp=L.max_ajuste_participacion_pp,
                                       escala_historica_pp=L.escala_senal_pp, tasa_final_referencia=L.tasa_final_referencia)
                 if dato is not None and dato.estado == 'actualizado'
                 else legado.sin_senal(corte, 'sin dato actualizado', L.max_ajuste_participacion_pp))
        par = legado.ParametrosShocks(L.tasa_shocks_semanal, L.magnitud_shock_sd_pp, L.shock_t_gl)
        s3 = legado.simular_comparativo(ag_leg['margen'], senal.cambio_margen_pp, L.sigma_normal_pp,
                                        m.n_simulaciones, m.semilla, corte, cfg.dia_eleccion, par)
        s4 = legado.simular_comparativo(ag_leg['margen'], senal.cambio_margen_pp, L.sigma_normal_pp,
                                        m.n_simulaciones, m.semilla, corte, cfg.dia_eleccion,
                                        legado.ParametrosShocks(sent.tasa_condicional_semanal, L.magnitud_shock_sd_pp, L.shock_t_gl))
        sims.update({'M1 · encuestas (legado)': s3.referencia, 'M2 · + participación (legado)': s3.participacion,
                     'M3 · + shocks (legado)': s3.con_shocks, 'M4 · + sentimiento (legado)': s4.con_shocks})

    tabla_mod = pd.DataFrame([{'modelo': k, 'mediana_margen_pp': float(np.median(v)),
                               'ic95_inf_pp': float(np.quantile(v, .025)), 'ic95_sup_pp': float(np.quantile(v, .975)),
                               'de_pp': float(np.std(v, ddof=1)), 'p_d_gana': float(np.mean(v > 0))}
                              for k, v in sims.items()])
    tabla_mod['p_final_con_kalshi'] = np.where(tabla_mod.modelo.str.startswith('M5'), m5['p_final'], np.nan)
    tabla_pct = modelo.porcentajes(cfg, {k: v for k, v in sims.items() if k.startswith(('M5', 'M1'))})

    # 7) Reporte -------------------------------------------------------------------------
    pct = tabla_pct[tabla_pct.modelo.str.startswith('M5')].set_index('candidato')
    pd_, pr_ = pct.pronostico_pct.iloc[0], pct.pronostico_pct.iloc[1]
    ahora = datetime.now(ZoneInfo(e.zona_horaria))
    rep = {
        'version': __version__, 'generado': ahora.isoformat(timespec='seconds'), 'fecha_corte': corte.isoformat(),
        'dias_a_eleccion': dias, 'offline': cfg.offline, 'config': str(cfg.archivo),
        'pronostico': {'candidato_d': e.candidato_d, 'candidato_r': e.candidato_r,
                       'pct_d': pd_, 'pct_r': pr_, 'margen_pp': float(np.median(m5['simulacion'])),
                       'ic80_pct_d': [pct.ic80_inf.iloc[0], pct.ic80_sup.iloc[0]],
                       'ic95_pct_d': [pct.ic95_inf.iloc[0], pct.ic95_sup.iloc[0]],
                       'p_d_gana_modelo': m5['p_modelo'], 'p_d_gana_final': m5['p_final']},
        'estados_fuentes': estados,
        'ultima_encuesta': ultima,
        'encuestas': {'n': len(incluidas), 'por_origen': origenes, 'margen_legado_pp': ag_leg['margen'], 'margen_m5_pp': ag['margen'],
                      'dispersion_pp': ag['dispersion_encuestas'], 'n_efectivo': ag['n_efectivo']},
        'voto_temprano': civiq.resumen_participacion(dato) if dato else None,
        'participacion_m2': {'por_edad': m2e, 'historico': m2h, 'w_m2': m.w_m2},
        'pdi_contraste': pdi,
        'sentimiento': {'propio': sent.to_dict(), 'gdelt': gd, 'k_sent_candidato': k_cand,
                        'k_sent_aplicado': k_sent, 'validado': m.validado_sentimiento},
        'kalshi': kal, 'calibracion': cal,
        'm5': {k: v for k, v in m5.items() if not k.startswith('simulacion')},
        'avisos': avisos,
        'duracion_s': round(time.monotonic() - t0, 1),
    }
    res = {'reporte': rep, 'tabla_modelos': tabla_mod, 'tabla_porcentajes': tabla_pct,
           'tabla_encuestas': tabla_enc, 'simulaciones': sims, 'dato_temprano': dato}
    res['resumen_texto'] = resumen_texto(cfg, res)

    carpeta = cfg.dir_salidas / 'corridas' / ahora.strftime('%Y-%m-%d_%H%M%S')
    reporte.escribir_corrida(cfg, carpeta, res)
    reporte.publicar_ultimo(cfg, carpeta)
    reporte.agregar_historial(cfg, {
        'generado': rep['generado'], 'fecha_corte': rep['fecha_corte'], 'dias_a_eleccion': dias,
        f'pct_{e.candidato_d.lower()}': round(pd_, 2), f'pct_{e.candidato_r.lower()}': round(pr_, 2),
        'margen_pp': round(rep['pronostico']['margen_pp'], 2), 'sigma_pp': round(m5['sigma_pp'], 2),
        'p_d_modelo': round(m5['p_modelo'], 4), 'p_d_final': round(m5['p_final'], 4),
        'p_kalshi': round(kal['p_d_normalizada'], 4), 'margen_encuestas_m5': round(ag['margen'], 2),
        'delta_m2_edad': round(m2e.get('delta_m2_pp', np.nan), 2) if m2e.get('disponible') else '',
        'delta_m2_historico': round(m2h.get('delta_vs_referencias_pp', np.nan), 2) if m2h.get('disponible') else '',
        'estado_civiq': estados['civiq'][:80], 'estado_kalshi': kal['estado'][:40], 'estado_gdelt': estados['gdelt'][:40],
        'ultima_encuesta_fin': ultima['fin'], 'dias_desde_ultima_encuesta': ultima['dias_desde_fin'],
        'carpeta': carpeta.name})
    reporte.podar_corridas(cfg)
    res['carpeta'] = carpeta
    log.info('Pronóstico: %s %.1f%% · %s %.1f%% · P(%s)=%.3f · %s', e.candidato_d, pd_, e.candidato_r, pr_,
             e.candidato_d, m5['p_final'], carpeta)
    return res


def resumen_texto(cfg, r: dict) -> str:
    rep, e = r['reporte'], cfg.eleccion
    p, m5 = rep['pronostico'], rep['m5']
    ed, hi = rep['participacion_m2']['por_edad'], rep['participacion_m2']['historico']
    lineas = [
        f"{e.estado} · {e.cargo} · corte {rep['fecha_corte']} ({rep['dias_a_eleccion']} días)",
        '',
        f"PRONÓSTICO M5: {e.candidato_d} {p['pct_d']:.1f}%  ·  {e.candidato_r} {p['pct_r']:.1f}%   (margen {p['margen_pp']:+.1f} pp)",
        f"  IC 80% {e.candidato_d}: {p['ic80_pct_d'][0]:.1f}–{p['ic80_pct_d'][1]:.1f}%   IC 95%: {p['ic95_pct_d'][0]:.1f}–{p['ic95_pct_d'][1]:.1f}%",
        f"  P({e.candidato_d} gana): modelo {p['p_d_gana_modelo']:.3f} · con Kalshi {p['p_d_gana_final']:.3f}",
        f"  Última encuesta: {rep['ultima_encuesta']['encuestadora']}, terminó el {rep['ultima_encuesta']['fin']} "
        f"({rep['ultima_encuesta']['dias_desde_fin']} días antes del corte)",
        f"  σ {m5['sigma_pp']:.2f} pp (sistemático calibrado {rep['calibracion']['sigma_sis_pp']:.2f}; "
        f"RMSE histórico {rep['calibracion']['rmse_historico_pp']:.2f}, n={rep['calibracion']['n_elecciones']})",
        '',
        'FUENTES',
        *[f"  {k}: {v}" for k, v in rep['estados_fuentes'].items()],
        f"  encuestas: {rep['encuestas']['n']} ({', '.join(f'{k} {v}' for k, v in rep['encuestas']['por_origen'].items())}) · margen legado {rep['encuestas']['margen_legado_pp']:+.2f} → M5 {rep['encuestas']['margen_m5_pp']:+.2f}",
        '',
        'PARTICIPACIÓN (diagnóstico; w_m2 = %.2f)' % cfg.modelo.w_m2,
    ]
    if ed.get('disponible'):
        lineas.append(f"  devueltas D−R {ed['margen_dr_devueltas_pp']:+.2f} · esperado por edad "
                      f"{ed['margen_dr_esperado_por_edad_pp']:+.2f} → Δ {ed['delta_m2_pp']:+.2f} pp")
    if hi.get('disponible'):
        refs = ', '.join(f'{k} {v:+.1f}' for k, v in hi['margen_referencias_mismo_dia_pp'].items())
        lineas.append(f"  mismo día (T−{hi['dias_comparados']}): {hi['margen_actual_pp']:+.1f} vs {refs} → Δ {hi['delta_vs_referencias_pp']:+.1f}")
        if 'composicion_final_proyectada_pp' in hi:
            lineas.append(f"  composición final proyectada {hi['composicion_final_proyectada_pp']:+.1f}"
                          + (f" → margen implícito {hi['composicion_a_resultado']['margen_resultado_implicito_pp']:+.1f} pp"
                             f" (RMSE LOO {hi['composicion_a_resultado']['rmse_loo_pp']:.1f})" if 'composicion_a_resultado' in hi else ''))
        if 'correlacion_delta_error' in hi:
            lineas.append(f"  corr(Δ temprano, error de encuestas) = {hi['correlacion_delta_error']:+.2f} (n={len(hi['diagnostico_retrospectivo'])})")
    s = rep['sentimiento']
    lineas += ['', f"SENTIMIENTO: k candidato {s['k_sent_candidato']:.2f} · aplicado {s['k_sent_aplicado']:.2f} · "
                   f"GDELT {s['gdelt'].get('nota', 'z=%.2f' % s['gdelt'].get('z_innovacion', np.nan))}",
               f"KALSHI: {rep['kalshi']['p_d_normalizada']:.3f} ({rep['kalshi']['estado']}) · en mezcla {rep['kalshi']['usable_en_mezcla']}"]
    if rep['pdi_contraste'].get('disponible'):
        q = rep['pdi_contraste']
        lineas.append(f"PDI (contraste, {q['fecha']}): D−R {q['margen_dr_pp']:+.1f} en {q['devueltas']:,} boletas")
    lineas += ['', 'MODELOS', r['tabla_modelos'].round(3).to_string(index=False)]
    if rep['avisos']:
        lineas += ['', 'AVISOS', *[f'  - {a}' for a in rep['avisos']]]
    return '\n'.join(lineas) + '\n'
