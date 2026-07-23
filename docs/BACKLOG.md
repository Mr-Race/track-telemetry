# Track Telemetry Platform — Backlog

## Guiding principles
- **Cloud-native, Azure-first — applies to every item below.** All
  features are built on Azure managed services (Functions, Container
  Apps, Logic Apps, Static Web Apps, Azure SQL serverless, Blob,
  Entra); no locally hosted components, no VMs as permanent
  infrastructure, no on-box state. Prefer serverless/consumption
  tiers, managed identity over secrets, and infrastructure that
  scales to zero. When a non-Azure service is unavoidable (e.g.
  Open-Meteo, OneDrive trigger, GitHub), it integrates via API
  against Azure-hosted compute — nothing runs outside the cloud.
- **React is the sole visualization layer (decided 2026-07-22).**
  The dashboard is React + Vite on Azure Static Web Apps. Power BI
  is dropped from the roadmap to avoid licensing costs/dependencies
  down the line — no per-seat or Pro-license exposure; everything
  user-facing stays on free-tier, open tooling.

## MVP checklist (launch readiness)
The six pieces that define "launched": a visitor can land on the
site, sign in, land on a home screen, and use the core dashboard.
Items link to the backlog block that tracks the actual work.
- [x] List of sessions with drill-down detail — done, see `## Done`
      (2026-07-22 session list view + session detail page)
- [x] Consumable dashboard — done, see `## Done` (2026-07-22
      consumables life tracker)
- [x] Track directory — done, see `## Done` (2026-07-23 track
      directory + track view pages)
- [x] Landing page (public, pre-login) — done, see `## Done`
      (2026-07-23 landing page)
- [ ] Login page — see Block 5's "Dashboard login with Entra ID"
- [ ] Landing page after login (dashboard home) — new item, see Block 5

## Backlog (open)
Grouped into blocks; each block is buildable independently of the
others. Order below is the recommended build sequence — quick
independent wins first, then the sample-storage foundation the GPS
trace overlay needs, then the dashboard core, then auth (required
before any write-capable dashboard feature), then hardening and the
v2/portfolio tail.

### Block 1 — Data & parser enhancements
No dependencies on anything else in the backlog; small, self-contained.
- [ ] Devil's Pass T9 apex validation from first GPS trace on that
      layout (current pin is provisional)
- [ ] Corner names (Jersey Devil, Lightbulb, etc.) in corners table
- [ ] OBD channels in corner metrics (throttle position at apex,
      RPM at exit) — channels already present in CSV v3 exports

### Block 2 — Ingestion pipeline expansion
Builds on the existing /api/ingest path; independent of the dashboard
and auth work below.
- [ ] **Auto-fetch session weather at ingestion** — when a session is
      loaded, call Open-Meteo archive API (free, keyless) with track
      lat/lon + session start_time; populate sessions.weather and
      air_temp_f automatically. Consider adding columns: humidity_pct,
      wind_mph, precip_in, track-relevant conditions summary. The
      dashboard weather widget (Block 4) needs humidity + observation
      time captured, not just temp/summary.
- [ ] **Backfill historical sessions** — upload all pre-existing
      RaceChrono CSVs (before the ingest Function/Shortcut existed)
      through the same /api/ingest path so past track days show up
      alongside new ones.
- [ ] **One-step ingestion (automate the file load)** — remove the
      manual Shortcut prompts. Proposed design: export CSV from
      RaceChrono to a watched OneDrive folder; Logic App (OneDrive
      "file created" trigger) POSTs it to the ingest Function; the
      Function derives event/session automatically from CSV metadata
      (track name + date -> match or auto-create event;
      session_number = next for that event/date). Add idempotency
      (skip/flag already-ingested files, e.g. content hash) and a
      result notification (email/push via the Logic App) replacing
      the Shortcut popup. Retires the 3-prompt Shortcut once trusted.
      (Also still worth checking whether RaceChrono can auto-export
      on session stop.)

### Block 3 — Deep telemetry storage
Independent lift, but a prerequisite for the GPS trace overlay in
Block 4.
- [ ] telemetry_samples table or Parquet-in-Blob for sample-level
      analysis (full speed traces, throttle/RPM overlays) — either
      parse raw CSV from Blob on demand, or have the ingestion
      Function persist a downsampled (~5Hz) lat/lon trace per lap.

