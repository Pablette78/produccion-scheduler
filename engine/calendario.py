from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta


@dataclass
class Calendario:
    """Calendario laboral (sección 5).

    Base lunes a viernes. `feriados` y `excepciones` son editables desde la
    UI. Una excepción fija la capacidad de un puesto en una fecha puntual
    (por ejemplo un sábado trabajado, o capacidad reducida), sin importar si
    esa fecha es hábil o no.
    """

    feriados: set[date] = field(default_factory=set)
    # (puesto, fecha) -> capacidad de ese puesto ese día
    excepciones: dict[tuple[str, date], float] = field(default_factory=dict)

    def es_habil_base(self, dia: date) -> bool:
        return dia.weekday() < 5 and dia not in self.feriados

    def capacidad_del_dia(self, puesto: str, dia: date, capacidad_diaria: float) -> float:
        clave = (puesto, dia)
        if clave in self.excepciones:
            return self.excepciones[clave]
        if self.es_habil_base(dia):
            return capacidad_diaria
        return 0.0

    def sumar_dias_habiles(self, desde: date, cantidad: int) -> date:
        """Usado por puestos tiempo_fijo en modo `habiles`. Cuenta días
        hábiles del calendario base (feriados incluidos), sin mirar
        excepciones por puesto, porque no son de un puesto en particular."""
        dia = desde
        contados = 0
        while contados < cantidad:
            dia += timedelta(days=1)
            if self.es_habil_base(dia):
                contados += 1
        return dia
