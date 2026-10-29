"""Conteo RCV (Iniciativa 83) para la general.

`contar_rcv` es el conteo de `src/rcv_engine.py::run_rcv` del modelo de la primaria (repo dc2026-rcv-forecast), sin el
linaje: gana quien pasa del 50 % de las boletas activas; si no, se elimina al último y sus votos se transfieren según la
matriz (con fracción agotada); con dos candidatos activos gana el primero. `contar_rcv_vector` hace lo mismo para
todas las simulaciones a la vez; las pruebas verifican que ambos coinciden.
"""
from __future__ import annotations

import numpy as np


def contar_rcv(primeras: dict[str, float], transferencias: dict[str, dict[str, float]]) -> dict:
    activos = {c: float(v) for c, v in primeras.items()}
    agotadas, rondas = 0.0, []
    while True:
        tot = sum(activos.values())
        cuotas = {c: v / tot for c, v in activos.items()}
        lider = max(cuotas, key=cuotas.get)
        rondas.append(dict(cuotas))
        if cuotas[lider] > 0.5 or len(activos) <= 2:
            return {'ganador': lider, 'rondas': rondas, 'agotadas': agotadas}
        ultimo = min(cuotas, key=cuotas.get)
        receptores = [c for c in activos if c != ultimo]
        fila = transferencias.get(ultimo, {r: 1.0 / len(receptores) for r in receptores})
        p_ag = float(fila.get('agotada', 0.0))
        p = [float(fila.get(c, 0.0)) for c in receptores]
        s = sum(p) + p_ag
        p, p_ag = ([x / s for x in p], p_ag / s) if s > 0 else ([1 / len(receptores)] * len(receptores), 0.0)
        v = activos.pop(ultimo)
        for c, x in zip(receptores, p):
            activos[c] += v * x
        agotadas += v * p_ag


def matriz_transferencias(candidatos: list[str], transferencias: dict) -> np.ndarray:
    """T[i, j] = fracción de los votos de i que pasa a j; la columna extra es «agotada». Fila sin datos = reparto
    uniforme entre los demás (lo mismo que run_rcv); se renormaliza entre los activos en cada ronda."""
    k = len(candidatos)
    T = np.zeros((k, k + 1))
    for i, c in enumerate(candidatos):
        fila = transferencias.get(c)
        if fila is None:
            T[i, [j for j in range(k) if j != i]] = 1.0 / (k - 1)
        else:
            for j, d in enumerate(candidatos):
                T[i, j] = float(fila.get(d, 0.0)) if j != i else 0.0
            T[i, k] = float(fila.get('agotada', 0.0))
    return T


def contar_rcv_vector(V: np.ndarray, candidatos: list[str], transferencias: dict) -> dict:
    """V: (n_sims, k) primeras preferencias (cualquier escala). Devuelve ganador (índice), rondas usadas, cuota final
    del ganador entre boletas activas y cuota de primera ronda del candidato 0."""
    n, k = V.shape
    T = matriz_transferencias(candidatos, transferencias)
    act = np.ones((n, k), bool)
    votos = V.astype(float).copy()
    ganador = np.full(n, -1)
    rondas = np.zeros(n, int)
    cuota_final = np.full(n, np.nan)
    agot = np.zeros(n)
    for r in range(k):
        vv = np.where(act, votos, 0.0)
        tot = vv.sum(1, keepdims=True)
        cu = vv / tot
        pend = ganador < 0
        lider = cu.argmax(1)
        listo = pend & ((cu.max(1) > 0.5) | (act.sum(1) <= 2))
        ganador[listo] = lider[listo]
        rondas[listo] = r + 1
        cuota_final[listo] = cu.max(1)[listo]
        pend = ganador < 0
        if not pend.any():
            break
        cu_m = np.where(act, cu, np.inf)
        ult = cu_m.argmin(1)
        for i in range(k):                                   # elimina a i en las simulaciones donde es el último
            sel = pend & (ult == i)
            if not sel.any():
                continue
            fila = T[i, :k][None, :] * act[sel]              # solo receptores activos
            fila[:, i] = 0.0
            pa = np.full((sel.sum(), 1), T[i, k])
            s = fila.sum(1, keepdims=True) + pa
            unif = (s[:, 0] <= 0)
            fila = np.where(s > 0, fila / np.where(s > 0, s, 1), 0.0)
            pa = np.where(s > 0, pa / np.where(s > 0, s, 1), 0.0)
            if unif.any():
                rec = act[sel][unif].astype(float); rec[:, i] = 0
                fila[unif] = rec / rec.sum(1, keepdims=True)
            v = votos[sel, i][:, None]
            votos[sel] += v * fila
            agot[sel] += v[:, 0] * pa[:, 0]
            votos[sel, i] = 0.0
            act[np.where(sel)[0], i] = False
    return {'ganador': ganador, 'rondas': rondas, 'cuota_final': cuota_final, 'agotadas': agot,
            'cuota_primera_0': V[:, 0] / V.sum(1)}
