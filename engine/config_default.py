from __future__ import annotations

from .models import Puesto

# Configuración inicial de puestos (sección 2 del documento). Es solo un
# valor por defecto: en la app real esta tabla se edita desde la UI.
#
# Parámetros marcados como "a definir" en el documento (sección 11) quedan
# con un valor por defecto razonable, editable:
#   - capacidad_diaria de LED y de DTC1
#   - lote_traspaso de cada puesto (default "todo": el trabajo pasa al
#     puesto siguiente recién cuando terminó completo, y los días de cada
#     puesto se suman)


def puestos_predeterminados() -> list[Puesto]:
    return [
        Puesto(
            nombre="DTC1",
            predecesores=[],
            tipo="capacidad",
            unidad="trabajos",
            capacidad_diaria=5,  # a definir (sección 11)
            lote_traspaso="todo",
            condicion_de_uso="siempre",
            componente=None,
        ),
        Puesto(
            nombre="Corte",
            predecesores=["DTC1"],
            tipo="capacidad",
            unidad="placas",
            capacidad_diaria=18,
            lote_traspaso="todo",
            condicion_de_uso="siempre",
            componente="placas",
        ),
        Puesto(
            nombre="Filo",
            predecesores=["Corte"],
            tipo="capacidad",
            unidad="placas",
            capacidad_diaria=18,
            lote_traspaso="todo",
            condicion_de_uso="siempre",
            componente="placas",
        ),
        Puesto(
            nombre="Centro",
            predecesores=["Filo"],
            tipo="capacidad",
            unidad="placas",
            capacidad_diaria=12,
            lote_traspaso="todo",
            condicion_de_uso="siempre",
            componente="placas",
        ),
        Puesto(
            nombre="Laqueado",
            predecesores=["Centro"],
            tipo="tiempo_fijo",
            unidad="",
            dias_fijos=15,
            modo_dias="corridos",
            lote_traspaso="todo",
            condicion_de_uso="solo_si_el_trabajo_lo_lleva",
            componente=None,
            es_laqueado=True,
        ),
        Puesto(
            nombre="Bancos",
            predecesores=["Centro", "Laqueado"],
            tipo="capacidad",
            unidad="placas",
            capacidad_diaria=20,
            lote_traspaso="todo",
            condicion_de_uso="siempre",
            componente="placas",
        ),
        Puesto(
            nombre="LED",
            predecesores=["Bancos"],
            tipo="capacidad",
            unidad="metros",
            capacidad_diaria=50,  # a definir (sección 11)
            lote_traspaso="todo",
            condicion_de_uso="solo_si_el_trabajo_lo_lleva",
            componente="led_metros",
        ),
        Puesto(
            nombre="Puertas",
            predecesores=["Centro", "Laqueado"],
            tipo="capacidad",
            unidad="puertas",
            capacidad_diaria=6,
            lote_traspaso="todo",
            condicion_de_uso="siempre",
            componente="puertas",
        ),
        Puesto(
            nombre="Cajoneras",
            predecesores=["Centro", "Laqueado"],
            tipo="capacidad",
            unidad="cajoneras",
            capacidad_diaria=5,
            lote_traspaso="todo",
            condicion_de_uso="siempre",
            componente="cajoneras",
        ),
        Puesto(
            nombre="Cajones",
            predecesores=["Centro", "Laqueado"],
            tipo="capacidad",
            unidad="cajones",
            capacidad_diaria=20,
            lote_traspaso="todo",
            condicion_de_uso="siempre",
            componente="cajones",
        ),
    ]


UMBRAL_AMARILLO_DIAS_DEFAULT = 0  # a definir (sección 11)
