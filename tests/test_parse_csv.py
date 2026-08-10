"""Parser tests, starting with the OBD channel cases from issue #8.

The three cases that matter at a track day: the new `accelerator_pos`
channel, the historical `throttle_pos` channel, and no OBD at all
(dongle unpaired, Bluetooth dropped, or left at home).
"""

import pytest

from ingest.racechrono_parser import parse_csv


class TestObdChannelResolution:
    def test_reads_the_new_accelerator_pos_channel(self, make_csv):
        """The regression from issue #8: exports switched to PID 0x49 and
        the parser silently wrote NULL throttle for every corner."""
        path = make_csv(obd_channels=("rpm", "accelerator_pos"))

        _meta, samples, diag = parse_csv(path)

        assert diag["pedal_channel"] == "accelerator_pos"
        assert all(s["throttle_pos"] is not None for s in samples)

    def test_still_reads_historical_throttle_pos(self, make_csv):
        """Archived exports keep the old name; the backfill re-ingests
        them unchanged, so this path must keep working."""
        path = make_csv(obd_channels=("rpm", "throttle_pos"))

        _meta, samples, diag = parse_csv(path)

        assert diag["pedal_channel"] == "throttle_pos"
        assert all(s["throttle_pos"] is not None for s in samples)

    def test_prefers_accelerator_pos_when_both_are_present(self, make_csv):
        """True pedal position beats throttle plate - it isn't distorted
        by traction control or torque limiting."""
        rows = [[f"{1778954779.0 + i:.3f}", 1, f"{i:.3f}",
                 f"{39.3607 + i * 0.0001:.6f}", f"{-75.0559:.6f}", "20.0",
                 "3000", "11.0", "99.0"] for i in range(6)]
        # Column order puts throttle_pos first, so a parser that simply
        # took the first match would pick the wrong one.
        path = make_csv(obd_channels=("rpm", "throttle_pos", "accelerator_pos"),
                        rows=rows)

        _meta, samples, diag = parse_csv(path)

        assert diag["pedal_channel"] == "accelerator_pos"
        assert samples[0]["throttle_pos"] == pytest.approx(99.0)

    def test_session_with_no_obd_still_parses(self, make_csv):
        """A GPS-only session is valid: laps, corner metrics and segment
        times all derive from GPS. Must not raise or partially write."""
        path = make_csv(obd_channels=())

        _meta, samples, diag = parse_csv(path)

        assert diag["pedal_channel"] is None
        assert diag["has_rpm"] is False
        assert diag["has_obd"] is False
        assert len(samples) == 12
        assert all(s["throttle_pos"] is None for s in samples)
        assert all(s["rpm"] is None for s in samples)

    def test_rpm_present_without_a_pedal_channel(self, make_csv):
        """Channels are resolved independently - a partial OBD stream
        shouldn't cost us the channel that did arrive."""
        path = make_csv(obd_channels=("rpm",))

        _meta, samples, diag = parse_csv(path)

        assert diag["pedal_channel"] is None
        assert diag["has_rpm"] is True
        assert diag["has_obd"] is True
        assert all(s["rpm"] is not None for s in samples)


class TestSkippedRowDiagnostics:
    """Engineering review finding #8 (issue #15): rows were dropped
    silently, so a truncated upload looked like a short session."""

    def test_counts_malformed_rows(self, make_csv):
        rows = [[f"{1778954779.0 + i:.3f}", 1, f"{i:.3f}",
                 "39.3607", "-75.0559", "20.0"] for i in range(6)]
        rows.insert(3, ["1778954782.000", 1, "3.0"])  # truncated row

        path = make_csv(rows=rows)
        _meta, samples, diag = parse_csv(path)

        assert diag["rows_skipped"]["malformed"] == 1
        assert diag["rows_used"] == len(samples) == 6

    def test_counts_rows_before_the_first_lap_crossing(self, make_csv):
        """RaceChrono leaves lap_number blank until the first S/F
        crossing; those aren't corrupt, just not part of a lap."""
        rows = [["1778954779.000", "", "0.0", "39.3607", "-75.0559", "5.0"],
                ["1778954780.000", "", "1.0", "39.3607", "-75.0559", "9.0"]]
        rows += [[f"{1778954781.0 + i:.3f}", 1, f"{2.0 + i:.3f}",
                  "39.3607", "-75.0559", "20.0"] for i in range(4)]

        path = make_csv(rows=rows)
        _meta, _samples, diag = parse_csv(path)

        assert diag["rows_skipped"]["no_lap"] == 2
        assert diag["rows_used"] == 4

    def test_counts_rows_missing_gps(self, make_csv):
        rows = [[f"{1778954779.0 + i:.3f}", 1, f"{i:.3f}",
                 "39.3607", "-75.0559", "20.0"] for i in range(4)]
        rows.append(["1778954783.000", 1, "4.0", "", "", ""])  # GPS dropout

        path = make_csv(rows=rows)
        _meta, _samples, diag = parse_csv(path)

        assert diag["rows_skipped"]["missing_gps"] == 1
        assert diag["rows_used"] == 4


class TestParseFailures:
    def test_rejects_a_file_with_no_channel_header(self, tmp_path):
        path = tmp_path / "not_v3.csv"
        path.write_text("Format,2\nSession title,Nope\n")

        with pytest.raises(ValueError, match="No channel header row"):
            parse_csv(path)

    def test_rejects_a_file_with_no_lap_numbered_samples(self, make_csv):
        """Every row pre-dates the first crossing - nothing to load."""
        rows = [["1778954779.000", "", "0.0", "39.3607", "-75.0559", "5.0"]]

        path = make_csv(rows=rows)
        with pytest.raises(ValueError, match="No lap-numbered samples"):
            parse_csv(path)
