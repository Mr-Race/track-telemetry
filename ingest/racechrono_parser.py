#!/usr/bin/env python3
"""
RaceChrono CSV v3 -> Azure SQL loader for the track telemetry platform.

Usage:
  Dry run (parse + validate, no DB writes):
    python racechrono_parser.py session.csv --server X.database.windows.net \
        --database sqldb-telemetry --event-id 1 --session-number 2
  Load after dry run looks right: add --load

Design notes:
  - Stdlib-only for parsing (csv, math). pyodbc/azure auth imported lazily,
    so dry-run parsing works on any machine with bare Python 3.
  - Lap boundaries: lap N time = first-sample elapsed of lap N+1 minus
    first-sample elapsed of lap N (final lap uses its last sample; it is
    flagged in-lap anyway).
  - Corner metrics: min GPS speed within each corner's zone_radius_m of
    its apex point; entry/exit speeds at first/last sample inside zone.
  - Speeds converted m/s -> mph at parse time. Times stored as ms.
"""

import argparse
import csv
import logging
import math
import sys
from datetime import datetime, timezone

MPS_TO_MPH = 2.23694


# ---------------------------------------------------------------- parsing

def parse_csv(path):
    """Return (metadata dict, list of sample dicts)."""
    with open(path, newline="") as fh:
        rows = list(csv.reader(fh))

    meta = {}
    hidx = None
    for i, r in enumerate(rows):
        if r and r[0] == "timestamp":
            hidx = i
            break
        if len(r) >= 2:
            meta[r[0]] = r[1] if len(r) == 2 else ",".join(r[1:])
    if hidx is None:
        raise ValueError("No channel header row found - is this a v3 export?")

    names, units, sources = rows[hidx], rows[hidx + 1], rows[hidx + 2]

    def col(name, source=None):
        for i, n in enumerate(names):
            if n == name and (source is None or sources[i].strip() == source):
                return i
        raise ValueError(f"Column not found: {name} (source={source})")

    ci = {
        "ts": col("timestamp"),
        "lap": col("lap_number"),
        "elapsed": col("elapsed_time"),
        "lat": col("latitude", "100: gps"),
        "lon": col("longitude", "100: gps"),
        "speed": col("speed", "100: gps"),
    }

    # OBD channels are only present when the device is paired to the
    # car's OBD-II port - absent on some exports, so look these up
    # optionally rather than failing the whole parse.
    obd_ci = {}
    for name in ("rpm", "throttle_pos"):
        try:
            obd_ci[name] = col(name, "200: obd")
        except ValueError:
            obd_ci[name] = None

    samples = []
    for r in rows[hidx + 3:]:
        if not r or len(r) != len(names):
            continue
        lap = r[ci["lap"]].strip()
        if not lap:
            continue  # pre-first-crossing / pit samples
        spd = r[ci["speed"]].strip()
        lat = r[ci["lat"]].strip()
        lon = r[ci["lon"]].strip()
        if not (spd and lat and lon):
            continue

        def obd_value(channel):
            i = obd_ci[channel]
            if i is None or not r[i].strip():
                return None
            return float(r[i])

        samples.append({
            "ts": float(r[ci["ts"]]),
            "lap": int(lap),
            "elapsed": float(r[ci["elapsed"]]),
            "lat": float(lat),
            "lon": float(lon),
            "mph": float(spd) * MPS_TO_MPH,
            "rpm": obd_value("rpm"),
            "throttle_pos": obd_value("throttle_pos"),
        })
    if not samples:
        raise ValueError("No lap-numbered samples found in file.")
    return meta, samples


