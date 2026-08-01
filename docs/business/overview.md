# Track Telemetry Platform — The Business Story

*Audience: non-technical readers — recruiters, leadership peers,
LinkedIn. Written to be quoted from. Keep current per release; this
page is the narrative source of truth that posts and portfolio
material are carved from.*

## What it is
A personal motorsport analytics platform: every lap I drive at a
race track is automatically captured, stored in the cloud, enriched,
and made queryable — through a web dashboard, and conversationally
through an AI assistant ("how did my corner speeds improve since
June?" answered from live data, from my phone, in the paddock).

## Why it exists
Two reasons, honestly held:
1. **A real need.** I do high-performance driver education (HPDE)
   track days and analyze my telemetry to get faster. Pasting CSV
   files into chat tools session-by-session didn't scale.
2. **A capability demonstration.** I wanted proof — not claims —
   that I can architect and ship enterprise-grade cloud + AI
   systems: the same patterns (serverless, managed identity,
   event-driven ingestion, governed data, AI integration via MCP)
   that enterprises pay teams to deliver, built solo, time-boxed,
   at effectively zero cost.

## What it does today (v0.9, approaching v1.0)
- **Capture:** telemetry from my car (GPS + engine data, 20 samples
  per second) uploads from my phone in the paddock, seconds after a
  session ends.
- **Understand:** the platform computes lap times, per-corner
  minimum/entry/exit speeds, throttle and RPM at each apex, and
  flags warm-up/cool-down laps automatically.
- **Show:** a secured web dashboard — session history, per-corner
  analysis, track directory with satellite views, personal bests,
  friends' benchmark times, and a car-consumables life tracker
  (brake pads, fluids, tires).
- **Converse:** the database is connected to Claude via an MCP
  server, so analysis is a conversation: comparisons, trends, and
  coaching insights on demand, no files, no exports.

## Proof points
- **The analytics predict real performance.** The "optimal lap"
  method (best sector times stitched together) computed from one
  day's data predicted the personal best I would set the *next day*
  within 0.3 seconds — before I drove it.
- **The data catches lies.** The platform surfaced a duplicate
  upload, a mis-filed event, and an instructor-driven lap that was
  inflating my personal best — the kind of silent data-quality
  failures spreadsheet workflows never confess to.
- **Total infrastructure cost: effectively $0/month** (~$0.50
  lifetime to date), by design: every component is serverless and
  scales to zero, verified by a structured cost audit. The cost
  model is architecture, not luck.
- **Idea to launched MVP: three weeks of spare time.** Versioned
  roadmap (v1.0 launch scope, v1.x, v2.0) now governs releases.

## How it was built (the working model)
AI-assisted engineering with clear division of labor:
- **Human (me):** architecture, product decisions, domain
  vocabulary, review, and every judgment call — schema design
  trade-offs, security model, what ships in which version.
- **AI (Claude + Claude Code):** implementation, testing,
  deployment, documentation — delegated at the task level, reviewed
  at the outcome level.
- The backlog, specifications, and decision log live in version
  control and are maintained conversationally — from a phone, from
  a paddock, from anywhere. The tooling loop itself (chat ↔ repo ↔
  live data) is part of the demonstration.

This is the working model I believe enterprise technology teams are
converging on, practiced end-to-end on a real system with real
stakes (my own data, my own money, my own lap times).

## Platform, in one paragraph (for the technically curious)
Azure end-to-end: serverless SQL as the governed source of truth,
Blob storage for raw telemetry archive, Functions for event-driven
ingestion and APIs, Container Apps hosting the MCP server, Static
Web Apps serving a React dashboard, Entra ID (OAuth 2.1 + PKCE)
for identity, managed identities everywhere — no passwords, no
secrets in code, nothing that doesn't scale to zero.

## Where it goes next
- **v1.0 (imminent):** complete analysis loop — automatic weather
  enrichment, sector times and optimal-lap on every session, full
  historical backfill, all endpoints secured, living documentation.
- **v1.x:** one-tap ingestion, track management with a visual
  corner editor, custom domain.
- **v2.0:** the platform learns to replay and share driving — 
  RaceChrono-style lap replay animation, and a multi-user version
  where friends upload their own sessions and race each other's
  ghost laps.

---
*Changelog: seeded 2026-08-01 from the project's first month.
Update with each release.*
