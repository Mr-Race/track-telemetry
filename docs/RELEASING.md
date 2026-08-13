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
   section as the body:

   ```bash
   gh release create v0.9.0 --title "v0.9.0" --notes-file <(...)
   ```

   or via the API / web UI if `gh` isn't installed.

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
