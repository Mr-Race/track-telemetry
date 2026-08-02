# Spec: Engineering Practices Review (pre-v1.0)

Status: scoped 2026-08-02 per AC. Gate on the v1.0 release — "1.0"
implies the code has been looked at deliberately, not just that the
features work.

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
_To be completed during the review._

| # | Area | Severity | Finding | Fix | Status |
|---|------|----------|---------|-----|--------|
|   |      |          |         |     |        |
