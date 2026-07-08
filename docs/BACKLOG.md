# Track Telemetry Platform — Backlog

## Feature requests
- [ ] **Auto-fetch session weather at ingestion** — when a session is
      loaded, call Open-Meteo archive API (free, keyless) with track
      lat/lon + session start_time; populate sessions.weather and
      air_temp_f automatically. Consider adding columns: humidity_pct,
      wind_mph, precip_in, track-relevant conditions summary.
- [ ] **Dashboard weather section** — per-session conditions panel in
      the React dashboard; enable "compare my pace in cool vs hot
      sessions" views once enough data accumulates.

## Weekend 2 (in progress)
- [x] HTTP-triggered Azure Function: POST /api/ingest (parser wrapped
      as serverless endpoint; archives raw CSV to Blob, loads SQL,
      returns JSON summary) — code complete (function_app.py,
      ingest/cloud.py), compiles and imports locally via `func start`.
      **Not yet deployed**: no Function App resource provisioned in
      Azure yet (`az functionapp list` is empty). Next steps: create
      the Function App + managed identity, run sql/05_function_identity.sql
      against it, deploy, then test a real POST against it.
- [ ] iOS Shortcut: share-sheet upload from RaceChrono at the track
- [ ] MCP server on Azure Container Apps (Streamable HTTP), managed
      identity -> SQL (db_datareader)
- [ ] Register as Claude custom connector; test from phone

## Weekend 3 (planned)
- [ ] OAuth 2.1 + PKCE via Entra ID on the MCP server
- [ ] React dashboard on Azure Static Web Apps (PWA)
- [ ] Architecture diagram + README writeup (portfolio deliverable)

## Later / nice-to-have
- [ ] Power BI addendum: 2-3 report pages over the same DB (ephemeral
      Azure Windows VM for Desktop authoring)
- [ ] API Management in front of the ingest endpoint (hardening story)
- [ ] telemetry_samples table or Parquet-in-Blob for sample-level
      analysis (full speed traces, throttle/RPM overlays)
- [ ] OBD channels in corner metrics (throttle position at apex,
      RPM at exit) — channels already present in CSV v3 exports
- [ ] Devil's Pass T9 apex validation from first GPS trace on that
      layout (current pin is provisional)
- [ ] Lock storage account networking to selected networks
      (documented hardening step)
- [ ] Corner names (Jersey Devil, Lightbulb, etc.) in corners table

## Done
- [x] Resource group, Azure SQL (free tier, Entra-only), Storage
- [x] Schema DDL with config-aware tracks and corner zones
- [x] Corner apex coordinates: Lightning 10, Thunderbolt Classic 13,
      Devil's Pass 11 (T9 provisional)
- [x] Parser: CSV v3 -> laps + corner metrics, median-based lap
      validity, tested against real May/June sessions
