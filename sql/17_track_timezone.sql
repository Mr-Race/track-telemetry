/* Fixes a real bug: ingest stored each session's start_time as raw UTC
   (datetime.fromtimestamp(ts, tz=timezone.utc)) into a timezone-naive
   DATETIME2 column, and the dashboard displays it as if it were
   already local - the event summary page's session times were
   consistently off by the local UTC offset (e.g. 21:00 shown for a
   5pm EDT session). Small, manually-curated table (like corners/
   run_groups already are), so a plain per-track IANA name is simpler
   and lighter than a geospatial timezone lookup - every track here is
   NJMP so far, always America/New_York. */
ALTER TABLE dbo.tracks ADD iana_timezone NVARCHAR(50) NULL;

UPDATE dbo.tracks SET iana_timezone = 'America/New_York'
WHERE track_name = 'NJMP Lightning' OR track_name = 'NJMP Thunderbolt';
