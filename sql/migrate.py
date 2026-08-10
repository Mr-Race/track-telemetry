#!/usr/bin/env python3
"""Apply and record the numbered migrations in sql/.

    python sql/migrate.py                 # status: applied / pending / drifted
    python sql/migrate.py --apply         # run pending migrations, in order
    python sql/migrate.py --baseline      # record existing files as applied
                                          #   WITHOUT running them

Why this exists (GitHub issue #12): the files were applied by hand and
nothing in the database recorded which had run, so drift was found only
when something broke. `sql/17` sat unapplied for six days.

Three things it does that a checklist would not:

  * **Order.** Files are applied in numeric order, so 02 never runs
    before 01 because a shell glob sorted them as strings.
  * **Batches.** Statements are split on `GO`. SQL Server does not
    reliably see a newly added column later in the *same* batch, which
    has bitten this project twice (sql/13, sql/17) - each time
    discovered at apply time and split by hand.
  * **Drift.** Each file's sha256 is recorded. Editing an already
    applied migration silently desynchronises repo and database; that
    now shows up as a mismatch instead of as a bug months later.

Deliberately not a framework. No down-migrations (this is a single
small database with an archive of raw source data - restore and replay
beats a reverse script that has never been tested), and no transaction
wrapping the whole run, because SQL Server DDL batches and `GO` do not
compose into one.
"""

import argparse
import hashlib
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQL_DIR = os.path.join(REPO_ROOT, "sql")

sys.path.insert(0, REPO_ROOT)

# Numbered migrations only: `migrate.py` and any scratch files in here
# are not migrations.
MIGRATION_RE = re.compile(r"^(\d+)_.*\.sql$")

# `GO` is a batch separator understood by the client, not a T-SQL
# statement, so it has to be handled here rather than sent to the server.
# Only a line that is exactly GO (with optional whitespace/comment) counts
# - `GO` inside a string or identifier must not split anything.
GO_RE = re.compile(r"^\s*GO\s*(--.*)?$", re.IGNORECASE)


def discover(sql_dir=SQL_DIR):
    """Migration filenames in numeric order.

    Sorted on the parsed integer prefix, not the string: a plain sort
    puts '10_' before '2_', which would apply them out of order. The
    filename is the tie-break so a duplicated number still produces one
    stable order rather than depending on directory listing order -
    `07` is duplicated historically (see duplicate_numbers).
    """
    found = []
    for name in os.listdir(sql_dir):
        m = MIGRATION_RE.match(name)
        if m:
            found.append((int(m.group(1)), name))
    return [name for _n, name in sorted(found)]


def duplicate_numbers(sql_dir=SQL_DIR):
    """Prefixes used by more than one migration.

    `07` is duplicated by two files added two days apart in July 2026.
    Both have long been applied and their relative order does not
    matter, so they are left alone rather than renamed - but a *new*
    duplicate means two people numbered independently, and the order
    between them would be arbitrary. The runner surfaces it.
    """
    seen = {}
    for name in discover(sql_dir):
        seen.setdefault(int(MIGRATION_RE.match(name).group(1)), []).append(name)
    return {n: names for n, names in seen.items() if len(names) > 1}


def split_batches(sql_text):
    """Split on GO lines, dropping empty batches."""
    batches, current = [], []
    for line in sql_text.splitlines():
        if GO_RE.match(line):
            batches.append("\n".join(current))
            current = []
        else:
            current.append(line)
    batches.append("\n".join(current))
    return [b for b in batches if b.strip()]


def checksum(text):
    """sha256 of the file's bytes, normalised for line endings so a
    checkout on another platform doesn't read as drift."""
    return hashlib.sha256(text.replace("\r\n", "\n").encode()).hexdigest()


