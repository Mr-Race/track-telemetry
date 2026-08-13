#!/usr/bin/env python3
"""Is the platform ready to be tagged 1.0?

The v1.0 gate in `docs/BACKLOG.md` says: core loop finished, nothing
known-broken in production, all endpoints secured, docs baseline exists,
both review gates passed. Most of that is already true and recorded. The
one claim that has never been demonstrated is that a real
`accelerator_pos` export survives the whole pipeline - every check
before 2026-08-13 used a file whose pedal column was relabelled.

This script answers that question against production, and re-checks the
mechanical preconditions that a release should never skip.

Run it as often as you like; it writes nothing.

    python scripts/release_gate.py            # human-readable table
    python scripts/release_gate.py --json     # for scripting
    echo $?                                   # 0 = ready, 1 = not

Every check prints *why* it failed, not just that it did. A gate that
says "not ready" without saying what to do is a gate people route
around.
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

REPO = "Mr-Race/track-telemetry"

# The channel whose real-world behaviour is the open question. A session
# on the old channel proves nothing about it.
TARGET_CHANNEL = "accelerator_pos"

# A session that produced almost no corner data parsed, but did not
# work. Thunderbolt Classic has 13 corners; asking for most of them on
# at least one lap distinguishes "ingested" from "ingested correctly".
MIN_CORNERS_COVERED = 8
MIN_LAPS = 3


class Check:
    def __init__(self, name, ok, detail, fix=None):
        self.name, self.ok, self.detail, self.fix = name, ok, detail, fix


SETTINGS = os.path.join(REPO_ROOT, "local.settings.json")


def _connect():
    """Open the production connection, or raise with an actionable reason.

    The three ways this fails look identical from a stack trace and need
    completely different responses, so they are separated here. An
    earlier version reported a missing config file as "the database may
    be resuming - retry in a minute", which is advice that can never
    work."""
    if not os.path.exists(SETTINGS):
        raise RuntimeError(
            "local.settings.json is missing. It is gitignored, so a fresh "
            "Codespace does not have it.|"
            "cp local.settings.json.example local.settings.json, then fill "
            "in SQL_SERVER and SQL_DATABASE.")
    from ingest.cloud import get_cloud_connection
    with open(SETTINGS) as fh:
        v = json.load(fh)["Values"]
    try:
        return get_cloud_connection(v["SQL_SERVER"], v["SQL_DATABASE"])
    except Exception as exc:
        name = type(exc).__name__
        if "Credential" in name or "auth" in str(exc).lower():
            raise RuntimeError(
                f"Azure authentication failed ({name}).|"
                "Run `az login` - DefaultAzureCredential has nothing to "
                "use in a fresh Codespace.") from exc
        raise RuntimeError(
            f"Could not reach the database ({name}).|"
            "The serverless database auto-pauses and takes 30-60s to "
            "resume; retry once. If it persists, check the SQL firewall "
            "- Codespaces are covered by the AllowAllWindowsAzureIps "
            "rule, other machines need their IP added.") from exc


def _git(*args):
    return subprocess.run(["git", "-C", REPO_ROOT, *args],
                          capture_output=True, text=True).stdout.strip()


# ----------------------------------------------------------- the checks

def check_real_session(cnx):
    """A real session recorded on the new pedal channel."""
    cur = cnx.cursor()
    cur.execute("""
        SELECT TOP 1 s.session_id, s.session_date, s.source_file
        FROM dbo.sessions s
        WHERE s.pedal_channel = ?
        ORDER BY s.session_date DESC, s.session_id DESC""", TARGET_CHANNEL)
    row = cur.fetchone()
    if row is None:
        return Check(
            f"A session on `{TARGET_CHANNEL}` exists", False,
            f"No session in the database has pedal_channel = "
            f"'{TARGET_CHANNEL}'.",
            "Upload a session recorded after the 2026-08-10 logger "
            "change. This is the check the 1.0 gate exists for.")
    return Check(f"A session on `{TARGET_CHANNEL}` exists", True,
                 f"session_id={row[0]}, {row[1]}, {row[2]}")


def check_session_quality(cnx):
    """That session actually produced usable data, not just a row."""
    cur = cnx.cursor()
    cur.execute("""
        SELECT TOP 1 s.session_id FROM dbo.sessions s
        WHERE s.pedal_channel = ?
        ORDER BY s.session_date DESC, s.session_id DESC""", TARGET_CHANNEL)
    row = cur.fetchone()
    if row is None:
        return Check("That session produced usable data", False,
                     "Skipped - no such session yet.", None)
    sid = row[0]

    cur.execute("SELECT COUNT(*) FROM dbo.laps WHERE session_id = ?", sid)
    laps = cur.fetchone()[0]
    cur.execute("""
        SELECT COUNT(DISTINCT cm.corner_id)
        FROM dbo.corner_metrics cm
        JOIN dbo.laps l ON l.lap_id = cm.lap_id
        WHERE l.session_id = ?""", sid)
    corners = cur.fetchone()[0]
    cur.execute("""
        SELECT COUNT(*) FROM dbo.corner_metrics cm
        JOIN dbo.laps l ON l.lap_id = cm.lap_id
        WHERE l.session_id = ? AND cm.throttle_pos_apex_pct IS NOT NULL""",
        sid)
    pedal_rows = cur.fetchone()[0]

    problems = []
    if laps < MIN_LAPS:
        problems.append(f"only {laps} laps (want >= {MIN_LAPS})")
    if corners < MIN_CORNERS_COVERED:
        problems.append(
            f"only {corners} corners covered (want >= {MIN_CORNERS_COVERED})")
    if pedal_rows == 0:
        problems.append("no pedal values stored - the OBD dongle produced "
                        "nothing, so this session cannot prove the channel")

    if problems:
        return Check("That session produced usable data", False,
                     f"session {sid}: " + "; ".join(problems),
                     "A GPS-only or very short session is a valid session "
                     "but does not close this gate. Use a full one.")
    return Check("That session produced usable data", True,
                 f"session {sid}: {laps} laps, {corners} corners, "
                 f"{pedal_rows} pedal readings")


def check_normalisation(cnx):
    """Calibration resolves and produces sane percent-of-travel."""
    from ingest.queries import get_corner_metrics
    cur = cnx.cursor()
    cur.execute("""
        SELECT TOP 1 s.session_id FROM dbo.sessions s
        WHERE s.pedal_channel = ?
        ORDER BY s.session_date DESC, s.session_id DESC""", TARGET_CHANNEL)
    row = cur.fetchone()
    if row is None:
        return Check("Pedal values normalise on read", False,
                     "Skipped - no such session yet.", None)
    sid = row[0]

    metrics = [m for m in get_corner_metrics(cnx, sid)
               if m["pedal_pct_raw"] is not None]
    if not metrics:
        return Check("Pedal values normalise on read", False,
                     f"session {sid} stored no raw pedal values.", None)

    normalised = [m["pedal_pct"] for m in metrics]
    if any(n is None for n in normalised):
        return Check(
            "Pedal values normalise on read", False,
            f"session {sid}: raw values present but pedal_pct is null - "
            f"no calibration row for (car, '{TARGET_CHANNEL}').",
            "Insert the measured rest/full constants into "
            "dbo.pedal_calibration for this car and channel.")
    if not all(0.0 <= n <= 100.0 for n in normalised):
        return Check("Pedal values normalise on read", False,
                     f"session {sid}: normalised values outside 0-100.",
                     "Check the calibration constants.")
    return Check("Pedal values normalise on read", True,
                 f"session {sid}: {len(metrics)} corners, normalised "
                 f"{min(normalised):.1f}-{max(normalised):.1f}%")


def check_tests():
    r = subprocess.run([sys.executable, "-m", "pytest", "-q"],
                       cwd=REPO_ROOT, capture_output=True, text=True)
    last = (r.stdout.strip().splitlines() or ["no output"])[-1]
    return Check("Tests pass", r.returncode == 0, last,
                 "Fix the failures before tagging.")


def check_tree_clean():
    dirty = _git("status", "--porcelain")
    n = len(dirty.splitlines()) if dirty else 0
    return Check("Working tree is clean", n == 0,
                 "clean" if n == 0 else f"{n} uncommitted file(s)",
                 "Commit or stash before tagging - a tag must point at "
                 "something reproducible.")


def check_ci_green():
    sha = _git("rev-parse", "HEAD")
    url = (f"https://api.github.com/repos/{REPO}/actions/runs"
           f"?head_sha={sha}")
    req = urllib.request.Request(url, headers={"Accept":
                                               "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=60) as fh:
            runs = json.load(fh).get("workflow_runs", [])
    except Exception as exc:
        return Check("CI is green on HEAD", False,
                     f"could not query GitHub ({type(exc).__name__})",
                     "Check manually before tagging.")
    if not runs:
        return Check("CI is green on HEAD", False,
                     f"no workflow runs for {sha[:7]} yet",
                     "Push, and wait for CI to finish.")
    bad = [f"{r['name']}={r['conclusion'] or r['status']}"
           for r in runs
           if r["status"] != "completed" or r["conclusion"] != "success"]
    return Check("CI is green on HEAD", not bad,
                 ", ".join(bad) if bad else
                 f"{len(runs)} run(s) green on {sha[:7]}",
                 "A tag pointing at a red commit is worse than no tag.")


def check_v1_scope_closed():
    path = os.path.join(REPO_ROOT, "docs", "BACKLOG.md")
    with open(path) as fh:
        lines = fh.read().splitlines()
    try:
        start = next(i for i, l in enumerate(lines) if l.startswith("## v1.0"))
        end = next(i for i, l in enumerate(lines)
                   if i > start and l.startswith("## v1.x"))
    except StopIteration:
        return Check("v1.0 backlog scope is closed", False,
                     "could not locate the v1.0 section", None)
    open_items = [l for l in lines[start:end] if l.startswith("- [ ]")]
    return Check("v1.0 backlog scope is closed", not open_items,
                 f"{len(open_items)} item(s) still open" if open_items
                 else "all items checked",
                 "\n".join(open_items[:3]) if open_items else None)


def run_all():
    checks = [check_tree_clean(), check_v1_scope_closed(), check_tests(),
              check_ci_green()]
    try:
        cnx = _connect()
        checks += [check_real_session(cnx), check_session_quality(cnx),
                   check_normalisation(cnx)]
    except RuntimeError as exc:
        detail, _, fix = str(exc).partition("|")
        checks.append(Check("Database reachable", False, detail, fix))
    except Exception as exc:
        checks.append(Check("Database reachable", False,
                            f"unexpected: {type(exc).__name__}", None))
    return checks


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    checks = run_all()
    ready = all(c.ok for c in checks)

    if args.json:
        print(json.dumps({
            "ready": ready,
            "checks": [{"name": c.name, "ok": c.ok, "detail": c.detail}
                       for c in checks]}, indent=2))
        return 0 if ready else 1

    print("\nv1.0 release gate\n" + "=" * 60)
    for c in checks:
        print(f"  [{'PASS' if c.ok else 'FAIL'}]  {c.name}")
        print(f"          {c.detail}")
        if not c.ok and c.fix:
            for line in c.fix.splitlines():
                print(f"          -> {line}")
    print("=" * 60)
    print("READY to tag v1.0.0" if ready else
          "NOT READY - see the failures above")
    print()
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())
