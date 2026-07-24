/* OBD channels in corner_metrics (Block 1 backlog item): throttle
   position at the apex (the corner zone's min-speed sample) and RPM
   at exit (the zone's last sample, matching how exit_speed_mph is
   derived). Both channels were already present in CSV v3 exports
   (source "200: obd"), just not persisted. Existing rows stay NULL
   until their session is re-ingested. */
ALTER TABLE dbo.corner_metrics ADD
    throttle_pos_apex_pct DECIMAL(5,1) NULL,
    rpm_exit              DECIMAL(6,1) NULL;
