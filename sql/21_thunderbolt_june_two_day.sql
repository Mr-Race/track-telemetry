/* The June Thunderbolt event ran two days, not one.

   `Thunderbolt June 2026` was created with start_date 2026-06-13 and no
   end_date, because only the first day's session had been ingested. The
   historical backfill (2026-08-12) brought three more sessions from
   2026-06-14, which `resolve_event_id` could not place: it matches a
   CSV's date against `start_date <= date <= ISNULL(end_date,
   start_date)`, and with a null end_date that window is a single day.

   Confirmed with AC 2026-08-12: it was one two-day weekend. */

UPDATE dbo.events
SET end_date = '2026-06-14'
WHERE event_name = 'Thunderbolt June 2026'
  AND start_date = '2026-06-13';
GO
