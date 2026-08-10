# Database migrations

Numbered `.sql` files, applied in order, recorded in
`dbo.schema_migrations`.

## Running them

```bash
python sql/migrate.py              # status: applied / pending / drifted
python sql/migrate.py --apply      # run pending migrations, in order
```

Needs `local.settings.json` with `SQL_SERVER` / `SQL_DATABASE`, and an
identity that can reach the database — see the connection notes in
`docs/BACKLOG.md`. The free-tier database auto-pauses, so the first
connection after a quiet period times out; just run it again.

## Rules

**Never edit a migration that has been applied.** Its sha256 is
recorded, so an edit shows up as `DRIFT` on the next status run. Add a
new numbered file instead.

**Split batches with `GO` whenever a migration adds a column and then
uses it.** SQL Server does not reliably see a column added earlier in
the same batch, and the failure is `Invalid column name` at apply time.
This caught us twice by hand (`sql/13`, `sql/17`) before the separators
were written down. `tests/test_migrate.py` asserts that the migrations
which do this are multi-batch.

**Take the next free number.** `07` is duplicated historically by two
files added two days apart; both were long applied and their order does
not matter, but a new duplicate means the order between them is
arbitrary. `migrate.py` prints a warning when it sees one.

## Adopting this on a database that predates it

`--baseline` records every file as applied *without running it*, for a
database whose migrations were applied by hand. Verify first that each
migration's effect is actually present — baselining an unapplied
migration writes a false record into the very thing meant to prevent
that. That check was done on 2026-08-10: 23 object-existence assertions
across the 20 files, all passing, before baselining.

## Why this exists

Migrations used to be applied by hand with no record in the database of
what had run, so drift was detected by something breaking —
`sql/17_track_timezone.sql` sat unapplied for six days and was found by
accident while building an unrelated feature. GitHub issue #12,
engineering review finding #5.
