import { Link } from "react-router-dom";
import { listSessions } from "../api/client";
import { useFetch } from "../api/useFetch";

export function SessionListPage() {
  const state = useFetch(listSessions, []);

  if (state.status === "loading") return <p className="muted">Loading sessions…</p>;
  if (state.status === "error") return <p className="delta-bad">Error: {state.message}</p>;

  const sessions = state.data;
  if (sessions.length === 0) return <p className="muted">No sessions recorded yet.</p>;

  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Date</th>
          <th>Event</th>
          <th>Track</th>
          <th>Session</th>
          <th>Run group</th>
          <th>Best lap</th>
          <th>Avg valid lap</th>
        </tr>
      </thead>
      <tbody>
        {sessions.map((s) => (
          <tr key={s.session_id}>
            <td className="tabular">{s.session_date}</td>
            <td>{s.event_name}</td>
            <td>{s.track_name}</td>
            <td>
              <Link to={`/sessions/${s.session_id}`}>#{s.session_number}</Link>
            </td>
            <td>{s.run_group ?? "—"}</td>
            <td className="tabular">{s.best_lap ?? "—"}</td>
            <td className="tabular">{s.avg_valid_lap ?? "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
