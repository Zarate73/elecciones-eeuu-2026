"""Orquestación de una corrida: fuentes en vivo -> calibración -> modelo -> salidas."""
from __future__ import annotations

import logging

import numpy as np

from .anticipado import obtener_anticipado
from .anticipado_nyc import obtener_nyc
from .encuestas import obtener_encuestas
from .historico import calibrar
from .mercados import obtener_mercados
from .modelo import pronosticar
from .reporte import escribir, texto_resumen

log = logging.getLogger(__name__)


class ErrorFatal(RuntimeError):
    pass


def ultima_encuesta(p, cfg) -> dict:
    """Antigüedad de la observación más reciente: que las fuentes se consulten en vivo no implica encuestas recientes."""
    u = p.loc[p.fin.idxmax()]
    fin = u.fin.date()
    return {'encuestadora': str(u.pollster), 'fin': fin.isoformat(), 'dias_desde_fin': (cfg.corte - fin).days,
            'dias_antes_eleccion': (cfg.dia_eleccion - fin).days, 'origen': str(u.origen)}


def vivo(estado) -> bool:
    return str(estado).startswith(('en_vivo', 'archivo'))


def ejecutar(cfg, escribir_salidas: bool = True) -> dict:
    log.info('Corte %s · %d días a la elección · offline=%s', cfg.corte, cfg.dias_a_eleccion, cfg.offline)
    if cfg.dias_a_eleccion < 0:
        raise ErrorFatal('El corte es posterior a la elección')
    estados, avisos = {}, []
    h = int(np.clip(cfg.dias_a_eleccion, 0, 21))              # horizonte calibrado (días a la elección)
    par = calibrar(cfg, h)
    estados['historico_538'] = par['estado_fuente']
    try:
        e = obtener_encuestas(cfg)
    except ValueError as exc:
        raise ErrorFatal(f'Encuestas inválidas: {exc}') from exc
    estados.update(e['estados']); avisos += e['avisos']
    if e['encuestas'].empty:
        raise ErrorFatal('No hay encuestas posteriores a la primaria')
    mk = obtener_mercados(cfg)
    estados['kalshi'] = mk['kalshi']['estado']
    estados['polymarket'] = mk['polymarket']['estado']
    estados['polymarket_rangos'] = mk['rangos']['estado']
    for nom in ('kalshi', 'polymarket'):
        if 'p_D' in mk[nom] and not mk[nom]['usable']:
            avisos.append(f"{nom}: precio de {mk[nom]['fecha']} demasiado viejo; fuera de la mezcla")
    if mk['n_usables'] == 0:
        avisos.append('ningún mercado usable: pronóstico solo con encuestas')
    r = pronosticar(e['encuestas'], par, mk, cfg)
    ult = ultima_encuesta(e['encuestas'], cfg)
    if ult['dias_desde_fin'] > 7:
        avisos.append(f"la encuesta más reciente terminó hace {ult['dias_desde_fin']} días ({ult['fin']})")
    ant = obtener_anticipado(cfg)
    if not ant.get('disponible') and cfg.fuentes.get('civicapi_opcional', False):
        # Nueva York: civicAPI no publica voto anticipado de NY (404). Es diagnóstico con peso 0: se avisa, pero no cuenta
        # como fuente degradada ni hace fallar --estricto
        avisos.append(f"civicAPI sin datos de {cfg.eleccion.abrev} (diagnóstico opcional): {ant['estado'][:80]}")
        # en su lugar: check-ins de voto anticipado de la Junta Electoral de NYC (solo la ciudad), también diagnóstico
        if cfg.fuentes.get('nyc_voto_anticipado_url'):
            ant = obtener_nyc(cfg)
            estados['nyc_boe'] = ant['estado']
    else:
        estados['civicapi'] = ant['estado']
    degradadas = [k for k, v in estados.items() if not vivo(v)]
    res = {'modelo': r, 'mercados': mk, 'anticipado': ant, 'calibracion': par, 'estados_fuentes': estados,
           'avisos': avisos, 'degradadas': degradadas, 'conteos': e['conteos'], 'ultima_encuesta': ult}
    res['resumen_texto'] = texto_resumen(res, cfg)
    if escribir_salidas:
        res['carpeta'] = escribir(res, cfg)
    f = r['final']
    log.info('Pronóstico: %s %.1f%% · %s %.1f%% · terceros %.1f%% · P(%s)=%.3f', cfg.eleccion.candidato_d, f['pct_D'],
             cfg.eleccion.candidato_r, f['pct_R'], f['pct_terceros'], cfg.eleccion.candidato_d, f['P_D'])
    return res
