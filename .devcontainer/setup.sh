#!/usr/bin/env bash
# Environment bootstrap: MS ODBC driver 18 + Python deps
set -e
curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | \
  sudo gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg
echo "deb [signed-by=/usr/share/keyrings/microsoft-prod.gpg] \
https://packages.microsoft.com/debian/12/prod bookworm main" | \
  sudo tee /etc/apt/sources.list.d/mssql-release.list
sudo apt-get update -qq
sudo ACCEPT_EULA=Y apt-get install -y -qq msodbcsql18 unixodbc-dev
pip install --quiet pyodbc azure-identity
echo "devcontainer ready"
