/* Link consumables to a car, and account for real-world track days the
   app hasn't ingested yet (Block 2's historical-backfill item is still
   open). sessions_since_install becomes baseline_sessions (frozen count
   of sessions that happened before the car was being tagged on every
   upload) plus a live count of dbo.sessions rows scoped to this car
   since install_date - so it keeps incrementing correctly as new
   sessions get uploaded and tagged with car_id (sql/12_cars.sql), with
   no risk of double-counting the pre-tracking history baked into the
   baseline. car_id NULL means untracked/all-cars, same fallback the
   original query had before this migration. */
ALTER TABLE dbo.consumables ADD car_id INT NULL
    CONSTRAINT FK_consumables_cars REFERENCES dbo.cars(car_id);

ALTER TABLE dbo.consumables ADD baseline_sessions SMALLINT NOT NULL
    CONSTRAINT DF_consumables_baseline_sessions DEFAULT 0;
GO

/* The INSERT below names car_id and baseline_sessions, which the
   batch above has only just added - SQL Server does not reliably see
   them without the GO. This is the migration that first taught us
   that, on 2026-07-30; the separator is now explicit rather than
   applied by hand. */

/* Integra (car_id=2) consumables as of 2026-07-30. baseline_sessions
   is set so sessions_since_install lands on the real-world count given
   for each item today; only session_id=1 (2026-05-16) is car-tagged
   Integra so far and postdates the engine oil's install, hence its
   smaller baseline. */
INSERT INTO dbo.consumables
    (item_name, install_date, service_life_sessions, car_id,
     baseline_sessions, notes)
VALUES
    ('Front brake pads', '2026-05-30', 40, 2, 9, 'Paragon P3'),
    ('Rear brake pads',  '2026-05-30', 60, 2, 9, 'Paragon P3'),
    ('Brake fluid',      '2026-06-13', 12, 2, 9, NULL),
    ('Engine oil',       '2026-04-12', 20, 2, 11, '0W-20');
