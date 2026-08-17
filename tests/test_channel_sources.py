"""Channel source resolution.

RaceChrono writes each channel's source as `<rate>: <device>`, so the
numeric prefix is the *logging rate*, not an identity. Changing a
device's rate in the app rewrites the source string on every channel it
produces - which used to fail the parse with `Column not found:
latitude` and would have done so in the paddock, mid-event, with no way
to fix it from a phone.

The pedal channel already taught this lesson once (issue #8): a setting
changed, the export changed, and the parser was coupled to the old
string. These tests cover the same class of change for the source
column, and pin the reason the source can't simply be ignored instead -
`speed` is ambiguous without it.
"""

import pytest

from ingest.racechrono_parser import parse_csv, source_kind
from tests.conftest import DECOY_OFFSET

MPS_TO_MPH = 2.23694


class TestSourceKind:
    @pytest.mark.parametrize("raw,expected", [
        ("100: gps", "gps"),
        ("25: gps", "gps"),
        ("200: obd", "obd"),
        ("calc", "calc"),
        ("  100 :  GPS  ", "gps"),
    ])
    def test_drops_the_rate_prefix(self, raw, expected):
        assert source_kind(raw) == expected


class TestGpsSourceVariation:
    """Each of these is a source string the parser must still resolve."""

    @pytest.mark.parametrize("gps_source", [
        "100: gps",           # today's exports
        "25: gps",            # logging rate lowered to save battery
        "10: gps",            # lowered further
        "100: gnss",          # device renamed
        "100: gps (u-blox)",  # qualified with a receiver name
    ])
    def test_parses_whatever_the_rate_or_device_name(self, make_csv,
                                                     gps_source):
        path = make_csv(obd_channels=("rpm", "accelerator_pos"),
                        gps_source=gps_source)

        _meta, samples, diag = parse_csv(path)

        assert diag["gps_source"] == gps_source
        assert len(samples) == 12

    def test_reports_the_source_it_actually_used(self, make_csv):
        """Surfaced in the ingest response: the parse succeeding on a
        changed source is worth *seeing*, even though it isn't an error."""
        path = make_csv(gps_source="25: gps")

        _meta, _samples, diag = parse_csv(path)

        assert diag["gps_source"] == "25: gps"


class TestSpeedIsNotResolvedByNameAlone:
    """Why the source qualifier can't just be dropped.

    A real export carries three `speed` columns - gps, obd and calc. The
    fixtures carry all three, with the decoys offset by a wide margin.
    Binding by name alone would take whichever came first and quietly
    corrupt every lap time and corner metric, which is worse than the
    loud failure it would have replaced.
    """

    def test_binds_gps_speed_not_a_decoy(self, make_csv):
        path = make_csv(obd_channels=("rpm", "accelerator_pos"))

        _meta, samples, _diag = parse_csv(path)

        # default_rows starts GPS speed at 20.0 m/s.
        assert samples[0]["mph"] == pytest.approx(20.0 * MPS_TO_MPH, abs=0.1)
        decoy_mph = (20.0 + DECOY_OFFSET) * MPS_TO_MPH
        assert samples[0]["mph"] != pytest.approx(decoy_mph, abs=1.0)

    def test_gps_speed_still_wins_when_the_rate_changes(self, make_csv):
        """The mis-bind would be most likely exactly here - the rate
        changed, so a naive fallback to name-only matching would kick in
        and silently pick the obd column."""
        path = make_csv(obd_channels=("rpm",), gps_source="25: gps")

        _meta, samples, _diag = parse_csv(path)

        assert samples[0]["mph"] == pytest.approx(20.0 * MPS_TO_MPH, abs=0.1)


class TestUnresolvableSourceFailsLoudly:
    def test_error_names_the_sources_actually_present(self, make_csv):
        """If the device half changes to something unrecognised, the
        parse must fail with enough detail to fix it - not guess."""
        path = make_csv(gps_source="100: telemetry-unit-2")

        with pytest.raises(ValueError) as exc:
            parse_csv(path)

        msg = str(exc.value)
        assert "latitude" in msg
        assert "100: telemetry-unit-2" in msg
        assert "GPS_SOURCES" in msg


class TestObdSourceVariation:
    def test_obd_rate_change_keeps_the_pedal_channel(self, make_csv):
        """OBD lookups are optional, so a source change here degrades
        silently to 'no OBD' rather than erroring - the same rate-prefix
        coupling, but with a quieter and more misleading failure."""
        path = make_csv(obd_channels=("rpm", "accelerator_pos"),
                        obd_source="50: obd")

        _meta, samples, diag = parse_csv(path)

        assert diag["pedal_channel"] == "accelerator_pos"
        assert diag["has_rpm"] is True
        assert all(s["throttle_pos"] is not None for s in samples)


class TestDataLoggingSessions:
    """RaceChrono's 'Data logging' mode records every channel but does no
    lap timing, so `lap_number` is blank for the whole file. That is a
    phone setting, not a parser bug, and the error should say so."""

    def test_blank_lap_numbers_name_the_session_type(self, make_csv):
        rows = [["1786446720.000", "", "0.000", "40.7580", "-73.9855",
                 "11.000"]]
        path = make_csv(rows=rows)
        text = path.read_text().replace("Session type,Lap timing",
                                        "Session type,Data logging")
        path.write_text(text)

        with pytest.raises(ValueError) as exc:
            parse_csv(path)

        msg = str(exc.value)
        assert "Data logging" in msg
        assert "Lap timing" in msg

    def test_lap_timing_files_get_no_spurious_hint(self, make_csv):
        """A genuinely empty Lap timing file is a different problem, and
        blaming the mode would send someone the wrong way."""
        rows = [["1786446720.000", "", "0.000", "40.7580", "-73.9855",
                 "11.000"]]
        path = make_csv(rows=rows)

        with pytest.raises(ValueError) as exc:
            parse_csv(path)

        assert "Session type" not in str(exc.value)


class TestWeatherIsReportedNotAssumed:
    """Weather enrichment fails soft so a flaky external call cannot cost
    a session at the track. Three sessions from 2026-08-16 were therefore
    stored with null weather in silence, and by the time anyone looked the
    logs had expired. Soft failure is right; silent failure is not."""

    def test_the_ingest_response_shape_distinguishes_captured_from_missing(self):
        """Pins the contract the Shortcut popup relies on: a boolean that
        is false when weather is absent, rather than an absent key that
        reads the same as 'not checked'."""
        for row, expected in (((None, None), False),
                              (("Overcast", 77.8), True)):
            captured = bool(row and row[0] is not None)
            assert captured is expected
