"""Orquestación de una corrida: fuentes en vivo -> fundamentales -> encuestas (si hay) -> RCV -> mercados -> salidas."""
from __future__ import annotations

import logging

from .eleccion2026 import obtener_eleccion
from .encuestas import combinar, complementarias, promedio
from .historico import obtener_historico
from .mercados import obtener_mercados
from .modelo import pronosticar
from .registro import obtener_registro
from .reporte import escribir, texto_resumen

log = logging.getLogger(__name__)


class ErrorFatal(RuntimeError):
    pass


def vivo(estado) -> bool:
    return str(estado).startswith(('en_vivo', 'no_aplica'))


def ejecutar(cfg, escribir_salidas: bool = True) -> dict:
    log.info('Corte %s · %d días a la elección · offline=%s · reconstrucción=%s', cfg.corte, cfg.dias_a_eleccion,
             cfg.offline, cfg.es_reconstruccion)
    if cfg.dias_a_eleccion < 0:
        raise ErrorFatal('El corte es posterior a la elección')
    estados, avisos = {}, []
    try:
        hist = obtener_historico(cfg)
    except Exception as exc:                                        # noqa: BLE001
        raise ErrorFatal(f'Histórico de alcaldías: {exc}') from exc
    estados['wikipedia_historico'] = hist['estado']
    el = obtener_eleccion(cfg)
    estados['wikipedia_2026'] = el['estado']
    avisos += el['boleta'].get('avisos', [])
    if el['boleta'].get('con_resultados'):
        avisos.append('Wikipedia ya publica votos de la general: el pronóstico queda como referencia')
    enc = combinar(el['encuestas'], complementarias(cfg))
    prom = promedio(enc, cfg)
    estados['encuestas_general'] = (f"en_vivo ({prom['n_encuestas']} encuestas)" if prom else
                                    'no_aplica (no hay encuestas de la general)')
    if prom is None:
        avisos.append('sin encuestas de la general: pronóstico solo con fundamentales históricos')
    mk = obtener_mercados(cfg)
    estados['kalshi'] = mk['kalshi']['estado']
    estados['polymarket'] = mk['polymarket']['estado']
    reg = obtener_registro(cfg)
    estados['dcboe_registro'] = reg['estado']
    r = pronosticar(hist, el, prom, mk, cfg)
    degradadas = [k for k, v in estados.items() if not vivo(v)]
    if cfg.es_reconstruccion:
        avisos.insert(0, f'RECONSTRUCCIÓN del corte {cfg.corte} (corrida del {cfg.hoy}): solo encuestas publicadas al corte')
    res = {'modelo': r, 'historico': hist['tabla'], 'eleccion': el, 'encuestas': enc, 'promedio_encuestas': prom,
           'mercados': mk, 'registro': reg, 'estados_fuentes': estados, 'avisos': avisos, 'degradadas': degradadas}
    res['resumen_texto'] = texto_resumen(res, cfg)
    if escribir_salidas:
        res['carpeta'] = escribir(res, cfg)
    f = r['final']
    log.info('Pronóstico: %s %.1f%% · %s %.1f%% · P(%s)=%.4f · P(1.ª ronda)=%.4f', cfg.eleccion.candidato_d, f['pct_D'],
             cfg.eleccion.opositor, f['pct_opositor'], cfg.eleccion.candidato_d, f['P_D'], f['P_primera_ronda'])
    return res
