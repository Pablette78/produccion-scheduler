const BASE = "/api";

export type TipoPuesto = "capacidad" | "tiempo_fijo";
export type ModoDias = "corridos" | "habiles";
export type CondicionDeUso = "siempre" | "solo_si_el_trabajo_lo_lleva";
export type LoteTraspaso = number | "todo";

export interface Puesto {
  nombre: string;
  orden: number;
  predecesores: string[];
  tipo: TipoPuesto;
  unidad: string;
  capacidad_diaria: number | null;
  dias_fijos: number | null;
  modo_dias: ModoDias;
  lote_traspaso: LoteTraspaso;
  condicion_de_uso: CondicionDeUso;
  componente: string | null;
  es_laqueado: boolean;
}

export interface Faltante {
  material: string;
  puesto: string;
  fecha_estimada_llegada: string | null;
}

export interface Trabajo {
  nv: string;
  cliente: string;
  categoria: string;
  complejidad: number;
  vendedor: string;
  cantidades: Record<string, number>;
  cantidad_a_laquear: Record<string, number>;
  lleva_led: boolean;
  avance_por_puesto: Record<string, number>;
  ftf: string | null;
  fecha_real_terminado: string | null;
  faltantes: Faltante[];
  prioridad: number;
}

export type TrabajoIn = Omit<Trabajo, "prioridad">;

export interface Feriado {
  fecha: string;
}

export interface ExcepcionCalendario {
  puesto: string;
  fecha: string;
  capacidad: number;
}

export interface Parametros {
  umbral_amarillo_dias: number;
}

export interface ResultadoPuesto {
  puesto: string;
  total: number;
  avance: number;
  inicio: string | null;
  fin: string | null;
  bloqueado_sin_fecha: boolean;
  material_faltante: string | null;
}

export type Semaforo = "verde" | "amarillo" | "rojo" | null;

export interface ResultadoTrabajo {
  nv: string;
  cliente: string;
  ftf: string | null;
  fin_trabajo: string | null;
  desvio_dias: number | null;
  semaforo: Semaforo;
  avance_pct: number;
  carga_pendiente_dias: number;
  por_puesto: Record<string, ResultadoPuesto>;
}

export interface CargaDia {
  puesto: string;
  fecha: string;
  capacidad_total: number;
  capacidad_usada: number;
}

export interface Programa {
  hoy: string;
  trabajos: ResultadoTrabajo[];
  carga_diaria: CargaDia[];
}

export interface VistaPreviaExcel {
  hojas: string[];
  hoja: string;
  columnas: string[];
  filas_muestra: (string | null)[][];
  total_filas: number;
}

export interface MapeoImportacion {
  hoja: string;
  columna_nv: string;
  columna_cliente?: string | null;
  columna_categoria?: string | null;
  columna_vendedor?: string | null;
  columna_complejidad?: string | null;
  columna_ftf?: string | null;
  cantidades: Record<string, string>;
  cantidad_a_laquear: Record<string, string>;
  avance_por_puesto: Record<string, string>;
}

export interface ResultadoImportacion {
  creados: number;
  actualizados: number;
  filas_con_error: { fila: number; motivo: string }[];
}

async function solicitarArchivo<T>(ruta: string, cuerpo: FormData): Promise<T> {
  const respuesta = await fetch(`${BASE}${ruta}`, { method: "POST", body: cuerpo });
  if (!respuesta.ok) {
    const texto = await respuesta.text();
    throw new Error(`${respuesta.status} ${respuesta.statusText}: ${texto}`);
  }
  return respuesta.json() as Promise<T>;
}

async function solicitar<T>(ruta: string, opciones?: RequestInit): Promise<T> {
  const respuesta = await fetch(`${BASE}${ruta}`, {
    headers: { "Content-Type": "application/json" },
    ...opciones,
  });
  if (!respuesta.ok) {
    const cuerpo = await respuesta.text();
    throw new Error(`${respuesta.status} ${respuesta.statusText}: ${cuerpo}`);
  }
  if (respuesta.status === 204) return undefined as T;
  return respuesta.json() as Promise<T>;
}

