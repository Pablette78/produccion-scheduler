from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import date
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from engine.scheduler import calcular_programa

from . import repository
from .db import (
    ExcepcionCalendarioDB,
    FaltanteDB,
    FeriadoDB,
    ParametroDB,
    PuestoDB,
    TrabajoDB,
    crear_engine,
    crear_tablas,
)
from .schemas import (
    ExcepcionCalendarioIn,
    FeriadoIn,
    ParametrosIn,
    ProgramaOut,
    PuestoIn,
    PuestoOut,
    ReordenarTrabajosIn,
    ResultadoPuestoOut,
    ResultadoTrabajoOut,
    TrabajoIn,
    TrabajoOut,
)

_engine = crear_engine()


def get_session():
    with Session(_engine) as session:
        yield session


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    crear_tablas(_engine)
    with Session(_engine) as session:
        repository.sembrar_datos_iniciales(session)
    yield


app = FastAPI(title="Programador de producción", lifespan=ciclo_de_vida)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------
# Puestos
# --------------------------------------------------------------------------


def _puesto_out(fila: PuestoDB) -> PuestoOut:
    return PuestoOut(
        nombre=fila.nombre,
        orden=fila.orden,
        predecesores=json.loads(fila.predecesores_json),
        tipo=fila.tipo,
        unidad=fila.unidad,
        capacidad_diaria=fila.capacidad_diaria,
        dias_fijos=fila.dias_fijos,
        modo_dias=fila.modo_dias,
        lote_traspaso=repository.lote_desde_texto(fila.lote_traspaso),
        condicion_de_uso=fila.condicion_de_uso,
        componente=fila.componente,
        es_laqueado=fila.es_laqueado,
    )


@app.get("/puestos", response_model=list[PuestoOut])
def listar_puestos(session: Session = Depends(get_session)):
    filas = session.exec(select(PuestoDB).order_by(PuestoDB.orden)).all()
    return [_puesto_out(f) for f in filas]


@app.post("/puestos", response_model=PuestoOut, status_code=201)
def crear_puesto(datos: PuestoIn, session: Session = Depends(get_session)):
    if session.exec(select(PuestoDB).where(PuestoDB.nombre == datos.nombre)).first():
        raise HTTPException(409, f"Ya existe un puesto llamado '{datos.nombre}'")

    orden_maximo = session.exec(select(PuestoDB.orden).order_by(PuestoDB.orden.desc())).first()
    fila = PuestoDB(
        nombre=datos.nombre,
        orden=(orden_maximo or 0) + 1,
        predecesores_json=json.dumps(datos.predecesores),
        tipo=datos.tipo,
        unidad=datos.unidad,
        capacidad_diaria=datos.capacidad_diaria,
        dias_fijos=datos.dias_fijos,
        modo_dias=datos.modo_dias,
        lote_traspaso=repository.lote_a_texto(datos.lote_traspaso),
        condicion_de_uso=datos.condicion_de_uso,
        componente=datos.componente,
        es_laqueado=datos.es_laqueado,
    )
    session.add(fila)
    session.commit()
    session.refresh(fila)
    return _puesto_out(fila)


@app.put("/puestos/{nombre}", response_model=PuestoOut)
def actualizar_puesto(nombre: str, datos: PuestoIn, session: Session = Depends(get_session)):
    fila = session.exec(select(PuestoDB).where(PuestoDB.nombre == nombre)).first()
    if fila is None:
        raise HTTPException(404, f"No existe el puesto '{nombre}'")

    fila.nombre = datos.nombre
    fila.predecesores_json = json.dumps(datos.predecesores)
    fila.tipo = datos.tipo
    fila.unidad = datos.unidad
    fila.capacidad_diaria = datos.capacidad_diaria
    fila.dias_fijos = datos.dias_fijos
    fila.modo_dias = datos.modo_dias
    fila.lote_traspaso = repository.lote_a_texto(datos.lote_traspaso)
    fila.condicion_de_uso = datos.condicion_de_uso
    fila.componente = datos.componente
    fila.es_laqueado = datos.es_laqueado

    session.add(fila)
    session.commit()
    session.refresh(fila)
    return _puesto_out(fila)


@app.delete("/puestos/{nombre}", status_code=204)
def borrar_puesto(nombre: str, session: Session = Depends(get_session)):
    fila = session.exec(select(PuestoDB).where(PuestoDB.nombre == nombre)).first()
    if fila is None:
        raise HTTPException(404, f"No existe el puesto '{nombre}'")

    otros = session.exec(select(PuestoDB).where(PuestoDB.nombre != nombre)).all()
    si_lo_referencian = [o.nombre for o in otros if nombre in json.loads(o.predecesores_json)]
    if si_lo_referencian:
        raise HTTPException(
            400,
            f"No se puede borrar '{nombre}': es predecesor de {', '.join(si_lo_referencian)}",
        )

    session.delete(fila)
    session.commit()


# --------------------------------------------------------------------------
# Trabajos
# --------------------------------------------------------------------------


