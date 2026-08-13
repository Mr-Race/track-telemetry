# API reference

Base URL: `https://func-track-telemetry-ingest.azurewebsites.net/api`

## Authentication

Two different mechanisms, for two different callers.

**`POST /ingest` uses an Azure Functions key** (`?code=…`). It is called
by an iOS Shortcut, which has no way to hold an interactive sign-in.

**Every other route requires an MSAL-issued bearer token**
(`Authorization: Bearer …`), validated by `@require_auth` in
`ingest/api_auth.py`.

> The routes are declared `auth_level=ANONYMOUS`. That is Azure's
> function-key mechanism being switched off, not the endpoint being
> unauthenticated — `@require_auth` is what protects them. Reading the
> decorator alone will mislead you.

Errors return `{"error": "...", "error_id": "..."}`. The `error_id`
correlates to an Application Insights entry; internal exception text is
never returned to the client.

## Ingest

### `POST /ingest`

Upload a RaceChrono v3 CSV. Body is the raw CSV; `Content-Type: text/csv`.

| Param | Required | Meaning |
|---|---|---|
| `code` | yes | Function key |
| `filename` | no | Defaults to `session_<epoch>.csv`. Supply it — the archived blob is named from it |
| `event_id` | no | Override. Normally resolved from the CSV's track name + date |
| `session_number` | no | Override. Normally the next for that event |
| `car_id` | no | Override. Defaults to the configured car |
| `dry_run` | no | `1` parses and resolves but writes nothing — no rows, no blob |

**Auto-resolution.** `event_id` is matched from the CSV's `Track name`
and `Created` date against an existing event. It fails with 400 if
there is no match, or if more than one event covers that date.
**Create the event on the dashboard before the day starts.**

**Idempotency.** Keyed on the SHA-256 of the uploaded bytes, not the
filename. Re-uploading the same file refreshes the session it already
created rather than inserting a second one, and does not write a second
blob.

**Response** (abridged):

```json
{
  "event_id": 7,
  "session_number": 1,
  "session_id": 28,
  "samples": 87043,
  "blob_name": "7/1_1786631462_ab646574_session.csv",
  "duplicate": false,
  "loaded": true,
  "corner_coverage": ["1","2","3","4","5","6","7","8","9","10","11A","11B","12"],
  "laps_with_segments": 7,
  "laps": [{"lap_number": 1, "lap_time": "2:11.482", "is_valid": true, "...": "..."}],
  "parse": {
    "pedal_channel": "accelerator_pos",
    "gps_source": "100: gps",
    "has_rpm": true,
    "rows_used": 87043,
    "rows_skipped": {"malformed": 0, "no_lap": 39352, "missing_gps": 0}
  }
}
```

**What to check in the `parse` block at the track:**

- `pedal_channel` should be `accelerator_pos`. If it is `null`, the OBD
  dongle didn't connect — the session still ingests as GPS-only, but
  there will be no pedal data. **OBD lookups fail soft, so this is the
  one to eyeball.**
- `rows_skipped.no_lap` is normally large. Those are pre-first-crossing
  and pit samples, not errors.
- `rows_skipped.malformed` should be 0 or near it.

## Read endpoints

All require a bearer token.

| Route | Method | Notes |
|---|---|---|
| `/sessions` | GET | `?event_id=` optional filter |
| `/sessions/{id}` | GET | Detail incl. laps and driver |
| `/sessions/{id}` | PATCH | Editable session fields |
| `/sessions/{id}/summary` | GET | Corner metrics and segment analysis |
| `/events` | GET | Split into in progress / upcoming / past, computed against the track's local date |
| `/events` | POST | Create an event |
| `/events/{id}/summary` | GET | Hero stats, per-session pace, corner story, weather |
| `/tracks` | GET | Track directory |
| `/tracks/{id}/satellite` | GET | Azure Maps satellite view |
| `/tracks/{id}/benchmarks` | GET | Reference lap times |
| `/cars` | GET, POST | Car catalog |
| `/consumables` | GET | Service-life tracking |
| `/consumables/{id}/replace` | POST | Reset a consumable's counter |
| `/organizations` | GET | Event organizers |

## MCP tools

Served at `https://mcp.mr-race.com/mcp`, OAuth 2.1 + PKCE via Entra,
read-only (`db_datareader`). Added to Claude as a custom connector; see
[MCP server setup](../mcp_server.md).

| Tool | Arguments |
|---|---|
| `list_sessions` | `event_id` (optional) |
| `get_session_detail` | `session_id` |
| `get_corner_metrics` | `session_id`, corner filter optional |
| `compare_laps` | `session_id_a`, `session_id_b` |

The server publishes RFC 9728 protected-resource metadata at
`/.well-known/oauth-protected-resource`. The App ID URI must not end in
a slash — see the decision log for why that one character cost a day.
