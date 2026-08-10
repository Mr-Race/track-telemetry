"""Tests for the track-local time helpers.

Both exist because of real bugs. `to_track_local` fixes sessions having
been stored as raw UTC in a naive column, which displayed every session
4-5 hours late. `event_phase` decides the events list's in progress /
upcoming / past split, which a UTC comparison flips a day early for US
East tracks.
"""

from datetime import date, datetime, timezone

import pytest

from ingest.queries import event_phase
from ingest.racechrono_parser import DEFAULT_TRACK_TZ, to_track_local


class TestToTrackLocal:
    def test_converts_a_summer_instant_at_edt(self):
        """21:00 UTC in July is 17:00 EDT - the exact case that made a
        5pm session display as 9pm."""
        utc = datetime(2026, 7, 22, 21, 0, 34, tzinfo=timezone.utc)

        assert to_track_local(utc, "America/New_York") == \
            datetime(2026, 7, 22, 17, 0, 34)

    def test_converts_a_winter_instant_at_est(self):
        """The offset is not a constant - January is UTC-5, so a fixed
        -4 would be an hour out for half the year."""
        utc = datetime(2026, 1, 15, 21, 0, 34, tzinfo=timezone.utc)

        assert to_track_local(utc, "America/New_York") == \
            datetime(2026, 1, 15, 16, 0, 34)

    def test_the_result_is_naive(self):
        """sessions.start_time is DATETIME2 with no offset, so an aware
        datetime is what created the original bug."""
        utc = datetime(2026, 7, 22, 21, 0, tzinfo=timezone.utc)

        assert to_track_local(utc, "America/New_York").tzinfo is None

    def test_a_zone_where_the_date_also_changes(self):
        """Late-evening UTC is the previous afternoon on the US East
        coast - the conversion must move the date, not just the clock."""
        utc = datetime(2026, 7, 23, 1, 30, tzinfo=timezone.utc)

        assert to_track_local(utc, "America/New_York") == \
            datetime(2026, 7, 22, 21, 30)


class TestEventPhase:
    """`today` is evaluated inside the function against the track's zone,
    so these use dates far enough from now to be unambiguous."""

    def test_a_past_event(self):
        assert event_phase(date(2020, 5, 16), date(2020, 5, 17),
                           "America/New_York") == "past"

    def test_an_upcoming_event(self):
        assert event_phase(date(2099, 5, 16), None,
                           "America/New_York") == "upcoming"

    def test_a_single_day_event_uses_start_date_for_both_bounds(self):
        """end_date is null for single-day events."""
        assert event_phase(date(2020, 5, 16), None,
                           "America/New_York") == "past"

    def test_a_null_timezone_falls_back_rather_than_crashing(self):
        """A newly added track can sit with no zone until it is curated;
        the events list must not 500 because of it."""
        assert event_phase(date(2020, 5, 16), None, None) == "past"
        assert DEFAULT_TRACK_TZ == "America/New_York"

    def test_a_multi_day_event_spanning_today_is_in_progress(self):
        from zoneinfo import ZoneInfo
        today = datetime.now(ZoneInfo("America/New_York")).date()
        start = today.replace(day=1) if today.day > 1 else today

        assert event_phase(start, today, "America/New_York") == "in_progress"

    def test_an_event_that_is_exactly_today_is_in_progress(self):
        """Inclusive on both bounds - a one-day event is in progress on
        the day it runs, not already past."""
        from zoneinfo import ZoneInfo
        today = datetime.now(ZoneInfo("America/New_York")).date()

        assert event_phase(today, today, "America/New_York") == "in_progress"

    def test_the_zone_decides_the_boundary(self):
        """The reason the zone is threaded through at all: at 02:00 UTC
        it is still the previous day in New York, so an event ending
        'yesterday' UTC is still in progress locally."""
        from zoneinfo import ZoneInfo
        ny_today = datetime.now(ZoneInfo("America/New_York")).date()
        utc_today = datetime.now(timezone.utc).date()

        # Whenever the two disagree, the function must follow the track.
        phase = event_phase(ny_today, ny_today, "America/New_York")
        assert phase == "in_progress"
        if ny_today != utc_today:
            assert event_phase(utc_today, utc_today,
                               "America/New_York") != "in_progress"
