/* Consumables replacement history (v2). Logging a replacement (new
   pads, a fluid flush, an oil change) no longer edits the existing
   row in place - it retires the old row (active = 0) and inserts a
   fresh one with today's install_date, so remaining-life% resets to
   100 immediately (life is always computed from a row's own
   install_date, sql/08_consumables.sql) while the full service
   history for a car stays queryable via previous_consumable_id.
   Run as: Entra admin, connected to the telemetry database. */
ALTER TABLE dbo.consumables ADD active BIT NOT NULL
    CONSTRAINT DF_consumables_active DEFAULT 1;

ALTER TABLE dbo.consumables ADD previous_consumable_id INT NULL
    CONSTRAINT FK_consumables_previous
        REFERENCES dbo.consumables(consumable_id);
