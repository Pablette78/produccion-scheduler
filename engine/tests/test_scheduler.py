from datetime import date, timedelta

from engine.calendario import Calendario
from engine.config_default import puestos_predeterminados
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


def test_puesto_ya_terminado_por_avance_no_deja_el_trabajo_sin_fecha():
    # Caso real: un trabajo viejo que ya pasó por todos los puestos (el
    # avance cargado cubre el total en cada uno). Ninguno de esos puestos
    # tiene más nada que hacer, y eso no debería dejar al trabajo entero
    # "sin fecha estimada" — antes lo hacía, porque un puesto ya completo
    # devolvía fin=None igual que uno bloqueado.
    puestos = [
        _puesto_capacidad("Corte", [], capacidad_diaria=18),
        _puesto_capacidad("Centro", ["Corte"], capacidad_diaria=12),
    ]
    trabajo = Trabajo(
        nv="1",
        cantidades={"placas": 4},
        avance_por_puesto={"Corte": 4, "Centro": 4},
    )

    [resultado] = calcular_programa(puestos, [trabajo], Calendario(), HOY)

    assert resultado.fin_trabajo == HOY
    assert resultado.por_puesto["Corte"].fin == HOY
    assert resultado.por_puesto["Centro"].fin == HOY


def test_trabajo_terminado_no_consume_capacidad_ni_aparece_en_el_programa():
    puestos = [_puesto_capacidad("Centro", [], capacidad_diaria=12)]
    terminado = Trabajo(
        nv="viejo",
        cantidades={"placas": 12},
        fecha_real_terminado=date(2026, 1, 1),
    )
    nuevo = Trabajo(nv="nuevo", cantidades={"placas": 12})

    resultados = calcular_programa(puestos, [terminado, nuevo], Calendario(), HOY)

    assert [r.trabajo.nv for r in resultados] == ["nuevo"]
    # si el terminado siguiera consumiendo capacidad, "nuevo" recién
    # arrancaría al día siguiente
    assert resultados[0].por_puesto["Centro"].fin == HOY


def test_los_dias_de_cada_puesto_se_suman():
    # 50 placas: 3 días de Corte (18/día) + 3 de Filo + 5 de Centro (12/día).
    puestos = [
        _puesto_capacidad("Corte", [], capacidad_diaria=18, lote="todo"),
        _puesto_capacidad("Filo", ["Corte"], capacidad_diaria=18, lote="todo"),
        _puesto_capacidad("Centro", ["Filo"], capacidad_diaria=12, lote="todo"),
    ]
    [resultado] = calcular_programa(
        puestos, [Trabajo(nv="1", cantidades={"placas": 50})], Calendario(), HOY
    )
    corte, filo, centro = (resultado.por_puesto[n] for n in ("Corte", "Filo", "Centro"))

    # HOY es lunes: lun-mié, jue-lun, mar-lun
    assert (corte.inicio, corte.fin) == (HOY, HOY + timedelta(days=2))
    assert (filo.inicio, filo.fin) == (HOY + timedelta(days=3), HOY + timedelta(days=7))
    assert (centro.inicio, centro.fin) == (HOY + timedelta(days=8), HOY + timedelta(days=14))


def test_un_trabajo_chico_no_pasa_por_dos_puestos_el_mismo_dia():
    puestos = [
        _puesto_capacidad("Corte", [], capacidad_diaria=18),
        _puesto_capacidad("Filo", ["Corte"], capacidad_diaria=18),
    ]
    [resultado] = calcular_programa(
        puestos, [Trabajo(nv="1", cantidades={"placas": 2})], Calendario(), HOY
    )

    assert resultado.por_puesto["Corte"].fin == HOY
    assert resultado.por_puesto["Filo"].inicio == HOY + timedelta(days=1)


def _corte_y_centro():
    return [
        _puesto_capacidad("Corte", [], capacidad_diaria=18, lote="todo"),
        _puesto_capacidad("Centro", ["Corte"], capacidad_diaria=12, lote="todo"),
    ]


