import { useCallback } from "react";
import { Link, useParams } from "react-router-dom";
import { listTracks } from "../api/client";
import { useFetch } from "../api/useFetch";
import { TrackPanel } from "../components/TrackPanel";

export function TrackViewPage() {
  const { trackId } = useParams<{ trackId: string }>();
  const id = Number(trackId);

  const load = useCallback(() => listTracks(), []);
  const state = useFetch(load, [id]);

  if (state.status === "loading") return <p className="muted">Loading track…</p>;
  if (state.status === "error") return <p className="delta-bad">Error: {state.message}</p>;

  const track = state.data.find((t) => t.track_id === id);
  if (!track) return <p className="delta-bad">No track with track_id={id}</p>;

  return (
    <div>
      <p>
        <Link to="/tracks">&larr; All tracks</Link>
      </p>
      <h2>{track.track_name}</h2>
      <p className="muted">
        {track.configuration && `${track.configuration} · `}
        {track.length_miles !== null && `${track.length_miles} mi · `}
        {track.corner_count} corners
      </p>

      <TrackPanel trackId={track.track_id} />
    </div>
  );
}
