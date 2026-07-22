export interface SessionListItem {
  session_id: number;
  event_id: number;
  event_name: string;
  track_name: string;
  session_number: number;
  session_date: string;
  run_group: string | null;
  weather: string | null;
  air_temp_f: number | null;
  best_lap_ms: number | null;
  best_lap: string | null;
  avg_valid_lap_ms: number | null;
  avg_valid_lap: string | null;
}

export interface Lap {
  lap_number: number;
  lap_time_ms: number;
  lap_time: string;
  is_valid: boolean;
  is_out_lap: boolean;
  is_in_lap: boolean;
}

export interface SessionDetail extends SessionListItem {
  track_id: number;
  source_file: string | null;
  laps: Lap[];
  corner_coverage: string[];
}

export interface CornerDelta {
  corner_code: string;
  min_speed_mph: number;
  prior_min_speed_mph: number | null;
  delta_mph: number | null;
}

export interface SessionSummary extends SessionListItem {
  track_id: number;
  fastest_lap_ms: number;
  fastest_lap: string;
  valid_lap_count: number;
  consistency_stdev_ms: number;
  prior_session_id: number | null;
  corner_deltas: CornerDelta[];
}

export interface Benchmark {
  benchmark_id: number;
  driver_name: string;
  lap_time_ms: number;
  lap_time: string;
  set_date: string | null;
  notes: string | null;
}

export interface TrackBenchmarks {
  track_id: number;
  track_name: string;
  personal_best: {
    lap_time_ms: number;
    lap_time: string;
    session_id: number;
    session_date: string;
  } | null;
  benchmarks: Benchmark[];
}

export interface Consumable {
  consumable_id: number;
  item_name: string;
  install_date: string;
  install_session_id: number | null;
  service_life_sessions: number | null;
  service_life_months: number | null;
  notes: string | null;
  sessions_since_install: number;
  months_since_install: number;
  remaining_pct: number | null;
  overdue: boolean;
}

interface ApiError {
  error: string;
}

// Local dev proxies /api to the Functions host (vite.config.ts); the
// production build talks to the Function App directly since the Static
// Web App is Free tier (no same-origin linked backend).
const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as ApiError | null;
    throw new Error(body?.error ?? `Request to ${path} failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export function listSessions(): Promise<SessionListItem[]> {
  return getJson("/sessions");
}

export function getSessionDetail(sessionId: number): Promise<SessionDetail> {
  return getJson(`/sessions/${sessionId}`);
}

export function getSessionSummary(sessionId: number): Promise<SessionSummary> {
  return getJson(`/sessions/${sessionId}/summary`);
}

export function getTrackBenchmarks(trackId: number): Promise<TrackBenchmarks> {
  return getJson(`/tracks/${trackId}/benchmarks`);
}

export function getConsumables(): Promise<Consumable[]> {
  return getJson("/consumables");
}

export function trackSatelliteUrl(trackId: number): string {
  return `${API_BASE}/tracks/${trackId}/satellite`;
}
