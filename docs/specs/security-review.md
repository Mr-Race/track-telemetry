# Spec: Information Security Due Diligence (pre-v1.0)

Status: scoped 2026-08-02 per AC. Review completed 2026-08-03 - see
Findings below. 3 High-severity findings: #1 (MCP auth) is already a
separately tracked v1.0 backlog item running next by design; #2
(CIAM self-service sign-up + unused driver_id) needs an Entra portal
change only you can make; #3 (cryptography CVE) turned out to be
**not fixable** with a simple version floor - see the finding for
why, and for the real live-incident it caused when deployed. **Not
yet clear to declare 1.0** until #2 is resolved and #3 has a real
remediation path.

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
_Completed 2026-08-03._

**Assets:** personal GPS telemetry (raw CSVs in Blob; parsed
laps/corner_metrics/segment_times/weather in Azure SQL), tied to a
named driver, car, and timestamp; the ingest function key; dashboard
bearer tokens (MSAL, `localStorage`); Azure infrastructure
credentials (managed identities, CIAM tenant config); availability of
the free-tier services themselves.

**Actors:** the owner/driver (sole legitimate user today); anyone who
discovers the MCP server's public FQDN (read access, no auth
required); anyone who discovers the dashboard URL and self-registers
via the CIAM `SignUpSignIn` flow (authenticated but not
intentionally-authorized access); anyone who obtains the ingest
function key (write/data-poisoning access); the PyPI/npm supply
chain (unpinned deps); GitHub collaborators (repo is private, so
bounded).

**Entry points:** Function App `/api/*` (JWT-gated, except
function-key-gated `/api/ingest`); MCP Container App (Streamable
HTTP, currently no auth at all); Static Web App (public static
assets + client-side route gating); the CIAM sign-up/sign-in flow;
the iOS Shortcut's URL-embedded function key; the private git
repository and its full history.

**Trust boundaries:** Internet ↔ Function App is JWT-gated for reads
and the one write route, function-key-gated for ingest. Internet ↔
MCP Container App has **no boundary** - flat, unauthenticated.
Internet ↔ Static Web App is public by design (static assets), with
auth enforced client-side plus server-side on the API it calls.
Function App / MCP App ↔ Azure SQL is managed-identity only,
scoped to `db_datareader`(+`db_datawriter` for the Function App) -
confirmed against deployed reality, not just `sql/*.sql` intent.
Function App ↔ Blob Storage and ↔ Azure Maps are managed-identity
only, each scoped to the single resource they need (confirmed via
`az role assignment list`, not assumed). Browser ↔ CIAM tenant is
standard OIDC.

## Findings
_Completed 2026-08-03. Live-verified against deployed Azure/GitHub
state, not just code/docs, per the method above._

