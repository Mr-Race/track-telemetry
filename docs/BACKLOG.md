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

## Known gaps and accepted risks
Things believed correct but not *proven* correct, plus decisions
deliberately deferred. Kept here because WAY-OF-WORKING §1 says a
decision that only exists in a chat doesn't exist — and an unproven
assumption is the same kind of thing. Reviewed 2026-08-10.

**Verification gaps** — shipped and believed working, never observed:
- The 500 error envelope has never been triggered in production. Auth
  runs first, so forcing one needs a valid token. Verified statically
  (no `str(exc)` remains in any 500 branch) and by unit test only.
- The ingest **duplicate path** has never run end-to-end against prod.
  The content-hash lookup, the refresh-vs-load branch and the DB
  constraint are each verified individually, but nothing has actually
  POSTed the same CSV twice to the live endpoint. First real exercise
  will be the historical backfill — watch it there.
- The `accelerator_pos` test fixture is **synthetic**. It proves the
  name-resolution logic, not that a real PID-0x49 export parses.
  Blocked on getting `session_20260810_071257_v3.csv` off the phone.

**Live UX problem, measured 2026-08-10:** the first requests after the
database has auto-paused take **~47 seconds** (48.7s, 47.7s, 46.7s
measured on `list_sessions`, `list_tracks`, `get_consumables`). The
free-tier serverless DB resumes in 30-60s, and because a new connection
is opened per request (issue #16) each concurrent call pays it
separately rather than sharing one resume. To a user this is
indistinguishable from the app being broken — it is what made the auth
incident look unresolved after it had been fixed. Fixing #16 would let
one resume cover the page; a keep-warm ping or a loading state that
says "waking the database" would address the perception.

**No JavaScript test runner.** The dashboard has none, so
`restoreActiveAccount()` — written to take its instance as a parameter
precisely so it could be stubbed — is untested, and CI's lint/typecheck/
build would not catch a repeat of the auth bug. The whole class of
client-side auth failure is currently untestable.

**Coverage gaps:**
- `ingest/queries.py` has no tests at all — ~800 lines of SQL, and the
  single largest untested surface. Needs a throwaway DB or a much
  larger stub; judged the wrong trade so far, but it is a real hole.
- ~~Nothing runs the tests on push~~ — closed 2026-08-10, CI now gates
  pytest, lint, typecheck and build. Two things it still does **not**
  cover: the migration *drift* check needs live DB access behind an IP
  allowlist and stays a manual pre-deploy step, and nothing verifies
  production after a deploy — the PR template carries that checklist
  but a checklist is not a gate.
- ~~Secret scanning / push protection unverified~~ — **all confirmed
  enabled 2026-08-11** (secret scanning, push protection, CodeQL code
  scanning, Dependabot). The framework's setup checklist is satisfied.
  Note when re-checking: on Settings -> Code security the button reads
  *Disable*, which is the action available, not the status — it means
  the feature is on.
  Worth calibrating rather than over-trusting: push protection matches
  *known provider patterns* (AWS/GitHub/Azure-style keys) only. It
  would not stop a hand-rolled connection string or the contents of
  `local.settings.json` — the `.gitignore` entries do more real work
  there — and it has no view at all of this repo's actual incident,
  which was security findings in public issues rather than credentials
  in code. `SECURITY.md` and the issue template are the controls for
  that.
- ~~Private vulnerability reporting disabled~~ — enabled 2026-08-11, so
  `SECURITY.md`'s "open a private advisory" instruction now points
  somewhere real rather than at a locked door whose fallback was a
  public issue. Unlike the rest of the security settings, this one is
  verifiable without admin auth:
  `curl -s https://api.github.com/repos/Mr-Race/track-telemetry/private-vulnerability-reporting`
  returns `{"enabled": true}`.
- ~~No migrations ledger~~ — closed 2026-08-10, see Done.

**Undecided, deliberately:**
- Whether `event_summary()` should order sessions by `start_time`
  rather than trusting `session_number` (own item below).
- Whether malformed-row drops should fail the request past a threshold
  (e.g. >1%). Counts are now reported; the threshold is unset because
  guessing one risks rejecting a good upload at a track day.

**Security:** tracked in `.local/security-findings.md` (gitignored —
this repo is public) as S-1..S-4, with their own residual-gap notes.
S-1..S-3 are fixed and deployed; S-4 (unpinned Python deps) is open.

**Environment gotchas that cost time — check here first:**
- `az monitor` fails to load on this CLI version; use `az rest` against
  ARM instead. Same class of bug as `az maps account create`.
- The serverless DB auto-pauses; the first connect after a pause times
  out and must simply be retried.
- `npm ci` removes the unsaved `playwright-core` used for screenshot
  and smoke tests — reinstall with `--no-save` to keep manifests clean.
- Azure SQL firewall rules are per-IP and the devcontainer's IP is
  ephemeral; re-add it when connections time out immediately.

## v1.0 — finish to launch
The cut line: completes the analysis story (every session ever
driven, ingested and enriched, with optimal laps, fully secured)
plus the docs baseline and the two pre-launch reviews. Nothing else
blocks 1.0.
- [ ] **Mobile/responsive pass across the dashboard** (added 2026-08-09
      per AC). Hard requirement: **the page scrolls vertically only —
      never sideways.** Wide content (tables) may scroll horizontally
      *inside its own container*, but `document.body` must never exceed
      the viewport width at any supported size.
      This is a real gap, not a polish item: `dashboard/src/index.css`
      currently contains **no width breakpoints at all** — the only
      `@media` in the file is `prefers-color-scheme`. Every layout is
      whatever the desktop rule produces, squeezed. (`index.html`'s
      viewport meta is correct, so this is purely CSS/layout.)
      Known culprits, from screenshots taken at 420px on 2026-08-09
      while building the event page:
      - `header` is a non-wrapping flex row holding the `h1`, a 6-link
        `nav`, and the auth control. At phone widths the last nav item
        ("Cars") runs under the "Sign in" button. Needs to wrap, or
        collapse to a menu.
      - `.data-table` is `width: 100%` but several tables carry 4-5
        columns, and the event page deliberately adds `white-space:
        nowrap` to session cells, corner labels, and date ranges (a
        wrapped label breaks the timing-screen row rhythm). Those
        tables need an `overflow-x: auto` wrapper so the *table*
        scrolls, not the page.
      - `.hero-grid` is a fixed 2-column grid; check it at ~320px,
        where the big display-face tile values may overflow their tile.
      Scope: audit every route (`/`, `/sessions`, `/sessions/:id`,
      `/tracks`, `/tracks/:id`, `/events`, `/events/:id`,
      `/consumables`, `/cars`) at ~320/390/420px and at tablet width,
      then fix. Worth an automated guard once fixed — assert
      `scrollWidth <= clientWidth` on `document.documentElement` per
      route in the Playwright pass described in the 2026-08-09 event
      page entry, so a future wide element fails loudly instead of
      being found by eye. Note `overflow-x: hidden` on `body` is NOT
      the fix — it hides the symptom and silently clips content.
- [ ] **First-request latency after the DB auto-pauses (~47s)** —
      promoted from v1.x (issue #16) on 2026-08-11 because it fails
      v1.0's own bar of *no known broken pieces in prod*. Measured, not
      estimated: 48.7s / 47.7s / 46.7s on `list_sessions`, `list_tracks`
      and `get_consumables`. The free-tier serverless DB resumes in
      30-60s and, because a new connection is opened per request, every
      concurrent call pays it separately instead of sharing one resume.
      To a user this is indistinguishable from the app being broken —
      it is exactly what made the 2026-08-10 auth incident look
      unresolved after it had been fixed. Fix #16 so one resume covers
      the page, and say so in the UI rather than showing silence.
- [ ] **Parser must accept the `accelerator_pos` OBD channel**
      (GitHub issue #8, raised 2026-08-10 — tracked there in full,
      summarized here because it gates the backfill item below).
      **PARTLY LANDED 2026-08-10 (not deployed).** Done: name
      resolution in `parse_csv` (accepts either channel, prefers
      `accelerator_pos`); OBD channels and skipped-row counts now
      reported in the ingest response and logged; `parse_csv` returns a
      third `diagnostics` value (both callers updated); first pytest
      suite covering all three OBD cases. **Remaining: (a) the
      calibration constants (18.82/94.90) still need somewhere to live
      — they want a vehicle-config concept that doesn't exist yet, and
      normalization happens on read, not at ingest; (b) the
      `accelerator_pos` test fixture is synthetic, so it verifies the
      resolution logic but not the real file's exact shape — needs
      `session_20260810_071257_v3.csv` off the phone. **Deployed
      2026-08-10** (rode along with the security-fix deploy, since
      `func publish` ships the whole app).
      `parse_csv` looks up only `throttle_pos` (source `200: obd`):
      `for name in ("rpm", "throttle_pos")`. After RaceChrono was
      reconfigured to log true pedal position (PID 0x49), exports name
      the column **`accelerator_pos`**, so the lookup misses,
      `obd_value()` returns None, and
      `corner_metrics.throttle_pos_apex_pct` silently writes NULL for
      every corner of every session — no error, no warning. Verified
      against a real export (`session_20260810_071257_v3.csv`).
      **Why it's v1.0 and not v1.x:** it blocks "Backfill historical
      sessions" below — re-ingesting the archive with a parser that
      can't read the channel would bake NULLs into the entire history.
      Fix is name resolution at parse time only: accept either name,
      prefer `accelerator_pos` when both are present (true pedal
      position beats throttle plate — undistorted by traction control
      or torque limiting, 40 Hz, wider usable range). **No data
      mutation** — historical exports keep `throttle_pos`, nothing in
      Blob is touched, and the backfill re-ingests archived originals
      unchanged, per the raw-data-is-sacred principle.
      Also required: an upload with **no OBD data at all** (dongle not
      paired, Bluetooth dropped, left at home) must still ingest
      normally — laps, corner metrics and segment times all derive
      from GPS. That path is documented as graceful but has never been
      tested, and it's now the failure mode most likely to hit at a
      track day. The ingest response should state which OBD channels
      were found, so a missing dongle is visible at upload time rather
      than discovered weeks later in the data — same fix as the
      engineering review's finding #8 (silently dropped rows), so do
      them together.
      Needs fixtures for all three cases (`accelerator_pos`,
      `throttle_pos`, neither) — feeds the test-suite issue #11. Note
      the new export isn't in `data/` yet (same phone/laptop blocker as
      the backfill item); the no-OBD case can be synthesized from the
      two exports already there.
      Calibration, measured 2026-08-10: pedal at rest **18.82%**
      (48/255), pedal at the stop **94.90%** (242/255). Store as
      calibration constants on the vehicle config and normalize
      percent-of-travel **on read** —
      `(raw - 18.82) / (94.90 - 18.82) * 100`. Deliberately NOT baked
      into ingest: if the PID ever changes, historical sessions would
      double-correct. (RaceChrono's gauge and the car's dash both show
      100% at full pedal; that's UI normalization, not the raw signal.
      The CSV ceiling of 94.90 is the real one.)
- [ ] **Backfill historical sessions** — the refresh-in-place
      `--backfill` CLI mode exists now (see Done, 2026-08-03) and has
      been run against the two historical CSVs already in `data/`
      (sessions 1 and 2). Remaining: more pre-automation RaceChrono
      CSVs exist outside this devcontainer (phone/laptop) and still
      need to land in `data/` before `--backfill` can be run against
      them too.
- [ ] **OAuth 2.1 + PKCE via Entra ID on the MCP server** — closes
      the last unauthenticated endpoint. The information security due
      diligence item is now fully closed (2026-08-03, see Done below),
      so this is unblocked.
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
- [x] 2026-08-11 — **Instructor-driven session attributed correctly**
      (GitHub issue #2, the only place the data was actually *wrong*).
      Session 13 was driven by AC's instructor in AC's car but carried
      the default `driver_id = 1` ('Me'), and **nothing in `queries.py`
      filtered on driver at all** — so NJMP Lightning's personal best
      read **1:21.837**, a lap AC never drove, instead of the real
      **1:24.975** (session 9).
      `sql/20` adds an `Instructor` driver, reattributes session 13, and
      records the lap in `dbo.benchmarks` — per AC, it is a legitimate
      reference for what the car can do, and a lap belonging to someone
      who isn't you is precisely what that table is for. Applied through
      the new ledger (`migrate.py --apply`, three GO-separated batches,
      recorded automatically) — the first real use of it.
      `list_tracks` and `get_track_benchmarks` now scope the personal
      best to a driver, taken as a parameter defaulting to
      `ME_DRIVER_ID` so multi-user (v2) resolves it from the
      authenticated user without rewriting the queries.
      **Event hero stats are deliberately NOT driver-scoped** (AC's
      call: "event best" means the fastest lap turned that day by
      anyone), so event 1 still reports 1:21.837. That only stays
      honest if the row says who drove it, so `event_summary` now joins
      `dbo.drivers` and the sessions table labels any session that
      wasn't AC's. The decision and the label are load-bearing on each
      other.
      Verified live: Lightning PB is now 1:24.975 (session 9), the
      Instructor benchmark shows 1:21.837, and event 1's S2 row reads
      `Instructor`. Guarded by tests that assert the driver filter is
      still in the SQL — the parameter alone would look right while
      being ignored.
- [x] 2026-08-11 — Renumbered event 1's sessions chronologically
      (S1, S4, S3 -> S1, S2, S3). Was blocked on issue #2 above:
      reassigning the driver could have changed what belonged in the
      event, so renumbering first would have had to be redone. The
      instructor session is now S2, between the two of AC's, which is
      what actually happened that day.
- [x] 2026-08-10 — **Production incident: signed in, every API call
      401, no data.** Fixed and confirmed (200s in App Insights, zero
      token rejections, zero exceptions).
      Root cause: MSAL only raises `LOGIN_SUCCESS` on a *fresh*
      sign-in, and the event callback in `msalInstance.ts` was the only
      thing setting the active account. On a page reload the session is
      restored from cache and no event fires, so nothing set it. The
      two ideas of "signed in" then disagreed —
      `useIsAuthenticated()`/`AuthenticatedTemplate` look at ALL
      accounts so the UI rendered as signed in, while
      `getAccessToken()` asks for the ACTIVE account, got null, and
      sent every request with no Authorization header.
      Latent, not a regression: `msal-browser` was untouched that day.
      It surfaces whenever a session is restored from cache rather than
      created fresh, which is why signing in again worked around it.
      Fixes: `restoreActiveAccount()` adopts a cached account at boot
      (after `initialize()`, before first render), plus a
      `getAllAccounts()` fallback in `getAccessToken()`.
      **The diagnosis came from the morning's Application Insights
      work.** `api_auth.py` logs "bearer token rejected" when a token
      is sent and fails; there were exactly two entries all day, both
      from my own probe tokens at 15:27. No real token had ever been
      rejected, which ruled out the server and pointed at the client.
      Before that wiring the same question was unanswerable.
      **Second defect found on the way, arguably worse than the first:**
      `getAccessToken()` returned `null` on *any* token failure, so
      every possible cause produced one identical symptom — no header,
      bare 401, no explanation. That is why the first fix could not be
      confirmed or ruled out. It now throws with the MSAL error name
      and message, and MSAL's own logger is enabled at error/warning
      with PII off. A failure to get a token is an error, not an empty
      result.
      Honest limit: with both fixes deployed close together and CDN
      propagation in between, **which one restored service was never
      isolated.** Both are correct independently, so this was not
      chased further.
- [x] 2026-08-10 — Event sessions now order by `start_time`, not
      `session_number` (AC's decision). The page's premise is the arc
      of a day — progression and the corner story compare first to last
      — so what matters is which ran first, not which was numbered
      first. NULLs sort last (a session with no start_time has no
      position in the day), `session_number` is the tie-break.
      The worry when this was deferred was that ordering by time would
      *hide* a numbering problem rather than surface it. It doesn't:
      rows are still labelled `S<n>`, so bad numbering now shows on
      screen as `S3, S1, S2` instead of producing a quietly wrong
      number. Correct computation and a visible anomaly, not a trade.
      **It found a second instance immediately.** Event 1 is numbered
      S1, S4, S3 in time order, so its progression tile had been
      measuring 14:11 -> 09:51 against a session that wasn't the day's
      last. Now -1.684s, 14:11 -> 15:52. Event 3 had been fixed by
      renumbering earlier the same day; nobody had thought to check
      whether it was the only one. Left as an open item rather than
      renumbered, because one of event 1's sessions is the
      instructor-driven one in issue #2.
      Not unit-tested: the ordering lives in SQL and `queries.py` has
      no coverage (a known gap). Verified against the live DB across
      all four events instead, asserting chronological order and
      flagging label anomalies.
- [x] 2026-08-10 — CI, and making the practices front-facing (issue
      #14). Prompted by AC asking whether the infosec and engineering
      practices were actually *embedded* — the honest answer was no.
      Five findings had been closed, but nearly everything built to
      close them was a **detector, not a gate**: 109 tests, a linter, a
      typechecker and a drift checksum that only fired when someone
      remembered. That is the same failure the review diagnosed, one
      level up.
      `.github/workflows/ci.yml` now runs pytest, oxlint, tsc and the
      vite build on every push and PR, plus a `git diff --exit-code`
      check that the build leaves tracked files alone. Verified green
      on the first run rather than assumed — a CI that fails on arrival
      teaches people to ignore it. Each step was dry-run locally first,
      including confirming oxlint exits 0 on the pre-existing warning
      and that `dist/` is gitignored so the diff check can pass.
      Deliberately not in CI: the migration drift check needs live DB
      access behind an IP allowlist. The parts needing no database -
      ordering, GO-splitting, duplicate numbers - are in the test suite
      and so do gate.
      `SECURITY.md` states the rule where someone looks *before* filing
      rather than only inside a review document, and records why it
      exists. The issue-template chooser links to it before a blank
      issue can be opened, and the template asks the question
      explicitly. The PR template carries the §5 verification checklist
      so "enumerate, don't spot-check" and the container cold-start
      step stop living in the Done log and in memory. `README.md` now
      links WAY-OF-WORKING, BACKLOG, SECURITY and the migration
      runbook - the framework says to read it first in any session, and
      nothing pointed at it from the entry point.
      Found while verifying: **CodeQL code scanning is already enabled**
      (a "Push on main" workflow analyses Python and TypeScript on every
      push, via GitHub's default setup, with no file in the repo).
      Dependabot is confirmed too. Secret scanning and push protection
      could **not** be verified - both API endpoints need repo-admin
      auth - so they are recorded as an open gap rather than assumed.
- [x] 2026-08-10 — **Engineering practices assessment CLOSED** — the
      v1.0 review gate. Review completed 2026-08-09 (22 findings: 5
      high, 9 medium, 8 low, in `docs/specs/engineering-review.md`,
      each verified against the repo or the live Azure/SQL resources
      rather than inferred from the docs). All five high-severity
      findings are now fixed, deployed and verified:
      #1 no tests (93 now), #2 no Application Insights, #3 no ingest
      idempotency, #4 TypeScript `strict` unset, #5 no migration
      tracking. The three security-relevant findings (S-1..S-3, held
      in `.local/`) are also fixed and deployed.
      Medium/low findings remain as v1.x issues — unpinned Python deps
      with no lockfile (#13), no CI (#14), per-request DB connections
      never closed (#16), and the rest.
      The review's own conclusion held up: the design judgement was
      sound and the documentation unusually strong; the gap was
      *verification* — everything confirmed by a human looking once,
      nothing re-checking itself. That is what the five fixes changed.
      Two corrections worth keeping. Finding #4's justification was
      wrong as filed (see the correction section in the review doc):
      it credited `strict` with catching the `min_speed_mph` crash,
      but that field was typed non-null, so strict would have accepted
      it too — enabling it produced zero errors, making it a cheap
      guard rather than a defect being masked. And filing the
      security-relevant findings as public GitHub issues was a
      mistake, since this repo is public; they were moved to `.local/`
      the following day.
- [x] 2026-08-10 — Migration ledger (issue #12, engineering review
      finding #5) — **the last of the five high-severity findings, so
      the engineering practices gate is now closed.**
      `dbo.schema_migrations` (filename, sha256, applied_at,
      applied_by) plus `sql/migrate.py`: status / `--apply` /
      `--baseline`, applying in numeric order, splitting on `GO`, and
      reporting drift. `sql/README.md` is the runbook. Deliberately not
      a framework — no down-migrations (a small DB with an archive of
      raw source beats a reverse script nobody has tested) and no
      transaction around the whole run, since DDL batches and `GO`
      don't compose into one.
      **Writing the tests found two real problems in `sql/` itself.**
      First, `07` is used by two files, so "apply everything pending"
      had no defined order between them; both were long applied so
      they are left alone, `discover()` now tie-breaks on filename, and
      the runner warns on any *new* duplicate. Second, and worse:
      `11`, `13` and `17` each add a column and then use it, with no
      `GO` — the exact failure that had to be fixed by hand at apply
      time, twice. They would have failed for anyone rebuilding from
      scratch, since these files are the only definition of the schema.
      Separators added, which also closes issue #21, and a test now
      asserts those migrations are multi-batch.
      Fixing them *before* baselining was the point: editing an applied
      migration is precisely what the checksum flags as drift, and the
      adoption window was the only moment it was legitimate.
      The baseline was verified rather than assumed — recording a file
      as applied when it wasn't would write a false record into the one
      thing meant to prevent that. 23 object-existence checks across
      the 20 migrations, all passing, before recording anything.
      Drift detection was then proved end-to-end: appended a comment to
      an applied migration, confirmed it reported as DRIFT with both
      checksums, restored it, confirmed clean.
- [x] 2026-08-10 — Parser core under test: suite grown 22 -> 93 tests,
      covering every target the engineering review's finding #1 named
      (`compute_laps`, `compute_corner_metrics`, `compute_segment_times`,
      event/session resolution, weather parsing, the track-local time
      helpers). Closes the original checklist on issue #11.
      **Writing the tests found three real bugs**, each written failing
      first and then fixed - issues #22, #19 and #23 all closed:
      the "median" was `sorted(durs)[len//2]`, the upper middle value
      for an even lap count, which biased the validity threshold
      lenient; `compute_corner_metrics` took entry/exit from
      `inside[0]`/`inside[-1]` without sorting by elapsed, unlike
      `compute_segment_times` next door, so out-of-order rows silently
      swapped the two speeds; and it flattened every in-zone sample into
      one list, so a layout passing the same apex twice in a lap merged
      both passes.
      All three were latent rather than live, and proving that mattered
      more than the fixes: these functions decide what the pending
      historical backfill will write, so a behaviour change here would
      quietly rewrite history. Recomputed 15 laps, 189 segment times and
      174 corner metrics from the archived exports and compared against
      what the old code stored - **zero differences**. The median moved
      (112.682s -> 112.125s on the even-lap session) without flipping
      any lap, which is exactly the kind of thing worth measuring rather
      than assuming.
      Notes: `resolve_event_id`/`next_session_number`/`track_timezone`
      take a cursor rather than a connection, so a stub covers them with
      no DB - whether `queries.py` gets integration tests against a
      throwaway database is still open and still looks like the wrong
      trade. The weather tests assert the fail-soft property directly
      (network error, missing hour, no corner coordinates), since
      WAY-OF-WORKING §7 holds that up as the reference pattern and it
      had never actually been checked.
      Still missing: no CI runs any of this on push (issue #14).
- [x] 2026-08-10 — Content-hash idempotency on the HTTP ingest path
      (GitHub issue #3, closed). Re-POSTing the same CSV created a
      second session - it happened for real (session 14 duplicating
      session 6, deleted 2026-08-03).
      The obvious fix was to reuse `find_existing_session()`, which
      matches on `source_file` - and it would not have worked. The iOS
      Shortcut sends `filename` only optionally, and without it the
      route invents `session_<epoch>.csv`, unique per upload. Five of
      the seven sessions in the DB carry exactly that generated name,
      so filename matching would never have caught the duplicate that
      actually occurred. Worth remembering as a pattern: the existing
      helper looked like the answer and wasn't, and only checking the
      real data showed it.
      So: `sql/18` adds `sessions.source_sha256` plus a filtered unique
      index on `(event_id, source_sha256)`, applied live in two batches
      per the ALTER/GO rule. A re-upload now refreshes the session it
      already owns, keeping its `session_number` instead of taking the
      next one, and skips the blob write since the original is already
      archived. `refresh()` COALESCEs the hash so a CLI `--backfill`
      refresh, which matches on filename and passes no hash, can't
      blank it. Backfilled hashes for the two sessions whose original
      CSV is in `data/`, so the pending historical backfill is covered;
      verified the lookup round-trips for both, with a negative control.
- [x] 2026-08-10 — Renumbered event 3's sessions into chronological
      order (4,5,6 -> 1,2,3). Leftovers from the duplicate cleanup, and
      out of time order, so the event page's progression tile and corner
      story - both first-vs-last **by session_number** - were comparing
      the wrong pair. Not cosmetic: progression was -1.485s measured
      17:00 -> 18:02, and is actually **-1.841s** measured 17:00 ->
      19:01; the corner story's biggest mover changed from T4 +5.3 to
      T4 +3.3. Best laps now read as a real day arc: 1:26.816 ->
      1:25.331 -> 1:24.975. The renumber script offsets by +100 first
      when the old and new ranges overlap (`UQ_sessions_event_number`
      would collide mid-update); here they were disjoint so it applied
      directly, but the guard stays for the next time.
- [x] 2026-08-10 — Merged the two open dependabot PRs: react-router /
      react-router-dom 7.18.1 -> 7.18.2 (#7) and postcss 8.5.22 ->
      8.5.26 (#6, which carries the "do not load source map without
      opts.from" security fix). Both squash-merged despite being based
      on a commit from 2026-08-07 and both touching the lockfile.
      `npm audit` now reports 0 vulnerabilities, clearing the "1 high,
      1 moderate" GitHub was warning about on every push.
      Verified beyond "it builds": `npm ci`, strict typecheck, lint and
      build all clean, then a browser smoke test, because react-router
      is a *runtime* dependency and a green build says nothing about
      whether routing still works. Confirmed the landing page renders
      and a client-side navigation to a protected route redirects, with
      no page errors. Note `npm ci` removes the unsaved `playwright-core`
      used for that check - reinstall with `--no-save` so the manifests
      stay clean.
- [x] 2026-08-10 — Closed the three security-relevant findings from the
      engineering review (S-1, S-2, S-3 — detail in `.local/`, not here;
      this repo is public). Commit `8dde245`; Function App and MCP
      Container App both redeployed and verified live.
      Verification followed WAY-OF-WORKING §5 (enumerate, don't
      spot-check): all 16 Function routes checked individually and the
      deployed function count reconciled against the 16 `@app.route`
      declarations in source — the "a bad dependency floor silently
      wiped every registered function" failure mode. For the MCP server,
      Container App revision `0000011` confirmed Active/Healthy at 100%
      traffic *and* cold-started with real requests, since a healthy
      revision that is scaled to zero proves nothing about whether the
      image runs. All 14 `queries.py` shapes were exercised against the
      live DB because S-3 changed the code path every query takes.
      **Lesson worth keeping: the first verification query returned the
      answer I wanted for the wrong reason.** Checking that the removed
      debug instrumentation had stopped logging, a search for the literal
      marker string returned zero both before *and* after the deploy —
      which looks like success but actually meant the query matched
      nothing at all. A corrected query found 120 occurrences before the
      deploy (last 2026-08-07) and zero after. A "clean" result is only
      evidence if the same query demonstrably finds the thing when it IS
      present. Always run the negative control.
      Two residual gaps, recorded rather than papered over: the 500-path
      envelope is verified statically and by unit test but was never
      triggered live (auth runs first, so forcing a production 500 needs
      a valid token), and the ~120 pre-fix log entries still sit in Log
      Analytics — the fix stops new leakage but does not purge retained
      history. Purging is an open decision.
- [x] 2026-08-10 — First automated tests in the project's history
      (engineering review finding #1, issue #11 — a first slice, not
      the whole item). `tests/` with pytest, 10 tests, all passing in
      0.03s. Test-only deps live in a new `requirements-dev.txt`,
      deliberately NOT in `requirements.txt`, which is what Azure
      Functions installs at deploy time.
      Fixtures are built in code (`tests/conftest.py`) as small
      synthetic v3 exports rather than committed CSVs — real exports
      are 11-14 MB and `data/` is gitignored under the raw-data-is-
      sacred principle. The synthetic layout mirrors a real file
      including `speed` appearing three times under different sources,
      which is exactly why the parser disambiguates GPS columns by
      source rather than by name.
      Covers the three OBD cases from issue #8 (`accelerator_pos`,
      historical `throttle_pos`, neither), the both-present preference
      ordered so a naive first-match would pick wrong, partial OBD
      (rpm but no pedal), the three skipped-row counters, and the two
      parse-failure paths.
      Validated against reality, not just fixtures: both real exports
      in `data/` parse unchanged through the modified parser, and the
      June session's 8 laps / 7 valid and best lap 1:49.558 match the
      live DB exactly.
- [x] 2026-08-09 — Engineering review findings filed as GitHub issues
      (#9-#28) and the first two high-severity ones fixed.
      **Finding #2, Application Insights (issue #9) — CLOSED.** There
      was no App Insights component in the resource group at all, so
      `host.json`'s logging block was inert and every
      `logging.exception()` in the ingest path went nowhere. Created
      `appi-track-telemetry` (workspace-based, bound to the existing
      Log Analytics workspace `workspace-racktelemetryLUkB` so Function
      and Container App telemetry land in one place) and set
      `APPLICATIONINSIGHTS_CONNECTION_STRING` on
      `func-track-telemetry-ingest`. Had to create it via `az rest`
      against ARM: `az monitor` fails to load on this CLI version
      ("Error loading command module 'monitor'"), the same class of bug
      already recorded for `az maps`. Verified live: `AppRequests` shows
      per-function rows with result codes, and `AppTraces` shows the
      host's per-invocation logs, which is the channel
      `logging.exception()` writes to. `AppExceptions` is empty because
      no exception occurred - deliberately did NOT force a production
      500 to populate it, so that specific path is wired-and-inferred
      rather than observed.
      **Finding #4, TypeScript strict (issue #10) — CLOSED.** `strict`
      was unset in every tsconfig, so `strictNullChecks` was off and the
      `| null` types in `api/client.ts` were unenforced. Set
      `"strict": true` in `tsconfig.app.json`; **the codebase compiled
      with zero errors** and `npm run build` passes. Confirmed strict is
      genuinely active (not silently ignored) with a throwaway probe
      that now correctly fails `TS18047`.
      Correction worth recording: the review originally justified this
      finding with the `min_speed_mph` crash fixed the same day, saying
      strict would have caught it. It wouldn't have - that field was
      typed `number`, so `.toFixed()` type-checks under strict too; the
      bug was the wrong annotation. The finding stands (the annotations
      were unenforced) but its value is prospective, not a defect it
      was actively masking. See the "Correction: finding #4" section in
      `docs/specs/engineering-review.md`.
- [x] 2026-08-09 — Corner story now sorts in lap order (T1, T2, … T10)
      instead of |Δ| descending, per AC — the table reads as a walk
      around the circuit in the order it's driven. Spec updated in the
      same commit so it doesn't drift from the build again. Sorting is
      on the track's `corners.sort_order`, never the code string:
      `corner_code` is text, so a string sort puts `10` before `2` and
      has nowhere sensible to put `3A`/`11A`. `corner_names()` became
      `corner_catalog()` (code -> name + sort_order); the session
      summary's delta table was moved onto the same ordering, replacing
      a `(len(code), code)` approximation that happened to be right for
      plain numeric codes and would have been wrong for lettered ones.
      Server-side only - no dashboard change, so only the Function App
      was redeployed.
- [x] 2026-08-09 — Event summary page rebuilt against the rewritten
      layout spec (`docs/specs/event-summary-page.md`, rewritten
      2026-08-03 *after* the first build landed, which is why the page
      had drifted from the approved mockup). Header now matches the
      spec: mono eyebrow `EVENT · <ORG> · <RUN GROUP>`, event name alone
      as the display-face title, `track · configuration · date`
      subtitle, and session/lap pill badges (track time moved out of the
      subtitle into a tile). Hero stats are now the spec'd **six** tiles
      in a 2-column grid under a `HERO STATS` label - added the missing
      Laps and Track time tiles, and a missing tile renders an em dash
      instead of disappearing. Deltas read as one-decimal seconds
      ("2.9s", "−1.5s") rather than the m:ss.mmm lap format. Sessions
      table adopts the timing-screen form (`S4 · 5:00p`, right-aligned
      mono, `WX` column) and the corner story gains its explainer line
      and `S<first> MIN`/`S<last> MIN` column order. Weather strip moved
      to the bottom, per the spec's section order.
      New in the API (`queries.event_summary()`): `configuration`,
      `run_group` (per-session field, so it only surfaces when the whole
      event ran one group), `valid_lap_count`, `best_lap_number`, and
      `corner_name` - the corner column now reads `T9 Lightbulb` /
      `T10 Kink` where a name is curated, `T4` where it isn't.
      Purple *was* built this time (AC's call): new `--fastest` token in
      both palettes, applied to event best + event optimal and to the
      event's best lap wherever it appears in the sessions table. The
      spec's Barlow Condensed + IBM Plex Mono were deliberately NOT
      added - the CSP has no `font-src` so it falls back to
      `default-src 'self'` and Google Fonts would be blocked; instead
      `--font-display`/`--font-mono` tokens carry system stacks, keeping
      the display/mono split the spec calls essential. Swapping in
      self-hosted webfonts later is a one-line token change.
      One deliberate deviation from the literal spec (AC's call): the
      session pace bar floors at 6% instead of 0%, because a zero-width
      bar on the slowest session reads as missing data rather than as a
      slow session.
      Shared components extended rather than forked: `StatTile` gained
      `tone` (fastest/good/bad) + `variant="hero"`; `CornerDeltaTable`
      gained `className`, a `columnOrder` prop (the event page reads
      left-to-right in time, the session page reads this-vs-prior), and
      corner-name labelling. Fixed a latent crash while there -
      `CornerDelta.min_speed_mph` was typed non-null but the server can
      return null (both delta paths union the two laps' corner codes),
      and the old cell did `.toFixed(1)` on it unguarded.
      Verified: `queries.event_summary()` run against the live DB for a
      3-session event (id 3), a single-session event (id 2, hides
      progression + corner story), and a zero-session event (id 5, six
      em dashes, no crash); `tsc --noEmit` and `oxlint` clean; screenshot
      pass in **both** light and dark through a throwaway unauthenticated
      `/preview/...` route with Playwright serving the real payloads as
      fixtures - which is what caught the wrapping session cells, the
      wrapping corner speeds, and the wrapping date ranges. Preview
      routes removed afterwards; `package.json`/`package-lock.json`
      untouched.
- [x] 2026-08-09 — Events list temporal split (in progress / upcoming /
      past), the separately-tracked half of the same spec. `phase` is
      computed server-side in `queries.list_events()` via a new
      `event_phase()` helper so the MCP tools and the dashboard agree on
      what "upcoming" means, and rows come back already in render order
      (in progress, then upcoming ascending, then past descending) -
      consistent with this project's sort-server-side convention. The
      comparison uses the track's local date, not UTC, per the spec.
      `EventsPage.tsx` renders one table per group, empty groups
      collapse, zero-session events show an em dash rather than a 0, and
      event names now link through to the summary page.
      Verified against live data: the multi-day 2026-08-08→08-09 event
      lands in "In progress" on 2026-08-09 (the inclusive-range case the
      spec calls out), "Summer Sizzle" (2026-08-16) in Upcoming, and the
      four past events sort most-recent-first.
- [x] 2026-08-09 — Fixed the session `start_time` timezone bug (v1.0
      item, found 2026-08-03, deferred then). All three spec'd parts
      done: (1) `sql/17_track_timezone.sql` applied to the live DB -
      adds `dbo.tracks.iana_timezone`, all 3 NJMP rows backfilled to
      `America/New_York`; (2) `racechrono_parser.py` now converts before
      storing, via new `track_timezone()` + `to_track_local()` helpers
      using stdlib `zoneinfo` (no new dependency, file stays
      stdlib-only). Weather still gets the UTC instant - it's keyed on
      the absolute time - while the column gets local wall-clock;
      (3) one-time data correction applied to all 7 existing sessions
      with a `start_time`. TNIA's sessions now read 5:00p / 7:01p /
      6:02p instead of 9:00p / 11:01p / 10:02p, matching what was
      actually driven. The backfill ran dry-run first and guarded on two
      invariants before writing: every converted time must land in
      plausible on-track hours (06:00-21:00 local) and no row's local
      date may drift off its `session_date` - both held for all 7.
      DST is handled by `zoneinfo`, verified both ways (a July instant
      converts at UTC-4, a January one at UTC-5). Note the backfill is
      deliberately NOT idempotent - running it twice would shift twice -
      so it was a one-shot, recorded here rather than kept as a script.
- [~] 2026-08-07 — OAuth 2.1 on the MCP server (last unauthenticated
      endpoint, tracked v1.0 item). SERVER SIDE SHIPPED & LIVE, CLAUDE
      CONNECTION BLOCKED by a known Entra↔MCP incompatibility — see
      "Blocked / next" at the end of this entry.
      What shipped: `ca-track-telemetry-mcp` is now an OAuth Resource
      Server. New `mcp_server/auth.py` (`EntraTokenVerifier`, async
      `TokenVerifier`) validates CIAM bearer tokens via PyJWT/JWKS —
      signature/issuer/audience + a required `mcp.access` scope —
      mirroring the proven `ingest/api_auth.py`. `server.py` wires it via
      `FastMCP(..., token_verifier=, auth=AuthSettings(issuer_url,
      resource_server_url, required_scopes))`, which auto-wraps `/mcp` in
      `RequireAuthMiddleware` and publishes
      `/.well-known/oauth-protected-resource` (RFC 9728). Separate CIAM
      app registration `track-telemetry-mcp`
      (`93fedc8d-17e5-428a-bfa1-1104befda24f`) with an `mcp.access`
      scope + Claude's `https://claude.ai/api/mcp/auth_callback` redirect
      + a client secret — created by hand in the Entra portal because the
      admin identity is a personal (MSA) account that Azure CLI /
      device-code sign-in rejects for this tenant (`AADSTS530035`), and
      portal-captured Graph tokens are nonce-bound and unusable from curl
      (`az ad`/`az rest` automation both closed). `mcp.access` delegated
      permission added + admin-consented (via "APIs my organization
      uses", since the app doesn't self-list under "My APIs"). Deployed
      via `az containerapp up --source .` with env vars
      `MCP_TENANT_ID`/`MCP_CLIENT_ID`/`MCP_RESOURCE_URL`.
      Verified working: locally against real RS256-signed tokens (accepts
      valid aud=client-id *and* aud=`api://`-uri; rejects missing-scope /
      wrong-aud / wrong-iss / expired); live in prod the metadata
      advertises the CIAM issuer, `/mcp` returns 401+`WWW-Authenticate`
      with no/garbage token, and the fully-qualified scope
      `api://…/mcp.access` is now advertised in `scopes_supported` (bare
      `mcp.access` was rejected by Entra as an unknown scope).
      Blocked / next (pick up here): Claude's connector completes OAuth
      discovery + consent but the token request fails with
      `AADSTS9010010: The resource parameter provided in the request
      doesn't match with the requested scopes.` Root cause is a known,
      widely-reported Entra↔MCP incompatibility (anthropics/claude-code
      #52871; microsoft/{azure-devops-mcp #1293, Dataverse-MCP #15,
      powerbi-modeling-mcp #68}): the MCP client sends an RFC 8707
      `resource` param (the server URL, `https://…azurecontainerapps.io/`
      — note the WHATWG-normalised trailing slash) alongside the scope,
      but Entra's v2.0 endpoint (post-~Mar-2026 enforcement) rejects the
      pair unless `resource` string-matches the scope's resource, which
      it can't here (server URL ≠ `api://93fedc8d…`). Plan agreed with
      Andres: (1) TRY alignment — set the app's Application ID URI to a
      PATH-based server URL (`https://…azurecontainerapps.io/mcp`, whose
      path dodges the client's host-only trailing-slash bug), expose
      `mcp.access` under it, have the server advertise that as the
      resource + scope, and accept aud=that URL in the verifier; (2) if
      the client bug still defeats it, FALL BACK to making the MCP server
      an OAuth AS proxy that strips/normalises the `resource` param
      before forwarding to Entra. NOTE: `mcp_server/auth.py` carries
      temporary debug instrumentation to strip once the connector works
      — detail in `.local/security-findings.md` (S-2), not here, since
      this repo is public.
      Diagnostics tip: Log Analytics workspace `1ac9567e-…` /
      `ContainerAppConsoleLogs_CL` aggregates all replicas (single-replica
      `az containerapp logs --follow` misses calls on the other replica).
      Docs: `docs/mcp_server.md` Authentication section + env vars.
- [x] 2026-08-03 — Redeployed the dashboard (`swa-track-telemetry-dashboard`)
      to pick up the security review's CSP + `X-Frame-Options` headers.
      `npm run build` then the standard SWA CLI deploy
      (`docs/BACKLOG.md`'s documented command with the live deployment
      token). Verified via `curl -I` against the live URL: both new
      headers present with the exact policy from
      `staticwebapp.config.json` (`connect-src` scoped to the Function
      App + both CIAM authority hosts, `frame-ancestors 'none'`); also
      confirmed the page shell, JS bundle, CSS, and favicon all still
      load (200s, all same-origin, satisfying `script-src`/`style-src`/
      `img-src 'self'`). Checked `index.html` and `dashboard/src/**`
      for any external resource references (CDN scripts, web fonts)
      before deploying, to rule out the new CSP breaking something
      silently - found none. **Not verified**: the actual interactive
      sign-in flow through the CIAM redirect, silent token renewal,
      and authenticated API calls - not automatable here, and this
      matters more than usual right now since the same day's Function
      App redeploy also carries an unverified `scp`-claim check on the
      backend this talks to. Needs a real browser check before this
      backlog item can close.
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
- [x] 2026-08-03 — Real interactive sign-in verification against prod,
      closing the last open piece of the 2026-08-03 CSP/`scp`-check
      deploy (see the "Redeploy dashboard with CSP/X-Frame-Options"
      commit). Manually signed in at
      `https://salmon-moss-0a7e4b70f.7.azurestaticapps.net` via the
      real `loginRedirect` flow against `tracktelemetry.ciamlogin.com`,
      landed on the authenticated `DashboardHome`, and loaded a
      protected route (`/sessions`) with a real bearer token — no CSP
      violations in the browser console and no unexpected 401s, so the
      `connect-src`/`frame-ancestors` policy in
      `dashboard/staticwebapp.config.json` and the `scp`-claim check in
      `ingest/api_auth.py` both work under real sign-in, not just
      `curl`. No server-side corroboration (no Application Insights
      component provisioned on the Function App to check request logs
      against) - the client-side check is the one that mattered here,
      since the risk was specifically a bad assumption locking out
      legitimate sign-in before it ever reaches the API.
- [x] 2026-08-03 — Disabled self-service sign-up on the CIAM
      `SignUpSignIn` user flow, closing item (1) of the security-review
      follow-ups (see the "Information security due diligence" entry
      above). PATCHed `isSignUpAllowed` to `false` via the Graph beta
      endpoint (`/beta/identity/authenticationEventsFlows/{id}`) using
      a bearer token captured through DevTools (Network tab on
      `entra.microsoft.com` → `authenticationEventsFlows` request).
      The obvious request shape - `onInteractiveAuthFlowStart` alone -
      got rejected with `AADB2C`/"request body is null or in bad
      format"; the fix was including a top-level `@odata.type` of
      `#microsoft.graph.externalUsersSelfServiceSignUpEventsFlow` on
      the PATCH body (the endpoint needs the derived flow resource's
      type, not just the nested property's), which returned `204` and
      verified `isSignUpAllowed: false` on a follow-up GET. Script at
      `patch-signup-flow.sh` (scratchpad, not committed - takes
      `GRAPH_TOKEN` as an env var, no token persisted to disk).
- [x] 2026-08-03 — Fixed GHSA-537c-gmf6-5ccf (`cryptography<48.0.1`,
      CVSS 7.5), closing item (2) of the security-review follow-ups.
      The real blocker was pytds's own TLS hostname check
      (`pytds/tls.py`'s `validate_host`), which calls the pyOpenSSL
      `X509.get_extension()`/`get_extension_count()` methods that
      pyOpenSSL 26.2 removed - hence the `pyOpenSSL<26.2` pin, which in
      turn capped `cryptography` below the fixed version. Added
      `ingest/_pytds_tls_compat.py`, which monkeypatches
      `pytds.tls.validate_host` at import time (via `cloud.py`) to do
      the same CN/SAN hostname check using `cert.to_cryptography()` and
      the `cryptography` library's own `x509` API instead of the
      removed pyOpenSSL methods - no pytds source touched, since
      `establish_channel` looks up `validate_host` as a module global
      at call time. `requirements.txt` and `mcp_server/requirements.txt`
      now read `pyOpenSSL>=26.2` / `cryptography>=48.0.1` instead of the
      old pin. Verified for real, not just by type-checking: installed
      the upgraded packages (`pyOpenSSL` 26.4.0, `cryptography` 50.0.0)
      in a throwaway venv and connected to the live
      `track-telemetry.database.windows.net` DB through
      `get_cloud_connection()`, running a real query successfully;
      also confirmed the patch is load-bearing by running the same
      connection *without* importing the compat shim, which reproduced
      the exact expected crash
      (`AttributeError: 'X509' object has no attribute 'get_extension'`).
      Upgraded the project's own `.venv` to the same versions and
      re-verified there too. `ingest/api_auth.py` and
      `mcp_server/server.py` weren't exercised end-to-end here (need
      `MSAL_TENANT_ID` and the separately-installed `mcp` package,
      respectively) - unrelated to this change, since both failed
      before reaching any pytds/TLS code.
- [x] 2026-08-03 — Closed the "Information security due diligence" v1.0
      item: all three remaining sub-items are done (self-service
      sign-up disabled, the `cryptography` CVE fixed, real interactive
      sign-in verified - see the three entries above). OAuth 2.1/PKCE
      on the MCP server remains open as its own separately-tracked
      v1.0 item, now unblocked.
- [x] 2026-08-03 — Event summary page (v1.x, pulled forward), replacing
      the `/events/:eventId` placeholder per
      `docs/specs/event-summary-page.md` (approved 2026-07-25). New
      `queries.event_summary()` (`ingest/queries.py`): header/badges
      (session count, total laps, total track time from *all* laps not
      just valid ones), event best lap (with which session/lap),
      event-wide optimal lap (same MIN-per-segment-then-SUM shape as
      the per-session `optimal_lap_ms()`, widened to every valid lap
      across the event's sessions), left-on-table, first-vs-last
      session progression, first-vs-last corner deltas sorted by
      `|delta_mph|` descending (server-side, matching this project's
      established sort-server-side convention), and a weather summary
      - each field `null`/empty and its UI section hidden when the
      event doesn't have the data (0-session events, single-session
      events, pre-segment_times sessions). New
      `GET /api/events/{id:int}/summary` route in `function_app.py`,
      same `@require_auth`/404-on-`ValueError` pattern as the session
      summary route. Frontend: `EventSummaryPage.tsx` rewritten against
      the new endpoint; reused `StatTile` and `CornerDeltaTable`
      (added an optional `labels` prop so the same component says
      "First session"/"Last session" here instead of "This
      session"/"Prior session") rather than forking either; added
      generic `.progress-bar-track`/`.progress-bar-fill` CSS (same
      sizing as the consumables page's `.life-bar-*`, undyed since
      lap pace isn't a good/warning/critical metric) and `.eyebrow`
      for the org_code header line. Deliberately not built: the
      spec's purple "optimal" timing-tower accent (no purple exists
      anywhere in the current palette, and the spec itself says
      existing dashboard styling wins on conflicts) and the separate
      events-list temporal-split section of the same spec (independent
      backlog item, not in scope here).
      Verified for real: `queries.event_summary()` run directly
      against the live DB for a multi-session event (id 3, 4 sessions
      + corner story), a single-session event (id 2, hides
      progression/corner-story, shows optimal/left-on-table/weather),
      and a zero-session event (id 5, everything null/empty, no
      crash). `tsc --noEmit` clean. Real interactive sign-in isn't
      automatable here, so laid out the exact verified JSON above as
      fixtures and screenshotted (light + dark) through a throwaway
      unauthenticated `/preview/events/:eventId` route with Playwright
      intercepting the API call - confirmed hero-tile conditional
      rendering, progress-bar scaling (fastest session = full bar,
      single-session event = 100%), and pluralization all render
      correctly against the real numbers, then deleted the preview
      route and the temporary `playwright` install (`git status`
      confirms `package.json`/`package-lock.json` untouched). Function
      App redeployed (`get_event_summary` live, confirmed a real 401
      rather than a crash for an unauthenticated request - i.e. this
      didn't repeat the pyOpenSSL live-incident pattern). Dashboard
      build (`tsc -b && vite build`) succeeded; deployed to production
      via the standard SWA CLI command shortly after (asset hashes on
      the live site confirmed to match the local build).
- [x] 2026-08-03 — Deleted a duplicate session found via the new event
      summary page. TNIA (event 3) showed two sessions with
      byte-identical `start_time`/lap times (#4 and #7); checking
      `source_file` showed different upload timestamps ~9.5 days
      apart, meaning the same RaceChrono CSV got re-ingested later as
      a "new" session rather than recognized as already loaded - there
      is no ingest idempotency yet (tracked separately under v1.x's
      "One-step ingestion" item, "add idempotency, e.g. content
      hash"). The event summary page's chronological session-by-
      session view is what made this obvious; the old flat sessions
      list didn't surface it. Deleted the later duplicate
      (`session_id=14`, session #7, `session_1785595321.csv`), kept
      the original (`session_id=6`, session #4,
      `session_1784769895.csv`), after confirming dependent-row counts
      first (9 laps, 90 corner_metrics, 0 segment_times, 0
      consumables referencing it) and deleting child rows before the
      parent in one pass (segment_times -> corner_metrics -> laps ->
      sessions). Re-verified `event_summary(cnx, 3)` after: 3 sessions,
      real (non-zero) corner deltas, a real progression value
      (-1.485s) - confirms the event page's math was correct all
      along and the "wrong" numbers reported were genuinely duplicate
      source data, not a query or rendering bug.
