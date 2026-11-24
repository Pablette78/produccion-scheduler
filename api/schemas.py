from __future__ import annotations

from datetime import date
from typing import Literal, Optional, Union

from pydantic import BaseModel

LoteTraspaso = Union[int, float, Literal["todo"]]


class PuestoIn(BaseModel):
    nombre: str
    predecesores: list[str] = []
    tipo: Literal["capacidad", "tiempo_fijo"] = "capacidad"
    unidad: str = ""
    capacidad_diaria: Optional[float] = None
    dias_fijos: Optional[int] = None
    modo_dias: Literal["corridos", "habiles"] = "corridos"
    lote_traspaso: LoteTraspaso = 1
    condicion_de_uso: Literal["siempre", "solo_si_el_trabajo_lo_lleva"] = "siempre"
    componente: Optional[str] = None
    es_laqueado: bool = False


class PuestoOut(PuestoIn):
    orden: int


class FaltanteIn(BaseModel):
    material: str
    puesto: str
    fecha_estimada_llegada: Optional[date] = None


class TrabajoIn(BaseModel):
    nv: str
    cliente: str = ""
    categoria: str = ""
    complejidad: int = 1
    vendedor: str = ""
    cantidades: dict[str, float] = {}
    cantidad_a_laquear: dict[str, float] = {}
    lleva_led: bool = False
    avance_por_puesto: dict[str, float] = {}
    ftf: Optional[date] = None
    fecha_real_terminado: Optional[date] = None
    faltantes: list[FaltanteIn] = []


class TrabajoOut(TrabajoIn):
    prioridad: int


class ReordenarTrabajosIn(BaseModel):
    nv_en_orden: list[str]


class FeriadoIn(BaseModel):
    fecha: date


class ExcepcionCalendarioIn(BaseModel):
    puesto: str
    fecha: date
    capacidad: float


class ParametrosIn(BaseModel):
    umbral_amarillo_dias: int


class ResultadoPuestoOut(BaseModel):
    puesto: str
    total: float
    avance: float
    inicio: Optional[date]
    fin: Optional[date]
    bloqueado_sin_fecha: bool
    material_faltante: Optional[str]


class ResultadoTrabajoOut(BaseModel):
    nv: str
    cliente: str
    ftf: Optional[date]
    fin_trabajo: Optional[date]
    desvio_dias: Optional[int]
    semaforo: Optional[str]
    por_puesto: dict[str, ResultadoPuestoOut]


class CargaDiaOut(BaseModel):
    puesto: str
    fecha: date
    capacidad_total: float
    capacidad_usada: float


class ProgramaOut(BaseModel):
    hoy: date
    trabajos: list[ResultadoTrabajoOut]
    carga_diaria: list[CargaDiaOut]
