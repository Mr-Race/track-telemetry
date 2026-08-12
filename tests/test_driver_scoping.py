"""Guards that "personal best" stays scoped to one driver.

`queries.py` has no integration coverage (it needs a database), so
these assert the properties that can be checked without one: that the
driver filter is present in the SQL, and that the entry points take a
driver.

That is worth pinning because the failure is silent and slow to notice
- an instructor-driven session carried the default driver_id, nothing
filtered on it, and NJMP Lightning's personal best read 1:21.837 for
weeks instead of the owner's real 1:24.975. See GitHub issue #2.
"""

import inspect

import pytest

from ingest import queries


class TestDriverConstant:
    def test_me_is_driver_one(self):
        """dbo.drivers row 1 is 'Me'; driver 2 is the instructor."""
        assert queries.ME_DRIVER_ID == 1


class TestPersonalBestIsScoped:
    @pytest.mark.parametrize("fn_name", ["list_tracks", "get_track_benchmarks"])
    def test_entry_point_takes_a_driver(self, fn_name):
        """Parameterised rather than hardcoded, so multi-user (v2) can
        resolve the driver from the authenticated user without
        rewriting the query."""
        sig = inspect.signature(getattr(queries, fn_name))

        assert "driver_id" in sig.parameters
        assert sig.parameters["driver_id"].default == queries.ME_DRIVER_ID

    @pytest.mark.parametrize("fn_name", ["list_tracks", "get_track_benchmarks"])
    def test_the_personal_best_query_filters_on_driver(self, fn_name):
        """The filter itself, not just the parameter: passing a driver
        in and then ignoring it would look correct from the signature.
        """
        source = inspect.getsource(getattr(queries, fn_name))

        assert "s.driver_id = ?" in source, (
            f"{fn_name} no longer filters its personal-best query by "
            "driver - an instructor's lap in your car would count as "
            "your PB again (issue #2)"
        )


class TestEventSummaryNamesTheDriver:
    def test_session_rows_carry_a_driver(self):
        """Event hero stats are deliberately NOT driver-scoped - "event
        best" means the fastest lap anyone turned that day. That only
        stays honest if each row says who drove it, so the join and the
        field are load-bearing rather than decorative."""
        source = inspect.getsource(queries.event_summary)

        assert "dbo.drivers d ON d.driver_id = s.driver_id" in source
        assert '"driver": r[' in source
