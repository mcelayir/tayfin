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

## Endpoints

### GET /indicators/latest

Return the most recent indicator value for a single ticker.

| Param | Required | Description |
|---|---|---|
| `ticker` | yes | e.g. `AAPL` |
| `indicator` | yes | e.g. `sma`, `atr`, `vol_sma`, `rolling_high` |
| `window` | no | integer window size (e.g. `50`) |

```bash
curl "http://localhost:8010/indicators/latest?ticker=AAPL&indicator=sma&window=50"
# {"ticker":"AAPL","as_of_date":"2026-02-12","indicator":"sma","params":{"window":50},"value":268.081,"source":"computed"}
```

### GET /indicators/range

Return indicator values for a date range (max ~5 years).

| Param | Required | Description |
|---|---|---|
| `ticker` | yes | e.g. `AAPL` |
| `indicator` | yes | e.g. `sma` |
| `from` | yes | start date `YYYY-MM-DD` |
| `to` | yes | end date `YYYY-MM-DD` |
| `window` | no | integer window size |

```bash
curl "http://localhost:8010/indicators/range?ticker=AAPL&indicator=sma&window=50&from=2025-01-01&to=2026-02-12"
# {"ticker":"AAPL","indicator":"sma","params":{"window":50},"from":"2025-01-01","to":"2026-02-12","items":[...]}
```

### GET /indicators/index/latest

Return the latest indicator value per ticker for all tickers in the specified index.

| Param | Required | Description |
|---|---|---|
| `index_code` | yes | index label (e.g. `NDX`) — filters results to index members |
| `indicator` | yes | e.g. `sma` |
| `window` | no | integer window size |

```bash
curl "http://localhost:8010/indicators/index/latest?index_code=NDX&indicator=sma&window=50"
# {"index_code":"NDX","indicator":"sma","params":{"window":50},"items":[{"ticker":"AAPL","as_of_date":"2026-02-12","value":268.081}]}
```
