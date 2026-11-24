from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Callable, Optional

from .calendario import Calendario
from .models import Faltante, Puesto, Trabajo

HORIZONTE_DIAS_SIN_AVANCE = 3650  # ~10 años: guarda contra bloqueos eternos


class ConfiguracionInvalida(ValueError):
    pass


@dataclass
class _Curva:
    """Cantidad acumulada entregada por un puesto, para un trabajo, a lo
    largo del tiempo. `avance` es la cantidad ya hecha antes de hoy."""

    avance: float
    total: float
    fechas: list[date] = field(default_factory=list)
    acumulados: list[float] = field(default_factory=list)

    def agregar(self, dia: date, acumulado: float) -> None:
        self.fechas.append(dia)
        self.acumulados.append(acumulado)

    def valor_en(self, dia: date) -> float:
        if not self.fechas:
            return self.avance
        idx = bisect_right(self.fechas, dia) - 1
        if idx < 0:
            return self.avance
        return self.acumulados[idx]

    def fraccion_en(self, dia: date) -> float:
        if self.total <= 0:
            return 1.0
        return min(1.0, self.valor_en(dia) / self.total)


@dataclass
class ResultadoPuesto:
    puesto: str
    total: float
    avance: float
    inicio: Optional[date]
    fin: Optional[date]
    bloqueado_sin_fecha: bool = False
    material_faltante: Optional[str] = None


@dataclass
class ResultadoTrabajo:
    trabajo: Trabajo
    por_puesto: dict[str, ResultadoPuesto]
    fin_trabajo: Optional[date]
    desvio_dias: Optional[int]
    semaforo: Optional[str]  # "verde" | "amarillo" | "rojo" | None
    avance_pct: int = 0
    carga_pendiente_dias: float = 0.0


@dataclass
class CargaDia:
    puesto: str
    fecha: date
    capacidad_total: float  # ya ajustada por calendario (0 en feriado, etc.)
    capacidad_usada: float


def _orden_topologico(puestos: list[Puesto]) -> list[Puesto]:
    por_nombre = {p.nombre: p for p in puestos}
    for p in puestos:
        for pred in p.predecesores:
            if pred not in por_nombre:
                raise ConfiguracionInvalida(
                    f"El puesto '{p.nombre}' tiene un predecesor desconocido: '{pred}'"
                )

    grado_entrada = {p.nombre: len(p.predecesores) for p in puestos}
    sucesores: dict[str, list[str]] = {p.nombre: [] for p in puestos}
    for p in puestos:
        for pred in p.predecesores:
            sucesores[pred].append(p.nombre)

    listos = [nombre for nombre, g in grado_entrada.items() if g == 0]
    orden: list[str] = []
    while listos:
        nombre = listos.pop(0)
        orden.append(nombre)
        for siguiente in sucesores[nombre]:
            grado_entrada[siguiente] -= 1
            if grado_entrada[siguiente] == 0:
                listos.append(siguiente)

    if len(orden) != len(puestos):
        raise ConfiguracionInvalida("Los puestos tienen una dependencia circular")

    return [por_nombre[n] for n in orden]


def _aplica_a_trabajo(puesto: Puesto, trabajo: Trabajo) -> bool:
    if puesto.es_laqueado:
        return sum(trabajo.cantidad_a_laquear.values()) > 0
    # Si el puesto tiene una cantidad propia (placas, puertas, ...) y el
    # trabajo no lleva nada de eso, el puesto no es parte de su ruta —
    # independientemente de `condicion_de_uso` (que distingue puestos
    # siempre necesarios, como Centro, de puestos verdaderamente opcionales
    # como LED). Sin esto, un total en cero queda "sin fecha" en vez de
    # simplemente no aplicar, y bloquea el fin del trabajo.
    if puesto.componente is not None and trabajo.cantidades.get(puesto.componente, 0) <= 0:
        return False
    return True


