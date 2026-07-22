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
  fastest_lap_ms: number;
  fastest_lap: string;
  valid_lap_count: number;
  consistency_stdev_ms: number;
  prior_session_id: number | null;
  corner_deltas: CornerDelta[];
}

interface ApiError {
  error: string;
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`/api${path}`);
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