| # | Area | Severity | Finding | Exploitability | Fix | Status |
|---|------|----------|---------|----------------|-----|--------|
| 1 | AuthN/AuthZ | High | MCP server (`ca-track-telemetry-mcp`) has zero authentication and public ingress (`external: true`, no IP restrictions, no client cert, no Container Apps auth config) - any of the 4 MCP tools can be called by anyone who has the FQDN, returning every session's GPS-tied telemetry. | Only requires discovering the FQDN; no credential needed at all. | OAuth 2.1 + PKCE via Entra - already its own tracked v1.0 backlog item, deliberately sequenced to run right after this review so the review shapes it. | Tracked (v1.0 backlog item, not fixed in this pass) |
| 2 | AuthN/AuthZ | High | Dashboard/API authorization is "any valid CIAM login," not "the owner." `dbo.sessions.driver_id` exists (added Block 5) but is never referenced in `ingest/queries.py` or `function_app.py`; the CIAM `SignUpSignIn` flow allows self-service email+password registration. Any self-registered account gets full read of all telemetry plus write access (create_event, create_car, session PATCH). | Bounded today by the dashboard URL not being published anywhere. The planned v1.0 docs-baseline/portfolio site risks publishing that exact URL, which flips this from obscure to trivially discoverable. | Immediate: restrict the CIAM user flow to invite-only / disable self-service sign-up. Durable: driver_id-scoped authorization before v2.0 multi-user. | **Needs your action** - requires an Entra portal change; I hit an interactive-auth wall trying to inspect/change the CIAM user flow non-interactively from this environment (`AADSTS530035`, needs `az login` device-code sign-in for the CIAM tenant). |
| 3 | Dependencies | High (CVSS 7.5) | `cryptography` 47.0.0 (pulled transitively via `PyJWT[crypto]`/`python-tds`) carries GHSA-537c-gmf6-5ccf - a statically-linked vulnerable OpenSSL, network-exploitable, no auth required. Fixed in 48.0.1; found via `pip-audit` against both `requirements.txt` and `mcp_server/requirements.txt`. | Network attack vector, no privileges/user interaction required (per the GHSA). | **Turns out not fixable with a simple floor.** `pyOpenSSL<26.2` is already pinned (X509.get_extension(), used by `python-tds`'s TLS hostname check, was removed in 26.2) - but every pyOpenSSL release below 26.2 caps `cryptography` below 48 (26.1.0 itself requires `cryptography<48,>=46`). Adding `cryptography>=48.0.1` alongside the existing pin makes the two constraints mutually unsatisfiable; pip doesn't error on that, it silently backtracks to the oldest pyOpenSSL with a loose-enough bound (22.0.0, from 2022), which is incompatible with cryptography 50.x and crashes at import. **This shipped to production**: deployed it, the Function App came back "Running" with **zero functions registered** (confirmed via `/admin/functions` returning `[]` and every route 404ing instead of the expected 401) - a real, if brief, full outage of every API route. Reverted the floor in both requirements files immediately and redeployed; verified restored (`/api/sessions` back to 401, all 14 routes re-registered, a real MCP tool call against the redeployed Container App returned live data). Real fix needs `python-tds` to drop its `X509.get_extension()` dependency (already flagged as a known migration in the existing pin comment) before `pyOpenSSL`/`cryptography` can move past this ceiling - not a security-review-scope fix, handing to the engineering review's dependency-pinning-policy item. | **Reverted, not fixed** - CVE remains open, now correctly documented as blocked rather than silently unpinned. Redeployed Function App + MCP Container App back to the known-working (still-vulnerable) state; both verified live. |
| 4 | Secrets | Medium | Orphaned SQL-authenticated database user `mcp_reader` (created 2026-07-03, `db_datareader`, password auth) existed in `free-sql-db-7848405`, undocumented in any `sql/*.sql` migration or project memory - predates the MCP server's managed-identity setup and was never cleaned up. Inert only because `azureADOnlyAuthentication=true` blocks all SQL/password logins server-wide (confirmed against Microsoft Learn - that setting does cover contained DB users, not just server logins). | None today (blocked by Entra-only auth), but becomes a live, unaccounted-for credential of unknown provenance/strength the moment that setting is ever toggled off for any reason (troubleshooting, misconfiguration). | `DROP USER mcp_reader`. | **Fixed** - dropped directly against live prod DB, verified removed. |
| 5 | Client-side | Medium | No CSP or `X-Frame-Options` on the Static Web App (`staticwebapp.config.json` only set `navigationFallback`). Azure SWA does apply good defaults - confirmed live via `curl -I` (HSTS, `X-Content-Type-Options`, `Referrer-Policy`, `X-XSS-Protection` all present) - but nothing restricts script sources or framing. Combined with MSAL's `cacheLocation: "localStorage"` (bearer tokens readable by any script on the page, persist cross-tab), an XSS or clickjacking bug would have a full token-theft blast radius. | Requires a separate XSS/clickjacking bug to actually exploit - this finding is about blast-radius reduction, not a standalone hole. | Added a `globalHeaders` CSP (`frame-ancestors 'none'`, scoped `connect-src` to the Function App + CIAM authority, no `unsafe-eval`) and `X-Frame-Options: DENY` to `staticwebapp.config.json`. | **Deployed** (2026-08-03) - CSP/X-Frame-Options confirmed live via `curl -I`, and the page shell/JS/CSS/favicon all load correctly (200s, all same-origin, satisfying the policy). **Not yet browser-verified**: the actual interactive sign-in flow (redirect to CIAM, silent token renewal, authenticated API calls, satellite image fetch) - not automatable here per this project's existing verification pattern for interactive Entra sign-in. Worth a real check given the same deploy also carries the unverified `scp` claim check (finding #6) on the backend it talks to. |
| 6 | AuthN/AuthZ | Low | `ingest/api_auth.py` validated signature/audience/issuer/expiry correctly but never checked the token's `scp` claim actually contains `access_as_user` - any token this API's JWKS could verify for the right audience would pass, not just ones that consented to that specific delegated scope. | Low in practice (Entra typically only issues audience-matching tokens for scopes actually consented to), but the spec explicitly asked to verify scope enforcement is real, not assumed - and it wasn't being checked at all. | Added an explicit `scp` claim check (`REQUIRED_SCOPE = "access_as_user"`) in `validate_bearer_token()`. | **Deployed** (2026-08-03 redeploy) but **not yet verified live** - still needs a real authenticated sign-in through the actual dashboard to confirm the `scp` claim shape assumption holds for this CIAM tenant (getting this wrong would 401 legitimate sign-ins; interactive Entra sign-in isn't automatable from this environment, same limitation noted throughout this project's auth work). |
| 7 | Secrets | Low | Real Azure Maps client ID and real SQL server/database/storage resource names were hardcoded in the git-tracked `local.settings.json.example` (the pre-existing known item from an earlier manual review). Not credentials - Maps auth is AAD-token-based, no key exposed - and the repo is confirmed **private** (checked via GitHub API), so exploitability was already low, but it's real-resource disclosure in a file literally named `.example`. | Low (private repo; disclosure aids reconnaissance at most, not direct access). | Replaced with placeholder values. | **Fixed.** |
| 8 | Network posture | Low | Storage account `racechronoraw` network default action is `Allow` (open to all networks). Blob public access is separately disabled at the account level (`allowBlobPublicAccess: false`), so this isn't public data exposure - just unrestricted network reachability for authenticated (managed-identity) calls. | Low - still requires a valid Azure AD token with the right RBAC role; network openness alone grants nothing. | Already tracked as its own v1.x backlog item ("Lock storage account networking to selected networks"). | Already tracked, no new action here. |
| 9 | Data protection | Low | No Blob lifecycle/retention policy - raw CSVs (personal GPS traces) are retained indefinitely with no automated deletion path. Consistent with the "raw data is sacred" guiding principle (System of Record), so likely intentional, but was an unexamined default rather than a documented decision. | N/A - this is a policy gap, not a technical exploit. | **Decision, recorded here per the "Personal location data" principle's pointer to this doc:** retention is intentionally indefinite - the archived CSV is the system of record and there is currently no deletion path, by design, not oversight. Revisit if/when a driver ever wants their data removed (relevant before v2.0 multi-user, where "delete my data" becomes someone else's request, not just a hypothetical). | Documented; no infra change. |
| 10 | AuthN/AuthZ | Low (accepted risk) | `/api/ingest`'s function key travels as a URL query parameter embedded in an iOS Shortcut (iCloud-synced if Shortcuts sync is on). Correctly scoped to a **per-function** key (not the host master key, confirmed via `docs/ios_shortcut.md`'s `--function-name ingest`), limiting blast radius to "write arbitrary sessions" (dataset poisoning) rather than broader Function App control. | Requires the key to leak first (device compromise, iCloud account compromise, or shoulder-surfing the Shortcut). Worst case is data poisoning, not data disclosure or infra compromise. | Accepted for a single-user personal project. Revisit rotation cadence or a header-based secret if this ever becomes multi-device/multi-user. | Accepted risk, documented. |
| 11 | Dependencies | Informational | `react-router`/`react-router-dom` have 2 high-severity npm advisories (GHSA-qwww-vcr4-c8h2, RSC-mode CSRF bypass) per `npm audit`. | Not exploitable in this app - the dashboard is a client-only Vite SPA using client-side routing only; it doesn't use React Server Components or server actions, which is the vulnerable code path. | None needed now; note for the next routine dependency bump (current fix requires a breaking downgrade per `npm audit fix --force`, not worth forcing for an inapplicable CVE). | No action needed. |
| 12 | Dependencies/Supply chain | Informational | Could not verify GitHub secret scanning / push protection / Dependabot alert status from this environment - no `gh` CLI available, and the connected GitHub MCP server doesn't expose repo `security_and_analysis` settings. | N/A | Manually check/enable under repo Settings -> Code security. | **Needs your action** - can't verify or enable from here. |
| 13 | Network posture | Informational | No API Management / rate limiting in front of `/api/ingest`. | Requires the function key to already be known (see #10). | Already tracked as its own v1.0 item ("API Management in front of the ingest endpoint"). | Already tracked, no new action here. |

**Confirmed clean (no finding):** full git-history secret sweep (common
credential patterns - AWS/GitHub/Google/Slack keys, connection
strings, PEM blocks - found nothing beyond the resource-identifier
disclosure in #7); managed-identity story holds against deployed
reality (Function App MI has `Storage Blob Data Contributor` scoped
to `racechronoraw` only + `Azure Maps Data Reader` scoped to
`maps-track-telemetry` only + SQL `db_datareader`/`db_datawriter`;
MCP Container App MI has SQL `db_datareader` only; no broader RBAC
grants on either); `@require_auth` present on every read/write route
except the intentionally function-key-gated `/api/ingest`
(enumerated all 14 routes in `function_app.py`); no handler touches
the DB before token validation; CORS on the Function App restricts to
exactly the SWA origin, credentials not included; Azure SQL server is
Entra-only auth with TLS 1.2 minimum; MSAL token refresh uses the
correct `acquireTokenSilent` -> `acquireTokenRedirect` fallback
pattern; no secrets found in the built dashboard JS bundle (Vite only
inlines `VITE_`-prefixed vars, all of which are intentionally-public
SPA values).

**Deferred to next review pass (not high-severity, don't block 1.0):**
re-run this whole review before v2.0 multi-user, since driver-scoped
authorization (finding #2's durable fix) changes the trust model
fundamentally, not just incrementally.
