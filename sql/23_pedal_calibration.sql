/* Calibration constants for pedal-position channels.

   `corner_metrics.throttle_pos_apex_pct` stores the raw percentage the
   OBD channel reported. Raw is not percent-of-travel: a pedal position
   sensor has a voltage baseline, so the pedal at rest reads 18.82% and
   at the stop reads 94.90% (issue #8, measured 2026-08-10 by flooring it
   in 6th at low rpm and watching the value plateau). Reading a corner
   as "18.8% throttle" when the driver's foot was completely off it is
   not a rounding problem, it is a wrong answer.

   Per the raw-data-is-sacred principle, normalisation happens on read
   and never at ingest. If the PID or the sensor ever changes, baking a
   correction into stored values would make historical sessions
   double-correct, and the error would be invisible.

   Keyed on (car_id, channel), not car alone. `throttle_pos` (throttle
   plate) and `accelerator_pos` (true pedal position) are different
   signals with different rest and full points, and the archive contains
   both - which is what `sessions.pedal_channel` (migration 22) exists to
   disambiguate.

   A table rather than columns on `dbo.cars` because the relationship is
   genuinely one-car-to-many-channels, and because a second car would
   otherwise need its own pair of nullable columns per channel.

   No row is seeded for `throttle_pos`. Nobody has measured that
   channel's rest and full points on this car, and inventing plausible
   numbers would silently rescale two years of history. A session whose
   channel has no calibration returns a null normalised value and its
   raw value unchanged - visibly uncalibrated rather than quietly wrong. */

CREATE TABLE dbo.pedal_calibration (
    calibration_id  INT IDENTITY(1,1) NOT NULL
        CONSTRAINT PK_pedal_calibration PRIMARY KEY,
    car_id          INT            NOT NULL
        CONSTRAINT FK_pedal_calibration_car
        REFERENCES dbo.cars (car_id),
    channel         NVARCHAR(32)   NOT NULL,
    rest_pct        DECIMAL(5,2)   NOT NULL,
    full_pct        DECIMAL(5,2)   NOT NULL,
    measured_on     DATE           NULL,
    notes           NVARCHAR(400)  NULL,
    CONSTRAINT UQ_pedal_calibration_car_channel UNIQUE (car_id, channel),
    -- Guards the divide in the normalisation: an inverted or equal pair
    -- would produce a division by zero or a mirrored scale.
    CONSTRAINT CK_pedal_calibration_range CHECK (full_pct > rest_pct)
);
GO

INSERT INTO dbo.pedal_calibration
    (car_id, channel, rest_pct, full_pct, measured_on, notes)
VALUES
    (2, 'accelerator_pos', 18.82, 94.90, '2026-08-10',
     'Measured per issue #8. Rest = 48/255 sensor baseline; full = '
     + '242/255, confirmed by flooring it in 6th at low rpm where the '
     + 'value plateaus. RaceChrono''s gauge and the car dash both show '
     + '100% at full pedal - that is UI normalisation, not the signal.');
GO
