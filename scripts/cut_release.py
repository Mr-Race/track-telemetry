#!/usr/bin/env python3
"""Cut a release: gate, bump, tag, publish, deploy, verify.

Executes every step of `docs/RELEASING.md` in order, refusing to start
if `release_gate.py` says the platform is not ready.

    python scripts/cut_release.py 1.0.0            # plan only, changes nothing
    python scripts/cut_release.py 1.0.0 --release  # actually do it

The default is a plan. A release is hard to take back on a public repo,
so doing nothing is what happens when the command is run by accident or
half-remembered.

What this deliberately does NOT do is write the changelog. The section
for the version must already exist in `CHANGELOG.md`, authored by a
human. Generated release notes read like generated release notes, and
the changelog is the one artifact a reader meets first. The script
checks the section is there and uses it as the GitHub Release body.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "Mr-Race/track-telemetry"
SWA_NAME = "swa-track-telemetry-dashboard"
RESOURCE_GROUP = "Track-telemetry"
# Verify against the canonical public address, not the origin behind
# it - that is what a reader actually visits. The Azure host stays a
# registered redirect URI and CORS origin, so both keep working.
DASHBOARD_HOST = "https://www.mr-race.com"


def run(cmd, check=True, cwd=REPO_ROOT, capture=True):
    r = subprocess.run(cmd, cwd=cwd, capture_output=capture, text=True)
    if check and r.returncode != 0:
        sys.exit(f"FAILED: {' '.join(cmd)}\n{(r.stderr or r.stdout)[-2000:]}")
    return (r.stdout or "").strip()


def changelog_section(version):
    """The already-authored `## [x.y.z]` block, for the Release body."""
    path = os.path.join(REPO_ROOT, "CHANGELOG.md")
    with open(path) as fh:
        text = fh.read()
    m = re.search(rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## |\Z|^\[)",
                  text, re.S | re.M)
    if not m:
        sys.exit(
            f"CHANGELOG.md has no '## [{version}]' section.\n"
            "Write it first - this script does mechanics, not authorship.")
    body = m.group(1).strip()
    if not body:
        sys.exit(f"The '## [{version}]' section in CHANGELOG.md is empty.")
    return body


def gate():
    # The gate writes to the inherited stdout; flush ours first so the
    # two streams don't interleave out of order.
    sys.stdout.flush()
    r = subprocess.run([sys.executable,
                        os.path.join(REPO_ROOT, "scripts", "release_gate.py")],
                       cwd=REPO_ROOT)
    return r.returncode == 0


def github(path, payload=None, method="POST"):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN is not set - cannot publish the Release.")
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/{path}",
        data=json.dumps(payload).encode() if payload else None,
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/vnd.github+json",
                 "Content-Type": "application/json"},
        method=method)
    with urllib.request.urlopen(req, timeout=120) as fh:
        return json.load(fh)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("version", help="e.g. 1.0.0 (no leading v)")
    ap.add_argument("--release", action="store_true",
                    help="actually tag, publish and deploy")
    ap.add_argument("--skip-gate", action="store_true",
                    help="tag despite a failing gate. Records nothing and "
                         "explains nothing - use only with a reason you "
                         "would defend out loud")
    args = ap.parse_args()

    version = args.version.lstrip("v")
    tag = f"v{version}"
    prerelease = version.startswith("0.")

    print(f"\n=== Cutting {tag} ===\n")

    body = changelog_section(version)          # fails fast if unwritten
    print(f"Changelog section found: {len(body.splitlines())} lines\n")

    if not gate():
        if not args.skip_gate:
            sys.exit("\nGate failed. Nothing has been changed.")
        print("\n!! Gate failed and --skip-gate was passed. Continuing.\n")

    existing = run(["git", "tag", "-l", tag])
    if existing:
        sys.exit(f"Tag {tag} already exists. Releases are not re-cut; "
                 f"bump the version instead.")

    if not args.release:
        print("PLAN (nothing will change without --release):")
        print(f"  1. VERSION -> {version}")
        print(f"  2. commit 'release: {tag}'")
        print(f"  3. annotated tag {tag}, pushed")
        print(f"  4. GitHub Release {tag} (prerelease={prerelease}) "
              f"from the changelog section")
        print(f"  5. build + deploy the dashboard")
        print(f"  6. verify {version} and the tagged commit are live")
        print("\nRe-run with --release to execute.\n")
        return 0

    # 1-2. Version and commit -------------------------------------------
    with open(os.path.join(REPO_ROOT, "VERSION"), "w") as fh:
        fh.write(version + "\n")
    run(["git", "add", "VERSION"])
    if run(["git", "diff", "--cached", "--name-only"]):
        run(["git", "commit", "-m", f"release: {tag}"])
        run(["git", "push", "origin", "HEAD"])
    print(f"[1/6] VERSION={version}, committed and pushed")

    # 3. Tag -------------------------------------------------------------
    run(["git", "tag", "-a", tag, "-m", f"{tag}\n\n{body[:1500]}"])
    run(["git", "push", "origin", tag])
    sha = run(["git", "rev-parse", "--short", "HEAD"])
    print(f"[2/6] annotated tag {tag} -> {sha}, pushed")

    # 4. GitHub Release --------------------------------------------------
    rel = github("releases", {"tag_name": tag, "name": tag, "body": body,
                              "draft": False, "prerelease": prerelease})
    print(f"[3/6] Release published: {rel['html_url']}")

    # 5. Deploy ----------------------------------------------------------
    run(["npm", "run", "build"], cwd=os.path.join(REPO_ROOT, "dashboard"))
    token = run(["az", "staticwebapp", "secrets", "list", "-n", SWA_NAME,
                 "-g", RESOURCE_GROUP, "--query", "properties.apiKey",
                 "-o", "tsv"])
    run(["npx", "@azure/static-web-apps-cli", "deploy", "./dist",
         "--deployment-token", token, "--env", "production"],
        cwd=os.path.join(REPO_ROOT, "dashboard"))
    print("[4/6] dashboard built and deployed")

    # 6. Verify against the platform -------------------------------------
    # The point of putting the version in the footer: close the loop
    # between "I tagged it" and "that is what is running". Includes a
    # negative control, because a grep that cannot fail proves nothing.
    import urllib.request as u
    index = u.urlopen(DASHBOARD_HOST, timeout=60).read().decode()
    m = re.search(r"/assets/index-[A-Za-z0-9_-]+\.js", index)
    if not m:
        sys.exit("[5/6] could not find the bundle on the live site")
    asset = u.urlopen(DASHBOARD_HOST + m.group(0), timeout=120).read().decode()

    ok_version = version in asset
    ok_commit = sha in asset
    bogus = f"{int(version.split('.')[0]) + 9}.9.9"
    ok_control = bogus not in asset

    print(f"[5/6] live bundle {m.group(0)}")
    print(f"        version {version}: {'found' if ok_version else 'MISSING'}")
    print(f"        commit {sha}: {'found' if ok_commit else 'MISSING'}")
    print(f"        negative control ({bogus} absent): "
          f"{'ok' if ok_control else 'FAILED - the grep matches anything'}")

    if not (ok_version and ok_commit and ok_control):
        sys.exit("\n[6/6] Released and deployed, but verification FAILED. "
                 "The tag stands; investigate what is actually running.")

    print(f"\n[6/6] {tag} is live and verified.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
