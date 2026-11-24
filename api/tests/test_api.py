from datetime import date, timedelta


def test_puestos_sembrados_al_iniciar(client):
    respuesta = client.get("/puestos")
    assert respuesta.status_code == 200
    nombres = [p["nombre"] for p in respuesta.json()]
    assert nombres == [
        "DTC1",
        "Corte",
        "Filo",
        "Centro",
        "Laqueado",
        "Bancos",
        "LED",
        "Puertas",
        "Cajoneras",
        "Cajones",
    ]


def test_crear_y_listar_trabajo(client):
    respuesta = client.post(
        "/trabajos",
        json={"nv": "5-14969", "cliente": "Pérez", "cantidades": {"placas": 36}},
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["prioridad"] == 0

    respuesta = client.get("/trabajos")
    assert [t["nv"] for t in respuesta.json()] == ["5-14969"]


def test_no_permite_nv_duplicado(client):
    client.post("/trabajos", json={"nv": "1", "cantidades": {}})
    respuesta = client.post("/trabajos", json={"nv": "1", "cantidades": {}})
    assert respuesta.status_code == 409


def test_reordenar_trabajos_cambia_la_prioridad(client):
    client.post("/trabajos", json={"nv": "A", "cantidades": {}})
    client.post("/trabajos", json={"nv": "B", "cantidades": {}})

    respuesta = client.post("/trabajos/reordenar", json={"nv_en_orden": ["B", "A"]})
    assert respuesta.status_code == 200
    assert [t["nv"] for t in respuesta.json()] == ["B", "A"]


def test_reordenar_rechaza_lista_incompleta(client):
    client.post("/trabajos", json={"nv": "A", "cantidades": {}})
    client.post("/trabajos", json={"nv": "B", "cantidades": {}})

    respuesta = client.post("/trabajos/reordenar", json={"nv_en_orden": ["A"]})
    assert respuesta.status_code == 400


def test_programa_calcula_el_cronograma_end_to_end(client):
    client.post("/trabajos", json={"nv": "1", "cantidades": {"placas": 36}})

    respuesta = client.get("/programa")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()

    [trabajo] = cuerpo["trabajos"]
    assert trabajo["nv"] == "1"
    assert trabajo["fin_trabajo"] is not None
    assert "Centro" in trabajo["por_puesto"]
    assert len(cuerpo["carga_diaria"]) > 0


def test_programa_respeta_faltante_sin_fecha(client):
    client.post(
        "/trabajos",
        json={
            "nv": "1",
            "cantidades": {"placas": 10, "cajones": 4},
            "faltantes": [{"material": "bisagras", "puesto": "Cajones"}],
        },
    )

    respuesta = client.get("/programa")
    [trabajo] = respuesta.json()["trabajos"]

    assert trabajo["fin_trabajo"] is None
    assert trabajo["por_puesto"]["Cajones"]["bloqueado_sin_fecha"] is True
    assert trabajo["por_puesto"]["Cajones"]["material_faltante"] == "bisagras"


def test_feriado_vuelve_la_capacidad_cero_ese_dia(client):
    lunes = date.today()
    while lunes.weekday() != 0:
        lunes += timedelta(days=1)

    client.post("/calendario/feriados", json={"fecha": lunes.isoformat()})
    client.post("/trabajos", json={"nv": "1", "cantidades": {"placas": 12}})

    respuesta = client.get("/programa", params={"hoy": lunes.isoformat()})
    cuerpo = respuesta.json()

    carga_lunes = next(
        c
        for c in cuerpo["carga_diaria"]
        if c["puesto"] == "Centro" and c["fecha"] == lunes.isoformat()
    )
    assert carga_lunes["capacidad_total"] == 0


def test_no_permite_borrar_puesto_que_es_predecesor_de_otro(client):
    respuesta = client.delete("/puestos/Centro")
    assert respuesta.status_code == 400


def test_parametros_umbral_amarillo_se_puede_editar(client):
    respuesta = client.put("/parametros", json={"umbral_amarillo_dias": 3})
    assert respuesta.status_code == 200
    assert client.get("/parametros").json()["umbral_amarillo_dias"] == 3
