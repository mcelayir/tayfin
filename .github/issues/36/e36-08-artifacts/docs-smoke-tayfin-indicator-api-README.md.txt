Checking tayfin-indicator/tayfin-indicator-api/README.md
## Environment variables
curl http://localhost:8010/health
curl "http://localhost:8010/indicators/latest?ticker=AAPL&indicator=sma&window=50"
curl "http://localhost:8010/indicators/range?ticker=AAPL&indicator=sma&window=50&from=2025-01-01&to=2026-02-12"
curl "http://localhost:8010/indicators/index/latest?index_code=NDX&indicator=sma&window=50"
--- summary ---
FAIL: missing one or more required headings