### Block 4 — React dashboard core
The dashboard itself is the foundation; everything else in this
block renders into it, so build it first. Session list, session
summary, satellite view, benchmarks, consumables, and the track
directory are done (see `## Done`). GPS overlay and weather section
remain genuinely blocked on earlier blocks.
- [ ] **Dashboard: GPS trace overlay** — draw the car's driven line
      over the satellite view, RaceChrono-style, for a selected
      lap/session. Depends on Block 3's sample-level GPS storage.
- [ ] **Dashboard weather section** — per-session conditions panel
      (temp, humidity, day/date, session time); enable "compare my
      pace in cool vs hot sessions" views once enough data
      accumulates. Full value once Block 2's weather auto-fetch is
      also in place.

### Block 5 — Auth foundation (Entra ID)
Required before any write-capable dashboard feature (Block 6) and
before the custom-domain login page below.
- [ ] **Dashboard login with Entra ID (modern auth stack)** —
      authentication for the React dashboard and write APIs:
      Entra External ID tenant (successor to AD B2C; me as primary
      user, ready for friends as external identities later); OAuth
      2.1 authorization code flow + PKCE via MSAL React (no implicit
      flow, no secrets in the SPA); passkeys (FIDO2/WebAuthn) as the
      primary passwordless sign-in; Function app validates bearer
      tokens — write endpoints require auth, read endpoints may stay
      open initially. Foundation for track management writes,
      friends' benchmarks, multi-user v2.
      - [x] 2026-07-23 — Schema prep: dbo.drivers table + FK'd,
            NOT NULL, backfilled driver_id on dbo.sessions
            (sql/09_drivers.sql). Built the real table now rather than
            a bare nullable column, since the table only had 7 rows —
            Block 8 (multi-user v2) won't need to touch historical
            data later. DEFAULT constraint (driver_id=1, the sole
            'Me' row) means ingest.py's existing INSERT needs no code
            changes yet. Verified: drivers has 1 row, all 7 sessions
            backfilled to driver_id=1, FK_sessions_drivers exists,
            list_sessions/get_session_detail still return correctly
            against the live DB.
      - [x] 2026-07-23 — Entra External ID (CIAM) tenant provisioned
            (tenant `cc8e128a-ad5b-49af-a3ce-35e7c3c3e30c`,
            `tracktelemetry.onmicrosoft.com`), SPA app "Track Telemetry
            Dashboard" registered (client `99a220cf-5739-4be8-8d68-55ebaa905ad3`,
            public client, no secret), user flow `SignUpSignIn` created
            and attached. Note: the CIAM user-flow wizard only offers
            email + password as a primary identity provider today, not
            passkeys/passwordless as originally scoped above — revisit
            via Entra's Authentication Methods policy later if wanted.
      - [x] 2026-07-23 — MSAL React integration in the dashboard —
            `@azure/msal-browser` + `@azure/msal-react` added,
            `MsalProvider` wraps the app (`dashboard/src/main.tsx`),
            sign-in/out control in the header (`dashboard/src/App.tsx`).
            Interactive sign-in confirmed working end-to-end (auth-code
            + PKCE via `loginRedirect`). Two config gotchas worth
            knowing if this needs touching again: this CIAM tenant's
            OIDC issuer resolves to the tenant-GUID subdomain rather
            than the friendly domain, so `authConfig.ts`'s
            `knownAuthorities` lists both; and Azure AD's redirect URI
            match is byte-exact (trailing slash included).
      - [ ] Function app bearer-token validation (once Block 6 has a
            write endpoint to protect)
