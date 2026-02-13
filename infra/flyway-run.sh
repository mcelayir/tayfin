#!/bin/bash
set -euo pipefail

export FLYWAY_URL=jdbc:postgresql://db:5432/${POSTGRES_DB}
export FLYWAY_USER=${POSTGRES_USER}
export FLYWAY_PASSWORD=${POSTGRES_PASSWORD}

echo "Running Flyway for tayfin_ingestor"
FLYWAY_LOCATIONS=filesystem:/flyway/sql/tayfin-ingestor FLYWAY_DEFAULT_SCHEMA=tayfin_ingestor flyway migrate

echo "Running Flyway for tayfin_screener"
FLYWAY_LOCATIONS=filesystem:/flyway/sql/tayfin-screener FLYWAY_DEFAULT_SCHEMA=tayfin_screener flyway migrate

echo "Running Flyway for tayfin_analyzer"
FLYWAY_LOCATIONS=filesystem:/flyway/sql/tayfin-analyzer FLYWAY_DEFAULT_SCHEMA=tayfin_analyzer flyway migrate

echo "Running Flyway for tayfin_indicator"
FLYWAY_LOCATIONS=filesystem:/flyway/sql/tayfin-indicator FLYWAY_DEFAULT_SCHEMA=tayfin_indicator flyway migrate

echo "Flyway migrations completed"
