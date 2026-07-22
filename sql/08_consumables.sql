/* ============================================================
   Consumables life tracker (v1) - manual install/replacement entries.
   Wear is derived from the sessions table (sessions elapsed since
   install), not tracked as a manual counter.
   Run as: Entra admin, connected to the telemetry database.
   ============================================================ */
CREATE TABLE dbo.consumables (
    consumable_id           INT IDENTITY(1,1) PRIMARY KEY,
    item_name               NVARCHAR(100) NOT NULL,  -- e.g. 'Front brake pads'
    install_date            DATE NOT NULL,
    install_session_id      INT NULL
        CONSTRAINT FK_consumables_sessions
            REFERENCES dbo.sessions(session_id),
    service_life_sessions   SMALLINT NULL,           -- e.g. 8 track days
    service_life_months     SMALLINT NULL,           -- e.g. 12 months
    notes                   NVARCHAR(400) NULL
);

/* Add a consumable with, e.g.:
INSERT INTO dbo.consumables
    (item_name, install_date, service_life_sessions, notes)
VALUES ('Front brake pads', '2026-05-01', 8, 'Hawk DTC-60');
*/
