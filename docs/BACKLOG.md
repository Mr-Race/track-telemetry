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
- [ ] **Backfill historical sessions** — upload all pre-existing
      RaceChrono CSVs (before the ingest Function/Shortcut existed)
      through the same /api/ingest path so past track days show up
      alongside new ones.
- [ ] **Investigate automating the file load from RaceChrono/Shortcuts**
      — today's flow is share-sheet -> Shortcut -> manual trigger;
      look into whether RaceChrono can auto-export/auto-share on
      session stop, or whether Shortcuts has a folder-watch/automation
      trigger, to remove the manual step at the track.
- [ ] **Login page on a custom domain (www.mr-race.com)** — front the
      MCP connector/dashboard with a proper login page on the owned
      domain instead of the raw Container Apps URL; ties into the
      planned OAuth 2.1 + PKCE work below.
- [ ] **Push session summaries/analysis to the dashboard** — after
      ingest, generate a per-session summary (fastest lap, corner
      deltas vs. prior sessions at the same track, consistency/std
      dev across valid laps) and surface it as a dashboard view rather
      than something you have to ask Claude for on demand.

## Weekend 2 (complete)
- [x] HTTP-triggered Azure Function: POST /api/ingest (parser wrapped
      as serverless endpoint; archives raw CSV to Blob, loads SQL,
      returns JSON summary) — deployed and smoke-tested 2026-07-08.
      `func-track-telemetry-ingest` (Consumption, Linux, Python 3.12,
      eastus), system-assigned managed identity granted
      `Storage Blob Data Contributor` on `racechronoraw` and
      `db_datareader`/`db_datawriter` on the SQL DB (via
      sql/05_function_identity.sql). Live at
      `https://func-track-telemetry-ingest.azurewebsites.net/api/ingest`
      (function-key auth). Verified end-to-end with a real 52k-sample
      CSV: `dry_run=1` (parse, lap calc, corner-metric calc, SQL
      corner lookup, Blob archive, ~7s) and a real `dry_run=0` load
      (session + 7 laps + 70 corner_metrics written, ~14s; test row
      deleted afterward). Verified from the iOS Shortcut too — see
      docs/ios_shortcut.md.
- [x] iOS Shortcut: share-sheet upload from RaceChrono at the track —
      built per docs/ios_shortcut.md, tested 2026-07-21 end-to-end
      (dry run + real load: session_id 5, 10 laps, 100 corner_metrics).
- [x] 2026-07-21 — MCP server on Azure Container Apps (Streamable
      HTTP), managed identity -> SQL (db_datareader). Deployed as
      `ca-track-telemetry-mcp` (see docs/mcp_server.md). Fixed two
      deploy-time bugs: missing `azure-storage-blob` in
      mcp_server/requirements.txt (server imports `ingest.cloud`,
      which imports it at module level, causing a crash loop), and
      FastMCP's DNS-rebinding host-header check rejecting all traffic
      because `mcp.settings.host` was set post-construction instead
      of passed to the `FastMCP(...)` constructor (421 "Invalid Host
      header"). Granted the identity `db_datareader` via
      sql/06_mcp_identity.sql. Verified all four tools
      (list_sessions, get_session_detail, get_corner_metrics,
      compare_laps) against the live endpoint with a real MCP client.
- [x] 2026-07-21 — Register as Claude custom connector; test from
      phone. Added via Settings -> Connectors -> Add custom
      connector, no auth. Confirmed working end-to-end from the
      phone.

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
- [x] 2026-07-03 — Resource group, Azure SQL (free tier, Entra-only), Storage
- [x] 2026-07-06 — Schema DDL with config-aware tracks and corner zones
- [x] 2026-07-06 — Corner apex coordinates: Lightning 10, Thunderbolt
      Classic 13, Devil's Pass 11 (T9 provisional)
- [x] 2026-07-06 — Parser: CSV v3 -> laps + corner metrics, median-based
      lap validity, tested against real May/June sessions
- [x] 2026-07-08 — HTTP ingest Azure Function (POST /api/ingest):
      built, deployed (func-track-telemetry-ingest, eastus), and
      verified end-to-end with both dry-run and a real DB load
- [x] 2026-07-21 — iOS Shortcut share-sheet upload from RaceChrono,
      tested end-to-end from an iPhone (real session loaded: session_id
      5, 10 laps, 100 corner_metrics)
