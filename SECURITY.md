# Security policy

**This repository is public.** Anything filed as an issue, written in a
tracked file, or put in a commit message is world-readable the moment it
is pushed.

## Do not report security findings as GitHub issues

An open security finding in a public tracker is a disclosure. If the
weakness is still live, filing it publicly tells everyone how to use it
before it is fixed.

Instead:

- **Live/unfixed findings** go in `.local/security-findings.md`, which
  is gitignored. Tracked files may refer to them by identifier
  (`S-1`, `S-2`, …) and nothing more.
- **Commit messages count as public too.** Reference the identifier,
  never the detail.
- Once a finding is **fixed and deployed**, the write-up can be
  published — at that point it describes a closed hole, which is
  useful rather than dangerous. See `docs/WAY-OF-WORKING.md` §10.

For anything found by an outside reporter, open a
[private security advisory](https://github.com/Mr-Race/track-telemetry/security/advisories/new)
rather than an issue.

## Why this file exists

On 2026-08-09 an engineering review's findings were filed as public
issues, three of which described live weaknesses — an information
disclosure and a token-logging issue — while both were still deployed.
They were redacted and closed the next day, but **redaction is not
removal**: GitHub retains issue edit history, and anyone with read
access to a public repo can read it.

So the rule is written down here, in the place someone looks before
filing, rather than only in a review document.

## Data sensitivity

Sessions are GPS traces tied to a named driver, a car and a timestamp —
personal location data, not just lap times. Security, retention and
sharing decisions are made on that basis. See the guiding principles in
`docs/BACKLOG.md`.
