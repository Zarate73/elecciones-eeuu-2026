"""Tipos compartidos."""
from __future__ import annotations

from dataclasses import dataclass, asdict, field


class FuenteNoDisponible(ValueError):
    pass


@dataclass
class VotoTemprano:
    fuente: str
    url: str
    fecha_datos: str
    fecha_consulta: str
    registrados: int
    devueltas: int
    registro_dem: int
    registro_rep: int
    registro_otro: int
    devueltas_dem: int
    devueltas_rep: int
    devueltas_otro: int
    registro_edad: dict[str, int]
    devueltas_edad: dict[str, int]
    estado: str = 'actualizado'
    referencia_historica: dict = field(default_factory=dict)
    partido_edad: dict = field(default_factory=dict)   # {'dem': [[reg, dev] x 4 edades], ...}
    origen: str = ''                                  # 'api' | 'navegador' | 'cache'

    @property
    def fraccion_devuelta(self) -> float:
        return 100*self.devueltas/self.registrados

    def to_dict(self) -> dict:
        return asdict(self)


