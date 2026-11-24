from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from openpyxl import load_workbook


class ExcelInvalido(ValueError):
    pass


def listar_hojas(contenido: bytes) -> list[str]:
    libro = load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
    try:
        return libro.sheetnames
    finally:
        libro.close()


def leer_hoja(contenido: bytes, hoja: Optional[str] = None) -> tuple[str, list[str], list[list]]:
    """Lee una hoja del Excel. La primera fila no vacía se toma como
    encabezados; el resto son datos. Devuelve (nombre_de_hoja, encabezados,
    filas), con cada fila ya recortada/rellenada al largo de los
    encabezados."""

    libro = load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
    try:
        if hoja is not None and hoja not in libro.sheetnames:
            raise ExcelInvalido(f"La hoja '{hoja}' no existe en este archivo")
        hoja_activa = libro[hoja] if hoja else libro[libro.sheetnames[0]]

        filas_crudas = list(hoja_activa.iter_rows(values_only=True))
        if not filas_crudas:
            return hoja_activa.title, [], []

        encabezados = [
            str(valor).strip() if valor is not None else f"columna_{i + 1}"
            for i, valor in enumerate(filas_crudas[0])
        ]
        ancho = len(encabezados)

        filas = []
        for fila in filas_crudas[1:]:
            if fila is None or all(v is None for v in fila):
                continue
            fila = list(fila[:ancho]) + [None] * max(0, ancho - len(fila))
            filas.append(fila)

        return hoja_activa.title, encabezados, filas
    finally:
        libro.close()


def parsear_fecha(valor) -> Optional[date]:
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor).strip()
    for formato in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def parsear_numero(valor) -> float:
    if valor is None or valor == "":
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip().replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return 0.0


def parsear_texto(valor) -> str:
    if valor is None:
        return ""
    return str(valor).strip()


@dataclass
class MapeoColumnas:
    columna_nv: str
    columna_cliente: Optional[str] = None
    columna_categoria: Optional[str] = None
    columna_vendedor: Optional[str] = None
    columna_complejidad: Optional[str] = None
    columna_ftf: Optional[str] = None
    cantidades: dict[str, str] = field(default_factory=dict)
    cantidad_a_laquear: dict[str, str] = field(default_factory=dict)
    avance_por_puesto: dict[str, str] = field(default_factory=dict)


@dataclass
class FilaImportada:
    nv: str
    cliente: Optional[str] = None
    categoria: Optional[str] = None
    vendedor: Optional[str] = None
    complejidad: Optional[int] = None
    ftf: Optional[date] = None
    cantidades: dict[str, float] = field(default_factory=dict)
    cantidad_a_laquear: dict[str, float] = field(default_factory=dict)
    avance_por_puesto: dict[str, float] = field(default_factory=dict)


def interpretar_filas(
    encabezados: list[str], filas: list[list], mapeo: MapeoColumnas
) -> tuple[list[FilaImportada], list[dict]]:
    """Convierte las filas crudas del Excel en `FilaImportada`, aplicando el
    mapeo de columnas. Devuelve (filas_ok, errores), donde cada error es
    `{"fila": numero_de_fila_1_based, "motivo": texto}`. Una fila sin NV se
    reporta como error en vez de importarse a medias."""

    try:
        indice_nv = encabezados.index(mapeo.columna_nv)
    except ValueError:
        raise ExcelInvalido(f"La columna de NV '{mapeo.columna_nv}' no está en este archivo")

    def indice_de(nombre_columna: Optional[str]) -> Optional[int]:
        if nombre_columna is None:
            return None
        try:
            return encabezados.index(nombre_columna)
        except ValueError:
            raise ExcelInvalido(f"La columna '{nombre_columna}' no está en este archivo")

    indice_cliente = indice_de(mapeo.columna_cliente)
    indice_categoria = indice_de(mapeo.columna_categoria)
    indice_vendedor = indice_de(mapeo.columna_vendedor)
    indice_complejidad = indice_de(mapeo.columna_complejidad)
    indice_ftf = indice_de(mapeo.columna_ftf)
    indices_cantidades = {comp: indice_de(col) for comp, col in mapeo.cantidades.items()}
    indices_a_laquear = {comp: indice_de(col) for comp, col in mapeo.cantidad_a_laquear.items()}
    indices_avance = {puesto: indice_de(col) for puesto, col in mapeo.avance_por_puesto.items()}

    filas_ok: list[FilaImportada] = []
    errores: list[dict] = []

    for numero, fila in enumerate(filas, start=2):  # fila 1 = encabezados
        nv = parsear_texto(fila[indice_nv])
        if not nv:
            errores.append({"fila": numero, "motivo": "Falta el NV"})
            continue

        try:
            filas_ok.append(
                FilaImportada(
                    nv=nv,
                    cliente=parsear_texto(fila[indice_cliente]) if indice_cliente is not None else None,
                    categoria=parsear_texto(fila[indice_categoria]) if indice_categoria is not None else None,
                    vendedor=parsear_texto(fila[indice_vendedor]) if indice_vendedor is not None else None,
                    complejidad=(
                        int(parsear_numero(fila[indice_complejidad])) if indice_complejidad is not None else None
                    ),
                    ftf=parsear_fecha(fila[indice_ftf]) if indice_ftf is not None else None,
                    cantidades={
                        comp: parsear_numero(fila[idx]) for comp, idx in indices_cantidades.items() if idx is not None
                    },
                    cantidad_a_laquear={
                        comp: parsear_numero(fila[idx]) for comp, idx in indices_a_laquear.items() if idx is not None
                    },
                    avance_por_puesto={
                        puesto: parsear_numero(fila[idx])
                        for puesto, idx in indices_avance.items()
                        if idx is not None
                    },
                )
            )
        except Exception as e:  # datos corruptos en una fila puntual
            errores.append({"fila": numero, "motivo": str(e)})

    return filas_ok, errores
