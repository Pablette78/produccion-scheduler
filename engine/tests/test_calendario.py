from datetime import date

from engine.calendario import Calendario


def test_fin_de_semana_no_suma_capacidad():
    cal = Calendario()
    sabado = date(2026, 11, 28)  # sábado
    assert cal.capacidad_del_dia("Corte", sabado, capacidad_diaria=18) == 0.0


def test_feriado_no_suma_capacidad():
    lunes_feriado = date(2026, 12, 7)  # lunes, marcado feriado
    cal = Calendario(feriados={lunes_feriado})
    assert cal.capacidad_del_dia("Corte", lunes_feriado, capacidad_diaria=18) == 0.0


def test_dia_habil_normal_usa_capacidad_diaria():
    martes = date(2026, 12, 8)
    cal = Calendario()
    assert cal.capacidad_del_dia("Corte", martes, capacidad_diaria=18) == 18


def test_excepcion_de_sabado_trabajado_si_suma_capacidad():
    sabado = date(2026, 11, 28)
    cal = Calendario(excepciones={("Corte", sabado): 60})
    assert cal.capacidad_del_dia("Corte", sabado, capacidad_diaria=18) == 60


def test_excepcion_no_afecta_otros_puestos_ni_otras_fechas():
    sabado = date(2026, 11, 28)
    cal = Calendario(excepciones={("Corte", sabado): 60})
    assert cal.capacidad_del_dia("Filo", sabado, capacidad_diaria=18) == 0.0


def test_sumar_dias_habiles_salta_fines_de_semana():
    viernes = date(2026, 11, 27)
    cal = Calendario()
    # desde el viernes, 1 día hábil cae el lunes siguiente
    assert cal.sumar_dias_habiles(viernes, 1) == date(2026, 11, 30)