def _trabajo_out(fila: TrabajoDB) -> TrabajoOut:
    return TrabajoOut(
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
            {
                "material": f.material,
                "puesto": f.puesto,
                "fecha_estimada_llegada": f.fecha_estimada_llegada,
            }
            for f in fila.faltantes
        ],
    )


@app.get("/trabajos", response_model=list[TrabajoOut])
def listar_trabajos(session: Session = Depends(get_session)):
    filas = session.exec(select(TrabajoDB).order_by(TrabajoDB.prioridad)).all()
    return [_trabajo_out(f) for f in filas]


@app.post("/trabajos", response_model=TrabajoOut, status_code=201)
def crear_trabajo(datos: TrabajoIn, session: Session = Depends(get_session)):
    if session.exec(select(TrabajoDB).where(TrabajoDB.nv == datos.nv)).first():
        raise HTTPException(409, f"Ya existe un trabajo con nv '{datos.nv}'")

    prioridad_maxima = session.exec(select(TrabajoDB.prioridad).order_by(TrabajoDB.prioridad.desc())).first()
    fila = TrabajoDB(
        nv=datos.nv,
        cliente=datos.cliente,
        categoria=datos.categoria,
        complejidad=datos.complejidad,
        vendedor=datos.vendedor,
        cantidades_json=json.dumps(datos.cantidades),
        cantidad_a_laquear_json=json.dumps(datos.cantidad_a_laquear),
        lleva_led=datos.lleva_led,
        avance_por_puesto_json=json.dumps(datos.avance_por_puesto),
        ftf=datos.ftf,
        fecha_real_terminado=datos.fecha_real_terminado,
        prioridad=(prioridad_maxima if prioridad_maxima is not None else -1) + 1,
    )
    fila.faltantes = [
        FaltanteDB(material=f.material, puesto=f.puesto, fecha_estimada_llegada=f.fecha_estimada_llegada)
        for f in datos.faltantes
    ]
    session.add(fila)
    session.commit()
    session.refresh(fila)
    return _trabajo_out(fila)


@app.put("/trabajos/{nv}", response_model=TrabajoOut)
def actualizar_trabajo(nv: str, datos: TrabajoIn, session: Session = Depends(get_session)):
    fila = session.exec(select(TrabajoDB).where(TrabajoDB.nv == nv)).first()
    if fila is None:
        raise HTTPException(404, f"No existe el trabajo '{nv}'")

    fila.nv = datos.nv
    fila.cliente = datos.cliente
    fila.categoria = datos.categoria
    fila.complejidad = datos.complejidad
    fila.vendedor = datos.vendedor
    fila.cantidades_json = json.dumps(datos.cantidades)
    fila.cantidad_a_laquear_json = json.dumps(datos.cantidad_a_laquear)
    fila.lleva_led = datos.lleva_led
    fila.avance_por_puesto_json = json.dumps(datos.avance_por_puesto)
    fila.ftf = datos.ftf
    fila.fecha_real_terminado = datos.fecha_real_terminado

    for faltante_existente in list(fila.faltantes):
        session.delete(faltante_existente)
    fila.faltantes = [
        FaltanteDB(material=f.material, puesto=f.puesto, fecha_estimada_llegada=f.fecha_estimada_llegada)
        for f in datos.faltantes
    ]

    session.add(fila)
    session.commit()
    session.refresh(fila)
    return _trabajo_out(fila)


@app.delete("/trabajos/{nv}", status_code=204)
def borrar_trabajo(nv: str, session: Session = Depends(get_session)):
    fila = session.exec(select(TrabajoDB).where(TrabajoDB.nv == nv)).first()
    if fila is None:
        raise HTTPException(404, f"No existe el trabajo '{nv}'")
    session.delete(fila)
    session.commit()


@app.post("/trabajos/reordenar", response_model=list[TrabajoOut])
def reordenar_trabajos(datos: ReordenarTrabajosIn, session: Session = Depends(get_session)):
    """Recibe la lista completa de `nv` en el nuevo orden de prioridad
    (arrastrar y soltar en la UI) y reasigna la prioridad de todos."""

    filas = {f.nv: f for f in session.exec(select(TrabajoDB)).all()}
    faltantes = set(filas) - set(datos.nv_en_orden)
    desconocidos = set(datos.nv_en_orden) - set(filas)
    if faltantes or desconocidos:
        raise HTTPException(
            400,
            f"La lista debe incluir todos los trabajos existentes. "
            f"Faltan: {sorted(faltantes)}. Desconocidos: {sorted(desconocidos)}.",
        )

    for prioridad, nv in enumerate(datos.nv_en_orden):
        filas[nv].prioridad = prioridad
        session.add(filas[nv])
    session.commit()

    filas_ordenadas = session.exec(select(TrabajoDB).order_by(TrabajoDB.prioridad)).all()
    return [_trabajo_out(f) for f in filas_ordenadas]


# --------------------------------------------------------------------------
# Calendario
# --------------------------------------------------------------------------


