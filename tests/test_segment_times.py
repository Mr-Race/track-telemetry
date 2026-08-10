"""Tests for per-lap corner-to-corner segment times.

Segment times drive the optimal lap, which drives "event optimal" and
"left on table" on the event page. The function is deliberately
all-or-nothing per lap: a lap with any unresolved or out-of-order gate
is dropped entirely rather than contributing a partial chain, because a
half-built chain would quietly corrupt the optimal lap.
"""

import pytest

from ingest.racechrono_parser import compute_segment_times

from conftest import geo_corner, geo_sample


def two_corner_lap(lap=1, base=0.0, hit_second=True):
    """A lap passing corner A then corner B, with a gap between them."""
    far_lat = 39.37000  # ~1 km north - outside A's zone
    pts = [
        geo_sample(200, 100.0, lap=lap, elapsed=base + 0.0),
        geo_sample(5, 55.0, lap=lap, elapsed=base + 1.0),      # gate A
        geo_sample(200, 90.0, lap=lap, elapsed=base + 2.0),
    ]
    second_offset = 5 if hit_second else 400
    pts.append(geo_sample(second_offset, 60.0, lap=lap, elapsed=base + 3.0,
                          apex_lat=far_lat))
    pts.append(geo_sample(400, 95.0, lap=lap, elapsed=base + 4.0,
                          apex_lat=far_lat))
    return pts, [
        geo_corner("1", corner_id=101),
        geo_corner("2", corner_id=102, apex_lat=far_lat),
    ]


class TestSegmentChain:
    def test_a_clean_lap_produces_one_more_segment_than_corners(self):
        """Segments are start->A, A->B, B->lap end."""
        pts, corners = two_corner_lap()
        segs = compute_segment_times(pts, corners)

        assert [s["segment_order"] for s in segs] == [1, 2, 3]
        assert [s["to_corner_id"] for s in segs] == [101, 102, None]

    def test_segment_times_are_positive_and_sum_to_the_lap(self):
        pts, corners = two_corner_lap()
        segs = compute_segment_times(pts, corners)

        assert all(s["segment_time_ms"] > 0 for s in segs)
        # Lap runs 0.0 -> 4.0s here, so the chain must span 4000 ms.
        assert sum(s["segment_time_ms"] for s in segs) == pytest.approx(
            4000, abs=2)

    def test_no_corners_means_no_segments(self):
        pts, _ = two_corner_lap()
        assert compute_segment_times(pts, []) == []

    def test_corners_without_an_apex_are_ignored(self):
        pts, corners = two_corner_lap()
        corners[1]["apex_lat"] = None
        segs = compute_segment_times(pts, corners)

        # Only corner 1 remains a gate, so: start->1, 1->end.
        assert [s["to_corner_id"] for s in segs] == [101, None]


class TestLapRejection:
    def test_a_lap_missing_a_gate_is_dropped_entirely(self):
        """Partial chains are worse than none - they would feed the
        optimal lap a segment that never happened."""
        pts, corners = two_corner_lap(hit_second=False)

        assert compute_segment_times(pts, corners) == []

    def test_one_bad_lap_does_not_drop_the_others(self):
        good, corners = two_corner_lap(lap=1, base=0.0)
        bad, _ = two_corner_lap(lap=2, base=100.0, hit_second=False)
        segs = compute_segment_times(good + bad, corners)

        assert {s["lap_number"] for s in segs} == {1}

    def test_a_non_chronological_gate_drops_the_lap(self):
        """Bad GPS or a bad interpolation can put gate B before gate A;
        the resulting negative segment must not reach the DB."""
        far_lat = 39.37000
        pts = [
            geo_sample(200, 100.0, elapsed=0.0),
            geo_sample(5, 60.0, elapsed=5.0, apex_lat=far_lat),   # B early
            geo_sample(5, 55.0, elapsed=6.0),                     # A late
            geo_sample(400, 95.0, elapsed=7.0, apex_lat=far_lat),
        ]
        corners = [geo_corner("1", corner_id=101),
                   geo_corner("2", corner_id=102, apex_lat=far_lat)]
        segs = compute_segment_times(pts, corners)

        assert all(s["segment_time_ms"] > 0 for s in segs)


class TestSampleOrdering:
    def test_shuffled_input_produces_the_same_chain(self):
        """compute_segment_times sorts each lap by elapsed; this pins
        that behaviour so it can't regress the way #19 did next door."""
        pts, corners = two_corner_lap()
        shuffled = list(reversed(pts))

        assert compute_segment_times(pts, corners) == \
            compute_segment_times(shuffled, corners)