def _total_del_puesto(puesto: Puesto, trabajo: Trabajo) -> float:
    if puesto.componente is not None:
        return trabajo.cantidades.get(puesto.componente, 0.0)
    return 1.0  # puestos sin componente propio (DTC1, Laqueado): el trabajo entero


def _floor_a_lote(disponible: float, lote, total: float) -> float:
    if disponible >= total:
        return total
    if lote == "todo" or lote is None:
        return 0.0
    if lote <= 0:
        return disponible
    return math.floor(disponible / lote) * lote


def _fraccion_predecesor(nombre: str, curvas: dict[str, _Curva], dia: date) -> float:
    """Si el predecesor no está en `curvas` es porque no le aplicaba al
    trabajo (su propia cantidad total era cero, sección "componente" de
    `_aplica_a_trabajo`) — no tiene nada que entregar, así que no debe
    frenar a nadie: se lo trata como ya 100% resuelto."""
    curva = curvas.get(nombre)
    return curva.fraccion_en(dia) if curva is not None else 1.0


def _disponible_en(
    dia: date,
    puesto: Puesto,
    curvas: dict[str, _Curva],
    es_laqueado: dict[str, bool],
    total_this: float,
    a_laquear_this: float,
) -> float:
    """Cantidad que el puesto puede haber procesado al cierre de `dia`.

    Lo que un puesto produce en un día recién está disponible para el
    siguiente al día siguiente: así los días de cada puesto se suman en vez
    de superponerse en una misma jornada. La excepción es Laqueado: sus
    días cuentan desde el día en que se envía la última pieza, y su `fin` es
    la fecha en que vuelve el material, que ya se puede usar ese día."""

    if not puesto.predecesores:
        return total_this

    laqueado_names = [n for n in puesto.predecesores if es_laqueado.get(n)]
    otros = [n for n in puesto.predecesores if not es_laqueado.get(n)]

    dia_entrega = dia if puesto.es_laqueado else dia - timedelta(days=1)
    frac_otro = min((_fraccion_predecesor(n, curvas, dia_entrega) for n in otros), default=1.0)

    if not laqueado_names:
        return _floor_a_lote(frac_otro * total_this, puesto.lote_traspaso, total_this)

    # El lote se aplica a lo no laqueado por separado: aun con lote "todo",
    # esas unidades no esperan a que vuelva Laqueado.
    total_no_laqueado = max(total_this - a_laquear_this, 0.0)
    disponible_no_laqueado = _floor_a_lote(
        frac_otro * total_no_laqueado, puesto.lote_traspaso, total_no_laqueado
    )
    laq_curva = curvas.get(laqueado_names[0])
    disponible_laqueado = a_laquear_this if (laq_curva and laq_curva.fraccion_en(dia) >= 1.0) else 0.0
    return disponible_no_laqueado + disponible_laqueado


def _simular_capacidad(
    puesto: Puesto,
    total_this: float,
    avance_this: float,
    dia_inicio_minimo: Optional[date],
    disponible_fn: Callable[[date], float],
    obtener_capacidad: Callable[[str, date], float],
    consumir_capacidad: Callable[[str, date, float], None],
    hoy: date,
) -> tuple[_Curva, Optional[date], Optional[date], bool]:
    curva = _Curva(avance=avance_this, total=total_this)

    if avance_this >= total_this:
        # Ya estaba terminado (el avance cargado cubre todo el total): no
        # hay nada que simular, y no debe figurar como "sin fecha" — eso
        # bloquearía el fin del trabajo entero (sección 7, regla 4).
        return curva, hoy, hoy, False

    if dia_inicio_minimo is None:
        # Faltante sin fecha estimada: no arranca, no consume capacidad,
        # no bloquea a otros trabajos (sección 6).
        return curva, None, None, True

    procesado = avance_this
    dia = dia_inicio_minimo
    inicio: Optional[date] = None
    fin: Optional[date] = None
    dias_sin_avance = 0

    while procesado < total_this:
        disponible = disponible_fn(dia)
        margen = disponible - procesado
        if margen > 0:
            cap_hoy = obtener_capacidad(puesto.nombre, dia)
            procesado_hoy = min(margen, cap_hoy) if cap_hoy > 0 else 0.0
        else:
            procesado_hoy = 0.0

        if procesado_hoy > 0:
            if inicio is None:
                inicio = dia
            consumir_capacidad(puesto.nombre, dia, procesado_hoy)
            procesado += procesado_hoy
            curva.agregar(dia, procesado)
            fin = dia
            dias_sin_avance = 0
        else:
            dias_sin_avance += 1
            if dias_sin_avance > HORIZONTE_DIAS_SIN_AVANCE:
                return curva, inicio, None, False

        dia += timedelta(days=1)

    return curva, inicio, fin, False


