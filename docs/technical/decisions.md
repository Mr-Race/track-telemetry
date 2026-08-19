# Decision log

Architecture decisions, newest first. Each records what was decided,
what it cost, and what would reverse it. A decision whose reasoning
only exists in a chat log does not exist.

---

## ADR-010 — Record the pedal channel per session

**2026-08-13 · Accepted**

`corner_metrics.throttle_pos_apex_pct` stores a raw percentage. The
channel behind it changed on 2026-08-10 when RaceChrono was
reconfigured from throttle position to true pedal position (PID 0x49).
The two have different rest and full points — 18.82% and 94.90% for the
pedal — so a stored value cannot be normalised without knowing its
source, and nothing recorded it.

**Decision.** Add `sessions.pedal_channel`, populated at ingest from a
value the parser already computed and discarded. Calibration is keyed on
`(car, channel)`.

**Alternative rejected:** keying calibration on a date boundary. Same
information, implicit and fragile.

**Cost of delay:** every event run without it widens the span of
ambiguous rows. This is why it landed before an event rather than with
the calibration work it serves.

---

## ADR-009 — Match channel sources by device, never by rate

**2026-08-13 · Accepted**

RaceChrono writes a channel's source as `<rate>: <device>` — `100: gps`.
The prefix is the logging rate, so changing a rate in the app rewrites
every source string that device produces. The parser matched the literal
`100: gps` and would have failed every upload with `Column not found:
latitude`.

**Decision.** Match on the device half, accepting renames (`gnss`) and
qualified names (`gps (u-blox)`).

**Alternative rejected — and it was the first proposal:** fall back to
matching by column name alone. Real exports carry **three** `speed`
columns (gps, obd, calc), so dropping the source qualifier would bind
lap times and corner metrics to OBD wheel speed. That trades a loud
failure for silently wrong data. An unrecognised device still raises,
now naming the sources present.

**What made this findable:** the fixtures claimed to reproduce the
three-source layout and built one column, so no test could have caught a
mis-bind. Verification is only as good as its ability to fail.

---

## ADR-008 — The App ID URI must not end in a slash

**2026-08-12 · Accepted**

MCP OAuth failed for a day with no Entra sign-in log at all. Entra
compares the RFC 8707 `resource` parameter to the App ID URI literally.
Pydantic's `AnyHttpUrl` appends a trailing slash; Entra refuses to store
an App ID URI ending in one. The two could never match.

**Decision.** `MCP_APP_ID_URI` is normalised with `.rstrip("/")`, and the
metadata route is replaced rather than relying on the framework's.

**The lesson worth more than the fix:** the rejection happens *before*
authentication, so Entra writes no sign-in log. Absence of a log looked
like a credentials problem and was actually proof of where the failure
was. When an error leaves no trace, look before authentication.

---

## ADR-013 — Don't hand-roll TLS hostname verification

**2026-08-18 · Accepted**

`ingest/_pytds_tls_compat.py` replaces pytds's certificate hostname
check, to unpin pyOpenSSL/cryptography for GHSA-537c-gmf6-5ccf. The
replacement was written by hand.

**Decision.** Delegate to `service_identity`, the audited RFC 6125
implementation the pyOpenSSL/Twisted ecosystem standardised on. Our
shim is now four lines: call it, convert an exception into the bool
pytds expects.

**Why.** This code decides whether the server we reached is the server
we asked for. The list of things it has to get right is long and each
entry is a documented way to accept the wrong certificate: Common Name
being inadmissible when subjectAltName is present, wildcards spanning
exactly one label and never the bare domain, case-insensitivity,
trailing root dots, IDNA, IP SANs.

The hand-rolled version got one of them wrong. It checked CN **first**
and returned on a match, so a certificate whose SAN covered
`attacker.example.com` and whose CN read the database host would have
been accepted for the database host. Chain validation against certifi
makes that hard to reach — an attacker needs a CA-issued certificate
naming the victim in its CN — but hostname verification is not held to
"hard to reach".

