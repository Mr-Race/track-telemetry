import { Fragment } from "react";
import { Link } from "react-router-dom";
import { listSessions, type SessionListItem } from "../api/client";
import { useFetch } from "../api/useFetch";

// Mirrors ingest/racechrono_parser.py's fmt_ms, for lap times computed
// client-side (event-level averages) that don't come pre-formatted from the API.
function formatMs(ms: number): string {
  const minutes = Math.floor(ms / 60000);
  const seconds = ((ms % 60000) / 1000).toFixed(3).padStart(6, "0");
  return `${minutes}:${seconds}`;
}

interface EventGroup {
  event_id: number;
  event_name: string;
  track_name: string;
  sessions: SessionListItem[];
}

function groupByEvent(sessions: SessionListItem[]): EventGroup[] {
  const groups: EventGroup[] = [];
  const byId = new Map<number, EventGroup>();
  for (const s of sessions) {
    let group = byId.get(s.event_id);
    if (!group) {
      group = { event_id: s.event_id, event_name: s.event_name, track_name: s.track_name, sessions: [] };
      byId.set(s.event_id, group);
      groups.push(group);
    }
    group.sessions.push(s);
  }
  return groups;
}

function dateRange(sessions: SessionListItem[]): string {
  const start = sessions[0].session_date;
  const end = sessions[sessions.length - 1].session_date;
  return start === end ? start : `${start} – ${end}`;
}

function runGroupSummary(sessions: SessionListItem[]): string {
  const groups = new Set(sessions.map((s) => s.run_group).filter((g): g is string => g !== null));
  if (groups.size === 0) return "—";
  if (groups.size === 1) return [...groups][0];
  return "Mixed";
}

function carSummary(sessions: SessionListItem[]): string {
  const cars = new Set(sessions.map((s) => s.car).filter((c): c is string => c !== null));
  if (cars.size === 0) return "—";
  if (cars.size === 1) return [...cars][0];
  return "Mixed";
}

function eventBestLap(sessions: SessionListItem[]): string {
  const best = sessions.reduce<SessionListItem | null>((acc, s) => {
    if (s.best_lap_ms === null) return acc;
    if (acc === null || s.best_lap_ms < acc.best_lap_ms!) return s;
    return acc;
  }, null);
  return best?.best_lap ?? "—";
}

function eventAvgValidLap(sessions: SessionListItem[]): string {
  const values = sessions.map((s) => s.avg_valid_lap_ms).filter((v): v is number => v !== null);
  if (values.length === 0) return "—";
  const avg = values.reduce((a, b) => a + b, 0) / values.length;
  return formatMs(Math.round(avg));
}

export function SessionListPage() {
  const state = useFetch(listSessions, []);

  if (state.status === "loading") return <p className="muted">Loading sessions…</p>;
  if (state.status === "error") return <p className="delta-bad">Error: {state.message}</p>;

  const sessions = state.data;
  if (sessions.length === 0) return <p className="muted">No sessions recorded yet.</p>;

  const groups = groupByEvent(sessions);

  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Event</th>
          <th>Date range</th>
          <th>Track</th>
          <th>Sessions</th>
          <th>Run group</th>
          <th>Car</th>
          <th>Best lap</th>
          <th>Avg valid lap</th>
        </tr>
      </thead>
      <tbody>
        {groups.map((g) => (
          <Fragment key={g.event_id}>
            <tr className="event-row">
              <td>
                <Link to={`/events/${g.event_id}`}>{g.event_name}</Link>
              </td>
              <td className="tabular">{dateRange(g.sessions)}</td>
              <td>{g.track_name}</td>
              <td className="tabular">{g.sessions.length}</td>
              <td>{runGroupSummary(g.sessions)}</td>
              <td>{carSummary(g.sessions)}</td>
              <td className="tabular">{eventBestLap(g.sessions)}</td>
              <td className="tabular">{eventAvgValidLap(g.sessions)}</td>
            </tr>
            {g.sessions.map((s) => (
              <tr key={s.session_id} className="session-row muted">
                <td className="indent">
                  <Link to={`/sessions/${s.session_id}`}>Session #{s.session_number}</Link>
                </td>
                <td className="tabular">{s.session_date}</td>
                <td></td>
                <td></td>
                <td>{s.run_group ?? "—"}</td>
                <td>{s.car ?? "—"}</td>
                <td className="tabular">{s.best_lap ?? "—"}</td>
                <td className="tabular">{s.avg_valid_lap ?? "—"}</td>
              </tr>
            ))}
          </Fragment>
        ))}
      </tbody>
    </table>
  );
}
