/* Auto-fetch session weather (v1.0 backlog item). sessions.weather
   and air_temp_f already existed as manual-entry columns and were
   never populated (same as tire_notes); ingestion now fills all five
   columns below from Open-Meteo's free/keyless historical archive
   API at load time (ingest/weather.py), using the event's track
   corner-apex centroid as the query point and the session's first
   GPS timestamp as the query time.

   Stays nullable: pre-existing sessions have none of this, and a
   track with no corner coordinates yet can't be geolocated. */
ALTER TABLE dbo.sessions ADD humidity_pct DECIMAL(4,1) NULL;
ALTER TABLE dbo.sessions ADD wind_mph DECIMAL(4,1) NULL;
ALTER TABLE dbo.sessions ADD precip_in DECIMAL(5,2) NULL;
ALTER TABLE dbo.sessions ADD weather_observed_at DATETIME2(0) NULL;
