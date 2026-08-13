# Runbook

Deploys are hand-run on purpose while there is one operator. Every
command here has actually been run; none is aspirational.

## Deploy

### Function App (ingest + API)

```bash
func azure functionapp publish func-track-telemetry-ingest --python
```

Ships the whole app, so an unrelated change riding along is normal —
say so in the commit rather than being surprised by it later.

### Dashboard (Static Web Apps)

```bash
cd dashboard && npm run build
npx @azure/static-web-apps-cli deploy ./dist \
  --deployment-token "$(az staticwebapp secrets list \
      -n swa-track-telemetry-dashboard -g Track-telemetry \
      --query 'properties.apiKey' -o tsv)" \
  --env production
```

### MCP server (Container Apps)

See [MCP server setup](../mcp_server.md).

## Migrations

Numbered files in `sql/`, applied and recorded against the
`dbo.schema_migrations` ledger.

```bash
python sql/migrate.py           # preview: what's applied, what's pending
python sql/migrate.py --apply   # run the pending ones
```

**Checklist — the lesson from issue #1:**

1. **Preview first.** `migrate.py` with no flag lists applied and pending
   and reports checksum drift. A changed file that is already applied is
   a problem to resolve, not to re-run.
2. **Write the reasoning into the migration.** Every file in `sql/`
   opens with a comment explaining *why*. The schema is the one artifact
   nobody re-derives from first principles.
3. **Verify the data, not the exit code.** After applying, query the
   rows the migration claims to have changed. Migration 22 backfilled 15
   sessions; the check was `SELECT pedal_channel, COUNT(*) … GROUP BY`,
   not "no error".
4. **Prefer a real column to a nullable stopgap.** If the proper
   structure is cheap now, build it now.

## Verify a deploy

Not "did it deploy" — **did the thing that is running change**.

```bash
# The dashboard footer carries the version and the short commit.
curl -s https://<dashboard-host>/ | grep -o '/assets/index-[A-Za-z0-9_-]*\.js'
curl -s https://<dashboard-host>/assets/index-XXXX.js | grep -c '0\.9\.0'
```

**Always run a negative control.** A grep that matches nothing proves
nothing until you have seen it match something and fail to match
something else. The blob check for a rehearsal once queried a container
that did not exist and returned empty, which read as success.

## Rehearse an upload before an event

`dry_run=1` parses, resolves the event, computes laps and corner metrics,
and writes **nothing** — no rows, no blob. Safe against production.

```bash
KEY=$(az functionapp keys list -n func-track-telemetry-ingest \
      -g Track-telemetry --query 'functionKeys.default' -o tsv)
curl -X POST "https://func-track-telemetry-ingest.azurewebsites.net/api/ingest?dry_run=1&code=$KEY" \
     -H "Content-Type: text/csv" --data-binary "@session.csv"
```

Then confirm it wrote nothing:

```bash
az storage blob list --account-name racechronoraw \
  --container-name racechrono-raw --auth-mode login \
  --query "[?starts_with(name,'<event_id>/')].name" -o tsv
```

> The storage **account** is `racechronoraw`; the **container** is
> `racechrono-raw`. Getting this wrong returns an empty list that looks
> like a passing check.

## Before a track day

1. **Create the event** on the dashboard's Events page. Ingest resolves
   `event_id` from the CSV's track name and date and 400s if there is no
   match — in the paddock.
2. **Check the track configuration.** Two tracks are named
   `NJMP Thunderbolt`; the event points at one of them, and sessions are
   scored against that one's corners.
3. **Rehearse** with `dry_run=1` if anything in the pipeline changed.
4. **Expect the first upload to be slow.** The database auto-pauses after
   60 idle minutes. Measured: 59s end to end for an 87k-sample file
   against a paused database. It is not hung.

## Cold start

The serverless database resumes on first connect. Confirm its state:

```bash
SUB=$(az account show --query id -o tsv)
az rest --method get --url "https://management.azure.com/subscriptions/$SUB\
/resourceGroups/Track-telemetry/providers/Microsoft.Sql/servers/track-telemetry\
/databases/free-sql-db-7848405?api-version=2021-11-01" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['properties']['status'])"
```

`az sql db pause` is **unavailable on the free tier** — the REST call
returns `FeatureDisabledOnSelectedEdition`. A cold start cannot be
forced; wait for the 60-minute auto-pause.

Several `az` command modules fail to load on the CLI version in this
devcontainer (`monitor`, `rdbms`, and `az sql db pause`). `az rest`
against the management API is the workaround.

## DNS hygiene

```bash
python scripts/dns_audit.py          # exit 0 = clean, 1 = something dangles
```

Checks every CNAME in the zone for a target that no longer resolves. A
dangling record is a subdomain takeover risk: cloud endpoint names are
globally unique and claimable, so whoever registers the missing name
serves content on our subdomain, under a valid certificate.

**Dangling records are created by deleting cloud resources, not by
editing DNS.** Run this whenever an Azure resource with a custom domain
is decommissioned — that is the moment one appears, and the moment
nobody is looking at DNS.

It also runs as part of `release_gate.py`.

!!! warning "Not a scheduled workflow, on purpose"
    The obvious move is a nightly GitHub Action. On a **public** repo the
    run log would publish the exact hostname an attacker needs to claim —
    continuously, while the window is open. A finding here is a
    disclosure. Run it locally; findings go in `.local/`, per
    `SECURITY.md`.

## Cut a release

See [RELEASING.md](../RELEASING.md).

## Logs

```bash
az monitor app-insights query --app appi-track-telemetry -g Track-telemetry \
  --analytics-query "traces | where timestamp > ago(30m) \
     | where message has 'ingest parse' | order by timestamp desc | take 5" \
  --query "tables[0].rows" -o tsv
```

The ingest path logs `pedal_channel`, `gps_source`, `has_rpm`,
`rows_used` and the skipped-row breakdown for every upload.
