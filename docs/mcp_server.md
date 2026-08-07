# MCP server: query track telemetry from Claude

Read-only Streamable HTTP MCP server exposing session/lap/corner data
from the Azure SQL DB, deployed on Azure Container Apps
(`ca-track-telemetry-mcp`, managed identity, `db_datareader` only — see
`sql/06_mcp_identity.sql`). The `/mcp` endpoint is an OAuth 2.1 Resource
Server: it validates bearer tokens issued by the Entra External ID
(CIAM) tenant and requires the `mcp.access` scope (see
[Authentication](#authentication) below). The managed identity behind it
is read-only regardless.

## Tools

- `list_sessions(event_id?)` — sessions with track/event names, date,
  weather.
- `get_session_detail(session_id)` — session metadata, all laps,
  corner coverage.
- `get_corner_metrics(session_id, lap_number?)` — per-lap, per-corner
  min/entry/exit speeds.
- `compare_laps(session_id_a, session_id_b)` — fastest valid lap of each
  session, corner-by-corner speed delta.

## Authentication

The server is an OAuth 2.1 Resource Server (RFC 9728). `mcp_server/auth.py`
validates each bearer token's signature/audience/issuer against the CIAM
tenant's JWKS (PyJWT `PyJWKClient`) and requires the `mcp.access` scope —
the same validation approach as the dashboard's read API
(`ingest/api_auth.py`), adapted to the MCP SDK's async `TokenVerifier`.
Setting `token_verifier` + `auth.resource_server_url` on `FastMCP` makes
it wrap `/mcp` in `RequireAuthMiddleware` and publish
`/.well-known/oauth-protected-resource` advertising the CIAM issuer, so a
client discovers where to authenticate; no hand-rolled routes.

The resource lives in its **own** Entra CIAM app registration
(`track-telemetry-mcp`), separate from the dashboard SPA — a distinct
audience with a client secret, which is the correct per-resource pattern.
That app registration needs:

- `identifierUris`: `api://<mcp-client-id>`
- an `mcp.access` delegated (`User`) scope under `api.oauth2PermissionScopes`
- redirect URI `https://claude.ai/api/mcp/auth_callback` (Claude's fixed
  MCP OAuth callback)
- a client secret (`addPassword`) — Claude.ai's connector Advanced
  Settings needs both the client id and secret, because Entra CIAM does
  **not** support OAuth Dynamic Client Registration.

Entra CIAM has no `/register` (DCR) endpoint, so the app registration is
created via Microsoft Graph REST (`az ad app create` hits the tenant's
Security-Defaults CLI block — see `docs/BACKLOG.md`).

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
                 SQL_DATABASE=free-sql-db-7848405 \
                 MCP_TENANT_ID=cc8e128a-ad5b-49af-a3ce-35e7c3c3e30c \
                 MCP_CLIENT_ID=<mcp-app-client-id> \
                 MCP_RESOURCE_URL=https://ca-track-telemetry-mcp.ambitiousgrass-8ff8b80e.eastus.azurecontainerapps.io
```

`MCP_RESOURCE_URL` is the server's own public FQDN — it becomes the
`resource` in the protected-resource metadata and the audience clients
request tokens for. `MCP_TENANT_ID`/`MCP_CLIENT_ID` are the CIAM tenant
and the `track-telemetry-mcp` app registration's client id (kept
separate from the dashboard's `MSAL_TENANT_ID`/`MSAL_CLIENT_ID`).

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
paste `https://<fqdn>/mcp`, then open **Advanced settings** and enter the
`track-telemetry-mcp` app registration's **OAuth Client ID** and **Client
Secret** (required because the CIAM tenant does not support DCR). Claude
runs the OAuth 2.1 + PKCE consent flow on connect. Test from the phone by
asking Claude about a recent session (e.g. "how did session 5 go?").
