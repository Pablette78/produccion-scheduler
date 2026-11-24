import {
  DndContext,
  type DragEndEvent,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  api,
  type Programa,
  type Puesto,
  type ResultadoPuesto,
  type ResultadoTrabajo,
  type Trabajo,
} from "../api";
import Semaforo from "../components/Semaforo";
import { formatearFecha, hoyISO } from "../fecha";

type Criterio = "prioridad" | "ftf" | "estimado" | "carga" | "avance" | "placas" | "nv" | "cliente";

const CRITERIOS: Record<Criterio, string> = {
  prioridad: "Prioridad (orden de producción)",
  ftf: "FTF",
  estimado: "Estimado de terminación",
  carga: "Carga pendiente",
  avance: "% de avance",
  placas: "Placas",
  nv: "NV",
  cliente: "Cliente",
};

function valorDe(
  criterio: Criterio,
  trabajo: Trabajo,
  resultado: ResultadoTrabajo | undefined
): string | number | null {
  switch (criterio) {
    case "ftf":
      return trabajo.ftf;
    case "estimado":
      return resultado?.fin_trabajo ?? null;
    case "carga":
      return resultado?.carga_pendiente_dias ?? null;
    case "avance":
      return resultado?.avance_pct ?? null;
    case "placas":
      return trabajo.cantidades.placas ?? 0;
    case "nv":
      return trabajo.nv;
    case "cliente":
      return trabajo.cliente;
    default:
      return trabajo.prioridad;
  }
}

// Los que no tienen valor (sin FTF, sin fecha estimada) van siempre al final,
// en cualquier sentido. A igual valor se conserva el orden de prioridad.
function ordenarTrabajos(
  trabajos: Trabajo[],
  resultados: Map<string, ResultadoTrabajo>,
  criterio: Criterio,
  descendente: boolean
): Trabajo[] {
  if (criterio === "prioridad") return trabajos;
  const signo = descendente ? -1 : 1;
  return [...trabajos].sort((a, b) => {
    const va = valorDe(criterio, a, resultados.get(a.nv));
    const vb = valorDe(criterio, b, resultados.get(b.nv));
    if (va === null || vb === null) return Number(va === null) - Number(vb === null);
    if (typeof va === "number" && typeof vb === "number") return signo * (va - vb);
    return signo * String(va).localeCompare(String(vb), "es", { numeric: true });
  });
}

const formatearNumero = (n: number) => n.toLocaleString("es-AR", { maximumFractionDigits: 1 });

