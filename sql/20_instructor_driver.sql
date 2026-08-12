/* Attribute the instructor-driven session correctly (GitHub issue #2).

   Session 13 (Lightning May 2026, 2026-05-17) was driven by AC's
   instructor in AC's car, but carried the default driver_id = 1 ('Me').
   Nothing filtered on driver, so every "personal best" computation
   returned a lap AC didn't drive: NJMP Lightning's PB read 1:21.837
   instead of AC's real 1:24.975 (session 9).

   The lap itself is a legitimate reference for what the car can do, so
   per AC (2026-08-11) it is kept as a benchmark rather than hidden -
   which is exactly what dbo.benchmarks is for: a lap attributed to
   someone who isn't you.

   Deliberately NOT changed: the event page's hero stats. AC's call -
   "event best" there means the fastest lap turned that day by anyone,
   so event 1 still reports 1:21.837. The session rows now name their
   driver so the page can't silently credit it to AC. */

INSERT INTO dbo.drivers (display_name) VALUES ('Instructor');
GO

/* Separate batch: the UPDATE reads back the row inserted above. */
UPDATE dbo.sessions
SET driver_id = (SELECT driver_id FROM dbo.drivers
                 WHERE display_name = 'Instructor')
WHERE session_id = 13;
GO

INSERT INTO dbo.benchmarks (track_id, driver_name, lap_time_ms, set_date, notes)
SELECT e.track_id, 'Instructor', 81837, '2026-05-17',
       'Instructor-driven session in AC''s car (session_id 13). See issue #2.'
FROM dbo.sessions s
JOIN dbo.events e ON e.event_id = s.event_id
WHERE s.session_id = 13;
GO
