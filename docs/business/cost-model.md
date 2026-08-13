# The cost model

*Audience: non-technical readers. The short version — this platform
runs at effectively $0/month, and that is an architectural property,
not a lucky billing month.*

## The number

**Roughly $0.50 in total lifetime spend** to date, against a platform
that ingests real telemetry, serves a secured web dashboard, and
answers questions conversationally through an AI assistant.

> Sourced from the structured cost audit recorded in
> [the business overview](overview.md). A live re-query of the Azure
> Cost Management API on 2026-08-13 was rate-limited and could not
> confirm the figure independently; it is carried forward from that
> audit rather than re-measured.

## Why it is nearly free, by design

Every component either scales to zero or sits inside a permanent free
allowance. Nothing is provisioned "just in case."

| Component | Tier | Why it costs nothing |
|---|---|---|
| Database | Azure SQL serverless, free tier | **Auto-pauses after 60 idle minutes.** A personal track platform is idle almost always — a handful of active hours a month |
| Ingest + API | Azure Functions, Consumption (Y1) | Billed per execution. A track day is ~6 uploads |
| Dashboard | Static Web Apps, Free | Static assets on a CDN |
| Raw archive | Blob Storage | 22 CSVs. Storage cost is measured in fractions of a cent |
| MCP server | Container Apps | Scales to zero between conversations |
| Identity | Entra External ID | Free below a monthly-active-user threshold this will never approach |
| CI | GitHub Actions | Free for a public repository |
| Monitoring | Application Insights | Inside the free data allowance, with sampling on |

## The trade the design actually makes

Scaling to zero is not free of consequence — it is paid for in **latency
on the first request**.

The database takes 30–60 seconds to resume from auto-pause. Measured on
2026-08-13: a full 87,000-sample upload against a genuinely paused
database completed in **59 seconds** end to end.

That trade is correct here and would be wrong in most businesses. One
operator uploading six files a day can absorb a one-minute wait once per
day. A customer-facing checkout cannot. The interesting engineering is
not "we used the free tier" — it is knowing which workloads can pay in
latency and building so the wait lands where it is tolerable.

Concretely, the design absorbs it rather than ignoring it:

- One pooled database connection per process, so concurrent requests
  queue behind a *single* resume instead of each paying separately. This
  turned a 48-second page load into one slow request followed by fast
  ones.
- A 90-second connection timeout with a retry, because the previous
  60-second limit was the same number as the top of the documented
  resume window — a coin flip on the day's first upload.
- The upload path is told to expect it, so a slow first request is not
  mistaken for a broken one.

## What would change the number

Honestly stated, since a cost model that only ever says "$0" is not a
model:

- **Multi-user (v2.0).** More users means more active database hours and
  a real identity tier. The free tier is a single-operator property.
- **The Claude-generated session assessment** (planned, v1.x) is the
  first component with a genuine per-use cost. It is designed to
  generate once at ingest and store the result, rather than on every
  page view — which is the difference between pennies and a
  subscription.
- **Sample-level telemetry storage (v2.0 replay).** 87,000 samples per
  session is currently reduced to per-lap and per-corner rows. Keeping
  every sample for replay changes the storage story materially.

## The point

The $0 is a demonstration, not a boast: the same architectural patterns
that make an enterprise platform elastic — serverless, scale-to-zero,
managed identity, no idle capacity — are what make a personal one free.
The discipline is identical; only the bill differs.