export default function TrabajosPage() {
  const [trabajos, setTrabajos] = useState<Trabajo[]>([]);
  const [programa, setPrograma] = useState<Programa | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mostrarTerminados, setMostrarTerminados] = useState(false);
  const [puestos, setPuestos] = useState<Puesto[]>([]);
  const [criterio, setCriterio] = useState<Criterio>("prioridad");
  const [descendente, setDescendente] = useState(false);

  async function cargarTodo() {
    setCargando(true);
    setError(null);
    try {
      const [listaTrabajos, resultadoPrograma, listaPuestos] = await Promise.all([
        api.listarTrabajos(),
        api.obtenerPrograma(),
        api.listarPuestos(),
      ]);
      setPuestos([...listaPuestos].sort((a, b) => a.orden - b.orden));
      setTrabajos(listaTrabajos);
      setPrograma(resultadoPrograma);
    } catch (e) {
      setError(String(e));
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => {
    cargarTodo();
  }, []);

  const resultadosPorNv = new Map<string, ResultadoTrabajo>(
    (programa?.trabajos ?? []).map((r) => [r.nv, r])
  );

  const trabajosActivos = trabajos.filter((t) => !t.fecha_real_terminado);
  const trabajosTerminados = trabajos.filter((t) => t.fecha_real_terminado);

  const porPrioridad = criterio === "prioridad";
  const trabajosVisibles = ordenarTrabajos(trabajosActivos, resultadosPorNv, criterio, descendente);

  async function usarComoPrioridad() {
    const pregunta =
      `¿Usar el orden por "${CRITERIOS[criterio]}" como orden de producción?\n\n` +
      "Reemplaza el orden actual de la tabla y recalcula todas las fechas.";
    if (!window.confirm(pregunta)) return;
    try {
      await api.reordenarTrabajos([...trabajosVisibles, ...trabajosTerminados].map((t) => t.nv));
      setCriterio("prioridad");
      setDescendente(false);
    } catch (e) {
      setError(String(e));
      return;
    }
    cargarTodo();
  }

  const sensores = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  async function alTerminarArrastre(evento: DragEndEvent) {
    const { active, over } = evento;
    if (!over || active.id === over.id) return;

    const indiceOrigen = trabajosActivos.findIndex((t) => t.nv === active.id);
    const indiceDestino = trabajosActivos.findIndex((t) => t.nv === over.id);
    if (indiceOrigen === -1 || indiceDestino === -1) return;

    const nuevoOrdenActivos = [...trabajosActivos];
    const [movido] = nuevoOrdenActivos.splice(indiceOrigen, 1);
    nuevoOrdenActivos.splice(indiceDestino, 0, movido);
    const nuevoOrdenCompleto = [...nuevoOrdenActivos, ...trabajosTerminados];
    setTrabajos(nuevoOrdenCompleto);

    try {
      await api.reordenarTrabajos(nuevoOrdenCompleto.map((t) => t.nv));
      const resultadoPrograma = await api.obtenerPrograma();
      setPrograma(resultadoPrograma);
    } catch (e) {
      setError(String(e));
      cargarTodo();
    }
  }

  async function borrar(nv: string) {
    if (!window.confirm(`¿Borrar el trabajo ${nv}?`)) return;
    await api.borrarTrabajo(nv);
    cargarTodo();
  }

  async function marcarTerminado(nv: string) {
    await api.marcarTerminado(nv, hoyISO());
    cargarTodo();
  }

  async function reabrir(nv: string) {
    await api.marcarTerminado(nv, null);
    cargarTodo();
  }

  if (cargando) return <p>Cargando…</p>;

  return (
    <div>
      <div className="encabezado-pantalla">
        <h2>Trabajos (orden de prioridad)</h2>
        <Link className="boton" to="/trabajos/nuevo">
          + Nuevo trabajo
        </Link>
      </div>
      {error && <p className="error">{error}</p>}
      {programa && <p className="nota">Cronograma calculado desde hoy: {formatearFecha(programa.hoy)}</p>}

      <div className="barra-orden">
        <label>
          Ordenar por{" "}
          <select
            value={criterio}
            onChange={(e) => {
              setCriterio(e.target.value as Criterio);
              setDescendente(false);
            }}
          >
            {Object.entries(CRITERIOS).map(([clave, etiqueta]) => (
              <option key={clave} value={clave}>
                {etiqueta}
              </option>
            ))}
          </select>
        </label>
        {!porPrioridad && (
          <>
            <button className="boton-chico" onClick={() => setDescendente((v) => !v)}>
              {descendente ? "↓ Mayor a menor" : "↑ Menor a mayor"}
            </button>
            <button className="boton-chico" onClick={usarComoPrioridad}>
              Usar este orden para producir
            </button>
            <span className="nota">
              Solo cambia la vista: las fechas siguen el orden de prioridad. Para arrastrar, volvé a
              «Prioridad».
            </span>
          </>
        )}
      </div>

      <DndContext
        sensors={sensores}
        collisionDetection={closestCenter}
        onDragEnd={alTerminarArrastre}
      >
        <SortableContext
          items={trabajosVisibles.map((t) => t.nv)}
          strategy={verticalListSortingStrategy}
        >
          <table className="tabla tabla-trabajos">
            <thead>
              <tr>
                <th></th>
                <th>NV</th>
                <th>Cliente</th>
                <th>Placas</th>
                {puestos.map((p) => (
                  <th key={p.nombre} className="col-puesto">
                    {p.nombre}
                  </th>
                ))}
                <th>Avance</th>
                <th title="Días de trabajo que le faltan, sumando la capacidad de cada puesto">
                  Carga pend.
                </th>
                <th>FTF</th>
                <th>Fecha estimada</th>
                <th>Desvío</th>
                <th>Semáforo</th>
                <th>Material pendiente</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {trabajosVisibles.map((trabajo) => (
                <FilaTrabajo
                  key={trabajo.nv}
                  trabajo={trabajo}
                  resultado={resultadosPorNv.get(trabajo.nv)}
                  puestos={puestos}
                  arrastrable={porPrioridad}
                  onBorrar={() => borrar(trabajo.nv)}
                  onTerminar={() => marcarTerminado(trabajo.nv)}
                />
              ))}
            </tbody>
          </table>
        </SortableContext>
      </DndContext>
      {trabajosActivos.length === 0 && (
        <p className="nota">Todavía no hay trabajos activos cargados.</p>
      )}

      {trabajosTerminados.length > 0 && (
        <div className="seccion-terminados">
          <button onClick={() => setMostrarTerminados((v) => !v)}>
            {mostrarTerminados ? "Ocultar" : "Mostrar"} terminados ({trabajosTerminados.length})
          </button>
          {mostrarTerminados && (
            <table className="tabla">
              <thead>
                <tr>
                  <th>NV</th>
                  <th>Cliente</th>
                  <th>Terminado el</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {trabajosTerminados.map((trabajo) => (
                  <tr key={trabajo.nv}>
                    <td>{trabajo.nv}</td>
                    <td>{trabajo.cliente}</td>
                    <td>{formatearFecha(trabajo.fecha_real_terminado)}</td>
                    <td className="acciones">
                      <Link to={`/trabajos/${encodeURIComponent(trabajo.nv)}/editar`}>Editar</Link>
                      <button onClick={() => reabrir(trabajo.nv)}>Reabrir</button>
                      <button onClick={() => borrar(trabajo.nv)}>Borrar</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}

function CeldaPuesto({ puesto, resultado }: { puesto: string; resultado: ResultadoPuesto | undefined }) {
  if (!resultado) {
    return (
      <td className="col-puesto estado-no-aplica" title={`${puesto}: no lleva`}>
        ·
      </td>
    );
  }
  const { total, avance, inicio, fin, bloqueado_sin_fecha, material_faltante } = resultado;
  if (avance >= total) {
    return (
      <td className="col-puesto" title={`${puesto}: realizado`}>
        <span className="estado-puesto estado-realizado">✓</span>
      </td>
    );
  }
  const fechas = bloqueado_sin_fecha
    ? "sin fecha"
    : `${formatearFecha(inicio)} al ${formatearFecha(fin)}`;
  const faltante = material_faltante ? ` — falta ${material_faltante}` : "";
  const clase = bloqueado_sin_fecha
    ? "estado-frenado"
    : avance > 0
    ? "estado-parcial"
    : "estado-pendiente";
  return (
    <td className="col-puesto" title={`${puesto}: ${fechas}${faltante}`}>
      <span className={`estado-puesto ${clase}`}>
        {bloqueado_sin_fecha && "⏸ "}
        {formatearNumero(avance)}/{formatearNumero(total)}
      </span>
    </td>
  );
}

function FilaTrabajo({
  trabajo,
  resultado,
  puestos,
  arrastrable,
  onBorrar,
  onTerminar,
}: {
  trabajo: Trabajo;
  resultado: ResultadoTrabajo | undefined;
  puestos: Puesto[];
  arrastrable: boolean;
  onBorrar: () => void;
  onTerminar: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: trabajo.nv,
    disabled: !arrastrable,
  });

  // Se muestra cualquier faltante con material cargado, tenga o no fecha
  // estimada: aunque ya tenga una fecha de fin recalculada (no está
  // "bloqueado sin fecha"), sigue siendo la causa de ese retraso y hay que
  // verlo acá.
  const materialesPendientes = Object.values(resultado?.por_puesto ?? {})
    .filter((p) => p.material_faltante)
    .map((p) => (p.bloqueado_sin_fecha ? `⏸ ${p.material_faltante} (${p.puesto})` : `${p.material_faltante} (${p.puesto})`))
    .join(", ");

  return (
    <tr
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
      }}
    >
      {arrastrable ? (
        <td className="asa-arrastre" title="Arrastrar para cambiar la prioridad" {...attributes} {...listeners}>
          ⠿
        </td>
      ) : (
        <td></td>
      )}
      <td className="col-nv">{trabajo.nv}</td>
      <td>{trabajo.cliente}</td>
      <td>{trabajo.cantidades.placas ?? 0}</td>
      {puestos.map((p) => (
        <CeldaPuesto key={p.nombre} puesto={p.nombre} resultado={resultado?.por_puesto[p.nombre]} />
      ))}
      <td>
        <div className="avance" title={`${resultado?.avance_pct ?? 0}% del trabajo realizado`}>
          <div className="avance-barra">
            <div style={{ width: `${resultado?.avance_pct ?? 0}%` }} />
          </div>
          {resultado?.avance_pct ?? 0}%
        </div>
      </td>
      <td className="col-nv">{formatearNumero(resultado?.carga_pendiente_dias ?? 0)} d</td>
      <td>{formatearFecha(trabajo.ftf)}</td>
      <td>{formatearFecha(resultado?.fin_trabajo ?? null)}</td>
      <td>
        {resultado?.desvio_dias == null
          ? "—"
          : resultado.desvio_dias <= 0
          ? `${-resultado.desvio_dias} días de margen`
          : `${resultado.desvio_dias} días de atraso`}
      </td>
      <td>
        <Semaforo valor={resultado?.semaforo ?? null} />
      </td>
      <td>{materialesPendientes || "—"}</td>
      <td>
        <div className="acciones">
          <Link to={`/trabajos/${encodeURIComponent(trabajo.nv)}/editar`}>Editar</Link>
          <button className="boton-chico" onClick={onTerminar} title="Marcar como terminado">
            Terminado
          </button>
          <button className="boton-chico" onClick={onBorrar}>
            Borrar
          </button>
        </div>
      </td>
    </tr>
  );
}
