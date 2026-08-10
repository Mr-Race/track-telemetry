/* Migration ledger (GitHub issue #12, engineering review finding #5).

   Until now, which of the numbered scripts in sql/ had been applied was
   held in memory and in the Done log. Drift was detected by something
   breaking - sql/17 sat unapplied for six days and was found by
   accident while building an unrelated feature.

   `checksum` is the sha256 of the file's contents at the time it ran,
   which turns this from a checklist into drift detection: editing an
   already-applied migration is a silent way to make the repo and the
   database disagree, and the runner reports it as a mismatch.

   `applied_by` records SUSER_SNAME() because migrations here are run by
   a human against prod, not by a pipeline - knowing which identity ran
   one is worth a column.

   Apply and record migrations with `python sql/migrate.py --apply`.
   Never edit an applied file: add a new one. */

CREATE TABLE dbo.schema_migrations (
    filename    NVARCHAR(260)  NOT NULL
        CONSTRAINT PK_schema_migrations PRIMARY KEY,
    checksum    CHAR(64)       NOT NULL,
    applied_at  DATETIME2(0)   NOT NULL
        CONSTRAINT DF_schema_migrations_applied_at DEFAULT SYSUTCDATETIME(),
    applied_by  NVARCHAR(128)  NULL
        CONSTRAINT DF_schema_migrations_applied_by DEFAULT SUSER_SNAME()
);
GO
