import type { ReactElement } from "react";
import { Link, Navigate, Route, Routes } from "react-router-dom";
import {
  AuthenticatedTemplate,
  UnauthenticatedTemplate,
  useIsAuthenticated,
  useMsal,
} from "@azure/msal-react";
import { LandingPage } from "./pages/LandingPage";
import { DashboardHome } from "./pages/DashboardHome";
import { SessionListPage } from "./pages/SessionListPage";
import { SessionDetailPage } from "./pages/SessionDetailPage";
import { ConsumablesPage } from "./pages/ConsumablesPage";
import { TrackDirectoryPage } from "./pages/TrackDirectoryPage";
import { TrackViewPage } from "./pages/TrackViewPage";
import { EventsPage } from "./pages/EventsPage";
import { EventSummaryPage } from "./pages/EventSummaryPage";
import { CarsPage } from "./pages/CarsPage";
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

function RequireAuth({ children }: { children: ReactElement }) {
  const isAuthenticated = useIsAuthenticated();
  return isAuthenticated ? children : <Navigate to="/" replace />;
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
          <Link to="/events">Events</Link>
          <Link to="/cars">Cars</Link>
        </nav>
        <div className="auth-control">
          <AuthControl />
        </div>
      </header>
      <main>
        <Routes>
          <Route
            path="/"
            element={
              <>
                <AuthenticatedTemplate>
                  <DashboardHome />
                </AuthenticatedTemplate>
                <UnauthenticatedTemplate>
                  <LandingPage />
                </UnauthenticatedTemplate>
              </>
            }
          />
          <Route
            path="/sessions"
            element={
              <RequireAuth>
                <SessionListPage />
              </RequireAuth>
            }
          />
          <Route
            path="/sessions/:sessionId"
            element={
              <RequireAuth>
                <SessionDetailPage />
              </RequireAuth>
            }
          />
          <Route
            path="/tracks"
            element={
              <RequireAuth>
                <TrackDirectoryPage />
              </RequireAuth>
            }
          />
          <Route
            path="/tracks/:trackId"
            element={
              <RequireAuth>
                <TrackViewPage />
              </RequireAuth>
            }
          />
          <Route
            path="/events/:eventId"
            element={
              <RequireAuth>
                <EventSummaryPage />
              </RequireAuth>
            }
          />
          <Route
            path="/consumables"
            element={
              <RequireAuth>
                <ConsumablesPage />
              </RequireAuth>
            }
          />
          <Route
            path="/events"
            element={
              <RequireAuth>
                <EventsPage />
              </RequireAuth>
            }
          />
          <Route
            path="/cars"
            element={
              <RequireAuth>
                <CarsPage />
              </RequireAuth>
            }
          />
        </Routes>
      </main>
      <AppFooter />
    </div>
  );
}

function AppFooter() {
  // Version and commit are injected at build time (vite.config.ts). The
  // commit is the half that actually answers "which build is this" -
  // deploys are hand-run, so two builds of the same version are
  // routine, and after an incident the first question is always which
  // one is live.
  return (
    <footer className="app-footer">
      <a href="https://github.com/Mr-Race/track-telemetry">track-telemetry</a>
      {" v"}
      {__APP_VERSION__}
      <span className="app-footer-commit"> · {__APP_COMMIT__}</span>
    </footer>
  );
}

export default App;
