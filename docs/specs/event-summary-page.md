# Spec: Event Summary Page (`/events/:eventId`)

Status: approved by AC 2026-07-25 (via interactive mockup in Claude
chat). Replaces the placeholder EventSummaryPage.tsx. Scheduled:
v1.x (but the optimal-lap tiles depend on v1.0's segment-times +
optimal-lap work, so build after those land).

## Purpose
The event page tells the story of a track DAY. Session detail tells
the story of one run; this page answers "how did the day go" —
progression across sessions, what the day was worth, what improved.

## Layout (top to bottom, phone-first single column)

1. **Header** — event name, org + run group eyebrow, track +
   configuration, date(s). Badges: session count, total laps,
   total track time. (Laps/track time live HERE, not as hero cards.)

2. **Hero stat row (4 tiles, 2x2 on phone):**
   - **Event best lap** — fastest valid lap of the event, with
     which session/lap it came from.
   - **Event optimal lap** — theoretical best from the best
     segments across ALL sessions of the event (not per-session).
     Depends on segment_times (v1.0).
   - **Left on table** — event best minus event optimal.
   - **Progression** — delta between first session's best and last
     session's best (negative/green = day got faster).

3. **Sessions table** — one row per session, tap-through to the
   existing session detail page. Columns: session (number + start
   time), best lap, avg valid lap, session optimal, weather temp.
   A thin progress bar under each row scaled to best lap (visual
   arc of the day).

4. **Corner story of the day (Option A — day arc)** — table of
   corner min speeds: first session vs last session of the event,
   with delta column (green positive / red negative). Sorted by
   |delta| descending so the biggest changes lead. Uses corner
   names where set (Lightbulb, Kink). Single-session events: hide
   this section entirely (no arc to tell).

5. **Weather strip** — small day-conditions summary (temp range
   across sessions, conditions). Only render once weather data
   exists for the event's sessions (v1.0 auto-fetch + backfill).

Explicitly EXCLUDED (decided): satellite thumbnail (lives on track
pages), consumables impact (lives on consumables page), corner-vs-
all-time-PB comparison (session summary already covers vs-prior-
session; a vs-PB view can be a future session-detail enhancement,
not an event-page section).

## Events list: temporal split (added 2026-08-02, per AC)
Applies to the events LIST (`/events`) and anywhere events are
enumerated — distinct from the single-event summary above.

Split events into three groups, ordered top to bottom:

1. **In progress** — today falls within `start_date`..`end_date`
   inclusive. Expect zero or one; a multi-day weekend keeps the
   event "in progress" across both days.
2. **Upcoming** — `start_date` is in the future. Sorted ascending
   (soonest first) — this is a planning view, so the nearest event
   leads.
3. **Past** — `end_date` is before today. Sorted descending (most
   recent first) — this is a review view, so the last track day
   leads.

Notes:
- Derive the split from the dates already on `dbo.events`; no new
  columns needed. `end_date` may be null for single-day events —
  fall back to `start_date` for both bounds.
- Compute the grouping server-side in the `/api/events` response
  (a `phase` field per row) rather than in the client, so the MCP
  tools and the dashboard agree on what "upcoming" means.
- Use the track's local date, not UTC, when deciding which group an
  event lands in — a UTC comparison flips events a day early for
  US East tracks.
- Empty groups collapse rather than render an empty header.
- An event with no sessions yet is still valid in Upcoming or In
  progress — the aggregate columns (best lap, session count) render
  as em dashes, not zeros.

## Data requirements
- Existing: sessions of event with laps (best/avg valid), corner
  metrics per session, event/org/run-group/track joins.
- New: event-level optimal (min segment time per segment across all
  sessions of the event, summed) — natural extension of the v1.0
  per-session optimal query.
- New: `phase` (in_progress | upcoming | past) computed per event
  row in `GET /api/events`, per the temporal-split section above.
- Likely one new endpoint: GET /api/events/{id}/summary returning
  header data, hero stats, per-session rows, and the first-vs-last
  corner deltas in one payload.

## Design language
Timing-screen conventions, harmonized with the existing dashboard
styles (do not fork the design system):
- Purple = fastest/optimal (timing-tower convention)
- Green = improvement / personal best; red = slower
- Tabular/monospace numerals for all times and speeds
- Times formatted m:ss.mmm as elsewhere
Reference mockup: built in chat 2026-07-25 (Barlow Condensed
display + IBM Plex Mono data faces, asphalt/panel dark palette) —
treat as directional, not pixel-binding; existing dashboard
typography wins where they conflict.
