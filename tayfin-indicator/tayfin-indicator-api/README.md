# tayfin-indicator-api

Read-only REST API exposing computed technical indicators.

## Install

```bash
pip install -r requirements.txt
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_HOST` | `localhost` | Database host |
| `POSTGRES_PORT` | `5432` | Database port |
| `POSTGRES_DB` | `tayfin` | Database name |
| `POSTGRES_USER` | `tayfin_user` | Database user |
| `POSTGRES_PASSWORD` | _(empty)_ | Database password |

You can also source the repo-root `.env` file.

## Run

```bash
# Option 1: helper script (loads .env, installs deps, starts on port 8010)
bash scripts/run_api.sh

# Option 2: manual
export PYTHONPATH=src
source ../../.env          # or export vars manually
flask --app tayfin_indicator_api.app run --port 8010
```

## Health check

```bash
curl http://localhost:8010/health
# {"status":"ok"}
```
