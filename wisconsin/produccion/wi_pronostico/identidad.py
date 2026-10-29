"""Identidad de encuestas entre fuentes (auditoría transversal T3, 26-oct-2026).

Módulo común a los diez paquetes de producción: el archivo es idéntico en cada `<sigla>_pronostico/identidad.py`
(la prueba `test_identidad.py` lo verifica con su huella). Ninguna fuente publica un identificador de estudio, así que la
identidad se decide con el PERIODO DE CAMPO y, cuando una fuente solo da una fecha, con la coherencia entre esa fecha
(publicación) y el cierre de campo de la otra.

Reglas (misma firma = misma clave de 14 letras tras ALIAS):
  1. Dos periodos de campo con rango:
       - MISMO periodo (mismo inicio y mismo fin) → mismo estudio siempre, aunque los márgenes difieran (versiones LV/RV
         o con/sin indecisos asignados de una misma muestra; gana LV > RV > A). Revisión del 26-oct: separarlas dejaba
         dos filas con la misma llave (firma, inicio, fin) y la validación de duplicados detenía la corrida;
       - se solapan o se tocan sin coincidir → mismo estudio (la misma encuesta en dos fuentes), salvo que vengan de la
         MISMA fuente con márgenes a más de 3 pp: estudios paralelos (Univision/YouGov 2–15 oct y YouGov 28 sep–5 oct
         en Florida; se conservan los dos y se registra);
       - disjuntos → estudios DISTINTOS, aunque estén a 1 día o tengan las mismas cifras (ActiVote TX 30 sep–14 oct y
         17–21 oct; OnMessage NY 1–6 oct y 12–14 oct). Se elimina la regla «≤ 7 días» y la de «mismas cifras ≤ 60 días».
  2. Un rango y una fecha puntual (270toWin publica por fecha de publicación):
       - la fecha puntual cae entre el inicio de campo y 14 días después del cierre, y las cifras son compatibles
         (mismas cifras ±0.5, margen a ≤ 3 pp o mismo n) → mismo estudio. De las 62 parejas de este tipo en las fuentes
         del 25/26-oct (fin ≥ 1-ago), 60 tienen margen a ≤ 3 pp; las otras 2 (YouGov TX y FL, 5–6 pp) son en realidad la
         encuesta del patrocinador (CBS, Univision), con la que sí se funden;
       - fuera de esa ventana (hasta 60 días), solo con mismas cifras Y mismo n → mismo estudio con la fecha mal
         capturada (Arizona State/BSP: campo 18 ago–4 sep, fechada el 19-oct en 270toWin; se registra para revisión);
       - en otro caso, o con cifras incompatibles → estudios distintos (se registra como «ambigua» si la fecha
         cae en la ventana pero las cifras no cuadran: conservar ambas pesa poco, porque el promedio divide el peso de
         una firma entre sus encuestas en la ventana; fundir dos olas, en cambio, pierde una).
  3. Dos fechas puntuales: mismo estudio solo con margen a ≤ 3 pp y a ≤ 3 días.
Firmas distintas: los alias conocidos se resuelven antes (ALIAS de cada paquete). Fuera de eso solo se funde la etiqueta
  genérica «YouGov» de 270toWin con «<patrocinador>/YouGov» u otro patrocinador, con calendario compatible (reglas 1–3),
  las mismas cifras y (ambas mencionan YouGov o mismo n ≥ 300). Mismas cifras y mismo n entre dos firmas reales NO
  bastan (GQR y GrayHouse, Arizona: 49–45, n = 600).
  Una fila de origen verificado con periodo de campo («complementaria») nunca se funde con otra firma.
Cuando varias filas cumplen, se elige la MÁS CERCANA en el calendario, no la primera (Beacon/Shaw TX repitió 47–52 el
28-sep y el 19-oct). Al fundir: gana la población LV > RV > A, se conserva el periodo de campo (no la fecha de
publicación), se completan los datos que falten y, si una fuente verificada trae decimales compatibles con el redondeo,
mandan sus decimales. Cada decisión queda en `decisiones` (fusión, separación por periodos distintos con mismas
cifras, o ambigua).
"""
from __future__ import annotations

import math

VENTANA_PUBLICACION_DIAS = 14     # publicación hasta 14 días después del cierre de campo
TOL_MARGEN_PP = 3.0               # versiones del mismo estudio (LV/RV, con/sin indecisos asignados) difieren ≤ 3 pp
TOL_PUNTUALES_DIAS = 3
MAX_FECHA_MAL_CAPTURADA_DIAS = 60  # fecha puntual lejos del campo: misma encuesta solo con mismas cifras Y mismo n
N_MINIMO_MISMO_N = 300
RANGO_POP = {'LV': 0, 'RV': 1, 'A': 2}
VERIFICADAS = ('base', 'complementaria')


def _num(x) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return math.nan
    return v


