"""Lectura del Excel de encuestas y agregados (legado y M5)."""
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

MESES = {
    'jan': 1, 'january': 1, 'ene': 1, 'enero': 1, 'feb': 2, 'february': 2, 'febrero': 2,
    'mar': 3, 'march': 3, 'marzo': 3, 'apr': 4, 'april': 4, 'abr': 4, 'abril': 4,
    'may': 5, 'mayo': 5, 'jun': 6, 'june': 6, 'junio': 6, 'jul': 7, 'july': 7, 'julio': 7,
    'aug': 8, 'august': 8, 'ago': 8, 'agosto': 8, 'sep': 9, 'sept': 9, 'september': 9,
    'septiembre': 9, 'oct': 10, 'october': 10, 'octubre': 10, 'nov': 11, 'november': 11,
    'noviembre': 11, 'dec': 12, 'december': 12, 'dic': 12, 'diciembre': 12,
}
# Encuestas de campaña o de encuestadoras partidistas: «campaña de X», «(D)», «(R)»
PATRON_PARTIDISTA = re.compile(r'campana|\((?:d|r)\)')


def simplificar(s: object) -> str:
    txt = unicodedata.normalize('NFKD', str(s))
    return ''.join(c for c in txt if not unicodedata.combining(c)).lower().strip()


def identificar_familia(nombre: str) -> str:
    n = simplificar(nombre)
    if 'wolfson' in n:
        return 'David Wolfson'
    if 'berkeley igs' in n:
        return 'Berkeley IGS'
    if 'ppic' in n:
        return 'PPIC'
    if 'surveyusa' in n:
        return 'SurveyUSA'
    if 'independent voter' in n or n == 'ivn':
        return 'IVN'
    if 'citrin' in n:
        return 'Politico/Citrin Center'
    if 'kreate' in n:
        return 'Kreate Strategies'
    # resto: sin etiquetas «(R)», «(D)», «(para X)» ni texto tras « — », para que Wikipedia y 270toWin coincidan
    base = re.sub(r'\s*\([^)]*\)', '', str(nombre)).split(' — ')[0].strip()
    return base or str(nombre).strip()


def parsear_fecha_campo(s: object, anio: int = 2026) -> tuple[date, date, bool]:
    """Admite: 'Oct 1–2', 'hasta Oct 4', 'Jun 29–Jul 6'.

    Retorna (inicio, fin, rango_conocido). Si dice 'hasta', solo se conoce fin.
    """
    raw = simplificar(s).replace('–', '-').replace('—', '-')
    raw = re.sub(r'\b(hasta|until|through)\b', ' ', raw)
    raw = re.sub(r'\s+', ' ', raw).strip()
    year_matches = re.findall(r'\b(?:19|20)\d{2}\b', raw)
    year = int(year_matches[-1]) if year_matches else anio
    raw = re.sub(r'\b(?:19|20)\d{2}\b', ' ', raw).strip()
    parts = [p.strip() for p in raw.split('-')]
    if len(parts) not in (1, 2):
        raise ValueError(f'Rango de fecha no reconocido: {s!r}')

    def extraer(parte: str, mes_default: int | None = None) -> tuple[int, int]:
        v = re.fullmatch(r'([a-z]+)\s+(\d{1,2})', parte)
        if v:
            mes = MESES.get(v.group(1))
            if mes is None:
                raise ValueError(f'Mes desconocido en: {s!r}')
            return mes, int(v.group(2))
        v = re.fullmatch(r'(\d{1,2})', parte)
        if v and mes_default is not None:
            return mes_default, int(v.group(1))
        raise ValueError(f'Fecha sin formato admitido: {s!r}')

    m1, d1 = extraer(parts[0])
    if len(parts) == 1:
        fecha = date(year, m1, d1)
        return fecha, fecha, False
    m2, d2 = extraer(parts[1], mes_default=m1)
    fin = date(year, m2, d2)
    inicio = date(year - 1 if m1 > m2 else year, m1, d1)
    if inicio > fin:
        raise ValueError(f'Rango invertido: {s!r}')
    return inicio, fin, True


def valor_porcentual(x: object) -> float:
    if x is None or str(x).strip() == '' or simplificar(x) in ('n.d.', 'nd', 'nan'):
        raise ValueError('dato no disponible')
    return float(str(x).strip().replace('%', '').replace(',', '.'))


@dataclass
class Encuesta:
    encuestadora: str
    familia: str
    fecha_texto: str
    inicio: date
    fin: date
    fecha_efectiva: date
    intervalo_conocido: bool
    becerra: float
    hilton: float
    indecisos_otros: float
    encargada_campania: bool
    preprimaria: bool
    peso: float = 0.0
    origen: str = 'base'

    @property
    def becerra_bipartidista(self) -> float:
        return 100 * self.becerra / (self.becerra + self.hilton)

    @property
    def hilton_bipartidista(self) -> float:
        return 100 - self.becerra_bipartidista

    @property
    def margen_bipartidista(self) -> float:
        return self.becerra_bipartidista - self.hilton_bipartidista

