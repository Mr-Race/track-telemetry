# Spec: Engineering Practices Review (pre-v1.0)

Status: scoped 2026-08-02 per AC. **Review completed 2026-08-09** —
see Findings below (22 findings: 5 high, 9 medium, 8 low). Gate on the
v1.0 release — "1.0" implies the code has been looked at deliberately,
not just that the features work. The five high-severity findings are
the remaining gate; none are fixed yet.

## Purpose
An honest assessment of everything built and deployed so far,
against the practices a reviewer would expect of production
software. Two audiences: future-me maintaining this, and anyone
evaluating the work as evidence of engineering judgment.

Output is a findings table with severities and a remediation plan —
not a pass/fail. Findings become GitHub issues; this doc is the
index.

## Scope — what gets reviewed
Everything in the repo and everything deployed:
`ingest/`, `mcp_server/`, `dashboard/`, `sql/`, `function_app.py`,
plus the Azure resources they run on.

## Review areas

### 1. Automated testing (expected to be the biggest gap)
There is no test suite. The highest-value targets are pure
functions with real fixtures already in `data/`:
- `parse_csv` — header/channel detection, the OBD-absent path,
  malformed rows.
- Lap detection and the median-based validity rule.
- `compute_corner_metrics` — zone entry/exit, apex selection.
- `resolve_event_id` / `next_session_number` — the zero-match and
  multi-match error paths, which currently only fail in prod.
- Weather parsing (`ingest/weather.py`) — WMO code mapping, the
  all-None failure path.
Decide a realistic target (smoke-level coverage of the parser, not
a coverage percentage) and whether `queries.py` gets integration
tests against a throwaway DB or stays manually verified.

