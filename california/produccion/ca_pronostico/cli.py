"""Línea de comandos.

  python -m ca_pronostico correr                     # corrida normal (fuentes en vivo)
  python -m ca_pronostico correr --offline           # solo cachés
  python -m ca_pronostico correr --corte 2026-10-15  # reproducir un corte
  python -m ca_pronostico correr --modo-conteo       # noche electoral (apaga Kalshi)
  python -m ca_pronostico conteo --votos-d 3000000 --votos-r 2400000 --restantes 5000000
  python -m ca_pronostico verificar                  # revisa config, rutas y dependencias

Códigos de salida: 0 = OK · 1 = error fatal · 2 = OK pero con fuentes degradadas (--estricto)
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
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
    raiz.addHandler(fh)
    raiz.addHandler(sh)
    for ruidoso in ('urllib3', 'matplotlib', 'PIL'):
        logging.getLogger(ruidoso).setLevel(logging.WARNING)


def _cmd_correr(a) -> int:
    from .pipeline import ErrorFatal, ejecutar
    cfg = cargar_config(a.config, offline=a.offline, corte=a.corte, modo_conteo=a.modo_conteo or None)
    if a.sin_graficas:
        cfg.ejecucion['graficas'] = False
    _logging(cfg, a.verboso)
    log = logging.getLogger('ca_pronostico')
    try:
        r = ejecutar(cfg)
    except ErrorFatal as exc:
        log.error('ERROR FATAL: %s', exc)
        return 1
    except Exception:
        log.exception('Error no controlado')
        return 1
    print('\n' + r['resumen_texto'])
    degradadas = [k for k, v in r['reporte']['estados_fuentes'].items()
                  if not str(v).startswith(('api_en_vivo', 'en_vivo', 'Datos de Civiq'))]
    if degradadas:
        log.warning('Fuentes degradadas: %s', ', '.join(degradadas))
        return 2 if a.estricto else 0
    return 0


def _cmd_conteo(a) -> int:
    from .modelo import proyectar_conteo
    cfg = cargar_config(a.config)
    r = proyectar_conteo(cfg, a.votos_d, a.votos_r, a.restantes, a.corrimiento)
    print(json.dumps(r, indent=2, ensure_ascii=False))
    return 0


def _cmd_verificar(a) -> int:
    cfg = cargar_config(a.config)
    ok = True
    for clave in ('encuestas_base', 'carpeta_sentimiento', 'datos'):
        p = cfg.ruta(clave)
        print(f"{'OK ' if p.exists() else 'FALTA'} {clave}: {p}")
        ok &= p.exists() or clave == 'carpeta_sentimiento'
    if not cfg.offline and cfg.fuentes.get('encuestas_en_vivo', True):
        from .encuestas_web import obtener_web
        web, est = obtener_web(cfg)
        for k, v in est.items():
            print(f"{'OK ' if v == 'en_vivo' else 'AVISO'} {k}: {v} ({len(web[k.split('_', 1)[1]])} encuestas)")
    for mod in ('numpy', 'pandas', 'openpyxl', 'matplotlib', 'requests', 'bs4', 'lxml'):
        try:
            __import__(mod)
            print(f'OK  módulo {mod}')
        except ImportError:
            print(f'FALTA módulo {mod}')
            ok = False
    try:
        __import__('playwright')
        print('OK  playwright (respaldo de Civiq con navegador)')
    except ImportError:
        print('AVISO playwright no instalado: sin respaldo por navegador si la API de Civiq falla')
    print(f"Config: {cfg.archivo} · elección {cfg.dia_eleccion} · hoy {datetime.now():%Y-%m-%d}")
    return 0 if ok else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog='ca_pronostico', description='ODISEO · pronóstico California (M5)')
    p.add_argument('--config', default=None, help='ruta a un .toml (por defecto config/california.toml)')
    sub = p.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('correr', help='ejecuta el pronóstico')
    c.add_argument('--offline', action='store_true', help='no consulta fuentes en vivo (usa cachés)')
    c.add_argument('--corte', help='fecha de corte YYYY-MM-DD (por defecto hoy en California)')
    c.add_argument('--modo-conteo', action='store_true', help='noche electoral: Kalshi fuera de la mezcla')
    c.add_argument('--sin-graficas', action='store_true')
    c.add_argument('--estricto', action='store_true', help='código 2 si alguna fuente no está en vivo')
    c.add_argument('-v', '--verboso', action='store_true')
    c.set_defaults(f=_cmd_correr)
    k = sub.add_parser('conteo', help='proyección del conteo (noche electoral)')
    k.add_argument('--votos-d', type=int, required=True)
    k.add_argument('--votos-r', type=int, required=True)
    k.add_argument('--restantes', type=int, required=True, help='boletas por contar (reporte SOS)')
    k.add_argument('--corrimiento', type=float, default=None, help='pp de cuota R en boletas tardías')
    k.set_defaults(f=_cmd_conteo)
    v = sub.add_parser('verificar', help='revisa configuración, rutas y dependencias')
    v.set_defaults(f=_cmd_verificar)
    a = p.parse_args(argv)
    return a.f(a)


if __name__ == '__main__':
    sys.exit(main())
