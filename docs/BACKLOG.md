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
- **Not a trackside tool (decided 2026-08-02).** Paddock/session-day
  analysis stays in RaceChrono, which already does on-device lap
  comparison and channel overlays and works with no connectivity.
  This platform is the season-level instrument: cross-session trends,
  corner progression, optimal-lap synthesis, consumables, weather
  correlation — all questions that want history, and therefore want
  the cloud. Consequence: offline-first / PWA-with-local-parse is
  explicitly OUT of scope, not merely deferred. Poor paddock signal
  is not a defect to engineer around.
- **Raw data is sacred.** The archived CSV in Blob is the system of
  record for a session. Compression is fine; downsampling, column
  pruning, or format conversion before upload is not — derived or
  columnar artifacts are generated server-side, never in place of
  the original.
- **Personal location data (decided 2026-08-02).** Sessions are GPS
  traces tied to a named driver, a car, and a timestamp — sensitive
  personal data, not just lap times. Security, retention, and
  sharing decisions are made on that basis. See
  `docs/specs/security-review.md`.

## Versioning (decided 2026-07-24)
Semver-style product versioning:
- **0.x (current, ~0.9):** pre-stable — schemas change freely,
  features land daily, nothing is promised. The MVP launch was a
  milestone inside 0.x, not 1.0.
- **1.0:** declared when the v1.0 scope below is complete — core
  loop finished (drive -> auto-ingest -> enriched analysis ->
  review), no known broken pieces in prod, all endpoints secured,
  docs baseline exists, and both pre-launch reviews (engineering
  practices, information security) are complete with no open
  high-severity findings. From 1.0 on, breaking changes cost.
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
plus the docs baseline and the two pre-launch reviews. Nothing else
blocks 1.0.
- [ ] **Backfill historical sessions** — the refresh-in-place
      `--backfill` CLI mode exists now (see Done, 2026-08-03) and has
      been run against the two historical CSVs already in `data/`
      (sessions 1 and 2). Remaining: more pre-automation RaceChrono
      CSVs exist outside this devcontainer (phone/laptop) and still
      need to land in `data/` before `--backfill` can be run against
      them too.
- [ ] **Information security due diligence** — SPEC:
      `docs/specs/security-review.md` (scoped 2026-08-02, review
      completed 2026-08-03 - see Done below). Remaining items before
      this can close: (1) restrict the CIAM `SignUpSignIn` user flow
      to invite-only / disable self-service sign-up (Entra portal
      change, needs you - any self-registered account currently gets
      full read/write access to all telemetry, since `driver_id`
      exists but is never used for authorization); (2) the
      `cryptography` CVE (GHSA-537c-gmf6-5ccf) turned out to be
      **not fixable** with a simple version floor - it conflicts with
      the existing `pyOpenSSL<26.2` pin (see Done below for the
      live-incident this caused); real fix needs `python-tds` off
      `X509.get_extension()` first, handed to the engineering review's
      dependency-pinning-policy item; (3) the `scp`-claim check in
      `ingest/api_auth.py` is deployed (Function App redeployed
      2026-08-03) but not yet verified against a real interactive
      sign-in - do that before trusting it; (4) redeploy the dashboard
      with the new CSP headers and manually confirm sign-in/API
      calls/satellite images still work. The MCP OAuth item below
      remains its own separately-tracked follow-up.
- [ ] **OAuth 2.1 + PKCE via Entra ID on the MCP server** — closes
      the last unauthenticated endpoint. Do this after the security
      review above.
