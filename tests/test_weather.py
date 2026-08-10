"""Tests for session weather enrichment.

Weather is the project's reference example of failing soft: a flaky
external call must degrade to nulls, never block an ingest. That
property is asserted here rather than assumed.
"""

import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from ingest import weather
from ingest.racechrono_parser import fetch_session_weather


def archive_response(hours, **series):
    """An Open-Meteo hourly payload for the given ISO hour strings."""
    return {"hourly": {"time": list(hours), **series}}


def fake_urlopen(payload):
    class _Resp:
        def read(self):
            return json.dumps(payload).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    return lambda url, timeout=None: _Resp()


BASE = archive_response(
    ["2026-07-22T16:00", "2026-07-22T17:00", "2026-07-22T18:00"],
    temperature_2m=[80.0, 88.0, 91.0],
    relative_humidity_2m=[50, 45, 40],
    precipitation=[0.0, 0.0, 0.1],
    wind_speed_10m=[5.0, 7.0, 9.0],
    weather_code=[3, 0, 95],
)


class TestWmoCodeMapping:
    @pytest.mark.parametrize("code,expected", [
        (0, "Clear"),
        (3, "Overcast"),
        (61, "Light rain"),
        (95, "Thunderstorm"),
        (75, "Heavy snow"),
    ])
    def test_known_codes_map_to_labels(self, code, expected):
        assert weather.WMO_CODES[code] == expected

    def test_an_unknown_code_becomes_none_rather_than_raising(self):
        """Open-Meteo can add codes; an unrecognised one must not break
        an ingest, so the mapping is a .get()."""
        payload = archive_response(
            ["2026-07-22T17:00"], temperature_2m=[88.0],
            relative_humidity_2m=[45], precipitation=[0.0],
            wind_speed_10m=[7.0], weather_code=[9999])
        start = datetime(2026, 7, 22, 17, 0, tzinfo=timezone.utc)

        with patch("urllib.request.urlopen", fake_urlopen(payload)):
            result = weather.fetch_weather(39.36, -75.05, start)

        assert result["weather"] is None
        assert result["air_temp_f"] == 88.0


class TestHourSelection:
    def test_picks_the_hour_containing_the_session(self):
        start = datetime(2026, 7, 22, 17, 10, tzinfo=timezone.utc)

        with patch("urllib.request.urlopen", fake_urlopen(BASE)):
            result = weather.fetch_weather(39.36, -75.05, start)

        assert result["air_temp_f"] == 88.0
        assert result["weather"] == "Clear"

    def test_rounds_up_past_the_half_hour(self):
        """A session starting at 17:45 is better described by the 18:00
        observation than the 17:00 one."""
        start = datetime(2026, 7, 22, 17, 45, tzinfo=timezone.utc)

        with patch("urllib.request.urlopen", fake_urlopen(BASE)):
            result = weather.fetch_weather(39.36, -75.05, start)

        assert result["air_temp_f"] == 91.0
        assert result["weather"] == "Thunderstorm"

    def test_observed_at_is_naive_to_match_the_column(self):
        """weather_observed_at is a timezone-naive DATETIME2."""
        start = datetime(2026, 7, 22, 17, 10, tzinfo=timezone.utc)

        with patch("urllib.request.urlopen", fake_urlopen(BASE)):
            result = weather.fetch_weather(39.36, -75.05, start)

        assert result["weather_observed_at"].tzinfo is None


class TestFailingSoft:
    """fetch_session_weather must return EMPTY rather than raise, for
    any failure - that is what keeps a flaky API from blocking ingest."""

    def test_empty_has_every_column_the_loader_writes(self):
        assert set(weather.EMPTY) == {
            "weather", "air_temp_f", "humidity_pct", "wind_mph",
            "precip_in", "weather_observed_at"}
        assert all(v is None for v in weather.EMPTY.values())

    def test_a_network_failure_degrades_to_empty(self):
        corners = [{"apex_lat": 39.36, "apex_lon": -75.05}]
        start = datetime(2026, 7, 22, 17, 0, tzinfo=timezone.utc)

        def boom(*a, **k):
            raise OSError("connection reset")

        with patch("ingest.racechrono_parser.fetch_corners",
                    return_value=corners), \
             patch("ingest.weather.fetch_weather", side_effect=boom):
            assert fetch_session_weather(None, 1, start) == weather.EMPTY

    def test_a_missing_hour_degrades_to_empty(self):
        """The archive can lag; .index() raises and must be swallowed."""
        corners = [{"apex_lat": 39.36, "apex_lon": -75.05}]
        start = datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc)

        with patch("ingest.racechrono_parser.fetch_corners",
                    return_value=corners), \
             patch("urllib.request.urlopen", fake_urlopen(BASE)):
            assert fetch_session_weather(None, 1, start) == weather.EMPTY

    def test_a_track_with_no_corner_coordinates_degrades_to_empty(self):
        """No apexes means no location to query - a new track before its
        corners are curated."""
        with patch("ingest.racechrono_parser.fetch_corners",
                    return_value=[{"apex_lat": None, "apex_lon": None}]):
            assert fetch_session_weather(
                None, 1, datetime(2026, 7, 22, tzinfo=timezone.utc)
            ) == weather.EMPTY
