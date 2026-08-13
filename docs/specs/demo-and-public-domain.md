# Spec: Demo Access and Public Domain

Status: scoped 2026-08-13. Two related pieces of work that share a
purpose — letting someone who is not AC see the product without
credentials, and giving it a real address.

Scheduled: v1.x. Supersedes the v1.x backlog line "Login page on a
custom domain (www.mr-race.com)".

---

## Why this exists

The repo went public on 2026-08-05 and is linked from job
applications. A visitor currently gets code and documentation and
nothing else: the dashboard is behind Entra sign-in, and the MCP
server has required OAuth since 2026-08-12.

That is the wrong outcome for the two audiences that matter:

- **A hiring manager or recruiter** who will spend two minutes and
  will never configure a connector.
- **A friend or peer** who will actually try it, and for whom the
  conversational layer is the interesting part.

The dashboard is the commodity half of this product. The ability to
ask questions of the data in plain language is the differentiator.
A demo that only shows the dashboard demonstrates the wrong thing.

---

## Part 1 — Demo data

### Fictional, not anonymised

Generate plausible fake sessions rather than stripping identifiers
from real ones.

Rationale: per the guiding principle recorded 2026-08-02 and
`docs/specs/security-review.md`, session data is personal location
data — GPS traces tied to a driver, a car and a timestamp. Removing
a name does not change that. A demo built on real traces is a
data-classification problem that will resurface every time the demo
is extended.

Fictional data has no such constraint, which is what makes the rest
of this spec simple.

### Isolation via `driver_id`

The schema already carries driver scoping, and the filtering work
done for issue #2 (instructor session misattribution) established
the query pattern.

- One `Demo` driver row.
- Every demo session, lap, corner metric and segment time hangs off
  it.
- Demo rows must never appear in AC's queries, and real rows must
  never appear in demo queries.
- Verification is by enumeration, not spot check: assert that every
  read path returns zero real rows when scoped to the demo driver,
  and zero demo rows otherwise. Same discipline applied during the
  security review.

### Read-only

No ingest, no `PATCH /api/sessions/{id}`, no consumable
replacement, no event creation. A demo visitor should be unable to
change anything.

### Seed data requirements

Enough that the analysis features have something to show. An empty
or thin demo is worse than none.

- Two or three events across at least two track configurations
- Multiple sessions per event, with a visible progression within
  one event so the first-vs-last corner delta table has an arc to
  display
- Weather populated on every session
- Segment times present, so optimal lap and gap-to-optimal render
- OBD channels populated, so apex throttle and exit RPM are not
  null
- Consumables across a range of remaining life, including one
  overdue, so the status colours are all exercised

### Open question — dashboard auth for the demo

Two options, and this needs deciding before implementation:

**Option A — published Entra credential.** A real user in the CIAM
tenant, scoped to the demo driver, with the username and password
in the README. Simplest, reuses all existing auth. The cost is
publishing a working credential, and any future scope error becomes
a real exposure.

**Option B — unauthenticated read path.** Separate routes that
hard-code the demo `driver_id` server-side and cannot accept a
driver parameter. No credential to leak. The cost is reintroducing
an anonymous endpoint — the exact finding category closed in the
security review — so it carries the burden of proving it cannot
return anything else.

Option B is cleaner in principle and riskier in practice. Whichever
is chosen, the enumeration test above is the gate.

---

## Part 2 — Demo MCP server

The point of the product is the conversation. Demonstrating it
requires an MCP endpoint a visitor can actually connect to.

### Design

- A **second Container App** running the same image, deployed as
  e.g. `ca-track-telemetry-mcp-demo`.
- Hard-coded to the demo `driver_id` — not parameterised, not
  configurable at request time.
- Reachable at `mcp-demo.mr-race.com`, following the same custom
  domain pattern proven for `mcp.mr-race.com` on 2026-08-12
  (`asuid` TXT plus CNAME).
- **Unauthenticated, deliberately.** The OAuth requirement on the
  production MCP server exists to protect real location data. There
  is nothing to protect here, and requiring OAuth would defeat the
  purpose — a visitor is not going to complete a consent flow
  against a stranger's identity tenant.

