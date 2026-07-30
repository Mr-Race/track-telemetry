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

## Versioning (decided 2026-07-24)
Semver-style product versioning:
- **0.x (current, ~0.9):** pre-stable — schemas change freely,
  features land daily, nothing is promised. The MVP launch was a
  milestone inside 0.x, not 1.0.
- **1.0:** declared when the v1.0 scope below is complete — core
  loop finished (drive -> auto-ingest -> enriched analysis ->
  review), no known broken pieces in prod, all endpoints secured,
  docs baseline exists. From 1.0 on, breaking changes cost.
- **1.x:** additive, backward-compatible features (1.1, 1.2...);
  fixes are 1.0.1-style patches.
- **2.0:** reserved for breaking/identity-level change — for this
  product, the replay + multi-user platform.

Release mechanics to adopt at 1.0 (part of the v1.0 scope):
git tag + GitHub Release per version, CHANGELOG.md updated with
every release, version number shown in the dashboard footer.

## v1.0 — finish to launch
The cut line: completes the analysis story (every session ever
driven, ingested and enriched, with optimal laps, fully secured)
plus the docs baseline. Nothing else blocks 1.0.
- [ ] **Fix issue #1: MCP server redeploy** — prod MCP is down
      (stale image queries the dropped sessions.run_group column).
      Rebuild/redeploy `ca-track-telemetry-mcp` from main, verify all
      four tools live. Automatic 1.0 blocker: "no known broken
      pieces in prod."
- [ ] **Auto-fetch session weather at ingestion** — when a session is
      loaded, call Open-Meteo archive API (free, keyless) with track
      lat/lon + session start_time; populate sessions.weather and
      air_temp_f automatically. Consider adding columns: humidity_pct,
      wind_mph, precip_in, track-relevant conditions summary. Capture
      humidity + observation time, not just temp/summary (the v1.x
      dashboard weather section consumes them).
- [ ] **Per-segment (corner-to-corner) times at ingestion** —
      compute segment times between consecutive corner zones per lap
      and store them (new segment_times table or columns on
      corner_metrics). Prerequisite for the optimal-lap feature
      below; derivable at ingest from data already parsed (zone
      entry timestamps), no sample storage needed. IMPLEMENTATION
      NOTE (validated 2026-07-24 on real CSVs): segment boundaries
      must be fixed distance/timing gates with interpolated crossing
      times — NOT the per-lap min-speed timestamp, whose lap-to-lap
      jitter inflates the optimal-lap gap badly (13.3s vs a credible
      3.1s on the same Thunderbolt session).
- [ ] **Dashboard: optimal lap time per session** — in the event
      view and session drill-down detail, show each session's
      optimal (theoretical best) lap: the sum of that session's best
      segment times, alongside actual best lap and the gap between
      them ("how much time was left on the table"). Depends on the
      per-segment times item above.
- [ ] **Backfill historical sessions** — upload all pre-existing
      RaceChrono CSVs (before the ingest Function/Shortcut existed)
      through the same /api/ingest path so past track days show up
      alongside new ones. Run AFTER weather + segment times land, so
      one re-ingest pass populates everything (weather, segments,
      OBD corner metrics) for the whole history.
- [ ] **OAuth 2.1 + PKCE via Entra ID on the MCP server** — closes
      the last unauthenticated endpoint.
- [ ] **Docs baseline (living documentation v1)** — technical +
      business doc sets as docs-as-code in the repo
      (docs/technical/, docs/business/), updated in the same commits
      as the changes they describe, rendered via GitHub Pages
      (MkDocs Material or similar; $0, no sync job):
      - Technical: architecture + diagram, schema/data dictionary,
        API reference, deployment/runbook (incl. migration checklist
        per issue #1's lesson), ADR-style decision log (Power BI
        drop, distance-gate optimal-lap method, Entra CIAM gotchas).
      - Business: what the platform does and why, feature overview
        per release, roadmap narrative, cost model ($0 story),
        value/outcomes (e.g. optimal-lap predicting the next day's
        PB within 0.3s). Non-technical reader; reusable for
        portfolio and interviews.
      - Confluence Cloud (Free tier) mirror is OPTIONAL, deferred to
        v1.x if ever wanted for audience reasons — requirement is
        currency, not the tool; Pages is the system of record's
        renderer.