@app.get("/calendario/feriados", response_model=list[FeriadoIn])
def listar_feriados(session: Session = Depends(get_session)):
    return [FeriadoIn(fecha=f.fecha) for f in session.exec(select(FeriadoDB)).all()]


@app.post("/calendario/feriados", status_code=201)
def agregar_feriado(datos: FeriadoIn, session: Session = Depends(get_session)):
    if session.exec(select(FeriadoDB).where(FeriadoDB.fecha == datos.fecha)).first():
        return {"ok": True}
    session.add(FeriadoDB(fecha=datos.fecha))
    session.commit()
    return {"ok": True}


@app.delete("/calendario/feriados/{fecha}", status_code=204)
def borrar_feriado(fecha: date, session: Session = Depends(get_session)):
    fila = session.exec(select(FeriadoDB).where(FeriadoDB.fecha == fecha)).first()
    if fila:
        session.delete(fila)
        session.commit()


@app.get("/calendario/excepciones", response_model=list[ExcepcionCalendarioIn])
def listar_excepciones(session: Session = Depends(get_session)):
    return [
        ExcepcionCalendarioIn(puesto=e.puesto, fecha=e.fecha, capacidad=e.capacidad)
        for e in session.exec(select(ExcepcionCalendarioDB)).all()
    ]


@app.post("/calendario/excepciones", status_code=201)
def agregar_excepcion(datos: ExcepcionCalendarioIn, session: Session = Depends(get_session)):
    existente = session.exec(
        select(ExcepcionCalendarioDB).where(
            ExcepcionCalendarioDB.puesto == datos.puesto, ExcepcionCalendarioDB.fecha == datos.fecha
        )
    ).first()
    if existente:
        existente.capacidad = datos.capacidad
        session.add(existente)
    else:
        session.add(ExcepcionCalendarioDB(puesto=datos.puesto, fecha=datos.fecha, capacidad=datos.capacidad))
    session.commit()
    return {"ok": True}


@app.delete("/calendario/excepciones/{puesto}/{fecha}", status_code=204)
def borrar_excepcion(puesto: str, fecha: date, session: Session = Depends(get_session)):
    fila = session.exec(
        select(ExcepcionCalendarioDB).where(
            ExcepcionCalendarioDB.puesto == puesto, ExcepcionCalendarioDB.fecha == fecha
        )
    ).first()
    if fila:
        session.delete(fila)
        session.commit()


# --------------------------------------------------------------------------
# Parámetros
# --------------------------------------------------------------------------


@app.get("/parametros", response_model=ParametrosIn)
def obtener_parametros(session: Session = Depends(get_session)):
    return ParametrosIn(umbral_amarillo_dias=repository.cargar_umbral_amarillo(session))


@app.put("/parametros", response_model=ParametrosIn)
def actualizar_parametros(datos: ParametrosIn, session: Session = Depends(get_session)):
    fila = session.exec(
        select(ParametroDB).where(ParametroDB.clave == repository.CLAVE_UMBRAL_AMARILLO)
    ).first()
    fila.valor = str(datos.umbral_amarillo_dias)
    session.add(fila)
    session.commit()
    return datos


# --------------------------------------------------------------------------
# Programa (cálculo del cronograma)
# --------------------------------------------------------------------------


@app.get("/programa", response_model=ProgramaOut)
def obtener_programa(hoy: Optional[date] = None, session: Session = Depends(get_session)):
    hoy = hoy or date.today()

    puestos = repository.cargar_puestos(session)
    trabajos = repository.cargar_trabajos_en_orden(session)
    calendario = repository.cargar_calendario(session)
    umbral = repository.cargar_umbral_amarillo(session)

    resultados, carga_diaria = calcular_programa(
        puestos, trabajos, calendario, hoy, umbral_amarillo_dias=umbral, devolver_carga_diaria=True
    )

    trabajos_out = [
        ResultadoTrabajoOut(
            nv=r.trabajo.nv,
            cliente=r.trabajo.cliente,
            ftf=r.trabajo.ftf,
            fin_trabajo=r.fin_trabajo,
            desvio_dias=r.desvio_dias,
            semaforo=r.semaforo,
            por_puesto={
                nombre: ResultadoPuestoOut(
                    puesto=rp.puesto,
                    total=rp.total,
                    avance=rp.avance,
                    inicio=rp.inicio,
                    fin=rp.fin,
                    bloqueado_sin_fecha=rp.bloqueado_sin_fecha,
                    material_faltante=rp.material_faltante,
                )
                for nombre, rp in r.por_puesto.items()
            },
        )
        for r in resultados
    ]

    return ProgramaOut(
        hoy=hoy,
        trabajos=trabajos_out,
        carga_diaria=[
            {
                "puesto": c.puesto,
                "fecha": c.fecha,
                "capacidad_total": c.capacidad_total,
                "capacidad_usada": c.capacidad_usada,
            }
            for c in carga_diaria
        ],
    )
