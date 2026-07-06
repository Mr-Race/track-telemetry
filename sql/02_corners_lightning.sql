/* Lightning (track_id = 1) apex coordinates - from AC's map pins.
   zone_radius_m: 35 default, larger on fast sweepers where the
   min-speed point wanders. Tune per corner later if needed. */

UPDATE dbo.corners SET apex_lat=39.3601687, apex_lon=-75.0553074, zone_radius_m=35 WHERE track_id=1 AND corner_code='1';
UPDATE dbo.corners SET apex_lat=39.3601319, apex_lon=-75.0589931, zone_radius_m=35 WHERE track_id=1 AND corner_code='2';
UPDATE dbo.corners SET apex_lat=39.3610047, apex_lon=-75.0597049, zone_radius_m=35 WHERE track_id=1 AND corner_code='3';
UPDATE dbo.corners SET apex_lat=39.3617878, apex_lon=-75.0596371, zone_radius_m=35 WHERE track_id=1 AND corner_code='4';
UPDATE dbo.corners SET apex_lat=39.3635458, apex_lon=-75.0608958, zone_radius_m=40 WHERE track_id=1 AND corner_code='5';
UPDATE dbo.corners SET apex_lat=39.3643683, apex_lon=-75.0579118, zone_radius_m=35 WHERE track_id=1 AND corner_code='6';
UPDATE dbo.corners SET apex_lat=39.3629895, apex_lon=-75.0544045, zone_radius_m=35 WHERE track_id=1 AND corner_code='7';
UPDATE dbo.corners SET apex_lat=39.3650868, apex_lon=-75.0531321, zone_radius_m=35 WHERE track_id=1 AND corner_code='8';
UPDATE dbo.corners SET apex_lat=39.3673126, apex_lon=-75.0521678, zone_radius_m=40 WHERE track_id=1 AND corner_code='9';
UPDATE dbo.corners SET apex_lat=39.3643566, apex_lon=-75.0514349, zone_radius_m=40 WHERE track_id=1 AND corner_code='10';

-- Verify: all 10 rows should show coordinates
SELECT corner_code, apex_lat, apex_lon, zone_radius_m
FROM dbo.corners WHERE track_id=1 ORDER BY sort_order;
