import type { Semaforo as SemaforoValor } from "../api";

const COLORES: Record<string, string> = {
  verde: "#2e9e4f",
  amarillo: "#d9a400",
  rojo: "#c43b3b",
};

const ETIQUETAS: Record<string, string> = {
  verde: "A tiempo",
  amarillo: "Al límite",
  rojo: "Atrasado",
};

export default function Semaforo({ valor }: { valor: SemaforoValor }) {
  if (!valor) {
    return <span className="semaforo semaforo--vacio" title="Sin FTF o sin fecha estimada">—</span>;
  }
  return (
    <span
      className="semaforo"
      style={{ backgroundColor: COLORES[valor] }}
      title={ETIQUETAS[valor]}
    >
      {ETIQUETAS[valor]}
    </span>
  );
}