- [ ] **Post-login landing page (dashboard home)** — first screen
      after sign-in: quick links (most recent session, consumables due
      soon, track directory) rather than dropping straight into the
      session list. Depends on the auth item above (needs to know
      you're signed in) and benefits from Block 4's track directory.
- [ ] OAuth 2.1 + PKCE via Entra ID on the MCP server
- [ ] **Login page on a custom domain (www.mr-race.com)** — front the
      MCP connector/dashboard with a proper login page on the owned
      domain instead of the raw Container Apps URL; depends on the
      two auth items above.

### Block 6 — Write-capable dashboard features
Depend on Block 5's auth foundation (write endpoints require it).
- [ ] **Dashboard: track management interface** — view and add
      tracks/configurations with track info (length, corner count,
      location) and my personal best per configuration (computed
      from laps table). First write-capable dashboard feature —
      requires write API endpoints on the Function app + auth on
      those routes (read endpoints can stay open/simple).
- [ ] **Dashboard: corner apex editor** — within track management,
      click/tap on the satellite view to place or adjust corner apex
      coordinates and zone radii, writing to the corners table.
      Replaces the manual Google Maps coordinate workflow for new
      tracks.

### Block 7 — Hardening
Independent of dashboard content; production-readiness items that
can run anytime.
- [ ] API Management in front of the ingest endpoint (hardening story)
- [ ] Lock storage account networking to selected networks
      (documented hardening step)

### Block 8 — Multi-user platform (v2 ambition)
Depends on Block 5's driver_id schema prep — design that decision
before building this.
- [ ] **Multi-user platform (v2 ambition)** — friends create
      accounts, upload their own RaceChrono sessions, share best
      laps and corner speeds. MAJOR scope: adds identity/auth
      (Entra External ID), per-user data ownership on sessions/laps,
      and sharing permissions.

### Block 9 — Reporting & portfolio wrap-up
Do last — documents the finished system.
- [ ] Architecture diagram + README writeup (portfolio deliverable)

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
- [x] 2026-07-22 — Decision: Power BI removed from roadmap; React on
      Static Web Apps is the sole visualization layer (licensing)
- [x] 2026-07-22 — React dashboard on Azure Static Web Apps (PWA):
      Vite + React + TypeScript app in dashboard/, deployed to
      `swa-track-telemetry-dashboard` (Free tier, East US 2) at
      https://salmon-moss-0a7e4b70f.7.azurestaticapps.net via the SWA
      CLI. Calls func-track-telemetry-ingest directly (CORS enabled
      for the SWA origin) rather than a Standard-tier linked backend,
      to stay on the free tier; local dev proxies /api to the
      Functions host instead.
- [x] 2026-07-22 — Dashboard: session list view — all sessions with
      track, date, best lap, average of valid laps; tap/click to open
      session detail. Backed by new GET /api/sessions (extended with
      an OUTER APPLY aggregate for best/avg lap) and
      GET /api/sessions/{id}; query logic shared with the MCP server
      via the new ingest/queries.py module.
- [x] 2026-07-22 — Push session summaries/analysis to the dashboard —
      new GET /api/sessions/{id}/summary: fastest lap, corner-speed
      deltas vs. the most recent prior session at the same track, and
      lap-time consistency (stdev across valid laps). Rendered as stat
      tiles + a color-coded corner-delta table on the session detail
      page.
- [x] 2026-07-22 — Dashboard: satellite track view — Azure Maps
      account `maps-track-telemetry` (Gen2/G2, global), accessed only
      via the Function App's managed identity (`Azure Maps Data
      Reader` role, no key ever leaves the server). New
      GET /api/tracks/{id}/satellite proxies the Get Map Static Image
      API, framing the bbox computed from that track's corner apex
      coordinates (ingest/maps.py, zoom picked analytically from the
      Web Mercator meters-per-pixel formula, validated against
      Lightning and Thunderbolt). Rendered as an <img> on the session
      detail page — no client-side map key exposure.
- [x] 2026-07-22 — Dashboard: friends' benchmark laps (v1) — new
      dbo.benchmarks table (sql/07_benchmarks.sql, manual INSERT, no
      write API) and GET /api/tracks/{id}/benchmarks, merged with my
      all-time personal best at that track into one ranked leaderboard
      on the session detail page.
- [x] 2026-07-22 — Dashboard: consumables life tracker (v1) — new
      dbo.consumables table (sql/08_consumables.sql, manual INSERT) and
      GET /api/consumables, computing sessions/months elapsed since
      install server-side. New /consumables dashboard page with
      remaining-life bars (good/warning/critical) and an overdue
      state; table starts empty pending real install data.
- [x] 2026-07-23 — Dashboard: track directory — new GET /api/tracks
      (ingest/queries.py's list_tracks, reusing the personal-best
      pattern from get_track_benchmarks) and a /tracks page listing
      every track/configuration with length, corner count, and
      personal best, linking to a new /tracks/:trackId view that
      reuses the existing TrackPanel (satellite + benchmarks).
      Verified end-to-end against the live Azure SQL DB via local
      `func start` + dashboard dev server: /api/tracks returns real
      data for all three configs, and both null-length and
      no-personal-best states (Devil's Pass) render cleanly.
- [x] 2026-07-23 — Landing page (public, pre-login) — new LandingPage
      at "/", now the site's front door: project blurb, feature
      summary, a live stat-tile preview (sessions logged/tracks
      tracked/best lap, computed client-side from the existing
      session and track list endpoints), and a "View the dashboard"
      CTA linking to the session list. Session list moved from "/" to
      "/sessions" to free up the root route; updated the nav and the
      one stale internal link (SessionDetailPage's back-link).
      Verified in-browser via local dev servers: landing renders with
      real data, "View the dashboard" and nav links route correctly.