def _simular_tiempo_fijo(
    puesto: Puesto,
    total_this: float,
    avance_this: float,
    dia_inicio_minimo: Optional[date],
    disponible_fn: Callable[[date], float],
    calendario: Calendario,
    hoy: date,
) -> tuple[_Curva, Optional[date], Optional[date], bool]:
    curva = _Curva(avance=avance_this, total=total_this)

    if avance_this >= total_this:
        return curva, hoy, hoy, False

    if dia_inicio_minimo is None:
        return curva, None, None, True

    dia = dia_inicio_minimo
    limite = dia_inicio_minimo + timedelta(days=HORIZONTE_DIAS_SIN_AVANCE)
    inicio: Optional[date] = None
    while dia <= limite:
        if disponible_fn(dia) >= total_this:
            inicio = dia
            break
        dia += timedelta(days=1)

    if inicio is None:
        return curva, None, None, False

    if puesto.modo_dias == "habiles":
        fin = calendario.sumar_dias_habiles(inicio, puesto.dias_fijos or 0)
    else:
        fin = inicio + timedelta(days=puesto.dias_fijos or 0)

    curva.agregar(fin, total_this)
    return curva, inicio, fin, False


def _faltante_demora(
    faltante: Faltante,
    puesto: Puesto,
    turno: date,
    resultado_por_puesto: dict[str, ResultadoPuesto],
) -> bool:
    """True si el material faltante es lo que frena al puesto (llega después
    de que le toque el turno y de que le entreguen los puestos anteriores)."""

    llegada = faltante.fecha_estimada_llegada
    if llegada is None:
        return True
    fines = [resultado_por_puesto[n].fin for n in puesto.predecesores if n in resultado_por_puesto]
    return llegada > max([turno, *(f for f in fines if f is not None)])


def _avance_y_carga(
    resultado_por_puesto: dict[str, ResultadoPuesto], capacidad_diaria: dict[str, float]
) -> tuple[int, float]:
    """(% de avance, carga pendiente) de un trabajo, midiendo lo que lleva
    cada puesto en días de su capacidad — así 10 placas y 10 cajones no pesan
    igual. Los puestos de tiempo fijo (Laqueado) no cuentan: no ocupan
    capacidad propia. El % se redondea hacia abajo, para que 100% signifique
    siempre que no queda nada pendiente."""

    total = hecho = 0.0
    for r in resultado_por_puesto.values():
        capacidad = capacidad_diaria.get(r.puesto) or 0.0
        if capacidad <= 0:
            continue
        total += r.total / capacidad
        hecho += min(r.avance, r.total) / capacidad
    if total <= 0:
        return 0, 0.0
    return math.floor(100 * hecho / total + 1e-9), total - hecho


