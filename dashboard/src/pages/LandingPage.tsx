import { Link } from "react-router-dom";
import { listSessions, listTracks } from "../api/client";
import { useFetch } from "../api/useFetch";
import { StatTile } from "../components/StatTile";
import { IS_DEMO } from "../demoMode";

function usePreviewStats() {
  const sessions = useFetch(listSessions, []);
  const tracks = useFetch(listTracks, []);

  if (sessions.status !== "ready" || tracks.status !== "ready") return null;

  const bestLapMs = sessions.data.reduce<number | null>((best, s) => {
    if (s.best_lap_ms === null) return best;
    return best === null || s.best_lap_ms < best ? s.best_lap_ms : best;
  }, null);
  const bestLap = sessions.data.find((s) => s.best_lap_ms === bestLapMs);

  return {
    sessionCount: sessions.data.length,
    trackCount: tracks.data.length,
    bestLap: bestLap?.best_lap ?? "—",
    bestLapTrack: bestLap?.track_name,
  };
}

export function LandingPage() {
  const stats = usePreviewStats();

  return (
    <div className="landing">
      {/* Say it once, plainly, above the fold: a visitor should never
          wonder whether these lap times belong to a real person. */}
      {IS_DEMO && (
        <p className="demo-banner">
          <strong>Demo.</strong> Every session, lap and consumable here is
          fictional, generated to show how the platform behaves. The tracks
          are real. The driving is not.{" "}
          <a href="https://www.mr-race.com">See the real platform</a>.
        </p>
      )}
      <section className="landing-hero">
        <h2>Track days, actually measured.</h2>
        <p>
          Track Telemetry ingests lap and corner-speed data straight from
          RaceChrono, so every session builds toward corner-by-corner
          personal bests instead of living in a stack of CSV exports.
          Satellite track views, friends&apos; benchmark laps, and a
          consumables tracker for tires and pads round it out.
        </p>
        <Link className="cta-button" to="/sessions">
          View the dashboard
        </Link>
        {/* On the real site this points a visitor at the demo. On the
            demo it would point at itself, so it is hidden there and
            replaced by the banner below. */}
        {!IS_DEMO && (
          <p className="landing-demo-link">
            No account?{" "}
            <a href="https://demo.mr-race.com">
              Explore the demo with sample data
            </a>{" "}
            &mdash; no sign-in needed.
          </p>
        )}
      </section>

      {stats && (
        <div className="stat-tile-row">
          <StatTile label="Sessions logged" value={String(stats.sessionCount)} />
          <StatTile label="Tracks tracked" value={String(stats.trackCount)} />
          <StatTile
            label="Best lap"
            value={stats.bestLap}
            sublabel={stats.bestLapTrack}
          />
        </div>
      )}
    </div>
  );
}
