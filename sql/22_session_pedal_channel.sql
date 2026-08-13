/* Record which OBD channel produced a session's pedal values.

   `corner_metrics.throttle_pos_apex_pct` holds a raw percentage, but the
   channel behind it changed on 2026-08-10: RaceChrono was reconfigured
   from throttle position (throttle plate) to true pedal position (PID
   0x49, `accelerator_pos`). The parser accepts either and deliberately
   writes both into the same key, so downstream code needed no change.

   That is fine for storage and wrong for interpretation. The two signals
   have different rest and full points - issue #8 measured the pedal at
   18.82% at rest and 94.90% at the stop - so normalising a stored value
   requires knowing which channel it came from. Nothing recorded it,
   which left the archive silently mixed at the 2026-08-10 boundary.

   Per the raw-data-is-sacred principle, issue #8 puts normalisation on
   read, not at ingest. This column is what makes that possible: it is
   the other half of the calibration key, `(car, channel)`.

   The parser already computes this value and reports it in the ingest
   diagnostics - it was simply being discarded.

   Backfill: every session on record is dated 2026-07-22 or earlier and
   every one carries pedal data, so all of them predate the change and
   are `throttle_pos`. Verified 2026-08-13 against all 15 rows rather
   than assumed from the dates alone.

   No CHECK constraint on the value on purpose. A third channel name
   appearing would then fail the insert at the track, and a session that
   ingests with an unrecognised channel name is far better than one that
   does not ingest at all. */

ALTER TABLE dbo.sessions
    ADD pedal_channel NVARCHAR(32) NULL;
GO

UPDATE dbo.sessions
SET pedal_channel = 'throttle_pos'
WHERE pedal_channel IS NULL
  AND session_date < '2026-08-10'
  AND EXISTS (
      SELECT 1
      FROM dbo.laps l
      JOIN dbo.corner_metrics cm ON cm.lap_id = l.lap_id
      WHERE l.session_id = dbo.sessions.session_id
        AND cm.throttle_pos_apex_pct IS NOT NULL);
GO
