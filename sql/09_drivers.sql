/* ============================================================
   Schema prep for future multi-user support (Block 8). Adds a real
   drivers table and backfills a driver_id FK on dbo.sessions now,
   while the table is small and single-user, so Block 8 never has to
   backfill historical data or touch a bigger table under load later.
   Run as: Entra admin, connected to the telemetry database.
   ============================================================ */
CREATE TABLE dbo.drivers (
    driver_id       INT IDENTITY(1,1) PRIMARY KEY,
    display_name    NVARCHAR(100) NOT NULL,
    entra_object_id NVARCHAR(100) NULL   -- filled in once the Entra
                                          -- External ID tenant (Block 5)
                                          -- exists and this driver signs in
);

INSERT INTO dbo.drivers (display_name) VALUES ('Me');

/* NOT NULL + DEFAULT backfills all existing sessions to driver_id=1
   (the row above) in the same statement, and any future INSERT that
   omits driver_id (e.g. today's ingest.py, which doesn't know about
   drivers yet) also gets 1 automatically -- no application code
   changes required until Block 8 actually needs to set a different
   driver. */
ALTER TABLE dbo.sessions
    ADD driver_id INT NOT NULL CONSTRAINT DF_sessions_driver_id DEFAULT 1;

ALTER TABLE dbo.sessions
    ADD CONSTRAINT FK_sessions_drivers
    FOREIGN KEY (driver_id) REFERENCES dbo.drivers(driver_id);
