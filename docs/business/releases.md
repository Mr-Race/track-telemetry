# Releases and roadmap

*What shipped, what's next, and why the order is what it is. The
engineering record is [`docs/BACKLOG.md`](../BACKLOG.md) and
[`CHANGELOG.md`](https://github.com/Mr-Race/track-telemetry/blob/main/CHANGELOG.md); this is the narrative.*

## Versioning

| | Meaning |
|---|---|
| **0.x** | Pre-stable. Schemas change freely, nothing is promised |
| **1.0** | Core loop finished, nothing known-broken in production, all endpoints secured, docs baseline exists, both review gates passed |
| **1.x** | Additive and backward-compatible |
| **2.0** | Reserved for breaking or identity-level change |

## v0.9.0 — first tagged release · 2026-08-12

Cut deliberately as 0.9.0 rather than 1.0.0, with two v1.0 items still
open. The point was to find the release process broken *before* the
release that matters — and it worked: running the freshly-written
runbook exposed two errors in it within the hour.

**What it contains**

- **Conversational analysis over real data.** The MCP server
  authenticated with OAuth 2.1 via Entra and working as a Claude
  connector. This is the product's premise, and it was nearly descoped
  when it proved difficult — the right call was to fix it, not cut it.
- **Event summary pages** — hero stats, per-session pace, corner story,
  weather.
- **Idempotent ingest.** Re-uploading a CSV refreshes the session it
  already created instead of duplicating it.
- **A migration ledger** with checksum drift detection.
- **Test suites where there were none** — 149 Python and 23 dashboard
  tests, gating in CI on every push.
- **A responsive dashboard** that no longer scrolls sideways at any
  phone width.
- **Historical archive fully reconciled** — 15 sessions, 127 laps, 1,520
  segment times, four of them recovered from the blob archive after the
  local copies were gone.

**What it fixed** — the honest list: sign-in that appeared to work while
every API call returned 401; every session displaying 4–5 hours late; an
instructor-driven session counting as a personal best; a median lap
calculation that took the wrong value on an even lap count; corner
metrics that could merge two passes through the same zone.

## v1.0 — remaining

Two items, one of which is not fully in my hands:

1. **Pedal-position calibration.** The parser reads the new
   `accelerator_pos` channel, and each session now records which channel
   produced its values. What remains is storing the calibration
   constants and applying them on read.
2. **This documentation set.**

## v1.x — next

- **A demo account with fictional data**, so the platform can actually
  be seen from a CV link without an account. Fictional rather than
  anonymised: GPS traces are personal location data even with the name
  removed.
- **Claude-generated session assessments** stored on the session at
  ingest — the first component in the system with a real per-use cost,
  designed accordingly.
- **Upload from the event page**, as a fallback for when the phone
  shortcut fails at the track.
- **One-tap ingestion**, retiring the manual prompts.
- Gzip before upload; paddock cellular is weak and the files are 15–20 MB.

## v2.0 — the platform learns to replay and share

Lap replay animation, and a multi-user version where friends upload
their own sessions and race each other's ghost laps. This is the point
at which the free-tier cost model stops holding, which is why it is a
major version rather than an increment.

## How the order gets decided

Roughly, in descending priority:

1. **Anything that fails at the track.** A bug in the paddock cannot be
   fixed from a phone, so pre-event hardening outranks features. Three
   ingest defects were fixed on 2026-08-13 for exactly this reason.
2. **Anything that gets more expensive by waiting.** Recording the pedal
   channel per session landed before the calibration work it serves,
   because every event without it widened a span of ambiguous data.
3. **Anything that proves the system works** — tests, verification,
   release mechanics.
4. **Features.**
