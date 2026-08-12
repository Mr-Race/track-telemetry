import { describe, expect, it } from "vitest";

import {
  EMPTY, formatDateRange, formatDuration, formatSeconds,
  formatSignedSeconds, formatStartTime, progressPct,
} from "./format";

describe("formatStartTime", () => {
  it("uses the compact timing-screen form", () => {
    // "5:40p", not "5:40 PM" - the sessions table is a timing screen.
    expect(formatStartTime("2026-07-22 17:40:00")).toBe("5:40p");
    expect(formatStartTime("2026-07-22 09:51:14")).toBe("9:51a");
  });

  it("renders midnight and noon as 12, not 0", () => {
    expect(formatStartTime("2026-07-22 00:05:00")).toBe("12:05a");
    expect(formatStartTime("2026-07-22 12:05:00")).toBe("12:05p");
  });

  it("pads the minutes", () => {
    expect(formatStartTime("2026-07-22 17:05:00")).toBe("5:05p");
  });

  it("is an em dash when there is no time, never a fake one", () => {
    expect(formatStartTime(null)).toBe(EMPTY);
    expect(formatStartTime("not a date")).toBe(EMPTY);
  });
});

describe("formatSignedSeconds", () => {
  it("uses a real minus sign so figures line up", () => {
    // U+2212, not a hyphen - it shares the width of the tabular digits.
    expect(formatSignedSeconds(-1841)).toBe("−1.8s");
    expect(formatSignedSeconds(-1841).charCodeAt(0)).toBe(0x2212);
  });

  it("keeps an explicit plus for a slower day", () => {
    expect(formatSignedSeconds(1841)).toBe("+1.8s");
  });

  it("treats zero as non-negative", () => {
    expect(formatSignedSeconds(0)).toBe("+0.0s");
  });
});

describe("formatSeconds and formatDuration", () => {
  it("reads deltas as one-decimal magnitudes, not lap times", () => {
    expect(formatSeconds(2927)).toBe("2.9s");
  });

  it("rounds track time to the nearest minute", () => {
    // 3,150,259 ms is 52.5 minutes - rounds up, and this is the real
    // TNIA total that renders on the event page.
    expect(formatDuration(3150259)).toBe("53m");
    expect(formatDuration(52 * 60_000 + 20_000)).toBe("52m");
  });

  it("adds hours once past sixty minutes", () => {
    expect(formatDuration(3_600_000 + 300_000)).toBe("1h 5m");
  });
});

describe("formatDateRange", () => {
  it("collapses a single-day event to one date", () => {
    expect(formatDateRange("2026-07-22", null)).toBe("2026-07-22");
    expect(formatDateRange("2026-07-22", "2026-07-22")).toBe("2026-07-22");
  });

  it("shows both ends of a weekend", () => {
    expect(formatDateRange("2026-06-13", "2026-06-14")).toBe("2026-06-13 – 2026-06-14");
  });
});

describe("progressPct", () => {
  const sessions = (...ms: (number | null)[]) => ms.map((m) => ({ best_lap_ms: m }));

  it("gives the fastest session the full bar", () => {
    expect(progressPct(84975, sessions(86816, 85331, 84975))).toBe(100);
  });

  it("floors the slowest session rather than showing nothing", () => {
    // A zero-width bar reads as missing data, not as a slow session.
    expect(progressPct(86816, sessions(86816, 85331, 84975))).toBe(6);
  });

  it("places a middle session between the two", () => {
    const pct = progressPct(85331, sessions(86816, 85331, 84975));
    expect(pct).toBeGreaterThan(6);
    expect(pct).toBeLessThan(100);
  });

  it("gives a lone session the full bar rather than dividing by zero", () => {
    expect(progressPct(84975, sessions(84975))).toBe(100);
  });

  it("is zero when the session has no valid lap", () => {
    expect(progressPct(null, sessions(86816, 84975))).toBe(0);
  });

  it("ignores sessions with no lap time when scaling", () => {
    expect(progressPct(84975, sessions(86816, null, 84975))).toBe(100);
  });

  it("is zero when nothing in the event has a lap time", () => {
    expect(progressPct(null, sessions(null, null))).toBe(0);
  });
});
