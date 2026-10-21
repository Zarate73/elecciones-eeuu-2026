"""Modelos M1–M4 del notebook original (solo para comparar con M5)."""
from __future__ import annotations

import json, re, time, unicodedata
from dataclasses import dataclass, asdict, field
from datetime import date, datetime, timedelta
from math import sqrt, tanh
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from .tipos import VotoTemprano


@dataclass
class SenalParticipacion:
    activa: bool
    estado: str
    fecha_datos: Optional[str]
    fecha_corte: str
    dias_antes_eleccion: Optional[int]
    metodo: str
    participacion_devueltas_pct: Optional[float]
    proporcion_retorno_final_esperada_pct: Optional[float]
    margen_dem_rep_devoluciones_pp: Optional[float]
    margen_comparacion_pp: Optional[float]
    desviacion_composicion_pp: Optional[float]
    peso_de_cobertura: float
    max_ajuste_margen_pp: float
    cambio_margen_pp: float
    nota: str
    fuentes_comparacion: list[str]

    def to_dict(self):
        return asdict(self)


def sin_senal(corte: date, motivo: str, cap_pp: float = 2.0) -> SenalParticipacion:
    return SenalParticipacion(
        activa=False, estado='sin_ajuste', fecha_datos=None,
        fecha_corte=corte.isoformat(), dias_antes_eleccion=None,
        metodo='no_disponible', participacion_devueltas_pct=None,
        proporcion_retorno_final_esperada_pct=None,
        margen_dem_rep_devoluciones_pp=None, margen_comparacion_pp=None,
        desviacion_composicion_pp=None, peso_de_cobertura=0.,
        max_ajuste_margen_pp=cap_pp, cambio_margen_pp=0., nota=motivo,
        fuentes_comparacion=[]
    )


def calcular_senal(
    dato: Optional[VotoTemprano], corte: date, dia_eleccion: date, *,
    max_ajuste_margen_pp: float = 2.0,
    escala_historica_pp: float = 10.0,
    tasa_final_referencia: float = 0.60,
    max_antiguedad_dias: int = 2,
) -> SenalParticipacion:
    """Construye una perturbación ACOTADA del margen del agregador.

    delta_margen = cap * sqrt(fraccion_de_devuelto_sobre_retorno_final)
                    * tanh(desviacion_pp / escala)

    La raíz cuadrada preserva sensibilidad temprana sin dejar que 0.8% de
    devolución domine a las encuestas. Todos los parámetros son HIPÓTESIS
    explícitas, no coeficientes calibrados. Alternativa secundaria: discrepancia
    frente a registro con 50% de amplitud y escala más conservadora.
    """
    if max_ajuste_margen_pp < 0 or escala_historica_pp <= 0 or not 0 < tasa_final_referencia <= 1:
        raise ValueError('Parametros de la senal invalidos')
    if dato is None:
        return sin_senal(corte, 'No hay datos de voto temprano; agregado sin cambios.', max_ajuste_margen_pp)
    if dato.estado != 'actualizado':
        return sin_senal(corte, f'Estado {dato.estado}: cache o fuente rezagada; no se aplica ajuste.', max_ajuste_margen_pp)
    fecha = date.fromisoformat(dato.fecha_datos)
    antiguedad = (corte - fecha).days
    if antiguedad < 0 or antiguedad > max_antiguedad_dias:
        return sin_senal(corte, f'Datos de voto temprano con {antiguedad} dias de diferencia; no se aplican.', max_ajuste_margen_pp)
    if dato.registrados <= 0 or dato.devueltas <= 0 or not (dato.registro_dem > 0 and dato.registro_rep > 0):
        return sin_senal(corte, 'Sin observaciones de devolución suficientes.', max_ajuste_margen_pp)
    dte = (dia_eleccion - fecha).days
    if dte < 0:
        return sin_senal(corte, 'La eleccion ya se realizo; no actualizar pronostico con retorno posterior.', max_ajuste_margen_pp)

    margen_actual = 100.0 * (dato.devueltas_dem - dato.devueltas_rep) / dato.devueltas
    porcentaje_reg = 100.0 * (dato.registro_dem - dato.registro_rep) / dato.registrados
    historial = dato.referencia_historica or {}
    historicos_validos = []
    if historial.get('dias_antes_eleccion') == dte:
        for k in ('2022 General', '2024 General'):
            if isinstance(historial.get(k), (int, float)) and -100 <= float(historial[k]) <= 100:
                historicos_validos.append((k, float(historial[k])))

    if historicos_validos:
        base = sum(x for _, x in historicos_validos) / len(historicos_validos)
        metodo = 'comparacion_historica_dias_equivalentes'
        factor_credibilidad = 1.0
        escala = escala_historica_pp
        fuentes = [k for k, _ in historicos_validos]
        nota = ('Desviacion frente al margen D-R en boletas devueltas en elecciones '
                'anteriores, con igual distancia al dia electoral. No son votos por candidato.')
    else:
        # Si la tabla historica no se puede analizar, mantener una señal menor,
        # bien diferenciada, sin fingir una serie historica disponible.
        base = porcentaje_reg
        metodo = 'proxy_registro_sin_historial'
        factor_credibilidad = 0.5
        escala = escala_historica_pp * 1.5
        fuentes = []
        nota = ('Solo proxy de tasas de devolución D/R respecto del registro; '
                'mas debil: el ritmo de devolucion no indica preferencia de voto.')

    desviacion = margen_actual - base
    cobertura = min(1.0, max(0.0, dato.devueltas / (dato.registrados * tasa_final_referencia)))
    peso = sqrt(cobertura)
    delta = max_ajuste_margen_pp * factor_credibilidad * peso * tanh(desviacion / escala)
    delta = max(-max_ajuste_margen_pp, min(max_ajuste_margen_pp, delta))
    return SenalParticipacion(
        activa=True, estado='escenario_experimental_no_calibrado',
        fecha_datos=dato.fecha_datos, fecha_corte=corte.isoformat(), dias_antes_eleccion=dte,
        metodo=metodo,
        participacion_devueltas_pct=100*dato.devueltas/dato.registrados,
        proporcion_retorno_final_esperada_pct=100*cobertura,
        margen_dem_rep_devoluciones_pp=margen_actual,
        margen_comparacion_pp=base,
        desviacion_composicion_pp=desviacion,
        peso_de_cobertura=peso, max_ajuste_margen_pp=max_ajuste_margen_pp,
        cambio_margen_pp=delta, nota=nota, fuentes_comparacion=fuentes,
    )


