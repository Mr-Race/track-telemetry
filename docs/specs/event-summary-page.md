# Spec: Event Summary Page (`/events/:eventId`)

Status: approved by AC 2026-07-25 (via interactive mockup in Claude
chat). Layout section rewritten 2026-08-03 against the approved
mockup screenshots, because the first build drifted badly from it.
Replaces the placeholder EventSummaryPage.tsx. Scheduled: v1.x —
the optimal-lap tiles depend on v1.0's segment-times + optimal-lap
work, which landed 2026-08-02, so this is unblocked.

## Purpose
The event page tells the story of a track DAY. Session detail tells
the story of one run; this page answers "how did the day go" —
progression across sessions, what the day was worth, what improved.

## Visual intent (read this before building)
This is a **timing screen**, not a business dashboard. The mockup's
character comes from four things, and losing any one of them is why
a build reads as "awful" even when every number is correct:

1. **Dark, near-black page with slightly lighter panels.** Tiles and
   tables sit on raised panels, one step lighter than the page
   background, with generous internal padding and a soft rounded
   corner (~12px). No borders doing the work that background
   contrast should do; no white cards on grey.
2. **Two type families, used strictly.** A condensed display face
   for the event title and the big tile numbers; a monospace face
   for every table cell, label, and small stat. Labels are
   uppercase, small, wide-tracked, and muted. The mockup used
   Barlow Condensed + IBM Plex Mono — match the existing dashboard
   fonts if they conflict, but keep the display/mono split.
3. **Numbers are the loudest thing on the page.** Tile values are
   very large (roughly 3x the label size) and sit directly under a
   small muted label, with a smaller muted caption underneath giving
   provenance ("session 2, lap 6", "best segments, any session").
   Label, value, caption — that three-line stack is the tile.
4. **Colour is semantic and sparing.** Purple for fastest/optimal
   values only. Green for improvement, red for regression. Every
   other number is plain white or muted grey. No accent colours for
   decoration.

## Layout (top to bottom, phone-first single column)

### 1. Header
- **Eyebrow** — `EVENT · <ORG> · <RUN GROUP>`, uppercase, mono,
  small, muted, dot-separated (e.g. `EVENT · SCCA-HPDE · NOVICE`).
- **Title** — event name in the large condensed display face, the
  biggest text on the page (e.g. "TNIA — Track Night in America").
- **Subtitle** — `<track> · <configuration> · <date>`, one line,
  muted (e.g. "NJMP Lightning · Full Course · Jul 22, 2026").
- **Badges** — small pill chips below the subtitle: session count
  and total laps (e.g. `2 SESSIONS` `19 LAPS`). Uppercase mono,
  light pill on dark. Track time is NOT a badge — it's a hero tile
  (see below).

### 2. Hero stats — SIX tiles in a 2-column grid (3 rows on phone)
Section label `HERO STATS` above the grid, uppercase mono muted.
Reading order is left-to-right, top-to-bottom:

| | left | right |
|---|---|---|
| row 1 | **Event best** | **Event optimal** |
| row 2 | **Left on table** | **Progression** |
| row 3 | **Laps** | **Track time** |

- **Event best** — fastest valid lap of the event, formatted
  m:ss.mmm, in **purple**. Caption: which session and lap
  ("session 2, lap 6").
- **Event optimal** — sum of the best segment times across ALL
  sessions of the event, not per-session. Also **purple**. Caption:
  "best segments, any session".
- **Left on table** — event best minus event optimal, as seconds
  with one decimal and a trailing `s` ("0.9s"). Plain white.
  Caption: "best vs optimal".
- **Progression** — first session's best minus last session's best,
  signed, one decimal ("−1.1s"). **Green when negative** (the day
  got faster), red when positive. Caption: "S1 best → S2 best".
- **Laps** — total lap count, plain white. Caption: valid count
  ("15 valid").
- **Track time** — total across sessions, rounded to minutes
  ("41m"). Caption: "across N sessions".

Any tile whose data doesn't exist renders an em dash, never a zero.

### 3. Sessions table
Section label `SESSIONS`. Columns, left to right:
`SESSION · BEST · AVG · OPTIMAL · WX`

- **SESSION** cell is `S<n> · <start time>` (e.g. `S1 · 5:40p`),
  left-aligned. Every other column is **right-aligned**, mono,
  tabular numerals.
- The event's best lap is rendered in **purple** wherever it appears
  in the BEST column; all other values plain.
- **WX** is just the air temperature (e.g. `88°F`), not a summary
  string — the full conditions live in the weather strip.
- **Under each row sits a thin horizontal progress bar** (~3px,
  full row width, rounded) scaled to that session's best lap
  relative to the event's range. This is the visual arc of the day
  and is the single most distinctive element of the mockup — do not
  drop it. Bar fill uses a muted-to-green gradient; the fastest
  session's bar reaches full width.
- Rows are tap-through to the existing session detail page.

### 4. Corner story of the day
Section label `CORNER STORY`. Approved variant is **A · day arc**:
what improved from the first to the last session of the day.

Columns: `CORNER · S1 MIN · S2 MIN · Δ`
- Corner column uses the name where one is set
  (`T9 Lightbulb`, `T10 Kink`), otherwise the bare number (`T2`).
- Min speeds in mph, one decimal, right-aligned mono.
- Δ column is signed and coloured: **green for positive** (faster
  through the corner), **red for negative**.
- **Sorted in lap order** (T1, T2, … T10) using the track's
  `corners.sort_order`, so the table reads as a walk around the
  circuit in the order it's driven. (Changed 2026-08-09 per AC; was
  |Δ| descending, which led with the biggest movers but scrambled the
  lap. Sort on `sort_order`, never on the code string — codes are
  text, so `10` sorts before `2` and `3A` lands nowhere sensible.)
- One-line muted explainer under the section label: "What improved
  from first to last session of the day — the arc of the event."
- Single-session events: hide this section entirely.

### 5. Weather strip
Small day-conditions summary (temp range across sessions,
conditions). Only render once weather data exists for the event's
sessions. Muted, single line, no panel of its own.

### Explicitly EXCLUDED (decided at mockup review)
Satellite thumbnail (pretty, not analytical — lives on track
pages), consumables impact (lives on the consumables page), and
corner-vs-all-time-PB comparison (session summary already covers
vs-prior-session; a vs-PB view can be a future session-detail
enhancement, not an event-page section).

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
  per-session optimal query (`queries.optimal_lap_ms`).
- New: `phase` (in_progress | upcoming | past) computed per event
  row in `GET /api/events`, per the temporal-split section above.
- One new endpoint: `GET /api/events/{id}/summary` returning header
  data, the six hero stats, per-session rows, and the first-vs-last
  corner deltas in one payload.

## Design language
Timing-screen conventions, harmonized with the existing dashboard
styles (do not fork the design system):
- Purple = fastest/optimal (timing-tower convention)
- Green = improvement / personal best; red = slower
- Tabular/monospace numerals for all times and speeds
- Times formatted m:ss.mmm as elsewhere; speeds one decimal;
  second-deltas one decimal with an explicit sign

Reference mockup: built in chat 2026-07-25, re-reviewed 2026-08-03
(Barlow Condensed display + IBM Plex Mono data faces, asphalt/panel
dark palette). Treat the **structure, hierarchy, alignment, and
colour semantics above as binding** — that's what the first build
missed. Exact fonts and pixel values are directional; existing
dashboard typography wins where they conflict.
