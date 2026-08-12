import { Link } from "react-router-dom";
import { listTracks } from "../api/client";
import { useFetch } from "../api/useFetch";
import { Loading } from "../components/Loading";

export function TrackDirectoryPage() {
  const state = useFetch(listTracks, []);

  if (state.status === "loading") return <Loading what="tracks" />;
  if (state.status === "error") return <p className="delta-bad">Error: {state.message}</p>;

  const tracks = state.data;
  if (tracks.length === 0) return <p className="muted">No tracks recorded yet.</p>;

  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Track</th>
          <th>Configuration</th>
          <th>Length</th>
          <th>Corners</th>
          <th>Personal best</th>
        </tr>
      </thead>
      <tbody>
        {tracks.map((t) => (
          <tr key={t.track_id}>
            <td>
              <Link to={`/tracks/${t.track_id}`}>{t.track_name}</Link>
            </td>
            <td>{t.configuration ?? "—"}</td>
            <td className="tabular">{t.length_miles !== null ? `${t.length_miles} mi` : "—"}</td>
            <td className="tabular">{t.corner_count}</td>
            <td className="tabular">{t.personal_best?.lap_time ?? "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
