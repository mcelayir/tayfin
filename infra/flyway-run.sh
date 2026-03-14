#!/bin/bash
set -euo pipefail

export POSTGRES_DB=${POSTGRES_DB:-tayfin}
export POSTGRES_USER=${POSTGRES_USER:-tayfin_user}
export POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-tayfin_password}

export FLYWAY_URL=jdbc:postgresql://db:5432/${POSTGRES_DB}
export FLYWAY_USER=${POSTGRES_USER}
export FLYWAY_PASSWORD=${POSTGRES_PASSWORD}

# Wait for the DB to accept client connections (pg_isready can return
# true before the DB is ready for authenticated connections on first boot).
for i in $(seq 1 10); do
  if flyway info >/dev/null 2>&1; then
    break
  fi
  echo "Waiting for DB to accept connections (attempt $i/10)…"
  sleep 2
done

# Fail fast if DB never became ready (avoids cryptic Flyway errors).
if ! flyway info >/dev/null 2>&1; then
  echo "Error: Flyway could not connect to the database after 10 attempts; aborting migrations." >&2
  exit 1
fi

echo "Running Flyway for tayfin_ingestor"
FLYWAY_LOCATIONS=filesystem:/flyway/sql/tayfin-ingestor FLYWAY_DEFAULT_SCHEMA=tayfin_ingestor flyway migrate

echo "Running Flyway for tayfin_screener"
FLYWAY_LOCATIONS=filesystem:/flyway/sql/tayfin-screener FLYWAY_DEFAULT_SCHEMA=tayfin_screener flyway migrate

echo "Running Flyway for tayfin_analyzer"
FLYWAY_LOCATIONS=filesystem:/flyway/sql/tayfin-analyzer FLYWAY_DEFAULT_SCHEMA=tayfin_analyzer flyway migrate

echo "Running Flyway for tayfin_indicator"
FLYWAY_LOCATIONS=filesystem:/flyway/sql/tayfin-indicator FLYWAY_DEFAULT_SCHEMA=tayfin_indicator flyway migrate

echo "Flyway migrations completed"