- [ ] **Engineering practices assessment** — SPEC:
      `docs/specs/engineering-review.md` (scoped 2026-08-02). Honest
      review of everything written and deployed: automated testing
      (currently none — the parser, lap validity, corner metrics,
      event resolution, and weather parsing are the high-value
      targets), CI/CD to replace hand-run deploys and encode the
      verification steps currently held in memory, migration
      discipline for `sql/*.sql`, a dependency pinning policy (per
      the `mcp` crash-loop lesson), `ingest/` module structure,
      error handling and observability, and docs currency. Produces
      a severity-rated findings log; high-severity findings block
      1.0, the rest become v1.x issues.
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
- [ ] **Gzip the CSV before upload** — raw RaceChrono exports run
      15-20 MB, which is slow and flaky over weak paddock cellular.
      Numeric telemetry CSV compresses roughly 10:1, so the same
      file goes out at ~1.5-2 MB. Compress in the iOS Shortcut
      before POSTing; Blob archives the `.gz`; the Function
      decompresses on read (`Content-Encoding`/suffix sniff, with
      plain-CSV still accepted so historical files and the CLI path
      keep working). Deliberately compression only — no
      downsampling, no column pruning, no Parquet conversion on the
      phone, per the raw-data-is-sacred principle above. If a
      columnar format is ever wanted, it's a server-side derived
      artifact (see v2.0 deep telemetry storage), not a replacement
      for the archived original.
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
      /events/:eventId placeholder route. SPEC:
      `docs/specs/event-summary-page.md` (approved by AC 2026-07-25)
      — header/badges, four hero tiles (event best, event optimal
      across all sessions of the event, left on table, first-to-last
      progression), sessions table with per-row progress bars, the
      first-vs-last corner-delta table sorted by |delta|, weather
      strip, explicit exclusions, a new
      `GET /api/events/{id}/summary` endpoint, and timing-screen
      color conventions. Build AFTER v1.0's segment-times +
      optimal-lap work, which the hero tiles depend on.
- [ ] **Events list: in progress / upcoming / past split** (added
      2026-08-02) — the events list renders one flat table today.
      Split it into three groups using the dates already on
      `dbo.events`: **In progress** (today between start and end,
      inclusive — a multi-day weekend stays in progress across both
      days), **Upcoming** (sorted soonest-first; it's a planning
      view), **Past** (sorted most-recent-first; it's a review
      view). Compute the group server-side as a `phase` field on the
      `GET /api/events` rows rather than in the client, so the MCP
      tools and the dashboard agree on what "upcoming" means. Use
      the track's local date, not UTC — a UTC comparison flips US
      East events a day early. Null `end_date` falls back to
      `start_date`; empty groups collapse rather than render an
      empty header; an event with no sessions yet is valid in
      Upcoming/In progress with em dashes in the aggregate columns.
      Full detail in `docs/specs/event-summary-page.md`. Independent
      of the event summary page above — no dependency on segment
      times, so this can land earlier.
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
      NOTE: survey prior art before building (serious-racing.com
      ships 3D track models with onboard/replay modes) and decide
      deliberately whether replay is worth building here or whether
      the platform's differentiation stays in analysis.
- [ ] **Video correlation** — scope this as *correlation*, not
      "video". The hard problem is time-syncing footage to lap time
      (clock offset between camera and GPS logger; per-lap seek
      offsets), not playback. Storage is the second decision and
      should probably not be Blob: GoPro-bitrate footage gets
      expensive fast, and unlisted YouTube is free and is what
      comparable products do — store a URL + offset per lap rather
      than the media itself. Depends on lap replay for the
      side-by-side experience to mean anything.
- [ ] **Multi-user platform** — friends create accounts, upload
      their own RaceChrono sessions, share best laps and corner
      speeds; ghost comparisons against friends' laps. MAJOR scope:
      per-user data ownership on sessions/laps and sharing
      permissions on top of the existing Entra External ID +
      driver_id foundation (schema prep done 2026-07-23). Re-run the
      security review before this ships — multi-user changes the
      trust model fundamentally.

