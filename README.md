# Programador de producción de fábrica

App para programar la producción de una fábrica de placares/muebles a medida.

Se construye en etapas:

1. **Motor de cálculo** (`engine/`) — código puro, con tests. Es lo que hay hasta ahora.
2. **API** (`api/`) — todavía no construida.
3. **Interfaz web** (`web/`) — todavía no construida.

## Motor de cálculo

Simula día por día el avance de cada trabajo a través de los puestos de la
fábrica, respetando capacidad diaria, calendario laboral, precedencia entre
puestos, material faltante y el circuito de Laqueado (tercerizado, con
duración fija en días corridos).

### Correr los tests

```powershell
pip install -r engine/requirements.txt
pytest
```

(Correr `pytest` desde la raíz del proyecto, no desde `engine/`.)

### Decisiones de modelado a validar con el usuario

- **Centro → puestos de ensamble (Bancos, Puertas, Cajoneras, Cajones, LED):**
  cada puesto de ensamble tiene su propia cantidad total (puertas, cajones,
  etc.) tomada directamente del trabajo. La disponibilidad de esa cantidad
  avanza en la misma proporción en que Centro completa las placas del
  trabajo (si Centro lleva 60% de las placas, hay 60% de las puertas
  disponibles para procesar, redondeado hacia abajo al lote de traspaso).
  Esto evita tener que convertir unidades (placas → puertas) de forma
  explícita, pero es una aproximación — a confirmar con datos reales.
- **Laqueado:** se dispara cuando Centro terminó el 100% de las placas del
  trabajo (confirmado), dura 15 días corridos, y libera todo junto. Los
  puestos de ensamble procesan primero las unidades no laqueadas (según la
  misma proporción de avance de Centro) y suman las laqueadas cuando
  Laqueado entrega.
- **DTC1:** se trata como un puesto de capacidad con unidad "trabajos"
  (1 por trabajo), con lote de traspaso "todo" — el trabajo no pasa a Corte
  hasta que DTC1 lo completa (o ya viene marcado como completado en el
  avance).

### Parámetros pendientes de definir (ya están en el código con un valor por
defecto, pero son editables)

- Capacidad diaria de LED (metros/día) y de DTC1 (trabajos/día).
- Tamaño del lote de traspaso de cada puesto.
- Umbral del semáforo amarillo (días de desvío).
