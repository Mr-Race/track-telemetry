<!--
  THIS REPOSITORY IS PUBLIC - including this description and every
  commit message. Reference security findings by identifier (S-1, S-2)
  and nothing more. See SECURITY.md.
-->

## What and why

<!-- What changed, and what problem it solves. -->

## Verification

CI covers tests, lint, typecheck and build. It does **not** cover
whether production is actually right — see `docs/WAY-OF-WORKING.md` §5:
*the code being right does not mean production is right.*

Tick what applies; delete what doesn't.

- [ ] Behaviour verified against **real data**, not only fixtures
      <!-- Especially for parser/query changes: these decide what the
           historical backfill will write. Recomputing against stored
           values and getting zero differences is the check. -->
- [ ] Deployed, and verified against the **platform's own view** rather
      than the deploy command's success message
- [ ] Routes **enumerated**, not spot-checked
      <!-- "all 16 routes 401 without a token" is verification;
           "the one I tried worked" is not -->
- [ ] Deployed function/revision count reconciled against source
      <!-- A bad dependency floor once wiped every registered function -->
- [ ] Container revision confirmed healthy **and** cold-started
      <!-- Single-revision mode keeps serving the last good revision
           while a new one crash-loops -->
- [ ] Migrations: `python sql/migrate.py` clean, no drift
- [ ] Anything unverifiable is stated plainly below, not left implied

## Known gaps left behind

<!-- Anything shipped but not proven, or deliberately deferred. If it
     only exists in a chat, it does not exist - add it to the "Known
     gaps and accepted risks" section of docs/BACKLOG.md. -->

## Backlog / issues

<!-- Closes #N. If this is v1.0 scope, docs/BACKLOG.md is the record;
     an issue alone is not enough. -->