def _ts(x):
    import pandas as pd
    return pd.Timestamp(x) if x is not None and not (isinstance(x, float) and math.isnan(x)) and str(x) not in ('', 'NaT') else None


def intervalo(r: dict):
    """(inicio, fin, puntual). Puntual = la fuente da una sola fecha (suele ser la de publicación)."""
    fin = _ts(r.get('fin'))
    ini = _ts(r.get('inicio')) or fin
    if ini > fin:                         # periodo invertido por error de captura (Grassroots NV: «8 jul–6 jul»)
        ini, fin = fin, ini
    return ini, fin, ini == fin


def separacion(a, b) -> int:
    """Días entre dos periodos (0 si se solapan o se tocan)."""
    return max((a[0] - b[1]).days, (b[0] - a[1]).days, 0)


def _cifras(r: dict, b: dict):
    dD, dR = abs(_num(r.get('D')) - _num(b.get('D'))), abs(_num(r.get('R')) - _num(b.get('R')))
    mismas = dD <= 0.51 and dR <= 0.51
    dm = abs((_num(r.get('D')) - _num(r.get('R'))) - (_num(b.get('D')) - _num(b.get('R'))))
    nr, nb = _num(r.get('n')), _num(b.get('n'))
    mismo_n = not math.isnan(nr) and not math.isnan(nb) and nr >= N_MINIMO_MISMO_N and abs(nr - nb) < 0.5
    return mismas, dm, mismo_n


def calendario(r: dict, b: dict) -> tuple[str, int]:
    """Relación temporal entre dos filas: ('solapados'|'disjuntos'|'publicacion'|'publicacion_fuera'|'puntuales'|
    'puntuales_lejos', distancia en días para elegir la más cercana)."""
    ir, ib = intervalo(r), intervalo(b)
    if not ir[2] and not ib[2]:
        s = separacion(ir, ib)
        return ('solapados' if s == 0 else 'disjuntos'), s
    if ir[2] and ib[2]:
        d = abs((ir[1] - ib[1]).days)
        return ('puntuales' if d <= TOL_PUNTUALES_DIAS else 'puntuales_lejos'), d
    rg, pt = (ib, ir) if ir[2] else (ir, ib)
    lag = (pt[1] - rg[1]).days                                  # publicación − cierre de campo
    if rg[0] <= pt[1] and lag <= VENTANA_PUBLICACION_DIAS:
        return 'publicacion', max(lag, 0)
    return 'publicacion_fuera', abs(lag)


def relacion(r: dict, b: dict) -> tuple[bool, str]:
    """(mismo estudio, razón). r y b: dicts con clave, pollster, inicio, fin, n, pop, D, R, origen."""
    cal, _ = calendario(r, b)
    mismas, dm, mismo_n = _cifras(r, b)
    compatibles = mismas or dm <= TOL_MARGEN_PP or mismo_n
    if r.get('clave') == b.get('clave'):
        if cal == 'solapados':
            ir, ib = intervalo(r), intervalo(b)
            if ir[0] == ib[0] and ir[1] == ib[1]:
                return True, 'misma firma, mismo periodo de campo (versiones del mismo estudio)'
            if r.get('origen') == b.get('origen') and dm > TOL_MARGEN_PP:
                return False, 'ambigua: periodos solapados en la misma fuente con márgenes distintos'
            return True, 'misma firma, periodos de campo solapados'
        if cal == 'disjuntos':
            return False, ('periodos de campo distintos con las mismas cifras' if mismas else 'periodos de campo distintos')
        if cal == 'publicacion':
            if compatibles:
                return True, 'misma firma, fecha de publicación coherente con el cierre de campo'
            return False, 'ambigua: publicación en la ventana pero cifras incompatibles'
        if cal == 'puntuales':
            if dm <= TOL_MARGEN_PP:
                return True, 'misma firma, fechas puntuales a ≤ 3 días'
            return False, 'fechas puntuales cercanas con cifras distintas'
        if cal == 'publicacion_fuera' and mismas and mismo_n and calendario(r, b)[1] <= MAX_FECHA_MAL_CAPTURADA_DIAS:
            # 270toWin fechó el 19-oct la encuesta de Arizona State/BSP (campo 18 ago–4 sep, 47–34, n = 1,300 RV)
            return True, 'fecha puntual mal capturada: mismas cifras y mismo n (revisar)'
        return False, 'fechas incompatibles'
    # firmas distintas: patrocinador frente a encuestadora
    if cal not in ('solapados', 'publicacion', 'puntuales'):
        return False, 'firmas distintas, fechas incompatibles'
    verificada = 'complementaria' in (r.get('origen'), b.get('origen')) and not (intervalo(r)[2] or intervalo(b)[2])
    if verificada:
        return False, 'firma verificada con periodo de campo propio'
    # 270toWin rotula «YouGov» encuestas que Wikipedia atribuye al patrocinador (CBS, Univision, UT/Texas Politics
    # Project). Solo ese caso: dos firmas reales con las mismas cifras y el mismo n son estudios distintos (GQR y
    # GrayHouse publicaron ambas 49–45 con n = 600 en Arizona).
    generica = 'yougov' in (r.get('clave'), b.get('clave'))
    ambas_yougov = 'yougov' in str(r.get('pollster', '')).lower() and 'yougov' in str(b.get('pollster', '')).lower()
    if generica and mismas and (ambas_yougov or mismo_n):
        return True, 'etiqueta genérica YouGov = patrocinador/YouGov, mismas cifras' + ('' if ambas_yougov else ' y mismo n')
    return False, 'firmas distintas'


