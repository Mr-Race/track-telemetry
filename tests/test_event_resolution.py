"""Tests for event/session resolution during ingest.

These branches decide where an upload lands. Until now their only
exercise was a real upload, so the zero-match and multi-match paths
failed for the first time in production, mid-track-day.

They take a cursor rather than a connection, so a small stub is enough -
no database required.
"""

import pytest

from ingest.racechrono_parser import (
    next_session_number, parse_session_date, resolve_event_id,
    track_timezone,
)


class FakeCursor:
    """Records the SQL and params it was given and replays canned rows."""

    def __init__(self, rows):
        self._rows = list(rows)
        self.executed = []

    def execute(self, sql, *params):
        self.executed.append((sql, params))
        return self

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


class FakeConnection:
    def __init__(self, rows):
        self._cursor = FakeCursor(rows)

    def cursor(self):
        return self._cursor


META = {"Track name": "NJMP Lightning", "Created": "22/07/2026,17:00"}


class TestResolveEventId:
    def test_a_single_match_resolves(self):
        assert resolve_event_id(FakeConnection([(3,)]), META) == 3

    def test_no_match_explains_what_to_do(self):
        """The message is the whole value of this path - it is what the
        uploader sees on their phone at the track."""
        with pytest.raises(ValueError) as exc:
            resolve_event_id(FakeConnection([]), META)

        message = str(exc.value)
        assert "NJMP Lightning" in message
        assert "2026-07-22" in message
        assert "dashboard" in message

    def test_multiple_matches_name_the_candidates(self):
        with pytest.raises(ValueError) as exc:
            resolve_event_id(FakeConnection([(3,), (7,)]), META)

        message = str(exc.value)
        assert "[3, 7]" in message
        assert "event_id" in message

    def test_missing_track_name_is_rejected_before_querying(self):
        with pytest.raises(ValueError, match="Track name"):
            resolve_event_id(FakeConnection([]), {"Created": "22/07/2026,17:00"})

    def test_missing_created_date_is_rejected_before_querying(self):
        with pytest.raises(ValueError, match="Track name|Created"):
            resolve_event_id(FakeConnection([]), {"Track name": "NJMP Lightning"})

    def test_the_date_is_matched_against_the_event_range(self):
        """A multi-day weekend must match on either day, so the query
        has to bound start_date and end_date, not equal a single date."""
        cnx = FakeConnection([(3,)])
        resolve_event_id(cnx, META)
        sql, params = cnx.cursor().executed[0]

        assert "start_date <= ?" in sql
        assert "end_date" in sql
        assert params[0] == "NJMP Lightning"


class TestParseSessionDate:
    def test_parses_racechrono_s_day_first_format(self):
        """'22/07/2026' is 22 July, not 7 October - day-first, which is
        worth pinning because it is silently wrong the other way."""
        assert str(parse_session_date(META)) == "2026-07-22"

    def test_returns_none_when_the_metadata_has_no_created_field(self):
        assert parse_session_date({}) is None


class TestNextSessionNumber:
    def test_first_session_of_an_event_is_one(self):
        """The query returns ISNULL(MAX(...), 0) + 1, so an empty event
        yields 1."""
        assert next_session_number(FakeConnection([(1,)]), 5) == 1

    def test_continues_from_the_highest_existing_number(self):
        assert next_session_number(FakeConnection([(4,)]), 3) == 4


class TestTrackTimezone:
    def test_uses_the_track_s_zone(self):
        assert track_timezone(FakeConnection([("America/New_York",)]), 3) == \
            "America/New_York"

    def test_falls_back_when_the_track_has_no_zone_set(self):
        """Tracks are curated by hand; a newly added one can sit with a
        null zone, and that must not crash an ingest."""
        assert track_timezone(FakeConnection([(None,)]), 3) == "America/New_York"

    def test_falls_back_when_the_event_is_missing(self):
        assert track_timezone(FakeConnection([]), 999) == "America/New_York"
