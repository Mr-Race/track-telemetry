/* ============================================================
   Track Telemetry Platform - Schema DDL (Weekend 1)
   Target: Azure SQL Database (free offer, serverless GP)
   Run as: Entra admin, connected to the telemetry database
   ============================================================ */

/* ---------- Reference: tracks ---------- */
CREATE TABLE dbo.tracks (
    track_id        INT IDENTITY(1,1) PRIMARY KEY,
    track_name      NVARCHAR(100) NOT NULL,
    configuration   NVARCHAR(100) NULL,          -- e.g. 'Full Course'
    length_miles    DECIMAL(4,2)  NULL,
    CONSTRAINT UQ_tracks_name_config UNIQUE (track_name, configuration)
);

/* ---------- Reference: corners (stable identity per track) ---------- */
CREATE TABLE dbo.corners (
    corner_id       INT IDENTITY(1,1) PRIMARY KEY,
    track_id        INT NOT NULL
        CONSTRAINT FK_corners_tracks REFERENCES dbo.tracks(track_id),
    corner_code     NVARCHAR(4) NOT NULL,        -- official label: '1','3A','11A'
    sort_order      TINYINT NOT NULL,            -- sequence around the lap
    corner_name     NVARCHAR(50) NULL,           -- e.g. 'Jersey Devil'
    apex_lat        DECIMAL(9,6) NULL,           -- from Google Maps satellite
    apex_lon        DECIMAL(9,6) NULL,
    zone_radius_m   SMALLINT NOT NULL DEFAULT 25,-- parser search zone around apex
    CONSTRAINT UQ_corners_track_code UNIQUE (track_id, corner_code)
);

/* ---------- events (a track weekend) ---------- */
CREATE TABLE dbo.events (
    event_id        INT IDENTITY(1,1) PRIMARY KEY,
    track_id        INT NOT NULL
        CONSTRAINT FK_events_tracks REFERENCES dbo.tracks(track_id),
    event_name      NVARCHAR(100) NOT NULL,      -- e.g. 'NASA NE June'
    organization    NVARCHAR(50)  NULL,          -- e.g. 'NASA', 'SCDA'
    start_date      DATE NOT NULL,
    end_date        DATE NULL,
    notes           NVARCHAR(MAX) NULL
);

/* ---------- sessions (one on-track run) ---------- */
CREATE TABLE dbo.sessions (
    session_id      INT IDENTITY(1,1) PRIMARY KEY,
    event_id        INT NOT NULL
        CONSTRAINT FK_sessions_events REFERENCES dbo.events(event_id),
    session_number  TINYINT NOT NULL,            -- 1..n within the event
    session_date    DATE NOT NULL,
    start_time      DATETIME2(0) NULL,
    run_group       NVARCHAR(20) NULL,           -- e.g. 'HPDE2'
    weather         NVARCHAR(50) NULL,           -- e.g. 'Dry, sunny'
    air_temp_f      DECIMAL(4,1) NULL,
    tire_notes      NVARCHAR(200) NULL,          -- cold/hot psi observations
    source_file     NVARCHAR(260) NULL,          -- blob name of raw CSV (provenance)
    notes           NVARCHAR(MAX) NULL,
    CONSTRAINT UQ_sessions_event_number UNIQUE (event_id, session_number)
);

/* ---------- laps ---------- */
CREATE TABLE dbo.laps (
    lap_id          INT IDENTITY(1,1) PRIMARY KEY,
    session_id      INT NOT NULL
        CONSTRAINT FK_laps_sessions REFERENCES dbo.sessions(session_id),
    lap_number      SMALLINT NOT NULL,
    lap_time_ms     INT NOT NULL,                -- store ms; format in views
    is_valid        BIT NOT NULL DEFAULT 1,      -- 0 = traffic/off/aborted
    is_out_lap      BIT NOT NULL DEFAULT 0,
    is_in_lap       BIT NOT NULL DEFAULT 0,
    notes           NVARCHAR(400) NULL,
    CONSTRAINT UQ_laps_session_lapnum UNIQUE (session_id, lap_number)
);

