#!/usr/bin/env python3
"""Check the mr-race.com zone for dangling CNAMEs (subdomain takeover).

A dangling CNAME points at a hostname that no longer resolves. Cloud
endpoint names are globally unique and claimable, so whoever registers
the missing name serves content on our subdomain - under a valid
certificate, because the certificate follows the name.

This is not hypothetical here. Until 2026-08-13 `www.mr-race.com`
pointed at `azureresumeach.azureedge.net`, an Azure CDN classic endpoint
deleted with an earlier project. It was found while configuring the
custom domain, not by looking for it. By then `www.mr-race.com` had
become an Entra redirect URI, so a takeover would have meant receiving
OAuth authorization codes.

The failure mode is worth stating precisely: **dangling records are
created by deleting cloud resources, not by editing DNS.** Nobody edits
the zone and introduces one. They appear when something is decommissioned
and its DNS record outlives it, which is exactly when nobody is looking
at DNS.

    python scripts/dns_audit.py           # table
    python scripts/dns_audit.py --json
    echo $?                               # 0 = clean, 1 = something dangles

## Why this is not a scheduled GitHub Action

The obvious move is a nightly workflow. That would be a mistake on a
**public** repository: the run log would publish the exact name an
attacker needs to claim, to everyone, continuously, while the window is
open. A finding here is a disclosure. It runs locally, and its output
belongs in `.local/`, per SECURITY.md.
"""

import argparse
import json
import subprocess
import sys

ZONE = "mr-race.com"

# Subdomains we have used, plan to use, or might have used and forgotten.
# The forgotten ones are the point: a name is only checkable if someone
# thought to list it, so this errs toward over-listing.
NAMES = [
    "",            # apex
    "www",
    "mcp",
    "mcp-demo",    # planned, issue #33
    "demo",
    "api",
    "app",
    "dashboard",
    "staging",
    "test",
    "dev",
    "pay",
    "cdn",
    "assets",
    "docs",
    "blog",
    "resume",      # the earlier project that left the dangling record
]

RESOLVER = "1.1.1.1"


def dig(name, rtype):
    r = subprocess.run(["dig", "+short", rtype, name, f"@{RESOLVER}"],
                       capture_output=True, text=True, timeout=30)
    return [l.strip() for l in r.stdout.splitlines() if l.strip()]


def resolves(host):
    """True if the host has any address. A CNAME to a name with no
    address is the dangling case."""
    return bool(dig(host, "A") or dig(host, "AAAA"))


def audit():
    results = []
    for sub in NAMES:
        fqdn = f"{sub}.{ZONE}" if sub else ZONE
        cnames = dig(fqdn, "CNAME")
        if not cnames:
            # No CNAME: either an A record, or nothing. Neither dangles.
            continue
        target = cnames[0].rstrip(".")
        ok = resolves(target)
        results.append({"name": fqdn, "target": target, "resolves": ok})
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    try:
        rows = audit()
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        print(f"could not run dig: {type(exc).__name__}", file=sys.stderr)
        return 2

    dangling = [r for r in rows if not r["resolves"]]

    if args.json:
        print(json.dumps({"dangling": dangling, "checked": rows}, indent=2))
        return 1 if dangling else 0

    print(f"\nDNS audit - {ZONE}\n" + "=" * 62)
    for r in rows:
        mark = "ok      " if r["resolves"] else "DANGLING"
        print(f"  [{mark}] {r['name']}")
        print(f"             -> {r['target']}")
    if not rows:
        print("  no CNAME records found (nothing to dangle)")
    print("=" * 62)
    if dangling:
        print(f"{len(dangling)} dangling record(s). Each is a takeover risk:")
        for r in dangling:
            print(f"  - {r['name']} points at {r['target']}, which does not "
                  f"resolve.")
        print("\nFix by removing or repointing the record. Do NOT paste the "
              "target into a public issue or commit message - it names what "
              "an attacker would claim. See SECURITY.md.")
    else:
        print("No dangling CNAMEs.")
    print()
    return 1 if dangling else 0


if __name__ == "__main__":
    sys.exit(main())
