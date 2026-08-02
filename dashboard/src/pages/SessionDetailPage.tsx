import { useCallback, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getSessionDetail, getSessionSummary, listCars, updateSessionCar } from "../api/client";
import { useFetch } from "../api/useFetch";
import { StatTile } from "../components/StatTile";
import { CornerDeltaTable } from "../components/CornerDeltaTable";
import { TrackPanel } from "../components/TrackPanel";

function formatStdev(ms: number): string {
  return `±${(ms / 1000).toFixed(3)}s`;
}

function formatGap(ms: number): string {
  return `+${(ms / 1000).toFixed(3)}s`;
}

function CarAssignment({
  sessionId,
  carId,
  onSaved,
}: {
  sessionId: number;
  carId: number | null;
  onSaved: () => void;
}) {
  const cars = useFetch(listCars, []);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const value = e.target.value ? Number(e.target.value) : null;
    setSaving(true);
    setError(null);
    try {
      await updateSessionCar(sessionId, value);
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  if (cars.status !== "ready") return null;

  return (
    <span>
      {" · "}
      <select
        className="form-input"
        value={carId ?? ""}
        onChange={handleChange}
        disabled={saving}
      >
        <option value="">No car assigned</option>
        {cars.data.map((c) => (
          <option key={c.car_id} value={c.car_id}>
            {c.display_name}
          </option>
        ))}
      </select>
      {error && <span className="delta-bad"> {error}</span>}
    </span>
  );
}

export function SessionDetailPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const id = Number(sessionId);
  const [refreshKey, setRefreshKey] = useState(0);

  const load = useCallback(
    () => Promise.all([getSessionDetail(id), getSessionSummary(id)]),
    [id],
  );
  const state = useFetch(load, [id, refreshKey]);

  if (state.status === "loading") return <p className="muted">Loading session…</p>;
  if (state.status === "error") return <p className="delta-bad">Error: {state.message}</p>;

  const [detail, summary] = state.data;

  return (
    <div>
      <p>
        <Link to="/sessions">&larr; All sessions</Link>
      </p>
      <h2>
        {detail.track_name} &mdash; {detail.event_name}
      </h2>
      <p className="muted">
        {detail.session_date} &middot; Session #{detail.session_number}
        {detail.run_group && ` · ${detail.run_group}`}
        {detail.weather && ` · ${detail.weather}`}
        {detail.air_temp_f !== null && ` · ${detail.air_temp_f}°F`}
        <CarAssignment
          key={detail.car_id}
          sessionId={detail.session_id}
          carId={detail.car_id}
          onSaved={() => setRefreshKey((k) => k + 1)}
        />
      </p>

      <div className="stat-tile-row">
        <StatTile label="Fastest lap" value={summary.fastest_lap} />
        <StatTile
          label="Consistency"
          value={formatStdev(summary.consistency_stdev_ms)}
          sublabel="stdev across valid laps"
        />
        <StatTile label="Valid laps" value={`${summary.valid_lap_count} / ${detail.laps.length}`} />
        {summary.optimal_lap && (
          <StatTile label="Optimal lap" value={summary.optimal_lap} sublabel="sum of best segments" />
        )}
        {summary.gap_to_optimal_ms !== null && (
          <StatTile
            label="Left on table"
            value={formatGap(summary.gap_to_optimal_ms)}
            sublabel="fastest lap vs. optimal"
          />
        )}
      </div>

      <h3>Track</h3>
      <TrackPanel trackId={detail.track_id} />

      <h3>Corner speeds vs. prior session at this track</h3>
      <CornerDeltaTable deltas={summary.corner_deltas} />

      <h3>Laps</h3>
      <table className="data-table">
        <thead>
          <tr>
            <th>Lap</th>
            <th>Time</th>
            <th>Flags</th>
          </tr>
        </thead>
        <tbody>
          {detail.laps.map((lap) => (
            <tr key={lap.lap_number} className={lap.is_valid ? undefined : "muted"}>
              <td className="tabular">{lap.lap_number}</td>
              <td className="tabular">{lap.lap_time}</td>
              <td>
                {!lap.is_valid && "invalid "}
                {lap.is_out_lap && "out-lap "}
                {lap.is_in_lap && "in-lap"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
