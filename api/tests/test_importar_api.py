import io
import json
from datetime import date

from openpyxl import Workbook


def _xlsx(filas: list[list], encabezados: list[str]) -> bytes:
    libro = Workbook()
    hoja = libro.active
    hoja.append(encabezados)
    for fila in filas:
        hoja.append(fila)
    buffer = io.BytesIO()
    libro.save(buffer)
    return buffer.getvalue()


def test_vista_previa_devuelve_columnas_y_muestra(client):
    archivo = _xlsx([["5-14969", "Perez", 36]], ["NV", "Cliente", "Placas"])

    respuesta = client.post(
        "/importar/excel/vista-previa",
        files={"archivo": ("placas.xlsx", archivo, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["columnas"] == ["NV", "Cliente", "Placas"]
    assert cuerpo["total_filas"] == 1
    assert cuerpo["filas_muestra"][0][0] == "5-14969"


def test_aplicar_importacion_crea_trabajo(client):
    archivo = _xlsx(
        [["5-14969", "Perez", 36, "20/12/2026"]],
        ["NV", "Cliente", "Placas", "FTF"],
    )
    mapeo = {
        "hoja": "Sheet",
        "columna_nv": "NV",
        "columna_cliente": "Cliente",
        "columna_ftf": "FTF",
        "cantidades": {"placas": "Placas"},
    }

    respuesta = client.post(
        "/importar/excel/aplicar",
        files={"archivo": ("placas.xlsx", archivo, "application/octet-stream")},
        data={"mapeo": json.dumps(mapeo)},
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"creados": 1, "actualizados": 0, "filas_con_error": []}

    [trabajo] = client.get("/trabajos").json()
    assert trabajo["nv"] == "5-14969"
    assert trabajo["cantidades"] == {"placas": 36.0}
    assert trabajo["ftf"] == "2026-12-20"


def test_segunda_importacion_de_otro_archivo_completa_sin_pisar_lo_anterior(client):
    archivo_placas = _xlsx([["5-14969", "Perez", 36]], ["NV", "Cliente", "Placas"])
    client.post(
        "/importar/excel/aplicar",
        files={"archivo": ("placas.xlsx", archivo_placas, "application/octet-stream")},
        data={
            "mapeo": json.dumps(
                {"hoja": "Sheet", "columna_nv": "NV", "columna_cliente": "Cliente", "cantidades": {"placas": "Placas"}}
            )
        },
    )

    archivo_puertas = _xlsx([["5-14969", 6]], ["Nota de venta", "Puertas"])
    respuesta = client.post(
        "/importar/excel/aplicar",
        files={"archivo": ("puertas.xlsx", archivo_puertas, "application/octet-stream")},
        data={
            "mapeo": json.dumps(
                {"hoja": "Sheet", "columna_nv": "Nota de venta", "cantidades": {"puertas": "Puertas"}}
            )
        },
    )

    assert respuesta.json() == {"creados": 0, "actualizados": 1, "filas_con_error": []}

    [trabajo] = client.get("/trabajos").json()
    assert trabajo["cliente"] == "Perez"  # no se pisó con la segunda importación
    assert trabajo["cantidades"] == {"placas": 36.0, "puertas": 6.0}


def test_fila_sin_nv_se_reporta_como_error(client):
    archivo = _xlsx([[None, "Sin NV", 10]], ["NV", "Cliente", "Placas"])

    respuesta = client.post(
        "/importar/excel/aplicar",
        files={"archivo": ("placas.xlsx", archivo, "application/octet-stream")},
        data={"mapeo": json.dumps({"hoja": "Sheet", "columna_nv": "NV", "cantidades": {"placas": "Placas"}})},
    )

    cuerpo = respuesta.json()
    assert cuerpo["creados"] == 0
    assert cuerpo["filas_con_error"] == [{"fila": 2, "motivo": "Falta el NV"}]
