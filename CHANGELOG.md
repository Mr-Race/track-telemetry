# Changelog

Notable changes per release. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning is
the semver-style scheme described in `docs/BACKLOG.md`:

- **0.x** — pre-stable; schemas change freely, nothing is promised
- **1.0** — core loop finished, nothing known-broken in prod, all
  endpoints secured, docs baseline exists, both review gates passed
- **1.x** — additive and backward-compatible
- **2.0** — reserved for breaking/identity-level change

`docs/BACKLOG.md`'s `## Done` log stays the detailed record, including
what broke and why. This file is the summary a reader wants first.

## [Unreleased]

Nothing yet.

## [1.0.0] — unreleased

The core loop is complete: capture, enrichment, a secured dashboard, and
conversational analysis over real session data — with the pipeline
proven end to end on a real export from the reconfigured logger.

### Added
- **Pedal position is calibrated.** Raw OBD values carry a sensor
  voltage baseline, so the pedal at rest read 18.82% and at the stop
  94.90% — a corner taken with the foot completely off reported 18.8%
  throttle. Calibration is stored per `(car, channel)` and applied on
  read, never at ingest, so a future sensor change cannot make history
  double-correct
- Sessions record which OBD channel produced their pedal values, so the
  archive is no longer silently mixed across the 2026-08-10 logger change
- **Documentation baseline** — architecture, schema and data dictionary,
  API reference, runbook and a decision log, published at
  https://mr-race.github.io/track-telemetry/. The schema page is
  generated from the live database rather than transcribed, and the
  whole set builds with `--strict` so a broken link fails CI
- A release gate and release script: the gate checks against production
  that a real session on the new channel parsed, produced usable laps
  and corners, and normalised correctly
- **The dashboard is at https://www.mr-race.com**, with an auto-renewing
  managed certificate; the apex redirects to it
- A DNS sweep for dangling CNAMEs, which are a subdomain-takeover risk
  and are created by deleting cloud resources rather than by editing DNS

### Changed
- Channel sources are resolved by device rather than by logging rate, so
  changing the GPS rate in RaceChrono no longer fails every upload with
  `Column not found: latitude`. The source qualifier is still required —
  `speed` appears three times in a real export, so matching by name
  alone would bind lap and corner metrics to OBD wheel speed
- The first upload after the database auto-pauses survives the resume.
  The login timeout was the same 60s as the top of the documented resume
  window, with no retry; measured at 59s against a genuinely paused
  database

### Fixed
- **Every API endpoint 500'd under concurrent requests.** One SQL
  connection was shared across the whole process, but pytds connections
  are not thread-safe and allow a single active cursor, so parallel
  requests corrupted the connection. Connections are now per-thread
- A dry run no longer archives a raw blob for a session it never loads,
  which is what makes it usable as a pre-event rehearsal
- A lap-less export now explains itself: RaceChrono's "Data logging"
  mode does no lap timing, which read as a parser bug

## [0.9.0] — 2026-08-12

First tagged release. The platform is feature-complete for 1.0 bar two
items, and this exists to prove the release process works before it is
needed for 1.0.

### Added
- **MCP server authenticated with OAuth 2.1 via Entra**, working as a
  Claude connector at `https://mcp.mr-race.com/mcp` — conversational
  analysis over real session data, which is the product's premise
- Event summary page: six hero stats, per-session pace bars, corner
  story, weather strip
- Events list split into in progress / upcoming / past, computed
  server-side against the track's local date
- Content-hash idempotency on ingest — re-uploading a CSV refreshes the
  session it already created instead of duplicating it
- Migration ledger (`dbo.schema_migrations`) plus `sql/migrate.py`, with
  checksum drift detection
- Application Insights on the ingest path; parse diagnostics in the
  ingest response so a missing OBD dongle or truncated file is visible
  at upload time
- Test suites where there were none: 123 Python tests, 23 dashboard
  tests, both gating in CI
- CI on every push — pytest, vitest, lint, typecheck, build
- `SECURITY.md`, issue and PR templates, `docs/WAY-OF-WORKING.md`

### Changed
- Parser accepts either `accelerator_pos` or `throttle_pos`, preferring
  true pedal position
- Event sessions order chronologically rather than by `session_number`
- Personal bests are scoped to a driver
- One pooled SQL connection and credential per process, replacing one
  per request — a page load now pays at most one serverless resume
- Dashboard is responsive; the page no longer scrolls sideways at any
  phone width
- TypeScript `strict` enabled

### Fixed
- Sign-in appeared to work while every API call returned 401: a
  reloaded MSAL session had cached accounts but no *active* one
- Session `start_time` stored as raw UTC in a naive column, displaying
  every session 4–5 hours late
- An instructor-driven session counted as a personal best
- Median lap calculation used the upper-middle value for an even lap
  count
- Corner metrics could merge two passes through the same zone, and did
  not sort samples chronologically before reading entry/exit speeds

### Security
- Internal exception text no longer returned to API clients
- Removed per-request token metadata from MCP server logs
- SQL placeholder conversion is parse-aware instead of a blind
  string replace

### Data
- Historical archive fully reconciled: 15 sessions, 127 laps, 1520
  segment times, every session with an optimal lap and a content hash.
  Four sessions were recovered from the Blob archive after their local
  copies were gone.

[Unreleased]: https://github.com/Mr-Race/track-telemetry/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Mr-Race/track-telemetry/releases/tag/v1.0.0
[0.9.0]: https://github.com/Mr-Race/track-telemetry/releases/tag/v0.9.0
