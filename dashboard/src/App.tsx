import { Link, Route, Routes } from "react-router-dom";
import { SessionListPage } from "./pages/SessionListPage";
import { SessionDetailPage } from "./pages/SessionDetailPage";
import { ConsumablesPage } from "./pages/ConsumablesPage";

function App() {
  return (
    <div className="app-shell">
      <header>
        <h1>Track Telemetry</h1>
        <nav>
          <Link to="/">Sessions</Link>
          <Link to="/consumables">Consumables</Link>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<SessionListPage />} />
          <Route path="/sessions/:sessionId" element={<SessionDetailPage />} />
          <Route path="/consumables" element={<ConsumablesPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
