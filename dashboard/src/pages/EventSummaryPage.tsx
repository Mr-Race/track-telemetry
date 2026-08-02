import { Link, useParams } from "react-router-dom";
import { listSessions } from "../api/client";
import { useFetch } from "../api/useFetch";

export function EventSummaryPage() {
  const { eventId } = useParams<{ eventId: string }>();
  const id = Number(eventId);

  const state = useFetch(listSessions, []);

  if (state.status === "loading") return <p className="muted">Loading event…</p>;
  if (state.status === "error") return <p className="delta-bad">Error: {state.message}</p>;

  const sessions = state.data.filter((s) => s.event_id === id);
  if (sessions.length === 0) return <p className="muted">Event not found.</p>;

  const { event_name, track_name } = sessions[0];

  return (
    <div>
      <p>
        <Link to="/sessions">&larr; All sessions</Link>
      </p>
      <h2>
        {event_name} &mdash; {track_name}
      </h2>
      <p className="muted">Event summary dashboard coming soon.</p>

      <table className="data-table">
        <thead>
          <tr>
            <th>Session</th>
            <th>Date</th>
            <th>Run group</th>
            <th>Car</th>
            <th>Best lap</th>
            <th>Avg valid lap</th>
            <th>Optimal lap</th>
          </tr>
        </thead>
        <tbody>
          {sessions.map((s) => (
            <tr key={s.session_id}>
              <td>
                <Link to={`/sessions/${s.session_id}`}>#{s.session_number}</Link>
              </td>
              <td className="tabular">{s.session_date}</td>
              <td>{s.run_group ?? "—"}</td>
              <td>{s.car ?? "—"}</td>
              <td className="tabular">{s.best_lap ?? "—"}</td>
              <td className="tabular">{s.avg_valid_lap ?? "—"}</td>
              <td className="tabular">{s.optimal_lap ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
