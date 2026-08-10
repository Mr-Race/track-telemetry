# Way of Working

A reusable framework for solo-built projects. Drop this into a new
repo, adapt the specifics, and the practices below carry over.

Everything here was learned the hard way on this project — each rule
exists because something broke without it.

---

## 1. The backlog governs

One file, `docs/BACKLOG.md`, is the system of record. Read it first
in any session. It holds:

- **Guiding principles** — the decisions that constrain every future
  choice. Write these down the moment you make them, or you will
  relitigate them monthly.
- **Versioned scope** — what's in 1.0, what's 1.x, what's 2.0, what's
  parked. Anything without a version is a wish, not a plan.
- **A Done log** — dated, with the lesson, not just the outcome.

If a decision only exists in a chat, it doesn't exist.

## 2. Specs live in `docs/specs/`, the backlog points at them

Anything with more than three requirements gets its own spec file.
The backlog carries a one-line pointer.

A spec must pin **structure, hierarchy, and semantics** — not just
data. The first build of a spec'd page came out correct and ugly
because the spec described what to show and never how it should
look. Fonts and pixels are directional; layout and colour meaning
are binding.

## 3. Versioning is a commitment device

- **0.x** — pre-stable. Schemas change freely. Nothing is promised.
- **1.0** — the core loop works end to end, nothing known-broken in
  prod, all endpoints secured, docs exist, review gates passed.
- **1.x** — additive, backward-compatible.
- **2.0** — reserved for breaking or identity-level change.

The point isn't ceremony. It's that "1.0" forces you to name a
finish line, and everything you'd rather not do gets done before it.

## 4. Two review gates before 1.0

Both get a spec, a findings table with severities, and remediation
tracked as issues. High-severity findings block the release.

- **Engineering practices** — testing, CI/CD, migrations, dependency
  pinning, module structure, error handling, docs currency.
- **Information security** — secrets across full git history, auth
  and scope enforcement on every route, data classification,
  network posture, dependency CVEs, client-side handling.

Run security **before** any auth work, so the review shapes the
implementation rather than reviewing fresh code.

## 5. Verify against deployed reality, not source

The rule that has caught the most: **the code being right does not
mean production is right.**

- A deploy command's success message is not verification. Check the
  platform's own view — revision health, route list, live response.
- Enumerate rather than spot-check. "All 14 routes 401 without a
  token" is verification; "the one I tried worked" is not.
- After any deploy that could break access, make one real
  authenticated request before walking away.

Corollaries learned individually and painfully: a container platform
in single-revision mode will keep serving the last good revision
while the new one crash-loops; a dependency version floor can
silently backtrack and wipe every registered function.

## 6. Raw data is sacred

Whatever arrives from the source gets archived unmodified. Parse,
derive, and enrich downstream — never in place of the original.

- Compression is fine. Downsampling, column pruning, and format
  conversion before storage are not.
- Calibration and normalization happen **on read**, with constants
  in config. Bake them into ingest and the day you change the source
  every historical record double-corrects.
- Accept input variation rather than rewriting inputs. When a source
  renames a field, teach the parser both names — don't edit files.

## 7. Fail soft on anything external

Any call you don't control — a weather API, a sensor, a Bluetooth
device — must degrade to a null result, never block the pipeline.

And say so in the response. The ingest reply should state which
optional channels were found, so a dead sensor is visible at upload
time instead of discovered weeks later in the data.

## 8. Migrations need a record

Numbered SQL files applied by hand, with no record in the database
of what ran, means drift is detected by something breaking. Either
keep an applied-migrations table or accept that you're the record —
and if you're the record, write it in the Done log every time.

Platform quirk worth remembering: `ALTER` and a statement
referencing the new column must run as separate batches.

## 9. Pin dependencies, deliberately

Every unpinned dependency is a future outage on someone else's
release schedule. Pin, then bump on a schedule you choose.

## 10. Document failures, not just features

The Done log entries with the most value are the ones describing
what broke, why, and how it was caught. They're also the most
persuasive thing in the repo to anyone evaluating the work.

**But: publish findings only after they're fixed.** Open security
findings in a public repo are a disclosure. Use private advisory
drafts for anything unresolved, and publish the write-up once the
hole is closed.

## 11. Scope decisions are features

Writing down what the project is deliberately **not** is worth as
much as the roadmap. It stops the same idea resurfacing every few
weeks, and "we decided against this, here's why" is a stronger
answer than silence.

---

## Starting a new project with this

1. Create `docs/BACKLOG.md` with guiding principles, versioned
   scope, and an empty Done log.
2. Create `docs/specs/` — empty until something needs one.
3. Enable dependency alerts, secret scanning, and push protection
   before the first real commit.
4. Add `.gitignore` entries for raw data, local settings, and
   anything with a credential shape, on day one. Retrofitting this
   is the one mistake with no clean fix.
5. Write the first guiding principle before the first feature.
