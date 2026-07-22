"""Read-only SQL queries shared between the MCP server (mcp_server/server.py)
and the dashboard read API (function_app.py). Pulled out of the MCP server so
both callers query the DB the same way instead of maintaining two copies of
the same SQL.
"""

from .racechrono_parser import fmt_ms


def list_sessions(cnx, event_id=None):
    cur = cnx.cursor()
    sql = """
        SELECT s.session_id, s.event_id, e.event_name, t.track_name,
               s.session_number, s.session_date, s.run_group,
               s.weather, s.air_temp_f,
               lap_agg.best_lap_ms, lap_agg.avg_valid_lap_ms
        FROM dbo.sessions s
        JOIN dbo.events e ON e.event_id = s.event_id
        JOIN dbo.tracks t ON t.track_id = e.track_id
        OUTER APPLY (
            SELECT MIN(CASE WHEN l.is_valid = 1 THEN l.lap_time_ms END)
                       AS best_lap_ms,
                   AVG(CASE WHEN l.is_valid = 1
                            THEN CAST(l.lap_time_ms AS FLOAT) END)
                       AS avg_valid_lap_ms
            FROM dbo.laps l WHERE l.session_id = s.session_id
        ) lap_agg
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
            "best_lap_ms": r[9],
            "best_lap": fmt_ms(r[9]) if r[9] is not None else None,
            "avg_valid_lap_ms": (round(r[10]) if r[10] is not None
                                  else None),
            "avg_valid_lap": (fmt_ms(round(r[10]))
                               if r[10] is not None else None),
        }
        for r in cur.fetchall()
    ]


def get_session_detail(cnx, session_id):
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


def get_corner_metrics(cnx, session_id, lap_number=None):
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


def fastest_valid_lap(cur, session_id):
    cur.execute("""
        SELECT TOP 1 lap_id, lap_number, lap_time_ms
        FROM dbo.laps
        WHERE session_id = ? AND is_valid = 1
        ORDER BY lap_time_ms ASC""", session_id)
    row = cur.fetchone()
    if row is None:
        raise ValueError(f"No valid lap found for session_id={session_id}")
    return {"lap_id": row[0], "lap_number": row[1], "lap_time_ms": row[2]}


def corner_speeds_for_lap(cur, lap_id):
    cur.execute("""
        SELECT c.corner_code, cm.min_speed_mph
        FROM dbo.corner_metrics cm
        JOIN dbo.corners c ON c.corner_id = cm.corner_id
        WHERE cm.lap_id = ?
        ORDER BY c.sort_order""", lap_id)
    return {r[0]: float(r[1]) for r in cur.fetchall()}


def compare_laps(cnx, session_id_a, session_id_b):
    cur = cnx.cursor()

    lap_a = fastest_valid_lap(cur, session_id_a)
    lap_b = fastest_valid_lap(cur, session_id_b)
    speeds_a = corner_speeds_for_lap(cur, lap_a["lap_id"])
    speeds_b = corner_speeds_for_lap(cur, lap_b["lap_id"])

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


def _prior_session_id(cur, track_id, session_date, session_id):
    cur.execute("""
        SELECT TOP 1 s2.session_id
        FROM dbo.sessions s2
        JOIN dbo.events e2 ON e2.event_id = s2.event_id
        WHERE e2.track_id = ?
          AND (s2.session_date < ?
               OR (s2.session_date = ? AND s2.session_id < ?))
        ORDER BY s2.session_date DESC, s2.session_id DESC""",
        track_id, session_date, session_date, session_id)
    row = cur.fetchone()
    return row[0] if row else None


def session_summary(cnx, session_id):
    """Fastest valid lap, lap-time consistency, and corner-speed deltas
    against the most recent prior session at the same track."""
    cur = cnx.cursor()
    cur.execute("""
        SELECT s.session_id, s.event_id, e.event_name, t.track_id,
               t.track_name, s.session_number, s.session_date,
               s.run_group, s.weather, s.air_temp_f
        FROM dbo.sessions s
        JOIN dbo.events e ON e.event_id = s.event_id
        JOIN dbo.tracks t ON t.track_id = e.track_id
        WHERE s.session_id = ?""", session_id)
    row = cur.fetchone()
    if row is None:
        raise ValueError(f"No session with session_id={session_id}")
    track_id, session_date = row[3], row[6]

    cur.execute("""
        SELECT lap_time_ms FROM dbo.laps
        WHERE session_id = ? AND is_valid = 1""", session_id)
    valid_times = [r[0] for r in cur.fetchall()]
    if not valid_times:
        raise ValueError(f"No valid laps for session_id={session_id}")

    fastest_ms = min(valid_times)
    mean_ms = sum(valid_times) / len(valid_times)
    variance = (sum((t - mean_ms) ** 2 for t in valid_times)
                / len(valid_times))

    prior_session_id = _prior_session_id(cur, track_id, session_date,
                                          session_id)
    corner_deltas = []
    if prior_session_id is not None:
        lap_a = fastest_valid_lap(cur, session_id)
        lap_b = fastest_valid_lap(cur, prior_session_id)
        speeds_a = corner_speeds_for_lap(cur, lap_a["lap_id"])
        speeds_b = corner_speeds_for_lap(cur, lap_b["lap_id"])
        for code in sorted(set(speeds_a) | set(speeds_b),
                            key=lambda c: (len(c), c)):
            a, b = speeds_a.get(code), speeds_b.get(code)
            corner_deltas.append({
                "corner_code": code,
                "min_speed_mph": a,
                "prior_min_speed_mph": b,
                "delta_mph": (round(a - b, 1) if a is not None
                              and b is not None else None),
            })

    return {
        "session_id": row[0], "event_id": row[1], "event_name": row[2],
        "track_name": row[4], "session_number": row[5],
        "session_date": str(session_date), "run_group": row[7],
        "weather": row[8],
        "air_temp_f": float(row[9]) if row[9] is not None else None,
        "fastest_lap_ms": fastest_ms, "fastest_lap": fmt_ms(fastest_ms),
        "valid_lap_count": len(valid_times),
        "consistency_stdev_ms": round(variance ** 0.5, 1),
        "prior_session_id": prior_session_id,
        "corner_deltas": corner_deltas,
    }