def read_migration(name, sql_dir=SQL_DIR):
    with open(os.path.join(sql_dir, name), encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------- database

def _connect():
    from ingest.cloud import get_cloud_connection

    settings = os.path.join(REPO_ROOT, "local.settings.json")
    with open(settings) as fh:
        values = json.load(fh)["Values"]
    return get_cloud_connection(values["SQL_SERVER"], values["SQL_DATABASE"])


LEDGER_DDL = """
CREATE TABLE dbo.schema_migrations (
    filename    NVARCHAR(260)  NOT NULL
        CONSTRAINT PK_schema_migrations PRIMARY KEY,
    checksum    CHAR(64)       NOT NULL,
    applied_at  DATETIME2(0)   NOT NULL
        CONSTRAINT DF_schema_migrations_applied_at DEFAULT SYSUTCDATETIME(),
    applied_by  NVARCHAR(128)  NULL
        CONSTRAINT DF_schema_migrations_applied_by DEFAULT SUSER_SNAME()
)"""


def ensure_ledger(cnx):
    """Create the ledger if absent. Bootstrapping it here rather than
    requiring 19_schema_migrations.sql to have been run by hand keeps
    `migrate.py` usable on a fresh database."""
    cur = cnx.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'schema_migrations'""")
    if cur.fetchone()[0]:
        return False
    cur = cnx.cursor()
    cur.execute(LEDGER_DDL)
    cnx.commit()
    return True


def applied_migrations(cnx):
    cur = cnx.cursor()
    cur.execute("""
        SELECT filename, checksum, applied_at
        FROM dbo.schema_migrations""")
    return {r[0]: (r[1].strip(), r[2]) for r in cur.fetchall()}


def record(cnx, name, digest):
    cur = cnx.cursor()
    cur.execute("""
        INSERT INTO dbo.schema_migrations (filename, checksum)
        VALUES (?, ?)""", name, digest)
    cnx.commit()


def status(cnx):
    """(pending, drifted) - drifted are applied files whose contents
    have since changed."""
    done = applied_migrations(cnx)
    pending, drifted = [], []
    for name in discover():
        digest = checksum(read_migration(name))
        if name not in done:
            pending.append(name)
        elif done[name][0] != digest:
            drifted.append((name, done[name][0], digest))
    return pending, drifted


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true",
                    help="run pending migrations and record them")
    ap.add_argument("--baseline", action="store_true",
                    help="record every migration as applied WITHOUT running "
                         "it - for adopting the ledger on a database whose "
                         "migrations were already applied by hand")
    args = ap.parse_args()

    cnx = _connect()
    if ensure_ledger(cnx):
        print("created dbo.schema_migrations")

    done = applied_migrations(cnx)
    pending, drifted = status(cnx)

    print(f"\n{len(discover())} migrations on disk, {len(done)} recorded")
    for name in discover():
        mark = "applied " if name in done else "PENDING "
        print(f"   {mark} {name}")

    dupes = duplicate_numbers()
    if dupes:
        print("\nduplicate migration numbers (order between them is "
              "alphabetical, not intentional):")
        for number, names in sorted(dupes.items()):
            print(f"   {number:02d}: {', '.join(names)}")

    if drifted:
        print("\nDRIFT - these files changed after being applied:")
        for name, was, now in drifted:
            print(f"   {name}: recorded {was[:12]}... now {now[:12]}...")
        print("   Never edit an applied migration; add a new one.")

    if args.baseline:
        if not pending:
            print("\nnothing to baseline")
            return 0
        print(f"\nbaselining {len(pending)} migrations as already applied "
              "(NOT running them):")
        for name in pending:
            record(cnx, name, checksum(read_migration(name)))
            print(f"   recorded {name}")
        return 0

    if not pending:
        print("\nup to date")
        return 1 if drifted else 0

    if not args.apply:
        print(f"\n{len(pending)} pending. Re-run with --apply to run them.")
        return 0

    for name in pending:
        text = read_migration(name)
        batches = split_batches(text)
        print(f"\napplying {name} ({len(batches)} batch"
              f"{'' if len(batches) == 1 else 'es'})")
        for i, batch in enumerate(batches, 1):
            cur = cnx.cursor()
            cur.execute(batch)
            cnx.commit()
            print(f"   batch {i} ok")
        record(cnx, name, checksum(text))
        print(f"   recorded {name}")

    return 1 if drifted else 0


if __name__ == "__main__":
    sys.exit(main())
