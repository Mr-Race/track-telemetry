import { useCallback, useState } from "react";
import { createCar, listCars } from "../api/client";
import { useFetch } from "../api/useFetch";
import { Loading } from "../components/Loading";
import { IS_DEMO } from "../demoMode";

export function CarsPage() {
  const [refreshKey, setRefreshKey] = useState(0);
  const cars = useFetch(listCars, [refreshKey]);

  const [displayName, setDisplayName] = useState("");
  const [make, setMake] = useState("");
  const [model, setModel] = useState("");
  const [year, setYear] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const resetForm = useCallback(() => {
    setDisplayName("");
    setMake("");
    setModel("");
    setYear("");
    setNotes("");
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setSubmitting(true);
    try {
      await createCar({
        display_name: displayName.trim(),
        make: make.trim() || null,
        model: model.trim() || null,
        year: year ? Number(year) : null,
        notes: notes.trim() || null,
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
      {/* Read-only demo - see EventsPage. */}
      {!IS_DEMO && (
      <>
      <h3>Add car</h3>
      <form className="event-form" onSubmit={handleSubmit}>
        <div className="form-row">
          <label>
            Display name
            <input
              className="form-input"
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="e.g. E92 M3"
              required
            />
          </label>
          <label>
            Year
            <input
              className="form-input"
              type="number"
              value={year}
              onChange={(e) => setYear(e.target.value)}
            />
          </label>
        </div>
        <div className="form-row">
          <label>
            Make
            <input
              className="form-input"
              type="text"
              value={make}
              onChange={(e) => setMake(e.target.value)}
            />
          </label>
          <label>
            Model
            <input
              className="form-input"
              type="text"
              value={model}
              onChange={(e) => setModel(e.target.value)}
            />
          </label>
        </div>
        <div className="form-row">
          <label>
            Notes
            <input
              className="form-input"
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </label>
        </div>
        {formError && <p className="delta-bad">{formError}</p>}
        <button className="cta-button" type="submit" disabled={submitting}>
          {submitting ? "Adding…" : "Add car"}
        </button>
      </form>
      </>
      )}

      <h3>Cars</h3>
      {cars.status === "loading" && <Loading what="cars" />}
      {cars.status === "error" && <p className="delta-bad">Error: {cars.message}</p>}
      {cars.status === "ready" && cars.data.length === 0 && (
        <p className="muted">No cars yet.</p>
      )}
      {cars.status === "ready" && cars.data.length > 0 && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Year</th>
              <th>Make</th>
              <th>Model</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            {cars.data.map((c) => (
              <tr key={c.car_id}>
                <td>{c.display_name}</td>
                <td className="tabular">{c.year ?? "—"}</td>
                <td>{c.make ?? "—"}</td>
                <td>{c.model ?? "—"}</td>
                <td>{c.notes ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