## v3 — parked ideas (not scheduled)
- [ ] **iRacing telemetry ingestion** (parked 2026-08-02) — iRacing
      writes `.ibt` telemetry files that `pyirsdk` can read offline,
      carrying `Brake`, `Throttle`, `SteeringWheelAngle`, `Gear`,
      `RPM`, `Speed`, and `LapDistPct` at ~60Hz — i.e. the driver-input
      channels the real-world side can't reach without a CAN
      reverse-engineering project, plus exact normalized lap distance
      that would make segment gating trivial. Deliberately NOT v1.x or
      v2.0: sim and real-world serve different purposes and folding
      them together would muddy what the platform is for. If it's ever
      built, it's a second ingest adapter behind the same schema, and
      the open questions are whether `.ibt` lat/lon are real-world
      coordinates that match existing corner apex zones (if not, key
      corners off `LapDistPct` instead) and whether sim and real
      sessions share tables at all.

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
- [x] 2026-08-03 — Redeployed the Function App and MCP Container App
      to pick up the security review's in-source fixes, and hit (then
      fixed) a real production incident along the way. The
      `cryptography>=48.0.1` floor added earlier that day turned out
      to be mutually unsatisfiable with the existing `pyOpenSSL<26.2`
      pin (every pyOpenSSL release below 26.2 caps `cryptography`
      under 48). `pip` doesn't error on that - it silently backtracked
      to `pyOpenSSL==22.0.0` (2022-era, incompatible with modern
      `cryptography`), which crashed at import. `func azure
      functionapp publish` reported success and the app showed
      "Running," but `/admin/functions` returned `[]` and every route
      404'd instead of the expected 401 - a real, brief, full outage
      of every API route caught by not trusting the deploy output
      (the exact lesson from the earlier `mcp` crash-loop incident,
      which is why this got checked instead of assumed). Reverted the
      floor in both `requirements.txt` files (documented why inline:
      the CVE fix needs `python-tds` off `X509.get_extension()`
      first, not fixable at the version-pin level today), redeployed,
      confirmed restored (`/api/sessions` back to 401, all 14 routes
      re-registered via `func`'s own deploy summary). MCP Container
      App redeployed separately (`az containerapp up --source .`);
      per the established lesson, checked `az containerapp revision
      list` for the new revision reaching `Healthy`/`Running` at 100%
      traffic with the old revision fully deprovisioned (not just the
      "Congrats!" message), then made a real `list_sessions` MCP tool
      call against the live endpoint and got real data back.
      `docs/specs/security-review.md` finding #3 updated to reflect
      the CVE is genuinely unfixed (not silently reintroduced) and
      finding #6 (the `scp` claim check) updated to "deployed, not
      yet verified" - it needs a real interactive sign-in to confirm
      the claim shape assumption before it's trusted, since getting
      it wrong would lock out legitimate sign-in. Dashboard (CSP
      headers) NOT redeployed this pass - out of scope for what was
      asked.
- [x] 2026-08-02 — Specs written for the two pre-launch reviews AC
      called for before declaring v1.0: `docs/specs/engineering-review.md`
      (testing, CI/CD, migrations, dependency policy, module
      structure, error handling/observability, docs currency) and
      `docs/specs/security-review.md` (secrets across git history,
      auth/scope enforcement, the ingest function-key model, personal
      location data classification and retention, network posture,
      dependency CVEs, client-side token handling). Both follow the
      event-summary-page precedent: the spec doc holds scope, method,
      and a findings log; the backlog carries a pointer. Both added to
      v1.0 scope, with the security review sequenced ahead of the MCP
      OAuth work. Also recorded the personal-location-data guiding
      principle and parked iRacing ingestion under a new v3 section.
- [x] 2026-08-03 — Information security due diligence review (v1.0
      item, partially - 2 items need your action, see still-open entry
      above). Full findings log + one-page threat model written into
      `docs/specs/security-review.md`, verified against deployed
      Azure/GitHub state rather than docs/intent - firewall rules,
      RBAC role assignments (`az role assignment list`), SQL database
      principals and role memberships (queried live), Function App
      CORS config, Container App ingress config, Storage account
      network/encryption settings, actual HTTP response headers
      (`curl -I` against the live SWA), `pip-audit`/`npm audit`, and a
      full-git-history grep for common secret patterns. 13 findings
      logged (3 High, 2 Medium, 3 Low, 1 accepted-risk, 4
      Informational). Fixed directly during the review, low-risk and
      already verified: dropped an orphaned, undocumented
      SQL-authenticated database user `mcp_reader` (created
      2026-07-03, `db_datareader`, predates the MCP server's
      managed-identity setup, currently inert only because
      `azureADOnlyAuthentication=true` blocks all SQL/password
      logins - confirmed against Microsoft Learn); replaced the real
      Azure Maps client ID and real SQL/storage resource names in
      `local.settings.json.example` with placeholders (repo confirmed
      **private** via the GitHub API, so this was hygiene, not a live
      leak). Fixed in source, needs a deploy to take effect live:
      `cryptography>=48.0.1` floor added to both requirements files
      (`pip-audit` found GHSA-537c-gmf6-5ccf, CVSS 7.5, in the
      transitive `PyJWT[crypto]`/`python-tds` chain); explicit `scp`
      claim check added to `ingest/api_auth.py`'s
      `validate_bearer_token()` (it verified signature/audience/
      issuer/expiry correctly but never actually checked the token
      carried the `access_as_user` delegated scope); CSP + X-Frame-
      Options added to `dashboard/staticwebapp.config.json` (SWA's
      platform defaults already covered HSTS/nosniff/referrer-policy,
      confirmed live via `curl -I`, but nothing restricted script
      sources or framing, and MSAL caches tokens in `localStorage`).
      Biggest finding, NOT fixed here: `driver_id` exists on
      `dbo.sessions` (added Block 5) but is never used for
      authorization anywhere in `ingest/queries.py`/`function_app.py`
      - combined with the CIAM `SignUpSignIn` flow allowing
      self-service email+password registration, any account someone
      creates gets full read/write access to all personal telemetry.
      Low exploitability today only because the dashboard URL isn't
      published anywhere; the v1.0 docs-baseline/portfolio item risks
      publishing exactly that URL. Tried to fix the CIAM user-flow
      restriction directly via Graph API (same pattern as the earlier
      Block 5 work) but hit `AADSTS530035` requiring interactive
      device-code sign-in for that tenant - needs you. Also confirmed
      clean, no action needed: managed-identity story holds
      end-to-end against deployed reality (not just `sql/*.sql`
      intent) - Function App MI has exactly `Storage Blob Data
      Contributor` scoped to `racechronoraw` + `Azure Maps Data
      Reader` scoped to `maps-track-telemetry` + SQL
      `db_datareader`/`db_datawriter`; MCP Container App MI has SQL
      `db_datareader` only; `@require_auth` present on all 13
      read/write routes (enumerated every route in `function_app.py`);
      no DB connection happens before token validation; CORS scoped
      to exactly the SWA origin; SQL server is Entra-only auth with
      TLS 1.2 minimum; full git-history secret grep found nothing
      beyond the already-known/now-fixed Maps client ID.
- [x] 2026-08-03 — Backfill tooling: refresh-in-place re-ingest for
      historical sessions (v1.0 item, partially - see still-open entry
      above for remaining CSVs). Problem: the two pre-automation
      RaceChrono CSVs in `data/` were already loaded as session_id 1
      and 2 (manually, before weather/segment-times/car_id existed),
      so simply running them back through the normal `load()` insert
      path would have created duplicate session rows rather than
      enriching the originals. `ingest/racechrono_parser.py` gains
      `find_existing_session(cnx, event_id, source_filename)` (matches
      on the exact original filename, which `source_file` already
      stores) and `refresh(cnx, session_id, ...)`, which deletes and
      re-inserts a session's `segment_times`/`corner_metrics`/`laps`
      (respecting FK dependency order - no `ON DELETE CASCADE` in the
      schema) and updates `sessions.weather*`/`car_id` in place,
      leaving `session_id`/`session_number`/`source_file` untouched.
      `car_id` uses `COALESCE(?, car_id)` and a failed weather refetch
      (`weather.EMPTY`) is never written over a previously-successful
      one, so re-running `refresh()` can't clobber data set by other
      paths (e.g. the dashboard's car-assignment PATCH). `load()`'s
      insert logic was factored out into a shared `_insert_children()`
      used by both. New CLI mode `--backfill`: resolves `event_id`
      from the CSV via the existing `resolve_event_id()` if
      `--event-id` is omitted, then calls `refresh()` if a session
      already exists for that `(event_id, filename)` or `load()` (with
      `next_session_number()`) if not - one flag handles both historical
      re-ingestion and genuinely-new CSVs. Verified against live prod
      (not a dry run): added a firewall rule for the devcontainer's
      current IP, connected with `DefaultAzureCredential` via the
      already-`az login`'d CLI session (no interactive browser flow
      needed this time - simpler than the DeviceCodeCredential path
      used previously), then ran `--backfill` on both
      `data/session_20260516_140619_njmp_lightning_v3.csv` (event 1)
      and `data/session_20260613_095533_njmp_thunderbolt_v3.csv`
      (event 2). Both matched their existing session by filename and
      refreshed: session 1 gained weather ("Clear", 77.4°F) and kept
      its existing `car_id` (Integra) untouched, session 2 gained
      weather ("Clear", 79°F); `list_sessions` before/after showed the
      same 8 session rows throughout (no duplicates created). Re-ran
      `--backfill` on session 1's CSV a second time to confirm
      idempotency - same session_id, same data, no duplicate. What's
      NOT done: the actual backfill of the *other* historical CSVs,
      which live outside this devcontainer and haven't been
      transferred into `data/` yet - tracked in the still-open entry
      above.
- [x] 2026-08-02 — Dashboard: optimal lap time per session (v1.0
      item). `ingest/queries.py` gains `optimal_lap_ms()` (sums each
      segment_order's best `segment_time_ms` across a session's valid
      laps) and wires it into both `session_summary()` (adds
      `optimal_lap_ms`/`optimal_lap`/`gap_to_optimal_ms`, all `None`
      if the session predates segment_times) and `list_sessions()`
      (adds `optimal_lap_ms`/`optimal_lap` via the same OUTER APPLY
      pattern the existing best/avg-lap columns use). Session
      drill-down (`SessionDetailPage.tsx`) gains "Optimal lap" and
      "Left on table" stat tiles alongside the existing three; the
      event view's placeholder sessions table
      (`EventSummaryPage.tsx`) gains an "Optimal lap" column — the
      full hero-tile rebuild of that page is separately spec'd and
      v1.x-gated (`docs/specs/event-summary-page.md`), so this only
      extends the still-live placeholder, not a preview of that spec.
      Verified against a throwaway real-data session (segments kept
      this time, not deleted first): `queries.session_summary()` and
      `list_sessions()` both returned the correct optimal
      (1:29.161) and gap (2076ms), matching the local
      `compute_segment_times()` result from the prior item exactly.
      `tsc --noEmit` clean. Real authenticated in-browser check isn't
      automatable here (Entra sign-in requires an interactive user —
      see `block5_auth_progress` memory), so instead rendered the new
      StatTiles/column with the real verified values via a throwaway
      unauthenticated preview route + a local Playwright screenshot
      (light and dark), confirmed layout/styling, then deleted the
      preview route/file before committing — nothing shipped. Redeployed
      `func-track-telemetry-ingest` (query changes) and rebuilt +
      redeployed `swa-track-telemetry-dashboard` (SWA CLI) to prod.
      Cleaned up the throwaway session afterward.
- [x] 2026-08-02 — Per-segment (corner-to-corner) times at ingestion
      (v1.0 item, prerequisite for the optimal-lap dashboard item
      below). New `sql/16_segment_times.sql`
      (`dbo.segment_times`: lap_id, segment_order 1..N+1, to_corner_id
      [NULL on the final segment], segment_time_ms). New
      `racechrono_parser.py` functions: `_closest_approach_time()`
      (parabolic interpolation around each corner's closest-approach
      sample, giving a sub-sample-precision crossing time at a FIXED
      physical gate — the apex — rather than the per-lap min-speed
      sample the 2026-07-24 note warned off) and
      `compute_segment_times()` (builds the full per-lap gate chain,
      skipping a lap entirely if any corner's zone wasn't reached or
      if the interpolated gates come out non-chronological, rather
      than storing a partial/wrong chain). Segment boundaries reuse
      `compute_laps()`'s own first-sample-of-next-lap convention for
      the lap start/end, so a lap's segment_time_ms values sum to its
      existing lap_time_ms exactly (verified, off by ≤1ms rounding) —
      needed so "optimal lap" and "actual best lap" are on the same
      time basis later. Wired into `load()` (new optional `segments`
      param) and both call sites (CLI `main()`, `POST /api/ingest`).
      Verified against both real CSVs before touching prod: Lightning
      (7/7 laps fully covered, optimal-vs-best gap 2.08s) and
      Thunderbolt (8/8 laps, gap 2.93s) — both in the "credible ~3s"
      range the note called out, vs. the old approach's 13.3s bug,
      confirming the fixed-gate/interpolation method actually fixes
      it and isn't just algorithmically different. Applied the
      migration to the live DB, redeployed
      `func-track-telemetry-ingest`, then ran a throwaway `dry_run=0`
      load over real HTTP (`session_number=98`) — `segment_count: 77`
      (7 laps × 11 segments) matched the local computation exactly —
      before deleting the throwaway session/laps/corner_metrics/
      segment_times rows and their two archived blobs.
- [x] 2026-08-02 — Auto-fetch session weather at ingestion (v1.0
      item). New `ingest/weather.py` (stdlib-only: urllib + json, kept
      out of `racechrono_parser.py`'s top-level imports so its
      pyodbc/azure-free dry-run path stays intact — pulled in with a
      lazy import) queries Open-Meteo's free/keyless historical
      archive API for temperature, humidity, wind, precipitation, and
      a WMO-code weather summary, at the hour nearest the session's
      first GPS timestamp. `racechrono_parser.py` gains
      `fetch_session_weather()`, called from `load()`: it averages the
      event's track corner apex coordinates (from the already-fetched
      `fetch_corners()`) as the query point, and swallows any failure
      (missing coords, API timeout/error) down to an
      all-`None` result rather than blocking the ingest — a flaky
      external call should never break a session upload.
      `sql/15_session_weather.sql` adds `humidity_pct`, `wind_mph`,
      `precip_in`, `weather_observed_at` to `dbo.sessions` (`weather`
      and `air_temp_f` already existed as unused manual-entry
      columns, now auto-populated too). Verified against live prod:
      applied the migration to the real DB, redeployed
      `func-track-telemetry-ingest`, then ran the real Lightning CSV
      through a throwaway `dry_run=0` load (`session_number=97`) over
      HTTP — confirmed `weather='Clear', air_temp_f=77.4,
      humidity_pct=43, wind_mph=8.3, precip_in=0,
      weather_observed_at=2026-05-16 18:00` landed on the row, matching
      a local direct-call test against the same CSV — then deleted the
      throwaway session/laps/corner_metrics and its two archived
      blobs. Exposing the new columns through the dashboard/API is
      deliberately out of scope here — that's the existing v1.x
      "Dashboard weather section" item, which already notes it
      consumes humidity + observation time.
