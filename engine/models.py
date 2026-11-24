from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal, Optional, Union

TipoPuesto = Literal["capacidad", "tiempo_fijo"]
ModoDias = Literal["corridos", "habiles"]
CondicionDeUso = Literal["siempre", "solo_si_el_trabajo_lo_lleva"]

LOTE_TODO: Literal["todo"] = "todo"
LoteTraspaso = Union[int, float, Literal["todo"]]


@dataclass
class Puesto:
    """Un puesto de la fábrica. La lista de puestos vive en una tabla
    editable desde la UI, no en el código (sección 2 del documento)."""

    nombre: str
    predecesores: list[str] = field(default_factory=list)
    tipo: TipoPuesto = "capacidad"
    unidad: str = "unidades"
    capacidad_diaria: Optional[float] = None
    dias_fijos: Optional[int] = None
    modo_dias: ModoDias = "corridos"
    lote_traspaso: LoteTraspaso = 1
    condicion_de_uso: CondicionDeUso = "siempre"

    # Campo propio del motor (no está en la tabla que ve el usuario):
    # qué cantidad del trabajo (sección 4, campo `cantidades`) consume/produce
    # este puesto. None = el puesto no tiene cantidad propia, representa al
    # trabajo completo como una sola unidad (ej. DTC1, Laqueado).
    componente: Optional[str] = None

    # Marca el puesto que implementa el circuito de Laqueado (sección 3):
    # tiempo fijo, lote "todo", y reparto de unidades laqueadas/no laqueadas
    # hacia los puestos sucesores. Es un flag en vez de comparar por nombre
    # para no hardcodear el puesto en el algoritmo.
    es_laqueado: bool = False


@dataclass
class Faltante:
    """Material faltante (sección 6)."""

    material: str
    puesto: str
    fecha_estimada_llegada: Optional[date] = None


@dataclass
class Trabajo:
    """Un trabajo a programar (sección 4)."""

    nv: str
    cliente: str = ""
    categoria: str = ""
    complejidad: int = 1
    vendedor: str = ""

    # componente -> cantidad total (ej. {"placas": 85, "puertas": 6, ...})
    cantidades: dict[str, float] = field(default_factory=dict)
    # componente -> cantidad a laquear (subconjunto de `cantidades`)
    cantidad_a_laquear: dict[str, float] = field(default_factory=dict)

    lleva_led: bool = False

    # puesto -> unidades ya procesadas en ese puesto (avance, sección 4)
    avance_por_puesto: dict[str, float] = field(default_factory=dict)

    ftf: Optional[date] = None
    fecha_real_terminado: Optional[date] = None

    # El orden de prioridad lo da la posición del trabajo en la lista que
    # se le pasa al motor (arrastrar y soltar en la UI), no este campo.
    # Se guarda solo a modo informativo/persistencia.
    prioridad: int = 0

    faltantes: list[Faltante] = field(default_factory=list)

    def faltante_en(self, puesto: str) -> Optional[Faltante]:
        for f in self.faltantes:
            if f.puesto == puesto:
                return f
        return None
