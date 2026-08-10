"""Tests for the qmark -> pyformat conversion in ingest/cloud.py.

The conversion sits between every query in ingest/queries.py and the
database. It used to be a blind `sql.replace("?", "%s")`, safe only
because no query happened to contain a literal '?' or '%'. These tests
pin the cases that would previously have produced a silently altered
query.
"""

import pytest

from ingest.cloud import qmark_to_pyformat
from ingest import queries


class TestPlaceholderConversion:
    def test_converts_placeholders(self):
        assert qmark_to_pyformat(
            "SELECT * FROM t WHERE a = ? AND b = ?"
        ) == "SELECT * FROM t WHERE a = %s AND b = %s"

    def test_leaves_a_question_mark_inside_a_string_literal_alone(self):
        """The case the old blind replace would have corrupted."""
        assert qmark_to_pyformat(
            "SELECT * FROM t WHERE note = 'why?' AND id = ?"
        ) == "SELECT * FROM t WHERE note = 'why?' AND id = %s"

    def test_handles_escaped_quotes_inside_a_literal(self):
        """'' is an escaped quote, not the end of the literal - getting
        this wrong would flip the parser's idea of inside vs outside."""
        assert qmark_to_pyformat(
            "SELECT * FROM t WHERE s = 'it''s a ? really' AND id = ?"
        ) == "SELECT * FROM t WHERE s = 'it''s a ? really' AND id = %s"

    def test_leaves_a_question_mark_in_a_bracketed_identifier(self):
        assert qmark_to_pyformat(
            "SELECT [odd?name] FROM t WHERE id = ?"
        ) == "SELECT [odd?name] FROM t WHERE id = %s"

    def test_leaves_a_question_mark_in_a_line_comment(self):
        sql = "SELECT 1 -- really? yes\nWHERE id = ?"
        assert qmark_to_pyformat(sql) == "SELECT 1 -- really? yes\nWHERE id = %s"

    def test_leaves_a_question_mark_in_a_block_comment(self):
        sql = "SELECT 1 /* who knows? */ WHERE id = ?"
        assert qmark_to_pyformat(sql) == "SELECT 1 /* who knows? */ WHERE id = %s"


class TestPercentEscaping:
    """pytds interpolates with pyformat, so a bare '%' would be read as
    a format specifier the moment parameters are supplied."""

    def test_doubles_a_literal_percent_in_a_like_pattern(self):
        assert qmark_to_pyformat(
            "SELECT * FROM t WHERE name LIKE 'NJMP%' AND id = ?"
        ) == "SELECT * FROM t WHERE name LIKE 'NJMP%%' AND id = %s"

    def test_doubles_a_percent_outside_a_literal(self):
        assert qmark_to_pyformat("SELECT 10 % ? AS r") == "SELECT 10 %% %s AS r"

    def test_converted_sql_survives_pyformat_interpolation(self):
        """End to end: what pytds will actually do with the result."""
        converted = qmark_to_pyformat(
            "SELECT * FROM t WHERE name LIKE 'NJMP%' AND id = ?")
        assert converted % ("x",) == (
            "SELECT * FROM t WHERE name LIKE 'NJMP%' AND id = x")


class TestRealQueriesInvariant:
    """Engineering review finding #11: the old implementation was safe
    only under an unenforced invariant. It is now enforced by the
    conversion itself, so this guards the weaker property that the
    project's real SQL still round-trips as expected."""

    @pytest.mark.parametrize("sql", [
        "SELECT session_id FROM dbo.sessions WHERE event_id = ? AND source_file = ?",
        "SELECT ISNULL(MAX(session_number), 0) + 1 FROM dbo.sessions WHERE event_id = ?",
    ])
    def test_placeholder_count_is_preserved(self, sql):
        converted = qmark_to_pyformat(sql)
        assert converted.count("%s") == sql.count("?")
        assert "?" not in converted

    def test_module_imports_without_a_database(self):
        """queries.py must stay importable without a live connection -
        the tests and the MCP server both rely on that."""
        assert hasattr(queries, "event_phase")