def compute_laps(samples):
    """Return list of lap dicts with times and flags."""
    first_elapsed = {}
    last_elapsed = {}
    for s in samples:
        if s["lap"] not in first_elapsed:
            first_elapsed[s["lap"]] = s["elapsed"]
        last_elapsed[s["lap"]] = s["elapsed"]

    lap_nums = sorted(first_elapsed)
    durs = []
    for i, ln in enumerate(lap_nums):
        if i + 1 < len(lap_nums):
            durs.append(first_elapsed[lap_nums[i + 1]] - first_elapsed[ln])
        else:
            durs.append(last_elapsed[ln] - first_elapsed[ln])

    # Evidence-based out/in-lap flags: RaceChrono only numbers laps
    # after the first S/F crossing, so lap 1 may already be flying.
    # Flag first/last laps only if >12% slower than the session median.
    med = sorted(durs)[len(durs) // 2]
    laps = []
    for i, (ln, dur) in enumerate(zip(lap_nums, durs)):
        slow = dur > med * 1.12
        laps.append({
            "lap_number": ln,
            "lap_time_ms": round(dur * 1000),
            "is_out_lap": 1 if (i == 0 and slow) else 0,
            "is_in_lap": 1 if (i == len(lap_nums) - 1 and slow) else 0,
            "is_valid": 0 if slow else 1,  # flying laps only
        })
    return laps


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def compute_corner_metrics(samples, corners):
    """corners: list of dicts with corner_code, corner_id (optional),
    apex_lat, apex_lon, zone_radius_m.
    Returns list of dicts: lap_number, corner_code, min/entry/exit mph."""
    metrics = []
    by_lap = {}
    for s in samples:
        by_lap.setdefault(s["lap"], []).append(s)

    for ln, pts in sorted(by_lap.items()):
        for c in corners:
            if c.get("apex_lat") is None:
                continue
            inside = [p for p in pts
                      if haversine_m(p["lat"], p["lon"],
                                     c["apex_lat"], c["apex_lon"])
                      <= c["zone_radius_m"]]
            if not inside:
                continue
            apex = min(inside, key=lambda p: p["mph"])
            exit_sample = inside[-1]
            metrics.append({
                "lap_number": ln,
                "corner_code": c["corner_code"],
                "corner_id": c.get("corner_id"),
                "min_speed_mph": round(apex["mph"], 1),
                "entry_speed_mph": round(inside[0]["mph"], 1),
                "exit_speed_mph": round(exit_sample["mph"], 1),
                "throttle_pos_apex_pct": (
                    round(apex["throttle_pos"], 1)
                    if apex["throttle_pos"] is not None else None),
                "rpm_exit": (
                    round(exit_sample["rpm"], 1)
                    if exit_sample["rpm"] is not None else None),
            })
    return metrics


def _closest_approach_time(pts, apex_lat, apex_lon):
    """Interpolated elapsed-time of closest approach to (apex_lat,
    apex_lon) among pts (chronologically ordered lap samples), via
    parabolic interpolation around the sample of minimum distance.
    The raw per-sample minimum jitters by up to one sample interval
    depending on GPS timing - fine for entry/exit speed, but too
    imprecise as a segment-time gate when summed across many corners.
    """
    dists = [haversine_m(p["lat"], p["lon"], apex_lat, apex_lon) for p in pts]
    i = min(range(len(dists)), key=lambda k: dists[k])
    if i == 0 or i == len(pts) - 1:
        return pts[i]["elapsed"]

    t0, t1, t2 = pts[i - 1]["elapsed"], pts[i]["elapsed"], pts[i + 1]["elapsed"]
    f0, f1, f2 = dists[i - 1], dists[i], dists[i + 1]
    denom = (t1 - t0) * (f1 - f2) - (t1 - t2) * (f1 - f0)
    if denom == 0:
        return t1
    t_star = t1 - 0.5 * ((t1 - t0) ** 2 * (f1 - f2) -
                         (t1 - t2) ** 2 * (f1 - f0)) / denom
    return t_star if t0 <= t_star <= t2 else t1


def compute_segment_times(samples, corners):
    """Per-lap corner-to-corner segment times (see sql/16_segment_times.sql
    for the full rationale). Returns a list of dicts: lap_number,
    segment_order, to_corner_id (None for the final segment),
    segment_time_ms. A lap with any unresolved or out-of-order gate is
    left out entirely rather than guessing at a partial chain."""
    valid_corners = [c for c in corners if c.get("apex_lat") is not None]
    if not valid_corners:
        return []

    by_lap = {}
    for s in samples:
        by_lap.setdefault(s["lap"], []).append(s)
    for pts in by_lap.values():
        pts.sort(key=lambda p: p["elapsed"])

    lap_nums = sorted(by_lap)
    first_elapsed = {ln: by_lap[ln][0]["elapsed"] for ln in lap_nums}

    segments = []
    for i, ln in enumerate(lap_nums):
        pts = by_lap[ln]
        lap_end = (first_elapsed[lap_nums[i + 1]] if i + 1 < len(lap_nums)
                   else pts[-1]["elapsed"])

        gate_times = []
        for c in valid_corners:
            if not any(haversine_m(p["lat"], p["lon"],
                                    c["apex_lat"], c["apex_lon"])
                       <= c["zone_radius_m"] for p in pts):
                gate_times = None
                break
            gate_times.append(
                _closest_approach_time(pts, c["apex_lat"], c["apex_lon"]))
        if gate_times is None:
            continue

        boundaries = [pts[0]["elapsed"], *gate_times, lap_end]
        if any(b1 <= b0 for b0, b1 in zip(boundaries, boundaries[1:])):
            continue  # bad GPS/interpolation produced a non-chronological gate

        to_corner_ids = [c.get("corner_id") for c in valid_corners] + [None]
        for order, (t0, t1, corner_id) in enumerate(
                zip(boundaries, boundaries[1:], to_corner_ids), start=1):
            segments.append({
                "lap_number": ln,
                "segment_order": order,
                "to_corner_id": corner_id,
                "segment_time_ms": round((t1 - t0) * 1000),
            })
    return segments


def fmt_ms(ms):
    return f"{ms // 60000}:{(ms % 60000) / 1000:06.3f}"


# ---------------------------------------------------------------- database

def get_connection(server, database, auth="interactive"):
    import struct
    import pyodbc
    from azure.identity import (DefaultAzureCredential,
                                InteractiveBrowserCredential)

    cred = (DefaultAzureCredential() if auth == "default"
            else InteractiveBrowserCredential())
    token = cred.get_token("https://database.windows.net/.default").token
    tb = token.encode("utf-16-le")
    token_struct = struct.pack(f"<I{len(tb)}s", len(tb), tb)
    SQL_COPT_SS_ACCESS_TOKEN = 1256

    drivers = [d for d in pyodbc.drivers() if "SQL Server" in d]
    if not drivers:
        raise RuntimeError("No SQL Server ODBC driver found.")
    driver = sorted(drivers)[-1]

    conn_str = (
        f"Driver={{{driver}}};"
        f"Server=tcp:{server},1433;Database={database};"
        "Encrypt=yes;TrustServerCertificate=no;"
    )
    return pyodbc.connect(
        conn_str, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct})


