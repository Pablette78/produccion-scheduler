import io
from datetime import date

from openpyxl import Workbook

from api.importador_excel import (
    ExcelInvalido,
    MapeoColumnas,
    interpretar_filas,
    leer_hoja,
    listar_hojas,
    parsear_fecha,
    parsear_numero,
)


def _excel_de_placas() -> bytes:
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Placas"
    hoja.append(["NV", "Cliente", "Placas", "FTF"])
    hoja.append(["5-14969", "Perez", 36, date(2026, 12, 20)])
    hoja.append(["5-15000", "Gomez", 20, "15/12/2026"])
    hoja.append([None, None, None, None])  # fila vacía, se debe ignorar
    buffer = io.BytesIO()
    libro.save(buffer)
    return buffer.getvalue()


def _excel_de_puertas() -> bytes:
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Puertas"
    hoja.append(["Nota de venta", "Puertas", "Puertas a laquear"])
    hoja.append(["5-14969", 6, 6])
    buffer = io.BytesIO()
    libro.save(buffer)
    return buffer.getvalue()


def test_listar_hojas():
    assert listar_hojas(_excel_de_placas()) == ["Placas"]


def test_leer_hoja_descarta_filas_vacias():
    hoja, columnas, filas = leer_hoja(_excel_de_placas())
    assert hoja == "Placas"
    assert columnas == ["NV", "Cliente", "Placas", "FTF"]
    assert len(filas) == 2


def test_leer_hoja_desconocida_falla():
    try:
        leer_hoja(_excel_de_placas(), hoja="NoExiste")
        assert False, "debería haber fallado"
    except ExcelInvalido:
        pass


def test_parsear_fecha_acepta_date_y_texto_dd_mm_aaaa():
    assert parsear_fecha(date(2026, 12, 20)) == date(2026, 12, 20)
    assert parsear_fecha("15/12/2026") == date(2026, 12, 15)
    assert parsear_fecha(None) is None


def test_parsear_numero_acepta_coma_decimal():
    assert parsear_numero("12,5") == 12.5
    assert parsear_numero(None) == 0.0
    assert parsear_numero(36) == 36.0


def test_interpretar_filas_mapea_cantidades_y_ftf():
    _, columnas, filas = leer_hoja(_excel_de_placas())
    mapeo = MapeoColumnas(
        columna_nv="NV",
        columna_cliente="Cliente",
        columna_ftf="FTF",
        cantidades={"placas": "Placas"},
    )
    filas_ok, errores = interpretar_filas(columnas, filas, mapeo)

    assert errores == []
    assert len(filas_ok) == 2
    assert filas_ok[0].nv == "5-14969"
    assert filas_ok[0].cliente == "Perez"
    assert filas_ok[0].cantidades == {"placas": 36.0}
    assert filas_ok[0].ftf == date(2026, 12, 20)
    assert filas_ok[1].ftf == date(2026, 12, 15)  # texto dd/mm/aaaa


def test_interpretar_filas_reporta_error_si_falta_nv():
    _, columnas, filas = leer_hoja(_excel_de_placas())
    filas.append([None, "Sin NV", 10, None])
    mapeo = MapeoColumnas(columna_nv="NV", cantidades={"placas": "Placas"})

    filas_ok, errores = interpretar_filas(columnas, filas, mapeo)

    assert len(filas_ok) == 2
    assert len(errores) == 1
    assert errores[0]["motivo"] == "Falta el NV"


def test_interpretar_filas_columna_de_otro_archivo_distinta_de_nv():
    _, columnas, filas = leer_hoja(_excel_de_puertas())
    mapeo = MapeoColumnas(
        columna_nv="Nota de venta",
        cantidades={"puertas": "Puertas"},
        cantidad_a_laquear={"puertas": "Puertas a laquear"},
    )

    filas_ok, errores = interpretar_filas(columnas, filas, mapeo)

    assert errores == []
    assert filas_ok[0].nv == "5-14969"
    assert filas_ok[0].cantidades == {"puertas": 6.0}
    assert filas_ok[0].cantidad_a_laquear == {"puertas": 6.0}


def test_interpretar_filas_columna_inexistente_falla():
    _, columnas, filas = leer_hoja(_excel_de_placas())
    mapeo = MapeoColumnas(columna_nv="NV", cantidades={"placas": "NoExiste"})
    try:
        interpretar_filas(columnas, filas, mapeo)
        assert False, "debería haber fallado"
    except ExcelInvalido:
        pass
