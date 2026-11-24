import { useEffect, useState } from "react";
import { api, type MapeoImportacion, type Puesto, type ResultadoImportacion, type VistaPreviaExcel } from "../api";

const SIN_USAR = "";

export default function ImportarPage() {
  const [puestos, setPuestos] = useState<Puesto[]>([]);
  const [archivo, setArchivo] = useState<File | null>(null);
  const [vistaPrevia, setVistaPrevia] = useState<VistaPreviaExcel | null>(null);
  const [resultado, setResultado] = useState<ResultadoImportacion | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);

  const [mapeo, setMapeo] = useState<MapeoImportacion>({
    hoja: "",
    columna_nv: "",
    columna_cliente: null,
    columna_categoria: null,
    columna_vendedor: null,
    columna_complejidad: null,
    columna_ftf: null,
    cantidades: {},
    cantidad_a_laquear: {},
    avance_por_puesto: {},
  });

  useEffect(() => {
    api.listarPuestos().then(setPuestos).catch((e) => setError(String(e)));
  }, []);

  const componentes = [...new Set(puestos.map((p) => p.componente).filter(Boolean))] as string[];
  const nombresPuestos = puestos.map((p) => p.nombre);

  async function elegirArchivo(nuevoArchivo: File) {
    setArchivo(nuevoArchivo);
    setResultado(null);
    setError(null);
    setCargando(true);
    try {
      const vp = await api.vistaPreviaExcel(nuevoArchivo);
      setVistaPrevia(vp);
      setMapeo((m) => ({ ...m, hoja: vp.hoja, columna_nv: vp.columnas[0] ?? "" }));
    } catch (e) {
      setError(String(e));
    } finally {
      setCargando(false);
    }
  }

  async function cambiarHoja(hoja: string) {
    if (!archivo) return;
    setCargando(true);
    setError(null);
    try {
      const vp = await api.vistaPreviaExcel(archivo, hoja);
      setVistaPrevia(vp);
      setMapeo((m) => ({ ...m, hoja: vp.hoja, columna_nv: vp.columnas[0] ?? "" }));
    } catch (e) {
      setError(String(e));
    } finally {
      setCargando(false);
    }
  }

  function actualizarCampo(campo: keyof MapeoImportacion, valor: string) {
    setMapeo((m) => ({ ...m, [campo]: valor === SIN_USAR ? null : valor }));
  }

  function actualizarGrupo(
    grupo: "cantidades" | "cantidad_a_laquear" | "avance_por_puesto",
    clave: string,
    columna: string
  ) {
    setMapeo((m) => {
      const copia = { ...m[grupo] };
      if (columna === SIN_USAR) delete copia[clave];
      else copia[clave] = columna;
      return { ...m, [grupo]: copia };
    });
  }

  async function aplicar() {
    if (!archivo) return;
    setCargando(true);
    setError(null);
    try {
      const resultado = await api.aplicarImportacionExcel(archivo, mapeo);
      setResultado(resultado);
    } catch (e) {
      setError(String(e));
    } finally {
      setCargando(false);
    }
  }

  function SelectorColumna({
    etiqueta,
    valor,
    onCambio,
  }: {
    etiqueta: string;
    valor: string | null | undefined;
    onCambio: (v: string) => void;
  }) {
    return (
      <label>
        {etiqueta}
        <select value={valor ?? SIN_USAR} onChange={(e) => onCambio(e.target.value)}>
          <option value={SIN_USAR}>— no usar —</option>
          {vistaPrevia?.columnas.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </label>
    );
  }

  return (
    <div>
      <h2>Importar desde Excel</h2>
      <p className="nota">
        Las cantidades de puertas, cajoneras y cajones suelen venir en un archivo distinto al de
        placas: importalos uno por uno, con su propio mapeo. Si el NV ya existe, solo se actualizan
        los campos que mapeaste acá — el resto del trabajo queda como estaba.
      </p>

      {error && <p className="error">{error}</p>}

      <fieldset>
        <legend>1. Elegir archivo</legend>
        <input
          type="file"
          accept=".xlsx,.xlsm"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) elegirArchivo(f);
          }}
        />
        {vistaPrevia && vistaPrevia.hojas.length > 1 && (
          <label>
            Hoja
            <select value={mapeo.hoja} onChange={(e) => cambiarHoja(e.target.value)}>
              {vistaPrevia.hojas.map((h) => (
                <option key={h} value={h}>
                  {h}
                </option>
              ))}
            </select>
          </label>
        )}
      </fieldset>

      {vistaPrevia && (
        <>
          <fieldset>
            <legend>2. Vista previa ({vistaPrevia.total_filas} filas)</legend>
            <table className="tabla">
              <thead>
                <tr>
                  {vistaPrevia.columnas.map((c) => (
                    <th key={c}>{c}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {vistaPrevia.filas_muestra.map((fila, i) => (
                  <tr key={i}>
                    {fila.map((valor, j) => (
                      <td key={j}>{valor ?? "—"}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </fieldset>

          <fieldset>
            <legend>3. Mapeo de columnas</legend>
            <label>
              Columna de NV (clave para crear o actualizar)
              <select value={mapeo.columna_nv} onChange={(e) => actualizarCampo("columna_nv", e.target.value)}>
                {vistaPrevia.columnas.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </label>
            <SelectorColumna
              etiqueta="Cliente"
              valor={mapeo.columna_cliente}
              onCambio={(v) => actualizarCampo("columna_cliente", v)}
            />
            <SelectorColumna
              etiqueta="Categoría"
              valor={mapeo.columna_categoria}
              onCambio={(v) => actualizarCampo("columna_categoria", v)}
            />
            <SelectorColumna
              etiqueta="Vendedor"
              valor={mapeo.columna_vendedor}
              onCambio={(v) => actualizarCampo("columna_vendedor", v)}
            />
            <SelectorColumna
              etiqueta="Complejidad"
              valor={mapeo.columna_complejidad}
              onCambio={(v) => actualizarCampo("columna_complejidad", v)}
            />
            <SelectorColumna
              etiqueta="FTF"
              valor={mapeo.columna_ftf}
              onCambio={(v) => actualizarCampo("columna_ftf", v)}
            />
          </fieldset>

          <fieldset>
            <legend>Cantidades</legend>
            {componentes.map((comp) => (
              <SelectorColumna
                key={comp}
                etiqueta={comp}
                valor={mapeo.cantidades[comp]}
                onCambio={(v) => actualizarGrupo("cantidades", comp, v)}
              />
            ))}
          </fieldset>

          <fieldset>
            <legend>Cantidad a laquear</legend>
            {componentes.map((comp) => (
              <SelectorColumna
                key={comp}
                etiqueta={`${comp} a laquear`}
                valor={mapeo.cantidad_a_laquear[comp]}
                onCambio={(v) => actualizarGrupo("cantidad_a_laquear", comp, v)}
              />
            ))}
          </fieldset>

          <fieldset>
            <legend>Avance ya realizado</legend>
            {nombresPuestos.map((puesto) => (
              <SelectorColumna
                key={puesto}
                etiqueta={puesto}
                valor={mapeo.avance_por_puesto[puesto]}
                onCambio={(v) => actualizarGrupo("avance_por_puesto", puesto, v)}
              />
            ))}
          </fieldset>

          <div className="acciones-formulario">
            <button onClick={aplicar} disabled={cargando || !mapeo.columna_nv}>
              {cargando ? "Importando…" : "Aplicar importación"}
            </button>
          </div>
        </>
      )}

      {resultado && (
        <fieldset>
          <legend>Resultado</legend>
          <p>
            {resultado.creados} trabajos creados, {resultado.actualizados} actualizados.
          </p>
          {resultado.filas_con_error.length > 0 && (
            <ul className="lista-simple">
              {resultado.filas_con_error.map((e) => (
                <li key={e.fila}>
                  Fila {e.fila}: {e.motivo}
                </li>
              ))}
            </ul>
          )}
        </fieldset>
      )}
    </div>
  );
}
