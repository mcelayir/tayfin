# tradingview-scraper — Capability Guide

This document captures an evidence-based capability inventory and usage patterns for the `tradingview-scraper` Python package as exercised by the examples in `docs/examples/tradingview_scraper/`.

Overview
--------
- Purpose: programmatic scraping of TradingView resources (ideas, technical indicators, news, screener results, symbol overview / OHLCV snapshots) where the library exposes high-level classes.
- Typical Tayfin use-cases: building scrapers for a screener, obtaining recent indicator snapshots (RSI, Stoch), collecting headlines for sentiment analysis, and fetching short-term OHLCV snapshots for research.

Capability matrix (evidence-based)
----------------------------------
The table below maps feature areas to the modules/classes used in the example scripts. These are the exact import paths exercised by the examples in `docs/examples/tradingview_scraper`.

| Feature Area | Primary module/class used (example) | Required inputs | Output shape (example fields) |
|---|---:|---|---|
| Ideas | `tradingview_scraper.symbols.ideas.Ideas` | `symbol` (e.g. BTCUSD), optional paging/sort | list of dicts: `{ "title", "author", "body", "created_at" }` (examples may redact long body)
| Indicators / Technicals | `tradingview_scraper.symbols.technicals.Indicators` | `exchange`, `symbol`, `timeframe`, `indicators` list | dict/list with indicator values per series: keys like `RSI`, `STOCH.K` depending on provider
| News / Headlines | `tradingview_scraper.symbols.news.NewsScraper` | `symbol` | list of headlines / article metadata (title, source, url)
| Screener | library-specific screener class (examples try to import `tradingview_scraper.screener` variants) | `market` / filters (e.g. `market=america`) | list/dict rows with selected columns (symbol, price, market_cap)
| Symbol overview / OHLCV | symbol-specific methods present on package (examples attempt `symbol overview` calls) | `symbol`, `exchange`, `timeframe` | OHLCV time-series in DataFrame-like structure or dict
| Introspection | Standard Python `pkgutil` / `inspect` on `tradingview_scraper` | None | JSON inventory of modules, classes and callable methods

Rate limits, captcha and reliability notes
----------------------------------------
- TradingView actively rate-limits and may present captchas or block scraping.
- The common workaround is to provide a session cookie (browser cookie) that includes the TradingView session authentication. The examples will check the env var `TRADINGVIEW_COOKIE` if scraping encounters a captcha or blocked request.
- Env var used by examples: `TRADINGVIEW_COOKIE` (do not commit this value). If required, set it in your shell before running examples:

  export TRADINGVIEW_COOKIE="<your_cookie_here>"

- Reliability: scraping may return empty results, partial data, or raise exceptions when TradingView changes the site format. Examples are defensive and print actionable messages on failures.

How to run the examples
-----------------------
1. Create and activate a venv (recommended):

   python -m venv .venv
   source .venv/bin/activate

2. Install the package (examples assume `tradingview-scraper` is available):

   pip install tradingview-scraper

3. Run examples from repo root (examples write to `docs/examples/tradingview_scraper/out/` by default):

   python docs/examples/tradingview_scraper/smoke_ideas.py --symbol BTCUSD
   python docs/examples/tradingview_scraper/smoke_indicators.py --symbol BTCUSD --timeframe 1d
   python docs/examples/tradingview_scraper/smoke_news.py --symbol BTCUSD
   python docs/examples/tradingview_scraper/smoke_screener.py --market america
   python docs/examples/tradingview_scraper/introspect_modules.py

Troubleshooting
---------------
- If you hit captchas or empty outputs: set `TRADINGVIEW_COOKIE` and re-run.
- If `ModuleNotFoundError: tradingview_scraper`: install from PyPI.
- If specific example fails due to a missing class/method, inspect `docs/examples/tradingview_scraper/introspect_modules.py` output (`out/inventory.json`) to see available modules and adapt the script accordingly.

Notes
-----
- The examples are deliberately conservative: they attempt safe imports and handle missing API surfaces gracefully, printing instructions rather than crashing.
- Only document and rely on classes that the examples exercise; if a method is not present in the installed package the script reports it and exits with a helpful message.

Guide produced from running the example scripts in `docs/examples/tradingview_scraper/` and introspecting the installed package.
