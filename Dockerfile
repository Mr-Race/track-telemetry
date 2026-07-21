# Lives at the repo root (not mcp_server/) because az containerapp up
# --source only looks for ./Dockerfile in the given source dir, and this
# needs the repo root as build context so it can COPY ingest/ (server.py
# imports ingest.cloud / ingest.racechrono_parser).
FROM python:3.12-slim

WORKDIR /app

COPY mcp_server/requirements.txt mcp_server/requirements.txt
RUN pip install --no-cache-dir -r mcp_server/requirements.txt

COPY ingest/ ingest/
COPY mcp_server/ mcp_server/

EXPOSE 8000
CMD ["python", "-m", "mcp_server.server"]
