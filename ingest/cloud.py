"""Cloud-specific plumbing for the ingest Function: SQL connection via
pytds (pure Python, no ODBC driver needed) and raw CSV archival to Blob.
Kept separate from racechrono_parser.py, which stays stdlib-only so the
CLI dry-run path works without any cloud SDKs installed.

DefaultAzureCredential resolves to the Function App's managed identity
when running in Azure, and to the local `az login` session during
`func start` testing - no branching needed between environments.
"""

import logging
import threading

import certifi
import pytds
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from ingest import _pytds_tls_compat  # noqa: F401 - patches pytds.tls.validate_host on import

SQL_SCOPE = "https://database.windows.net/.default"

# The free-tier serverless DB auto-pauses after inactivity; the first
# connection after a pause can take 30-60s to resume, well past pytds's
# 15s default.
#
# 60s was the same number as the top of that range, so a slow resume
# failed the connect outright. The upload that pays this cost is always
# the first of the day - at a track, on a phone, from someone who can't
# do anything about it - so the margin is deliberately generous, and one
# retry follows: a connect that times out has already *started* the
# resume, so the second attempt usually returns quickly.
LOGIN_TIMEOUT_S = 90
CONNECT_ATTEMPTS = 2


def qmark_to_pyformat(sql):
    """Convert ?-style placeholders to the %s form pytds expects.

    This walks the statement rather than doing a blind str.replace,
    because two things are not placeholders and must survive untouched:

      - a '?' inside a string literal, a bracketed identifier, or a
        comment
      - a literal '%', which pytds would otherwise read as the start of
        a format specifier once it interpolates - so every '%' in the
        statement is doubled

    Neither case exists in the current queries, which is exactly why the
    old blind replace worked. It relied on an unenforced invariant
    across ~800 lines of SQL, and the failure mode was a silently
    altered query rather than an error, so the invariant is enforced
    here instead of being documented and hoped for.

    Only called when parameters are actually supplied; a statement with
    no parameters is passed through untouched (pytds skips
    interpolation entirely in that case, so doubling '%' there would
    leave literal '%%' in the SQL).
    """
    out = []
    i, n = 0, len(sql)
    while i < n:
        ch = sql[i]
        if ch == "'":
            # String literal; '' is an escaped quote, not a terminator.
            j = i + 1
            while j < n:
                if sql[j] == "'":
                    if j + 1 < n and sql[j + 1] == "'":
                        j += 2
                        continue
                    break
                j += 1
            out.append(sql[i:j + 1].replace("%", "%%"))
            i = j + 1
        elif ch == "[":
            # Bracketed identifier, e.g. [my?column].
            j = sql.find("]", i)
            j = n - 1 if j == -1 else j
            out.append(sql[i:j + 1].replace("%", "%%"))
            i = j + 1
        elif sql.startswith("--", i):
            j = sql.find("\n", i)
            j = n if j == -1 else j
            out.append(sql[i:j].replace("%", "%%"))
            i = j
        elif sql.startswith("/*", i):
            j = sql.find("*/", i)
            j = n if j == -1 else j + 2
            out.append(sql[i:j].replace("%", "%%"))
            i = j
        elif ch == "?":
            out.append("%s")
            i += 1
        elif ch == "%":
            out.append("%%")
            i += 1
        else:
            out.append(ch)
            i += 1
    return "".join(out)


class _QmarkCursor:
    """Wraps a pytds cursor to accept the ?-style placeholders used by
    ingest/queries.py and racechrono_parser.py, which pytds does not
    understand - it takes %s (pyformat) instead.
    """

    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, sql, *params):
        self._cursor.execute(
            qmark_to_pyformat(sql) if params else sql, params or None)
        return self

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class _QmarkConnection:
    def __init__(self, cnx):
        self._cnx = cnx

    def cursor(self):
        return _QmarkCursor(self._cnx.cursor())

    def __getattr__(self, name):
        return getattr(self._cnx, name)


_credential = None
_credential_lock = threading.Lock()

