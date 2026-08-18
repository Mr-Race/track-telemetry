import { useCallback, useState } from "react";
import { Link } from "react-router-dom";
import {
  createEvent,
  listEvents,
  listOrganizations,
  listTracks,
  type EventListItem,
  type EventPhase,
} from "../api/client";
import { useFetch } from "../api/useFetch";
import { Loading } from "../components/Loading";
import { IS_DEMO } from "../demoMode";

// Render order matches the server's row order; empty groups collapse
// rather than render an empty header.
const PHASE_GROUPS: { phase: EventPhase; heading: string }[] = [
  { phase: "in_progress", heading: "In progress" },
  { phase: "upcoming", heading: "Upcoming" },
  { phase: "past", heading: "Past" },
];

function EventGroup({ heading, events }: { heading: string; events: EventListItem[] }) {
  if (events.length === 0) return null;

  return (
    <>
      <div className="section-label">{heading}</div>
      <table className="data-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Organization</th>
            <th>Track</th>
            <th>Dates</th>
            <th>Sessions</th>
          </tr>
        </thead>
        <tbody>
          {events.map((ev) => (
            <tr key={ev.event_id}>
              <td>
                <Link to={`/events/${ev.event_id}`}>{ev.event_name}</Link>
              </td>
              <td>{ev.org_code}</td>
              <td>{ev.track_name}</td>
              {/* Each date stays whole; a multi-day range breaks at the
                  dash rather than mid-date. */}
              <td className="tabular">
                <span className="nowrap">{ev.start_date}</span>
                {ev.end_date && ev.end_date !== ev.start_date ? (
                  <>
                    {" – "}
                    <span className="nowrap">{ev.end_date}</span>
                  </>
                ) : null}
              </td>
              {/* An event with no sessions yet is valid in Upcoming /
                  In progress - em dash, not a zero. */}
              <td className="tabular">{ev.session_count > 0 ? ev.session_count : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

export function EventsPage() {
  const [refreshKey, setRefreshKey] = useState(0);
  const events = useFetch(listEvents, [refreshKey]);
  const organizations = useFetch(listOrganizations, []);
  const tracks = useFetch(listTracks, []);

  const [trackId, setTrackId] = useState("");
  const [organizationId, setOrganizationId] = useState("");
  const [eventName, setEventName] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const resetForm = useCallback(() => {
    setTrackId("");
    setOrganizationId("");
    setEventName("");
    setStartDate("");
    setEndDate("");
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setSubmitting(true);
    try {
      await createEvent({
        track_id: Number(trackId),
        organization_id: Number(organizationId),
        event_name: eventName.trim(),
        start_date: startDate,
        end_date: endDate || null,
      });
      resetForm();
      setRefreshKey((k) => k + 1);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      {/* Read-only demo: a form that can only fail is worse than no
          form. The events list below is the point of the page. */}
      {!IS_DEMO && (
      <>
      <h3>Create event</h3>
      <form className="event-form" onSubmit={handleSubmit}>
        <div className="form-row">
          <label>
            Event name
            <input
              className="form-input"
              type="text"
              value={eventName}
              onChange={(e) => setEventName(e.target.value)}
              required
            />
          </label>
          <label>
            Organization
            <select
              className="form-input"
              value={organizationId}
              onChange={(e) => setOrganizationId(e.target.value)}
              required
            >
              <option value="" disabled>
                Select organization
              </option>
              {organizations.status === "ready" &&
                organizations.data.map((o) => (
                  <option key={o.organization_id} value={o.organization_id}>
                    {o.org_name}
                  </option>
                ))}
            </select>
          </label>
        </div>
        <div className="form-row">
          <label>
            Track
            <select
              className="form-input"
              value={trackId}
              onChange={(e) => setTrackId(e.target.value)}
              required
            >
              <option value="" disabled>
                Select track
              </option>
              {tracks.status === "ready" &&
                tracks.data.map((t) => (
                  <option key={t.track_id} value={t.track_id}>
                    {t.track_name}
                    {t.configuration ? ` (${t.configuration})` : ""}
                  </option>
                ))}
            </select>
          </label>
        </div>
        <div className="form-row">
          <label>
            Start date
            <input
              className="form-input"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              required
            />
          </label>
          <label>
            End date (optional, multi-day events)
            <input
              className="form-input"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </label>
        </div>
        {formError && <p className="delta-bad">{formError}</p>}
        <button className="cta-button" type="submit" disabled={submitting}>
          {submitting ? "Creating…" : "Create event"}
        </button>
      </form>
      </>
      )}

      <h3>Events</h3>
      {events.status === "loading" && <Loading what="events" />}
      {events.status === "error" && <p className="delta-bad">Error: {events.message}</p>}
      {events.status === "ready" && events.data.length === 0 && (
        <p className="muted">No events yet.</p>
      )}
      {events.status === "ready" &&
        events.data.length > 0 &&
        PHASE_GROUPS.map((g) => (
          <EventGroup
            key={g.phase}
            heading={g.heading}
            events={events.data.filter((ev) => ev.phase === g.phase)}
          />
        ))}
    </div>
  );
}
