"""Carga y valida config/california.toml."""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

try:                                    # Python >= 3.11
    import tomllib
except ModuleNotFoundError:             # pragma: no cover - Python 3.10
    import tomli as tomllib

RAIZ = Path(__file__).resolve().parent.parent
CONFIG_DEFECTO = RAIZ / 'config' / 'california.toml'


class Seccion(dict):
    """dict con acceso por atributo (cfg.modelo.w_kalshi)."""

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
    legado: Seccion
    sentimiento_propio: Seccion
    ejecucion: Seccion
    archivo: Path
    offline: bool = False
    corte_manual: date | None = None

    # ---- derivados ----
    @property
    def dia_eleccion(self) -> date:
        return date.fromisoformat(self.eleccion.dia_eleccion)

    @property
    def inicio_voto(self) -> date:
        return date.fromisoformat(self.eleccion.inicio_voto)

    @property
    def fecha_primaria(self) -> date:
        return date.fromisoformat(self.eleccion.fecha_primaria)

    def ruta(self, clave: str) -> Path:
        p = Path(self.rutas[clave])
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

    @property
    def sigma_sis_fijo(self) -> float | None:
        v = self.modelo.sigma_sis_pp
        return None if v in ('', None) else float(v)


def cargar_config(ruta: str | Path | None = None, *, offline: bool = False,
                  corte: str | None = None, modo_conteo: bool | None = None) -> Config:
    ruta = Path(ruta) if ruta else CONFIG_DEFECTO
    with open(ruta, 'rb') as f:
        crudo = tomllib.load(f)
    secciones = {k: Seccion(crudo.get(k, {})) for k in
                 ('eleccion', 'rutas', 'fuentes', 'modelo', 'legado', 'sentimiento_propio', 'ejecucion')}
    cfg = Config(**secciones, archivo=ruta, offline=offline,
                 corte_manual=date.fromisoformat(corte) if corte else None)
    if modo_conteo is not None:
        cfg.ejecucion['modo_conteo'] = modo_conteo
    if os.environ.get('PRONOSTICO_SIN_NAVEGADOR') == '1':        # GitHub Actions: sin Brave/Playwright
        cfg.fuentes['civiq_usar_navegador_respaldo'] = False
    validar(cfg)
    return cfg


def validar(cfg: Config) -> None:
    m = cfg.modelo
    errores = []
    if not 0 <= m.w_kalshi <= 1:
        errores.append('modelo.w_kalshi debe estar en [0, 1]')
    if not 0 <= m.w_m2 <= 1:
        errores.append('modelo.w_m2 debe estar en [0, 1]')
    if not 0 < m.penal_interna <= 1:
        errores.append('modelo.penal_interna debe estar en (0, 1]')
    if m.nu_colas <= 2:
        errores.append('modelo.nu_colas debe ser > 2 (varianza finita)')
    if m.k_sent_max < 1:
        errores.append('modelo.k_sent_max debe ser >= 1')
    if not 1_000 <= m.n_simulaciones <= 5_000_000:
        errores.append('modelo.n_simulaciones fuera de [1e3, 5e6]')
    if cfg.inicio_voto >= cfg.dia_eleccion:
        errores.append('eleccion.inicio_voto debe ser anterior a dia_eleccion')
    if errores:
        raise ValueError('Configuración inválida:\n  - ' + '\n  - '.join(errores))