/* ---------- corner metrics (derived per lap per corner) ---------- */
CREATE TABLE dbo.corner_metrics (
    corner_metric_id INT IDENTITY(1,1) PRIMARY KEY,
    lap_id          INT NOT NULL
        CONSTRAINT FK_cm_laps REFERENCES dbo.laps(lap_id),
    corner_id       INT NOT NULL
        CONSTRAINT FK_cm_corners REFERENCES dbo.corners(corner_id),
    min_speed_mph   DECIMAL(5,1) NOT NULL,
    entry_speed_mph DECIMAL(5,1) NULL,
    exit_speed_mph  DECIMAL(5,1) NULL,
    CONSTRAINT UQ_cm_lap_corner UNIQUE (lap_id, corner_id)
);

/* ---------- indexes on lookup paths ---------- */
CREATE INDEX IX_sessions_event   ON dbo.sessions(event_id);
CREATE INDEX IX_laps_session     ON dbo.laps(session_id) INCLUDE (lap_time_ms, is_valid);
CREATE INDEX IX_cm_corner        ON dbo.corner_metrics(corner_id) INCLUDE (min_speed_mph);
CREATE INDEX IX_cm_lap           ON dbo.corner_metrics(lap_id);

/* ---------- convenience view: readable lap summary ---------- */
GO
CREATE VIEW dbo.v_lap_summary AS
SELECT
    t.track_name,
    e.event_name,
    e.start_date       AS event_date,
    s.session_number,
    s.run_group,
    l.lap_number,
    l.lap_time_ms,
    /* mm:ss.mmm formatting */
    FORMAT(l.lap_time_ms / 60000, '0') + ':' +
    FORMAT((l.lap_time_ms % 60000) / 1000, '00') + '.' +
    FORMAT(l.lap_time_ms % 1000, '000') AS lap_time_display,
    l.is_valid,
    l.is_out_lap,
    l.is_in_lap
FROM dbo.laps l
JOIN dbo.sessions s ON s.session_id = l.session_id
JOIN dbo.events   e ON e.event_id   = s.event_id
JOIN dbo.tracks   t ON t.track_id   = e.track_id;
GO

/* ============================================================
   Seed data - tracks
   ============================================================ */
/* Each distinct layout = its own track row. Lap times and corner
   sets are per-configuration and never mixed in queries. */
INSERT INTO dbo.tracks (track_name, configuration, length_miles) VALUES
('NJMP Lightning', 'Full Course', 1.90);

-- Thunderbolt: June 2026 sessions ran the classic layout,
-- T3 as the fast right sweeper (no chicane).
INSERT INTO dbo.tracks (track_name, configuration, length_miles) VALUES
('NJMP Thunderbolt', 'Classic', 2.25);
-- Add other layouts only when first driven, e.g.:
-- ('NJMP Thunderbolt', 'Devil''s Pass', ...) or a chicane variant

/* ============================================================
   Seed data - corners
   corner_code matches the OFFICIAL NJMP map labels, so database
   queries use the same language as the drivers' meeting.
   The parser computes min speed inside a zone_radius_m circle
   around each apex_lat/apex_lon. Fill coordinates later with:
     UPDATE dbo.corners SET apex_lat = xx.xxxxxx, apex_lon = -yy.yyyyyy
     WHERE track_id = ? AND corner_code = ?;
   ============================================================ */
-- Lightning (track_id = 1): official 10-corner layout
INSERT INTO dbo.corners (track_id, corner_code, sort_order) VALUES
(1,'1',1),(1,'2',2),(1,'3',3),(1,'4',4),(1,'5',5),
(1,'6',6),(1,'7',7),(1,'8',8),(1,'9',9),(1,'10',10);

-- Thunderbolt Classic (track_id = 2): 12 turns, T3 as the single
-- fast right (chicane not used in car sessions), plus 11A.
-- Drop the 11A row if you'd never analyze it separately.
INSERT INTO dbo.corners (track_id, corner_code, sort_order) VALUES
(2,'1',1),(2,'2',2),(2,'3',3),(2,'4',4),(2,'5',5),
(2,'6',6),(2,'7',7),(2,'8',8),(2,'9',9),(2,'10',10),
(2,'11',11),(2,'11A',12),(2,'12',13);

/* Optional: name notable corners, e.g.
UPDATE dbo.corners SET corner_name = 'Jersey Devil'
WHERE track_id = 2 AND corner_code = '10';  -- set the right code
*/
