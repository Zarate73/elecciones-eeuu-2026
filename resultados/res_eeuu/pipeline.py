"""Una corrida: congelar pronósticos finales (una vez) → consultar fuentes → comparar → escribir salidas y tablero."""
from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .comparar import agregado, comparar
from .fuentes import ADAPTADORES, Conteo

log = logging.getLogger(__name__)
RAIZ_RES = Path(__file__).resolve().parent.parent
RAIZ_REPO = RAIZ_RES.parent
try:
    import tomllib
except ModuleNotFoundError:                                    # pragma: no cover
    import tomli as tomllib


def cargar_config(ruta: Path | None = None) -> dict:
    with open(ruta or RAIZ_RES / 'config' / 'carreras.toml', 'rb') as f:
        c = tomllib.load(f)
    g = c['general']
    g['corte'] = datetime.fromisoformat(g['corte_congelado_utc'].replace('Z', '+00:00'))
    return c


def congelar(cfg: dict, dir_tablero: Path, dir_finales: Path, ahora: datetime, forzar: bool = False) -> dict:
    """Copia el pronóstico publicado de cada estado la primera vez que corre después del corte: ese es el «final»."""
    estado = {}
    dir_finales.mkdir(parents=True, exist_ok=True)
    for clave in cfg['carreras']:
        dst = dir_finales / f'{clave}.json'
        if dst.exists():
            previo = json.loads(dst.read_text(encoding='utf-8')).get('congelado_utc', '')
            prematuro = previo and datetime.fromisoformat(previo) < cfg['general']['corte'] <= ahora
            if not prematuro:                                    # un congelado de prueba antes del corte se rehace
                estado[clave] = 'congelado'
                continue
        src = dir_tablero / f'{clave}.json'
        if not src.exists():
            estado[clave] = 'sin_pronostico'
            continue
        if ahora >= cfg['general']['corte'] or forzar:
            d = json.loads(src.read_text(encoding='utf-8'))
            d['congelado_utc'] = ahora.isoformat(timespec='seconds')
            dst.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')
            estado[clave] = 'congelado'
        else:
            estado[clave] = 'provisional'
    return estado


def pronostico_final(clave: str, dir_tablero: Path, dir_finales: Path) -> tuple[dict | None, bool]:
    f = dir_finales / f'{clave}.json'
    if f.exists():
        return json.loads(f.read_text(encoding='utf-8')), True
    f = dir_tablero / f'{clave}.json'
    return (json.loads(f.read_text(encoding='utf-8')), False) if f.exists() else (None, False)


def manual(clave: str, ruta: Path) -> Conteo | None:
    if not ruta.exists():
        return None
    d = pd.read_csv(ruta)
    d = d[d.clave == clave]
    if d.empty:
        return None
    x = d.sort_values('hora_utc').iloc[-1]
    av = None if pd.isna(x.avance) else float(x.avance)
    return Conteo(f'Manual: {x.fuente}', float(x.votos_D), float(x.votos_R), float(x.votos_otros or 0), av,
                  '' if av is None else f'{av:.0%} (manual)', str(x.hora_utc), '' if pd.isna(x.url) else str(x.url))


def consultar(clave: str, carrera: dict, cfg: dict, ruta_manual: Path, adaptadores=ADAPTADORES) -> tuple[Conteo | None, list]:
    estados = []
    m = manual(clave, ruta_manual)
    if m is not None:
        return m, [{'fuente': 'manual', 'estado': 'usada'}]
    elegido = None
    for f in carrera['fuentes']:
        try:
            c = adaptadores[f['tipo']](carrera, f, cfg['general'])
            st = 'sin votos todavía' if c is None else f'{c.total:,.0f} votos'
            if c is not None and elegido is None:
                elegido, st = c, st + ' (usada)'
        except Exception as exc:                                 # noqa: BLE001 - cada fuente falla por separado
            log.warning('%s %s: %s', clave, f['tipo'], exc)
            st = f'error: {str(exc)[:90]}'
        estados.append({'fuente': f['tipo'], 'estado': st})
        if elegido is not None:
            break                                                 # las de menor prioridad no se consultan
    return elegido, estados


