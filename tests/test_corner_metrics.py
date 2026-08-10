"""Tests for per-corner min/entry/exit speeds.

These feed corner_metrics, the corner story on the event page, and
compare_laps - and until now nothing checked them.

Geometry helper: at NJMP's latitude one degree of latitude is ~111,320 m,
so offsets are expressed in metres and converted, which keeps the tests
readable against a 25 m default zone radius.
"""

import pytest

from ingest.racechrono_parser import compute_corner_metrics

from conftest import geo_corner as corner, geo_sample as sample


class TestSpeedExtraction:
    def test_min_entry_and_exit_speeds(self):
        pts = [
            sample(20, 80.0, elapsed=0.0),   # entering the zone
            sample(5, 55.0, elapsed=1.0),    # apex - slowest
            sample(20, 70.0, elapsed=2.0),   # leaving
        ]
        [m] = compute_corner_metrics(pts, [corner()])

        assert m["min_speed_mph"] == pytest.approx(55.0)
        assert m["entry_speed_mph"] == pytest.approx(80.0)
        assert m["exit_speed_mph"] == pytest.approx(70.0)
        assert m["corner_code"] == "1"
        assert m["lap_number"] == 1

    def test_samples_outside_the_zone_are_ignored(self):
        pts = [
            sample(500, 120.0, elapsed=0.0),  # well outside
            sample(10, 60.0, elapsed=1.0),
            sample(500, 118.0, elapsed=2.0),
        ]
        [m] = compute_corner_metrics(pts, [corner()])

        assert m["entry_speed_mph"] == pytest.approx(60.0)
        assert m["exit_speed_mph"] == pytest.approx(60.0)

    def test_a_corner_never_entered_produces_no_row(self):
        pts = [sample(500, 120.0), sample(600, 118.0)]

        assert compute_corner_metrics(pts, [corner()]) == []

    def test_a_corner_without_an_apex_is_skipped(self):
        """Corners are curated by hand; some have no coordinates yet."""
        pts = [sample(5, 55.0)]

        assert compute_corner_metrics(pts, [corner(apex_lat=None)]) == []

    def test_obd_channels_are_optional(self):
        """A GPS-only session must still produce corner metrics."""
        pts = [sample(20, 80.0, elapsed=0.0), sample(5, 55.0, elapsed=1.0)]
        [m] = compute_corner_metrics(pts, [corner()])

        assert m["throttle_pos_apex_pct"] is None
        assert m["rpm_exit"] is None

    def test_throttle_is_taken_at_the_apex_and_rpm_at_the_exit(self):
        pts = [
            sample(20, 80.0, elapsed=0.0, throttle=10.0, rpm=4000),
            sample(5, 55.0, elapsed=1.0, throttle=2.0, rpm=3000),
            sample(20, 70.0, elapsed=2.0, throttle=90.0, rpm=6000),
        ]
        [m] = compute_corner_metrics(pts, [corner()])

        assert m["throttle_pos_apex_pct"] == pytest.approx(2.0)
        assert m["rpm_exit"] == pytest.approx(6000)


class TestSampleOrdering:
    def test_entry_and_exit_are_unaffected_by_input_order(self):
        """Regression for issue #19.

        compute_segment_times sorts each lap's samples by elapsed;
        compute_corner_metrics did not, yet takes entry from inside[0]
        and exit from inside[-1]. It worked only because RaceChrono
        happens to emit rows in order - an accidental guarantee, and
        when it fails the speeds silently swap rather than erroring.
        """
        ordered = [
            sample(20, 80.0, elapsed=0.0),
            sample(5, 55.0, elapsed=1.0),
            sample(20, 70.0, elapsed=2.0),
        ]
        shuffled = [ordered[2], ordered[0], ordered[1]]

        [a] = compute_corner_metrics(ordered, [corner()])
        [b] = compute_corner_metrics(shuffled, [corner()])

        assert a == b
        assert b["entry_speed_mph"] == pytest.approx(80.0)
        assert b["exit_speed_mph"] == pytest.approx(70.0)


class TestMultiplePassesThroughOneZone:
    def test_two_passes_do_not_merge_into_one_corner_record(self):
        """Regression for issue #23.

        A tight layout can pass within zone_radius_m of the same apex
        twice in a lap. Flattening every in-zone sample into one list
        took entry from the first pass and exit from the second, with an
        apex that is the minimum across both.
        """
        pts = [
            sample(20, 80.0, elapsed=0.0),    # first pass in
            sample(5, 60.0, elapsed=1.0),     # first pass apex
            sample(20, 75.0, elapsed=2.0),    # first pass out
            sample(400, 110.0, elapsed=10.0),  # away round the lap
            sample(20, 70.0, elapsed=20.0),   # second pass in
            sample(5, 40.0, elapsed=21.0),    # second pass apex - slower
            sample(20, 65.0, elapsed=22.0),   # second pass out
        ]
        [m] = compute_corner_metrics(pts, [corner()])

        # The slowest pass is the corner; its own entry/exit come with
        # it, rather than being taken from whichever pass came first.
        assert m["min_speed_mph"] == pytest.approx(40.0)
        assert m["entry_speed_mph"] == pytest.approx(70.0)
        assert m["exit_speed_mph"] == pytest.approx(65.0)


class TestMultipleLapsAndCorners:
    def test_one_row_per_lap_per_corner(self):
        pts = [
            sample(5, 55.0, lap=1, elapsed=1.0),
            sample(5, 53.0, lap=2, elapsed=100.0),
        ]
        rows = compute_corner_metrics(pts, [corner()])

        assert [r["lap_number"] for r in rows] == [1, 2]
        assert [r["min_speed_mph"] for r in rows] == [55.0, 53.0]

    def test_corner_id_is_carried_through_for_the_fk(self):
        [m] = compute_corner_metrics([sample(5, 55.0)],
                                      [corner(corner_id=42)])
        assert m["corner_id"] == 42