def _vacio(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x)) or str(x) in ('', 'nan', 'NaT', 'None')


def _desc(r: dict) -> str:
    ir = intervalo(r)
    per = f"{ir[0]:%Y-%m-%d}" if ir[2] else f"{ir[0]:%Y-%m-%d}–{ir[1]:%Y-%m-%d}"
    return f"{r.get('pollster')} {per} {r.get('pop')} {_num(r.get('D')):g}–{_num(r.get('R')):g} [{r.get('origen')}]"


def combinar_registros(fuentes, fusionar_campos: bool = True) -> tuple[list[dict], list[dict]]:
    """Une listas de dicts en orden de prioridad. Devuelve (estudios, decisiones).

    fusionar_campos=False conserva la fila de mayor prioridad sin tocarla (Georgia y California)."""
    base: list[dict] = []
    decisiones: list[dict] = []
    for f in fuentes:
        for r0 in f:
            r = dict(r0)
            mejor, mejor_d, razon_m = None, None, ''
            for b in base:
                misma, razon = relacion(r, b)
                if misma:
                    d = calendario(r, b)[1]
                    clave_d = (r.get('clave') != b.get('clave'), d)
                    if mejor_d is None or clave_d < mejor_d:
                        mejor, mejor_d, razon_m = b, clave_d, razon
                elif razon.startswith('ambigua') or 'mismas cifras' in razon:
                    decisiones.append({'decision': 'separadas', 'razon': razon, 'conservada': _desc(b), 'nueva': _desc(r)})
            if mejor is None:
                base.append(r)
                continue
            b = mejor
            decisiones.append({'decision': 'fusion', 'razon': razon_m, 'conservada': _desc(b), 'nueva': _desc(r)})
            b.setdefault('tambien_en', set()).add(r.get('origen'))
            if not fusionar_campos:
                continue
            # mejor población, solo si ambas la declaran: una fila verificada sin población (base) no cede sus cifras
            # a la versión redondeada de 270toWin (HighGround AZ 49.5–34.3 frente a 50–34)
            if (str(b.get('pop')) in RANGO_POP and str(r.get('pop')) in RANGO_POP
                    and RANGO_POP[str(r.get('pop'))] < RANGO_POP[str(b.get('pop'))]):
                for c in ('D', 'R', 'otros', 'indecisos', 'n', 'pop'):
                    if c in r:
                        b[c] = r[c]
                b['nota_version'] = f"versión {r.get('pop')} de {r.get('origen')}"
            if intervalo(b)[2] and not intervalo(r)[2]:          # periodo de campo en lugar de fecha de publicación
                b['inicio'], b['fin'] = r.get('inicio'), r.get('fin')
            for c in ('n', 'pop', 'otros', 'indecisos'):
                if c in r and _vacio(b.get(c)) and not _vacio(r.get(c)):
                    b[c] = r[c]
            dr, dd = _num(r.get('D')), _num(r.get('R'))
            if (r.get('origen') in VERIFICADAS and b.get('origen') not in VERIFICADAS
                    and abs(dr - _num(b.get('D'))) <= 0.5 and abs(dd - _num(b.get('R'))) <= 0.5 and (dr % 1 or dd % 1)):
                b['D'], b['R'] = r['D'], r['R']
                b['nota_version'] = ((b.get('nota_version') or '') + ' cifras con decimales de la fuente verificada').strip()
    return base, decisiones


def combinar_df(*fuentes, cols: list[str]):
    """Interfaz de los paquetes V11 (columnas COLS + tambien_en + nota_version). Las decisiones van en .attrs."""
    import pandas as pd
    registros = [f.to_dict('records') for f in fuentes if f is not None and len(f)]
    base, dec = combinar_registros(registros)
    out = pd.DataFrame(base, columns=cols + ['tambien_en', 'nota_version'])
    out['tambien_en'] = out.tambien_en.map(lambda s: ', '.join(sorted(map(str, s))) if isinstance(s, set) else '')
    out['nota_version'] = out.nota_version.astype(object).where(out.nota_version.notna(), '')
    out.attrs['decisiones'] = dec
    return out