def calcular_programa(
    puestos: list[Puesto],
    trabajos_en_orden: list[Trabajo],
    calendario: Calendario,
    hoy: date,
    umbral_amarillo_dias: int = 0,
    devolver_carga_diaria: bool = False,
):
    """Calcula el cronograma completo. `trabajos_en_orden` debe venir en
    orden de prioridad (el primero es el de mayor prioridad y consume
    capacidad primero). El cronograma siempre arranca desde `hoy`.

    Cada puesto atiende los trabajos en el orden de la tabla: uno no empieza
    hasta que el puesto terminó lo pendiente de los de arriba, así que un
    trabajo grande atrasa a todos los que tiene debajo. La excepción son los
    que están esperando algo externo (material faltante o la vuelta de
    Laqueado): esos no frenan al resto (sección 6).

    Devuelve la lista de `ResultadoTrabajo`. Si `devolver_carga_diaria` es
    True, devuelve en cambio una tupla `(resultados, carga_diaria)`, donde
    `carga_diaria` es una lista de `CargaDia` (capacidad usada vs. total por
    puesto y día, sección 8.2 — "carga diaria por puesto contra su
    capacidad")."""

    # Un trabajo ya terminado (fecha_real_terminado cargada) no debe seguir
    # consumiendo capacidad ni aparecer en el cronograma activo.
    trabajos_en_orden = [t for t in trabajos_en_orden if t.fecha_real_terminado is None]

    orden_puestos = _orden_topologico(puestos)
    es_laqueado = {p.nombre: p.es_laqueado for p in puestos}

    capacidad_restante: dict[tuple[str, date], float] = {}
    capacidad_diaria_por_puesto = {p.nombre: p.capacidad_diaria or 0.0 for p in puestos}

    def obtener_capacidad(nombre_puesto: str, dia: date) -> float:
        clave = (nombre_puesto, dia)
        if clave not in capacidad_restante:
            capacidad_restante[clave] = calendario.capacidad_del_dia(
                nombre_puesto, dia, capacidad_diaria_por_puesto[nombre_puesto]
            )
        return capacidad_restante[clave]

    def consumir_capacidad(nombre_puesto: str, dia: date, cantidad: float) -> None:
        capacidad_restante[(nombre_puesto, dia)] = obtener_capacidad(nombre_puesto, dia) - cantidad

    # puesto -> último día ocupado por los trabajos de arriba en la tabla
    ocupado_hasta: dict[str, date] = {}

    resultados: list[ResultadoTrabajo] = []

    for trabajo in trabajos_en_orden:
        curvas_por_puesto: dict[str, _Curva] = {}
        resultado_por_puesto: dict[str, ResultadoPuesto] = {}
        espera_externa: set[str] = set()

        for puesto in orden_puestos:
            if not _aplica_a_trabajo(puesto, trabajo):
                continue

            total_this = _total_del_puesto(puesto, trabajo)
            avance_this = trabajo.avance_por_puesto.get(puesto.nombre, 0.0)
            a_laquear_this = (
                trabajo.cantidad_a_laquear.get(puesto.componente, 0.0)
                if puesto.componente is not None
                else 0.0
            )

            faltante = trabajo.faltante_en(puesto.nombre)
            material_faltante = faltante.material if faltante else None
            # Respeta la cola del puesto: no arranca antes de que terminen los
            # trabajos de arriba (puede usar lo que sobra de ese último día).
            turno = max(hoy, ocupado_hasta.get(puesto.nombre, hoy))
            if faltante is None:
                dia_inicio_minimo: Optional[date] = turno
            elif faltante.fecha_estimada_llegada is not None:
                dia_inicio_minimo = max(turno, faltante.fecha_estimada_llegada)
            else:
                dia_inicio_minimo = None  # sin fecha: bloqueado

            pendiente = avance_this < total_this
            if pendiente and (
                (faltante is not None and _faltante_demora(faltante, puesto, turno, resultado_por_puesto))
                or any(n in espera_externa for n in puesto.predecesores)
                or (a_laquear_this > 0 and any(es_laqueado[n] and n in curvas_por_puesto for n in puesto.predecesores))
            ):
                espera_externa.add(puesto.nombre)

            def disponible_fn(dia: date, puesto=puesto, total_this=total_this, a_laquear_this=a_laquear_this) -> float:
                return _disponible_en(
                    dia,
                    puesto,
                    curvas_por_puesto,
                    es_laqueado,
                    total_this,
                    a_laquear_this,
                )

            if puesto.tipo == "capacidad":
                curva, inicio, fin, bloqueado_sin_fecha = _simular_capacidad(
                    puesto,
                    total_this,
                    avance_this,
                    dia_inicio_minimo,
                    disponible_fn,
                    obtener_capacidad,
                    consumir_capacidad,
                    hoy,
                )
            else:
                curva, inicio, fin, bloqueado_sin_fecha = _simular_tiempo_fijo(
                    puesto,
                    total_this,
                    avance_this,
                    dia_inicio_minimo,
                    disponible_fn,
                    calendario,
                    hoy,
                )

            curvas_por_puesto[puesto.nombre] = curva
            if (
                puesto.tipo == "capacidad"
                and pendiente
                and fin is not None
                and puesto.nombre not in espera_externa
            ):
                ocupado_hasta[puesto.nombre] = max(turno, fin)
            resultado_por_puesto[puesto.nombre] = ResultadoPuesto(
                puesto=puesto.nombre,
                total=total_this,
                avance=avance_this,
                inicio=inicio,
                fin=fin,
                bloqueado_sin_fecha=bloqueado_sin_fecha,
                material_faltante=material_faltante,
            )

        fines = [r.fin for r in resultado_por_puesto.values()]
        fin_trabajo = max(fines) if fines and all(f is not None for f in fines) else None

        desvio_dias: Optional[int] = None
        semaforo: Optional[str] = None
        if fin_trabajo is not None and trabajo.ftf is not None:
            desvio_dias = (fin_trabajo - trabajo.ftf).days
            if desvio_dias <= 0:
                semaforo = "verde"
            elif desvio_dias <= umbral_amarillo_dias:
                semaforo = "amarillo"
            else:
                semaforo = "rojo"

        avance_pct, carga_pendiente = _avance_y_carga(resultado_por_puesto, capacidad_diaria_por_puesto)

        resultados.append(
            ResultadoTrabajo(
                trabajo=trabajo,
                por_puesto=resultado_por_puesto,
                fin_trabajo=fin_trabajo,
                desvio_dias=desvio_dias,
                semaforo=semaforo,
                avance_pct=avance_pct,
                carga_pendiente_dias=carga_pendiente,
            )
        )

    if not devolver_carga_diaria:
        return resultados

    # La simulación solo consulta `capacidad_restante` en los días donde
    # algún trabajo tenía algo disponible para procesar. Para que la
    # carga diaria muestre el calendario completo (incluidos los días
    # ociosos, para ver dónde hay margen), se completa explícitamente
    # cada puesto desde hoy hasta el fin más lejano de todos los trabajos.
    fines_de_trabajos = [r.fin_trabajo for r in resultados if r.fin_trabajo is not None]
    fecha_hasta = max(fines_de_trabajos) if fines_de_trabajos else hoy
    for puesto in puestos:
        dia = hoy
        while dia <= fecha_hasta:
            obtener_capacidad(puesto.nombre, dia)
            dia += timedelta(days=1)

    carga_diaria = []
    for (nombre_puesto, dia), restante in sorted(capacidad_restante.items(), key=lambda kv: kv[0]):
        capacidad_efectiva = calendario.capacidad_del_dia(
            nombre_puesto, dia, capacidad_diaria_por_puesto[nombre_puesto]
        )
        carga_diaria.append(
            CargaDia(
                puesto=nombre_puesto,
                fecha=dia,
                capacidad_total=capacidad_efectiva,
                capacidad_usada=capacidad_efectiva - restante,
            )
        )
    return resultados, carga_diaria
