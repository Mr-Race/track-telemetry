"""Tests for lap timing and the median-based validity rule.

Lap validity is load-bearing: best lap, average, optimal lap,
progression and the whole event page derive from it. It had never been
tested.
"""

import pytest

from ingest.racechrono_parser import compute_laps


class TestLapTiming:
    def test_lap_time_comes_from_the_next_lap_s_first_sample(self, laps_from):
        laps = compute_laps(laps_from([90.0, 92.0, 91.0]))

        assert [l["lap_number"] for l in laps] == [1, 2, 3]
        assert [l["lap_time_ms"] for l in laps] == [90_000, 92_000, 91_000]

    def test_a_single_lap_session_is_valid(self, laps_from):
        """No other lap to compare against, so nothing can be an outlier."""
        laps = compute_laps(laps_from([95.0]))

        assert len(laps) == 1
        assert laps[0]["is_valid"] == 1

    def test_laps_are_ordered_by_number_not_file_order(self):
        """Samples are grouped by lap number, so shuffled input must not
        reorder the laps."""
        samples = [
            {"lap": 2, "elapsed": 90.0}, {"lap": 1, "elapsed": 0.0},
            {"lap": 2, "elapsed": 180.0}, {"lap": 1, "elapsed": 45.0},
        ]
        laps = compute_laps(samples)

        assert [l["lap_number"] for l in laps] == [1, 2]


class TestValidityRule:
    """A lap more than 12% off the session median is not a flying lap."""

    def test_a_slow_lap_is_invalid(self, laps_from):
        # 130 is >12% above a 100 median; 100/101/99 are not.
        laps = compute_laps(laps_from([100.0, 101.0, 130.0, 99.0, 100.0]))
        by_number = {l["lap_number"]: l for l in laps}

        assert by_number[3]["is_valid"] == 0
        assert all(by_number[n]["is_valid"] == 1 for n in (1, 2, 4, 5))

    def test_a_lap_just_inside_the_threshold_stays_valid(self, laps_from):
        # 111% of the median - under the 112% cut.
        laps = compute_laps(laps_from([100.0, 100.0, 111.0, 100.0, 100.0]))

        assert all(l["is_valid"] == 1 for l in laps)

    def test_the_median_is_a_true_median_for_an_even_lap_count(self, laps_from):
        """Regression for issue #22.

        With four laps the old implementation took `sorted(durs)[2]` -
        the upper of the two middle values - so the median came out as
        130 instead of 115, and the 130s were measured against a
        threshold of 145.6 rather than 128.8. They were called valid.
        A true median makes them the outliers they are.
        """
        laps = compute_laps(laps_from([100.0, 100.0, 130.0, 130.0]))
        by_number = {l["lap_number"]: l for l in laps}

        assert by_number[1]["is_valid"] == 1
        assert by_number[2]["is_valid"] == 1
        assert by_number[3]["is_valid"] == 0
        assert by_number[4]["is_valid"] == 0

    def test_odd_lap_counts_are_unaffected_by_that_fix(self, laps_from):
        """The odd case already picked the true middle value, so the fix
        must not move it."""
        laps = compute_laps(laps_from([100.0, 100.0, 130.0]))
        by_number = {l["lap_number"]: l for l in laps}

        assert by_number[1]["is_valid"] == 1
        assert by_number[3]["is_valid"] == 0


class TestOutAndInLapFlags:
    """RaceChrono only numbers laps after the first S/F crossing, so lap
    1 may already be flying - the flags are evidence-based, not
    positional."""

    def test_a_slow_first_lap_is_flagged_as_an_out_lap(self, laps_from):
        laps = compute_laps(laps_from([140.0, 100.0, 100.0, 99.0, 101.0]))

        assert laps[0]["is_out_lap"] == 1
        assert laps[0]["is_valid"] == 0

    def test_a_slow_last_lap_is_flagged_as_an_in_lap(self, laps_from):
        laps = compute_laps(laps_from([100.0, 100.0, 99.0, 101.0, 150.0]))

        assert laps[-1]["is_in_lap"] == 1
        assert laps[-1]["is_valid"] == 0

    def test_a_fast_first_lap_is_not_flagged(self, laps_from):
        """The whole point of the evidence-based rule: a lap 1 that is
        already at pace is a flying lap, not an out lap."""
        laps = compute_laps(laps_from([100.0, 100.0, 101.0, 99.0]))

        assert laps[0]["is_out_lap"] == 0
        assert laps[0]["is_valid"] == 1

    def test_a_slow_middle_lap_is_invalid_but_neither_out_nor_in(self, laps_from):
        laps = compute_laps(laps_from([100.0, 140.0, 100.0, 99.0, 101.0]))
        middle = laps[1]

        assert middle["is_valid"] == 0
        assert middle["is_out_lap"] == 0
        assert middle["is_in_lap"] == 0


class TestLapTimeFormatting:
    @pytest.mark.parametrize("ms,expected", [
        (84975, "1:24.975"),
        (109558, "1:49.558"),
        (60000, "1:00.000"),
        (59999, "0:59.999"),
        (3661000, "61:01.000"),
    ])
    def test_fmt_ms(self, ms, expected):
        from ingest.racechrono_parser import fmt_ms
        assert fmt_ms(ms) == expected