def fetch_corners(cnx, event_id):
    cur = cnx.cursor()
    cur.execute("""
        SELECT c.corner_id, c.corner_code, c.apex_lat, c.apex_lon,
               c.zone_radius_m
        FROM dbo.corners c
        JOIN dbo.events e ON e.track_id = c.track_id
        WHERE e.event_id = ?
        ORDER BY c.sort_order""", event_id)
    return [{"corner_id": r[0], "corner_code": r[1],
             "apex_lat": float(r[2]) if r[2] is not None else None,
             "apex_lon": float(r[3]) if r[3] is not None else None,
             "zone_radius_m": r[4]} for r in cur.fetchall()]


def parse_session_date(meta):
    created = meta.get("Created", "")
    if not created:
        return None
    return datetime.strptime(created.split(",")[0], "%d/%m/%Y").date()


def resolve_event_id(cnx, meta):
    """Auto-match the CSV's track name + date against an event already
    created on the dashboard, so phone uploads don't need a manual
    event_id prompt."""
    track_name = meta.get("Track name")
    session_date = parse_session_date(meta)
    if not track_name or session_date is None:
        raise ValueError(
            "Can't auto-match an event: CSV is missing 'Track name' or "
            "'Created' date.")

    cur = cnx.cursor()
    cur.execute("""
        SELECT e.event_id
        FROM dbo.events e
        JOIN dbo.tracks t ON t.track_id = e.track_id
        WHERE t.track_name = ?
          AND e.start_date <= ?
          AND ISNULL(e.end_date, e.start_date) >= ?""",
        track_name, session_date, session_date)
    rows = cur.fetchall()
    if not rows:
        raise ValueError(
            f"No event found for '{track_name}' on {session_date}. "
            "Create the event on the dashboard first, or pass event_id "
            "explicitly.")
    if len(rows) > 1:
        raise ValueError(
            f"Multiple events match '{track_name}' on {session_date} "
            f"({[r[0] for r in rows]}) - pass event_id explicitly.")
    return rows[0][0]


