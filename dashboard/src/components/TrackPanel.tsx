import { useCallback, useEffect, useState } from "react";
import { fetchTrackSatelliteBlob, getTrackBenchmarks } from "../api/client";
import { useFetch } from "../api/useFetch";

function useSatelliteImageUrl(trackId: number): string | null {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    setUrl(null);
    fetchTrackSatelliteBlob(trackId)
      .then((blobUrl) => {
        if (cancelled) {
          URL.revokeObjectURL(blobUrl);
          return;
        }
        objectUrl = blobUrl;
        setUrl(blobUrl);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [trackId]);

  return url;
}

export function TrackPanel({ trackId }: { trackId: number }) {
  const load = useCallback(() => getTrackBenchmarks(trackId), [trackId]);
  const state = useFetch(load, [trackId]);
  const satelliteUrl = useSatelliteImageUrl(trackId);

  return (
    <div className="track-panel">
      {satelliteUrl && (
        <img
          className="satellite-image"
          src={satelliteUrl}
          alt="Satellite view of the track"
          loading="lazy"
        />
      )}

      {state.status === "loading" && <p className="muted">Loading leaderboard…</p>}
      {state.status === "error" && <p className="delta-bad">Error: {state.message}</p>}
      {state.status === "ready" && (() => {
        const { personal_best, benchmarks } = state.data;
        const rows = [
          ...(personal_best
            ? [{
                key: "me",
                driver_name: "You",
                lap_time_ms: personal_best.lap_time_ms,
                lap_time: personal_best.lap_time,
                set_date: personal_best.session_date,
                notes: null as string | null,
                mine: true,
              }]
            : []),
          ...benchmarks.map((b) => ({
            key: `b${b.benchmark_id}`,
            driver_name: b.driver_name,
            lap_time_ms: b.lap_time_ms,
            lap_time: b.lap_time,
            set_date: b.set_date,
            notes: b.notes,
            mine: false,
          })),
        ].sort((a, b) => a.lap_time_ms - b.lap_time_ms);

        if (rows.length === 0) {
          return <p className="muted">No lap times recorded at this track yet.</p>;
        }

        return (
          <table className="data-table">
            <thead>
              <tr>
                <th>Driver</th>
                <th>Lap time</th>
                <th>Date</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.key} className={r.mine ? "mine" : undefined}>
                  <td>{r.driver_name}</td>
                  <td className="tabular">{r.lap_time}</td>
                  <td className="tabular">{r.set_date ?? "—"}</td>
                  <td>{r.notes ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        );
      })()}
    </div>
  );
}
