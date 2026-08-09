import { InteractionRequiredAuthError } from "@azure/msal-browser";
import { apiRequest } from "../authConfig";
import { msalInstance } from "../msalInstance";

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
  car: string | null;
  optimal_lap_ms: number | null;
  optimal_lap: string | null;
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
  car_id: number | null;
  laps: Lap[];
  corner_coverage: string[];
}

export interface CornerDelta {
  corner_code: string;
  // Curated per track and optional - null falls back to the bare code.
  corner_name: string | null;
  // Null when the corner only appears in the other lap of the pair -
  // both sides are built from a union of the two laps' corner codes.
  min_speed_mph: number | null;
  prior_min_speed_mph: number | null;
  delta_mph: number | null;
}

export interface SessionSummary extends SessionListItem {
  track_id: number;
  fastest_lap_ms: number;
  fastest_lap: string;
  valid_lap_count: number;
  consistency_stdev_ms: number;
  gap_to_optimal_ms: number | null;
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

export interface Track {
  track_id: number;
  track_name: string;
  configuration: string | null;
  length_miles: number | null;
  corner_count: number;
  personal_best: {
    lap_time_ms: number;
    lap_time: string;
    session_id: number;
    session_date: string;
  } | null;
}

export interface Consumable {
  consumable_id: number;
  item_name: string;
  install_date: string;
  install_session_id: number | null;
  service_life_sessions: number | null;
  service_life_months: number | null;
  notes: string | null;
  car_id: number | null;
  car: string | null;
  sessions_since_install: number;
  months_since_install: number;
  remaining_pct: number | null;
  overdue: boolean;
}

export interface Organization {
  organization_id: number;
  org_code: string;
  org_name: string;
}

export type EventPhase = "in_progress" | "upcoming" | "past";

export interface EventListItem {
  event_id: number;
  event_name: string;
  track_id: number;
  track_name: string;
  organization_id: number;
  org_code: string;
  start_date: string;
  end_date: string | null;
  session_count: number;
  // Computed server-side against the track's local date so the MCP
  // tools and the dashboard agree on what "upcoming" means; rows
  // arrive already in render order.
  phase: EventPhase;
}

export interface NewEvent {
  track_id: number;
  organization_id: number;
  event_name: string;
  start_date: string;
  end_date: string | null;
}

export interface EventSessionRow {
  session_id: number;
  session_number: number;
  start_time: string | null;
  best_lap_ms: number | null;
  best_lap: string | null;
  avg_valid_lap_ms: number | null;
  avg_valid_lap: string | null;
  optimal_lap_ms: number | null;
  optimal_lap: string | null;
  air_temp_f: number | null;
}

export interface EventWeather {
  temp_min_f: number | null;
  temp_max_f: number | null;
  conditions: string[];
}

export interface EventSummary {
  event_id: number;
  event_name: string;
  track_id: number;
  track_name: string;
  configuration: string | null;
  org_code: string;
  run_group: string | null;
  start_date: string;
  end_date: string | null;
  session_count: number;
  total_laps: number;
  valid_lap_count: number;
  total_track_time_ms: number | null;
  best_lap_ms: number | null;
  best_lap: string | null;
  best_lap_session_id: number | null;
  best_lap_session_number: number | null;
  best_lap_number: number | null;
  optimal_lap_ms: number | null;
  optimal_lap: string | null;
  left_on_table_ms: number | null;
  progression_ms: number | null;
  corner_deltas: CornerDelta[];
  weather: EventWeather | null;
  sessions: EventSessionRow[];
}

export interface Car {
  car_id: number;
  display_name: string;
  make: string | null;
  model: string | null;
  year: number | null;
  notes: string | null;
}

export interface NewCar {
  display_name: string;
  make: string | null;
  model: string | null;
  year: number | null;
  notes: string | null;
}

interface ApiError {
  error: string;
}

// Local dev proxies /api to the Functions host (vite.config.ts); the
// production build talks to the Function App directly since the Static
// Web App is Free tier (no same-origin linked backend).
const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

// Every read route requires a bearer token (see ingest/api_auth.py). A
// signed-out caller just gets null here and the API 401s - client.ts
// doesn't need its own "not signed in" error path.
async function getAccessToken(): Promise<string | null> {
  const account = msalInstance.getActiveAccount();
  if (!account) return null;

  try {
    const result = await msalInstance.acquireTokenSilent({ ...apiRequest, account });
    return result.accessToken;
  } catch (err) {
    if (err instanceof InteractionRequiredAuthError) {
      await msalInstance.acquireTokenRedirect(apiRequest);
    }
    return null;
  }
}

async function authHeaders(): Promise<HeadersInit> {
  const token = await getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { headers: await authHeaders() });
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as ApiError | null;
    throw new Error(body?.error ?? `Request to ${path} failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

async function postJson<T>(path: string, payload: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { ...(await authHeaders()), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as ApiError | null;
    throw new Error(body?.error ?? `Request to ${path} failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

async function patchJson<T>(path: string, payload: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "PATCH",
    headers: { ...(await authHeaders()), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
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

export function listTracks(): Promise<Track[]> {
  return getJson("/tracks");
}

export function getConsumables(): Promise<Consumable[]> {
  return getJson("/consumables");
}

export interface ConsumableReplacement {
  install_date?: string;
  install_session_id?: number | null;
  notes?: string | null;
}

export function replaceConsumable(
  consumableId: number,
  replacement: ConsumableReplacement,
): Promise<{ consumable_id: number }> {
  return postJson(`/consumables/${consumableId}/replace`, replacement);
}

export function listOrganizations(): Promise<Organization[]> {
  return getJson("/organizations");
}

export function listEvents(): Promise<EventListItem[]> {
  return getJson("/events");
}

export function getEventSummary(eventId: number): Promise<EventSummary> {
  return getJson(`/events/${eventId}/summary`);
}

export function createEvent(event: NewEvent): Promise<{ event_id: number }> {
  return postJson("/events", event);
}

export function listCars(): Promise<Car[]> {
  return getJson("/cars");
}

export function createCar(car: NewCar): Promise<{ car_id: number }> {
  return postJson("/cars", car);
}

export function updateSessionCar(
  sessionId: number,
  carId: number | null,
): Promise<{ session_id: number; car_id: number | null }> {
  return patchJson(`/sessions/${sessionId}`, { car_id: carId });
}

// <img src> can't send an Authorization header, so the satellite image
// is fetched with the bearer token and exposed as an object URL instead
// of a plain route URL.
export async function fetchTrackSatelliteBlob(trackId: number): Promise<string> {
  const res = await fetch(`${API_BASE}/tracks/${trackId}/satellite`, {
    headers: await authHeaders(),
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as ApiError | null;
    throw new Error(body?.error ?? `Request to /tracks/${trackId}/satellite failed (${res.status})`);
  }
  return URL.createObjectURL(await res.blob());
}
