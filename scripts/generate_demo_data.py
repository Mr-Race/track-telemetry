#!/usr/bin/env python3
"""Generate the static fixtures behind demo.mr-race.com.

The demo is a static site (ADR-012): the same React app compiled with a
demo flag, reading these JSON files instead of the API. That deletes the
isolation problem rather than solving it — fictional data never shares a
database with real GPS traces, so no forgotten `WHERE` clause can leak
one into the other.

**The sessions are invented. The track geometry is real.** Corner
layouts at NJMP are public facts about a racetrack, not personal data;
what makes telemetry personal is whose car was where and when. Reusing
the real corner catalogue makes the demo behave like the product,
because the analysis views are driven by corner codes.

Determinism matters: same seed, same fixtures, so a rebuild produces a
reviewable diff instead of noise.

    python scripts/generate_demo_data.py            # -> dashboard/public/demo-api
    python scripts/generate_demo_data.py --out DIR

Every file is written at the path the client requests plus `.json`,
because `getJson` appends that suffix in demo mode.
"""

import argparse
import json
import os
import random

SEED = 20260817

# Real corner catalogues (public track geometry). Sessions on top are not.
CORNERS = {
    1: [("1", None), ("2", None), ("3", None), ("4", None), ("5", None),
        ("6", None), ("7", None), ("8", None), ("9", "Lightbulb"),
        ("10", "Kink")],
    2: [("1", None), ("2", None), ("3", None), ("4", None), ("5", None),
        ("6", None), ("7", None), ("8", None), ("9", None), ("10", None),
        ("11A", None), ("11B", None), ("12", None)],
}

TRACKS = {
    1: {"track_name": "NJMP Lightning", "configuration": "Full Course",
        "length_miles": 1.9, "base_lap_ms": 84_500},
    2: {"track_name": "NJMP Thunderbolt", "configuration": "Classic",
        "length_miles": 2.25, "base_lap_ms": 106_000},
}

DRIVER = "Alex Rivera"
CAR = {"car_id": 1, "display_name": "BRZ", "make": "Subaru", "model": "BRZ",
       "year": 2019, "notes": "Demo car. Fictional, like everything else here."}
ORG = {"organization_id": 1, "org_code": "APEX", "org_name": "Apex Track Days"}

# Three events with an arc: a first outing, a wet day, and a quick one.
EVENTS = [
    {"event_id": 1, "event_name": "Spring Opener", "track_id": 1,
     "start_date": "2026-04-18", "end_date": None, "run_group": "Novice",
     "sessions": 3, "pace": 1.035, "improve": 0.006,
     "weather": ["Partly cloudy", "Clear"], "temp": (61.0, 68.0)},
    {"event_id": 2, "event_name": "Summer Sizzle", "track_id": 2,
     "start_date": "2026-06-13", "end_date": "2026-06-14", "run_group": "Intermediate",
     "sessions": 5, "pace": 1.018, "improve": 0.005,
     "weather": ["Overcast", "Light rain"], "temp": (72.0, 79.0)},
    {"event_id": 3, "event_name": "Autumn Cup", "track_id": 2,
     "start_date": "2026-09-26", "end_date": None, "run_group": "Advanced",
     "sessions": 4, "pace": 1.000, "improve": 0.004,
     "weather": ["Clear", "Mainly clear"], "temp": (57.0, 64.0)},
]


def fmt_ms(ms):
    """`1:46.482` - matches the API's formatting so the UI needs no
    special case for demo data."""
    if ms is None:
        return None
    total = ms / 1000.0
    return f"{int(total // 60)}:{total % 60:06.3f}"


