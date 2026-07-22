/* ============================================================
   Friends' benchmark laps (v1) - manually entered, no accounts.
   Run as: Entra admin, connected to the telemetry database.
   ============================================================ */
CREATE TABLE dbo.benchmarks (
    benchmark_id    INT IDENTITY(1,1) PRIMARY KEY,
    track_id        INT NOT NULL
        CONSTRAINT FK_benchmarks_tracks REFERENCES dbo.tracks(track_id),
    driver_name     NVARCHAR(100) NOT NULL,
    lap_time_ms     INT NOT NULL,
    set_date        DATE NULL,
    notes           NVARCHAR(400) NULL
);

CREATE INDEX IX_benchmarks_track ON dbo.benchmarks(track_id);

/* Add a benchmark lap with, e.g.:
INSERT INTO dbo.benchmarks (track_id, driver_name, lap_time_ms, set_date, notes)
VALUES (1, 'Jane Doe', 88123, '2026-04-12', 'HPDE1, stock setup');
*/
