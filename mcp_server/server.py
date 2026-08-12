"""Read-only MCP server over the track-telemetry Azure SQL DB.

Exposes session/lap/corner data as Streamable HTTP MCP tools so Claude
can query real track-day results conversationally. Managed identity
(Container Apps) / az login (local) resolves via the same
get_cloud_connection() used by function_app.py - db_datareader only,
no write path here. See docs/mcp_server.md for deployment notes.
"""

import os
from typing import Optional

from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from starlette.responses import JSONResponse
from starlette.routing import Route

from ingest import queries
from ingest.cloud import get_cloud_connection
from mcp_server.auth import (APP_ID_URI, ISSUER, QUALIFIED_SCOPE,
                              EntraTokenVerifier)

# OAuth 2.1 Resource Server: token_verifier + auth.resource_server_url
# make FastMCP wrap /mcp in RequireAuthMiddleware and publish
# /.well-known/oauth-protected-resource (RFC 9728) advertising ISSUER as
# the authorization server, so an MCP client can discover where to
# authenticate. MCP_RESOURCE_URL is this server's own public FQDN.
mcp = FastMCP(
    "track-telemetry",
    host="0.0.0.0",
    token_verifier=EntraTokenVerifier(),
    auth=AuthSettings(
        issuer_url=ISSUER,
        resource_server_url=os.environ["MCP_RESOURCE_URL"],
        # Advertise the fully-qualified scope so clients request the form
        # Entra accepts (api://<id>/mcp.access), not the bare short name.
        required_scopes=[QUALIFIED_SCOPE],
    ),
)


def _connect():
    return get_cloud_connection(os.environ["SQL_SERVER"],
                                 os.environ["SQL_DATABASE"])


@mcp.tool()
def list_sessions(event_id: Optional[int] = None) -> list[dict]:
    """List recorded track sessions, optionally filtered to one event."""
    return queries.list_sessions(_connect(), event_id)


@mcp.tool()
def get_session_detail(session_id: int) -> dict:
    """Session metadata, all laps, and corner coverage for one session."""
    return queries.get_session_detail(_connect(), session_id)


@mcp.tool()
def get_corner_metrics(session_id: int,
                        lap_number: Optional[int] = None) -> list[dict]:
    """Per-lap, per-corner min/entry/exit speeds for a session."""
    return queries.get_corner_metrics(_connect(), session_id, lap_number)


@mcp.tool()
def compare_laps(session_id_a: int, session_id_b: int) -> dict:
    """Compare the fastest valid lap of two sessions, corner by corner."""
    return queries.compare_laps(_connect(), session_id_a, session_id_b)


# RFC 9728 §3.1 puts the metadata here when the resource has no path.
RESOURCE_METADATA_PATH = "/.well-known/oauth-protected-resource"


async def protected_resource_metadata(request):
    """Advertise `resource` exactly as Entra stores the App ID URI.

    The SDK builds this document from AuthSettings.resource_server_url,
    which is a pydantic AnyHttpUrl - and pydantic normalises a bare host
    by appending a trailing slash. Entra compares the client's RFC 8707
    `resource` parameter *literally* against the Application ID URI,
    rejects the whole authorize request when they differ, and refuses to
    store an App ID URI that ends in a slash. So the two can only ever
    agree if the unslashed form is emitted here.

    Measured against Entra's own authorize endpoint, same request
    otherwise:
        resource=https://mcp.mr-race.com/   -> AADSTS9010010
        resource=https://mcp.mr-race.com    -> accepted

    That one character is why the connector could not authorize. The
    rejection happens before authentication, so it produced no sign-in
    log at all, which is what made it so hard to find.
    """
    return JSONResponse(
        {
            "resource": APP_ID_URI,
            "authorization_servers": [ISSUER],
            "scopes_supported": [QUALIFIED_SCOPE],
            "bearer_methods_supported": ["header"],
        },
        headers={
            # Public, non-sensitive discovery document; the SDK's own
            # route wraps its handler in CORS for browser-based clients
            # and replacing it would otherwise drop that.
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )


def build_app():
    """The SDK's app with the metadata route swapped for ours.

    Custom routes are appended *after* the SDK's, and Starlette matches
    first-wins, so `@mcp.custom_route` cannot shadow it - the route has
    to be removed and re-added.
    """
    app = mcp.streamable_http_app()
    app.router.routes = [
        route for route in app.router.routes
        if getattr(route, "path", None) != RESOURCE_METADATA_PATH
    ] + [
        Route(RESOURCE_METADATA_PATH, protected_resource_metadata,
              methods=["GET", "OPTIONS"])
    ]
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(build_app(), host="0.0.0.0",
                port=int(os.environ.get("PORT", "8000")))
