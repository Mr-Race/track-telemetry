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
               s.session_number, s.session_date, rg.group_code,
               s.weather, s.air_temp_f,
               lap_agg.best_lap_ms, lap_agg.avg_valid_lap_ms, c.display_name
        FROM dbo.sessions s
        JOIN dbo.events e ON e.event_id = s.event_id
        JOIN dbo.tracks t ON t.track_id = e.track_id
        LEFT JOIN dbo.run_groups rg ON rg.run_group_id = s.run_group_id
        LEFT JOIN dbo.cars c ON c.car_id = s.car_id
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
            "car": r[11],
        }
        for r in cur.fetchall()
    ]


def get_session_detail(cnx, session_id):
    cur = cnx.cursor()
    cur.execute("""
        SELECT s.session_id, s.event_id, e.event_name, t.track_id,
               t.track_name, s.session_number, s.session_date,
               rg.group_code, s.weather, s.air_temp_f, s.source_file,
               c.display_name, s.car_id
        FROM dbo.sessions s
        JOIN dbo.events e ON e.event_id = s.event_id
        JOIN dbo.tracks t ON t.track_id = e.track_id
        LEFT JOIN dbo.run_groups rg ON rg.run_group_id = s.run_group_id
        LEFT JOIN dbo.cars c ON c.car_id = s.car_id
        WHERE s.session_id = ?""", session_id)
    row = cur.fetchone()
    if row is None:
        raise ValueError(f"No session with session_id={session_id}")

    session = {
        "session_id": row[0], "event_id": row[1], "event_name": row[2],
        "track_id": row[3], "track_name": row[4], "session_number": row[5],
        "session_date": str(row[6]), "run_group": row[7],
        "weather": row[8],
        "air_temp_f": float(row[9]) if row[9] is not None else None,
        "source_file": row[10],
        "car": row[11],
        "car_id": row[12],
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
               rg.group_code, s.weather, s.air_temp_f, c.display_name
        FROM dbo.sessions s
        JOIN dbo.events e ON e.event_id = s.event_id
        JOIN dbo.tracks t ON t.track_id = e.track_id
        LEFT JOIN dbo.run_groups rg ON rg.run_group_id = s.run_group_id
        LEFT JOIN dbo.cars c ON c.car_id = s.car_id
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
        "track_id": track_id, "track_name": row[4],
        "session_number": row[5],
        "session_date": str(session_date), "run_group": row[7],
        "weather": row[8],
        "air_temp_f": float(row[9]) if row[9] is not None else None,
        "car": row[10],
        "fastest_lap_ms": fastest_ms, "fastest_lap": fmt_ms(fastest_ms),
        "valid_lap_count": len(valid_times),
        "consistency_stdev_ms": round(variance ** 0.5, 1),
        "prior_session_id": prior_session_id,
        "corner_deltas": corner_deltas,
    }


def list_tracks(cnx):
    """Every track/configuration with corner count and my personal best,
    for the read-only track directory page."""
    cur = cnx.cursor()
    cur.execute("""
        SELECT t.track_id, t.track_name, t.configuration, t.length_miles,
               (SELECT COUNT(*) FROM dbo.corners c
                WHERE c.track_id = t.track_id) AS corner_count,
               pb.lap_time_ms, pb.session_id, pb.session_date
        FROM dbo.tracks t
        OUTER APPLY (
            SELECT TOP 1 l.lap_time_ms, l.session_id, s.session_date
            FROM dbo.laps l
            JOIN dbo.sessions s ON s.session_id = l.session_id
            JOIN dbo.events e ON e.event_id = s.event_id
            WHERE e.track_id = t.track_id AND l.is_valid = 1
            ORDER BY l.lap_time_ms ASC
        ) pb
        ORDER BY t.track_name, t.configuration""")

    tracks = []
    for r in cur.fetchall():
        personal_best = None
        if r[5] is not None:
            personal_best = {
                "lap_time_ms": r[5], "lap_time": fmt_ms(r[5]),
                "session_id": r[6], "session_date": str(r[7]),
            }
        tracks.append({
            "track_id": r[0], "track_name": r[1], "configuration": r[2],
            "length_miles": float(r[3]) if r[3] is not None else None,
            "corner_count": r[4],
            "personal_best": personal_best,
        })
    return tracks


def list_organizations(cnx):
    cur = cnx.cursor()
    cur.execute("""
        SELECT organization_id, org_code, org_name
        FROM dbo.organizations ORDER BY org_name""")
    return [
        {"organization_id": r[0], "org_code": r[1], "org_name": r[2]}
        for r in cur.fetchall()
    ]


def list_events(cnx):
    """Every event with its org/track and how many sessions are logged
    under it, for the dashboard's event management page."""
    cur = cnx.cursor()
    cur.execute("""
        SELECT e.event_id, e.event_name, e.track_id, t.track_name,
               e.organization_id, o.org_code, e.start_date, e.end_date,
               (SELECT COUNT(*) FROM dbo.sessions s
                WHERE s.event_id = e.event_id) AS session_count
        FROM dbo.events e
        JOIN dbo.tracks t ON t.track_id = e.track_id
        JOIN dbo.organizations o ON o.organization_id = e.organization_id
        ORDER BY e.start_date DESC, e.event_id DESC""")
    return [
        {
            "event_id": r[0], "event_name": r[1],
            "track_id": r[2], "track_name": r[3],
            "organization_id": r[4], "org_code": r[5],
            "start_date": str(r[6]),
            "end_date": str(r[7]) if r[7] is not None else None,
            "session_count": r[8],
        }
        for r in cur.fetchall()
    ]


