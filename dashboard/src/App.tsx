import { Link, Route, Routes } from "react-router-dom";
import { LandingPage } from "./pages/LandingPage";
import { SessionListPage } from "./pages/SessionListPage";
import { SessionDetailPage } from "./pages/SessionDetailPage";
import { ConsumablesPage } from "./pages/ConsumablesPage";
import { TrackDirectoryPage } from "./pages/TrackDirectoryPage";
import { TrackViewPage } from "./pages/TrackViewPage";

function App() {
  return (
    <div className="app-shell">
      <header>
        <h1>Track Telemetry</h1>
        <nav>
          <Link to="/">Home</Link>
          <Link to="/sessions">Sessions</Link>
          <Link to="/tracks">Tracks</Link>
          <Link to="/consumables">Consumables</Link>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/sessions" element={<SessionListPage />} />
          <Route path="/sessions/:sessionId" element={<SessionDetailPage />} />
          <Route path="/tracks" element={<TrackDirectoryPage />} />
          <Route path="/tracks/:trackId" element={<TrackViewPage />} />
          <Route path="/consumables" element={<ConsumablesPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
