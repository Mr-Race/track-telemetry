# Track Telemetry Platform

Enterprise-grade telemetry pipeline for HPDE track data (RaceChrono ->
Azure SQL -> Claude via MCP -> dashboards). Built as a portfolio piece
demonstrating cloud + AI architecture.

## Architecture (target)
RaceChrono CSV v3 -> iOS Shortcut -> HTTP Azure Function (parse/enrich)
-> Azure SQL (source of truth) + Blob (raw archive)
-> MCP server (Container Apps, managed identity, read-only)
-> Claude custom connector / React dashboard / Power BI

## Status
- [x] Azure SQL (free tier, Entra-only auth) + Blob provisioned
- [x] Schema: config-aware tracks, corner apex zones (3 layouts seeded)
- [x] Parser: laps + corner metrics, validated against real sessions
- [ ] Initial data load (Cloud Shell or laptop)
- [ ] Weekend 2: ingestion Function + iOS Shortcut + MCP server
- [ ] Weekend 3: OAuth, dashboard, writeup

## Repo layout
- sql/ - schema and seed scripts, run in order
- ingest/ - RaceChrono parser (stdlib parsing, pyodbc load)
- docs/ - backlog and (future) architecture writeup
