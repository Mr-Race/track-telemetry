/* Per-segment (corner-to-corner) lap times, computed at ingest from
   already-parsed GPS samples - no raw telemetry storage needed.
   Prerequisite for the optimal-lap dashboard item (v1.0).

   Each corner apex acts as a fixed timing gate; the crossing time is
   interpolated (parabolic fit around the sample of closest approach)
   rather than taken from a raw sample. This matters: an earlier
   attempt used each lap's raw min-speed sample as the corner "split"
   marker, and that point drifts by braking/line choice lap to lap,
   which inflated the theoretical-best-lap gap badly (13.3s vs a
   credible 3.1s on the same Thunderbolt session - see BACKLOG.md's
   2026-07-24 note). A fixed apex location with interpolated crossing
   time is comparable lap-to-lap and session-to-session.

   segment_order runs 1..N+1 for a track with N corners: #1 = lap
   start -> first corner's gate, #2..#N = corner-to-corner, #N+1 =
   last corner's gate -> lap end (to_corner_id NULL marks this final
   segment, matching the same lap-boundary elapsed-time convention
   dbo.laps.lap_time_ms already uses, so segment times for a lap sum
   to its lap_time_ms). A lap gets no rows at all if any corner's gate
   can't be resolved for it (car missed the zone / bad GPS) or if the
   interpolated gates aren't chronologically increasing - a partial
   chain would be worse than none for summing into an optimal lap. */
CREATE TABLE dbo.segment_times (
    segment_time_id INT IDENTITY(1,1) PRIMARY KEY,
    lap_id          INT NOT NULL
        CONSTRAINT FK_segment_times_laps REFERENCES dbo.laps(lap_id),
    segment_order   TINYINT NOT NULL,
    to_corner_id    INT NULL
        CONSTRAINT FK_segment_times_corners REFERENCES dbo.corners(corner_id),
    segment_time_ms INT NOT NULL,
    CONSTRAINT UQ_segment_times_lap_order UNIQUE (lap_id, segment_order)
);
