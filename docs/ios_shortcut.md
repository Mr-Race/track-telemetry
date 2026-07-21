# iOS Shortcut: RaceChrono → Track Telemetry Ingest

Share-sheet shortcut that takes a RaceChrono CSV export and POSTs it
straight to the deployed ingest Function
(`https://func-track-telemetry-ingest.azurewebsites.net/api/ingest`),
so a session can be uploaded from the phone at the track. Build this
natively in the Shortcuts app — no import file, since the format is
easy to get subtly wrong without on-device testing.

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
`Upload to Track Telemetry`.

1. **Add Action → "Ask for Input"**
   - Input Type: `Number`
   - Prompt: `Event ID (1 = Lightning, 2 = Thunderbolt)`
   - Default Answer: `1`
   - Tap the output of this action (top-right "..." on the action, or
     tap the blue result chip) and rename the variable to `EventID`.

2. **Add Action → "Ask for Input"**
   - Input Type: `Number`
   - Prompt: `Session number (1, 2, 3... for this event)`
   - Default Answer: `1`
   - Rename its output variable to `SessionNumber`.

3. **Add Action → "Ask for Input"**
   - Input Type: `Number`
   - Prompt: `Dry run? (1 = test only, 0 = load for real)`
   - Default Answer: `1` (default to a safe test run first)
   - Rename its output variable to `DryRun`.

4. **Add Action → "URL"**
   - Type the full URL with placeholder query values, e.g.:
     ```
     https://func-track-telemetry-ingest.azurewebsites.net/api/ingest?event_id=1&session_number=1&dry_run=1&code=PASTE_YOUR_KEY_HERE
     ```
   - Shortcuts splits `?event_id=1&session_number=1&dry_run=1&code=...`
     into separate tappable query-value chips. Tap the `1` after
     `event_id=` and replace it with the `EventID` variable (use the
     variable-picker icon above the keyboard). Do the same for
     `session_number=` → `SessionNumber` and `dry_run=` → `DryRun`.
     Leave `code=` as your literal key — this keeps values
     URL-encoded correctly even if you later add a filename with
     spaces.

5. **Add Action → "Get Contents of URL"**
   - URL field: tap it, pick the magic-variable chip for the **URL**
     action's output from step 4 (not a fresh URL — reuse the built one).
   - Tap **Show More**:
     - Method: `POST`
     - Request Body: `File`
     - Tap the file field and pick **Shortcut Input** (the variable
       representing whatever RaceChrono shared in) as the file.
   - Leave headers empty — the function reads the raw POST body and
     doesn't check Content-Type.

6. **Add Action → "Get Dictionary from Input"**
   - Input: the result of "Get Contents of URL" (should auto-select).
     This parses the JSON response so the next step is readable.

7. **Add Action → "Show Result"**
   - Input: the dictionary from step 6.

## 3. Configure share-sheet visibility

Tap the settings icon (ⓘ) at the top of the shortcut editor:

- Enable **Show in Share Sheet**.
- Under **Share Sheet Types**, make sure **Files** is checked (this is
  what lets RaceChrono's CSV export target this shortcut).
- Optionally set an icon/color so it's easy to spot in the share sheet.

## 4. Test it

1. In RaceChrono, open a completed session → **Share/Export** → CSV.
2. In the share sheet, find `Upload to Track Telemetry` (tap **More**
   and enable it as a favorite if it doesn't show up right away).
3. Answer the three prompts — leave `DryRun = 1` for the first test.
4. Confirm the JSON result shows the expected track name, sample
   count, lap count, and corner coverage, with `"loaded": false`.
5. Re-run with `DryRun = 0` once the dry run looks right — check for
   `"loaded": true` and a `session_id`.

## Troubleshooting

- **401/403 from the Function**: the `code=` value is wrong or missing
  — re-check the key from step 1 (keys can be rotated in the portal).
- **400 "event_id and session_number query params are required
  integers"**: one of the `Ask for Input` values didn't get wired into
  the URL query chip correctly — re-open the URL action and confirm
  each chip shows the variable name, not literal `1`.
- **`UQ_sessions_event_number` violation on a real load**: that
  event_id + session_number combination is already in `dbo.sessions`
  — bump the session number.
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
Input` right after step 1, rename its output to `Filename`, and add a
`filename=` chip in the URL action wired to that variable.
