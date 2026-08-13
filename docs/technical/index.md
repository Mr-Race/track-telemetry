# Technical documentation

Documentation-as-code: these pages live in the repo and are updated in
the same commits as the changes they describe. If a decision only exists
in a chat log, it does not exist.

| Page | What it answers |
|---|---|
| [Architecture](architecture.md) | What the pieces are, how a session flows through them, and where the sharp edges are |
| [Schema and data dictionary](schema.md) | Every table and column, generated from the live database, plus what the types don't tell you |
| [API reference](api.md) | Every endpoint, both auth mechanisms, and what to check in an upload response at the track |
| [Runbook](runbook.md) | Deploys, migrations, verifying a release, and rehearsing an upload safely against production |
| [Decision log](decisions.md) | Architecture decisions, what each cost, and what would reverse it |

## Also in this repo

- [`docs/WAY-OF-WORKING.md`](../WAY-OF-WORKING.md) — the practices this
  project holds itself to. Every rule exists because something broke
  without it.
- [`docs/BACKLOG.md`](../BACKLOG.md) — the system of record: scope,
  known gaps, and a dated Done log.
- [`docs/mcp_server.md`](../mcp_server.md) — MCP server setup, the
  custom domain, and the trailing-slash trap.
- [`docs/ios_shortcut.md`](../ios_shortcut.md) — the phone upload path.
- [`sql/README.md`](https://github.com/Mr-Race/track-telemetry/blob/main/sql/README.md) — how migrations are applied
  and recorded.
- [`docs/RELEASING.md`](../RELEASING.md) — how to cut a release.
- [`SECURITY.md`](https://github.com/Mr-Race/track-telemetry/blob/main/SECURITY.md) — this repo is public; security
  findings do **not** go in issues.

## Reviews

- [Engineering review](../specs/engineering-review.md)
- [Security review](../specs/security-review.md)

Both gates passed before v0.9.0. All high-severity findings are closed.
