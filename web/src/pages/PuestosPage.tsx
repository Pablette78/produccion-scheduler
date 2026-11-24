import { useEffect, useState } from "react";
import { api, type LoteTraspaso, type Puesto } from "../api";

export default function PuestosPage() {
  const [puestos, setPuestos] = useState<Puesto[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [guardandoNombre, setGuardandoNombre] = useState<string | null>(null);

  async function cargar() {
    try {
      setPuestos(await api.listarPuestos());
    } catch (e) {
      setError(String(e));
    }
  }

  useEffect(() => {
    cargar();
  }, []);

  function actualizarLocal(nombre: string, cambios: Partial<Puesto>) {
    setPuestos((lista) => lista.map((p) => (p.nombre === nombre ? { ...p, ...cambios } : p)));
  }

  async function guardar(puesto: Puesto) {
    setGuardandoNombre(puesto.nombre);
    setError(null);
    try {
      const { orden, ...datos } = puesto;
      await api.actualizarPuesto(puesto.nombre, datos);
    } catch (e) {
      setError(String(e));
    } finally {
      setGuardandoNombre(null);
    }
  }

  function parsearLote(texto: string): LoteTraspaso {
    if (texto.trim().toLowerCase() === "todo") return "todo";
    const numero = Number(texto);
    return Number.isFinite(numero) ? numero : 1;
  }

  if (error) return <p className="error">{error}</p>;

  return (
    <div>
      <h2>Puestos</h2>
      <p className="nota">
        Capacidad diaria, lote de traspaso y demás parámetros editables (sección 11 del documento:
        LED y DTC1 todavía no tienen un valor definitivo). Lote «todo»: el trabajo entra al puesto
        recién cuando el anterior lo terminó completo.
      </p>

      <table className="tabla">
        <thead>
          <tr>
            <th>Nombre</th>
            <th>Predecesores</th>
            <th>Tipo</th>
            <th>Unidad</th>
            <th>Capacidad diaria</th>
            <th>Días fijos</th>
            <th>Lote de traspaso</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {puestos.map((puesto) => (
            <tr key={puesto.nombre}>
              <td>{puesto.nombre}</td>
              <td>{puesto.predecesores.join(", ") || "—"}</td>
              <td>{puesto.tipo}</td>
              <td>{puesto.unidad}</td>
              <td>
                {puesto.tipo === "capacidad" ? (
                  <input
                    type="number"
                    min={0}
                    value={puesto.capacidad_diaria ?? 0}
                    onChange={(e) =>
                      actualizarLocal(puesto.nombre, { capacidad_diaria: Number(e.target.value) })
                    }
                  />
                ) : (
                  "—"
                )}
              </td>
              <td>
                {puesto.tipo === "tiempo_fijo" ? (
                  <input
                    type="number"
                    min={0}
                    value={puesto.dias_fijos ?? 0}
                    onChange={(e) => actualizarLocal(puesto.nombre, { dias_fijos: Number(e.target.value) })}
                  />
                ) : (
                  "—"
                )}
              </td>
              <td>
                <input
                  value={String(puesto.lote_traspaso)}
                  onChange={(e) =>
                    actualizarLocal(puesto.nombre, { lote_traspaso: parsearLote(e.target.value) })
                  }
                />
              </td>
              <td>
                <button onClick={() => guardar(puesto)} disabled={guardandoNombre === puesto.nombre}>
                  {guardandoNombre === puesto.nombre ? "Guardando…" : "Guardar"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
