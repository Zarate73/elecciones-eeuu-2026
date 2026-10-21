"""Línea de comandos.

  python -m az_pronostico correr                     # corrida normal (todas las fuentes en vivo)
  python -m az_pronostico correr --offline           # solo cachés
  python -m az_pronostico correr --corte 2026-10-21  # fecha de corte explícita
  python -m az_pronostico encuestas                  # muestra las encuestas combinadas (en vivo)
  python -m az_pronostico verificar                  # revisa config, dependencias y cada fuente en vivo

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
    for ruidoso in ('urllib3', 'matplotlib', 'PIL'):
        logging.getLogger(ruidoso).setLevel(logging.WARNING)


def _cmd_correr(a) -> int:
    from .pipeline import ErrorFatal, ejecutar
    cfg = cargar_config(a.config, offline=a.offline, corte=a.corte)
    if a.sin_graficas:
        cfg.ejecucion['graficas'] = False
    _logging(cfg, a.verboso)
    log = logging.getLogger('az_pronostico')
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


def _cmd_encuestas(a) -> int:
    import pandas as pd
    from .encuestas import obtener_encuestas
    cfg = cargar_config(a.config, offline=a.offline, corte=a.corte)
    _logging(cfg, False)
    pd.set_option('display.width', 220); pd.set_option('display.max_rows', 200)
    r = obtener_encuestas(cfg)
    print(f"\nFuentes: {r['estados']}")
    print(r['encuestas'][['fin', 'pollster', 'clave', 'pop', 'n', 'D', 'R', 'otros', 'origen', 'tambien_en']].to_string(index=False))
    for x in r['avisos']:
        print('  -', x)
    return 0


def _cmd_verificar(a) -> int:
    cfg = cargar_config(a.config)
    _logging(cfg, False)
    ok = True
    for mod in ('numpy', 'pandas', 'scipy', 'matplotlib', 'requests', 'lxml', 'bs4', 'openpyxl'):
        try:
            __import__(mod); print(f'OK    módulo {mod}')
        except ImportError:
            print(f'FALTA módulo {mod}'); ok = False
    rb = cfg.ruta_encuestas_base
    if rb is not None:
        print(f"{'OK   ' if rb.exists() else 'AVISO'} base verificada: {rb}")
    print('\nProbando fuentes en vivo (puede tardar ~1 min)...')
    from .anticipado import obtener_anticipado
    from .encuestas import obtener_encuestas
    from .historico import obtener_raw_polls
    from .mercados import obtener_mercados
    try:
        raw, est, _ = obtener_raw_polls(cfg)
        print(f'{"OK   " if est == "en_vivo" else "AVISO"} FiveThirtyEight raw-polls: {est} ({len(raw)} filas)')
    except Exception as exc:
        print(f'ERROR FiveThirtyEight: {exc}'); ok = False
    try:
        r = obtener_encuestas(cfg)
        for k, v in r['estados'].items():
            print(f'{"OK   " if str(v).startswith(("en_vivo", "archivo")) else "AVISO"} {k}: {v}')
        print(f"      -> {len(r['encuestas'])} encuestas tras combinar")
    except Exception as exc:
        print(f'ERROR encuestas: {exc}'); ok = False
    mk = obtener_mercados(cfg)
    for nom in ('kalshi', 'polymarket'):
        x = mk[nom]
        print(f'{"OK   " if x["estado"] == "en_vivo" else "AVISO"} {nom}: {x["estado"]} {x.get("p_D", "")}')
    print(f'{"OK   " if mk["rangos"]["estado"] == "en_vivo" else "AVISO"} polymarket rangos: {mk["rangos"]["estado"]}')
    c = obtener_anticipado(cfg)
    print(f'{"OK   " if c["estado"] == "en_vivo" else "AVISO"} civicAPI: {c["estado"]}')
    print(f'\nConfig: {cfg.archivo} · elección {cfg.dia_eleccion} · corte {cfg.corte}')
    return 0 if ok else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog='az_pronostico', description='pronóstico Arizona Gobernador 2026')
    p.add_argument('--config', default=None, help='ruta a un .toml (por defecto config/arizona.toml)')
    sub = p.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('correr', help='ejecuta el pronóstico')
    c.add_argument('--offline', action='store_true', help='no consulta fuentes en vivo (usa cachés)')
    c.add_argument('--corte', help='fecha de corte YYYY-MM-DD (por defecto hoy, hora de Arizona)')
    c.add_argument('--sin-graficas', action='store_true')
    c.add_argument('--estricto', action='store_true', help='código 2 si alguna fuente no está en vivo')
    c.add_argument('-v', '--verboso', action='store_true')
    c.set_defaults(f=_cmd_correr)
    e = sub.add_parser('encuestas', help='muestra las encuestas combinadas que usaría el modelo')
    e.add_argument('--offline', action='store_true'); e.add_argument('--corte')
    e.set_defaults(f=_cmd_encuestas)
    v = sub.add_parser('verificar', help='revisa configuración, dependencias y fuentes en vivo')
    v.set_defaults(f=_cmd_verificar)
    a = p.parse_args(argv)
    return a.f(a)


if __name__ == '__main__':
    sys.exit(main())
