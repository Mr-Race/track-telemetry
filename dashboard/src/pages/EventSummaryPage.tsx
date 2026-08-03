import { Fragment } from "react";
import { Link, useParams } from "react-router-dom";
import { getEventSummary, type EventSessionRow, type EventSummary } from "../api/client";
import { useFetch } from "../api/useFetch";
import { StatTile } from "../components/StatTile";
import { CornerDeltaTable } from "../components/CornerDeltaTable";

function formatDateRange(start: string, end: string | null): string {
  return end === null || end === start ? start : `${start} – ${end}`;
}

function formatDuration(ms: number): string {
  const totalMinutes = Math.round(ms / 60000);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
}

function formatGap(ms: number): string {
  return `+${(ms / 1000).toFixed(3)}s`;
}

function formatSignedGap(ms: number): string {
  const seconds = ms / 1000;
  return seconds >= 0 ? `+${seconds.toFixed(3)}s` : `${seconds.toFixed(3)}s`;
}

function formatStartTime(startTime: string | null): string {
  if (startTime === null) return "—";
  const date = new Date(startTime.replace(" ", "T"));
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

// Fastest session in the event fills the bar completely; the slowest
// is empty - a quick visual arc of how the day's pace moved.
function progressPct(bestLapMs: number | null, sessions: EventSessionRow[]): number {
  if (bestLapMs === null) return 0;
  const times = sessions.map((s) => s.best_lap_ms).filter((t): t is number => t !== null);
  if (times.length === 0) return 0;
  const fastest = Math.min(...times);
  const slowest = Math.max(...times);
  if (fastest === slowest) return 100;
  return Math.round(((slowest - bestLapMs) / (slowest - fastest)) * 100);
}

function WeatherStrip({ weather }: { weather: EventSummary["weather"] }) {
  if (weather === null) return null;
  const tempRange =
    weather.temp_min_f !== null && weather.temp_max_f !== null
      ? weather.temp_min_f === weather.temp_max_f
        ? `${weather.temp_min_f}°F`
        : `${weather.temp_min_f}–${weather.temp_max_f}°F`
      : null;
  const parts = [tempRange, weather.conditions.join(", ") || null].filter(Boolean);
  if (parts.length === 0) return null;
  return <p className="muted">{parts.join(" · ")}</p>;
}

export function EventSummaryPage() {
  const { eventId } = useParams<{ eventId: string }>();
  const id = Number(eventId);

  const state = useFetch(() => getEventSummary(id), [id]);

  if (state.status === "loading") return <p className="muted">Loading event…</p>;
  if (state.status === "error") return <p className="delta-bad">Error: {state.message}</p>;

  const event = state.data;

  return (
    <div>
      <p>
        <Link to="/sessions">&larr; All sessions</Link>
      </p>
      <div className="eyebrow">{event.org_code}</div>
      <h2>
        {event.event_name} &mdash; {event.track_name}
      </h2>
      <p className="muted">
        {formatDateRange(event.start_date, event.end_date)} · {event.session_count}{" "}
        session{event.session_count === 1 ? "" : "s"} · {event.total_laps} laps
        {event.total_track_time_ms !== null && ` · ${formatDuration(event.total_track_time_ms)} on track`}
      </p>

      <div className="stat-tile-row">
        {event.best_lap && (
          <StatTile
            label="Event best lap"
            value={event.best_lap}
            sublabel={`session #${event.best_lap_session_number}`}
          />
        )}
        {event.optimal_lap && (
          <StatTile label="Event optimal lap" value={event.optimal_lap} sublabel="best segments, all sessions" />
        )}
        {event.left_on_table_ms !== null && (
          <StatTile label="Left on table" value={formatGap(event.left_on_table_ms)} sublabel="best vs. optimal" />
        )}
        {event.progression_ms !== null && (
          <StatTile
            label="Progression"
            value={formatSignedGap(event.progression_ms)}
            sublabel="first session vs. last"
          />
        )}
      </div>

      <WeatherStrip weather={event.weather} />

      <h3>Sessions</h3>
      {event.sessions.length === 0 ? (
        <p className="muted">No sessions logged for this event yet.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Session</th>
              <th>Best lap</th>
              <th>Avg valid lap</th>
              <th>Optimal lap</th>
              <th>Temp</th>
            </tr>
          </thead>
          <tbody>
            {event.sessions.map((s) => (
              <Fragment key={s.session_id}>
                <tr>
                  <td>
                    <Link to={`/sessions/${s.session_id}`}>
                      #{s.session_number} &middot; {formatStartTime(s.start_time)}
                    </Link>
                  </td>
                  <td className="tabular">{s.best_lap ?? "—"}</td>
                  <td className="tabular">{s.avg_valid_lap ?? "—"}</td>
                  <td className="tabular">{s.optimal_lap ?? "—"}</td>
                  <td className="tabular">{s.air_temp_f !== null ? `${s.air_temp_f}°F` : "—"}</td>
                </tr>
                <tr>
                  <td colSpan={5}>
                    <div className="progress-bar-track">
                      <div
                        className="progress-bar-fill"
                        style={{ width: `${progressPct(s.best_lap_ms, event.sessions)}%` }}
                      />
                    </div>
                  </td>
                </tr>
              </Fragment>
            ))}
          </tbody>
        </table>
      )}

      {event.corner_deltas.length > 0 && (
        <>
          <h3>Corner story of the day</h3>
          <CornerDeltaTable
            deltas={event.corner_deltas}
            labels={{ current: "Last session", prior: "First session" }}
          />
        </>
      )}
    </div>
  );
}
