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
import { api, type Programa, type ResultadoTrabajo, type Trabajo } from "../api";
import Semaforo from "../components/Semaforo";
import { formatearFecha } from "../fecha";

export default function TrabajosPage() {
  const [trabajos, setTrabajos] = useState<Trabajo[]>([]);
  const [programa, setPrograma] = useState<Programa | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function cargarTodo() {
    setCargando(true);
    setError(null);
    try {
      const [listaTrabajos, resultadoPrograma] = await Promise.all([
        api.listarTrabajos(),
        api.obtenerPrograma(),
      ]);
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

  const sensores = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  async function alTerminarArrastre(evento: DragEndEvent) {
    const { active, over } = evento;
    if (!over || active.id === over.id) return;

    const indiceOrigen = trabajos.findIndex((t) => t.nv === active.id);
    const indiceDestino = trabajos.findIndex((t) => t.nv === over.id);
    if (indiceOrigen === -1 || indiceDestino === -1) return;

    const nuevoOrden = [...trabajos];
    const [movido] = nuevoOrden.splice(indiceOrigen, 1);
    nuevoOrden.splice(indiceDestino, 0, movido);
    setTrabajos(nuevoOrden);

    try {
      await api.reordenarTrabajos(nuevoOrden.map((t) => t.nv));
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

      <table className="tabla">
        <thead>
          <tr>
            <th></th>
            <th>NV</th>
            <th>Cliente</th>
            <th>Complejidad</th>
            <th>FTF</th>
            <th>Fecha estimada</th>
            <th>Desvío</th>
            <th>Semáforo</th>
            <th>Material pendiente</th>
            <th></th>
          </tr>
        </thead>
        <DndContext
          sensors={sensores}
          collisionDetection={closestCenter}
          onDragEnd={alTerminarArrastre}
        >
          <SortableContext
            items={trabajos.map((t) => t.nv)}
            strategy={verticalListSortingStrategy}
          >
            <tbody>
              {trabajos.map((trabajo) => (
                <FilaTrabajo
                  key={trabajo.nv}
                  trabajo={trabajo}
                  resultado={resultadosPorNv.get(trabajo.nv)}
                  onBorrar={() => borrar(trabajo.nv)}
                />
              ))}
            </tbody>
          </SortableContext>
        </DndContext>
      </table>
      {trabajos.length === 0 && <p className="nota">Todavía no hay trabajos cargados.</p>}
    </div>
  );
}

function FilaTrabajo({
  trabajo,
  resultado,
  onBorrar,
}: {
  trabajo: Trabajo;
  resultado: ResultadoTrabajo | undefined;
  onBorrar: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: trabajo.nv,
  });

  const materialesPendientes = Object.values(resultado?.por_puesto ?? {})
    .filter((p) => p.material_faltante && !p.fin)
    .map((p) => `${p.material_faltante} (${p.puesto})`)
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
      <td className="asa-arrastre" {...attributes} {...listeners}>
        ⠿
      </td>
      <td>{trabajo.nv}</td>
      <td>{trabajo.cliente}</td>
      <td>{trabajo.complejidad}</td>
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
      <td className="acciones">
        <Link to={`/trabajos/${encodeURIComponent(trabajo.nv)}/editar`}>Editar</Link>
        <button onClick={onBorrar}>Borrar</button>
      </td>
    </tr>
  );
}