def aplicar_a_agregado(becerra: float, hilton: float, senal: SenalParticipacion) -> dict:
    if abs(becerra + hilton - 100) > 1e-5:
        raise ValueError('El agregado debe sumar 100%')
    margen_base = becerra - hilton
    delta = senal.cambio_margen_pp
    if not 0 <= becerra + delta/2 <= 100:
        raise ValueError('La senal produce un porcentaje invalido')
    return {
        'becerra_bipartidista_pct': becerra + delta/2,
        'hilton_bipartidista_pct': hilton - delta/2,
        'margen_becerra_menos_hilton_pp': margen_base + delta,
        'diferencia_frente_encuestas_pp': delta,
        'tipo': 'escenario_experimental_condicional_no_calibrado',
    }

@dataclass(frozen=True)
class ParametrosShocks:
    tasa_semanal: float = 0.15
    magnitud_sd_pp: float = 3.0
    grados_libertad: float = 5.0

    def validar(self) -> None:
        if not (np.isfinite(self.tasa_semanal) and self.tasa_semanal >= 0):
            raise ValueError('tasa_semanal debe ser finita y >= 0')
        if not (np.isfinite(self.magnitud_sd_pp) and self.magnitud_sd_pp >= 0):
            raise ValueError('magnitud_sd_pp debe ser finita y >= 0')
        if not (np.isfinite(self.grados_libertad) and self.grados_libertad > 2):
            raise ValueError('grados_libertad debe ser >2 para tener varianza finita')