def test_un_trabajo_grande_atrasa_a_los_de_abajo_y_no_a_los_de_arriba():
    # Los chicos ya están cortados y listos para Centro; el grande no. Aun
    # así, el que está debajo del grande espera su turno.
    arriba = Trabajo(nv="arriba", cantidades={"placas": 6}, avance_por_puesto={"Corte": 6})
    grande = Trabajo(nv="grande", cantidades={"placas": 50})
    abajo = Trabajo(nv="abajo", cantidades={"placas": 6}, avance_por_puesto={"Corte": 6})

    resultados = calcular_programa(
        _corte_y_centro(), [arriba, grande, abajo], Calendario(), HOY
    )
    centro = {r.trabajo.nv: r.por_puesto["Centro"] for r in resultados}

    assert centro["arriba"].fin == HOY
    # 50 = 4 días de 12 + 2 placas; ese último día sobran 10 y "abajo" entra ahí
    assert centro["grande"].fin > HOY + timedelta(days=7)
    assert centro["abajo"].inicio == centro["grande"].fin
    assert centro["abajo"].fin == centro["grande"].fin


def test_mover_un_trabajo_en_la_tabla_cambia_las_fechas():
    grande = Trabajo(nv="grande", cantidades={"placas": 50})
    chico = Trabajo(nv="chico", cantidades={"placas": 6})

    def fin_chico(orden):
        resultados = calcular_programa(_corte_y_centro(), orden, Calendario(), HOY)
        return next(r.fin_trabajo for r in resultados if r.trabajo.nv == "chico")

    assert fin_chico([chico, grande]) == HOY + timedelta(days=1)
    assert fin_chico([grande, chico]) > HOY + timedelta(days=7)


def test_trabajo_esperando_material_no_frena_a_los_de_abajo():
    for llegada in (None, HOY + timedelta(days=30)):
        frenado = Trabajo(
            nv="frenado",
            cantidades={"placas": 6},
            faltantes=[Faltante(material="placa", puesto="Corte", fecha_estimada_llegada=llegada)],
        )
        abajo = Trabajo(nv="abajo", cantidades={"placas": 6})

        resultados = calcular_programa(_corte_y_centro(), [frenado, abajo], Calendario(), HOY)
        r_abajo = next(r for r in resultados if r.trabajo.nv == "abajo")

        assert r_abajo.fin_trabajo == HOY + timedelta(days=1)


def test_carga_diaria_refleja_capacidad_usada():
    puestos = [_puesto_capacidad("Centro", [], capacidad_diaria=12)]
    trabajo = Trabajo(nv="1", cantidades={"placas": 12})

    _, carga_diaria = calcular_programa(
        puestos, [trabajo], Calendario(), HOY, devolver_carga_diaria=True
    )

    carga_hoy = next(c for c in carga_diaria if c.puesto == "Centro" and c.fecha == HOY)
    assert carga_hoy.capacidad_total == 12
    assert carga_hoy.capacidad_usada == 12


def test_trabajo_sin_placas_pero_con_cajoneras_no_rompe_el_calculo():
    # Caso real: un trabajo con "cantidad de placas" en cero (no pasa por
    # Centro) pero con cajoneras a producir. Cajoneras depende de Centro y
    # de Laqueado; Centro no le aplica a este trabajo (total 0), lo que no
    # debería frenar ni romper el cálculo de Cajoneras.
    trabajo = Trabajo(nv="5-15043", cantidades={"cajoneras": 1})

    [resultado] = calcular_programa(puestos_predeterminados(), [trabajo], Calendario(), HOY)

    assert "Centro" not in resultado.por_puesto
    cajoneras = resultado.por_puesto["Cajoneras"]
    assert cajoneras.inicio == HOY
    assert cajoneras.fin is not None


def test_avance_y_carga_pendiente_se_miden_en_dias_de_cada_puesto():
    puestos = [
        _puesto_capacidad("Corte", [], capacidad_diaria=18),
        _puesto_capacidad("Centro", ["Corte"], capacidad_diaria=12),
    ]
    # Corte: 36/18 = 2 días (hechos). Centro: 36/12 = 3 días (1 hecho).
    trabajo = Trabajo(
        nv="1", cantidades={"placas": 36}, avance_por_puesto={"Corte": 99, "Centro": 12}
    )

    [resultado] = calcular_programa(puestos, [trabajo], Calendario(), HOY)

    assert resultado.avance_pct == 60
    assert resultado.carga_pendiente_dias == 2


def test_100_por_ciento_solo_si_no_queda_nada_pendiente():
    puestos = [_puesto_capacidad("Centro", [], capacidad_diaria=12)]

    def pct(hecho):
        trabajo = Trabajo(nv="1", cantidades={"placas": 1000}, avance_por_puesto={"Centro": hecho})
        return calcular_programa(puestos, [trabajo], Calendario(), HOY)[0].avance_pct

    assert pct(0) == 0
    assert pct(999) == 99
    assert pct(1000) == 100


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