### 2. CI/CD
Today every deploy is hand-run `az`/SWA CLI commands, and
correctness is confirmed by manually curling prod. Assess:
- GitHub Actions on push: lint, tests, build.
- Deploy workflow for the Function App, SWA, and Container App —
  encoding the verification steps that are currently remembered
  (notably the Container Apps revision-health check from issue #1).
- Whether prod deploys should require a green build.

### 3. Database migration discipline
`sql/*.sql` files are applied by hand, in order, from memory. There
is no record in the database of which have run — drift is currently
detected by something breaking. Assess a migrations table or a
lightweight tool, and the documented rule that ALTER and reference
run as separate batches.

### 4. Dependency management
`mcp<2.0.0` was pinned reactively after a production crash loop.
Review every requirements file for unpinned or loosely-pinned
dependencies, and decide a policy (pin + scheduled bump vs float).

### 5. Code structure
`ingest/` currently holds the parser, SQL queries, blob/cloud
access, maps, API auth, and weather. Assess whether that's still
one coherent module or wants splitting, and whether the
MCP server and Function App sharing `ingest/queries.py` is the
right coupling.

### 6. Error handling and observability
- What a malformed or truncated CSV does today, end to end.
- Whether Application Insights is on, and what's actually logged.
- Structured logging vs prints; correlation between an ingest
  request and its outcome.
- The weather fetch already models the right pattern (fail soft,
  never block ingest) — check whether other external calls do.

### 7. Documentation currency
The backlog is excellent and the Done log is unusually good. Check
that `docs/technical/` matches deployed reality once the v1.0 docs
baseline lands, and that the runbook covers the failure modes
already learned the hard way.

## Method
1. Read every file in the repo against the areas above.
2. Log each finding: area, severity (high/medium/low), what's
   wrong, why it matters, proposed fix, effort.
3. Fix anything high-severity before declaring 1.0; medium and low
   become v1.x issues.
4. Record the decisions worth remembering in the ADR-style decision
   log that the v1.0 docs baseline item already calls for.

## Findings

Review conducted 2026-08-09 against commit `0233914`. Every finding
below was verified against the repo or the live Azure/SQL resources —
none are inferred from the docs. 22 findings: 5 high, 9 medium, 8 low.

> **This repository is public.** Security-relevant findings are held in
> `.local/security-findings.md` (gitignored) as S-1…S-4 and are
> referenced here by identifier only. Do not restore their detail to
> this file, to commit messages, or to GitHub issues.

Severity means: **high** blocks 1.0 per the Method section above,
**medium** becomes a v1.x issue, **low** is a judgement call to fix
opportunistically. Effort is S (< half a day), M (1-2 days), L (more).

| # | Area | Sev | Finding | Fix | Effort |
|---|------|-----|---------|-----|--------|
| 1 | Testing | **High** | No automated tests exist. `git ls-files` matches no test file; 2,400 lines of Python and 12 React components have never been exercised except by hand. | Pytest suite over the pure functions, fixtures from `data/`. | M |
| 2 | Observability | **High** | **No Application Insights at all** — not merely unconfigured: there is no App Insights component in resource group `Track-telemetry`, and no `APPLICATIONINSIGHTS_CONNECTION_STRING` on the Function App. `host.json`'s `logging.applicationInsights` block is therefore inert, and every `logging.exception()` in `function_app.py` goes nowhere. The production ingest path — the write path into the system of record — is unobservable. | Create the component, wire the connection string, verify a real exception surfaces. | S |
| 3 | Error handling | **High** | The HTTP ingest route has **no idempotency**. `find_existing_session()` exists and is used by the CLI `--backfill` path, but `function_app.py`'s `ingest` never calls it — it always `load()`s a new row. Re-POSTing the same CSV silently creates a duplicate session. This is not theoretical: a duplicate was found and deleted on 2026-08-03. | Look up by `(event_id, source_file)` — or better a content hash — and `refresh()` instead of `load()`. | S |
| 4 | Testing | **High** ([corrected](#correction-finding-4)) | **TypeScript `strict` is not set in any tsconfig**, so `strictNullChecks` is off (verified via `tsc --showConfig`). Every `\| null` in `api/client.ts` is decorative — the compiler will not reject a genuine null flow, and `tsc --noEmit` is the dashboard's only automated check. | Set `"strict": true`, fix the resulting errors. | M |
| 5 | Migrations | **High** | No record of which migrations have run. 17 files in `sql/`, 13 tables live, and **no migrations-tracking table in the database**. Which scripts have been applied is held in memory and the Done log; drift is detected only when something breaks. `sql/17` was found unapplied today purely by inspection. | A `dbo.schema_migrations` table + a small apply script that records each filename. | M |
| 6 | CI/CD | Medium | No CI whatsoever — no `.github/` directory. Lint, typecheck, build, and tests (once they exist) run only when someone remembers. | GitHub Actions on push: `oxlint`, `tsc -b`, `pytest`. | S |
| 7 | Dependencies | Medium | Most Python dependencies are entirely unpinned: `azure-functions`, `azure-identity`, `azure-storage-blob`, `python-tds`, `PyJWT[crypto]`, `certifi` carry no constraint in either requirements file. The only bounds present (`mcp<2.0.0`, `pyOpenSSL>=26.2`) were each added *reactively after a production break*. There is no lockfile, so two deploys of the same commit can install different code. | Pin with hashes (`pip-compile`), add a scheduled bump PR. | M |
| 8 | Error handling | Medium | `parse_csv` silently discards malformed rows (`if not r or len(r) != len(names): continue`) with no count, warning, or telemetry. Combined with #2, a truncated or partly-corrupt upload loads quietly with missing samples and looks successful. | Count skipped rows, return in the response, log; fail past a threshold. | S |
| 9 | Structure | Medium | Every request builds a new SQL connection *and* a new `DefaultAzureCredential()` (`_connect()` → `get_cloud_connection()`, and again in `maps._maps_token()`), and **no connection is ever closed** — there is no `with`/`.close()` anywhere in `function_app.py` or `mcp_server/server.py`. Against a serverless DB with a 60s login timeout this is both slow and leaky. | Module-level cached credential; context-managed connections. | M |
| 10 | Error handling | Medium | *Tracked privately (S-1) — this repo is public.* | — | S |
| 11 | Structure | Medium | *Tracked privately (S-3) — this repo is public.* | — | M |
| 12 | Testing | Medium | `compute_segment_times` explicitly sorts each lap's samples by `elapsed`; `compute_corner_metrics` does **not**, yet depends on order for `inside[0]`/`inside[-1]` (entry/exit speeds). Two functions with the same precondition, one defended, one not. | Sort in both; test with shuffled input. | S |
| 13 | Observability | Medium | *Tracked privately (S-2) — this repo is public.* | — | S |
| 14 | Migrations | Medium | 5 of 17 migration files mix `ALTER TABLE` with `INSERT`/`UPDATE` in one file with no `GO` separator (`09`, `11`, `12`, `13`, `17`). SQL Server does not reliably see a newly added column later in the same batch — this has now bitten twice (`sql/13`, and `sql/17` again today, both needing manual splitting). The rule is known but encoded nowhere. | Add `GO` separators and state the rule in the runbook. | S |
| 15 | Testing | Medium | `resolve_event_id`'s zero-match and multi-match branches, and `next_session_number`, have no coverage — they are reachable only through a real upload, so they fail in production first. | Unit-test both with a fake cursor. | S |
| 16 | Docs | Low | `README.md` is stale: it lists "OAuth on the MCP server" as pending (server side shipped 2026-08-07), describes status as "MVP launched", omits segment times, weather, optimal laps, cars, and the event pages, and **its repo layout never mentions `mcp_server/`** despite that being a deployed service. | Refresh at the v1.0 docs baseline. | S |
| 17 | Docs | Low | No local development or test instructions anywhere — how to run `func start`, the dev server, or (soon) the tests is undocumented. For a piece explicitly built as portfolio evidence, a reviewer cannot run it. | Add a Getting Started section. | S |
| 18 | Error handling | Low | External-call resilience is inconsistent. `weather.py` fails soft and never blocks an ingest (the spec calls this the right pattern); `maps.fetch_satellite_image` has no timeout guard beyond 30s, no retry, and propagates to a 500. | Decide per call site and document the choice. | S |
| 19 | Testing | Low | `compute_laps` uses `sorted(durs)[len(durs)//2]` as "median" — for an even lap count this is the upper-middle value, not the mean of the middle two, which biases the validity threshold lenient. | Use `statistics.median`; test odd/even. | S |
| 20 | Testing | Low | `compute_corner_metrics` collects *all* in-zone samples for a lap into one `inside` list. If a layout passes the same apex twice in a lap, both passes merge — entry from the first, exit from the second, apex the global minimum. | Segment by contiguous runs; test with a synthetic double-pass. | M |
| 21 | Structure | Low | `DEFAULT_CAR_ID = 2` hardcodes a database row id into application code, and `function_app.py` repeats the same try/except/`_json_response` block ~15 times. | Config setting; a decorator for the error envelope. | S |
| 22 | CI/CD | Low | Deploys are hand-run `func publish` / SWA CLI commands, and correctness is confirmed by manually curling prod. The verification steps that matter (Container Apps revision health, a real 401 rather than a crash) live in the Done log and in memory, not in code. | Encode as a deploy workflow with post-deploy smoke checks. | M |

### Correction: finding #4
Recorded 2026-08-09, after fixing it.

As originally written, finding #4 justified itself with the
`CornerDelta.min_speed_mph` crash fixed earlier that day, claiming it
was invisible to `tsc` because strict was off. **That was wrong.** That
field was declared `number` (non-null), so `.toFixed()` on it
type-checks under strict too — the defect was the inaccurate
annotation, not the compiler setting. Strict would not have caught it.

The finding itself stands: the `| null` annotations were genuinely
unenforced. But enabling `"strict": true` produced **zero errors**
across the whole dashboard — the code had been written null-safely by
discipline, not by enforcement. So the honest reading is that this was
a cheap guard worth putting in place, not a high-severity defect that
was actively hurting. Severity left as filed for traceability.

### Finding → issue index
Filed 2026-08-09. This doc stays the index; the issues carry the work.

| Finding | Issue | Finding | Issue |
|---|---|---|---|
| #1 tests | [#11](https://github.com/Mr-Race/track-telemetry/issues/11) | #12 unsorted samples | [#19](https://github.com/Mr-Race/track-telemetry/issues/19) |
| #2 App Insights | [#9](https://github.com/Mr-Race/track-telemetry/issues/9) | #13 | private (S-2) |
| #3 ingest idempotency | [#3](https://github.com/Mr-Race/track-telemetry/issues/3) (pre-existing) | #14 ALTER/GO | [#21](https://github.com/Mr-Race/track-telemetry/issues/21) |
| #4 TS strict | [#10](https://github.com/Mr-Race/track-telemetry/issues/10) | #15 event-resolution tests | folded into [#11](https://github.com/Mr-Race/track-telemetry/issues/11) |
| #5 migration tracking | [#12](https://github.com/Mr-Race/track-telemetry/issues/12) | #16 stale README | [#24](https://github.com/Mr-Race/track-telemetry/issues/24) |
| #6 CI | [#14](https://github.com/Mr-Race/track-telemetry/issues/14) | #17 no dev docs | [#25](https://github.com/Mr-Race/track-telemetry/issues/25) |
| #7 dependencies | [#13](https://github.com/Mr-Race/track-telemetry/issues/13) | #18 external-call resilience | [#26](https://github.com/Mr-Race/track-telemetry/issues/26) |
| #8 malformed CSV rows | [#15](https://github.com/Mr-Race/track-telemetry/issues/15) | #19 median | [#22](https://github.com/Mr-Race/track-telemetry/issues/22) |
| #9 connections | [#16](https://github.com/Mr-Race/track-telemetry/issues/16) | #20 double-pass corner | [#23](https://github.com/Mr-Race/track-telemetry/issues/23) |
| #10 | private (S-1) | #21 hardcoded car / boilerplate | [#27](https://github.com/Mr-Race/track-telemetry/issues/27) |
| #11 | private (S-3) | #22 deploy automation | [#28](https://github.com/Mr-Race/track-telemetry/issues/28) |

Note finding #3 was already filed on 2026-08-03 as issue #3, from the
duplicate-session incident itself — the review independently found the
same root cause by reading the code.

### Reading of the result

The system is well-designed and unusually well-documented for a
solo project — the Done log, the security review, and the specs are
better than most professional codebases. The gap is not judgement, it
is **verification**: almost everything is confirmed by a human looking
at it once, and nothing re-checks itself afterwards.

That single theme explains most of the list. There are no tests (#1),
so refactors are unguarded. `strict` is off (#4), so the type
annotations that look like safety are not. There is no CI (#6), so
even the checks that exist run only by hand. There is no telemetry
(#2), so production failures are invisible. There is no migration
ledger (#5), so schema drift is found by breakage. Each is
individually cheap; together they mean the project cannot tell you
when it is broken.

Two findings are worth fixing regardless of the 1.0 timeline because
they have already caused real incidents: the missing ingest
idempotency (#3) produced a duplicate session, and the unpinned
dependencies (#7) produced a crash loop.

### Suggested order

1. **#2 App Insights** and **#13 debug prints** — an hour, and every
   later fix becomes verifiable.
2. **#4 `strict: true`** — one line, then fix the fallout; do it
   before writing tests so the tests are written against honest types.
3. **#1 tests** for `parse_csv`, `compute_laps`, `compute_corner_metrics`,
   `resolve_event_id`, and `weather` parsing, which also closes #12,
   #15, #19, #20.
4. **#6 CI** to run all of the above on push.
5. **#3 idempotency** and **#5 migrations table**.
6. Everything medium/low remaining becomes v1.x issues.

Findings #1-#5 are the 1.0 gate. Realistically that is a few focused
days, and #2 plus #4 are same-day wins.
