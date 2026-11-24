import { useEffect, useState } from "react";
import { api, type Programa } from "../api";
import { formatearFecha } from "../fecha";

const ANCHO_DIA = 14; // px

function diasEntre(a: string, b: string): number {
  const msPorDia = 1000 * 60 * 60 * 24;
  return Math.round((new Date(b).getTime() - new Date(a).getTime()) / msPorDia);
}

export default function GanttPage() {
  const [programa, setPrograma] = useState<Programa | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.obtenerPrograma().then(setPrograma).catch((e) => setError(String(e)));
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
      <h2>Gantt por trabajo</h2>
      <p className="nota">Hoy: {formatearFecha(hoy)}. Cada fila es un puesto de la ruta del trabajo.</p>

      <div className="gantt-scroll">
        <div className="gantt" style={{ width: anchoPista + 220 }}>
          {programa.trabajos.map((trabajo) => (
            <div className="gantt-bloque-trabajo" key={trabajo.nv}>
              <div className="gantt-titulo-trabajo">
                {trabajo.nv} — {trabajo.cliente}
              </div>
              {Object.values(trabajo.por_puesto).map((puesto) => (
                <div className="gantt-fila" key={puesto.puesto}>
                  <div className="gantt-etiqueta">{puesto.puesto}</div>
                  <div className="gantt-pista" style={{ width: anchoPista }}>
                    {puesto.fin && puesto.inicio ? (
                      <div
                        className={`gantt-barra ${
                          puesto.puesto === "Laqueado" ? "gantt-barra--laqueado" : ""
                        }`}
                        style={{
                          left: diasEntre(hoy, puesto.inicio) * ANCHO_DIA,
                          width: Math.max((diasEntre(puesto.inicio, puesto.fin) + 1) * ANCHO_DIA, 4),
                        }}
                        title={`${puesto.puesto}: ${formatearFecha(puesto.inicio)} → ${formatearFecha(
                          puesto.fin
                        )}`}
                      >
                        {formatearFecha(puesto.inicio)} → {formatearFecha(puesto.fin)}
                      </div>
                    ) : puesto.bloqueado_sin_fecha ? (
                      <div
                        className="gantt-bloqueado"
                        style={{ left: 0 }}
                        title={`${puesto.puesto}: frenado, falta "${puesto.material_faltante}"`}
                      >
                        ⏸ falta {puesto.material_faltante}
                      </div>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
