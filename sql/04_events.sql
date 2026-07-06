/* Events for the two loaded sessions.
   Edit event_name / organization to your preferred labels before
   running - these strings are what you'll see in query results. */

INSERT INTO dbo.events (track_id, event_name, organization, start_date)
VALUES (1, 'Lightning May 2026', 'EDIT_ME', '2026-05-16');

INSERT INTO dbo.events (track_id, event_name, organization, start_date)
VALUES (2, 'Thunderbolt June 2026', 'EDIT_ME', '2026-06-13');

/* Note the ids - the parser needs them for --event-id */
SELECT event_id, event_name, start_date FROM dbo.events;
