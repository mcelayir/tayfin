# Tech Debt Log: Issue #46 — Pre-existing Debt

Logged before implementation begins on 2026-04-19.
These items pre-exist this branch and are NOT introduced by it.

---

## TD-1: `test_tradingview_bist_provider.py` mocks a non-existent import

**File:** `tayfin-ingestor/tayfin-ingestor-jobs/tests/test_tradingview_bist_provider.py`

**Severity:** Medium — tests provide false confidence

**Description:**
The test file's docstring and patch target both reference `get_all_symbols`:

```python
# Docstring:
# All calls to get_all_symbols are mocked via unittest.mock.patch.
# Patch target: "tayfin_ingestor_jobs.discovery.providers.tradingview_bist.get_all_symbols"

PATCH_TARGET = "tayfin_ingestor_jobs.discovery.providers.tradingview_bist.get_all_symbols"
```

The production provider `tradingview_bist.py` no longer imports or calls
`get_all_symbols`. It was updated to use `Query().get_scanner_data()` from
`tradingview_screener`. Because `unittest.mock.patch` silently succeeds when
patching a non-existent name on a module (it injects the attribute), the
patch takes no effect on the actual `Query()` call path. All 8 tests pass
trivially by accident — not because the provider behaves correctly.

**Additional breakage:** The provider now returns dicts with 4 keys
`{"ticker", "country", "index_code", "exchange"}`, but `test_dict_keys`
asserts exactly 3 keys `{"ticker", "country", "index_code"}`. This test
would fail if the mock were ever fixed to actually intercept the query.

**NOT fixed in this issue.** Tracked here for a follow-up issue.

**Correct fix (for follow-up):** Replace the `PATCH_TARGET`-based mock with
a patch of `tradingview_screener.Query` using `MagicMock` chaining, and
update `test_dict_keys` to assert 4 keys including `exchange`.

---

## TD-2: `default_exchange` absent from NASDAQ-100 `ohlcv.yml` entry

**File:** `tayfin-ingestor/tayfin-ingestor-jobs/config/ohlcv.yml`

**Severity:** Low — no functional impact today (hardcoded fallback is `NASDAQ`)

**Description:**
The `nasdaq-100` entry in `ohlcv.yml` omits `default_exchange`. The service
falls back to `_DEFAULT_EXCHANGE = "NASDAQ"` (hardcoded string in
`service.py`). If that default ever changes, or if a BIST instrument is
accidentally stored with `exchange = NULL` and a future operator uses the
nasdaq-100 config path to debug, the asymmetry between the two config
entries will cause confusion.

**NOT fixed in this issue.** This issue adds `default_exchange: BIST`
explicitly to the new `bist` config entry; the NASDAQ entry is intentionally
left untouched per constraint C3.

**Correct fix (for follow-up):** Add `default_exchange: NASDAQ` to the
`nasdaq-100` entry in `ohlcv.yml` and the corresponding entry in
`ohlcv_backfill.yml` for explicit parity.
