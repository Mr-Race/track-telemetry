"""Shared fixtures for the parser tests.

The real RaceChrono exports are 11-14 MB and live in `data/` (gitignored
- raw telemetry stays out of the repo, per the raw-data-is-sacred
principle). So the fixtures here are small synthetic v3 files built to
the same shape: metadata block, a three-row channel header
(names/units/sources), then samples.

Building them in code rather than committing sample CSVs keeps the
tests readable and lets each one vary exactly one thing.
"""

import textwrap

import pytest

# Channel layout mirrors a real v3 export. In a real file `speed`
# appears three times - under gps, obd and calc - so every fixture
# carries all three. The two decoys are appended by `build_csv` with
# deliberately wrong values (see DECOY_OFFSET): if the parser ever binds
# speed by name alone, or to the wrong device, the speeds these tests
# assert on move by a large, obvious amount instead of the file parsing
# happily with quietly wrong numbers.
BASE_NAMES = ["timestamp", "lap_number", "elapsed_time",
              "latitude", "longitude", "speed"]
BASE_UNITS = ["unix time", "", "s", "deg", "deg", "m/s"]
BASE_SOURCES = ["", "", "", "GPS", "GPS", "GPS"]

# Decoy speeds are offset far enough that a mis-bind can't be mistaken
# for a rounding difference.
DECOY_OFFSET = 50.0

OBD_UNITS = {"rpm": "rpm", "throttle_pos": "%", "accelerator_pos": "%"}


def build_csv(tmp_path, obd_channels=(), rows=None, name="session.csv",
              created="16/05/2026,18:06", track="NJMP Lightning",
              gps_source="100: gps", obd_source="200: obd",
              decoy_speeds=True):
    """Write a synthetic v3 export and return its path.

    obd_channels: channel names to append under source `200: obd`.
    rows: list of row-lists (already stringified). Defaults to a short
    two-lap run with plausible values.
    gps_source/obd_source: the source strings to write, so a test can
    vary the logging rate or device name the way RaceChrono would.
    decoy_speeds: append the obd and calc `speed` columns a real export
    carries. On by default - the realistic shape is the useful one.
    """
    names = BASE_NAMES + list(obd_channels)
    units = BASE_UNITS + [OBD_UNITS.get(c, "") for c in obd_channels]
    sources = [gps_source if s == "GPS" else s for s in BASE_SOURCES]
    sources += [obd_source] * len(obd_channels)

    if rows is None:
        rows = default_rows(len(obd_channels))

    if decoy_speeds:
        width = len(names)
        speed_i = BASE_NAMES.index("speed")
        names += ["speed", "speed"]
        units += ["m/s", "m/s"]
        sources += [obd_source, "calc"]

        def widen(r):
            # Rows of a deliberately wrong width are the malformed-row
            # tests' subject matter - leave them wrong. A blank speed is
            # the missing-GPS case, and its decoys are blank too.
            if len(r) != width:
                return list(r)
            raw = str(r[speed_i]).strip()
            if not raw:
                return list(r) + ["", ""]
            return list(r) + [f"{float(raw) + DECOY_OFFSET:.3f}",
                              f"{float(raw) + DECOY_OFFSET * 2:.3f}"]

        rows = [widen(r) for r in rows]

    header = textwrap.dedent(f"""\
        This file is created using RaceChrono Pro v10.2.4 ( http://racechrono.com/ ).
        Format,3
        Session title,"{track}"
        Session type,Lap timing
        Track name,"{track}"
        Driver name,
        Created,{created}
        Note,

        """)

    path = tmp_path / name
    lines = [",".join(names), ",".join(units), ",".join(sources)]
    lines += [",".join(str(c) for c in r) for r in rows]
    path.write_text(header + "\n".join(lines) + "\n")
    return path


def default_rows(n_obd):
    """Two laps of six samples, lap 2 slightly quicker than lap 1."""
    rows = []
    ts = 1778954779.0
    elapsed = 0.0
    for lap, step in ((1, 10.0), (2, 9.0)):
        for i in range(6):
            rows.append([
                f"{ts + elapsed:.3f}", lap, f"{elapsed:.3f}",
                f"{39.3607 + i * 0.0001:.6f}",
                f"{-75.0559 + i * 0.0001:.6f}",
                f"{20.0 + i:.3f}",
                *([f"{3000 + i * 100}", f"{40 + i}"][:n_obd]),
            ])
            elapsed += step / 6
    return rows


@pytest.fixture
def make_csv(tmp_path):
    """Factory so a test can build several variants in one body."""
    def _make(**kwargs):
        return build_csv(tmp_path, **kwargs)
    return _make


def samples_for_laps(durations, per_lap=5, lat=39.3607, lon=-75.0559,
                     mph=60.0):
    """Sample dicts for laps of the given durations, in seconds.

    compute_laps derives lap N's time from the *first* sample of lap N+1
    minus the first sample of lap N, so the samples within a lap are
    spread evenly across its duration and the next lap starts exactly
    where the previous one ends. The final lap has no successor, so its
    duration comes from its own last sample - which means it needs a
    sample at its full duration to measure the same way.
    """
    samples = []
    elapsed = 0.0
    for lap_number, dur in enumerate(durations, start=1):
        step = dur / per_lap
        for i in range(per_lap):
            samples.append({
                "ts": 1778954779.0 + elapsed + i * step,
                "lap": lap_number,
                "elapsed": elapsed + i * step,
                "lat": lat, "lon": lon, "mph": mph,
                "rpm": None, "throttle_pos": None,
            })
        elapsed += dur
    # Close out the final lap so its measured duration matches its
    # intended one rather than stopping a step short.
    samples.append({
        "ts": 1778954779.0 + elapsed, "lap": len(durations),
        "elapsed": elapsed, "lat": lat, "lon": lon, "mph": mph,
        "rpm": None, "throttle_pos": None,
    })
    return samples


@pytest.fixture
def laps_from():
    return samples_for_laps


# ---- geometry helpers, shared by the corner-metric and segment tests ----
# At NJMP's latitude one degree of latitude is ~111,320 m, so offsets are
# written in metres and converted. That keeps tests legible against the
# 25 m default zone radius.
APEX_LAT, APEX_LON = 39.36075, -75.05590
M_PER_DEG_LAT = 111_320.0


def geo_sample(offset_m, mph, lap=1, elapsed=0.0, rpm=None, throttle=None,
               apex_lat=APEX_LAT, apex_lon=APEX_LON):
    """A sample `offset_m` north of the given apex, at the given speed."""
    return {
        "lap": lap,
        "elapsed": elapsed,
        "lat": apex_lat + offset_m / M_PER_DEG_LAT,
        "lon": apex_lon,
        "mph": mph,
        "rpm": rpm,
        "throttle_pos": throttle,
    }


def geo_corner(code="1", radius=25, apex_lat=APEX_LAT, apex_lon=APEX_LON,
               corner_id=101):
    return {"corner_code": code, "corner_id": corner_id,
            "apex_lat": apex_lat, "apex_lon": apex_lon,
            "zone_radius_m": radius}