def ejecutar(cfg: dict | None = None, ahora: datetime | None = None, forzar_congelado: bool = False,
             dir_tablero: Path | None = None, dir_res: Path | None = None, adaptadores=ADAPTADORES) -> dict:
    cfg = cfg or cargar_config()
    ahora = ahora or datetime.now(timezone.utc)
    dir_tablero = dir_tablero or RAIZ_REPO / 'tablero' / 'datos'
    dir_res = dir_res or RAIZ_RES
    fin = congelar(cfg, dir_tablero, dir_res / 'pronosticos_finales', ahora, forzar_congelado)
    hist_p = dir_res / 'salidas' / 'historial.csv'
    hist = pd.read_csv(hist_p) if hist_p.exists() else pd.DataFrame()
    filas_h, estados = [], {}
    for clave, carrera in cfg['carreras'].items():
        p, congelado = pronostico_final(clave, dir_tablero, dir_res / 'pronosticos_finales')
        if p is None:
            continue
        c, fuentes = consultar(clave, carrera, cfg, dir_res / 'data' / 'manuales.csv', adaptadores)
        r = comparar(p['pronostico'], c.dict() if c else None, cfg['general']['avance_completo'])
        r.update({'clave': clave, 'estado_nombre': carrera['estado'], 'cargo': carrera['cargo'], 'candidatos': p['candidatos'],
                  'pronostico_corte': p.get('corte'), 'pronostico_congelado': congelado, 'fuentes': fuentes})
        if c is not None:
            filas_h.append({'consultado_utc': ahora.isoformat(timespec='seconds'), 'clave': clave, 'fuente': c.fuente,
                            'avance': c.avance, 'votos_D': c.votos_D, 'votos_R': c.votos_R, 'votos_otros': c.votos_otros,
                            'pct_D': r['pct_D'], 'pct_R': r['pct_R'], 'margen': r['margen'], 'error_margen': r['error_margen']})
        estados[clave] = r
    if filas_h:
        nuevas = pd.DataFrame(filas_h)
        if not hist.empty:                                       # solo cambios: misma fuente y mismos votos = no se repite
            ult = hist.sort_values('consultado_utc').groupby('clave').tail(1).set_index('clave')
            nuevas = nuevas[[not (k in ult.index and ult.loc[k, 'fuente'] == f and ult.loc[k, 'votos_D'] == d
                                  and ult.loc[k, 'votos_R'] == rr and ult.loc[k, 'votos_otros'] == o)
                             for k, f, d, rr, o in zip(nuevas.clave, nuevas.fuente, nuevas.votos_D, nuevas.votos_R, nuevas.votos_otros)]]
        hist = pd.concat([hist, nuevas], ignore_index=True)
        hist_p.parent.mkdir(parents=True, exist_ok=True)
        hist.to_csv(hist_p, index=False)
    for clave, r in estados.items():
        h = hist[hist.clave == clave].sort_values('consultado_utc') if not hist.empty else pd.DataFrame()
        r['serie'] = [{'t': x.consultado_utc, 'avance': None if pd.isna(x.avance) else float(x.avance), 'margen': float(x.margen),
                       'pct_D': float(x.pct_D), 'pct_R': float(x.pct_R)} for x in h.itertuples()]
    filas = list(estados.values())
    res = {'generado': ahora.isoformat(timespec='seconds'), 'dia_eleccion': cfg['general']['dia_eleccion'],
           'congelado': all(v == 'congelado' for v in fin.values()), 'estado_congelado': fin,
           'agregado': {'con_datos': agregado(filas), 'casi_completos': agregado(filas, True)}, 'estados': estados}
    texto = json.dumps(res, ensure_ascii=False, indent=1, allow_nan=False, default=float)
    (dir_res / 'salidas').mkdir(parents=True, exist_ok=True)
    (dir_res / 'salidas' / 'ultimo.json').write_text(texto, encoding='utf-8')
    (dir_tablero / 'resultados.json').write_text(texto, encoding='utf-8')
    (dir_res / 'salidas' / 'resumen.txt').write_text(resumen(res), encoding='utf-8')
    return res


def _pp(x):
    return '—' if x is None else f'{x:+.1f}'


def resumen(res: dict) -> str:
    lin = [f"Resultados preliminares vs pronóstico final · {res['generado']} UTC · "
           f"pronósticos {'congelados' if res['congelado'] else 'NO congelados todavía (provisional)'}", '=' * 100]
    for k, r in res['estados'].items():
        p = r['pronostico']
        if r['estado'] == 'sin_datos':
            lin.append(f"{r['estado_nombre']:16s} sin votos · pronóstico {_pp(p['margen'])} (IC80 {_pp(p['margen_IC80'][0])}, "
                       f"{_pp(p['margen_IC80'][1])}) · fuentes: " + '; '.join(f"{f['fuente']}={f['estado'][:40]}" for f in r['fuentes']))
            continue
        av = '—' if r['avance'] is None else f"{r['avance']:.0%}"
        lin.append(f"{r['estado_nombre']:16s} avance {av:>4s} · conteo {_pp(r['margen'])} vs pronóstico {_pp(p['margen'])} · error "
                   f"{_pp(r['error_margen'])} · percentil {r['percentil']:.0%} · IC80 {'sí' if r['en_IC80'] else 'NO'} · "
                   f"líder {r['lider']} ({'acierto' if r['acierto_lider'] else 'FALLO'}) · {r['fuente']}")
    for nom, a in res['agregado'].items():
        if a:
            lin.append(f"\n{nom}: n={a['n']} · MAE {a['MAE_margen']:.2f} · RMSE {a['RMSE_margen']:.2f} · sesgo {a['sesgo_margen']:+.2f} "
                       f"(>0 = mejor para D que el pronóstico) · IC80 {a['cobertura_IC80']:.0%} · IC95 {a['cobertura_IC95']:.0%} · "
                       f"líder {a['aciertos_lider']}/{a['n']} · Brier {a['brier']:.3f} · CRPS {a['crps']:.2f}")
    return '\n'.join(lin)
