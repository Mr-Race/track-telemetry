import { Link } from "react-router-dom";
import { useMsal } from "@azure/msal-react";
import { listSessions, getConsumables, listTracks } from "../api/client";
import { useFetch } from "../api/useFetch";

export function DashboardHome() {
  const { accounts } = useMsal();
  const sessions = useFetch(listSessions, []);
  const consumables = useFetch(getConsumables, []);
  const tracks = useFetch(listTracks, []);

  const firstName = accounts[0]?.name?.split(" ")[0];
  const recentSession = sessions.status === "ready" ? sessions.data.at(-1) ?? null : null;
  const dueSoon =
    consumables.status === "ready"
      ? consumables.data.filter((c) => c.overdue || (c.remaining_pct !== null && c.remaining_pct < 25))
      : [];

  return (
    <div className="dashboard-home">
      <h2>{firstName ? `Welcome back, ${firstName}` : "Welcome back"}</h2>

      <div className="quick-link-row">
        <Link
          className="quick-link-card"
          to={recentSession ? `/sessions/${recentSession.session_id}` : "/sessions"}
        >
          <div className="quick-link-label">Most recent session</div>
          {sessions.status === "loading" && <div className="muted">Loading…</div>}
          {sessions.status === "error" && <div className="delta-bad">Couldn&apos;t load sessions</div>}
          {sessions.status === "ready" && recentSession && (
            <>
              <div className="quick-link-value">{recentSession.track_name}</div>
              <div className="muted">
                {recentSession.session_date} &middot; Best lap {recentSession.best_lap ?? "—"}
              </div>
            </>
          )}
          {sessions.status === "ready" && !recentSession && (
            <div className="muted">No sessions logged yet</div>
          )}
        </Link>

        <Link className="quick-link-card" to="/consumables">
          <div className="quick-link-label">Consumables due soon</div>
          {consumables.status === "loading" && <div className="muted">Loading…</div>}
          {consumables.status === "error" && <div className="delta-bad">Couldn&apos;t load consumables</div>}
          {consumables.status === "ready" && dueSoon.length > 0 && (
            <>
              <div className="quick-link-value">
                {dueSoon.length} item{dueSoon.length === 1 ? "" : "s"}
              </div>
              <div className="muted">{dueSoon.map((c) => c.item_name).join(", ")}</div>
            </>
          )}
          {consumables.status === "ready" && dueSoon.length === 0 && (
            <div className="muted">Nothing due soon</div>
          )}
        </Link>

        <Link className="quick-link-card" to="/tracks">
          <div className="quick-link-label">Track directory</div>
          {tracks.status === "loading" && <div className="muted">Loading…</div>}
          {tracks.status === "error" && <div className="delta-bad">Couldn&apos;t load tracks</div>}
          {tracks.status === "ready" && (
            <div className="quick-link-value">
              {tracks.data.length} track{tracks.data.length === 1 ? "" : "s"}
            </div>
          )}
        </Link>
      </div>
    </div>
  );
}
