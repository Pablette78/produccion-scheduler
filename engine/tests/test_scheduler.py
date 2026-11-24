from datetime import date, timedelta

from engine.calendario import Calendario
from engine.models import Faltante, Puesto, Trabajo
from engine.scheduler import calcular_programa


def _siguiente_lunes(d: date) -> date:
    while d.weekday() != 0:
        d += timedelta(days=1)
    return d


HOY = _siguiente_lunes(date(2026, 11, 24))


def _puesto_capacidad(nombre, predecesores, capacidad_diaria, componente="placas", lote=1):
    return Puesto(
        nombre=nombre,
        predecesores=predecesores,
        tipo="capacidad",
        unidad=componente,
        capacidad_diaria=capacidad_diaria,
        lote_traspaso=lote,
        componente=componente,
    )


def test_36_placas_a_12_por_dia_sin_cola_ocupa_3_dias_habiles():
    puestos = [_puesto_capacidad("Centro", [], capacidad_diaria=12)]
    trabajo = Trabajo(nv="1", cantidades={"placas": 36})

    [resultado] = calcular_programa(puestos, [trabajo], Calendario(), HOY)
    centro = resultado.por_puesto["Centro"]

    assert centro.inicio == HOY
    assert centro.fin == HOY + timedelta(days=2)  # lunes, martes, miércoles


def test_invariante_de_precedencia_ningun_puesto_termina_antes_que_su_predecesor():
    puestos = [
        _puesto_capacidad("Corte", [], capacidad_diaria=18),
        _puesto_capacidad("Filo", ["Corte"], capacidad_diaria=13),  # más lento, genera cola
        _puesto_capacidad("Centro", ["Filo"], capacidad_diaria=12),
    ]
    trabajo = Trabajo(nv="1", cantidades={"placas": 85})

    [resultado] = calcular_programa(puestos, [trabajo], Calendario(), HOY)
    corte, filo, centro = (resultado.por_puesto[n] for n in ("Corte", "Filo", "Centro"))

    assert corte.fin <= filo.fin
    assert filo.fin <= centro.fin
    assert corte.inicio <= filo.inicio
    assert filo.inicio <= centro.inicio


def test_mayor_prioridad_consume_capacidad_primero():
    puestos = [_puesto_capacidad("Centro", [], capacidad_diaria=12)]
    alta = Trabajo(nv="alta", cantidades={"placas": 12})
    baja = Trabajo(nv="baja", cantidades={"placas": 12})

    resultados = calcular_programa(puestos, [alta, baja], Calendario(), HOY)
    r_alta = next(r for r in resultados if r.trabajo.nv == "alta")
    r_baja = next(r for r in resultados if r.trabajo.nv == "baja")

    assert r_alta.por_puesto["Centro"].fin == HOY
    assert r_baja.por_puesto["Centro"].fin == HOY + timedelta(days=1)


def test_faltante_sin_fecha_frena_el_puesto_y_sus_sucesores_no_otras_ramas():
    puestos = [
        _puesto_capacidad("Centro", [], capacidad_diaria=100),
        _puesto_capacidad("Puertas", ["Centro"], capacidad_diaria=100, componente="puertas"),
        _puesto_capacidad("Cajones", ["Centro"], capacidad_diaria=100, componente="cajones"),
    ]
    trabajo = Trabajo(
        nv="1",
        cantidades={"placas": 10, "puertas": 6, "cajones": 4},
        faltantes=[Faltante(material="bisagras", puesto="Cajones")],
    )

    [resultado] = calcular_programa(puestos, [trabajo], Calendario(), HOY)

    assert resultado.por_puesto["Centro"].fin is not None
    assert resultado.por_puesto["Puertas"].fin is not None
    cajones = resultado.por_puesto["Cajones"]
    assert cajones.fin is None
    assert cajones.bloqueado_sin_fecha is True
    assert cajones.material_faltante == "bisagras"


def test_faltante_con_fecha_programa_el_puesto_desde_esa_fecha():
    llega = HOY + timedelta(days=10)
    puestos = [
        _puesto_capacidad("Centro", [], capacidad_diaria=100),
        _puesto_capacidad("Cajones", ["Centro"], capacidad_diaria=100, componente="cajones"),
    ]
    trabajo = Trabajo(
        nv="1",
        cantidades={"placas": 10, "cajones": 4},
        faltantes=[Faltante(material="bisagras", puesto="Cajones", fecha_estimada_llegada=llega)],
    )

    [resultado] = calcular_programa(puestos, [trabajo], Calendario(), HOY)

    assert resultado.por_puesto["Cajones"].inicio == llega


def test_lote_todo_con_capacidad_infinita_coincide_con_calculo_manual():
    puestos = [
        Puesto(
            nombre="DTC1",
            predecesores=[],
            tipo="capacidad",
            capacidad_diaria=10_000,
            lote_traspaso="todo",
            componente=None,
        )
    ]
    trabajo = Trabajo(nv="1", cantidades={})

    [resultado] = calcular_programa(puestos, [trabajo], Calendario(), HOY)
    dtc1 = resultado.por_puesto["DTC1"]

    # cálculo manual: con capacidad infinita, el trabajo (1 unidad) se
    # completa el mismo día que arranca.
    assert dtc1.inicio == HOY
    assert dtc1.fin == HOY


def test_avance_ya_realizado_se_descuenta_del_total():
    puestos = [_puesto_capacidad("Centro", [], capacidad_diaria=12)]
    trabajo = Trabajo(
        nv="1",
        cantidades={"placas": 36},
        avance_por_puesto={"Centro": 24},
    )

    [resultado] = calcular_programa(puestos, [trabajo], Calendario(), HOY)
    centro = resultado.por_puesto["Centro"]

    assert centro.inicio == HOY
    assert centro.fin == HOY  # quedan 12 placas, un solo día a 12/día


def test_semaforo_contra_ftf():
    puestos = [_puesto_capacidad("Centro", [], capacidad_diaria=12)]
    trabajo_a_tiempo = Trabajo(nv="1", cantidades={"placas": 12}, ftf=HOY + timedelta(days=5))
    trabajo_tarde = Trabajo(nv="2", cantidades={"placas": 12}, ftf=HOY - timedelta(days=1))

    resultados = calcular_programa(
        puestos, [trabajo_a_tiempo, trabajo_tarde], Calendario(), HOY
    )
    r_a_tiempo = next(r for r in resultados if r.trabajo.nv == "1")
    r_tarde = next(r for r in resultados if r.trabajo.nv == "2")

    assert r_a_tiempo.semaforo == "verde"
    assert r_tarde.semaforo == "rojo"