def next_session_number(cnx, event_id):
    cur = cnx.cursor()
    cur.execute("""
        SELECT ISNULL(MAX(session_number), 0) + 1
        FROM dbo.sessions WHERE event_id = ?""", event_id)
    return cur.fetchone()[0]


def fetch_session_weather(cnx, event_id, start_time):
    """Best-effort weather lookup via Open-Meteo, keyed on the event's
    track location (corner apex centroid) and the session's start
    time. Returns weather.EMPTY on any failure (no corner coords yet,
    API error/timeout) so a flaky external call never blocks an
    ingest."""
    from ingest import weather

    corners = fetch_corners(cnx, event_id)
    lats = [c["apex_lat"] for c in corners if c["apex_lat"] is not None]
    lons = [c["apex_lon"] for c in corners if c["apex_lon"] is not None]
    if not lats or not lons:
        return weather.EMPTY
    try:
        return weather.fetch_weather(
            sum(lats) / len(lats), sum(lons) / len(lons), start_time)
    except Exception:
        logging.warning("weather fetch failed for event_id=%s", event_id,
                         exc_info=True)
        return weather.EMPTY


def load(cnx, event_id, session_number, source_filename, meta, samples,
         laps, metrics, car_id=None, segments=None):
    session_date = parse_session_date(meta)
    start_time = datetime.fromtimestamp(samples[0]["ts"], tz=timezone.utc)
    w = fetch_session_weather(cnx, event_id, start_time)

    cur = cnx.cursor()
    cur.execute("""
        INSERT INTO dbo.sessions
            (event_id, session_number, session_date, start_time,
             source_file, car_id, weather, air_temp_f, humidity_pct,
             wind_mph, precip_in, weather_observed_at)
        OUTPUT INSERTED.session_id
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        event_id, session_number, session_date, start_time,
        source_filename, car_id, w["weather"], w["air_temp_f"],
        w["humidity_pct"], w["wind_mph"], w["precip_in"],
        w["weather_observed_at"])
    session_id = cur.fetchone()[0]

    lap_ids = {}
    for l in laps:
        cur.execute("""
            INSERT INTO dbo.laps
                (session_id, lap_number, lap_time_ms, is_valid,
                 is_out_lap, is_in_lap)
            OUTPUT INSERTED.lap_id
            VALUES (?,?,?,?,?,?)""",
            session_id, l["lap_number"], l["lap_time_ms"],
            l["is_valid"], l["is_out_lap"], l["is_in_lap"])
        lap_ids[l["lap_number"]] = cur.fetchone()[0]

    for m in metrics:
        cur.execute("""
            INSERT INTO dbo.corner_metrics
                (lap_id, corner_id, min_speed_mph,
                 entry_speed_mph, exit_speed_mph,
                 throttle_pos_apex_pct, rpm_exit)
            VALUES (?,?,?,?,?,?,?)""",
            lap_ids[m["lap_number"]], m["corner_id"], m["min_speed_mph"],
            m["entry_speed_mph"], m["exit_speed_mph"],
            m["throttle_pos_apex_pct"], m["rpm_exit"])

    for seg in (segments or []):
        cur.execute("""
            INSERT INTO dbo.segment_times
                (lap_id, segment_order, to_corner_id, segment_time_ms)
            VALUES (?,?,?,?)""",
            lap_ids[seg["lap_number"]], seg["segment_order"],
            seg["to_corner_id"], seg["segment_time_ms"])

    cnx.commit()
    return session_id


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--server")
    ap.add_argument("--database")
    ap.add_argument("--event-id", type=int)
    ap.add_argument("--session-number", type=int, default=1)
    ap.add_argument("--car-id", type=int, default=None)
    ap.add_argument("--load", action="store_true",
                    help="write to DB (default is dry run)")
    ap.add_argument("--auth", choices=["interactive", "default"],
                    default="interactive",
                    help="use 'default' inside Azure Cloud Shell")
    ap.add_argument("--corners-json",
                    help="local corner defs for offline dry run")
    args = ap.parse_args()

    meta, samples = parse_csv(args.csv)
    laps = compute_laps(samples)

    corners = []
    cnx = None
    if args.corners_json:
        import json
        with open(args.corners_json) as fh:
            corners = json.load(fh)
    elif args.server and args.event_id:
        cnx = get_connection(args.server, args.database, args.auth)
        corners = fetch_corners(cnx, args.event_id)

    metrics = compute_corner_metrics(samples, corners) if corners else []
    segments = compute_segment_times(samples, corners) if corners else []

    print(f"\nFile: {args.csv}")
    print(f"Track: {meta.get('Track name','?')}  "
          f"Created: {meta.get('Created','?')}  "
          f"Samples: {len(samples)}")
    print(f"\n{'lap':>4} {'time':>10}  flags")
    for l in laps:
        flags = ("OUT" if l["is_out_lap"] else "") + \
                ("IN" if l["is_in_lap"] else "")
        print(f"{l['lap_number']:>4} {fmt_ms(l['lap_time_ms']):>10}  {flags}")

    if metrics:
        codes = sorted({m['corner_code'] for m in metrics},
                       key=lambda c: (len(c), c))
        print(f"\nCorner coverage: {len(codes)} corners "
              f"({', '.join('T'+c for c in codes)})")
        best = min((l for l in laps
                    if not l['is_out_lap'] and not l['is_in_lap']),
                   key=lambda l: l['lap_time_ms'], default=None)
        if best:
            print(f"\nBest flying lap {best['lap_number']} "
                  f"({fmt_ms(best['lap_time_ms'])}) corner speeds:")
            for m in metrics:
                if m["lap_number"] == best["lap_number"]:
                    print(f"  T{m['corner_code']:<4} "
                          f"min {m['min_speed_mph']:5.1f}  "
                          f"entry {m['entry_speed_mph']:5.1f}  "
                          f"exit {m['exit_speed_mph']:5.1f}")

    if segments:
        laps_covered = len({s["lap_number"] for s in segments})
        print(f"\nSegment times: {laps_covered}/{len(laps)} laps with a "
              f"complete gate chain ({len(segments)} segment rows)")

    if args.load:
        if cnx is None:
            sys.exit("--load requires --server/--database/--event-id")
        sid = load(cnx, args.event_id, args.session_number,
                   args.csv.split("/")[-1], meta, samples, laps, metrics,
                   car_id=args.car_id, segments=segments)
        print(f"\nLoaded as session_id {sid}: {len(laps)} laps, "
              f"{len(metrics)} corner metrics, {len(segments)} segments.")
    else:
        print("\nDry run only. Re-run with --load to write to the database.")


if __name__ == "__main__":
    main()
