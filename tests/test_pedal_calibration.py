"""Pedal-position normalisation (issue #8, part 2).

Raw OBD pedal values carry a sensor voltage baseline: on this car the
pedal at rest reads 18.82% and at the stop 94.90%. Percent-of-travel is
computed on read, never baked into stored values, so that a future
sensor or PID change cannot make history double-correct.

The cases that matter here are the ones that would be silently wrong
rather than loudly broken.
"""

import pytest

from ingest.pedal import calibration_map, normalize_pedal_pct

REST, FULL = 18.82, 94.90


class TestTheMeasuredEndpoints:
    def test_pedal_at_rest_is_zero_not_eighteen_percent(self):
        """The whole reason this exists: a corner taken with the foot
        completely off the pedal must not report 18.8% throttle."""
        assert normalize_pedal_pct(REST, REST, FULL) == pytest.approx(0.0)

    def test_pedal_at_the_stop_is_one_hundred_not_ninety_five(self):
        assert normalize_pedal_pct(FULL, REST, FULL) == pytest.approx(100.0)

    def test_midpoint_maps_to_fifty(self):
        mid = (REST + FULL) / 2
        assert normalize_pedal_pct(mid, REST, FULL) == pytest.approx(50.0)

    @pytest.mark.parametrize("raw,expected", [
        (56.86, 50.0),   # halfway between the endpoints
        (37.84, 25.0),
        (75.88, 75.0),
    ])
    def test_known_points(self, raw, expected):
        assert normalize_pedal_pct(raw, REST, FULL) == pytest.approx(
            expected, abs=0.1)


class TestMissingData:
    """None means 'not known'. Returning the raw value instead would put
    two different scales in one field, which is the failure this whole
    change exists to prevent."""

    def test_no_reading_gives_no_answer(self):
        assert normalize_pedal_pct(None, REST, FULL) is None

    @pytest.mark.parametrize("rest,full", [
        (None, FULL), (REST, None), (None, None),
    ])
    def test_uncalibrated_channel_gives_no_answer(self, rest, full):
        """A session on `throttle_pos`, which nobody has measured. It is
        better to show nothing than to rescale it with another
        channel's constants."""
        assert normalize_pedal_pct(50.0, rest, full) is None


class TestClamping:
    def test_slightly_below_rest_clamps_to_zero(self):
        """Sensor noise and mechanical slop, not bad calibration."""
        assert normalize_pedal_pct(REST - 0.4, REST, FULL) == 0.0

    def test_slightly_above_full_clamps_to_one_hundred(self):
        assert normalize_pedal_pct(FULL + 0.4, REST, FULL) == 100.0


class TestUnusableCalibration:
    """The database has a CHECK constraint for this, so reaching it means
    the constants arrived from somewhere else. Dividing by zero or
    mirroring the scale silently would be worse than raising."""

    def test_equal_endpoints_raise(self):
        with pytest.raises(ValueError, match="must exceed"):
            normalize_pedal_pct(50.0, 50.0, 50.0)

    def test_inverted_endpoints_raise(self):
        with pytest.raises(ValueError, match="must exceed"):
            normalize_pedal_pct(50.0, FULL, REST)


class TestCalibrationIsKeyedOnCarAndChannel:
    """Throttle plate and true pedal position are different signals. A
    calibration for one must never be applied to the other."""

    class FakeCursor:
        def __init__(self, rows):
            self._rows = rows

        def execute(self, sql, *params):
            return self

        def fetchall(self):
            return self._rows

    def test_map_is_keyed_by_both(self):
        cur = self.FakeCursor([
            (2, "accelerator_pos", REST, FULL),
            (2, "throttle_pos", 12.00, 88.00),
            (3, "accelerator_pos", 20.00, 96.00),
        ])

        m = calibration_map(cur)

        assert m[(2, "accelerator_pos")] == (REST, FULL)
        assert m[(2, "throttle_pos")] == (12.0, 88.0)
        assert m[(3, "accelerator_pos")] == (20.0, 96.0)

    def test_a_channel_without_a_row_is_absent(self):
        cur = self.FakeCursor([(2, "accelerator_pos", REST, FULL)])

        m = calibration_map(cur)

        assert (2, "throttle_pos") not in m
        assert m.get((2, "throttle_pos"), (None, None)) == (None, None)

    def test_the_wrong_channel_would_give_a_different_answer(self):
        """Pins that the key actually matters - if these agreed, keying
        on the channel would be pointless and the test would not fail
        when someone dropped it."""
        by_pedal = normalize_pedal_pct(50.0, REST, FULL)
        by_plate = normalize_pedal_pct(50.0, 12.00, 88.00)

        assert by_pedal != pytest.approx(by_plate, abs=1.0)
