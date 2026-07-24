/* Corner names - Lightning (track_id = 1)
   Per AC, 2026-07-24: T9 = Lightbulb (banked carousel onto the
   front straight), T10 = the Kink.
   Run in Query editor or via deployment tooling. Extend this file
   as more corners get named (Thunderbolt TBD). */

UPDATE dbo.corners SET corner_name = 'Lightbulb'
WHERE track_id = 1 AND corner_code = '9';

UPDATE dbo.corners SET corner_name = 'Kink'
WHERE track_id = 1 AND corner_code = '10';

/* Verify */
SELECT corner_code, corner_name
FROM dbo.corners
WHERE track_id = 1
ORDER BY sort_order;
