import { Route, Routes } from "react-router-dom";
import { SessionListPage } from "./pages/SessionListPage";
import { SessionDetailPage } from "./pages/SessionDetailPage";

function App() {
  return (
    <div className="app-shell">
      <header>
        <h1>Track Telemetry</h1>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<SessionListPage />} />
          <Route path="/sessions/:sessionId" element={<SessionDetailPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
