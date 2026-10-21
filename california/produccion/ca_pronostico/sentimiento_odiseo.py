"""Señal de sentimiento ODISEO (M4): anomalía retrospectiva de la brecha 7d."""
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

# Se fijan con configurar(cfg)
USAR_SENTIMIENTO_PARA_SHOCKS = True
PESO_NOTICIAS, PESO_REDES = 0.80, 0.20
GAMMA_SENTIMIENTO = 0.35
CAP_MULTIPLICADOR_SHOCK = 1.75
MIN_HISTORICO_SENAL = 5
DIAS_HISTORICO_SENAL = 14
DIAS_SEÑAL_RECIENTE = 7
DIAS_MAX_REZAGO_SENAL = 2


def configurar(cfg) -> None:
    global USAR_SENTIMIENTO_PARA_SHOCKS, PESO_NOTICIAS, PESO_REDES, GAMMA_SENTIMIENTO
    global CAP_MULTIPLICADOR_SHOCK, MIN_HISTORICO_SENAL, DIAS_HISTORICO_SENAL, DIAS_SEÑAL_RECIENTE, DIAS_MAX_REZAGO_SENAL
    s = cfg.sentimiento_odiseo
    USAR_SENTIMIENTO_PARA_SHOCKS, PESO_NOTICIAS, PESO_REDES = s.usar, s.peso_noticias, s.peso_redes
    GAMMA_SENTIMIENTO, CAP_MULTIPLICADOR_SHOCK = s.gamma, s.cap_multiplicador
    MIN_HISTORICO_SENAL, DIAS_HISTORICO_SENAL = s.min_historico, s.dias_historico
    DIAS_SEÑAL_RECIENTE, DIAS_MAX_REZAGO_SENAL = s.dias_recientes, s.dias_max_rezago



@dataclass
class SenalSentimiento:
    activa: bool
    corte: str
    ruta: str
    fecha_ultima_senal: Optional[str]
    brechas_7d: dict
    puntajes_fuente: dict
    n_referencias: dict
    factores_cobertura: dict
    puntuacion_ponderada: float
    multiplicador_lambda: float
    tasa_base_semanal: float
    tasa_condicional_semanal: float
    eventos_contextuales: list
    advertencias: list
    metodo: str = 'anomalia_retrospectiva_en_brecha_7d_no_voto'
    def to_dict(self):
        return asdict(self)


