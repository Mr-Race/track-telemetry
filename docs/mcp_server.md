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

- `identifierUris`: **`https://mcp.mr-race.com`** — see "The trailing
  slash" below; this must equal the `resource` the server advertises,
  exactly, and Entra will not store it with a trailing slash
- an `mcp.access` delegated (`User`) scope under
  `api.oauth2PermissionScopes`, giving the qualified scope
  `https://mcp.mr-race.com/mcp.access`
- redirect URI `https://claude.ai/api/mcp/auth_callback` (Claude's fixed
  MCP OAuth callback)
- a client secret (`addPassword`) — Claude.ai's connector needs both the
  client id and secret, because Entra CIAM does **not** support OAuth
  Dynamic Client Registration.

Entra CIAM has no `/register` (DCR) endpoint, so the app registration is
created via Microsoft Graph REST (`az ad app create` hits the tenant's
Security-Defaults CLI block — see `docs/BACKLOG.md`).

### Why a custom domain is required

Entra ties a scope to the resource that owns it, and an MCP client sends
the **server's own URL** as the RFC 8707 `resource` parameter. Entra
rejects the authorize request when the two disagree. They can only agree
if the Application ID URI *is* the server URL — and Entra only accepts an
`https` App ID URI on a **verified domain**.

`*.azurecontainerapps.io` is Microsoft's and can never be verified by
this tenant, so no configuration of the default hostname could ever have
worked. `mr-race.com` is verified in the CIAM tenant (apex `TXT` record),
and the Container App is bound to `mcp.mr-race.com` with a managed
certificate.

### The trailing slash

Entra compares `resource` against the App ID URI **literally**:

```
resource=https://mcp.mr-race.com/   ->  AADSTS9010010
resource=https://mcp.mr-race.com    ->  accepted
```

The MCP SDK builds its RFC 9728 document from a pydantic `AnyHttpUrl`,
which normalises a bare host by appending `/`. Entra refuses to store an
App ID URI ending in `/`. So the SDK's default output can never match.

`server.py` therefore owns the `/.well-known/oauth-protected-resource`
route and emits `resource` unslashed. The route has to be **removed and
re-added** rather than shadowed: `FastMCP` appends custom routes after
its own and Starlette matches first-wins, so `@mcp.custom_route` does not
override it. That is why the app is built via `build_app()` and served
with uvicorn instead of `mcp.run()`.

### Debugging note

This rejection happens **before authentication**, so Entra writes no
sign-in log at all — filtering sign-ins by the application returns
nothing, which looks exactly like a credential problem. To see the real
error, call the authorize endpoint directly and read the redirect:

```bash
curl -s -o /dev/null -w '%{redirect_url}\n' \
  "https://<tenant>.ciamlogin.com/<tenant>/oauth2/v2.0/authorize?client_id=<id>&response_type=code&redirect_uri=https%3A%2F%2Fclaude.ai%2Fapi%2Fmcp%2Fauth_callback&response_mode=query&scope=https%3A%2F%2Fmcp.mr-race.com%2Fmcp.access&resource=https%3A%2F%2Fmcp.mr-race.com&state=t"
```

An `AADSTS…` code in the returned URL is the actual failure. Changing one
parameter at a time against this endpoint is far faster than round-trips
through the connector UI.

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
                 MCP_RESOURCE_URL=https://mcp.mr-race.com \
                 MCP_APP_ID_URI=https://mcp.mr-race.com
```

### Custom domain

```
# DNS at the registrar (GoDaddy), on mr-race.com:
#   TXT   @           MS=ms...          <- from Entra "Add custom domain"
#   CNAME mcp         ca-track-telemetry-mcp.<env>.eastus.azurecontainerapps.io
#   TXT   asuid.mcp   <customDomainVerificationId>

az containerapp env show -n cae-track-telemetry -g Track-telemetry \
  --query "properties.customDomainConfiguration.customDomainVerificationId" -o tsv

az containerapp hostname add -n ca-track-telemetry-mcp -g Track-telemetry \
  --hostname mcp.mr-race.com

az containerapp hostname bind -n ca-track-telemetry-mcp -g Track-telemetry \
  --hostname mcp.mr-race.com --environment cae-track-telemetry \
  --validation-method CNAME
```

`bind` provisions a free managed certificate; it can take up to 20
minutes, though in practice it took about two.

`MCP_RESOURCE_URL` is the server's public FQDN — it becomes the
`resource` in the protected-resource metadata and the audience clients
request tokens for. `MCP_APP_ID_URI` is the app registration's
Application ID URI; it drives the advertised scope and the audiences the
verifier accepts, and defaults to `api://<client-id>` so the two can be
changed independently rather than needing a flag-day cutover.
`MCP_TENANT_ID`/`MCP_CLIENT_ID` are the CIAM tenant and the
`track-telemetry-mcp` app registration's client id (kept separate from
the dashboard's `MSAL_TENANT_ID`/`MSAL_CLIENT_ID`).

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
paste:

```
https://mcp.mr-race.com/mcp
```

Then enter the `track-telemetry-mcp` app registration's **OAuth Client
ID** and **Client Secret**. Both fields are labelled optional, but they
are **required here**: they are only optional for servers that support
Dynamic Client Registration, and this one deliberately doesn't — Entra is
the authorization server, and it issues tokens only to a pre-registered
app. Leaving them blank produces *"Automatic client registration isn't
supported by Track Telemetry."*

Claude then runs the OAuth 2.1 + PKCE consent flow. Confirmed working
end to end 2026-08-12. Test by asking about a recent session — e.g.
"list my track sessions" or "how did the TNIA day go?".

If reconnecting after a configuration change, **remove the connector
first**: a cached failed authorization replays the old error and makes a
fixed server look broken.
