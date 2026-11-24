import { NavLink, Route, Routes } from "react-router-dom";
import CalendarioPage from "./pages/CalendarioPage";
import CargaDiariaPage from "./pages/CargaDiariaPage";
import GanttPage from "./pages/GanttPage";
import ImportarPage from "./pages/ImportarPage";
import PuestosPage from "./pages/PuestosPage";
import TrabajoFormPage from "./pages/TrabajoFormPage";
import TrabajosPage from "./pages/TrabajosPage";

function App() {
  return (
    <div className="app">
      <header className="barra-superior">
        <h1>Programador de producción</h1>
        <nav>
          <NavLink to="/" end>
            Trabajos
          </NavLink>
          <NavLink to="/gantt">Gantt</NavLink>
          <NavLink to="/carga-diaria">Carga diaria</NavLink>
          <NavLink to="/puestos">Puestos</NavLink>
          <NavLink to="/calendario">Calendario</NavLink>
          <NavLink to="/importar">Importar</NavLink>
        </nav>
      </header>
      <main className="contenido">
        <Routes>
          <Route path="/" element={<TrabajosPage />} />
          <Route path="/trabajos/nuevo" element={<TrabajoFormPage />} />
          <Route path="/trabajos/:nv/editar" element={<TrabajoFormPage />} />
          <Route path="/gantt" element={<GanttPage />} />
          <Route path="/carga-diaria" element={<CargaDiariaPage />} />
          <Route path="/puestos" element={<PuestosPage />} />
          <Route path="/calendario" element={<CalendarioPage />} />
          <Route path="/importar" element={<ImportarPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
