import { useCallback, useState } from "react";
import {
  createEvent,
  listEvents,
  listOrganizations,
  listTracks,
} from "../api/client";
import { useFetch } from "../api/useFetch";

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

      <h3>Events</h3>
      {events.status === "loading" && <p className="muted">Loading events…</p>}
      {events.status === "error" && <p className="delta-bad">Error: {events.message}</p>}
      {events.status === "ready" && events.data.length === 0 && (
        <p className="muted">No events yet.</p>
      )}
      {events.status === "ready" && events.data.length > 0 && (
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
            {events.data.map((ev) => (
              <tr key={ev.event_id}>
                <td>{ev.event_name}</td>
                <td>{ev.org_code}</td>
                <td>{ev.track_name}</td>
                <td className="tabular">
                  {ev.start_date}
                  {ev.end_date && ev.end_date !== ev.start_date ? ` – ${ev.end_date}` : ""}
                </td>
                <td className="tabular">{ev.session_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
