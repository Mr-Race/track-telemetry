"""Cloud-specific plumbing for the ingest Function: SQL connection via
pytds (pure Python, no ODBC driver needed) and raw CSV archival to Blob.
Kept separate from racechrono_parser.py, which stays stdlib-only so the
CLI dry-run path works without any cloud SDKs installed.

DefaultAzureCredential resolves to the Function App's managed identity
when running in Azure, and to the local `az login` session during
`func start` testing - no branching needed between environments.
"""

import certifi
import pytds
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from ingest import _pytds_tls_compat  # noqa: F401 - patches pytds.tls.validate_host on import

SQL_SCOPE = "https://database.windows.net/.default"

# The free-tier serverless DB auto-pauses after inactivity; the first
# connection after a pause can take 30-60s to resume, well past pytds's
# 15s default.
LOGIN_TIMEOUT_S = 60


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


def get_cloud_connection(server, database):
    cred = DefaultAzureCredential()

    def get_token():
        return cred.get_token(SQL_SCOPE).token

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


def upload_raw_blob(account_url, container, blob_name, data):
    cred = DefaultAzureCredential()
    client = BlobServiceClient(account_url=account_url, credential=cred)
    client.get_container_client(container).upload_blob(
        blob_name, data, overwrite=False)