def create_event(cnx, track_id, organization_id, event_name, start_date,
                  end_date):
    cur = cnx.cursor()
    cur.execute("""
        INSERT INTO dbo.events
            (track_id, organization_id, event_name, start_date, end_date)
        OUTPUT INSERTED.event_id
        VALUES (?,?,?,?,?)""",
        track_id, organization_id, event_name, start_date, end_date)
    event_id = cur.fetchone()[0]
    cnx.commit()
    return event_id


def list_cars(cnx):
    cur = cnx.cursor()
    cur.execute("""
        SELECT car_id, display_name, make, model, year, notes
        FROM dbo.cars ORDER BY display_name""")
    return [
        {
            "car_id": r[0], "display_name": r[1], "make": r[2],
            "model": r[3], "year": r[4], "notes": r[5],
        }
        for r in cur.fetchall()
    ]


def create_car(cnx, display_name, make, model, year, notes):
    cur = cnx.cursor()
    cur.execute("""
        INSERT INTO dbo.cars (display_name, make, model, year, notes)
        OUTPUT INSERTED.car_id
        VALUES (?,?,?,?,?)""",
        display_name, make, model, year, notes)
    car_id = cur.fetchone()[0]
    cnx.commit()
    return car_id


def set_session_car(cnx, session_id, car_id):
    cur = cnx.cursor()
    cur.execute("""
        UPDATE dbo.sessions SET car_id = ?
        WHERE session_id = ?""", car_id, session_id)
    if cur.rowcount == 0:
        raise ValueError(f"No session with session_id={session_id}")
    cnx.commit()


def get_track_benchmarks(cnx, track_id):
    """My all-time personal best at this track, plus any manually
    entered friends' benchmark laps."""
    cur = cnx.cursor()
    cur.execute("SELECT track_name FROM dbo.tracks WHERE track_id = ?",
                track_id)
    row = cur.fetchone()
    if row is None:
        raise ValueError(f"No track with track_id={track_id}")
    track_name = row[0]

    cur.execute("""
        SELECT TOP 1 l.lap_time_ms, l.session_id, s.session_date
        FROM dbo.laps l
        JOIN dbo.sessions s ON s.session_id = l.session_id
        JOIN dbo.events e ON e.event_id = s.event_id
        WHERE e.track_id = ? AND l.is_valid = 1
        ORDER BY l.lap_time_ms ASC""", track_id)
    pb_row = cur.fetchone()
    personal_best = None
    if pb_row is not None:
        personal_best = {
            "lap_time_ms": pb_row[0], "lap_time": fmt_ms(pb_row[0]),
            "session_id": pb_row[1], "session_date": str(pb_row[2]),
        }

    cur.execute("""
        SELECT benchmark_id, driver_name, lap_time_ms, set_date, notes
        FROM dbo.benchmarks WHERE track_id = ?
        ORDER BY lap_time_ms ASC""", track_id)
    benchmarks = [
        {
            "benchmark_id": r[0], "driver_name": r[1],
            "lap_time_ms": r[2], "lap_time": fmt_ms(r[2]),
            "set_date": str(r[3]) if r[3] is not None else None,
            "notes": r[4],
        }
        for r in cur.fetchall()
    ]

    return {
        "track_id": track_id, "track_name": track_name,
        "personal_best": personal_best, "benchmarks": benchmarks,
    }


def get_consumables(cnx):
    """Every tracked consumable with sessions/months elapsed since
    install, so the dashboard can render remaining-life bars without
    the caller doing date math."""
    cur = cnx.cursor()
    cur.execute("""
        SELECT c.consumable_id, c.item_name, c.install_date,
               c.install_session_id, c.service_life_sessions,
               c.service_life_months, c.notes, c.car_id, car.display_name,
               c.baseline_sessions + (
                   SELECT COUNT(*) FROM dbo.sessions s2
                   WHERE s2.session_date >= c.install_date
                     AND (c.car_id IS NULL OR s2.car_id = c.car_id)
               ) AS sessions_since_install,
               DATEDIFF(month, c.install_date, GETDATE())
                   AS months_since_install
        FROM dbo.consumables c
        LEFT JOIN dbo.cars car ON car.car_id = c.car_id
        ORDER BY c.item_name""")

    consumables = []
    for r in cur.fetchall():
        service_life_sessions, service_life_months = r[4], r[5]
        sessions_since, months_since = r[9], r[10]

        remaining_pct = None
        if service_life_sessions:
            remaining_pct = 1 - sessions_since / service_life_sessions
        if service_life_months:
            by_months = 1 - months_since / service_life_months
            remaining_pct = (by_months if remaining_pct is None
                              else min(remaining_pct, by_months))

        consumables.append({
            "consumable_id": r[0], "item_name": r[1],
            "install_date": str(r[2]),
            "install_session_id": r[3],
            "service_life_sessions": service_life_sessions,
            "service_life_months": service_life_months,
            "notes": r[6],
            "car_id": r[7], "car": r[8],
            "sessions_since_install": sessions_since,
            "months_since_install": months_since,
            "remaining_pct": (round(max(0.0, remaining_pct) * 100, 1)
                              if remaining_pct is not None else None),
            "overdue": (remaining_pct is not None and remaining_pct <= 0),
        })
    return consumables
