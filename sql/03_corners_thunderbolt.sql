/* ============================================================
   Thunderbolt corners - AC's map pins, 2026-07-04
   Part 1: rename codes to match AC's vocabulary (11A/11B)
   Part 2: Classic config apex coordinates
   Part 3: Devil's Pass config (new track row + corners)
   ============================================================ */

/* ---- Part 1: rename existing codes (two-step to avoid
        unique-constraint collision) ---- */
UPDATE dbo.corners SET corner_code='11B' WHERE track_id=2 AND corner_code='11A';
UPDATE dbo.corners SET corner_code='11A' WHERE track_id=2 AND corner_code='11';

/* ---- Part 2: Classic config coordinates (track_id = 2) ----
   Radius 35 default; 45 on T3 (fast sweeper, min-speed point
   wanders most); 40 on T12 (fast). */
UPDATE dbo.corners SET apex_lat=39.3626577, apex_lon=-75.0771972, zone_radius_m=35 WHERE track_id=2 AND corner_code='1';
UPDATE dbo.corners SET apex_lat=39.3640469, apex_lon=-75.0767815, zone_radius_m=35 WHERE track_id=2 AND corner_code='2';
UPDATE dbo.corners SET apex_lat=39.3644644, apex_lon=-75.0726586, zone_radius_m=45 WHERE track_id=2 AND corner_code='3';
UPDATE dbo.corners SET apex_lat=39.3617250, apex_lon=-75.0691694, zone_radius_m=35 WHERE track_id=2 AND corner_code='4';
UPDATE dbo.corners SET apex_lat=39.3601492, apex_lon=-75.0689692, zone_radius_m=35 WHERE track_id=2 AND corner_code='5';
UPDATE dbo.corners SET apex_lat=39.3601241, apex_lon=-75.0646881, zone_radius_m=35 WHERE track_id=2 AND corner_code='6';
UPDATE dbo.corners SET apex_lat=39.3579556, apex_lon=-75.0637389, zone_radius_m=35 WHERE track_id=2 AND corner_code='7';
UPDATE dbo.corners SET apex_lat=39.3576927, apex_lon=-75.0657023, zone_radius_m=35 WHERE track_id=2 AND corner_code='8';
UPDATE dbo.corners SET apex_lat=39.3585718, apex_lon=-75.0662142, zone_radius_m=35 WHERE track_id=2 AND corner_code='9';
UPDATE dbo.corners SET apex_lat=39.3595154, apex_lon=-75.0651142, zone_radius_m=35 WHERE track_id=2 AND corner_code='10';
UPDATE dbo.corners SET apex_lat=39.3594913, apex_lon=-75.0670078, zone_radius_m=35 WHERE track_id=2 AND corner_code='11A';
UPDATE dbo.corners SET apex_lat=39.3594794, apex_lon=-75.0680703, zone_radius_m=35 WHERE track_id=2 AND corner_code='11B';
UPDATE dbo.corners SET apex_lat=39.3593378, apex_lon=-75.0703140, zone_radius_m=40 WHERE track_id=2 AND corner_code='12';

/* ---- Part 3: Devil's Pass configuration ----
   NOTE: T9 pin is PROVISIONAL (satellite imagery predates the
   new section). Validate against GPS trace after first session
   on this layout. */
INSERT INTO dbo.tracks (track_name, configuration, length_miles) VALUES
('NJMP Thunderbolt', 'Devil''s Pass', NULL);

/* Insert corners using the new track_id (looked up dynamically) */
DECLARE @dp INT = (SELECT track_id FROM dbo.tracks
                   WHERE track_name='NJMP Thunderbolt'
                     AND configuration='Devil''s Pass');

INSERT INTO dbo.corners (track_id, corner_code, sort_order, apex_lat, apex_lon, zone_radius_m) VALUES
(@dp,'1', 1, 39.3626577, -75.0771972, 35),
(@dp,'2', 2, 39.3640469, -75.0767815, 35),
(@dp,'3', 3, 39.3644644, -75.0726586, 45),
(@dp,'4', 4, 39.3617250, -75.0691694, 35),
(@dp,'5', 5, 39.3601492, -75.0689692, 35),
(@dp,'6', 6, 39.3601241, -75.0646881, 35),
(@dp,'7', 7, 39.3579556, -75.0637389, 35),
(@dp,'8', 8, 39.3576927, -75.0657023, 35),
(@dp,'9', 9, 39.3593822, -75.0668479, 35),   -- provisional pin
(@dp,'10',10, 39.3594794, -75.0680703, 35),
(@dp,'11',11, 39.3593378, -75.0703140, 40);

/* Verify: 13 Classic rows with coords, 11 Devil's Pass rows */
SELECT t.configuration, c.corner_code, c.apex_lat, c.apex_lon, c.zone_radius_m
FROM dbo.corners c JOIN dbo.tracks t ON t.track_id=c.track_id
WHERE t.track_name='NJMP Thunderbolt'
ORDER BY t.configuration, c.sort_order;
