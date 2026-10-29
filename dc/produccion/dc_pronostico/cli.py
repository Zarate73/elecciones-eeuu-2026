"""Línea de comandos.

  python -m dc_pronostico correr                     # corrida normal (todas las fuentes en vivo)
  python -m dc_pronostico correr --offline           # solo cachés
  python -m dc_pronostico correr --corte 2026-10-25  # fecha de corte explícita
  python -m dc_pronostico historico                  # muestra las 13 generales 1974–2022 (en vivo) y el backtest LOYO
  python -m dc_pronostico verificar                  # revisa config, dependencias y cada fuente en vivo

Códigos de salida: 0 = OK · 1 = error fatal · 2 = OK pero con fuentes degradadas (--estricto)
"""
from __future__ import annotations

import argparse
import logging
import sys
from logging.handlers import RotatingFileHandler

from .config import cargar_config


def _logging(cfg, verboso: bool) -> None:
    d = cfg.ruta('logs')
    d.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter('%(asctime)s %(levelname)-7s %(name)s: %(message)s', '%Y-%m-%d %H:%M:%S')
    raiz = logging.getLogger()
    raiz.handlers.clear()
    raiz.setLevel(logging.DEBUG if verboso else logging.INFO)
    fh = RotatingFileHandler(d / 'pronostico.log', maxBytes=5_000_000, backupCount=5, encoding='utf-8')
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    raiz.addHandler(fh); raiz.addHandler(sh)
    for ruidoso in ('urllib3', 'matplotlib', 'PIL', 'pypdf'):
        logging.getLogger(ruidoso).setLevel(logging.WARNING)


def _cmd_correr(a) -> int:
    from .pipeline import ErrorFatal, ejecutar
    cfg = cargar_config(a.config, offline=a.offline, corte=a.corte)
    if a.sin_graficas:
        cfg.ejecucion['graficas'] = False
    _logging(cfg, a.verboso)
    log = logging.getLogger('dc_pronostico')
    try:
        r = ejecutar(cfg)
    except ErrorFatal as exc:
        log.error('ERROR FATAL: %s', exc)
        return 1
    except Exception:
        log.exception('Error no controlado')
        return 1
    print('\n' + r['resumen_texto'])
    if r['degradadas']:
        log.warning('Fuentes NO en vivo: %s', ', '.join(r['degradadas']))
        return 2 if a.estricto else 0
    return 0


def _cmd_historico(a) -> int:
    import pandas as pd
    from .historico import obtener_historico
    from .modelo import loyo
    cfg = cargar_config(a.config, offline=a.offline)
    _logging(cfg, False)
    pd.set_option('display.width', 220)
    h = obtener_historico(cfg)
    t = h['tabla']
    print(f"\nFuente: {h['estado']}")
    print(t[['anio', 'nominado', 'pct_d', 'opositor', 'pct_op', 'pct_verde', 'pct_escrito', 'primaria_pct', 'fuerte',
             'titular', 'origen']].round(2).to_string(index=False))
    for v in (['fuerte'], ['fuerte', 'titular'], ['fuerte', 'primaria'], ['fuerte', 'tendencia'], []):
        r = loyo(t, v)
        print(f"LOYO {'+'.join(v) or 'media':22s} CRPS {r['crps']:.3f} · MAE {r['mae']:.2f} · cobertura IC80 {r['cobertura80']:.0%}")
    return 0


def _cmd_verificar(a) -> int:
    cfg = cargar_config(a.config)
    _logging(cfg, False)
    ok = True
    for mod in ('numpy', 'pandas', 'scipy', 'matplotlib', 'requests', 'lxml', 'bs4', 'pypdf'):
        try:
            __import__(mod); print(f'OK    módulo {mod}')
        except ImportError:
            print(f'FALTA módulo {mod}'); ok = False
    print('\nProbando fuentes en vivo (puede tardar ~1 min)...')
    from .eleccion2026 import obtener_eleccion
    from .historico import obtener_historico
    from .mercados import obtener_mercados
    from .registro import obtener_registro
    try:
        h = obtener_historico(cfg)
        print(f"{'OK   ' if h['estado'].startswith('en_vivo') else 'AVISO'} Wikipedia histórico: {h['estado']}")
    except Exception as exc:                                       # noqa: BLE001
        print(f'ERROR Wikipedia histórico: {exc}'); ok = False
    el = obtener_eleccion(cfg)
    print(f"{'OK   ' if el['estado'] == 'en_vivo' else 'AVISO'} Wikipedia 2026: {el['estado']} · boleta "
          f"{[c['candidato'] for c in el['boleta'].get('candidatos', [])]} · {len(el['encuestas'])} encuestas de la general · "
          f"primaria {el.get('primaria_pct')}")
    for x in el['boleta'].get('avisos', []):
        print('      -', x)
    mk = obtener_mercados(cfg)
    for nom in ('kalshi', 'polymarket'):
        x = mk[nom]
        print(f"{'OK   ' if x['estado'].startswith(('en_vivo', 'no_aplica')) else 'AVISO'} {nom}: {x['estado']} {x.get('p_D', '')}")
    reg = obtener_registro(cfg)
    print(f"{'OK   ' if reg['estado'] == 'en_vivo' else 'AVISO'} DCBOE registro: {reg['estado']} {reg.get('fecha_informe', '')} "
          f"{reg.get('total', '')}")
    print(f'\nConfig: {cfg.archivo} · elección {cfg.dia_eleccion} · corte {cfg.corte}')
    return 0 if ok else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog='dc_pronostico', description='pronóstico Washington D.C. Alcaldía 2026')
    p.add_argument('--config', default=None, help='ruta a un .toml (por defecto config/dc.toml)')
    sub = p.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('correr', help='ejecuta el pronóstico')
    c.add_argument('--offline', action='store_true', help='no consulta fuentes en vivo (usa cachés)')
    c.add_argument('--corte', help='fecha de corte YYYY-MM-DD (por defecto hoy, hora del Este)')
    c.add_argument('--sin-graficas', action='store_true')
    c.add_argument('--estricto', action='store_true', help='código 2 si alguna fuente no está en vivo')
    c.add_argument('-v', '--verboso', action='store_true')
    c.set_defaults(f=_cmd_correr)
    e = sub.add_parser('historico', help='muestra las generales 1974–2022 y el backtest LOYO')
    e.add_argument('--offline', action='store_true')
    e.set_defaults(f=_cmd_historico)
    v = sub.add_parser('verificar', help='revisa configuración, dependencias y fuentes en vivo')
    v.set_defaults(f=_cmd_verificar)
    a = p.parse_args(argv)
    return a.f(a)


if __name__ == '__main__':
    sys.exit(main())