Two smaller things it also got wrong: comparisons were case-sensitive
and did not strip the trailing root dot, both of which failed *closed*.
Safe, but they reject valid connections rather than invalid ones, which
is the kind of bug that gets diagnosed as a network problem.

**Cost.** One dependency (`service_identity`, plus `pyasn1`/`attrs`).
Cheap next to maintaining a hand-written matcher nobody will re-audit.

**A subtlety worth recording.** `VerificationError` and
`CertificateError` are siblings, not parent and child. Catching only the
first let a certificate with no subjectAltName raise out of a function
pytds expects to return a bool — crashing mid-handshake instead of
rejecting cleanly. Found by a test, not by reading.

**Revisit if:** `service_identity` becomes unmaintained. The answer then
is a different audited library, not a hand-rolled matcher.

---

## ADR-012 — The demo is a static site, not a live read-only backend

**2026-08-17 · Accepted · supersedes Parts 1 and 2 of
`docs/specs/demo-and-public-domain.md`**

The spec proposed fictional data in the production database, isolated by
a `Demo` driver row, served either behind a published Entra credential
or through unauthenticated read routes.

**What killed it.** The spec assumed isolation was nearly free because
"the schema already carries driver scoping". It does not: `driver_id`
exists only on `dbo.sessions`, and **10 of 12 read functions have no
driver filter at all** — issue #2 scoped personal bests, nothing more.
Cars, consumables, events and organizations have no driver link. Demo
isolation would have meant threading a filter through ten queries whose
failure mode is publishing real GPS traces.

**Decision.** Build the demo as a static site: the same React app,
compiled with a demo flag, reading bundled JSON instead of the API, at
`demo.mr-race.com`.

This does not solve the isolation problem — it **deletes** it. Fictional
data never shares a database with real data, so no `WHERE` clause can be
forgotten. It also removes the auth question entirely: no credential to
publish, no anonymous endpoint reopening a finding the security review
closed, and no serverless resume for a visitor to wait through.

Cheap because of one existing line — `API_BASE = import.meta.env
.VITE_API_BASE ?? "/api"` — plus a single `getJson` chokepoint and one
auth gate in `App.tsx`.

**The cost, stated plainly.** A static site cannot demonstrate the
conversational layer, which the spec correctly calls the differentiator.
That is covered instead by Part 4's screen recording: a real question
answered from real data. Static dashboard for *look at it*, recording
for *watch it think*.

**Revisit if:** the demo needs to show live or interactive analysis, at
which point the isolation work becomes unavoidable and should be costed
honestly rather than assumed cheap.

**Fixtures live in `dashboard/demo-fixtures/`, not `dashboard/public/`.**
Vite copies `public/` into *every* build, so fixtures there would have
shipped 35 fictional JSON files to www.mr-race.com on the next release —
and `cut_release.py` runs `npm run build` then deploys, so it would have
happened unattended. `npm run build:demo` copies them into the demo
bundle instead. Caught by checking whether production served a demo
fixture; it did not, but the build already contained one.

**Track geometry is reused, not invented** (AC, 2026-08-17). Corner apex
coordinates for NJMP are not personal data; the sessions on top of them
are fictional.

---

## ADR-011 — One SQL connection per *thread*, not per process

**2026-08-13 · Accepted · supersedes the connection half of ADR-007**

ADR-007 shared a single connection across the whole process. On
2026-08-13 every dashboard endpoint began returning 500:

    InterfaceError: Invalid TDS marker: 4(4)
    InterfaceError: Cursor is closed

**Cause.** pytds connections are not thread-safe and allow one active
cursor; `connection.cursor()` cancels whatever cursor is already open on
that connection. A dashboard page load fetches sessions, detail, summary
and consumables in parallel, so two requests routinely shared one wire
and desynchronised the TDS stream. The liveness probe compounded it by
running `SELECT 1` on the shared connection while another thread was
mid-query.

