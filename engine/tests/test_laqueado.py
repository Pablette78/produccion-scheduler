from datetime import date, timedelta

from engine.calendario import Calendario
from engine.models import Puesto, Trabajo
from engine.scheduler import calcular_programa


def _siguiente_lunes(d: date) -> date:
    while d.weekday() != 0:
        d += timedelta(days=1)
    return d


HOY = _siguiente_lunes(date(2026, 11, 24))


def _puestos():
    return [
        Puesto(
            nombre="Centro",
            predecesores=[],
            tipo="capacidad",
            capacidad_diaria=10_000,
            lote_traspaso=1,
            componente="placas",
        ),
        Puesto(
            nombre="Laqueado",
            predecesores=["Centro"],
            tipo="tiempo_fijo",
            dias_fijos=15,
            modo_dias="corridos",
            lote_traspaso="todo",
            condicion_de_uso="solo_si_el_trabajo_lo_lleva",
            es_laqueado=True,
        ),
        Puesto(
            nombre="Puertas",
            predecesores=["Centro", "Laqueado"],
            tipo="capacidad",
            capacidad_diaria=10_000,
            lote_traspaso=1,
            componente="puertas",
        ),
    ]


def test_laqueado_dura_15_dias_corridos_desde_la_ultima_pieza_enviada():
    trabajo = Trabajo(
        nv="1",
        cantidades={"placas": 10, "puertas": 6},
        cantidad_a_laquear={"puertas": 6},  # se laquean las 6 puertas
    )

    [resultado] = calcular_programa(_puestos(), [trabajo], Calendario(), HOY)
    centro = resultado.por_puesto["Centro"]
    laqueado = resultado.por_puesto["Laqueado"]

    assert centro.fin == HOY  # capacidad infinita, termina el mismo día
    assert laqueado.inicio == centro.fin
    # 15 días corridos: cuenta fines de semana, a diferencia de un plazo hábil
    assert laqueado.fin == laqueado.inicio + timedelta(days=15)


def test_puertas_no_laqueadas_se_procesan_antes_que_las_laqueadas():
    trabajo = Trabajo(
        nv="1",
        cantidades={"placas": 10, "puertas": 6},
        cantidad_a_laquear={"puertas": 2},  # 4 no laqueadas, 2 laqueadas
    )

    [resultado] = calcular_programa(_puestos(), [trabajo], Calendario(), HOY)
    centro = resultado.por_puesto["Centro"]
    laqueado = resultado.por_puesto["Laqueado"]
    puertas = resultado.por_puesto["Puertas"]

    # las 4 no laqueadas arrancan apenas Centro entrega (no esperan a Laqueado)
    assert puertas.inicio == centro.fin
    # pero el trabajo no cierra en Puertas hasta que vuelven las 2 laqueadas
    assert puertas.fin >= laqueado.fin


def test_todas_las_puertas_laqueadas_esperan_a_laqueado_completo():
    trabajo = Trabajo(
        nv="1",
        cantidades={"placas": 10, "puertas": 6},
        cantidad_a_laquear={"puertas": 6},  # todas laqueadas
    )

    [resultado] = calcular_programa(_puestos(), [trabajo], Calendario(), HOY)
    laqueado = resultado.por_puesto["Laqueado"]
    puertas = resultado.por_puesto["Puertas"]

    assert puertas.inicio == laqueado.fin


def test_trabajo_sin_laqueado_no_usa_el_puesto_laqueado():
    trabajo = Trabajo(
        nv="1",
        cantidades={"placas": 10, "puertas": 6},
        cantidad_a_laquear={},  # no laquea nada
    )

    [resultado] = calcular_programa(_puestos(), [trabajo], Calendario(), HOY)

    assert "Laqueado" not in resultado.por_puesto
    assert resultado.por_puesto["Puertas"].fin == resultado.por_puesto["Centro"].fin
