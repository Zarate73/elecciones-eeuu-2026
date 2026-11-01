"""¿Toca correr el pronóstico? Los pronósticos se congelan el día de la elección (3-nov-2026).

La última corrida válida es la de la MAÑANA del 3 de noviembre (todas empiezan entre las 10:00 y las 13:00 UTC, antes
de que abra la primera casilla en la costa oeste y mucho antes del primer cierre). Desde el corte de abajo ya no se
corre: así el «pronóstico final» de cada estado es el último publicado antes de que haya un solo voto contado, y es
contra él que se mide el error con los resultados preliminares (resultados/).

Uso en GitHub Actions:  python scripts/ventana_pronostico.py  → escribe correr=true|false en $GITHUB_OUTPUT.
Con FORZAR_PRONOSTICO=1 (input «forzar» del workflow_dispatch) se corre de todos modos (no recomendado tras el corte).
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

CORTE_UTC = datetime(2026, 11, 3, 15, 0, tzinfo=timezone.utc)   # 10:00 ET del 3-nov: ninguna corrida programada después


def toca_correr(ahora: datetime | None = None, forzar: bool = False) -> bool:
    ahora = ahora or datetime.now(timezone.utc)
    return forzar or ahora < CORTE_UTC


def main() -> int:
    forzar = os.environ.get('FORZAR_PRONOSTICO', '').strip().lower() in ('1', 'true', 'si', 'sí')
    ok = toca_correr(forzar=forzar)
    msg = ('Dentro de la ventana: se corre el pronóstico.' if ok and not forzar else
           'Corrida FORZADA después del corte.' if ok else
           f'Pronóstico congelado desde {CORTE_UTC:%Y-%m-%d %H:%M} UTC (día de la elección): no se corre. '
           'El pronóstico final es la última corrida publicada; el seguimiento de preliminares está en resultados/.')
    print(msg)
    salida = os.environ.get('GITHUB_OUTPUT')
    if salida:
        with open(salida, 'a', encoding='utf-8') as f:
            f.write(f"correr={'true' if ok else 'false'}\n")
    return 0


if __name__ == '__main__':
    sys.exit(main())
