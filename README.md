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

## Architecture
RaceChrono CSV v3 -> iOS Shortcut (share sheet) -> HTTP Azure Function
(`func-track-telemetry-ingest`, parse/enrich)
-> Azure SQL (`free-sql-db-7848405`, source of truth) + Blob
(`racechronoraw`, raw archive)
-> MCP server (`ca-track-telemetry-mcp`, Container Apps, managed
identity, read-only) + React dashboard
(`swa-track-telemetry-dashboard`, Static Web Apps, Entra ID auth)
-> Claude custom connector / browser

Power BI was dropped from the roadmap (2026-07-22, see
`docs/BACKLOG.md`) — React on Static Web Apps is the sole
visualization layer, to stay free-tier/no-license.

## Status
MVP launched (2026-07-24) — see `docs/BACKLOG.md`'s MVP checklist and
`## Done` log for the full history. Live pieces:
- [x] Azure SQL (free tier, Entra-only auth) + Blob provisioned
- [x] Schema: config-aware tracks, corner apex zones, run groups,
      organizations/events, drivers
- [x] Parser: laps + corner metrics (incl. OBD throttle/RPM),
      validated against real sessions
- [x] Ingestion Function (`POST /api/ingest`) + iOS Shortcut share-sheet
      upload
- [x] MCP server (read-only, registered as a Claude custom connector)
- [x] React dashboard: session list/detail, consumables, track
      directory + satellite view, benchmarks
- [x] Entra ID auth (MSAL, OAuth 2.1 + PKCE) — dashboard sign-in +
      bearer-token-protected API
- [x] First write-capable dashboard feature: event management
      (Block 6 step 1)
- [ ] Remaining Block 6 items: track management UI, corner apex editor
- [ ] Block 7 hardening (API Management, storage network lockdown)
- [ ] OAuth on the MCP server, custom-domain login page

## Repo layout
- sql/ - schema and seed scripts, run in order
- ingest/ - RaceChrono parser + queries (stdlib parsing, pyodbc load,
  shared by the Function app and MCP server)
- dashboard/ - React + Vite + TypeScript dashboard (Azure Static Web Apps)
- function_app.py - Azure Functions app: ingest + dashboard read/write API
- docs/ - backlog, MCP server setup, iOS Shortcut setup
