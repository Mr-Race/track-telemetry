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

Remaining before 1.0: `accelerator_pos` verification against a real
export (time-blocked on the next event), and the technical docs
baseline.

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

[Unreleased]: https://github.com/Mr-Race/track-telemetry/compare/v0.9.0...HEAD
[0.9.0]: https://github.com/Mr-Race/track-telemetry/releases/tag/v0.9.0
