import type { EventSessionRow } from "./api/client";

// Any value that doesn't exist renders an em dash, never a zero - a
// missing optimal lap is not a 0:00.000.
export const EMPTY = "—";

export function formatDateRange(start: string, end: string | null): string {
  return end === null || end === start ? start : `${start} – ${end}`;
}

export function formatDuration(ms: number): string {
  const totalMinutes = Math.round(ms / 60000);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
}

// Second-deltas read as magnitudes at one decimal ("0.9s"), not as the
// m:ss.mmm lap format.
export function formatSeconds(ms: number): string {
  return `${(ms / 1000).toFixed(1)}s`;
}

export function formatSignedSeconds(ms: number): string {
  const seconds = ms / 1000;
  // Minus sign, not hyphen - it lines up with the tabular figures.
  return seconds < 0 ? `−${Math.abs(seconds).toFixed(1)}s` : `+${seconds.toFixed(1)}s`;
}

// "5:40p" - the compact timing-screen form, not "5:40 PM".
export function formatStartTime(startTime: string | null): string {
  if (startTime === null) return EMPTY;
  const date = new Date(startTime.replace(" ", "T"));
  if (Number.isNaN(date.getTime())) return EMPTY;
  const hours = date.getHours();
  const minutes = date.getMinutes().toString().padStart(2, "0");
  const hour12 = hours % 12 === 0 ? 12 : hours % 12;
  return `${hour12}:${minutes}${hours < 12 ? "a" : "p"}`;
}

// The slowest session sits at the floor rather than at zero - a
// zero-width bar reads as missing data instead of as a slow session.
export const MIN_BAR_PCT = 6;

// Fastest session in the event fills the bar completely - a quick
// visual arc of how the day's pace moved.
export function progressPct(
  bestLapMs: number | null,
  sessions: Pick<EventSessionRow, "best_lap_ms">[],
): number {
  if (bestLapMs === null) return 0;
  const times = sessions.map((s) => s.best_lap_ms).filter((t): t is number => t !== null);
  if (times.length === 0) return 0;
  const fastest = Math.min(...times);
  const slowest = Math.max(...times);
  if (fastest === slowest) return 100;
  const scaled = (slowest - bestLapMs) / (slowest - fastest);
  return Math.round(MIN_BAR_PCT + scaled * (100 - MIN_BAR_PCT));
}
