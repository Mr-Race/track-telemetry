# Schema and data dictionary

Generated from the live database on 2026-08-13 and hand-annotated. Row
counts are a snapshot; everything else is structural.

Migrations live in `sql/`, numbered, applied and recorded by
`python sql/migrate.py --apply` against the `dbo.schema_migrations`
ledger. See [`sql/README.md`](https://github.com/Mr-Race/track-telemetry/blob/main/sql/README.md).

## The shape of it

```
organizations ─< events >─ tracks ─< corners
                  │                    │
                  └──< sessions ────┐  │
                       │  │  │      │  │
              drivers ─┘  │  └─ cars│  │
                          │         │  │
                          └──< laps─┴──┴──< corner_metrics
                                    └──< segment_times
```

An **event** is a day (or weekend) at a **track**, run by an
**organization**. A **session** is one run group's time on track, driven
by a **driver** in a **car**. A session has **laps**; each lap has
**corner_metrics** (one row per corner passed) and **segment_times**
(corner-to-corner splits).

## Notes that the column types don't tell you

- **`sessions.start_time` is local track time**, not UTC. It is a naive
  column, and storing UTC in it displayed every session 4-5 hours early
  until this was fixed. The conversion uses `tracks.iana_timezone`.
- **`sessions.pedal_channel`** records which OBD channel produced
  `corner_metrics.throttle_pos_apex_pct` — `throttle_pos` (throttle
  plate) before 2026-08-10, `accelerator_pos` (true pedal position)
  after. The two have different rest and full points, so a stored value
  cannot be normalised without it.
- **`corner_metrics.throttle_pos_apex_pct` is raw**, not normalised.
  Per the raw-data-is-sacred principle, calibration is applied on read
  so a future PID change cannot double-correct history.
- **`sessions.source_sha256`** is the content hash used for ingest
  idempotency. Re-uploading a CSV refreshes the session it already
  created instead of duplicating it. A uniqueness check only protects
  rows that carry the key — sessions loaded before this column existed
  were duplicated exactly this way.
- **Two tracks share the name `NJMP Thunderbolt`** and are distinguished
  by `configuration` (Classic, Devil's Pass). Anything matching a track
  by name alone is a latent bug.
- **`drivers`** exists so personal bests can exclude instructor-driven
  sessions. A PB is scoped to a driver, not to a car or an event.

## Tables

### `benchmarks`  (1 rows)

| Column | Type | Null | Key | References |
|---|---|---|---|---|
| `benchmark_id` | int | no | PK |  |
| `track_id` | int | no |  | `tracks.track_id` |
| `driver_name` | nvarchar(100) | no |  |  |
| `lap_time_ms` | int | no |  |  |
| `set_date` | date | yes |  |  |
| `notes` | nvarchar(400) | yes |  |  |

### `cars`  (2 rows)

| Column | Type | Null | Key | References |
|---|---|---|---|---|
| `car_id` | int | no | PK |  |
| `display_name` | nvarchar(50) | no |  |  |
| `make` | nvarchar(50) | yes |  |  |
| `model` | nvarchar(50) | yes |  |  |
| `year` | smallint | yes |  |  |
| `notes` | nvarchar(200) | yes |  |  |

### `consumables`  (4 rows)

| Column | Type | Null | Key | References |
|---|---|---|---|---|
| `consumable_id` | int | no | PK |  |
| `item_name` | nvarchar(100) | no |  |  |
| `install_date` | date | no |  |  |
| `install_session_id` | int | yes |  | `sessions.session_id` |
| `service_life_sessions` | smallint | yes |  |  |
| `service_life_months` | smallint | yes |  |  |
| `notes` | nvarchar(400) | yes |  |  |
| `car_id` | int | yes |  | `cars.car_id` |
| `baseline_sessions` | smallint | no |  |  |
| `previous_consumable_id` | int | yes |  | `consumables.consumable_id` |
| `active` | bit | no |  |  |

### `corner_metrics`  (1393 rows)

| Column | Type | Null | Key | References |
|---|---|---|---|---|
| `corner_metric_id` | int | no | PK |  |
| `lap_id` | int | no | UQ | `laps.lap_id` |
| `corner_id` | int | no | UQ | `corners.corner_id` |
| `min_speed_mph` | decimal(5,1) | no |  |  |
| `entry_speed_mph` | decimal(5,1) | yes |  |  |
| `exit_speed_mph` | decimal(5,1) | yes |  |  |
| `throttle_pos_apex_pct` | decimal(5,1) | yes |  |  |
| `rpm_exit` | decimal(6,1) | yes |  |  |

### `corners`  (34 rows)

| Column | Type | Null | Key | References |
|---|---|---|---|---|
| `corner_id` | int | no | PK |  |
| `track_id` | int | no | UQ | `tracks.track_id` |
| `corner_code` | nvarchar(4) | no | UQ |  |
| `sort_order` | tinyint | no |  |  |
| `corner_name` | nvarchar(50) | yes |  |  |
| `apex_lat` | decimal(9,6) | yes |  |  |
| `apex_lon` | decimal(9,6) | yes |  |  |
| `zone_radius_m` | smallint | no |  |  |

### `drivers`  (2 rows)

| Column | Type | Null | Key | References |
|---|---|---|---|---|
| `driver_id` | int | no | PK |  |
| `display_name` | nvarchar(100) | no |  |  |
| `entra_object_id` | nvarchar(100) | yes |  |  |

### `events`  (7 rows)

| Column | Type | Null | Key | References |
|---|---|---|---|---|
| `event_id` | int | no | PK |  |
| `track_id` | int | no |  | `tracks.track_id` |
| `event_name` | nvarchar(100) | no |  |  |
| `start_date` | date | no |  |  |
| `end_date` | date | yes |  |  |
| `notes` | nvarchar(max) | yes |  |  |
| `organization_id` | int | no |  | `organizations.organization_id` |

### `laps`  (127 rows)

| Column | Type | Null | Key | References |
|---|---|---|---|---|
| `lap_id` | int | no | PK |  |
| `session_id` | int | no | UQ | `sessions.session_id` |
| `lap_number` | smallint | no | UQ |  |
| `lap_time_ms` | int | no |  |  |
| `is_valid` | bit | no |  |  |
| `is_out_lap` | bit | no |  |  |
| `is_in_lap` | bit | no |  |  |
| `notes` | nvarchar(400) | yes |  |  |

### `organizations`  (2 rows)

| Column | Type | Null | Key | References |
|---|---|---|---|---|
| `organization_id` | int | no | PK |  |
| `org_code` | nvarchar(20) | no | UQ |  |
| `org_name` | nvarchar(100) | no |  |  |

### `run_groups`  (7 rows)

| Column | Type | Null | Key | References |
|---|---|---|---|---|
| `run_group_id` | int | no | PK |  |
| `organization_id` | int | no | UQ | `organizations.organization_id` |
| `group_code` | nvarchar(20) | no | UQ |  |
| `sort_order` | tinyint | no |  |  |

### `schema_migrations`  (23 rows)

| Column | Type | Null | Key | References |
|---|---|---|---|---|
| `filename` | nvarchar(260) | no | PK |  |
| `checksum` | char(64) | no |  |  |
| `applied_at` | datetime2 | no |  |  |
| `applied_by` | nvarchar(128) | yes |  |  |

### `segment_times`  (1520 rows)

| Column | Type | Null | Key | References |
|---|---|---|---|---|
| `segment_time_id` | int | no | PK |  |
| `lap_id` | int | no | UQ | `laps.lap_id` |
| `segment_order` | tinyint | no | UQ |  |
| `to_corner_id` | int | yes |  | `corners.corner_id` |
| `segment_time_ms` | int | no |  |  |

### `sessions`  (15 rows)

| Column | Type | Null | Key | References |
|---|---|---|---|---|
| `session_id` | int | no | PK |  |
| `event_id` | int | no | UQ | `events.event_id` |
| `session_number` | tinyint | no | UQ |  |
| `session_date` | date | no |  |  |
| `start_time` | datetime2 | yes |  |  |
| `weather` | nvarchar(50) | yes |  |  |
| `air_temp_f` | decimal(4,1) | yes |  |  |
| `tire_notes` | nvarchar(200) | yes |  |  |
| `source_file` | nvarchar(260) | yes |  |  |
| `notes` | nvarchar(max) | yes |  |  |
| `driver_id` | int | no |  | `drivers.driver_id` |
| `run_group_id` | int | yes |  | `run_groups.run_group_id` |
| `car_id` | int | yes |  | `cars.car_id` |
| `humidity_pct` | decimal(4,1) | yes |  |  |
| `wind_mph` | decimal(4,1) | yes |  |  |
| `precip_in` | decimal(5,2) | yes |  |  |
| `weather_observed_at` | datetime2 | yes |  |  |
| `source_sha256` | char(64) | yes |  |  |
| `pedal_channel` | nvarchar(32) | yes |  |  |

### `tracks`  (3 rows)

| Column | Type | Null | Key | References |
|---|---|---|---|---|
| `track_id` | int | no | PK |  |
| `track_name` | nvarchar(100) | no | UQ |  |
| `configuration` | nvarchar(100) | yes | UQ |  |
| `length_miles` | decimal(4,2) | yes |  |  |
| `iana_timezone` | nvarchar(50) | yes |  |  |
