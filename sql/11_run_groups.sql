/* Run group tables: replace the free-text events.organization and
   sessions.run_group columns with real reference tables + FKs, per
   the project's schema-scalability preference (real tables now while
   data volume is tiny, not a nullable-text stopgap).

   Run group codes/spelling as given 2026-07-24 - fix here (simple
   UPDATE, both tables are tiny) if any label is off:
     SCCA-HPDE:    Novice, Intermediate, Advanced
     NASA NE HPDE: DE1, DE2, DE3, DE4-Instructors
   ("DE4-Instructors" assumed from "D4-Instructors" - NASA HPDE run
   groups are conventionally DE1-DE4; correct if that's not it.) */

CREATE TABLE dbo.organizations (
    organization_id INT IDENTITY(1,1) PRIMARY KEY,
    org_code        NVARCHAR(20)  NOT NULL,   -- e.g. 'SCCA-HPDE'
    org_name        NVARCHAR(100) NOT NULL,   -- e.g. 'SCCA HPDE'
    CONSTRAINT UQ_organizations_code UNIQUE (org_code)
);

CREATE TABLE dbo.run_groups (
    run_group_id    INT IDENTITY(1,1) PRIMARY KEY,
    organization_id INT NOT NULL
        CONSTRAINT FK_run_groups_organizations
        REFERENCES dbo.organizations(organization_id),
    group_code      NVARCHAR(20) NOT NULL,    -- e.g. 'Novice', 'DE1'
    sort_order      TINYINT NOT NULL,         -- experience order within the org
    CONSTRAINT UQ_run_groups_org_code UNIQUE (organization_id, group_code)
);

INSERT INTO dbo.organizations (org_code, org_name) VALUES
('SCCA-HPDE', 'SCCA HPDE'),
('NASA-NE-HPDE', 'NASA NE HPDE');

INSERT INTO dbo.run_groups (organization_id, group_code, sort_order)
SELECT organization_id, v.group_code, v.sort_order
FROM dbo.organizations o
CROSS APPLY (VALUES ('Novice', 1), ('Intermediate', 2), ('Advanced', 3))
    AS v(group_code, sort_order)
WHERE o.org_code = 'SCCA-HPDE';

INSERT INTO dbo.run_groups (organization_id, group_code, sort_order)
SELECT organization_id, v.group_code, v.sort_order
FROM dbo.organizations o
CROSS APPLY (VALUES ('DE1', 1), ('DE2', 2), ('DE3', 3),
                     ('DE4-Instructors', 4)) AS v(group_code, sort_order)
WHERE o.org_code = 'NASA-NE-HPDE';

/* ---- events.organization (free text) -> organization_id (FK) ---- */
ALTER TABLE dbo.events ADD organization_id INT NULL
    CONSTRAINT FK_events_organizations REFERENCES dbo.organizations(organization_id);
GO

-- Both existing events are already tagged 'NASA-NE'. Separate batch:
-- organization_id was added in the batch above and is not reliably
-- visible until this one.
UPDATE dbo.events SET organization_id =
    (SELECT organization_id FROM dbo.organizations WHERE org_code = 'NASA-NE-HPDE')
WHERE organization = 'NASA-NE';
GO

/* Verify every event backfilled before tightening to NOT NULL */
SELECT event_id, event_name, organization, organization_id FROM dbo.events;
GO

-- Tightening to NOT NULL depends on the UPDATE above having committed.
ALTER TABLE dbo.events ALTER COLUMN organization_id INT NOT NULL;
GO

ALTER TABLE dbo.events DROP COLUMN organization;
GO

/* ---- sessions.run_group (free text) -> run_group_id (FK) ----
   Currently NULL on every session (never populated by ingestion -
   it's a manually-set field, like weather/tire_notes), so there's
   nothing to backfill; stays nullable since not every session will
   have a logged run group. */
ALTER TABLE dbo.sessions ADD run_group_id INT NULL
    CONSTRAINT FK_sessions_run_groups REFERENCES dbo.run_groups(run_group_id);
GO

ALTER TABLE dbo.sessions DROP COLUMN run_group;
GO
