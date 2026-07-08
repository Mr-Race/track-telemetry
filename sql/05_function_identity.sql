/* Grants the ingest Function App's system-assigned managed identity
   read/write access, once the Function App exists (see docs/BACKLOG.md
   for the provisioning steps). Run as the Entra admin, connected to the
   telemetry database - NOT master.

   Replace <FUNCTION_APP_NAME> with the actual Function App name
   (e.g. 'func-track-telemetry-ingest'); Azure SQL resolves it to the
   right principal automatically since Entra-only auth is already on. */

CREATE USER [<FUNCTION_APP_NAME>] FROM EXTERNAL PROVIDER;
ALTER ROLE db_datareader ADD MEMBER [<FUNCTION_APP_NAME>];
ALTER ROLE db_datawriter ADD MEMBER [<FUNCTION_APP_NAME>];
