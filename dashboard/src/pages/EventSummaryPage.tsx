import { Fragment } from "react";
import { Link, useParams } from "react-router-dom";
import { getEventSummary, type EventSummary } from "../api/client";
import { useFetch } from "../api/useFetch";
import { StatTile } from "../components/StatTile";
import { CornerDeltaTable } from "../components/CornerDeltaTable";
import { Loading } from "../components/Loading";
import {
  EMPTY, formatDateRange, formatDuration, formatSeconds,
  formatSignedSeconds, formatStartTime, progressPct,
} from "../format";

function Header({ event }: { event: EventSummary }) {
  // EVENT - ORG - RUN GROUP; the run group drops out when the event's
  // sessions don't share one.
  const eyebrow = ["Event", event.org_code, event.run_group].filter(Boolean).join(" · ");
  const subtitle = [event.track_name, event.configuration, formatDateRange(event.start_date, event.end_date)]
    .filter(Boolean)
    .join(" · ");

  return (
    <div>
      <div className="event-eyebrow">{eyebrow}</div>
      <h2 className="event-title">{event.event_name}</h2>
      <p className="event-subtitle">{subtitle}</p>
      <div className="badge-row">
        <span className="badge">
          {event.session_count} session{event.session_count === 1 ? "" : "s"}
        </span>
        <span className="badge">
          {event.total_laps} lap{event.total_laps === 1 ? "" : "s"}
        </span>
      </div>
    </div>
  );
}

function HeroStats({ event }: { event: EventSummary }) {
  return (
    <>
      <div className="section-label">Hero stats</div>
      <div className="hero-grid">
        <StatTile
          variant="hero"
          label="Event best"
          value={event.best_lap ?? EMPTY}
          tone={event.best_lap ? "fastest" : undefined}
          sublabel={
            event.best_lap_session_number !== null && event.best_lap_number !== null
              ? `session ${event.best_lap_session_number}, lap ${event.best_lap_number}`
              : undefined
          }
        />
        <StatTile
          variant="hero"
          label="Event optimal"
          value={event.optimal_lap ?? EMPTY}
          tone={event.optimal_lap ? "fastest" : undefined}
          sublabel="best segments, any session"
        />
        <StatTile
          variant="hero"
          label="Left on table"
          value={event.left_on_table_ms !== null ? formatSeconds(event.left_on_table_ms) : EMPTY}
          sublabel="best vs optimal"
        />
        <StatTile
          variant="hero"
          label="Progression"
          value={event.progression_ms !== null ? formatSignedSeconds(event.progression_ms) : EMPTY}
          // Negative is the day getting faster.
          tone={
            event.progression_ms === null
              ? undefined
              : event.progression_ms < 0
                ? "good"
                : event.progression_ms > 0
                  ? "bad"
                  : undefined
          }
          sublabel={
            event.sessions.length >= 2
              ? `S${event.sessions[0].session_number} best → S${
                  event.sessions[event.sessions.length - 1].session_number
                } best`
              : undefined
          }
        />
        <StatTile
          variant="hero"
          label="Laps"
          value={event.total_laps > 0 ? String(event.total_laps) : EMPTY}
          sublabel={event.total_laps > 0 ? `${event.valid_lap_count} valid` : undefined}
        />
        <StatTile
          variant="hero"
          label="Track time"
          value={event.total_track_time_ms !== null ? formatDuration(event.total_track_time_ms) : EMPTY}
          sublabel={
            event.session_count > 0
              ? `across ${event.session_count} session${event.session_count === 1 ? "" : "s"}`
              : undefined
          }
        />
      </div>
    </>
  );
}

function SessionsTable({ event }: { event: EventSummary }) {
  return (
    <>
      <div className="section-label">Sessions</div>
      {event.sessions.length === 0 ? (
        <p className="muted">No sessions logged for this event yet.</p>
      ) : (
        <table className="data-table timing-table">
          <thead>
            <tr>
              <th>Session</th>
              <th>Best</th>
              <th>Avg</th>
              <th>Optimal</th>
              <th>WX</th>
            </tr>
          </thead>
          <tbody>
            {event.sessions.map((s) => (
              <Fragment key={s.session_id}>
                <tr className="session-main">
                  <td>
                    <Link to={`/sessions/${s.session_id}`}>
                      S{s.session_number} &middot; {formatStartTime(s.start_time)}
                    </Link>
                    {/* Hero stats count every driver's laps, so a
                        session someone else drove has to say so here or
                        the page silently credits it to the owner. */}
                    {s.driver !== "Me" && (
                      <span className="session-driver"> {s.driver}</span>
                    )}
                  </td>
                  {/* The event's best lap is purple wherever it appears. */}
                  <td
                    className={
                      s.best_lap_ms !== null && s.best_lap_ms === event.best_lap_ms
                        ? "tabular tone-fastest"
                        : "tabular"
                    }
                  >
                    {s.best_lap ?? EMPTY}
                  </td>
                  <td className="tabular">{s.avg_valid_lap ?? EMPTY}</td>
                  <td className="tabular">{s.optimal_lap ?? EMPTY}</td>
                  <td className="tabular">{s.air_temp_f !== null ? `${s.air_temp_f}°F` : EMPTY}</td>
                </tr>
                <tr>
                  <td className="progress-cell" colSpan={5}>
                    <div className="progress-bar-track">
                      <div
                        className="progress-bar-fill pace-fill"
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
    </>
  );
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

  if (state.status === "loading") return <Loading what="event" />;
  if (state.status === "error") return <p className="delta-bad">Error: {state.message}</p>;

  const event = state.data;
  const first = event.sessions[0];
  const last = event.sessions[event.sessions.length - 1];

  return (
    <div>
      <p>
        <Link to="/sessions">&larr; All sessions</Link>
      </p>

      <Header event={event} />
      <HeroStats event={event} />
      <SessionsTable event={event} />

      {/* Single-session events have no arc to tell, so the whole
          section is hidden rather than rendered empty. */}
      {event.corner_deltas.length > 0 && first && last && (
        <>
          <div className="section-label">Corner story</div>
          <p className="section-note">
            What improved from first to last session of the day — the arc of the event.
          </p>
          <CornerDeltaTable
            deltas={event.corner_deltas}
            labels={{
              current: `S${last.session_number} min`,
              prior: `S${first.session_number} min`,
            }}
            className="timing-table"
            columnOrder="prior-first"
          />
        </>
      )}

      <WeatherStrip weather={event.weather} />
    </div>
  );
}
