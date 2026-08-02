# Spec: Information Security Due Diligence (pre-v1.0)

Status: scoped 2026-08-02 per AC. Gate on the v1.0 release.

## Purpose
A full security review of the platform before it's declared 1.0 and
before multi-user (v2.0) makes every weakness someone else's
problem too.

Output is a threat model plus a findings log with severities.
High-severity findings block 1.0.

## Why this matters more than it looks
This platform stores **personal location data**: GPS traces at
sample resolution, timestamped, tied to a named driver and a
specific car. A leaked session file says where the driver was, when,
and how fast. Treat it as sensitive personal data, not as lap
times.

## Review areas

### 1. Secrets
- Sweep the full git history, not just HEAD — a secret removed in a
  later commit is still in the history.
- Known item: a real Azure Maps client ID is hardcoded in
  `local.settings.json.example` (flagged in an earlier manual
  review, not yet cleaned).
- Enable GitHub secret scanning and push protection on the repo.
- Confirm the managed-identity story holds everywhere: the stated
  design is that no key ever leaves the server (Function App MI to
  SQL, Blob, and Azure Maps; MCP Container App MI to SQL as
  `db_datareader`). Verify against deployed config, not against
  intent.
- Audit Function App / Container App application settings and the
  SWA config for anything secret-shaped.

### 2. Authentication and authorization
- **MCP server is still unauthenticated** — already tracked as a
  v1.0 item (OAuth 2.1 + PKCE via Entra). Sequence that work AFTER
  this review so the review informs it rather than reviewing fresh
  code.
- Re-verify the read-API JWT validation in `ingest/api_auth.py`:
  signature via JWKS, audience, issuer, expiry, and that no handler
  touches the DB before validation.
- Confirm `@require_auth` is on every route that should have it —
  the Block 5 gap (routes serving personal telemetry anonymously)
  was found live in prod, so enumerate rather than assume.
- `POST /api/ingest` is function-key gated. Assess whether a shared
  key in an iOS Shortcut URL is acceptable, what rotation looks
  like, and what an attacker with the key can do (write arbitrary
  sessions; poison the dataset).
- Scope enforcement: `access_as_user` is requested, but check it's
  actually required server-side and not merely present.

### 3. Data protection
- Classification and retention: how long raw CSVs live in Blob, and
  whether there's a deletion path.
- Encryption at rest and in transit (defaults are fine — confirm,
  don't assume).
- What the API returns vs what it needs to return; whether any
  endpoint leaks another driver's rows once `driver_id` matters.
- Prepare for v2.0: per-user data ownership and sharing permissions
  are a security boundary, not a feature — note the requirements
  now.

### 4. Network and platform posture
- Storage account networking is currently open — tracked as a
  hardening item; assess and decide.
- No API Management in front of ingest — assess rate limiting and
  abuse exposure.
- CORS configuration on the Function App: confirm it's the SWA
  origin only.
- Container App ingress: confirm what's public and why.
- Azure SQL firewall and Entra-only auth.

### 5. Dependencies and supply chain
- CVE scan of every requirements file and `package.json`.
- Enable Dependabot alerts.
- Note the `mcp` incident (an unpinned dependency's major release
  broke prod) as evidence for the pinning policy in the engineering
  review.

### 6. Client-side
- Token handling in MSAL — storage location, refresh behavior.
- Confirm no secrets in the built dashboard bundle.
- Standard headers (CSP, HSTS) on Static Web Apps.

## Method
1. Threat model first: assets, actors, entry points, trust
   boundaries. Keep it to one page.
2. Walk each area above against deployed reality, not the docs.
3. Log every finding with severity, exploitability, and fix.
4. Remediate all high-severity findings before 1.0. Medium and low
   become tracked issues with owners and dates.
5. Re-run the review before v2.0 multi-user, since that changes the
   trust model fundamentally.

## Threat model
_To be completed during the review._

## Findings
_To be completed during the review._

| # | Area | Severity | Finding | Exploitability | Fix | Status |
|---|------|----------|---------|----------------|-----|--------|
|   |      |          |         |                |     |        |
