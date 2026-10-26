"""Carga y valida config/illinois.toml."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

try:                                    # Python >= 3.11
    import tomllib
except ModuleNotFoundError:             # pragma: no cover - Python 3.10
    import tomli as tomllib

RAIZ = Path(__file__).resolve().parent.parent
CONFIG_DEFECTO = RAIZ / 'config' / 'illinois.toml'
SECCIONES = ('eleccion', 'rutas', 'fuentes', 'modelo', 'ejecucion')


class Seccion(dict):
    """dict con acceso por atributo (cfg.modelo.peso_mercados)."""

    def __getattr__(self, k: str) -> Any:
        try:
            return self[k]
        except KeyError as exc:
            raise AttributeError(f'Falta la clave de configuración: {k}') from exc


@dataclass
class Config:
    eleccion: Seccion
    rutas: Seccion
    fuentes: Seccion
    modelo: Seccion
    ejecucion: Seccion
    archivo: Path
    offline: bool = False
    corte_manual: date | None = None

    @property
    def dia_eleccion(self) -> date:
        return date.fromisoformat(self.eleccion.dia_eleccion)

    @property
    def fecha_nominacion(self) -> date:
        return date.fromisoformat(self.eleccion.fecha_nominacion)

    @property
    def corte(self) -> date:
        return self.corte_manual or datetime.now(ZoneInfo(self.eleccion.zona_horaria)).date()

    @property
    def dias_a_eleccion(self) -> int:
        return (self.dia_eleccion - self.corte).days

    def ruta(self, clave: str) -> Path:
        p = Path(self.rutas[clave])
        return p if p.is_absolute() else (RAIZ / p).resolve()

    @property
    def ruta_encuestas_base(self) -> Path | None:
        txt = str(self.rutas.get('encuestas_base', '') or '').strip()
        if not txt:
            return None
        p = Path(txt)
        return p if p.is_absolute() else (RAIZ / p).resolve()

    @property
    def dir_salidas(self) -> Path:
        return self.ruta('salidas')

    @property
    def dir_cache(self) -> Path:
        d = self.dir_salidas / 'cache'
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def dir_datos(self) -> Path:
        return self.ruta('datos')


def cargar_config(ruta: str | Path | None = None, *, offline: bool = False, corte: str | None = None) -> Config:
    ruta = Path(ruta) if ruta else CONFIG_DEFECTO
    with open(ruta, 'rb') as f:
        crudo = tomllib.load(f)
    cfg = Config(**{k: Seccion(crudo.get(k, {})) for k in SECCIONES}, archivo=ruta, offline=offline,
                 corte_manual=date.fromisoformat(corte) if corte else None)
    validar(cfg)
    return cfg


def validar(cfg: Config) -> None:
    m = cfg.modelo
    err = []
    if not 0 <= m.peso_mercados <= 1:
        err.append('modelo.peso_mercados debe estar en [0, 1]')
    if not 1_000 <= m.n_simulaciones <= 5_000_000:
        err.append('modelo.n_simulaciones fuera de [1e3, 5e6]')
    if m.min_encuestadoras < 1 or m.ventana_dias_eleccion < 7:
        err.append('modelo.min_encuestadoras >= 1 y ventana_dias_eleccion >= 7')
    if m.sigma_dia_pp < 0:
        err.append('modelo.sigma_dia_pp >= 0')
    if str(m.get('sesgo_regla', 'todas')) not in ('todas', 'k2'):
        err.append('modelo.sesgo_regla debe ser "todas" o "k2"')
    if cfg.fecha_nominacion >= cfg.dia_eleccion:
        err.append('fecha_nominacion debe ser anterior a dia_eleccion')
    if err:
        raise ValueError('Configuración inválida:\n  - ' + '\n  - '.join(err))