- [x] 2026-08-02 — Verify /api/ingest still works end-to-end, then add
      a car prompt (v1.0 item closed). Server-side auto-resolution
      landed 2026-07-31 (event_id/session_number/car_id, no prompts
      needed) and was curl-verified against prod then; the remaining
      piece — running the rebuilt 3-action Shortcut from the
      Shortcuts app on a real phone — is now confirmed working
      end-to-end (share-sheet upload succeeds with no prompts).
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
- [x] 2026-07-25 — Spec: event summary page
      (`docs/specs/event-summary-page.md`), approved by AC via an
      interactive mockup in chat. Defines the real
      `/events/:eventId` dashboard that replaces the placeholder:
      header + badges, four hero tiles, sessions table, first-vs-last
      corner-delta table, weather strip, explicit exclusions, the
      `GET /api/events/{id}/summary` endpoint shape, and the
      timing-screen design language. Build is v1.x and gated on
      v1.0's segment-times + optimal-lap work.
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
- [x] 2026-07-30 — Consumable replacement history + reset-to-100%.
      Life% was already computed only from sessions/months on or
      after `install_date` (sql/08_consumables.sql), but there was no
      way to log a real-world replacement (new pads, a fluid flush, an
      oil change) other than hand-inserting a row, and `get_consumables`
      had no active/inactive concept — a manual insert would just leave
      two rows for the same item forever, one permanently stuck
      overdue. `sql/14_consumables_history.sql` adds `active BIT
      DEFAULT 1` and `previous_consumable_id` (self-FK) to
      `dbo.consumables`. New `queries.replace_consumable`: retires the
      current row (`active = 0`) and inserts a fresh one carrying over
      `item_name`/`service_life_*`/`car_id`, dated today (or a supplied
      date), linked back via `previous_consumable_id` — so remaining
      life recomputes from the new row's own `install_date` and reads
      100% immediately, while the full service history per car stays
      in the table (never deleted). `get_consumables` now filters
      `WHERE active = 1`. New `POST /api/consumables/{id}/replace`
      (`{install_date?, install_session_id?, notes?}`), same
      `@require_auth` pattern. `ConsumablesPage.tsx` gets a "Log
      replacement" control per row (date + notes, defaulting to today)
      that calls the new endpoint and refetches. Verified against the
      live DB: migration applied (two ALTERs, run as separate batches
      again), then a throwaway consumable row was inserted, run through
      `replace_consumable`, and deleted afterward — confirmed the old
      row flips to `active = 0`, the new row links via
      `previous_consumable_id` and reads 100%/not-overdue, and
      re-replacing an already-inactive row raises. Confirmed the four
      real Integra rows were untouched throughout. `func start`
      confirmed the new route registers and 401s with no token, same
      as the existing routes. Redeployed both
      `func-track-telemetry-ingest` (15 routes now, including the new
      `replace` route) and `swa-track-telemetry-dashboard` to prod;
      prod `/api/consumables` and the new replace route both 401
      with no token, dashboard root 200s.
