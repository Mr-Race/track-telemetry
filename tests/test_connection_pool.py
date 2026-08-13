"""Tests for the shared SQL connection in ingest/cloud.py.

The free-tier database auto-pauses and takes 30-60s to resume. When
every request opened its own connection, each concurrent call paid that
separately - measured at 48.7s / 47.7s / 46.7s for three calls on one
page load. These pin the behaviour that fixes it. See issue #16.
"""

import threading
import time

import pytest

from ingest import cloud


class FakeCursor:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, *params):
        if self._conn.dead:
            raise RuntimeError("connection is closed")
        self._conn.queries.append(sql)
        return self

    def fetchone(self):
        return (1,)


class FakeConnection:
    def __init__(self):
        self.dead = False
        self.closed = False
        self.queries = []

    def cursor(self):
        return FakeCursor(self)

    def close(self):
        self.closed = True


@pytest.fixture(autouse=True)
def reset_pool(monkeypatch):
    """Each test starts with an empty pool and a stubbed connect."""
    monkeypatch.setattr(cloud, "_connection", None)
    monkeypatch.setattr(cloud, "_connection_key", None)
    opened = []

    def fake_open(server, database):
        conn = FakeConnection()
        opened.append((server, database, conn))
        return conn

    monkeypatch.setattr(cloud, "_open_connection", fake_open)
    return opened


class TestReuse:
    def test_the_second_call_reuses_the_first_connection(self, reset_pool):
        """The whole point: one resume, not one per request."""
        a = cloud.get_cloud_connection("srv", "db")
        b = cloud.get_cloud_connection("srv", "db")

        assert a is b
        assert len(reset_pool) == 1

    def test_a_different_database_opens_a_new_connection(self, reset_pool):
        cloud.get_cloud_connection("srv", "db")
        cloud.get_cloud_connection("srv", "other")

        assert len(reset_pool) == 2

    def test_switching_database_closes_the_previous_connection(self, reset_pool):
        first = cloud.get_cloud_connection("srv", "db")
        cloud.get_cloud_connection("srv", "other")

        assert first.closed is True


class TestStaleConnections:
    def test_a_dead_connection_is_replaced(self, reset_pool):
        """A pooled connection can be closed under us by an idle timeout
        or by the database pausing. That must be retried here, not
        surfaced to the user as an error on their next page load."""
        first = cloud.get_cloud_connection("srv", "db")
        first.dead = True

        second = cloud.get_cloud_connection("srv", "db")

        assert second is not first
        assert len(reset_pool) == 2

    def test_liveness_is_probed_not_assumed(self, reset_pool):
        conn = cloud.get_cloud_connection("srv", "db")
        cloud.get_cloud_connection("srv", "db")

        assert conn.queries == ["SELECT 1"]

    def test_close_failures_do_not_block_reconnecting(self, reset_pool):
        """A dead connection often throws on close too; that must not
        stop us handing back a working one."""
        first = cloud.get_cloud_connection("srv", "db")
        first.dead = True
        first.close = lambda: (_ for _ in ()).throw(RuntimeError("already gone"))

        assert cloud.get_cloud_connection("srv", "db") is not first


class TestConcurrency:
    def test_concurrent_callers_share_a_single_connect(self, monkeypatch):
        """Ten threads arriving during a slow resume must produce one
        connect, not ten - that is the difference between waiting ~47s
        once and ten calls each waiting ~47s."""
        monkeypatch.setattr(cloud, "_connection", None)
        monkeypatch.setattr(cloud, "_connection_key", None)
        opened = []

        def slow_open(server, database):
            time.sleep(0.05)          # stand-in for the resume
            conn = FakeConnection()
            opened.append(conn)
            return conn

        monkeypatch.setattr(cloud, "_open_connection", slow_open)

        results = []
        threads = [
            threading.Thread(
                target=lambda: results.append(
                    cloud.get_cloud_connection("srv", "db")))
            for _ in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(opened) == 1
        assert all(r is opened[0] for r in results)


class TestCredential:
    def test_the_credential_is_built_once(self, monkeypatch):
        """DefaultAzureCredential caches tokens for its own lifetime, so
        a new one per request re-fetches every time."""
        monkeypatch.setattr(cloud, "_credential", None)
        built = []

        class FakeCredential:
            def __init__(self):
                built.append(self)

        monkeypatch.setattr(cloud, "DefaultAzureCredential", FakeCredential)

        first = cloud._get_credential()
        second = cloud._get_credential()

        assert first is second
        assert len(built) == 1


class TestAutoPauseResume:
    """The first upload of a track day is the one that pays for the
    resume, and it happens on a phone in a paddock. A connect that times
    out mid-resume must not end the request."""

    def test_retries_once_past_a_failed_resume(self, monkeypatch):
        monkeypatch.setattr(cloud, "_connection", None)
        monkeypatch.setattr(cloud, "_connection_key", None)
        attempts = []

        def flaky_open(server, database):
            attempts.append((server, database))
            if len(attempts) == 1:
                raise TimeoutError("login timed out")
            return FakeConnection()

        monkeypatch.setattr(cloud, "_open_connection", flaky_open)

        cnx = cloud.get_cloud_connection("srv", "db")

        assert cnx is not None
        assert len(attempts) == 2

    def test_gives_up_after_the_configured_attempts(self, monkeypatch):
        """It retries, it doesn't loop - a genuinely unreachable database
        should surface rather than hold the request open."""
        monkeypatch.setattr(cloud, "_connection", None)
        monkeypatch.setattr(cloud, "_connection_key", None)
        attempts = []

        def always_fails(server, database):
            attempts.append(1)
            raise TimeoutError("login timed out")

        monkeypatch.setattr(cloud, "_open_connection", always_fails)

        with pytest.raises(TimeoutError):
            cloud.get_cloud_connection("srv", "db")

        assert len(attempts) == cloud.CONNECT_ATTEMPTS

    def test_connect_failures_do_not_log_the_exception_text(
            self, monkeypatch, caplog):
        """Connection errors can name the server and the principal. The
        type is enough to diagnose a resume timeout."""
        monkeypatch.setattr(cloud, "_connection", None)
        monkeypatch.setattr(cloud, "_connection_key", None)
        secret = "sql-host=free-sql-server; user=super-secret-principal"

        def always_fails(server, database):
            raise TimeoutError(secret)

        monkeypatch.setattr(cloud, "_open_connection", always_fails)

        with caplog.at_level("WARNING"):
            with pytest.raises(TimeoutError):
                cloud.get_cloud_connection("srv", "db")

        assert "TimeoutError" in caplog.text
        assert secret not in caplog.text
        assert "super-secret-principal" not in caplog.text

    def test_login_timeout_exceeds_the_documented_resume_window(self):
        """The old value was 60s - the same number as the top of the
        documented 30-60s resume range, so a slow resume failed."""
        assert cloud.LOGIN_TIMEOUT_S > 60