def build(rng):
    sessions, events, session_id = [], [], 1

    for ev in EVENTS:
        track = TRACKS[ev["track_id"]]
        corners = CORNERS[ev["track_id"]]
        ev_sessions = []

        for n in range(1, ev["sessions"] + 1):
            # Pace improves across the day, with an out-lap and an in-lap
            # that are deliberately slower and marked invalid.
            factor = ev["pace"] - ev["improve"] * (n - 1)
            base = track["base_lap_ms"] * factor
            lap_count = rng.choice([7, 8, 9])
            laps = []
            for lap_no in range(1, lap_count + 1):
                out_lap = lap_no == 1
                in_lap = lap_no == lap_count
                jitter = rng.uniform(-0.004, 0.010)
                ms = base * (1 + jitter)
                if out_lap:
                    ms = base * rng.uniform(1.28, 1.42)
                elif in_lap:
                    ms = base * rng.uniform(1.18, 1.30)
                laps.append({
                    "lap_number": lap_no,
                    "lap_time_ms": int(ms),
                    "lap_time": fmt_ms(int(ms)),
                    "is_valid": not (out_lap or in_lap),
                    "is_out_lap": out_lap,
                    "is_in_lap": in_lap,
                })

            valid = [l for l in laps if l["is_valid"]]
            best = min(valid, key=lambda l: l["lap_time_ms"])
            avg = int(sum(l["lap_time_ms"] for l in valid) / len(valid))
            # Optimal is the theoretical stitch of best sectors, so it is
            # always a little quicker than the best actual lap.
            optimal = int(best["lap_time_ms"] * rng.uniform(0.978, 0.993))

            wx = ev["weather"][min(n - 1, len(ev["weather"]) - 1)] \
                if n > ev["sessions"] - len(ev["weather"]) else ev["weather"][0]
            temp = round(rng.uniform(*ev["temp"]), 1)
            hour = 9 + (n - 1) * 2

            row = {
                "session_id": session_id,
                "event_id": ev["event_id"],
                "event_name": ev["event_name"],
                "track_name": track["track_name"],
                "session_number": n,
                "session_date": ev["start_date"],
                "run_group": ev["run_group"],
                "weather": wx,
                "air_temp_f": temp,
                "best_lap_ms": best["lap_time_ms"],
                "best_lap": best["lap_time"],
                "avg_valid_lap_ms": avg,
                "avg_valid_lap": fmt_ms(avg),
                "car": CAR["display_name"],
                "optimal_lap_ms": optimal,
                "optimal_lap": fmt_ms(optimal),
            }
            row["_laps"] = laps
            row["_track_id"] = ev["track_id"]
            row["_corners"] = corners
            row["_start_time"] = f"{ev['start_date']}T{hour:02d}:{rng.randrange(0,59):02d}:00"
            sessions.append(row)
            ev_sessions.append(row)
            session_id += 1

        events.append({"ev": ev, "sessions": ev_sessions})

    return sessions, events


def corner_deltas(rng, corners, improving=True):
    """Per-corner minimum speed against the prior session. Small,
    mostly-positive deltas read like a driver actually improving."""
    out = []
    for code, name in corners:
        prior = round(rng.uniform(42.0, 96.0), 1)
        delta = round(rng.uniform(-0.8, 2.6) if improving
                      else rng.uniform(-2.4, 0.9), 1)
        out.append({
            "corner_code": code,
            "corner_name": name,
            "min_speed_mph": round(prior + delta, 1),
            "prior_min_speed_mph": prior,
            "delta_mph": delta,
        })
    return out