- [ ] **Release mechanics** — first git tag `v1.0.0` + GitHub
      Release, CHANGELOG.md created, version in dashboard footer.

## v1.x — post-launch backlog (additive)
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
- [ ] **Dashboard weather section** — per-session conditions panel
      (temp, humidity, day/date, session time); "compare my pace in
      cool vs hot sessions" views once enough data accumulates.
      Consumes v1.0's weather auto-fetch fields.
- [ ] **Dashboard: track management interface** — view and add
      tracks/configurations with track info (length, corner count,
      location) and my personal best per configuration (computed
      from laps table). Requires write API endpoints (auth
      foundation already in place).
- [ ] **Dashboard: corner apex editor** — within track management,
      click/tap on the satellite view to place or adjust corner apex
      coordinates and zone radii, writing to the corners table.
      Replaces the manual Google Maps coordinate workflow for new
      tracks.
- [ ] **Event summary page** — real dashboard behind the
      /events/:eventId placeholder route (reqs TBD).
- [ ] **Login page on a custom domain (www.mr-race.com)** — front the
      dashboard/MCP with the owned domain instead of raw Azure URLs.
- [ ] API Management in front of the ingest endpoint (hardening story)
- [ ] Lock storage account networking to selected networks
      (documented hardening step)
- [ ] Thunderbolt corner names (Lightning done: T9 Lightbulb,
      T10 Kink; Jersey Devil placement TBD per AC's coding)
- [ ] Devil's Pass T9 apex validation from first GPS trace on that
      layout (current pin is provisional) — blocked until a session
      is driven on that configuration
- [ ] Optional Confluence Cloud mirror of the docs (see v1.0 docs
      baseline — only if an audience warrants it)

## v2.0 — replay + multi-user platform
Theme: the platform learns to replay and share driving. Breaking /
identity-level scope; design as one coherent release.
- [ ] **Deep telemetry storage** — telemetry_samples table or
      Parquet-in-Blob for sample-level analysis (full speed traces,
      throttle/RPM overlays): parse raw CSV from Blob on demand, or
      ingestion Function persists a downsampled (~5Hz) lat/lon trace
      per lap. Prerequisite for replay.
- [ ] **Lap replay animation (RaceChrono-style)** — not a static
      line: an arrow/marker traveling the driven line over the
      satellite image in lap time, with playback controls and
      timeline scrubbing; speed/throttle/RPM readouts following the
      marker. Design target: ghost-lap mode — two laps replayed
      simultaneously for comparison (own laps, and friends' laps
      once multi-user lands). Depends on deep telemetry storage.
- [ ] **Multi-user platform** — friends create accounts, upload
      their own RaceChrono sessions, share best laps and corner
      speeds; ghost comparisons against friends' laps. MAJOR scope:
      per-user data ownership on sessions/laps and sharing
      permissions on top of the existing Entra External ID + 
      driver_id foundation (schema prep done 2026-07-23).

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
- [x] 2026-07-24 — Block 5 step 4: post-login dashboard home — new
      DashboardHome page at "/" shown via AuthenticatedTemplate
      instead of the public LandingPage once signed in
      (UnauthenticatedTemplate still shows LandingPage). Three quick
      links reusing existing endpoints: most recent session
      (listSessions, last entry since the API already orders
      ascending by date/session_number), consumables due soon
      (getConsumables, overdue or <25% remaining), and the track
      directory (listTracks) with a live track count. Verified
      layout/loading/error states render cleanly via a headless
      Playwright screenshot of the component (temporarily mounted at
      a throwaway route, reverted after) since real interactive Entra
      ID sign-in isn't automatable headlessly in this environment —
      full authenticated data flow still needs a manual browser check
      per [[block5_auth_progress]].
- [x] 2026-07-24 — Block 5 step 5: lock dashboard data behind auth —
      discovered `/sessions`, `/tracks`, `/tracks/{id}`, and
      `/consumables` served full personal telemetry with no sign-in
      required (client routes weren't gated, and the read API was
      anonymous by original design). Fixed both ends: exposed an
      `access_as_user` delegated scope on the SPA app registration
      (`identifierUris`/`api.oauth2PermissionScopes` via Graph API
      PATCH — confirmed via `az rest`, since `az ad app` commands need
      an explicit tenant-scoped token for a directory with no ARM
      subscription); MSAL now requests that scope alongside
      `openid`/`profile` at sign-in (`dashboard/src/authConfig.ts`)
      and attaches it as a Bearer header on every dashboard API call
      (`dashboard/src/api/client.ts`, via a new
      `dashboard/src/msalInstance.ts` singleton so the plain fetch
      functions can reach MSAL outside the React tree); the satellite
      image endpoint moved from a plain `<img src>` to a fetch+
      object-URL pattern since `<img>` can't send headers
      (`TrackPanel.tsx`). Server side: new `ingest/api_auth.py`
      validates the JWT with `PyJWT`'s `PyJWKClient` (signature via
      JWKS, audience = the app's client ID, issuer = the CIAM
      tenant's discovery doc) before any handler touches the DB;
      applied to all read routes in `function_app.py` via a
      `@require_auth` decorator, `POST /api/ingest` untouched (already
      function-key gated). Client-side, `App.tsx` gained a
      `RequireAuth` wrapper redirecting signed-out visitors to `/`.
      Pulled forward from Block 6 rather than waiting for a write
      endpoint, per explicit ask after the gap was found live in prod.
      Verified: local `func start` returns 401 with no/bad token
      without touching the DB; a live headless screenshot of prod
      confirms unauthenticated `/sessions` now falls back to the
      public landing page; prod API 401s with no token post-deploy.
      Full authenticated happy path (sign in, see real data) still
      needs a manual browser check — real interactive Entra sign-in
      isn't automatable headlessly here.
- [x] 2026-07-24 — Corner names (`sql/07_corner_names.sql`) — Lightning
      T9 = "Lightbulb", T10 = "Kink", per AC. File was authored and
      committed from the Claude web client in a separate session
      (`cf20e45`); applied to the live DB in this session (it hadn't
      been run yet) and verified via `SELECT`. Thunderbolt names still
      TBD.
- [x] 2026-07-24 — OBD channels in corner metrics
      (`sql/10_obd_corner_metrics.sql`) — new `corner_metrics.throttle_pos_apex_pct`
      / `rpm_exit` columns (additive `ALTER TABLE`, existing rows stay
      NULL until re-ingested — full backfill is the v1.0 backfill
      item's job). `ingest/racechrono_parser.py`: `parse_csv` now
      optionally reads the `rpm`/`throttle_pos` OBD channels (source
      `"200: obd"`, absent gracefully rather than erroring if the
      device wasn't OBD-paired for a given export);
      `compute_corner_metrics` records throttle at the zone's
      min-speed ("apex") sample and RPM at the zone's last ("exit")
      sample, matching how `exit_speed_mph` already picks its sample;
      `load()` inserts both. Verified against both real sample CSVs
      in `data/`: CLI dry run against the temp corners fixture, then
      a second dry run using the live DB's real 12-corner Lightning
      event fetched via `fetch_corners` — sensible throttle/RPM
      progression across a full flying lap (e.g. T10 exit onto the
      front straight: 76% throttle, 6405 RPM). Devil's Pass T9 apex
      validation stays blocked — no session has been driven on that
      layout yet, so there's no GPS trace to validate against.
- [x] 2026-07-24 — Run group reference tables
      (`sql/11_run_groups.sql`) — new `dbo.organizations`
      (SCCA-HPDE, NASA-NE-HPDE) and `dbo.run_groups` (FK'd, with a
      `sort_order` for experience level): SCCA-HPDE has Novice/
      Intermediate/Advanced, NASA-NE-HPDE has DE1/DE2/DE3/
      DE4-Instructors. Replaced the old free-text columns rather than
      adding alongside them, per the project's real-tables-not-text
      preference: `events.organization` backfilled to
      `organization_id` (both existing events were 'NASA-NE') then
      dropped, tightened to `NOT NULL`; `sessions.run_group` dropped
      in favor of nullable `run_group_id` (nothing to backfill there —
      it was never populated by ingestion, always a manually-set
      field). `ingest/queries.py`'s three session queries now
      `LEFT JOIN run_groups` instead of selecting the old text column;
      API response shape unchanged (`run_group` is still a plain
      string or null), so no dashboard changes needed. Verified: both
      events backfilled correctly before the `NOT NULL` tightening,
      and `list_sessions`/`get_session_detail` return cleanly against
      the live DB post-migration.
- [x] 2026-07-24 — Fixed event/organization data model: assigning run
      groups to the existing sessions surfaced that `event_id=1`
      ("Lightning May 2026") was wrongly acting as a catch-all for
      every Lightning session ever ingested regardless of actual
      calendar occurrence — the May 16-17 NASA weekend and a July 22
      SCCA day both got lumped into it, so July 22 inherited the wrong
      `organization_id`. The schema itself needed no changes:
      `events.organization_id` + free-text `event_name` already
      support one row per real occurrence, org-attributed, with
      whatever name that org actually used (NASA's "Ice Breaker",
      SCCA's "TNIA" for Track Night In America) — nothing stops
      multiple event rows sharing a name across different dates. Split
      the mis-attributed data: new event row ("TNIA", SCCA-HPDE,
      2026-07-22), moved sessions 6/9/10 onto it, tagged all three
      Novice. Also found and fixed a duplicate while at it: session #4
      and #5 on that day were byte-for-byte the same session (same
      start time, 9 laps, 1:26.816 best, 90 corner metrics) — an iOS
      Shortcut double-submit. Dropped the duplicate (cascading its
      laps/corner_metrics) and renumbered the remaining two sessions
      to close the gap. Verified `list_sessions` end-to-end
      post-cleanup: 6 real sessions, correct event/org/run_group per
      row.
- [x] 2026-07-24 — Dashboard: event management, Block 6's first
      write-capable feature. New endpoints on `function_app.py`/
      `ingest/queries.py`: `GET /api/organizations`, `GET /api/events`
      (event + org/track + session count per row), and
      `POST /api/events` (create) — all behind the existing
      `@require_auth` decorator, no new auth plumbing needed. New
      `dashboard/src/pages/EventsPage.tsx`: a create-event form
      (org/track selects, name, start/end date) plus a table of all
      events, wired up at `/events` behind `RequireAuth`. Verified
      locally end-to-end: `func start` + `npm run dev` (Vite proxies
      `/api` to the local host), signed in via MSAL, created two real
      events through the form, confirmed both `POST /api/events` calls
      and the subsequent `GET /api/events` refresh succeeded against
      the live DB.
- [x] 2026-07-24 — Dashboard: sessions list grouped by event.
      `SessionListPage.tsx` now renders one bold event-level row (date
      range, track, session count, run group, best lap, avg valid lap
      — all aggregated client-side from `/api/sessions`, no new
      backend endpoint) with its sessions indented underneath. Event
      name links to a new placeholder `/events/:eventId`
      (`EventSummaryPage.tsx`) — a real summary dashboard is deferred,
      reqs TBD, but the route exists so the link isn't dead. Verified
      end-to-end: `func start` + `npm run dev` on the default port
      5173 (a non-default port broke MSAL sign-in — the Codespaces
      forwarded-port URL didn't match the redirect URI already
      registered on the Entra app, see Block 5's redirect-URI gotcha),
      signed in, confirmed the grouped layout against real session
      data.
- [x] 2026-07-30 — Car catalog, another write-capable dashboard
      feature alongside events. New `dbo.cars` table (`sql/12_cars.sql`,
      already applied to the live DB in an earlier session but not
      yet committed — committed now) with a nullable `sessions.car_id`
      FK: scoped per session rather than per event since a driver
      could swap cars between sessions within the same event, matching
      how `run_group_id` already works (`sql/11_run_groups.sql`).
      New `GET /api/cars` / `POST /api/cars` on `function_app.py`
      (`queries.list_cars`/`create_car`), behind the existing
      `@require_auth` decorator. New `dashboard/src/pages/CarsPage.tsx`
      mirroring `EventsPage.tsx` (add-car form + table), wired up at
      `/cars`. `car` is also now surfaced read-only everywhere
      `run_group` already was — `list_sessions`/`get_session_detail`/
      `session_summary` LEFT JOIN `dbo.cars`, and `SessionListPage`/
      `SessionDetailPage`/`EventSummaryPage` display it — but there's
      no UI yet to assign a car to an existing session (all
      `sessions.car_id` stay NULL until set manually via SQL, same
      as `run_group_id` before it). Verified locally end-to-end:
      `func start` + `npm run dev` on port 5173, confirmed
      `GET /api/cars` and `GET /api/events` both 401 identically
      with no token, signed in via MSAL, added a real car through
      the form, confirmed it listed.
- [x] 2026-07-30 — Assign a car to an existing session. New
      `PATCH /api/sessions/{session_id}` (`queries.set_session_car`),
      same `@require_auth` pattern; `get_session_detail` now also
      returns `car_id` alongside the display-name `car` field. New
      `CarAssignment` control on `SessionDetailPage.tsx` — a `<select>`
      of all cars replacing the old static run_group/car text, wired to
      the new endpoint and refetching session detail on save (closes
      the gap noted in the car-catalog entry above). Verified locally:
      `func start` restart, confirmed `PATCH /api/sessions/{id}` 401s
      with no token, then a manual browser check — assigned a car to
      a real session through the dropdown and confirmed it stuck.
      Redeployed both `func-track-telemetry-ingest` (all 14 routes,
      including the new `cars`/`sessions` PATCH ones, synced and
      401ing correctly with no token) and
      `swa-track-telemetry-dashboard` (prod root 200s) to prod
      afterward, covering both this and the car-catalog entry above.
- [x] 2026-07-30 — Link consumables to a car; real Integra data.
      `sql/13_consumables_car_link.sql`: `dbo.consumables` gets a
      nullable `car_id` FK plus a `baseline_sessions` counter for
      real-world track days the app hasn't ingested yet (Block 2's
      historical-backfill item is still open — DB only has 6 sessions
      total, nowhere near the 9-12 these parts have actually seen).
      `get_consumables` now computes `sessions_since_install` as
      `baseline_sessions + COUNT(sessions since install_date scoped to
      car_id)`, so it keeps incrementing correctly as new sessions get
      uploaded *and tagged with the Integra's car_id* (depends on the
      session→car assignment UI two entries up) — car_id NULL falls
      back to counting all sessions, unchanged from before this
      migration. Inserted four real rows for car_id=2 (Integra): front
      brake pads (Paragon P3, installed 2026-05-30, target 40
      sessions, baseline 9), rear brake pads (same date, target 60,
      baseline 9), brake fluid (installed 2026-06-13, target 12,
      baseline 9 — 75% used, near due), engine oil (0W-20, installed
      2026-04-12, target 20, baseline 11 — one car-tagged session
      already postdates it). Baselines were reverse-solved so
      today's total matches the real counts given; a caveat worth
      remembering if historical sessions ever get backfilled and
      retroactively car-tagged for dates already covered by a
      baseline, they'd double-count. `ConsumablesPage.tsx` now shows
      the linked car name in each row. Verified: migration applied
      live (ALTER TABLE and the INSERT had to run as separate batches
      — SQL Server doesn't reliably resolve a same-batch ALTER-then-
      reference), a direct query confirmed all four computed totals
      matched (9/9/9/12), then a `func start` restart + manual
      browser check on the live Consumables page confirmed the same.
      Redeployed both `func-track-telemetry-ingest` and
      `swa-track-telemetry-dashboard` to prod same session; prod
      `/api/consumables` 401s with no token, dashboard root 200s.
