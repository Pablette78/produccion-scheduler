import { useEffect, useState } from "react";
import { api, type ExcepcionCalendario, type Feriado, type Parametros, type Puesto } from "../api";
import { formatearFecha, hoyISO } from "../fecha";

export default function CalendarioPage() {
  const [feriados, setFeriados] = useState<Feriado[]>([]);
  const [excepciones, setExcepciones] = useState<ExcepcionCalendario[]>([]);
  const [puestos, setPuestos] = useState<Puesto[]>([]);
  const [parametros, setParametros] = useState<Parametros | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [nuevoFeriado, setNuevoFeriado] = useState(hoyISO());
  const [nuevaExcepcion, setNuevaExcepcion] = useState<ExcepcionCalendario>({
    puesto: "",
    fecha: hoyISO(),
    capacidad: 0,
  });

  async function cargar() {
    try {
      const [f, e, p, par] = await Promise.all([
        api.listarFeriados(),
        api.listarExcepciones(),
        api.listarPuestos(),
        api.obtenerParametros(),
      ]);
      setFeriados(f);
      setExcepciones(e);
      setPuestos(p);
      setParametros(par);
      if (!nuevaExcepcion.puesto && p.length > 0) {
        setNuevaExcepcion((n) => ({ ...n, puesto: p[0].nombre }));
      }
    } catch (err) {
      setError(String(err));
    }
  }

  useEffect(() => {
    cargar();
  }, []);

  async function agregarFeriado() {
    await api.agregarFeriado(nuevoFeriado);
    cargar();
  }

  async function borrarFeriado(fecha: string) {
    await api.borrarFeriado(fecha);
    cargar();
  }

  async function agregarExcepcion() {
    await api.agregarExcepcion(nuevaExcepcion);
    cargar();
  }

  async function borrarExcepcion(puesto: string, fecha: string) {
    await api.borrarExcepcion(puesto, fecha);
    cargar();
  }

  async function guardarUmbral(valor: number) {
    const actualizado = await api.actualizarParametros({ umbral_amarillo_dias: valor });
    setParametros(actualizado);
  }

  if (error) return <p className="error">{error}</p>;

  return (
    <div>
      <h2>Calendario y parámetros</h2>

      <fieldset>
        <legend>Umbral del semáforo amarillo</legend>
        <label>
          Días de desvío que todavía se consideran "al límite"
          <input
            type="number"
            min={0}
            value={parametros?.umbral_amarillo_dias ?? 0}
            onChange={(e) => guardarUmbral(Number(e.target.value))}
          />
        </label>
      </fieldset>

      <fieldset>
        <legend>Feriados</legend>
        <ul className="lista-simple">
          {feriados.map((f) => (
            <li key={f.fecha}>
              {formatearFecha(f.fecha)}
              <button onClick={() => borrarFeriado(f.fecha)}>Quitar</button>
            </li>
          ))}
        </ul>
        <div className="fila-alta">
          <input type="date" value={nuevoFeriado} onChange={(e) => setNuevoFeriado(e.target.value)} />
          <button onClick={agregarFeriado}>+ Agregar feriado</button>
        </div>
      </fieldset>

      <fieldset>
        <legend>Excepciones por puesto y fecha (sábado trabajado, capacidad reducida, etc.)</legend>
        <ul className="lista-simple">
          {excepciones.map((e) => (
            <li key={`${e.puesto}-${e.fecha}`}>
              {e.puesto} — {formatearFecha(e.fecha)}: capacidad {e.capacidad}
              <button onClick={() => borrarExcepcion(e.puesto, e.fecha)}>Quitar</button>
            </li>
          ))}
        </ul>
        <div className="fila-alta">
          <select
            value={nuevaExcepcion.puesto}
            onChange={(ev) => setNuevaExcepcion((n) => ({ ...n, puesto: ev.target.value }))}
          >
            {puestos.map((p) => (
              <option key={p.nombre} value={p.nombre}>
                {p.nombre}
              </option>
            ))}
          </select>
          <input
            type="date"
            value={nuevaExcepcion.fecha}
            onChange={(ev) => setNuevaExcepcion((n) => ({ ...n, fecha: ev.target.value }))}
          />
          <input
            type="number"
            min={0}
            placeholder="Capacidad ese día"
            value={nuevaExcepcion.capacidad}
            onChange={(ev) => setNuevaExcepcion((n) => ({ ...n, capacidad: Number(ev.target.value) }))}
          />
          <button onClick={agregarExcepcion}>+ Agregar excepción</button>
        </div>
      </fieldset>
    </div>
  );
}
