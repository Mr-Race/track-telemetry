/* Grants the MCP server's Container App system-assigned managed identity
   read-only access, once the Container App exists (see docs/mcp_server.md
   for the provisioning steps). Run as the Entra admin, connected to the
   telemetry database - NOT master. Read-only by design: this server has
   no write path, unlike the ingest Function (sql/05_function_identity.sql).

   Replace <CONTAINER_APP_NAME> with the actual Container App name
   (e.g. 'ca-track-telemetry-mcp'); Azure SQL resolves it to the right
   principal automatically since Entra-only auth is already on. */

CREATE USER [<CONTAINER_APP_NAME>] FROM EXTERNAL PROVIDER;
ALTER ROLE db_datareader ADD MEMBER [<CONTAINER_APP_NAME>];
