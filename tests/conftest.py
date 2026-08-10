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

# Channel layout mirrors a real v3 export: `speed` appears three times
# under different sources, which is why the parser disambiguates GPS
# columns by source rather than by name alone.
BASE_NAMES = ["timestamp", "lap_number", "elapsed_time",
              "latitude", "longitude", "speed"]
BASE_UNITS = ["unix time", "", "s", "deg", "deg", "m/s"]
BASE_SOURCES = ["", "", "", "100: gps", "100: gps", "100: gps"]

OBD_UNITS = {"rpm": "rpm", "throttle_pos": "%", "accelerator_pos": "%"}


def build_csv(tmp_path, obd_channels=(), rows=None, name="session.csv",
              created="16/05/2026,18:06", track="NJMP Lightning"):
    """Write a synthetic v3 export and return its path.

    obd_channels: channel names to append under source `200: obd`.
    rows: list of row-lists (already stringified). Defaults to a short
    two-lap run with plausible values.
    """
    names = BASE_NAMES + list(obd_channels)
    units = BASE_UNITS + [OBD_UNITS.get(c, "") for c in obd_channels]
    sources = BASE_SOURCES + ["200: obd"] * len(obd_channels)

    if rows is None:
        rows = default_rows(len(obd_channels))

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
