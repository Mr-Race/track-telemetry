"""Pedal-position normalisation.

Raw OBD pedal values are not percent-of-travel. A pedal position sensor
has a voltage baseline, so on this car the pedal at rest reads 18.82%
and at the stop reads 94.90% (issue #8). Reporting a corner as "18.8%
throttle" when the driver's foot was completely off the pedal is a wrong
answer, not a rounding difference.

Normalisation happens here, on read. It is deliberately not applied at
ingest: stored values stay raw so that a future sensor or PID change
cannot make historical sessions double-correct.

Calibration is keyed on `(car_id, channel)` - throttle plate and true
pedal position are different signals with different endpoints, and the
archive contains both.
"""

# Values a hair outside the measured endpoints are ordinary sensor noise
# and mechanical slop, not evidence of bad calibration. Clamping keeps a
# displayed percentage inside 0-100 without hiding a genuinely wrong
# calibration, which would push values far outside this range.
FLOOR_PCT = 0.0
CEILING_PCT = 100.0


def normalize_pedal_pct(raw_pct, rest_pct, full_pct):
    """Convert a raw channel percentage to percent-of-travel.

    Returns None when the value or its calibration is missing - a
    session recorded without an OBD dongle, or one whose channel nobody
    has measured. None means "not known", and is the honest answer;
    returning the raw value would silently mix two different scales in
    one column.

    Raises ValueError on an unusable calibration rather than dividing by
    zero or mirroring the scale. The database has a CHECK constraint for
    this, so reaching it means the constants came from somewhere else.
    """
    if raw_pct is None or rest_pct is None or full_pct is None:
        return None

    raw, rest, full = float(raw_pct), float(rest_pct), float(full_pct)
    if full <= rest:
        raise ValueError(
            f"Unusable pedal calibration: full_pct ({full}) must exceed "
            f"rest_pct ({rest})")

    pct = (raw - rest) / (full - rest) * 100.0
    return max(FLOOR_PCT, min(CEILING_PCT, pct))


def calibration_map(cur):
    """`{(car_id, channel): (rest_pct, full_pct)}` for every calibration.

    Read once per request rather than per corner - a session detail page
    asks for hundreds of corner rows that all share one calibration.
    """
    cur.execute("""
        SELECT car_id, channel, rest_pct, full_pct
        FROM dbo.pedal_calibration""")
    return {(r[0], r[1]): (float(r[2]), float(r[3])) for r in cur.fetchall()}