def _validar_y_preparar_serie(ruta: Path):
    """Recalcula ventanas 7d desde el archivo ORIGINAL; no usa datos futuros."""
    if not ruta.exists():
        raise FileNotFoundError('No existe ' + str(ruta))
    df = pd.read_csv(ruta, encoding='utf-8-sig', dtype={'fecha_local':str})
    requeridas = {'fecha_local','candidato','tipo_fuente','n_menciones_validas',
                  'n_positivas','n_negativas','n_neutras','n_mixtas',
                  'n_indeterminadas','n_clasificables'}
    if not requeridas.issubset(df.columns):
        raise ValueError('Columnas faltantes en serie_sentimiento_diaria.csv: '+ str(sorted(requeridas - set(df.columns))))
    df=df[df['tipo_fuente'].isin(['NOTICIA','RED_SOCIAL']) & df['candidato'].isin(['BECERRA','HILTON'])].copy()
    df['fecha']=pd.to_datetime(df['fecha_local'], errors='raise').dt.normalize()
    if df.duplicated(['fecha','tipo_fuente','candidato']).any():
        raise ValueError('Se encontraron claves fecha/fuente/candidato duplicadas')
    numericas=['n_menciones_validas','n_positivas','n_negativas','n_neutras','n_mixtas',
               'n_indeterminadas','n_clasificables']
    for c in numericas:
        df[c]=pd.to_numeric(df[c], errors='raise')
        if df[c].isna().any() or (df[c] < 0).any() or not np.allclose(df[c],np.rint(df[c])):
            raise ValueError('Conteo inválido en columna '+c)
    if not (df['n_positivas']+df['n_negativas']+df['n_neutras']+df['n_mixtas']).eq(df['n_clasificables']).all():
        raise ValueError('No concuerdan las categorías clasificables')
    if not (df['n_clasificables']+df['n_indeterminadas']).eq(df['n_menciones_validas']).all():
        raise ValueError('No concuerdan las menciones válidas y no determinables')
    # Reindexar fechas: los días sin dato permanecen en cero conteos, jamás sentimiento=0.
    fechas=pd.date_range(df['fecha'].min(),df['fecha'].max(),freq='D')
    rows=[]
    for fuente in ('NOTICIA','RED_SOCIAL'):
        for candidato in ('BECERRA','HILTON'):
            sel=df[(df['tipo_fuente']==fuente)&(df['candidato']==candidato)].set_index('fecha').sort_index()
            if len(sel)==0: continue
            sel=sel[numericas].reindex(fechas,fill_value=0)
            suma=sel[numericas].rolling(7,min_periods=1).sum()
            observados=(sel['n_clasificables']>0).rolling(7,min_periods=1).sum()
            indice=(suma['n_positivas']-suma['n_negativas'])/suma['n_clasificables'].replace(0,np.nan)
            apta=(suma['n_clasificables']>=20)&(observados>=3)&((suma['n_positivas']+suma['n_negativas'])>=5)
            rows.append(pd.DataFrame({'fecha':fechas,'tipo_fuente':fuente,'candidato':candidato,
                                      'indice_7d':indice.to_numpy(),'apta_7d':apta.to_numpy(),
                                      'menciones_7d':suma['n_clasificables'].to_numpy(),
                                      'polarizadas_7d':(suma['n_positivas']+suma['n_negativas']).to_numpy(),
                                      'dias_con_dato_7d':observados.to_numpy()}))
    largo=pd.concat(rows,ignore_index=True)
    if len(largo)==0: raise ValueError('Sin datos para Becerra/Hilton')
    pa=largo.pivot(index=['fecha','tipo_fuente'],columns='candidato',values='apta_7d')
    v=largo.pivot(index=['fecha','tipo_fuente'],columns='candidato',values='indice_7d')
    n=largo.pivot(index=['fecha','tipo_fuente'],columns='candidato',values='menciones_7d')
    ambos=pa['BECERRA'].fillna(False)&pa['HILTON'].fillna(False)
    salida=pd.DataFrame({'fecha':v.index.get_level_values('fecha'),
                         'tipo_fuente':v.index.get_level_values('tipo_fuente'),
                         'brecha_sentimiento_7d':(v['BECERRA']-v['HILTON']).where(ambos).to_numpy(),
                         'n_becerra_7d':n['BECERRA'].to_numpy(),
                         'n_hilton_7d':n['HILTON'].to_numpy(),
                         'apta':ambos.to_numpy()}).reset_index(drop=True)
    return salida, largo


def _eventos_hasta_corte(carpeta: Path,corte: date):
    p=carpeta/'eventos.csv'
    if not p.exists(): return []
    x=pd.read_csv(p,encoding='utf-8-sig')
    requerido={'fecha_inicio_local','evento_id','tipo_evento','descripcion','verificado'}
    if not requerido.issubset(x.columns): return []
    x['fecha']=pd.to_datetime(x['fecha_inicio_local'],errors='coerce')
    lo=pd.Timestamp(corte)-pd.Timedelta(days=7)
    x=x[(x['fecha']<=pd.Timestamp(corte))&(x['fecha']>=lo)&(x['verificado']=='SI')]
    return [{'id':str(r['evento_id']),'fecha':str(r['fecha'].date()),
             'tipo':str(r['tipo_evento']),'descripcion':str(r['descripcion'])[:200]}
            for _,r in x.iterrows()]


