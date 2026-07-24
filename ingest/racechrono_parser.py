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


def load(cnx, event_id, session_number, source_filename, meta, samples,
         laps, metrics):
    session_date = None
    created = meta.get("Created", "")
    if created:
        session_date = datetime.strptime(created.split(",")[0],
                                         "%d/%m/%Y").date()
    start_time = datetime.fromtimestamp(samples[0]["ts"], tz=timezone.utc)

    cur = cnx.cursor()
    cur.execute("""
        INSERT INTO dbo.sessions
            (event_id, session_number, session_date, start_time, source_file)
        OUTPUT INSERTED.session_id
        VALUES (?,?,?,?,?)""",
        event_id, session_number, session_date,
        start_time, source_filename)
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

    if args.load:
        if cnx is None:
            sys.exit("--load requires --server/--database/--event-id")
        sid = load(cnx, args.event_id, args.session_number,
                   args.csv.split("/")[-1], meta, samples, laps, metrics)
        print(f"\nLoaded as session_id {sid}: "
              f"{len(laps)} laps, {len(metrics)} corner metrics.")
    else:
        print("\nDry run only. Re-run with --load to write to the database.")


if __name__ == "__main__":
    main()