def write(path, payload, out_dir):
    full = os.path.join(out_dir, path.lstrip("/") + ".json")
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as fh:
        json.dump(payload, fh, indent=1)
    return full


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    # Deliberately NOT dashboard/public: Vite copies public/ into every
    # build, so fixtures living there would ship 35 fictional JSON files
    # to www.mr-race.com on the next release. `npm run build:demo` copies
    # them into the demo bundle instead.
    ap.add_argument("--out", default=os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "dashboard", "demo-fixtures"))
    args = ap.parse_args()

    rng = random.Random(SEED)
    sessions, events = build(rng)
    written = []

    public = [{k: v for k, v in s.items() if not k.startswith("_")}
              for s in sessions]
    written.append(write("/sessions", public, args.out))

    for s in sessions:
        detail = {k: v for k, v in s.items() if not k.startswith("_")}
        detail.update({
            "track_id": s["_track_id"],
            "source_file": f"demo_session_{s['session_id']}.csv",
            "car_id": CAR["car_id"],
            "laps": s["_laps"],
            "corner_coverage": [c for c, _ in s["_corners"]],
        })
        written.append(write(f"/sessions/{s['session_id']}", detail, args.out))

        valid = [l for l in s["_laps"] if l["is_valid"]]
        times = [l["lap_time_ms"] for l in valid]
        mean = sum(times) / len(times)
        stdev = int((sum((t - mean) ** 2 for t in times) / len(times)) ** 0.5)
        prior = s["session_id"] - 1 if s["session_number"] > 1 else None
        summary = dict(detail)
        summary.pop("laps", None)
        summary.pop("corner_coverage", None)
        summary.update({
            "fastest_lap_ms": s["best_lap_ms"],
            "fastest_lap": s["best_lap"],
            "valid_lap_count": len(valid),
            "consistency_stdev_ms": stdev,
            "gap_to_optimal_ms": s["best_lap_ms"] - s["optimal_lap_ms"],
            "prior_session_id": prior,
            "corner_deltas": corner_deltas(rng, s["_corners"]) if prior else [],
        })
        written.append(write(f"/sessions/{s['session_id']}/summary",
                              summary, args.out))

    # Tracks, with the personal best across all demo sessions.
    track_rows = []
    for tid, t in TRACKS.items():
        mine = [s for s in sessions if s["_track_id"] == tid]
        pb = min(mine, key=lambda s: s["best_lap_ms"])
        track_rows.append({
            "track_id": tid, "track_name": t["track_name"],
            "configuration": t["configuration"],
            "length_miles": t["length_miles"],
            "corner_count": len(CORNERS[tid]),
            "personal_best": {
                "lap_time_ms": pb["best_lap_ms"],
                "lap_time": pb["best_lap"],
                "session_id": pb["session_id"],
                "session_date": pb["session_date"],
            },
        })
        written.append(write(f"/tracks/{tid}/benchmarks", {
            "track_id": tid, "track_name": t["track_name"],
            "personal_best": {
                "lap_time_ms": pb["best_lap_ms"], "lap_time": pb["best_lap"],
                "session_id": pb["session_id"],
                "session_date": pb["session_date"],
            },
            "benchmarks": [
                {"benchmark_id": 1, "driver_name": "Sam Whitfield",
                 "lap_time_ms": int(pb["best_lap_ms"] * 0.965),
                 "lap_time": fmt_ms(int(pb["best_lap_ms"] * 0.965)),
                 "set_date": "2026-05-02", "notes": "Same car, stickier tyres."},
                {"benchmark_id": 2, "driver_name": "Jordan Pike",
                 "lap_time_ms": int(pb["best_lap_ms"] * 1.021),
                 "lap_time": fmt_ms(int(pb["best_lap_ms"] * 1.021)),
                 "set_date": "2026-06-20", "notes": None},
            ],
        }, args.out))
    written.append(write("/tracks", track_rows, args.out))

    # Events list and per-event summaries.
    ev_rows = []
    for bundle in events:
        ev, evs = bundle["ev"], bundle["sessions"]
        t = TRACKS[ev["track_id"]]
        ev_rows.append({
            "event_id": ev["event_id"], "event_name": ev["event_name"],
            "track_id": ev["track_id"], "track_name": t["track_name"],
            "organization_id": ORG["organization_id"],
            "org_code": ORG["org_code"],
            "start_date": ev["start_date"], "end_date": ev["end_date"],
            "session_count": len(evs), "phase": "past",
        })

        best = min(evs, key=lambda s: s["best_lap_ms"])
        opt = min(s["optimal_lap_ms"] for s in evs)
        total_laps = sum(len(s["_laps"]) for s in evs)
        valid_laps = sum(len([l for l in s["_laps"] if l["is_valid"]])
                         for s in evs)
        best_lap_row = min((l for l in best["_laps"] if l["is_valid"]),
                           key=lambda l: l["lap_time_ms"])
        written.append(write(f"/events/{ev['event_id']}/summary", {
            "event_id": ev["event_id"], "event_name": ev["event_name"],
            "track_id": ev["track_id"], "track_name": t["track_name"],
            "configuration": t["configuration"],
            "org_code": ORG["org_code"], "run_group": ev["run_group"],
            "start_date": ev["start_date"], "end_date": ev["end_date"],
            "session_count": len(evs), "total_laps": total_laps,
            "valid_lap_count": valid_laps,
            "total_track_time_ms": sum(l["lap_time_ms"] for s in evs
                                        for l in s["_laps"]),
            "best_lap_ms": best["best_lap_ms"], "best_lap": best["best_lap"],
            "best_lap_session_id": best["session_id"],
            "best_lap_session_number": best["session_number"],
            "best_lap_number": best_lap_row["lap_number"],
            "optimal_lap_ms": opt, "optimal_lap": fmt_ms(opt),
            "left_on_table_ms": best["best_lap_ms"] - opt,
            "progression_ms": evs[0]["best_lap_ms"] - evs[-1]["best_lap_ms"],
            "corner_deltas": corner_deltas(rng, CORNERS[ev["track_id"]]),
            "weather": {
                "temp_min_f": min(s["air_temp_f"] for s in evs),
                "temp_max_f": max(s["air_temp_f"] for s in evs),
                "conditions": sorted({s["weather"] for s in evs}),
            },
            "sessions": [{
                "session_id": s["session_id"],
                "session_number": s["session_number"],
                "driver": DRIVER,
                "start_time": s["_start_time"],
                "best_lap_ms": s["best_lap_ms"], "best_lap": s["best_lap"],
                "avg_valid_lap_ms": s["avg_valid_lap_ms"],
                "avg_valid_lap": s["avg_valid_lap"],
                "optimal_lap_ms": s["optimal_lap_ms"],
                "optimal_lap": s["optimal_lap"],
                "air_temp_f": s["air_temp_f"],
            } for s in evs],
        }, args.out))
    written.append(write("/events", ev_rows, args.out))

    written.append(write("/organizations", [ORG], args.out))
    written.append(write("/cars", [CAR], args.out))

    # Consumables across the range, including one overdue so every status
    # colour appears rather than only the healthy one.
    total_sessions = len(sessions)
    consumables = [
        ("Front brake pads", 12, None, 4, False),
        ("Rear brake pads", 12, None, 2, False),
        ("Brake fluid", 20, 12, 17, False),
        ("Engine oil", 8, 6, 9, True),
        ("Front tyres", 15, None, 11, False),
    ]
    rows = []
    for i, (name, life_s, life_m, used, overdue) in enumerate(consumables, 1):
        rows.append({
            "consumable_id": i, "item_name": name,
            "install_date": "2026-04-18",
            "install_session_id": 1,
            "service_life_sessions": life_s,
            "service_life_months": life_m,
            "notes": None, "car_id": CAR["car_id"],
            "car": CAR["display_name"],
            "sessions_since_install": used,
            "months_since_install": 5,
            "remaining_pct": None if life_s is None
                              else round(max(0.0, 1 - used / life_s) * 100, 1),
            "overdue": overdue,
        })
    written.append(write("/consumables", rows, args.out))

    print(f"  {len(written)} files -> {args.out}")
    print(f"  {len(sessions)} sessions across {len(events)} events, "
          f"{total_sessions} total")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
