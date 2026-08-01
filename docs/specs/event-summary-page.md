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

## Data requirements
- Existing: sessions of event with laps (best/avg valid), corner
  metrics per session, event/org/run-group/track joins.
- New: event-level optimal (min segment time per segment across all
  sessions of the event, summed) — natural extension of the v1.0
  per-session optimal query.
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