@dataclass
class SimulacionComparativa:
    referencia: np.ndarray
    participacion: np.ndarray
    con_shocks: np.ndarray
    shocks_total: np.ndarray
    eventos_por_iteracion: np.ndarray
    dias_hasta_eleccion: int
    lambda_esperada: float

    def resumen(self, params: ParametrosShocks) -> dict:
        n = len(self.referencia)
        def estadisticos(v):
            q = np.quantile(v, [.025, .5, .975])
            return {
                'media_margen_pp': float(np.mean(v)),
                'mediana_margen_pp': float(q[1]),
                'intervalo_central_95_pp': [float(q[0]), float(q[2])],
                'desviacion_simulada_pp': float(np.std(v, ddof=1)),
            }
        d = {
            'advertencia': ('Distribuciones de sensibilidad, NO probabilidades electorales '
                            'calibradas. Frecuencias simuladas dependen de parametros hipoteticos.'),
            'dias_hasta_eleccion': self.dias_hasta_eleccion,
            'modelo': 'normal_comun + Poisson_compuesto + saltos_t_student_simetrica',
            'parametros_hipoteticos': {
                'tasa_shocks_por_semana': params.tasa_semanal,
                'desviacion_shock_individual_pp': params.magnitud_sd_pp,
                'grados_libertad_shock': params.grados_libertad,
                'eventos_esperados_restantes': self.lambda_esperada,
                'varianza_teorica_shocks_pp2': self.lambda_esperada * params.magnitud_sd_pp**2,
            },
            'n_simulaciones': n,
            'frecuencia_simulada_al_menos_un_shock': float(np.mean(self.eventos_por_iteracion > 0)),
            'frecuencia_simulada_desplazamiento_absoluto_2pp_o_mas': float(np.mean(np.abs(self.shocks_total) >= 2)),
            'componente_shocks': {
                'desviacion_simulada_pp': float(np.std(self.shocks_total, ddof=1)),
                'percentiles_2_5_50_97_5_pp': [float(x) for x in np.quantile(self.shocks_total, [.025,.5,.975])],
            },
            'escenarios': {
                'solo_encuestas': estadisticos(self.referencia),
                'encuestas_y_participacion': estadisticos(self.participacion),
                'encuestas_participacion_y_shocks': estadisticos(self.con_shocks),
            },
        }
        return d


def simular_comparativo(
    margen_base_pp: float,
    delta_participacion_pp: float,
    sigma_normal_pp: float,
    n_simulaciones: int,
    semilla: int,
    corte: date,
    eleccion: date,
    parametros: ParametrosShocks,
) -> SimulacionComparativa:
    parametros.validar()
    if not (-100 <= margen_base_pp <= 100):
        raise ValueError('El margen debe estar entre -100 y 100 pp')
    if not (np.isfinite(delta_participacion_pp) and np.isfinite(sigma_normal_pp) and sigma_normal_pp > 0):
        raise ValueError('Delta y sigma normal deben ser finitos, sigma > 0')
    if n_simulaciones < 100 or n_simulaciones > 2_000_000:
        raise ValueError('Numero de simulaciones fuera de [100, 2000000]')

    dias = max((eleccion - corte).days, 0)
    lam = parametros.tasa_semanal * dias / 7.0
    # Flujos separados con SeedSequence: aumentar muestras o cambiar lambda no
    # modifica la distribucion base, útil en comparaciones reproducibles.
    ss = np.random.SeedSequence(semilla)
    rng_normal, rng_eventos, rng_saltos = (np.random.default_rng(s) for s in ss.spawn(3))

    normal_comun = rng_normal.normal(0., sigma_normal_pp, n_simulaciones)
    referencia = margen_base_pp + normal_comun
    participacion = referencia + delta_participacion_pp

    eventos = rng_eventos.poisson(lam, n_simulaciones)
    efectos = np.zeros(n_simulaciones, dtype=float)
    total_eventos = int(np.sum(eventos))
    if total_eventos and parametros.magnitud_sd_pp > 0:
        # Desviacion de t(df): sqrt(df/(df-2)); de ahí el factor reescalado.
        escala = parametros.magnitud_sd_pp * np.sqrt((parametros.grados_libertad-2) / parametros.grados_libertad)
        saltos = rng_saltos.standard_t(parametros.grados_libertad, size=total_eventos) * escala
        # np.repeat produce indices por realizacion. np.bincount agrega eventos
        # en O(total_eventos) y evita millones de bucles Python.
        indices = np.repeat(np.arange(n_simulaciones, dtype=np.int32), eventos)
        efectos = np.bincount(indices, weights=saltos, minlength=n_simulaciones).astype(float)

    return SimulacionComparativa(
        referencia=referencia, participacion=participacion,
        con_shocks=participacion+efectos, shocks_total=efectos,
        eventos_por_iteracion=eventos, dias_hasta_eleccion=dias, lambda_esperada=lam,
    )