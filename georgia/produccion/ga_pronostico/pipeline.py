"""Orquestación de una corrida: fuentes en vivo -> calibración -> modelo -> salidas."""
from __future__ import annotations

import logging

import pandas as pd

from . import encuestas as enc
from .externas import obtener_anticipado, obtener_kalshi
from .historico import calibrar
from .modelo import estimar_carrera, pronosticar, senado_conjunto
from .reporte import escribir, texto_resumen

log = logging.getLogger(__name__)


class ErrorFatal(RuntimeError):
    pass


def _vivo(estado) -> bool:
    return str(estado).startswith(('en_vivo', 'archivo'))


def ejecutar(cfg, escribir_salidas: bool = True) -> dict:
    log.info('Corte %s · %d días a la elección · offline=%s', cfg.corte, cfg.dias_a_eleccion, cfg.offline)
    if cfg.dias_a_eleccion < 0:
        raise ErrorFatal('El corte es posterior a la elección')
    estados, avisos = {}, []
    par = calibrar(cfg)
    estados['historico_538'] = par['estado_fuente']
    # ---- gobernador (principal)
    try:
        eg = enc.obtener_encuestas(cfg, 'gob')
    except ValueError as exc:
        raise ErrorFatal(f'Encuestas de gobernador inválidas: {exc}') from exc
    estados.update(eg['estados']); avisos += [f'gob: {a}' for a in eg['avisos']]
    if eg['encuestas'].empty:
        raise ErrorFatal('No hay encuestas de gobernador (ni en vivo ni en caché)')
    gob = estimar_carrera(eg['encuestas'], cfg, par)
    kal = obtener_kalshi(cfg)
    estados['kalshi'] = kal['estado']
    pr = pronosticar(gob, kal, cfg, par)
    gob.update(pr)
    # ---- senado (adicional)
    sen = None
    if cfg.senado.activar:
        try:
            es = enc.obtener_encuestas(cfg, 'sen')
            estados.update(es['estados']); avisos += [f'sen: {a}' for a in es['avisos']]
            if len(es['encuestas']):
                carrera = estimar_carrera(es['encuestas'], cfg, par)
                sen = senado_conjunto(pr['final']['mu_final'], gob['dist'], carrera, cfg)
                sen['carrera'] = carrera
                sen['senado'].update({'k': carrera['k'], 'ventana': carrera['nota_ventana'], 'mu_encuestas': carrera['mu']})
        except Exception as exc:                     # el senado nunca detiene el pronóstico de gobernador
            avisos.append(f'senado omitido: {type(exc).__name__}: {exc}')
    # ---- diagnóstico de voto anticipado
    ant = obtener_anticipado(cfg)
    estados['civicforge'] = ant['estado']
    degradadas = [k for k, v in estados.items() if not _vivo(v)]
    r = {'gobernador': gob, 'senado': sen, 'kalshi': kal, 'anticipado': ant, 'calibracion': par,
         'estados_fuentes': estados, 'avisos': avisos, 'degradadas': degradadas,
         'ajustes_encuestas': eg['ajustes']}
    p_g = gob['encuestas']
    u = p_g.loc[pd.to_datetime(p_g.fin).idxmax()]
    fin_u = pd.Timestamp(u.fin).date()
    ultima = {'encuestadora': str(u.pollster), 'fin': fin_u.isoformat(), 'dias_desde_fin': (cfg.corte - fin_u).days,
              'dias_antes_eleccion': (cfg.dia_eleccion - fin_u).days, 'origen': str(u.origen)}
    if ultima['dias_desde_fin'] > 7:
        avisos.append(f"la encuesta más reciente terminó hace {ultima['dias_desde_fin']} días ({ultima['fin']})")
    r['reporte'] = {'ultima_encuesta': ultima,
        'corte': str(cfg.corte), 'dias_a_eleccion': cfg.dias_a_eleccion, 'estados_fuentes': estados, 'avisos': avisos,
        'gobernador': {**gob['final'], 'k': gob['k'], 'ventana': gob['nota_ventana'],
                       'margen_corregido_encuestas': gob['margen_corregido'], 'tres_categorias': gob['tres_categorias'],
                       'n_encuestas': len(gob['encuestas'])},
        'escenarios': gob['escenarios'],
        'senado': ({**sen['senado'], 'conjunto': sen['conjunto']} if sen else None),
        'kalshi': kal, 'anticipado': {k: v for k, v in ant.items() if k != 'tabla'},
        'calibracion': {k: v for k, v in par.items() if k not in ('efectos_casa', 'errores_estado')},
        'ajustes_encuestas': eg['ajustes']}
    r['resumen_texto'] = texto_resumen(r, cfg)
    if escribir_salidas:
        r['carpeta'] = escribir(r, cfg)
    f = gob['final']
    log.info('Pronóstico: %s %.1f%% · %s %.1f%% · P(%s)=%.3f', cfg.eleccion.candidato_d, f['pct_D'],
             cfg.eleccion.candidato_r, f['pct_R'], cfg.eleccion.candidato_d, f['P_D'])
    return r
