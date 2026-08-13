# Architecture

A personal HPDE telemetry platform: a lap timer's CSV becomes something
you can ask questions of in plain English, and a dashboard you can read
in the paddock on a phone.

Everything runs on Azure free or consumption tiers. That constraint is
the source of several design decisions below, and is deliberate — see
[the cost model](../business/cost-model.md).

## The path a session takes

```
  RaceChrono Pro (iPhone + OBD-II dongle)
        │  CSV v3 export, 15-20 MB, ~87k samples
        │
        ▼  iOS Shortcut, share sheet
  POST /api/ingest ─────────────────────────────┐
  (Azure Functions, Python, Consumption)        │
        │                                       │
        │ parse ─ laps ─ corner metrics ─       │ raw original
        │ segment times ─ weather               ▼
        │                              Blob: racechrono-raw
        ▼                              (the archive; never rewritten)
  Azure SQL (serverless, free tier)
  the source of truth
        │
        ├──────────────────────┐
        ▼                      ▼
  MCP server              React dashboard
  (Container Apps)        (Static Web Apps)
  OAuth 2.1 via Entra     MSAL sign-in
        │                      │
        ▼                      ▼
  Claude (connector)      a browser
```

## Components

| Piece | Runs on | Auth | Notes |
|---|---|---|---|
| Ingest + read/write API | Azure Functions (Python 3.12, Consumption Y1) | Function key for `/api/ingest`; MSAL bearer token for everything else | `function_app.py` |
| Database | Azure SQL serverless, free tier | Entra only, no SQL logins | Auto-pauses after 60 idle minutes |
| Raw archive | Blob Storage | Managed identity | Container `racechrono-raw` |
| MCP server | Container Apps | OAuth 2.1 + PKCE via Entra | `mcp.mr-race.com`, read-only |
| Dashboard | Static Web Apps | MSAL (OAuth 2.1 + PKCE) | React + Vite + TypeScript, at `www.mr-race.com` |
| Telemetry | Application Insights | — | Ingest path instrumented |

Parsing is stdlib-only and lives in `ingest/`, separate from cloud
access in `ingest/cloud.py`. Both the Function App and the MCP server
import it, so there is one parser rather than two that drift.

## Decisions that shaped this

Recorded in full in the [decision log](decisions.md). The ones that
explain the diagram:

**The database is the source of truth; Blob is the archive.** Every raw
CSV is kept forever and never rewritten. Derived values are recomputed
from it, so a parser fix can be replayed across history. This is why
calibration is applied on read rather than baked in at ingest.

**One pooled SQL connection per process.** The serverless database
auto-pauses, and the first connect after a pause waits 30-60s for a
resume. When every request opened its own connection, three concurrent
calls on one page load each paid it separately — measured at 48.7s /
47.7s / 46.7s. Now they queue behind one resume, and everything after
is fast.

**The MCP server is read-only.** It runs with a `db_datareader`
identity. A conversational interface that can also write is a much
larger blast radius for a much smaller benefit.

**Power BI was dropped** (2026-07-22). React on Static Web Apps is the
sole visualization layer, to stay free-tier with no per-seat licence.

## Where the sharp edges are

- **The serverless resume.** The first upload of a track day pays it.
  Measured at 59s end to end for an 87k-sample file against a genuinely
  paused database, which is why the login timeout is 90s with a retry
  and `functionTimeout` is pinned to the 10-minute Consumption ceiling.
- **Channel names come from a phone setting.** RaceChrono writes each
  channel's source as `<rate>: <device>`, so changing a logging rate
  rewrites every source string. Sources are matched by device, never by
  the rate prefix. The qualifier can't simply be dropped either —
  `speed` appears three times in a real export (gps, obd, calc).
- **Events must exist before a session can be uploaded.** Ingest matches
  the CSV's track name and date against an existing event, and 400s if
  there isn't one. That failure happens in the paddock.

## Related

- [Schema and data dictionary](schema.md)
- [API reference](api.md)
- [Runbook](runbook.md)
- [Decision log](decisions.md)
- [MCP server setup](../mcp_server.md) · [iOS Shortcut](../ios_shortcut.md)