- [x] 2026-07-30 — Fix issue #1: MCP server redeploy (v1.0 blocker).
      Confirmed current `main` already fixed the reported bug (queries
      join `dbo.run_groups` now, no bare `run_group` column reference)
      — the fix was purely a stale image. `az containerapp up --source .`
      rebuilt and pushed a new image, but the app turned out to be in
      **Single** revision mode, and the new revision never passed its
      health check, so Container Apps kept routing to the old (broken)
      revision automatically — my first MCP client test call actually
      landed on the *old* revision and reproduced the exact
      `Invalid column name 'run_group'` bug, which read as if the
      redeploy had done nothing. Manually deactivating the old revision
      to force the issue exposed the real problem: the new revision was
      `CrashLoopBackOff`. Root cause: `mcp_server/requirements.txt` pins
      `mcp` unversioned; a new `mcp==2.0.0` was released since the last
      build (2026-07-21) and it removed/renamed `mcp.server.fastmcp`
      (now `mcp.server.mcpserver.MCPServer`), so `server.py`'s
      `from mcp.server.fastmcp import FastMCP` import now fails at
      startup — this also bit local ad hoc MCP client testing
      (`streamablehttp_client` renamed to `streamable_http_client` in
      the same release). Pinned `mcp<2.0.0` in
      `mcp_server/requirements.txt` (server.py stays on the FastMCP API
      for now; migrating to `MCPServer` is a separate follow-up, not
      done here) and redeployed again. Verified for real this time:
      watched the new revision hit `Running`/`Healthy` with 100%
      traffic and the old one fully deprovisioned (single revision left
      in `az containerapp revision list`), then called all four tools
      (`list_sessions`, `get_session_detail`, `get_corner_metrics`,
      `compare_laps`) against the live endpoint with a real MCP client
      and got real data back for each. Lesson for future container app
      redeploys here: don't trust the deploy command's "Congrats!"
      output or a single warm-up curl — check
      `az containerapp revision list` for `Healthy`/`Running` and do a
      real functional call before calling it done, since single-
      revision-mode silently keeps serving the last-good revision while
      a bad one fails in the background.
