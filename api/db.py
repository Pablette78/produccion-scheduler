import os
from datetime import date
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel, create_engine

DEFAULT_SQLITE_PATH = "data/produccion.sqlite3"


class PuestoDB(SQLModel, table=True):
    __tablename__ = "puesto"

    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(unique=True, index=True)
    orden: int  # orden topológico de referencia, para mostrar la tabla

    # JSON-encoded list[str]
    predecesores_json: str = "[]"

    tipo: str = "capacidad"  # "capacidad" | "tiempo_fijo"
    unidad: str = ""
    capacidad_diaria: Optional[float] = None
    dias_fijos: Optional[int] = None
    modo_dias: str = "corridos"  # "corridos" | "habiles"

    # "todo" o un número, como texto (ej. "1", "todo")
    lote_traspaso: str = "1"

    condicion_de_uso: str = "siempre"  # "siempre" | "solo_si_el_trabajo_lo_lleva"
    componente: Optional[str] = None
    es_laqueado: bool = False


class TrabajoDB(SQLModel, table=True):
    __tablename__ = "trabajo"

    id: Optional[int] = Field(default=None, primary_key=True)
    nv: str = Field(unique=True, index=True)
    cliente: str = ""
    categoria: str = ""
    complejidad: int = 1
    vendedor: str = ""

    # JSON-encoded dict[str, float]
    cantidades_json: str = "{}"
    cantidad_a_laquear_json: str = "{}"
    avance_por_puesto_json: str = "{}"

    lleva_led: bool = False

    ftf: Optional[date] = None
    fecha_real_terminado: Optional[date] = None

    # Posición en la cola de prioridad: menor valor = mayor prioridad.
    # Se reasigna al reordenar (drag & drop en la UI).
    prioridad: int = 0

    faltantes: List["FaltanteDB"] = Relationship(
        back_populates="trabajo", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class FaltanteDB(SQLModel, table=True):
    __tablename__ = "faltante"

    id: Optional[int] = Field(default=None, primary_key=True)
    trabajo_id: int = Field(foreign_key="trabajo.id")
    material: str
    puesto: str
    fecha_estimada_llegada: Optional[date] = None

    trabajo: TrabajoDB = Relationship(back_populates="faltantes")


class FeriadoDB(SQLModel, table=True):
    __tablename__ = "feriado"

    id: Optional[int] = Field(default=None, primary_key=True)
    fecha: date = Field(unique=True)


class ExcepcionCalendarioDB(SQLModel, table=True):
    __tablename__ = "excepcion_calendario"

    id: Optional[int] = Field(default=None, primary_key=True)
    puesto: str
    fecha: date
    capacidad: float


class ParametroDB(SQLModel, table=True):
    """Valores editables sueltos: umbral del semáforo amarillo, etc.
    (sección 11)."""

    __tablename__ = "parametro"

    clave: str = Field(primary_key=True)
    valor: str


def crear_engine(sqlite_path: str = DEFAULT_SQLITE_PATH):
    carpeta = os.path.dirname(sqlite_path)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)
    return create_engine(f"sqlite:///{sqlite_path}", connect_args={"check_same_thread": False})


def crear_tablas(engine) -> None:
    SQLModel.metadata.create_all(engine)