# One connection PER THREAD, not per process.
#
# pytds connections are not thread-safe and allow a single active cursor:
# `connection.cursor()` cancels whatever cursor is already open on it. A
# single process-wide connection therefore breaks as soon as two requests
# overlap - which is every dashboard page load, since it fetches
# sessions, detail, summary and consumables in parallel. The symptom is
# not a clean error but a corrupted TDS stream:
#
#     InterfaceError: Invalid TDS marker: 4(4)
#     InterfaceError: Cursor is closed
#
# The liveness probe made it worse: `_is_alive()` runs `SELECT 1` on the
# shared connection while another thread may be mid-query, which is
# itself enough to desynchronise the stream.
#
# Thread-local keeps what issue #16 was actually for. That fix was about
# not paying the serverless resume *per request*; a handful of worker
# threads pay it once each and every request after is fast. What it must
# not do is share one wire between threads.
_local = threading.local()
_connection_lock = threading.Lock()


def _get_credential():
    """One credential for the process.

    DefaultAzureCredential caches tokens internally, but only for its own
    lifetime - building a new one per request threw that away and fetched
    a fresh token every time.
    """
    global _credential
    if _credential is None:
        with _credential_lock:
            if _credential is None:
                _credential = DefaultAzureCredential()
    return _credential


def _open_connection(server, database):
    def get_token():
        return _get_credential().get_token(SQL_SCOPE).token

    cnx = pytds.connect(
        server=server,
        database=database,
        access_token_callable=get_token,
        cafile=certifi.where(),  # pytds only enables TLS when a CA
                                  # bundle is given; Azure SQL requires it
        login_timeout=LOGIN_TIMEOUT_S,
        timeout=LOGIN_TIMEOUT_S,
    )
    return _QmarkConnection(cnx)


def _connect_with_resume(server, database):
    """Open a connection, retrying once past an auto-pause resume.

    The exception type is logged but never its text: connection errors
    can carry server and principal detail, and this runs in a request
    path (see the internal-exception finding fixed on 2026-08-05).
    """
    last_exc = None
    for attempt in range(1, CONNECT_ATTEMPTS + 1):
        try:
            return _open_connection(server, database)
        except Exception as exc:
            last_exc = exc
            logging.warning(
                "SQL connect attempt %d/%d failed (%s) - the database may "
                "be resuming from auto-pause",
                attempt, CONNECT_ATTEMPTS, type(exc).__name__)
    raise last_exc


def _is_alive(cnx):
    """Cheap liveness probe. A pooled connection can be closed under us
    by an idle timeout or by the database pausing, and the failure shows
    up as an error on the next real query - which would surface to a
    user rather than being retried here."""
    try:
        cur = cnx.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        return True
    except Exception:
        return False


def get_cloud_connection(server, database):
    """A connection for the calling thread, opened on first use.

    Previously every request built its own credential and its own
    connection. On the free-tier serverless database that was the
    dominant cost: it auto-pauses, the first connect after a pause takes
    30-60s to resume it, and because each concurrent call opened its own
    connection each one paid that separately. Measured 2026-08-11:
    48.7s / 47.7s / 46.7s for three calls on one page load, which is
    indistinguishable from the app being broken. Connections were also
    never closed.

    Holding the lock across the connect is deliberate rather than
    incidental: concurrent callers queue behind one resume instead of
    starting several. They wait roughly as long as before, once,
    and every request after that is fast.

    See GitHub issue #16.
    """
    key = (server, database)
    cnx = getattr(_local, "connection", None)

    # No lock around the probe or the reuse: this connection belongs to
    # this thread, so nothing else can be using it. Taking a global lock
    # here is what serialised - and corrupted - concurrent requests.
    if cnx is not None:
        if getattr(_local, "key", None) == key and _is_alive(cnx):
            return cnx
        # Either the target moved or the connection died. Close it either
        # way - dropping the reference without closing leaks the socket
        # until the process ends.
        try:
            cnx.close()
        except Exception:
            logging.debug("discarding an unusable connection", exc_info=True)
        _local.connection = None

    # Hold the lock only across the *connect*. Concurrent first-callers
    # would otherwise each trigger their own serverless resume; this way
    # they queue behind one and the rest return quickly.
    with _connection_lock:
        cnx = _connect_with_resume(server, database)
    _local.connection = cnx
    _local.key = key
    return cnx


def upload_raw_blob(account_url, container, blob_name, data):
    client = BlobServiceClient(account_url=account_url,
                                credential=_get_credential())
    client.get_container_client(container).upload_blob(
        blob_name, data, overwrite=False)