- [x] 2026-07-30 — Verify /api/ingest end-to-end + accept car_id
      (server side). `load()` (`ingest/racechrono_parser.py`) gains an
      optional `car_id=None` param, inserted into `dbo.sessions` at
      load time; `POST /api/ingest` (`function_app.py`) parses an
      optional `car_id` query param (matching the `event_id`/
      `session_number` pattern, no validation beyond "is it an int" —
      same as those two) and passes it through; also echoed in the
      JSON response summary. CLI (`racechrono_parser.py main()`) gets a
      matching `--car-id` flag for parity. `docs/ios_shortcut.md`
      updated: new step 4 "Ask for Input" (`CarID`, default `2` for the
      Integra) between `DryRun` and the URL-building step, URL
      template gets a `car_id=` chip, step numbering and the "answer
      the N prompts" test-instructions line updated (3 -> 4). Verified
      against live prod (not just dry-run): redeployed
      `func-track-telemetry-ingest` first, then a `dry_run=1` POST with
      a real CSV (`event_id=1`, `car_id=2`) returned the full expected
      summary (track name, 52717 samples, 7 laps, 10-corner coverage,
      `car_id: 2` echoed back) confirming the whole parse/corner-
      lookup/blob-upload path survived every redeploy since the last
      real exercise. Then a real `dry_run=0` load (`session_number=99`,
      a throwaway value — session_number is `TINYINT`, so `999`
      overflowed on the first attempt) wrote session_id 12 with 7 laps
      and 70 corner_metrics; a direct query confirmed
      `sessions.car_id = 2` on that row before deleting the test
      session/laps/corner_metrics. What's NOT verified here: the actual
      iOS Shortcut share-sheet flow on a real phone with the new 4th
      prompt — that's a manual on-device step, tracked as the remaining
      half of the still-open backlog item above.
