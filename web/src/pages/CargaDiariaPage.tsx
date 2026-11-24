import { useEffect, useMemo, useState } from "react";
import { api, type Programa } from "../api";
import { formatearFecha } from "../fecha";

export default function CargaDiariaPage() {
  const [programa, setPrograma] = useState<Programa | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.obtenerPrograma().then(setPrograma).catch((e) => setError(String(e)));
  }, []);

  const porPuesto = useMemo(() => {
    const mapa = new Map<string, Programa["carga_diaria"]>();
    if (!programa) return mapa;
    for (const carga of programa.carga_diaria) {
      const lista = mapa.get(carga.puesto) ?? [];
      lista.push(carga);
      mapa.set(carga.puesto, lista);
    }
    for (const lista of mapa.values()) lista.sort((a, b) => a.fecha.localeCompare(b.fecha));
    return mapa;
  }, [programa]);

  if (error) return <p className="error">{error}</p>;
  if (!programa) return <p>Cargando…</p>;

  return (
    <div>
      <h2>Carga diaria por puesto</h2>
      <p className="nota">Cuellos de botella: días donde la capacidad usada se acerca al 100%.</p>

      {[...porPuesto.entries()].map(([puesto, dias]) => (
        <div className="carga-puesto" key={puesto}>
          <h3>{puesto}</h3>
          <div className="carga-barras">
            {dias.map((dia) => {
              const porcentaje = dia.capacidad_total > 0 ? (dia.capacidad_usada / dia.capacidad_total) * 100 : 0;
              const color = porcentaje >= 100 ? "#c43b3b" : porcentaje >= 70 ? "#d9a400" : "#2e9e4f";
              return (
                <div
                  className="carga-barra-dia"
                  key={dia.fecha}
                  title={`${formatearFecha(dia.fecha)}: ${dia.capacidad_usada}/${dia.capacidad_total}`}
                >
                  <div
                    className="carga-barra-dia__relleno"
                    style={{ height: `${Math.min(porcentaje, 100)}%`, backgroundColor: color }}
                  />
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
