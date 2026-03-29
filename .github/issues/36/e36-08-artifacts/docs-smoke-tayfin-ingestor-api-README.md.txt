Checking tayfin-ingestor/tayfin-ingestor-api/README.md
### Environment Variables (API)
### Environment Variables (API)
**Curl Example**
curl -sS "http://localhost:8000/fundamentals/latest?symbol=AAPL" \
**Curl Examples**
curl -sS "http://localhost:8000/ohlcv?ticker=AAPL" \
curl -sS "http://localhost:8000/ohlcv?ticker=AAPL&from=2026-01-01&to=2026-03-21" \
- [ ] Run `curl` examples against local dev and verify response shapes.  
curl "http://localhost:8000/ohlcv?ticker=AAPL"
curl "http://localhost:8000/ohlcv?ticker=AAPL&from=2025-06-01&to=2025-06-05"
curl "http://localhost:8000/ohlcv?index_code=NDX"
--- summary ---
FAIL: missing one or more required headings
