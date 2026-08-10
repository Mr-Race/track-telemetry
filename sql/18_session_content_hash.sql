/* Idempotency for the HTTP ingest path (GitHub issue #3).

   Re-POSTing the same CSV created a duplicate session - it happened
   once for real (session 14 duplicating session 6, deleted 2026-08-03).
   `find_existing_session()` already matched on source_file, but the
   iOS Shortcut only sends `filename` optionally: without it the ingest
   route invents `session_<epoch>.csv`, which is unique on every upload,
   so filename matching would not have caught that duplicate.

   Hashing the raw body instead makes the check content-based and
   independent of what the client calls the file. Nullable because
   sessions loaded before this migration have no hash; they stay
   matchable by source_file, which is how the CLI --backfill path
   already works.

   CHAR(64) is exactly a hex sha256; the filtered unique index enforces
   one session per (event, content) while allowing many NULLs.

   NOTE the GO separators: SQL Server does not reliably see a
   newly added column later in the same batch, which has bitten this
   project twice (sql/13, sql/17). */

ALTER TABLE dbo.sessions ADD source_sha256 CHAR(64) NULL;
GO

CREATE UNIQUE INDEX UQ_sessions_event_content
    ON dbo.sessions (event_id, source_sha256)
    WHERE source_sha256 IS NOT NULL;
GO
