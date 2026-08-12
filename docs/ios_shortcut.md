# iOS Shortcut: RaceChrono → Track Telemetry Ingest

Share-sheet shortcut that takes a RaceChrono CSV export and POSTs it
straight to the deployed ingest Function
(`https://func-track-telemetry-ingest.azurewebsites.net/api/ingest`),
so a session can be uploaded from the phone at the track. Build this
natively in the Shortcuts app — no import file, since the format is
easy to get subtly wrong without on-device testing.

No prompts: the CSV already carries the track name and date, so the
Function auto-matches the event (create it on the dashboard first),
auto-picks the next session number for that event, and defaults the
car to the Integra. The URL is a fixed string — nothing to answer at
the track, just share the file and go. See "Overriding the defaults"
below if you ever need to force a specific event/session/car.

## 1. Get the function key

From a machine with `az` logged in (device-code login against the
`d5080430-a89e-4e80-930a-c9a8eb304c99` tenant — see prior Azure SQL
auth notes if `az login` needs the tenant flag):

```
az functionapp function keys list \
  -g Track-telemetry -n func-track-telemetry-ingest \
  --function-name ingest -o table
```

Copy the `default` key value. It only needs to live inside the
Shortcut on your phone (and iCloud if Shortcuts sync is on) — don't
paste it into any file in this repo.

## 2. Build the shortcut

Open the **Shortcuts** app → tap **+** → name it something like
`Upload to Track Telemetry`. No "Ask for Input" actions needed — the
whole shortcut is three actions:

1. **Add Action → "URL"**
   - Type the full URL, literally, with your function key pasted in:
     ```
     https://func-track-telemetry-ingest.azurewebsites.net/api/ingest?code=PASTE_YOUR_KEY_HERE
     ```
   - That's it — no `event_id`, `session_number`, `car_id`, or
     `dry_run` chips. The Function resolves all three from the CSV
     and existing dashboard data (see "How auto-resolution works"
     below) and defaults to a real load, not a dry run.

2. **Add Action → "Get Contents of URL"**
   - URL field: tap it, pick the magic-variable chip for the **URL**
     action's output from step 1 (not a fresh URL — reuse the built one).
   - Tap **Show More**:
     - Method: `POST`
     - Request Body: `File`
     - Tap the file field and pick **Shortcut Input** (the variable
       representing whatever RaceChrono shared in) as the file.
   - Leave headers empty — the function reads the raw POST body and
     doesn't check Content-Type.

3. **Add Action → "Get Dictionary from Input"**
   - Input: the result of "Get Contents of URL" (should auto-select).
     This parses the JSON response so the next step is readable.

4. **Add Action → "Show Result"**
   - Input: the dictionary from step 3. Check the `event_id`,
     `session_number`, and `track` fields in the result to confirm it
     matched the session you meant to upload.

### What to check in the result, at the track

The response carries a `parse` block precisely so a bad upload is
obvious while you can still do something about it, rather than turning
up weeks later as NULLs in the data:

- **`parse.pedal_channel`** — which OBD pedal channel was read.
  Since the logger was reconfigured to PID 0x49 this should read
  **`accelerator_pos`**. If it says `throttle_pos`, RaceChrono is still
  on the old channel config. If it's `null`, no pedal data was captured
  at all — usually the OBD dongle not paired.
- **`parse.has_rpm`** — `false` also points at the dongle.
- **`parse.rows_skipped`** — `malformed` and `missing_gps` should both
  be `0`. A non-zero `malformed` means a truncated or corrupt export;
  re-export before leaving the paddock. (`no_lap` is normal and often
  large — those are the pre-first-crossing and pit samples.)
- **`duplicate`** — `true` means this exact file was already ingested
  and the existing session was refreshed rather than a second one
  created. Safe, and expected if you upload twice.

A session with no OBD data still ingests fine — laps, corner metrics
and segment times all come from GPS.

## How auto-resolution works

- **Event**: matched from the CSV's `Track name` + `Created` date
  against `dbo.events` (track + date falling within
  `start_date`..`end_date`). **The event must already exist** — create
  it on the dashboard's Events page before the track day, or the
  upload 400s with "No event found for ... Create the event on the
  dashboard first."
- **Session number**: the next unused number for that event
  (`MAX(session_number) + 1`), so back-to-back uploads at the same
  event just increment automatically.
- **Car**: defaults to the Integra (`car_id=2`) — the only car
  currently tracked. Change `DEFAULT_CAR_ID` in `function_app.py` if
  that stops being true.

## Overriding the defaults

Append `event_id=`, `session_number=`, and/or `car_id=` query params
to the URL to force a value instead of auto-resolving it — useful for
re-uploading into a specific slot, or a dry run
(`&dry_run=1`, response has `"loaded": false` and nothing is written
to `dbo.sessions`/`dbo.laps`). The raw CSV is always archived to Blob
regardless of `dry_run`.

## 3. Configure share-sheet visibility

Tap the settings icon (ⓘ) at the top of the shortcut editor:

- Enable **Show in Share Sheet**.
- Under **Share Sheet Types**, make sure **Files** is checked (this is
  what lets RaceChrono's CSV export target this shortcut).
- Optionally set an icon/color so it's easy to spot in the share sheet.

## 4. Test it

1. Make sure the event for today is already created on the dashboard
   (Events page) — auto-resolution has nothing to match against
   otherwise.
2. In RaceChrono, open a completed session → **Share/Export** → CSV.
3. In the share sheet, find `Upload to Track Telemetry` (tap **More**
   and enable it as a favorite if it doesn't show up right away).
4. Confirm the JSON result shows `"loaded": true`, the expected
   `event_id`/`session_number`/`track`, a `session_id`, sample count,
   lap count, and corner coverage.

## Troubleshooting

- **401/403 from the Function**: the `code=` value is wrong or missing
  — re-check the key from step 1 (keys can be rotated in the portal).
- **400 "No event found for '<track>' on <date>. Create the event on
  the dashboard first."**: add the event on the dashboard's Events
  page before uploading, or the CSV's date/track doesn't fall inside
  any existing event's date range — check `start_date`/`end_date`.
- **400 "Multiple events match ... pass event_id explicitly"**: two
  events at the same track overlap the CSV's date — append
  `&event_id=` to the URL to disambiguate for this upload.
- **`UQ_sessions_event_number` violation on a real load**: session
  numbers are auto-assigned per event, so this should be rare — it
  means a concurrent upload raced this one to the same number. Just
  re-run the shortcut.
- **Timeout on the very first upload of the day**: expected, not a bug.
  The Function App (Consumption plan) spins workers down when idle, and
  the free-tier serverless SQL DB auto-pauses too — the first request
  has to cold-start the Function *and* wait ~30-60s for SQL to resume
  (see `LOGIN_TIMEOUT_S` in `ingest/cloud.py`). Just re-run the shortcut;
  the second attempt should complete in a few seconds.

## Optional: preserve the original filename

The Function defaults to `session_<epoch>.csv` in Blob storage if no
`filename` is given. To keep the RaceChrono export's real name, insert
a **"Get Details of Files"** action (Detail: `Name`) on `Shortcut
Input` *before* the URL action, rename its output to `Filename`, and
add a `&filename=` chip in the URL action wired to that variable (the
URL will then have both `code=` and `filename=` chips, tap the
variable-picker icon to wire the latter).
