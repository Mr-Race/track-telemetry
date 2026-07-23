import { Link, Route, Routes } from "react-router-dom";
import {
  AuthenticatedTemplate,
  UnauthenticatedTemplate,
  useMsal,
} from "@azure/msal-react";
import { LandingPage } from "./pages/LandingPage";
import { SessionListPage } from "./pages/SessionListPage";
import { SessionDetailPage } from "./pages/SessionDetailPage";
import { ConsumablesPage } from "./pages/ConsumablesPage";
import { TrackDirectoryPage } from "./pages/TrackDirectoryPage";
import { TrackViewPage } from "./pages/TrackViewPage";
import { loginRequest } from "./authConfig";

function AuthControl() {
  const { instance, accounts } = useMsal();

  return (
    <>
      <AuthenticatedTemplate>
        <span className="auth-account">{accounts[0]?.name ?? accounts[0]?.username}</span>
        <button
          className="auth-button"
          onClick={() => instance.logoutRedirect()}
        >
          Sign out
        </button>
      </AuthenticatedTemplate>
      <UnauthenticatedTemplate>
        <button
          className="auth-button"
          onClick={() => instance.loginRedirect(loginRequest)}
        >
          Sign in
        </button>
      </UnauthenticatedTemplate>
    </>
  );
}

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
        <div className="auth-control">
          <AuthControl />
        </div>
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
