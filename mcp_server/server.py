"""Read-only MCP server over the track-telemetry Azure SQL DB.

Exposes session/lap/corner data as Streamable HTTP MCP tools so Claude
can query real track-day results conversationally. Managed identity
(Container Apps) / az login (local) resolves via the same
get_cloud_connection() used by function_app.py - db_datareader only,
no write path here. See docs/mcp_server.md for deployment notes.
"""

import os
from typing import Optional

from mcp.server.fastmcp import FastMCP

from ingest import queries
from ingest.cloud import get_cloud_connection

mcp = FastMCP("track-telemetry", host="0.0.0.0")


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


if __name__ == "__main__":
    mcp.settings.port = int(os.environ.get("PORT", "8000"))
    mcp.run(transport="streamable-http")
