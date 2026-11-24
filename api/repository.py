from __future__ import annotations

import json

from sqlmodel import Session, select

from engine.calendario import Calendario
from engine.config_default import UMBRAL_AMARILLO_DIAS_DEFAULT, puestos_predeterminados
from engine.models import Faltante, Puesto, Trabajo

from .db import ExcepcionCalendarioDB, FaltanteDB, FeriadoDB, ParametroDB, PuestoDB, TrabajoDB
from .importador_excel import FilaImportada

CLAVE_UMBRAL_AMARILLO = "umbral_amarillo_dias"


def lote_desde_texto(texto: str):
    if texto == "todo":
        return "todo"
    return float(texto) if "." in texto else int(texto)


def lote_a_texto(lote) -> str:
    return "todo" if lote == "todo" else str(lote)


def sembrar_datos_iniciales(session: Session) -> None:
    """Carga la configuración por defecto si la base está vacía (primer
    arranque de la app)."""

    if session.exec(select(PuestoDB)).first() is None:
        for orden, puesto in enumerate(puestos_predeterminados()):
            session.add(
                PuestoDB(
                    nombre=puesto.nombre,
                    orden=orden,
                    predecesores_json=json.dumps(puesto.predecesores),
                    tipo=puesto.tipo,
                    unidad=puesto.unidad,
                    capacidad_diaria=puesto.capacidad_diaria,
                    dias_fijos=puesto.dias_fijos,
                    modo_dias=puesto.modo_dias,
                    lote_traspaso=lote_a_texto(puesto.lote_traspaso),
                    condicion_de_uso=puesto.condicion_de_uso,
                    componente=puesto.componente,
                    es_laqueado=puesto.es_laqueado,
                )
            )

    if session.exec(select(ParametroDB).where(ParametroDB.clave == CLAVE_UMBRAL_AMARILLO)).first() is None:
        session.add(ParametroDB(clave=CLAVE_UMBRAL_AMARILLO, valor=str(UMBRAL_AMARILLO_DIAS_DEFAULT)))

    session.commit()


def cargar_puestos(session: Session) -> list[Puesto]:
    filas = session.exec(select(PuestoDB).order_by(PuestoDB.orden)).all()
    return [
        Puesto(
            nombre=fila.nombre,
            predecesores=json.loads(fila.predecesores_json),
            tipo=fila.tipo,
            unidad=fila.unidad,
            capacidad_diaria=fila.capacidad_diaria,
            dias_fijos=fila.dias_fijos,
            modo_dias=fila.modo_dias,
            lote_traspaso=lote_desde_texto(fila.lote_traspaso),
            condicion_de_uso=fila.condicion_de_uso,
            componente=fila.componente,
            es_laqueado=fila.es_laqueado,
        )
        for fila in filas
    ]


def cargar_calendario(session: Session) -> Calendario:
    feriados = {f.fecha for f in session.exec(select(FeriadoDB)).all()}
    excepciones = {
        (e.puesto, e.fecha): e.capacidad for e in session.exec(select(ExcepcionCalendarioDB)).all()
    }
    return Calendario(feriados=feriados, excepciones=excepciones)


def cargar_umbral_amarillo(session: Session) -> int:
    fila = session.exec(select(ParametroDB).where(ParametroDB.clave == CLAVE_UMBRAL_AMARILLO)).first()
    return int(fila.valor) if fila else UMBRAL_AMARILLO_DIAS_DEFAULT


def _trabajo_desde_db(fila: TrabajoDB) -> Trabajo:
    return Trabajo(
        nv=fila.nv,
        cliente=fila.cliente,
        categoria=fila.categoria,
        complejidad=fila.complejidad,
        vendedor=fila.vendedor,
        cantidades=json.loads(fila.cantidades_json),
        cantidad_a_laquear=json.loads(fila.cantidad_a_laquear_json),
        lleva_led=fila.lleva_led,
        avance_por_puesto=json.loads(fila.avance_por_puesto_json),
        ftf=fila.ftf,
        fecha_real_terminado=fila.fecha_real_terminado,
        prioridad=fila.prioridad,
        faltantes=[
            Faltante(material=f.material, puesto=f.puesto, fecha_estimada_llegada=f.fecha_estimada_llegada)
            for f in fila.faltantes
        ],
    )


def cargar_trabajos_en_orden(session: Session) -> list[Trabajo]:
    """Devuelve los trabajos en orden de prioridad (el primero consume
    capacidad primero)."""
    filas = session.exec(select(TrabajoDB).order_by(TrabajoDB.prioridad)).all()
    return [_trabajo_desde_db(f) for f in filas]


def aplicar_filas_importadas(session: Session, filas: list[FilaImportada]) -> tuple[int, int]:
    """Crea o actualiza trabajos a partir de filas importadas de Excel.

    Solo toca los campos que la fila trae mapeados (el resto de un trabajo
    existente queda como estaba) — así una planilla de puertas/cajones no
    pisa las cantidades que ya cargó la planilla de placas. Devuelve
    (creados, actualizados)."""

    prioridad_siguiente = (
        session.exec(select(TrabajoDB.prioridad).order_by(TrabajoDB.prioridad.desc())).first() or -1
    ) + 1
    creados = 0
    actualizados = 0

    for fila in filas:
        existente = session.exec(select(TrabajoDB).where(TrabajoDB.nv == fila.nv)).first()

        if existente is None:
            session.add(
                TrabajoDB(
                    nv=fila.nv,
                    cliente=fila.cliente or "",
                    categoria=fila.categoria or "",
                    complejidad=fila.complejidad or 1,
                    vendedor=fila.vendedor or "",
                    cantidades_json=json.dumps(fila.cantidades),
                    cantidad_a_laquear_json=json.dumps(fila.cantidad_a_laquear),
                    avance_por_puesto_json=json.dumps(fila.avance_por_puesto),
                    ftf=fila.ftf,
                    prioridad=prioridad_siguiente,
                )
            )
            prioridad_siguiente += 1
            creados += 1
            continue

        if fila.cliente is not None:
            existente.cliente = fila.cliente
        if fila.categoria is not None:
            existente.categoria = fila.categoria
        if fila.vendedor is not None:
            existente.vendedor = fila.vendedor
        if fila.complejidad is not None:
            existente.complejidad = fila.complejidad
        if fila.ftf is not None:
            existente.ftf = fila.ftf
        if fila.cantidades:
            cantidades = json.loads(existente.cantidades_json)
            cantidades.update(fila.cantidades)
            existente.cantidades_json = json.dumps(cantidades)
        if fila.cantidad_a_laquear:
            a_laquear = json.loads(existente.cantidad_a_laquear_json)
            a_laquear.update(fila.cantidad_a_laquear)
            existente.cantidad_a_laquear_json = json.dumps(a_laquear)
        if fila.avance_por_puesto:
            avance = json.loads(existente.avance_por_puesto_json)
            avance.update(fila.avance_por_puesto)
            existente.avance_por_puesto_json = json.dumps(avance)
        session.add(existente)
        actualizados += 1

    session.commit()
    return creados, actualizados
