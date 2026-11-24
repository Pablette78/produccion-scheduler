# Programador de producción de fábrica

App para programar la producción de una fábrica de placares/muebles a medida.

Se construye en etapas:

1. **Motor de cálculo** (`engine/`) — código puro, con tests. Listo.
2. **API** (`api/`) — FastAPI + SQLite, envuelve el motor con persistencia. Lista.
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

## API

Envuelve el motor con persistencia en SQLite (`data/produccion.sqlite3`,
se crea sola al arrancar) y siembra la tabla de puestos por defecto la
primera vez.

### Correr la API

```powershell
pip install -r api/requirements.txt
uvicorn api.main:app --reload
```

Documentación interactiva en `http://127.0.0.1:8000/docs`.

### Endpoints principales

- `GET/POST/PUT/DELETE /puestos` — tabla de puestos (sección 2).
- `GET/POST/PUT/DELETE /trabajos` y `POST /trabajos/reordenar` — cola de
  trabajos y su prioridad (drag & drop en la futura UI).
- `GET/POST/DELETE /calendario/feriados` y `/calendario/excepciones` —
  calendario laboral (sección 5).
- `GET/PUT /parametros` — umbral del semáforo amarillo.
- `GET /programa` — corre el motor y devuelve el cronograma completo:
  fechas por puesto y por trabajo, semáforo contra FTF, y carga diaria por
  puesto contra su capacidad (para el Gantt y el gráfico de cuellos de
  botella, sección 8).

### Tests

```powershell
pip install -r api/requirements.txt
pytest
```

(El mismo comando de arriba corre los tests del motor y de la API juntos.)
