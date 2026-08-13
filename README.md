# Track Telemetry Platform

Enterprise-grade telemetry pipeline for HPDE track data (RaceChrono ->
Azure SQL -> Claude via MCP -> React dashboard). Built as a portfolio
piece demonstrating cloud + AI architecture.

## Start here
- **[docs/WAY-OF-WORKING.md](docs/WAY-OF-WORKING.md)** — the practices
  this project holds itself to. Read first; every rule in it exists
  because something broke without it.
- **[docs/BACKLOG.md](docs/BACKLOG.md)** — the system of record:
  guiding principles, versioned scope, known gaps, and a dated Done log.
  If a decision only exists in a chat, it doesn't exist.
- **[SECURITY.md](SECURITY.md)** — this repo is public; security
  findings do **not** go in issues.
- **[sql/README.md](sql/README.md)** — how migrations are applied and
  recorded.
- **[CHANGELOG.md](CHANGELOG.md)** — what changed per release;
  **[docs/RELEASING.md](docs/RELEASING.md)** — how to cut one.
- **[docs/technical/](docs/technical/)** — architecture, schema and data
  dictionary, API reference, runbook, decision log. Published at
  <https://mr-race.github.io/track-telemetry/>.

## Architecture
RaceChrono CSV v3 -> iOS Shortcut (share sheet) -> HTTP Azure Function
(`func-track-telemetry-ingest`, parse/enrich)
-> Azure SQL (`free-sql-db-7848405`, source of truth) + Blob
(`racechronoraw`, raw archive)
-> MCP server (`mcp.mr-race.com`, Container Apps, managed identity,
read-only) + React dashboard (`www.mr-race.com`, Static Web Apps,
Entra ID auth)
-> Claude custom connector / browser

Power BI was dropped from the roadmap (2026-07-22, see
`docs/BACKLOG.md`) — React on Static Web Apps is the sole
visualization layer, to stay free-tier/no-license.

## Status
Approaching 1.0 — see `docs/BACKLOG.md` for versioned scope, known gaps
and a dated `## Done` log. Live pieces:
- [x] Azure SQL (free tier, Entra-only auth) + Blob provisioned
- [x] Schema: config-aware tracks, corner apex zones, run groups,
      organizations/events, drivers, cars, segment times
- [x] Parser: laps + corner metrics (incl. OBD pedal position/RPM),
      validated against real sessions
- [x] Ingestion Function (`POST /api/ingest`) + iOS Shortcut share-sheet
      upload, with content-hash idempotency
- [x] **MCP server at `https://mcp.mr-race.com/mcp`, authenticated with
      OAuth 2.1 + PKCE via Entra, working as a Claude connector** —
      conversational analysis of real session data
- [x] React dashboard: session list/detail, event summary, consumables,
      track directory + satellite view, benchmarks
- [x] Entra ID auth (MSAL, OAuth 2.1 + PKCE) — dashboard sign-in +
      bearer-token-protected API
- [x] Write-capable dashboard features: event management, car catalog
- [x] Engineering practices + information security reviews complete,
      all high-severity findings closed
- [x] CI on every push: pytest (175), vitest, lint, typecheck, build
- [x] Released and tagged: **v0.9.0**, version + commit visible in the
      dashboard footer (`CHANGELOG.md`, `docs/RELEASING.md`)
- [x] **Dashboard at `https://www.mr-race.com`** — custom domain, managed
      certificate, apex 301s to `www`
- [x] Documentation published at
      <https://mr-race.github.io/track-telemetry/> — architecture, schema,
      API, runbook, decision log, plus the business set
- [x] Pedal position calibrated per `(car, channel)` and normalised on
      read; each session records which OBD channel produced its values
- [ ] Remaining v1.0: `accelerator_pos` verified against a real export
      (time-blocked on the next event) — see `docs/BACKLOG.md`

## Repo layout
- `sql/` - numbered migrations, applied and recorded via
  `python sql/migrate.py` (see `sql/README.md`)
- `ingest/` - RaceChrono parser + shared queries (stdlib-only parsing;
  cloud access separate), used by both the Function App and MCP server
- `mcp_server/` - read-only MCP server (Container Apps) and its Entra
  token verifier
- `dashboard/` - React + Vite + TypeScript dashboard (Static Web Apps)
- `function_app.py` - Azure Functions app: ingest + dashboard read/write API
- `tests/` - pytest suite; `pip install -r requirements-dev.txt`, then
  `pytest`
- `docs/` - way of working, backlog, specs, MCP and iOS Shortcut setup