**Decision.** Connections are thread-local. The connect still happens
under a lock, so concurrent first-callers queue behind one serverless
resume rather than each triggering their own.

This keeps what ADR-007 was actually for — not paying the resume per
*request* — and drops the part that was never justified: sharing one
connection between threads. A handful of worker threads pay the resume
once each.

**What made it survive review.** The test suite asserted *"N concurrent
callers share a single connect"*, which pinned the broken behaviour as
the correct behaviour. A passing test can encode a bug. The replacement
asserts each thread gets its own connection, and was checked against a
replay of the old design to confirm it fails there.

**Revisit if:** connection count per process becomes a constraint, which
would mean a real pool with checkout/checkin rather than a return to
sharing.

---

## ADR-007 — One pooled SQL connection and credential per process

**2026-08-11 · Superseded in part by ADR-011**

The serverless database auto-pauses after 60 idle minutes and the first
connect waits 30-60s for a resume. Every request opened its own
connection and credential, so three concurrent calls on one page load
each paid it: measured 48.7s / 47.7s / 46.7s.

**Decision.** One connection and one credential per process, with a
liveness probe, and the lock held across the connect so concurrent
callers queue behind a single resume.

**Revisit if:** the app moves off Consumption, or the database stops
auto-pausing.

---

## ADR-006 — Idempotency keyed on content, not filename

**2026-08-10 · Accepted**

The iOS Shortcut sends `filename` optionally. Without it the ingest
route invented a unique name per upload, which is how session 14
duplicated session 6.

**Decision.** Key on the SHA-256 of the uploaded bytes. A re-upload
refreshes the existing session and writes no second blob.

**The general lesson:** a uniqueness check only protects rows that carry
the key. Sessions loaded before the column existed were duplicated
exactly this way, and had to be found by fingerprinting CSVs against
stored lap-time sequences.

---

## ADR-005 — Normalise on read; never rewrite raw data

**2026-08-10 · Accepted**

Pedal position needs calibration constants applied. They could be baked
in at ingest.

**Decision.** Store raw; normalise on read. If a PID or a sensor ever
changes, historical sessions would otherwise double-correct, and the
error would be invisible.

**Corollary:** every raw CSV is archived in Blob and never rewritten.
Derived values are recomputed from it, so a parser fix can be replayed
across all of history.

---

## ADR-004 — The MCP server is read-only

**2026-07 · Accepted**

It runs with a `db_datareader` managed identity.

A conversational interface that can also write has a far larger blast
radius for a much smaller benefit. Ingest is a separate, authenticated
path.

---

## ADR-003 — Entra External ID for dashboard sign-in

**2026-07 · Accepted**

MSAL browser, OAuth 2.1 + PKCE, bearer-token-protected API.

**Gotcha that cost real time:** sign-in appeared to work while every API
call returned 401. A reloaded MSAL session has cached accounts but no
*active* one. `restoreActiveAccount()` sets it explicitly on load, and
takes the instance as a parameter so it can be tested.

---

## ADR-002 — Power BI dropped from the roadmap

**2026-07-22 · Accepted**

React on Static Web Apps is the sole visualization layer.

Power BI would have meant a per-seat licence, breaking the $0 constraint
that shapes the rest of the platform. The dashboard also has to be
readable on a phone in a paddock, which is not Power BI's strength.

---

## ADR-001 — Azure SQL as the source of truth, Blob as the archive

**2026-06 · Accepted**

Relational storage for sessions, laps, corners and segment times —
the questions asked of this data are overwhelmingly relational
("my best lap through T5 this year, excluding instructor sessions").

Raw CSVs live in Blob forever. The database can be rebuilt from them;
they cannot be rebuilt from the database.

**Revisit if:** sample-level telemetry needs storing per lap rather than
per corner, which is the v2.0 replay work. That is a derived,
server-side artifact — not a replacement for the archived original.
