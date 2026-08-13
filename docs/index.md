# Track Telemetry Platform

A personal HPDE track-day telemetry platform. Every lap driven at a race
track is captured from the car, stored in the cloud, enriched, and made
queryable — through a web dashboard, and conversationally through Claude.

Built solo, time-boxed, on Azure free and consumption tiers.

<div class="grid cards" markdown>

- **[Start with the story](business/overview.md)**

    What it is, why it exists, and what it has proven. Written for
    non-technical readers.

- **[How it works](business/how-it-works.md)**

    One lap of data followed from the car to a conversation. No jargon.

- **[Architecture](technical/architecture.md)**

    The components, the flow, and where the sharp edges are.

- **[Decision log](technical/decisions.md)**

    What was decided, what it cost, and what would reverse it.

</div>

## The shape of it

```
RaceChrono (iPhone + OBD-II)  ──▶  Azure Function  ──┬─▶  Azure SQL
        CSV via iOS Shortcut         parse/enrich    └─▶  Blob archive
                                                            │
                        ┌───────────────────────────────────┘
                        ▼
            MCP server ──▶ Claude          React dashboard ──▶ browser
            (OAuth 2.1)                    (Static Web Apps)
```

## Current state

**v0.9.0**, approaching 1.0. The core loop is complete: capture,
enrichment, a secured dashboard, and conversational analysis over real
session data. See [releases and roadmap](business/releases.md) for
what's left and why the order is what it is.

## Documentation

- **[Business](business/index.md)** — plain language: what it does, what
  it costs, how it was built.
- **[Technical](technical/index.md)** — architecture, schema, API,
  runbook, decisions.
- **[Way of working](WAY-OF-WORKING.md)** — the practices this project
  holds itself to. Every rule exists because something broke without it.

!!! note "This repository is public"
    Security findings are handled privately and never appear in issues,
    tracked documents, or commit messages. See
    [SECURITY.md](https://github.com/Mr-Race/track-telemetry/blob/main/SECURITY.md).
