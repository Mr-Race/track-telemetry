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


class _QmarkCursor:
    """Wraps a pytds cursor to accept the ?-style placeholders used by
    fetch_corners()/load() in racechrono_parser.py. pytds itself only
    accepts %s (pyformat) placeholders - none of the shared queries
    contain literal '?' outside of placeholder position, so a plain
    text substitution is safe here.
    """

    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, sql, *params):
        self._cursor.execute(sql.replace("?", "%s"), params or None)
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
