"""Tests for the migration runner's pure logic.

The DB-touching parts need a database; the parts that decide *what runs
and in what order* do not, and they are where a silent mistake would be
worst - applying migrations out of order, or sending a GO to the server.
"""

import importlib.util
import os

import pytest

# sql/ has no __init__.py (it is a directory of SQL files, not a
# package), so load the module by path.
_SPEC = importlib.util.spec_from_file_location(
    "migrate",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "sql", "migrate.py"))
migrate = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(migrate)


class TestDiscovery:
    def test_orders_numerically_not_lexically(self, tmp_path):
        """A string sort puts '10_' before '2_', which would apply
        migrations out of order - the one failure mode that cannot be
        undone by re-running."""
        for name in ["02_b.sql", "10_j.sql", "01_a.sql", "09_i.sql"]:
            (tmp_path / name).write_text("SELECT 1")

        assert migrate.discover(tmp_path) == [
            "01_a.sql", "02_b.sql", "09_i.sql", "10_j.sql"]

    def test_ignores_files_that_are_not_numbered_migrations(self, tmp_path):
        (tmp_path / "01_real.sql").write_text("SELECT 1")
        (tmp_path / "migrate.py").write_text("# not a migration")
        (tmp_path / "notes.sql").write_text("SELECT 1")
        (tmp_path / "README.md").write_text("hi")

        assert migrate.discover(tmp_path) == ["01_real.sql"]

    def test_the_real_sql_directory_is_in_ascending_order(self):
        names = migrate.discover()
        prefixes = [int(n.split("_")[0]) for n in names]

        assert prefixes == sorted(prefixes)

    def test_the_only_duplicate_number_is_the_known_historical_one(self):
        """`07` is duplicated by two files added two days apart in July
        2026, both long applied, so their relative order is moot. This
        pins that as the *only* one - a new duplicate means two
        migrations were numbered independently and the order between
        them would be arbitrary.
        """
        assert set(migrate.duplicate_numbers()) == {7}


class TestBatchSplitting:
    def test_splits_on_a_go_line(self):
        batches = migrate.split_batches("ALTER TABLE t ADD c INT;\nGO\nUPDATE t SET c = 1;")

        assert len(batches) == 2
        assert "ALTER TABLE" in batches[0]
        assert "UPDATE" in batches[1]

    def test_go_is_case_insensitive_and_tolerates_whitespace(self):
        assert len(migrate.split_batches("SELECT 1\n  go  \nSELECT 2")) == 2

    def test_a_file_with_no_go_is_a_single_batch(self):
        assert len(migrate.split_batches("SELECT 1;\nSELECT 2;")) == 1

    def test_empty_batches_are_dropped(self):
        """Trailing GO, or two in a row, must not send an empty command."""
        assert migrate.split_batches("SELECT 1\nGO\nGO\n") == ["SELECT 1"]

    def test_go_inside_a_statement_is_not_a_separator(self):
        """Only a line that is *only* GO separates batches - a column
        named `go`, or GO inside a string, must not split the file."""
        sql = "SELECT 'GO' AS x, go_flag FROM t WHERE note = 'GO GO'"

        assert migrate.split_batches(sql) == [sql]

    @pytest.mark.parametrize("name", [
        "11_run_groups.sql",
        "13_consumables_car_link.sql",
        "17_track_timezone.sql",
        "18_session_content_hash.sql",
    ])
    def test_migrations_that_add_then_use_a_column_are_multi_batch(self, name):
        """Every migration that adds a column and then references it
        must be split, or it fails with "Invalid column name". Three of
        these were split by hand at apply time before the separators
        were written down; this stops the next one being discovered the
        same way."""
        batches = migrate.split_batches(migrate.read_migration(name))

        assert len(batches) >= 2, f"{name} should be multi-batch"


class TestChecksum:
    def test_is_stable_for_identical_content(self):
        assert migrate.checksum("SELECT 1") == migrate.checksum("SELECT 1")

    def test_changes_when_content_changes(self):
        assert migrate.checksum("SELECT 1") != migrate.checksum("SELECT 2")

    def test_line_endings_do_not_count_as_drift(self):
        """A checkout on Windows must not make every migration look
        edited."""
        assert migrate.checksum("a\r\nb") == migrate.checksum("a\nb")
