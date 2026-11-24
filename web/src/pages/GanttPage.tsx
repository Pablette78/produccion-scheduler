import { useEffect, useState } from "react";
import { api, type Programa, type Puesto, type ResultadoPuesto } from "../api";
import { formatearFecha } from "../fecha";

const ANCHO_DIA = 14; // px

function diasEntre(a: string, b: string): number {
  const msPorDia = 1000 * 60 * 60 * 24;
  return Math.round((new Date(b).getTime() - new Date(a).getTime()) / msPorDia);
}

function sumarDias(iso: string, dias: number): string {
  const d = new Date(iso);
  d.setDate(d.getDate() + dias);
  return d.toISOString().slice(0, 10);
}

function Barra({ puesto, hoy, anchoPista }: { puesto: ResultadoPuesto; hoy: string; anchoPista: number }) {
  if (puesto.fin && puesto.inicio) {
    const conFaltante = Boolean(puesto.material_faltante);
    return (
      <div
        className={`gantt-barra ${puesto.puesto === "Laqueado" ? "gantt-barra--laqueado" : ""} ${
          conFaltante ? "gantt-barra--faltante" : ""
        }`}
        style={{
          left: diasEntre(hoy, puesto.inicio) * ANCHO_DIA,
          width: Math.max((diasEntre(puesto.inicio, puesto.fin) + 1) * ANCHO_DIA, 4),
        }}
        title={
          conFaltante
            ? `${puesto.puesto}: ${formatearFecha(puesto.inicio)} → ${formatearFecha(puesto.fin)} — esperó "${puesto.material_faltante}"`
            : `${puesto.puesto}: ${formatearFecha(puesto.inicio)} → ${formatearFecha(puesto.fin)}`
        }
      >
        {conFaltante ? `⏸ ${puesto.material_faltante}` : `${formatearFecha(puesto.inicio)} → ${formatearFecha(puesto.fin)}`}
      </div>
    );
  }
  if (puesto.bloqueado_sin_fecha) {
    return (
      <div
        className="gantt-bloqueado"
        style={{ left: 0, width: anchoPista }}
        title={`${puesto.puesto}: frenado, falta "${puesto.material_faltante}", sin fecha de llegada`}
      >
        ⏸ falta {puesto.material_faltante} (sin fecha)
      </div>
    );
  }
  return null;
}

function Regla({ hoy, totalDias }: { hoy: string; totalDias: number }) {
  const marcas = [];
  for (let d = 0; d <= totalDias; d += 7) {
    marcas.push(
      <div key={d} className="gantt-regla-marca" style={{ left: d * ANCHO_DIA }}>
        {formatearFecha(sumarDias(hoy, d))}
      </div>
    );
  }
  return (
    <div className="gantt-regla" style={{ width: totalDias * ANCHO_DIA }}>
      {marcas}
    </div>
  );
}

export default function GanttPage() {
  const [programa, setPrograma] = useState<Programa | null>(null);
  const [puestos, setPuestos] = useState<Puesto[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [vista, setVista] = useState<"trabajo" | "puesto">("puesto");

  useEffect(() => {
    Promise.all([api.obtenerPrograma(), api.listarPuestos()])
      .then(([p, pu]) => {
        setPrograma(p);
        setPuestos(pu);
      })
      .catch((e) => setError(String(e)));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!programa) return <p>Cargando…</p>;
  if (programa.trabajos.length === 0) return <p className="nota">No hay trabajos cargados.</p>;

  const hoy = programa.hoy;
  const todosLosFines = programa.trabajos.flatMap((t) =>
    Object.values(t.por_puesto)
      .map((p) => p.fin)
      .filter((f): f is string => Boolean(f))
  );
  const fechaMaxima = todosLosFines.length > 0 ? todosLosFines.reduce((a, b) => (a > b ? a : b)) : hoy;
  const totalDias = Math.max(diasEntre(hoy, fechaMaxima) + 3, 10);
  const anchoPista = totalDias * ANCHO_DIA;

  return (
    <div>
      <h2>Gantt</h2>
      <div className="gantt-selector">
        <button
          className={vista === "puesto" ? "activo" : ""}
          onClick={() => setVista("puesto")}
        >
          Por puesto (cola de cada estación)
        </button>
        <button
          className={vista === "trabajo" ? "activo" : ""}
          onClick={() => setVista("trabajo")}
        >
          Por trabajo (ruta completa)
        </button>
      </div>
      <p className="nota">
        Hoy: {formatearFecha(hoy)}. Las barras grises son Laqueado, y las naranjas marcan un tramo que
        esperó un material faltante (pasá el mouse para ver cuál).
        {vista === "puesto" &&
          " Dentro de cada puesto, los trabajos están en orden de prioridad: el de más arriba consume la capacidad primero."}
      </p>

      <div className="gantt-scroll">
        <div className="gantt" style={{ width: anchoPista + 220 }}>
          <div className="gantt-fila gantt-fila--regla">
            <div className="gantt-etiqueta"></div>
            <Regla hoy={hoy} totalDias={totalDias} />
          </div>

          {vista === "trabajo"
            ? programa.trabajos.map((trabajo) => (
                <div className="gantt-bloque-trabajo" key={trabajo.nv}>
                  <div className="gantt-titulo-trabajo">
                    {trabajo.nv} — {trabajo.cliente}
                  </div>
                  {Object.values(trabajo.por_puesto).map((puesto) => (
                    <div className="gantt-fila" key={puesto.puesto}>
                      <div className="gantt-etiqueta">{puesto.puesto}</div>
                      <div className="gantt-pista" style={{ width: anchoPista }}>
                        <Barra puesto={puesto} hoy={hoy} anchoPista={anchoPista} />
                      </div>
                    </div>
                  ))}
                </div>
              ))
            : puestos.map((puesto) => {
                const trabajosDelPuesto = programa.trabajos
                  .map((t) => ({ trabajo: t, resultado: t.por_puesto[puesto.nombre] }))
                  .filter((x) => x.resultado);
                if (trabajosDelPuesto.length === 0) return null;
                return (
                  <div className="gantt-bloque-trabajo" key={puesto.nombre}>
                    <div className="gantt-titulo-trabajo">{puesto.nombre}</div>
                    {trabajosDelPuesto.map(({ trabajo, resultado }) => (
                      <div className="gantt-fila" key={trabajo.nv}>
                        <div className="gantt-etiqueta" title={trabajo.cliente}>
                          {trabajo.nv}
                        </div>
                        <div className="gantt-pista" style={{ width: anchoPista }}>
                          <Barra puesto={resultado} hoy={hoy} anchoPista={anchoPista} />
                        </div>
                      </div>
                    ))}
                  </div>
                );
              })}
        </div>
      </div>
    </div>
  );
}
