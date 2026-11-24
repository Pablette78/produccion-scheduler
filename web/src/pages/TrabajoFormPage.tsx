import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, type Faltante, type Puesto, type TrabajoIn } from "../api";

const VACIO: TrabajoIn = {
  nv: "",
  cliente: "",
  categoria: "",
  complejidad: 1,
  vendedor: "",
  cantidades: {},
  cantidad_a_laquear: {},
  lleva_led: false,
  avance_por_puesto: {},
  ftf: null,
  fecha_real_terminado: null,
  faltantes: [],
};

export default function TrabajoFormPage() {
  const { nv: nvEnUrl } = useParams();
  const editando = Boolean(nvEnUrl);
  const navegar = useNavigate();

  const [puestos, setPuestos] = useState<Puesto[]>([]);
  const [datos, setDatos] = useState<TrabajoIn>(VACIO);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    (async () => {
      setCargando(true);
      try {
        const listaPuestos = await api.listarPuestos();
        setPuestos(listaPuestos);
        if (editando && nvEnUrl) {
          const trabajos = await api.listarTrabajos();
          const existente = trabajos.find((t) => t.nv === nvEnUrl);
          if (existente) {
            const { prioridad, ...resto } = existente;
            setDatos(resto);
          }
        }
      } catch (e) {
        setError(String(e));
      } finally {
        setCargando(false);
      }
    })();
  }, [editando, nvEnUrl]);

  const componentes = [...new Set(puestos.map((p) => p.componente).filter(Boolean))] as string[];
  const nombresPuestos = puestos.map((p) => p.nombre);

  function actualizarCantidad(mapa: "cantidades" | "cantidad_a_laquear", componente: string, valor: string) {
    const numero = valor === "" ? 0 : Number(valor);
    setDatos((d) => ({ ...d, [mapa]: { ...d[mapa], [componente]: numero } }));
  }

  function actualizarAvance(puesto: string, valor: string) {
    const numero = valor === "" ? 0 : Number(valor);
    setDatos((d) => ({ ...d, avance_por_puesto: { ...d.avance_por_puesto, [puesto]: numero } }));
  }

  function agregarFaltante() {
    setDatos((d) => ({
      ...d,
      faltantes: [...d.faltantes, { material: "", puesto: nombresPuestos[0] ?? "", fecha_estimada_llegada: null }],
    }));
  }

  function actualizarFaltante(indice: number, campo: keyof Faltante, valor: string) {
    setDatos((d) => ({
      ...d,
      faltantes: d.faltantes.map((f, i) =>
        i === indice ? { ...f, [campo]: campo === "fecha_estimada_llegada" && valor === "" ? null : valor } : f
      ),
    }));
  }

  function quitarFaltante(indice: number) {
    setDatos((d) => ({ ...d, faltantes: d.faltantes.filter((_, i) => i !== indice) }));
  }

  async function guardar(evento: React.FormEvent) {
    evento.preventDefault();
    setGuardando(true);
    setError(null);
    try {
      if (editando && nvEnUrl) {
        await api.actualizarTrabajo(nvEnUrl, datos);
      } else {
        await api.crearTrabajo(datos);
      }
      navegar("/");
    } catch (e) {
      setError(String(e));
    } finally {
      setGuardando(false);
    }
  }

  if (cargando) return <p>Cargando…</p>;

  return (
    <div>
      <h2>{editando ? `Editar trabajo ${nvEnUrl}` : "Nuevo trabajo"}</h2>
      {error && <p className="error">{error}</p>}

      <form className="formulario" onSubmit={guardar}>
        <fieldset>
          <legend>Datos generales</legend>
          <label>
            NV
            <input
              required
              disabled={editando}
              value={datos.nv}
              onChange={(e) => setDatos((d) => ({ ...d, nv: e.target.value }))}
            />
          </label>
          <label>
            Cliente
            <input
              value={datos.cliente}
              onChange={(e) => setDatos((d) => ({ ...d, cliente: e.target.value }))}
            />
          </label>
          <label>
            Categoría
            <input
              value={datos.categoria}
              onChange={(e) => setDatos((d) => ({ ...d, categoria: e.target.value }))}
            />
          </label>
          <label>
            Complejidad (1-4)
            <input
              type="number"
              min={1}
              max={4}
              value={datos.complejidad}
              onChange={(e) => setDatos((d) => ({ ...d, complejidad: Number(e.target.value) }))}
            />
          </label>
          <label>
            Vendedor
            <input
              value={datos.vendedor}
              onChange={(e) => setDatos((d) => ({ ...d, vendedor: e.target.value }))}
            />
          </label>
          <label>
            FTF (fecha prometida al cliente)
            <input
              type="date"
              value={datos.ftf ?? ""}
              onChange={(e) => setDatos((d) => ({ ...d, ftf: e.target.value || null }))}
            />
          </label>
        </fieldset>

        <fieldset>
          <legend>Cantidades</legend>
          {componentes.map((componente) => (
            <label key={componente}>
              {componente}
              <input
                type="number"
                min={0}
                value={datos.cantidades[componente] ?? 0}
                onChange={(e) => actualizarCantidad("cantidades", componente, e.target.value)}
              />
            </label>
          ))}
        </fieldset>

        <fieldset>
          <legend>Cantidad a laquear (subconjunto de las cantidades)</legend>
          {componentes.map((componente) => (
            <label key={componente}>
              {componente} a laquear
              <input
                type="number"
                min={0}
                value={datos.cantidad_a_laquear[componente] ?? 0}
                onChange={(e) => actualizarCantidad("cantidad_a_laquear", componente, e.target.value)}
              />
            </label>
          ))}
        </fieldset>

        <fieldset>
          <legend>Avance ya realizado (trabajos en curso)</legend>
          {nombresPuestos.map((puesto) => (
            <label key={puesto}>
              {puesto}
              <input
                type="number"
                min={0}
                value={datos.avance_por_puesto[puesto] ?? 0}
                onChange={(e) => actualizarAvance(puesto, e.target.value)}
              />
            </label>
          ))}
        </fieldset>

        <fieldset>
          <legend>Material faltante</legend>
          {datos.faltantes.map((faltante, indice) => (
            <div className="fila-faltante" key={indice}>
              <input
                placeholder="Material"
                value={faltante.material}
                onChange={(e) => actualizarFaltante(indice, "material", e.target.value)}
              />
              <select
                value={faltante.puesto}
                onChange={(e) => actualizarFaltante(indice, "puesto", e.target.value)}
              >
                {nombresPuestos.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
              <input
                type="date"
                value={faltante.fecha_estimada_llegada ?? ""}
                onChange={(e) => actualizarFaltante(indice, "fecha_estimada_llegada", e.target.value)}
              />
              <button type="button" onClick={() => quitarFaltante(indice)}>
                Quitar
              </button>
            </div>
          ))}
          <button type="button" onClick={agregarFaltante}>
            + Agregar faltante
          </button>
        </fieldset>

        <div className="acciones-formulario">
          <button type="submit" disabled={guardando}>
            {guardando ? "Guardando…" : "Guardar"}
          </button>
          <button type="button" onClick={() => navegar("/")}>
            Cancelar
          </button>
        </div>
      </form>
    </div>
  );
}