### Consequence worth stating

An unauthenticated MCP server is a defensible decision *only*
because the data behind it is fictional. If demo data ever becomes
anonymised real data, this decision must be revisited. Recording it
here so the reasoning does not get lost.

### Visitor cost

Custom connectors are available on Claude's free plan, limited to
one. A visitor spends their single slot on this. Acceptable for
someone genuinely interested; a barrier for everyone else — which
is what Part 4 addresses.

---

## Part 3 — mr-race.com as the public address

### Target state

- `mr-race.com` and `www.mr-race.com` serve the dashboard's public
  landing page (`LandingPage`, shipped 2026-07-23)
- `mcp.mr-race.com` — production MCP server (already live)
- `mcp-demo.mr-race.com` — demo MCP server (Part 2)

### Existing DNS to clean up

The zone at GoDaddy currently carries leftovers from earlier
projects:

| Record | Value | Action |
|---|---|---|
| `A @` | `15.197.225.128` | GoDaddy parking — remove |
| `A @` | `3.33.251.168` | GoDaddy parking — remove |
| `CNAME www` | `azureresumeach.azureedge.net` | Stale Azure CDN classic endpoint from a previous resume site; CDN classic is being retired. Replace. |
| `CNAME pay` | `paylinks.commerce.godaddy.com` | GoDaddy Payments default, unused — remove |
| `CNAME _domainconnect` | GoDaddy | Leave |
| `NS`, `SOA` | GoDaddy | Leave |
| `TXT @` | `MS=ms42749047` | Entra domain verification — leave |
| `TXT asuid.mcp`, `CNAME mcp` | Container App | Leave |

### The apex problem

Azure Static Web Apps custom domains want a CNAME. DNS does not
permit a CNAME at the zone apex, and GoDaddy does not offer
ALIAS/ANAME flattening.

Options:

1. **`www` as canonical, apex redirects.** Point `www` at the SWA
   hostname via CNAME; use GoDaddy's forwarding to send the apex to
   `www`. Simplest, works today, but the redirect is an HTTP hop
   rather than a real DNS answer.
2. **Move DNS to Azure DNS.** Supports alias records at the apex,
   pointing directly at the Static Web App. Cleanest technically,
   and consolidates DNS with the rest of the platform — consistent
   with the cloud-native, Azure-first guiding principle. Requires
   changing nameservers at the registrar.

Option 2 is the better end state. Option 1 is acceptable if the
nameserver change is not worth doing now.

### Steps

1. Decide apex strategy above
2. Add the custom domain in the Static Web App, take the TXT
   validation record it issues, add it at GoDaddy
3. Add the `www` CNAME to `salmon-moss-0a7e4b70f.7.azurestaticapps.net`
4. Remove the parking A records and the stale `azureedge` CNAME
5. Confirm the managed certificate issues (free, automatic)
6. Update the Entra SPA app registration redirect URIs to include
   the new origin — **this will break sign-in if missed**
7. Update CORS on `func-track-telemetry-ingest` to allow the new
   origin alongside the existing SWA origin

Step 6 is the one most likely to be forgotten and the one that
breaks production. Redirect URI mismatches have already cost time
once (see the Block 5 note about non-default ports).

---

## Part 4 — The zero-setup demo

Neither Part 1 nor Part 2 helps the visitor who will not configure
anything. Two things cover that audience:

- **A short screen recording** — sixty seconds of a real question
  being asked of real data and answered. Linked from the README and
  from the landing page. For most viewers this will be the only
  demo they ever see, and it is more persuasive than a URL they
  will not use.
- **The stored session assessment** — a short Claude-generated
  summary written at ingest and displayed on the session detail
  page. Tracked separately; its real value is exactly this: it
  demonstrates the conversational capability to someone who never
  connects anything.

---

## Sequencing

1. Demo data generation and `driver_id` isolation (Part 1)
2. Custom domain (Part 3) — independent, can run in parallel
3. Demo MCP server (Part 2) — depends on 1, and on the domain if
   using `mcp-demo.mr-race.com`
4. Screen recording (Part 4) — last, once there is something to
   record