def crear_encuesta(nombre: str, fecha_str, b, h, otro, fecha_primaria: date,
                   inicio: date | None = None, fin: date | None = None, rango: bool | None = None,
                   origen: str = 'base') -> Encuesta:
    """Valida y construye una Encuesta. Porcentajes en 0–1 o 0–100; deben sumar ~100."""
    if inicio is None or fin is None:
        inicio, fin, rango = parsear_fecha_campo(fecha_str)
    b, h, otro = valor_porcentual(b), valor_porcentual(h), valor_porcentual(otro)
    total = b + h + otro
    if .99 <= total <= 1.01:
        b, h, otro = b * 100, h * 100, otro * 100
        total *= 100
    if not 98.5 <= total <= 101.5:
        raise ValueError(f'porcentajes suman {total:.2f}%')
    if min(b, h, otro) < 0 or max(b, h, otro) > 100 or b + h <= 0:
        raise ValueError('porcentajes fuera de rango')
    medio = inicio + timedelta(days=(fin - inicio).days // 2)
    clave = simplificar(nombre)
    return Encuesta(
        encuestadora=nombre, familia=identificar_familia(nombre),
        fecha_texto=str(fecha_str), inicio=inicio, fin=fin,
        fecha_efectiva=medio, intervalo_conocido=bool(rango),
        becerra=b, hilton=h, indecisos_otros=otro,
        encargada_campania=bool(PATRON_PARTIDISTA.search(clave)),
        preprimaria=(fin < fecha_primaria), origen=origen,
    )


def cargar_encuestas_base(ruta: Path, corte: date, hoja: str, fecha_primaria: date):
    """Encuestas verificadas a mano: el Excel CALIFORNIA_GOBERNADOR-v3.xlsx (local) o su exportación
    data/encuestas_verificadas.csv (repositorio). Mismo resultado con cualquiera de los dos."""
    if not ruta.exists():
        raise FileNotFoundError(f'Falta {ruta}')
    if ruta.suffix.lower() == '.csv':
        t = pd.read_csv(ruta, dtype=str)
        crudas = [(r.encuestadora, r.fecha_campo, r.becerra, r.hilton, r.indecisos_otros) for r in t.itertuples()]
    else:
        crudas = leer_bloque_excel(ruta, hoja)
    registros, advertencias = [], []
    for nombre, fecha_str, b, h, otro in crudas:
        try:
            e = crear_encuesta(nombre, fecha_str, b, h, otro, fecha_primaria)
        except (ValueError, TypeError) as exc:
            advertencias.append(f'Encuesta descartada: {nombre} — {exc}')
            continue
        if e.fin > corte:
            advertencias.append(f'Excluida por fecha posterior al corte: {nombre} ({e.fin})')
            continue
        registros.append(e)
    return registros, advertencias


def leer_bloque_excel(ruta: Path, hoja: str) -> list[tuple]:
    """Lee filas etiquetadas / columnas de encuestas, según CALIFORNIA_GOBERNADOR-v3.xlsx."""
    matriz = pd.read_excel(ruta, sheet_name=hoja, header=None, dtype=object).values.tolist()
    etiquetas = {
        'nombre': ('encuestadora',),
        'fecha': ('survey dates', 'fecha levantamiento', 'fechas de levantamiento'),
        'becerra': ('xavier becerra',),
        'hilton': ('steve hilton',),
        'indecisos': ('indecisos / otros', 'indecisos/otros'),
    }
    filas = {}
    for i, fila in enumerate(matriz):
        primera = simplificar(fila[0])
        for campo, patrones in etiquetas.items():
            if campo not in filas and any(primera.startswith(p) for p in patrones):
                filas[campo] = i
    if len(filas) != 5:
        raise ValueError(f'No se encontraron las etiquetas requeridas: {filas}')
    crudas = []
    for j in range(1, len(matriz[0])):
        nombre = matriz[filas['nombre']][j]
        if pd.isna(nombre) or not str(nombre).strip():
            continue
        nombre = str(nombre).strip()
        clave = simplificar(nombre)
        if '(primaria)' in clave:
            break
        if 'promedio' in clave or 'prome' in clave:
            continue
        crudas.append((nombre, matriz[filas['fecha']][j], matriz[filas['becerra']][j],
                       matriz[filas['hilton']][j], matriz[filas['indecisos']][j]))
    return crudas


def cargar_encuestas_excel(ruta: Path, corte: date, hoja: str, fecha_primaria: date):
    """Compatibilidad con el notebook: solo la base verificada."""
    registros, advertencias = cargar_encuestas_base(ruta, corte, hoja, fecha_primaria)
    if not registros:
        raise ValueError('No hay encuestas comparables antes de la fecha de corte.')
    return registros, advertencias

def resumir(encuestas: list[Encuesta], corte: date, vida_media: float,
            usar_fin: bool = False) -> dict:
    if not encuestas:
        raise ValueError('No hay encuestas para el escenario')
    fechas = [e.fin if usar_fin else e.fecha_efectiva for e in encuestas]
    dias = np.array([(corte - f).days for f in fechas], dtype=float)
    pesos = np.exp(-np.log(2) * dias / vida_media)
    pesos /= pesos.sum()
    votos_b = np.array([e.becerra_bipartidista for e in encuestas], dtype=float)
    margenes = 2*votos_b - 100
    b = float(np.dot(pesos, votos_b))
    m = float(np.dot(pesos, margenes))
    # Dispersion de *encuestas*; NO equivale a incertidumbre del resultado final.
    dispersion = float(np.sqrt(np.dot(pesos, (margenes-m)**2) / (1-np.dot(pesos, pesos)))) if len(encuestas)>1 else float('nan')
    return {
        'becerra': b, 'hilton': 100-b, 'margen': m,
        'pesos': pesos, 'dispersion_encuestas': dispersion,
        'n_efectivo': 1/float(np.dot(pesos, pesos)),
        'numero_encuestas': len(encuestas),
    }

# ---------------------------------------------------------------------------------
# Agregado M5: corrige los tres sesgos detectados en la revisión
#   1) encuestas de campaña/partidistas a PENAL_INTERNA de peso
#   2) cada casa encuestadora cuenta ~1 vez (peso / sqrt(n encuestas de la familia))
#   3) fechas 'hasta X' -> campo de DIAS_CAMPO_DEFAULT días, no un solo día
# Es la misma función que se usa para calibrar sigma en el backtest (coherencia).
# ---------------------------------------------------------------------------------

def pesos_m5(fechas_medias, corte, partidistas, familias, vida_media=30.0, penal_interna=0.5):
    dias = np.array([max((corte - f).days, 0) for f in fechas_medias], dtype=float)
    w = np.exp(-np.log(2) * dias / vida_media)
    w *= np.where(np.asarray(partidistas, bool), penal_interna, 1.0)
    fam = pd.Series(list(familias))
    w /= np.sqrt(fam.map(fam.value_counts()).to_numpy(float))
    return w / w.sum()


def _fecha_media_m5(e, dias_campo_default=3):
    if e.intervalo_conocido:
        return e.fecha_efectiva
    return e.fin - timedelta(days=dias_campo_default // 2)


def resumir_mejorado(encuestas, corte, vida_media=30.0, penal_interna=0.5, dias_campo_default=3):
    if not encuestas:
        raise ValueError('No hay encuestas para M5')
    w = pesos_m5([_fecha_media_m5(e, dias_campo_default) for e in encuestas], corte,
                 [e.encargada_campania for e in encuestas], [e.familia for e in encuestas],
                 vida_media, penal_interna)
    m = np.array([e.margen_bipartidista for e in encuestas], float)
    mu = float(np.dot(w, m))
    disp = (float(np.sqrt(np.dot(w, (m - mu) ** 2) / (1 - np.dot(w, w)))) if len(m) > 1 else float('nan'))
    return {'becerra': 50 + mu / 2, 'hilton': 50 - mu / 2, 'margen': mu, 'pesos': w,
            'dispersion_encuestas': disp, 'n_efectivo': 1 / float(np.dot(w, w)),
            'numero_encuestas': len(encuestas)}


# Tabla de auditoría (del notebook original)
def tabla_encuestas(todas, incluidas, pesos):
    identificadores = {id(x): float(w) for x,w in zip(incluidas,pesos)}
    filas=[]
    for e in sorted(todas, key=lambda x:x.fin, reverse=True):
        filas.append({
            'Encuestadora':e.encuestadora, 'Familia':e.familia,
            'Fecha de campo':e.fecha_texto, 'Fecha ponderada':e.fecha_efectiva.isoformat(),
            'Becerra original %':e.becerra, 'Hilton original %':e.hilton,
            'Indecisos/otros %':e.indecisos_otros,
            'Becerra bipartidista %':e.becerra_bipartidista,
            'Margen bipartidista pp':e.margen_bipartidista,
            'Preprimaria':e.preprimaria, 'Encargada campaña':e.encargada_campania, 'Origen':e.origen,
            'Incluida':id(e) in identificadores, 'Peso':identificadores.get(id(e), 0.0),
        })
    return pd.DataFrame(filas)


