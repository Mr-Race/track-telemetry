# Releasing

A release is a git tag, a GitHub Release, a `CHANGELOG.md` entry, and a
version visible in the running app. Nothing is automated on purpose —
deploys are hand-run (see the deploy-automation item in
`docs/BACKLOG.md`), so the release steps stay explicit rather than
implied.

## Where the version lives

The root **`VERSION`** file is the single source of truth. `package.json`
deliberately isn't: the Python side ships from the same repo and has no
`package.json` to read.

`dashboard/vite.config.ts` reads it at build time and injects both the
version and the current short commit into the bundle, which the footer
renders. The commit matters as much as the version — deploys are
hand-run, so two builds of the same version are routine, and after an
incident the first question is always *which build is live*.

## Who runs this, and where

**Not from the paddock.** The release runs from a Codespace or
devcontainer on this repo — it needs the database, the Azure CLI, npm
and a GitHub token. A phone at a track has none of those.

The realistic sequence is: upload sessions at the track from the phone
as usual, then later, from a machine, open the Codespace and either run
the command or ask Claude Code to. The judgement — "was that a good
session, is this what 1.0 should mean" — is yours; everything after it
is mechanical.

### What the environment needs

| Requirement | Notes |
|---|---|
| `local.settings.json` | **Gitignored.** A fresh Codespace does not have it — `cp local.settings.json.example local.settings.json` and fill in `SQL_SERVER` / `SQL_DATABASE` |
| `az login` | `DefaultAzureCredential` has nothing to use otherwise |
| `GITHUB_TOKEN` | Provided automatically in Codespaces |
| Database reachable | Codespaces are covered by the `AllowAllWindowsAzureIps` firewall rule, so any Codespace works. Another machine needs its IP added |

`release_gate.py` names which of these is missing rather than reporting
them all as "the database is unreachable".

## Automated release

```bash
python scripts/release_gate.py                  # readiness only, writes nothing
python scripts/cut_release.py 1.0.0             # plan, changes nothing
python scripts/cut_release.py 1.0.0 --release   # tag, publish, deploy, verify
```

`cut_release.py` performs every step in the section below, in order, and
refuses to start if the gate fails. It does **not** write the changelog:
the `## [x.y.z]` section must already exist, authored by a human, and
becomes the GitHub Release body.

The gate is deliberately not wired to a trigger. It is objective, but
"the release is good" is not purely mechanical — it includes whether the
session was the day you actually had. Tagging is a decision; the steps
after it are not.

## Cutting a release

1. **Confirm the tree is clean and CI is green** on the commit you're
   about to tag. A tag pointing at a red commit is worse than no tag.

2. **Bump `VERSION`**, following the scheme in `docs/BACKLOG.md`
   (0.x pre-stable → 1.0 at the release gate → 1.x additive → 2.0
   breaking).

3. **Write the `CHANGELOG.md` entry.** Group as Added / Changed /
   Fixed / Security / Data. Say what changed for a *reader*, not what
   the commits did — `docs/BACKLOG.md`'s Done log is already the
   detailed record, including what broke and why.

4. **Commit both together** so `VERSION` and the changelog can never
   disagree.

5. **Tag and push:**

   ```bash
   git tag -a v0.9.0 -m "v0.9.0"
   git push origin v0.9.0
   ```

   Annotated, not lightweight — an annotated tag carries an author,
   date and message, and `git describe` prefers it.

6. **Create the GitHub Release** against that tag, with the changelog
   section as the body. `gh` is *not* installed in the Codespace, but
   `$GITHUB_TOKEN` is present and carries push rights, so the API works
   directly:

   ```bash
   # body = the changelog section for this version, as JSON
   curl -s -X POST \
     -H "Authorization: Bearer $GITHUB_TOKEN" \
     -H "Accept: application/vnd.github+json" \
     -d '{"tag_name":"v0.9.0","name":"v0.9.0","body":"...","prerelease":true}' \
     https://api.github.com/repos/Mr-Race/track-telemetry/releases
   ```

   Mark `prerelease: true` for anything below 1.0 — the versioning
   scheme calls 0.x pre-stable, and the Release should say so rather
   than leaving GitHub to label it "Latest" unqualified.

7. **Deploy, and verify against the platform** — see
   `docs/WAY-OF-WORKING.md` §5. Then confirm the footer shows the
   version and commit you just tagged:

   ```bash
   curl -s https://<dashboard-host>/assets/index-*.js | grep -o '0\.9\.0'
   ```

   That check is the point of putting the version in the footer at all:
   it closes the loop between "I tagged it" and "that is what is
   running".

## What a release does not mean

Tagging does not deploy anything, and deploying does not tag anything.
They are separate on purpose while deploys are manual — conflating them
would mean either untested tags or untagged production builds.
