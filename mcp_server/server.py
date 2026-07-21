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

from ingest.cloud import get_cloud_connection
from ingest.racechrono_parser import fmt_ms

mcp = FastMCP("track-telemetry", host="0.0.0.0")


def _connect():
    return get_cloud_connection(os.environ["SQL_SERVER"],
                                 os.environ["SQL_DATABASE"])


@mcp.tool()
def list_sessions(event_id: Optional[int] = None) -> list[dict]:
    """List recorded track sessions, optionally filtered to one event."""
    cnx = _connect()
    cur = cnx.cursor()
    sql = """
        SELECT s.session_id, s.event_id, e.event_name, t.track_name,
               s.session_number, s.session_date, s.run_group,
               s.weather, s.air_temp_f
        FROM dbo.sessions s
        JOIN dbo.events e ON e.event_id = s.event_id
        JOIN dbo.tracks t ON t.track_id = e.track_id
    """
    if event_id is not None:
        sql += " WHERE s.event_id = ?"
        cur.execute(sql + " ORDER BY s.session_date, s.session_number",
                    event_id)
    else:
        cur.execute(sql + " ORDER BY s.session_date, s.session_number")

    return [
        {
            "session_id": r[0], "event_id": r[1], "event_name": r[2],
            "track_name": r[3], "session_number": r[4],
            "session_date": str(r[5]), "run_group": r[6],
            "weather": r[7],
            "air_temp_f": float(r[8]) if r[8] is not None else None,
        }
        for r in cur.fetchall()
    ]


@mcp.tool()
def get_session_detail(session_id: int) -> dict:
    """Session metadata, all laps, and corner coverage for one session."""
    cnx = _connect()
    cur = cnx.cursor()
    cur.execute("""
        SELECT s.session_id, s.event_id, e.event_name, t.track_name,
               s.session_number, s.session_date, s.run_group,
               s.weather, s.air_temp_f, s.source_file
        FROM dbo.sessions s
        JOIN dbo.events e ON e.event_id = s.event_id
        JOIN dbo.tracks t ON t.track_id = e.track_id
        WHERE s.session_id = ?""", session_id)
    row = cur.fetchone()
    if row is None:
        raise ValueError(f"No session with session_id={session_id}")

    session = {
        "session_id": row[0], "event_id": row[1], "event_name": row[2],
        "track_name": row[3], "session_number": row[4],
        "session_date": str(row[5]), "run_group": row[6],
        "weather": row[7],
        "air_temp_f": float(row[8]) if row[8] is not None else None,
        "source_file": row[9],
    }

    cur.execute("""
        SELECT lap_number, lap_time_ms, is_valid, is_out_lap, is_in_lap
        FROM dbo.laps WHERE session_id = ? ORDER BY lap_number""",
        session_id)
    laps = [
        {
            "lap_number": r[0], "lap_time_ms": r[1],
            "lap_time": fmt_ms(r[1]),
            "is_valid": bool(r[2]), "is_out_lap": bool(r[3]),
            "is_in_lap": bool(r[4]),
        }
        for r in cur.fetchall()
    ]

    cur.execute("""
        SELECT DISTINCT c.corner_code
        FROM dbo.corner_metrics cm
        JOIN dbo.laps l ON l.lap_id = cm.lap_id
        JOIN dbo.corners c ON c.corner_id = cm.corner_id
        WHERE l.session_id = ?""", session_id)
    corner_coverage = sorted({r[0] for r in cur.fetchall()},
                              key=lambda c: (len(c), c))

    session["laps"] = laps
    session["corner_coverage"] = corner_coverage
    return session


@mcp.tool()
def get_corner_metrics(session_id: int,
                        lap_number: Optional[int] = None) -> list[dict]:
    """Per-lap, per-corner min/entry/exit speeds for a session."""
    cnx = _connect()
    cur = cnx.cursor()
    sql = """
        SELECT l.lap_number, c.corner_code, c.corner_name,
               cm.min_speed_mph, cm.entry_speed_mph, cm.exit_speed_mph
        FROM dbo.corner_metrics cm
        JOIN dbo.laps l ON l.lap_id = cm.lap_id
        JOIN dbo.corners c ON c.corner_id = cm.corner_id
        WHERE l.session_id = ?
    """
    params = [session_id]
    if lap_number is not None:
        sql += " AND l.lap_number = ?"
        params.append(lap_number)
    cur.execute(sql + " ORDER BY l.lap_number, c.sort_order", *params)

    return [
        {
            "lap_number": r[0], "corner_code": r[1], "corner_name": r[2],
            "min_speed_mph": float(r[3]),
            "entry_speed_mph": float(r[4]) if r[4] is not None else None,
            "exit_speed_mph": float(r[5]) if r[5] is not None else None,
        }
        for r in cur.fetchall()
    ]


def _fastest_valid_lap(cur, session_id):
    cur.execute("""
        SELECT TOP 1 lap_id, lap_number, lap_time_ms
        FROM dbo.laps
        WHERE session_id = ? AND is_valid = 1
        ORDER BY lap_time_ms ASC""", session_id)
    row = cur.fetchone()
    if row is None:
        raise ValueError(f"No valid lap found for session_id={session_id}")
    return {"lap_id": row[0], "lap_number": row[1], "lap_time_ms": row[2]}


def _corner_speeds_for_lap(cur, lap_id):
    cur.execute("""
        SELECT c.corner_code, cm.min_speed_mph
        FROM dbo.corner_metrics cm
        JOIN dbo.corners c ON c.corner_id = cm.corner_id
        WHERE cm.lap_id = ?
        ORDER BY c.sort_order""", lap_id)
    return {r[0]: float(r[1]) for r in cur.fetchall()}


@mcp.tool()
def compare_laps(session_id_a: int, session_id_b: int) -> dict:
    """Compare the fastest valid lap of two sessions, corner by corner."""
    cnx = _connect()
    cur = cnx.cursor()

    lap_a = _fastest_valid_lap(cur, session_id_a)
    lap_b = _fastest_valid_lap(cur, session_id_b)
    speeds_a = _corner_speeds_for_lap(cur, lap_a["lap_id"])
    speeds_b = _corner_speeds_for_lap(cur, lap_b["lap_id"])

    corners = []
    for code in sorted(set(speeds_a) | set(speeds_b),
                        key=lambda c: (len(c), c)):
        a, b = speeds_a.get(code), speeds_b.get(code)
        corners.append({
            "corner_code": code,
            "session_a_min_mph": a,
            "session_b_min_mph": b,
            "delta_mph": (round(a - b, 1) if a is not None
                          and b is not None else None),
        })

    return {
        "session_a": {
            "session_id": session_id_a,
            "lap_number": lap_a["lap_number"],
            "lap_time": fmt_ms(lap_a["lap_time_ms"]),
        },
        "session_b": {
            "session_id": session_id_b,
            "lap_number": lap_b["lap_number"],
            "lap_time": fmt_ms(lap_b["lap_time_ms"]),
        },
        "corners": corners,
    }


if __name__ == "__main__":
    mcp.settings.port = int(os.environ.get("PORT", "8000"))
    mcp.run(transport="streamable-http")