def calcular_senal_sentimiento(carpeta: Path,corte: date,tasa_base_semanal: float):
    advertencias=[]
    if not USAR_SENTIMIENTO_PARA_SHOCKS:
        advertencias.append('Módulo de sentimiento desactivado por configuración.')
    try:
        pares,largo = _validar_y_preparar_serie(carpeta/'serie_sentimiento_diaria.csv')
    except (OSError,ValueError,KeyError,TypeError) as e:
        advertencias.append(f'Datos de sentimiento no disponibles o inválidos: {type(e).__name__}: {e}')
        pares=pd.DataFrame(columns=['fecha','tipo_fuente','brecha_sentimiento_7d','apta'])
        largo=pd.DataFrame()
    # IMPORTANTE: truncar ANTES de estimar novedades, no usar observaciones futuras.
    pares=pares[pares['fecha']<=pd.Timestamp(corte)].copy()
    pesos={'NOTICIA':PESO_NOTICIAS,'RED_SOCIAL':PESO_REDES}
    scores={}; nrefs={}; fechas={}; brechas={}; cobertura={}
    for fuente,peso in pesos.items():
        x=pares[(pares['tipo_fuente']==fuente)&(pares['apta'])&pares['brecha_sentimiento_7d'].notna()].sort_values('fecha')
        ultimas=x[x['fecha']>=pd.Timestamp(corte)-pd.Timedelta(days=DIAS_SEÑAL_RECIENTE-1)].copy()
        if len(x)==0 or len(ultimas)==0 or (pd.Timestamp(corte)-x['fecha'].iloc[-1]).days > DIAS_MAX_REZAGO_SENAL:
            scores[fuente]=0.;nrefs[fuente]=0;fechas[fuente]=None;brechas[fuente]=None;cobertura[fuente]=0.
            advertencias.append(f'{fuente}: falta señal reciente con cobertura suficiente.')
            continue
        # Comparación contra historia inmediatamente ANTERIOR a cada observación.
        # Usar máximo reciente captura episodios sin sumar el mismo evento día tras día.
        candidatos=[]
        for _,r in ultimas.iterrows():
            hist=x[(x['fecha'] < r['fecha']) &
                   (x['fecha'] >= r['fecha']-pd.Timedelta(days=DIAS_HISTORICO_SENAL))]['brecha_sentimiento_7d'].dropna()
            if len(hist)<MIN_HISTORICO_SENAL:continue
            med=float(np.median(hist))
            mad=float(np.median(np.abs(hist-med)))
            escala=max(0.15,1.4826*mad)
            magnitud=abs(float(r['brecha_sentimiento_7d'])-med)
            # No activar por variaciones triviales; umbral inicial (NO calibrado)
            z=max(0.,(magnitud-0.10)/escala)
            z=min(3.,z)
            candidatos.append((z,str(r['fecha'].date()),float(r['brecha_sentimiento_7d']),len(hist)))
        nrefs[fuente]=len(candidatos)
        if candidatos:
            mejor=max(candidatos,key=lambda y:y[0])
            scores[fuente]=float(mejor[0]);fechas[fuente]=mejor[1];brechas[fuente]=mejor[2]
            # Cobertura distinta de capacidad predictiva: señal disponible no equivale a votantes.
            cobertura[fuente]=1.
        else:
            scores[fuente]=0.;fechas[fuente]=None;brechas[fuente]=None;cobertura[fuente]=0.
            advertencias.append(f'{fuente}: menos de {MIN_HISTORICO_SENAL} referencias aptas anteriores.')
    puntaje=float(sum(pesos[f]*scores[f]*cobertura[f] for f in pesos))
    # No se utiliza el signo del sentimiento para empujar el margen electoral.
    multiplicador=float(min(CAP_MULTIPLICADOR_SHOCK,np.exp(GAMMA_SENTIMIENTO*puntaje))) if USAR_SENTIMIENTO_PARA_SHOCKS else 1.
    activo=bool(USAR_SENTIMIENTO_PARA_SHOCKS and any(cobertura.values()))
    return SenalSentimiento(
        activa=activo,corte=corte.isoformat(),ruta=str(carpeta/'serie_sentimiento_diaria.csv'),
        fecha_ultima_senal=max((d for d in fechas.values() if d),default=None),
        brechas_7d=brechas,puntajes_fuente=scores,n_referencias=nrefs,factores_cobertura=cobertura,
        puntuacion_ponderada=puntaje,multiplicador_lambda=multiplicador,
        tasa_base_semanal=float(tasa_base_semanal),tasa_condicional_semanal=float(tasa_base_semanal*multiplicador),
        eventos_contextuales=_eventos_hasta_corte(carpeta,corte), advertencias=advertencias),pares,largo



