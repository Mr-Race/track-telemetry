"""The pedal channel must be recorded alongside the value it produced.

`corner_metrics.throttle_pos_apex_pct` stores a raw percentage, but the
channel behind it changed on 2026-08-10 (throttle plate -> true pedal
position). The two have different rest and full points, so a stored
value cannot be normalised without knowing its source. The parser has
always computed this and, until now, thrown it away.
"""

import pytest

from ingest import racechrono_parser as rp


class FakeCursor:
    def __init__(self):
        self.calls = []

    def execute(self, sql, *params):
        self.calls.append((sql, params))
        return self

    def fetchone(self):
        return (101,)


class FakeConnection:
    def __init__(self):
        self.cur = FakeCursor()
        self.committed = False

    def cursor(self):
        return self.cur

    def commit(self):
        self.committed = True


@pytest.fixture
def stub_session_context(monkeypatch):
    """load()/refresh() reach out for weather and the track timezone;
    neither is what these tests are about."""
    monkeypatch.setattr(rp, "fetch_session_weather", lambda *a, **k: {
        "weather": None, "air_temp_f": None, "humidity_pct": None,
        "wind_mph": None, "precip_in": None, "weather_observed_at": None})
    monkeypatch.setattr(rp, "track_timezone", lambda *a, **k: "America/New_York")
    monkeypatch.setattr(rp, "_insert_children", lambda *a, **k: None)


SAMPLES = [{"ts": 1786446720.0, "lap": 1, "elapsed": 0.0,
            "lat": 39.36, "lon": -75.05, "mph": 60.0,
            "rpm": None, "throttle_pos": None}]
META = {"Created": "10/08/2026,11:12", "Track name": "NJMP Thunderbolt"}


def _insert_params(cnx):
    sql, params = cnx.cur.calls[0]
    assert "INSERT INTO dbo.sessions" in sql
    return sql, params


class TestLoadRecordsTheChannel:
    @pytest.mark.parametrize("channel", ["accelerator_pos", "throttle_pos"])
    def test_channel_is_written_with_the_session(
            self, stub_session_context, channel):
        cnx = FakeConnection()

        rp.load(cnx, 7, 1, "s.csv", META, SAMPLES, [], [],
                pedal_channel=channel)

        sql, params = _insert_params(cnx)
        assert "pedal_channel" in sql
        assert channel in params

    def test_a_session_with_no_obd_records_none(self, stub_session_context):
        """No dongle is a real state, not a missing value to be guessed."""
        cnx = FakeConnection()

        rp.load(cnx, 7, 1, "s.csv", META, SAMPLES, [], [],
                pedal_channel=None)

        sql, params = _insert_params(cnx)
        assert "pedal_channel" in sql
        assert params[-1] is None


class TestRefreshOverwritesTheChannel:
    def test_refresh_sets_rather_than_coalesces(self, stub_session_context):
        """car_id and the hash are COALESCEd because they can be set from
        elsewhere. This is derived only from the file being re-parsed, so
        the file wins - including when it says None."""
        cnx = FakeConnection()

        rp.refresh(cnx, 101, 7, META, SAMPLES, [], [],
                   pedal_channel="accelerator_pos")

        updates = [c for c in cnx.cur.calls
                   if "UPDATE dbo.sessions" in c[0]]
        assert updates, "no session UPDATE issued"
        sql, params = updates[0]
        assert "pedal_channel = ?" in sql
        assert "COALESCE(?, pedal_channel)" not in sql
        assert "accelerator_pos" in params


class TestTheValueComesFromTheParser:
    def test_diagnostics_channel_matches_what_gets_stored(self, make_csv):
        """The stored channel must be the one actually read, not a guess
        from the filename or the date."""
        path = make_csv(obd_channels=("rpm", "accelerator_pos"))

        _meta, _samples, diag = rp.parse_csv(path)

        assert diag["pedal_channel"] == "accelerator_pos"