- [x] 2026-07-31 — Drop all Shortcut prompts: POST /api/ingest now
      auto-resolves event_id, session_number, and car_id instead of
      requiring them as query params. `ingest/racechrono_parser.py`
      gains `resolve_event_id()` (matches the CSV's `Track name` +
      `Created` date against `dbo.events`, erroring with a clear message
      if zero or multiple events match) and `next_session_number()`
      (`MAX(session_number)+1` for the resolved event);
      `parse_session_date()` factored out of `load()` so both share the
      same date-parsing logic. `function_app.py` calls these only when
      the query param is omitted (still overridable via
      `event_id=`/`session_number=`/`car_id=` for edge cases) and
      defaults `car_id` to a new `DEFAULT_CAR_ID = 2` (the Integra)
      constant. `dry_run` and `filename` prompts were already optional
      query params, just never exposed in the Shortcut.
      `docs/ios_shortcut.md` rewritten: the Shortcut is now 3 actions
      (URL → Get Contents of URL → Show Result) with a literal, static
      URL — no "Ask for Input" actions at all. Verified against live
      prod: redeployed `func-track-telemetry-ingest`, then a bare
      `dry_run=1` POST (no event_id/session_number/car_id/filename) of
      the real Lightning CSV correctly resolved `event_id: 1,
      session_number: 4, car_id: 2` — matching event 1's actual next
      unused session number and the Integra's car_id — confirming the
      auto-resolution logic works end-to-end through the real HTTP path,
      not just locally. Still open: exercising the rebuilt Shortcut
      itself from the Shortcuts app on a real phone (manual, on-device).
