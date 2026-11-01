"""python -m res_eeuu [--forzar-congelado] [--offline-prueba]: consulta las fuentes y escribe tablero/datos/resultados.json."""
import argparse
import logging
import sys

from .pipeline import ejecutar

a = argparse.ArgumentParser(prog='res_eeuu')
a.add_argument('--forzar-congelado', action='store_true', help='congela los pronósticos aunque no haya pasado el corte (solo pruebas)')
args = a.parse_args()
logging.basicConfig(level=logging.INFO, format='%(levelname)-7s %(name)s: %(message)s')
r = ejecutar(forzar_congelado=args.forzar_congelado)
from .pipeline import resumen  # noqa: E402
print(resumen(r))
sys.exit(0)
