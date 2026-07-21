# MCP server: query track telemetry from Claude

Read-only Streamable HTTP MCP server exposing session/lap/corner data
from the Azure SQL DB, deployed on Azure Container Apps
(`ca-track-telemetry-mcp`, managed identity, `db_datareader` only — see
`sql/06_mcp_identity.sql`). No auth for now (the backlog tracks OAuth
2.1 + PKCE via Entra ID as a separate follow-up); the endpoint is public
but unlisted, and the identity behind it cannot write.

## Tools

- `list_sessions(event_id?)` — sessions with track/event names, date,
  weather.
- `get_session_detail(session_id)` — session metadata, all laps,
  corner coverage.
- `get_corner_metrics(session_id, lap_number?)` — per-lap, per-corner
  min/entry/exit speeds.
- `compare_laps(session_id_a, session_id_b)` — fastest valid lap of each
  session, corner-by-corner speed delta.

## Deployment

```
az containerapp env create -g Track-telemetry -n cae-track-telemetry \
  --location eastus

az containerapp up --source . \
  --name ca-track-telemetry-mcp -g Track-telemetry \
  --environment cae-track-telemetry \
  --ingress external --target-port 8000

az containerapp identity assign --system-assigned \
  -n ca-track-telemetry-mcp -g Track-telemetry

az containerapp update -n ca-track-telemetry-mcp -g Track-telemetry \
  --set-env-vars SQL_SERVER=track-telemetry.database.windows.net \
                 SQL_DATABASE=free-sql-db-7848405
```

Then, as the Entra admin (device-code sign-in against tenant
`d5080430-a89e-4e80-930a-c9a8eb304c99`, same pattern as ad hoc SQL
queries — see prior Azure SQL auth notes), run `sql/06_mcp_identity.sql`
against the telemetry DB with `<CONTAINER_APP_NAME>` replaced by
`ca-track-telemetry-mcp`.

## Test the deployed endpoint

```python
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main():
    url = "https://<fqdn>/mcp"
    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print(await session.call_tool("list_sessions", {}))

asyncio.run(main())
```

## Register as a Claude custom connector

In the Claude app: **Settings -> Connectors -> Add custom connector**,
paste `https://<fqdn>/mcp`, no authentication. Test from the phone by
asking Claude about a recent session (e.g. "how did session 5 go?").
