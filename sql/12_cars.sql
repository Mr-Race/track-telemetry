/* Cars catalog, for the first write-capable dashboard feature (event
   creation, sessions to follow). Scoped per session, not per event -
   a driver could swap cars between sessions within the same event -
   so this attaches to dbo.sessions, matching how run_group_id already
   works (sql/11_run_groups.sql). */
CREATE TABLE dbo.cars (
    car_id       INT IDENTITY(1,1) PRIMARY KEY,
    display_name NVARCHAR(50) NOT NULL,   -- e.g. 'E92 M3'
    make         NVARCHAR(50) NULL,
    model        NVARCHAR(50) NULL,
    year         SMALLINT NULL,
    notes        NVARCHAR(200) NULL
);

INSERT INTO dbo.cars (display_name) VALUES ('My Car');  -- placeholder, edit later

ALTER TABLE dbo.sessions ADD car_id INT NULL
    CONSTRAINT FK_sessions_cars REFERENCES dbo.cars(car_id);