export const api = {
  listarPuestos: () => solicitar<Puesto[]>("/puestos"),
  crearPuesto: (datos: Omit<Puesto, "orden">) =>
    solicitar<Puesto>("/puestos", { method: "POST", body: JSON.stringify(datos) }),
  actualizarPuesto: (nombre: string, datos: Omit<Puesto, "orden">) =>
    solicitar<Puesto>(`/puestos/${encodeURIComponent(nombre)}`, {
      method: "PUT",
      body: JSON.stringify(datos),
    }),
  borrarPuesto: (nombre: string) =>
    solicitar<void>(`/puestos/${encodeURIComponent(nombre)}`, { method: "DELETE" }),

  listarTrabajos: () => solicitar<Trabajo[]>("/trabajos"),
  crearTrabajo: (datos: TrabajoIn) =>
    solicitar<Trabajo>("/trabajos", { method: "POST", body: JSON.stringify(datos) }),
  actualizarTrabajo: (nv: string, datos: TrabajoIn) =>
    solicitar<Trabajo>(`/trabajos/${encodeURIComponent(nv)}`, {
      method: "PUT",
      body: JSON.stringify(datos),
    }),
  borrarTrabajo: (nv: string) =>
    solicitar<void>(`/trabajos/${encodeURIComponent(nv)}`, { method: "DELETE" }),
  reordenarTrabajos: (nvEnOrden: string[]) =>
    solicitar<Trabajo[]>("/trabajos/reordenar", {
      method: "POST",
      body: JSON.stringify({ nv_en_orden: nvEnOrden }),
    }),
  marcarTerminado: (nv: string, fecha: string | null) =>
    solicitar<Trabajo>(`/trabajos/${encodeURIComponent(nv)}/terminado`, {
      method: "PUT",
      body: JSON.stringify({ fecha_real_terminado: fecha }),
    }),

  listarFeriados: () => solicitar<Feriado[]>("/calendario/feriados"),
  agregarFeriado: (fecha: string) =>
    solicitar<void>("/calendario/feriados", { method: "POST", body: JSON.stringify({ fecha }) }),
  borrarFeriado: (fecha: string) =>
    solicitar<void>(`/calendario/feriados/${fecha}`, { method: "DELETE" }),

  listarExcepciones: () => solicitar<ExcepcionCalendario[]>("/calendario/excepciones"),
  agregarExcepcion: (datos: ExcepcionCalendario) =>
    solicitar<void>("/calendario/excepciones", { method: "POST", body: JSON.stringify(datos) }),
  borrarExcepcion: (puesto: string, fecha: string) =>
    solicitar<void>(`/calendario/excepciones/${encodeURIComponent(puesto)}/${fecha}`, {
      method: "DELETE",
    }),

  obtenerParametros: () => solicitar<Parametros>("/parametros"),
  actualizarParametros: (datos: Parametros) =>
    solicitar<Parametros>("/parametros", { method: "PUT", body: JSON.stringify(datos) }),

  obtenerPrograma: (hoy?: string) =>
    solicitar<Programa>(`/programa${hoy ? `?hoy=${hoy}` : ""}`),

  vistaPreviaExcel: (archivo: File, hoja?: string) => {
    const form = new FormData();
    form.append("archivo", archivo);
    if (hoja) form.append("hoja", hoja);
    return solicitarArchivo<VistaPreviaExcel>("/importar/excel/vista-previa", form);
  },
  aplicarImportacionExcel: (archivo: File, mapeo: MapeoImportacion) => {
    const form = new FormData();
    form.append("archivo", archivo);
    form.append("mapeo", JSON.stringify(mapeo));
    return solicitarArchivo<ResultadoImportacion>("/importar/excel/aplicar", form);
  },
};
